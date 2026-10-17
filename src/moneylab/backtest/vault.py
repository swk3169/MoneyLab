"""Locked vault for the holdout and forward periods (BT-3d; docs/tasks/BT-3D/WORK_ORDER.md, docs/backtest_design.md
section 10.3, v0.6 draft section 19). Files only: no provider, no network, no CLI.

A vault splits two verified bar directories (daily, hourly) at explicit UTC boundaries (VaultSpec):
  PUBLIC        end_utc <= C                  (confirmatory data, warm-up included; standard bars/1 directories)
  HOLDOUT_EVAL  C < end_utc <= H              (locked)
  EXCLUDED      H < end_utc <= L              (locked, lookback only; empty when H == L)
An input bar ending after L refuses the build, so PUBLIC + locked rows are exactly the input. Forward bars (after L)
enter only through ForwardVault.seal, one calendar month per sealed directory.

Layout of <out_root>/<vault_id>/ (out_root must end with "-fixture" for fixture/synthetic bars):
  vault_manifest.json, SHA256SUMS.txt, public/<input dir name>/ (x2), locked/holdout_<interval>.jsonl   sealed set
  build_record.json, evidence/, access/, locked_forward/forward_YYYYMM/                               state entries
Sealed bytes are never written again. Access and evidence records are created once, exclusively (temporary file,
fsync, os.link) and never rewritten or removed; the vault manifest is not rewritten on access.

Locked rows are returned only by HistoricalHoldoutVault.open_once and ForwardVault.open_analysis. Both check every
precondition first (a failure there does not consume the single use), then create the access record, and only then
read: any failure after the record exists consumes the use. Status and error messages carry counts, hashes and
pass/fail only, never locked prices or bar times.

"forward N months" is not interpreted here: the analysis ends come from VaultSpec as explicit UTC boundaries (the
conversion belongs to the BT-4 config freeze). The monthly forward risk-limit check is not implemented (deferred).
All vaults of fixture or synthetic bars are SYNTHETIC / NOT_EVIDENCE.
"""

from __future__ import annotations

# Every import is bound to a private name: the supported public API is exactly __all__ (D1).
import hashlib as _hashlib
import json as _json
import os as _os
import platform as _platform
import re as _re
import tempfile as _tempfile
from dataclasses import dataclass as _dataclass
from datetime import UTC as _UTC
from datetime import datetime as _datetime
from datetime import timedelta as _timedelta
from decimal import Decimal as _Decimal
from pathlib import Path as _Path
from typing import Any as _Any

from moneylab.backtest.bars_io import MANIFEST_FILE as _BARS_MANIFEST_FILE
from moneylab.backtest.bars_io import REFUSED_KINDS as _REFUSED_KINDS
from moneylab.backtest.bars_io import SCHEMA as _BARS_SCHEMA
from moneylab.backtest.bars_io import SUMS_FILE as _SUMS_FILE
from moneylab.backtest.bars_io import load_bars as _load_bars
from moneylab.backtest.data import BarSeries as _BarSeries
from moneylab.backtest.data import DataIntegrityError as _DataIntegrityError
from moneylab.domain.bars import NOT_EVIDENCE as _NOT_EVIDENCE
from moneylab.domain.bars import PROVENANCE_KINDS as _PROVENANCE_KINDS
from moneylab.domain.bars import Bar as _Bar
from moneylab.domain.bars import bars_sha256 as _bars_sha256
from moneylab.domain.bars import canonical_bar_rows as _canonical_bar_rows
from moneylab.domain.bars import utc_iso as _utc_iso
from moneylab.storage.atomic import atomic_write_bytes as _atomic_write_bytes
from moneylab.storage.atomic import sha256_file as _sha256_file
from moneylab.storage.atomic import sha256_of as _sha256_of

__all__ = [
    "VaultSpec", "build_vault", "vault_status", "record_evidence", "HistoricalHoldoutVault", "ForwardVault",
    "VaultError", "VaultLockedError", "VaultPreconditionError", "VaultIntegrityError", "VaultExistsError",
    "CREATED", "ALREADY_SEALED_IDENTICAL", "RECORDED", "ALREADY_RECORDED_IDENTICAL", "UNOPENED", "OPENED",
    "RECORD_UNREADABLE", "ABSENT", "PASS", "FAIL",
]

_SCHEMA = "moneylab.backtest.vault/1"
_SEAL_SCHEMA = "moneylab.backtest.vault_forward_seal/1"
_EVIDENCE_SCHEMA = "moneylab.backtest.vault_evidence/1"
_ACCESS_KEYS = ("kind", "vault_content_sha256", "preregistration_sha256", "config_sha256", "evidence", "files",
                "opened_at_utc", "caller")  # D7: an access record holds exactly these keys
_BUILD_SCHEMA = "moneylab.backtest.vault_build/1"

_VAULT_MANIFEST = "vault_manifest.json"
_BUILD_RECORD = "build_record.json"
_SEAL_FILE = "seal.json"
_PUBLIC_DIR, _LOCKED_DIR, _FORWARD_DIR = "public", "locked", "locked_forward"
_EVIDENCE_DIR, _ACCESS_DIR = "evidence", "access"
_SEALED_TOP = (_VAULT_MANIFEST, _SUMS_FILE, _PUBLIC_DIR, _LOCKED_DIR)
_STATE_TOP = (_BUILD_RECORD, _EVIDENCE_DIR, _ACCESS_DIR, _FORWARD_DIR)
_FIXTURE_ROOT_SUFFIX = "-fixture"
_INTERVALS = ("day", "hour")

_EVIDENCE_KINDS = ("confirmatory_results", "row9_strategy", "q12_done")
_ANALYSIS_KINDS = ("interim", "final")
_HOLDOUT_OPEN = "holdout_open"
_HOLDOUT_EVAL, _EXCLUDED = "HOLDOUT_EVAL", "EXCLUDED"

CREATED, ALREADY_SEALED_IDENTICAL = "CREATED", "ALREADY_SEALED_IDENTICAL"
RECORDED, ALREADY_RECORDED_IDENTICAL = "RECORDED", "ALREADY_RECORDED_IDENTICAL"
UNOPENED, OPENED, RECORD_UNREADABLE = "UNOPENED", "OPENED", "RECORD_UNREADABLE"
ABSENT = "ABSENT"
PASS, FAIL = "PASS", "FAIL"

_HEX64 = _re.compile(r"[0-9a-f]{64}")
_MONTH = _re.compile(r"(\d{4})(\d{2})")
_FORWARD_NAME = _re.compile(r"forward_(\d{6})")
_SPEC_TIMES = ("confirmatory_data_end_utc", "holdout_end_utc", "locked_end_utc", "forward_interim_end_utc",
               "forward_final_end_utc")
_PAYLOAD_KEYS = ("schema", "market", "provenance", "spec", "intervals")


class VaultError(ValueError):
    """The vault cannot be built, read, opened or trusted."""


class VaultLockedError(VaultError):
    """The single use is already consumed (an access record exists or another caller created it first)."""


class VaultPreconditionError(VaultError):
    """A precondition is not met. Raised before any access record, so the single use is not consumed."""


class VaultIntegrityError(VaultError):
    """Files disagree with their recorded hashes or structure (before the access record: use not consumed;
    after it: consumed)."""


class VaultExistsError(VaultError):
    """An existing vault, forward month or record differs from what would be written; nothing is overwritten."""


# --- spec ---------------------------------------------------------------------------------------------------------

def _require_boundary(t: _Any, name: str) -> _datetime:
    if not isinstance(t, _datetime) or t.tzinfo is None or t.utcoffset() != _timedelta(0):
        raise VaultPreconditionError(f"{name} must be a timezone-aware UTC datetime")
    if t.hour or t.minute or t.second or t.microsecond:
        raise VaultPreconditionError(f"{name} must be 00:00:00 UTC")
    return t


def _require_hex(value: _Any, name: str) -> str:
    if not isinstance(value, str) or not _HEX64.fullmatch(value):
        raise VaultPreconditionError(f"{name} must be 64 lowercase hex characters")
    return value


@_dataclass(frozen=True)
class VaultSpec:
    """Explicit vault boundaries (no defaults). holdout_end_utc is exclusive (H_end + 1 day); locked_end_utc is the
    freeze date 00:00 UTC. A forward analysis end is an explicit UTC boundary or None (that analysis is disabled)."""

    confirmatory_data_end_utc: _datetime
    holdout_end_utc: _datetime
    locked_end_utc: _datetime
    forward_interim_end_utc: _datetime | None
    forward_final_end_utc: _datetime | None
    preregistration_sha256: str
    config_sha256: str

    def __post_init__(self) -> None:
        c = _require_boundary(self.confirmatory_data_end_utc, "confirmatory_data_end_utc")
        h = _require_boundary(self.holdout_end_utc, "holdout_end_utc")
        lk = _require_boundary(self.locked_end_utc, "locked_end_utc")
        if not c < h <= lk:
            raise VaultPreconditionError("boundaries must satisfy confirmatory_data_end < holdout_end <= locked_end")
        ends = {}
        for name in ("forward_interim_end_utc", "forward_final_end_utc"):
            w = getattr(self, name)
            if w is not None:
                ends[name] = _require_boundary(w, name)
                if w <= lk:
                    raise VaultPreconditionError(f"{name} must be after locked_end_utc")
        if len(ends) == 2 and not ends["forward_interim_end_utc"] < ends["forward_final_end_utc"]:
            raise VaultPreconditionError("forward_interim_end_utc must be before forward_final_end_utc")
        _require_hex(self.preregistration_sha256, "preregistration_sha256")
        _require_hex(self.config_sha256, "config_sha256")

    def analysis_end(self, kind: str) -> _datetime | None:
        if kind not in _ANALYSIS_KINDS:
            raise VaultPreconditionError(f"unknown analysis kind {kind!r}")
        return self.forward_interim_end_utc if kind == "interim" else self.forward_final_end_utc

    def to_dict(self) -> dict[str, _Any]:
        out: dict[str, _Any] = {k: (None if getattr(self, k) is None else _utc_iso(getattr(self, k)))
                               for k in _SPEC_TIMES}
        out["preregistration_sha256"] = self.preregistration_sha256
        out["config_sha256"] = self.config_sha256
        return out

    @classmethod
    def from_dict(cls, d: dict[str, _Any]) -> VaultSpec:
        times = {k: None if d[k] is None else _datetime.fromisoformat(d[k].replace("Z", "+00:00")) for k in _SPEC_TIMES}
        return cls(**times, preregistration_sha256=d["preregistration_sha256"], config_sha256=d["config_sha256"])


# --- small helpers ------------------------------------------------------------------------------------------------

def _sha(data: bytes) -> str:
    return _hashlib.sha256(data).hexdigest()


def _json_bytes(doc: dict[str, _Any]) -> bytes:
    return (_json.dumps(doc, sort_keys=True, indent=1) + "\n").encode("utf-8")


def _sums_bytes(entries: dict[str, bytes]) -> bytes:
    return "".join(f"{_sha(data)}  {name}\n"
                   for name, data in sorted(entries.items(), key=lambda kv: kv[0].encode())).encode("utf-8")


def _parse_sums(data: bytes, where: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in data.decode("utf-8").splitlines():
        digest, sep, name = line.partition("  ")
        if not sep or not _HEX64.fullmatch(digest) or not name or name in out:
            raise VaultIntegrityError(f"{where}: malformed {_SUMS_FILE}")
        out[name] = digest
    return out


def _now() -> str:
    return _utc_iso(_datetime.now(_UTC).replace(microsecond=0))


def _month_start(t: _datetime) -> _datetime:
    return _datetime(t.year, t.month, 1, tzinfo=_UTC)


def _next_month(m: _datetime) -> _datetime:
    return _datetime(m.year + (m.month == 12), m.month % 12 + 1, 1, tzinfo=_UTC)


def _parse_month(month: str) -> _datetime:
    m = _MONTH.fullmatch(month) if isinstance(month, str) else None
    if not m or not 1 <= int(m.group(2)) <= 12:
        raise VaultPreconditionError("month must be 'YYYYMM'")
    return _datetime(int(m.group(1)), int(m.group(2)), 1, tzinfo=_UTC)


def _month_name(m: _datetime) -> str:
    return f"{m.year:04d}{m.month:02d}"


def _locked_file(interval: str) -> str:
    return f"{_LOCKED_DIR}/holdout_{interval}.jsonl"


def _vault_id(market: str, locked_end: _datetime, content_sha256: str) -> str:
    return f"vault_{market}_lock{locked_end.strftime('%Y%m%dT%H%MZ')}_{content_sha256[:12]}"


def _public_file(interval: str) -> str:
    return f"bars_{interval}.jsonl"


def _content_payload(manifest: dict[str, _Any]) -> dict[str, _Any]:
    """The identity payload carried inside a vault manifest (lineage, identifiers and state excluded)."""
    return {k: manifest[k] for k in _PAYLOAD_KEYS}


def _check_kind(kind: str, where: str) -> None:
    if kind not in _PROVENANCE_KINDS:
        raise VaultPreconditionError(f"{where}: unknown provenance {kind!r}")
    if kind in _REFUSED_KINDS:
        raise VaultPreconditionError(f"{where}: provenance {kind!r} is refused before BT-5")


def _create_exclusive(path: _Path, data: bytes) -> bool:
    """Create `path` with exactly `data`, all or nothing, only if it does not exist (temporary file in the same
    directory, fsync, os.link). Returns False when the path already exists. Any other failure creates nothing and
    raises VaultPreconditionError. The temporary file is removed when possible and ignored otherwise."""
    try:
        path.parent.mkdir(exist_ok=True)
        fd, tmp = _tempfile.mkstemp(prefix=".tmp-rec-", dir=path.parent)
    except OSError as exc:
        raise VaultPreconditionError(f"the {path.parent.name} record cannot be prepared ({type(exc).__name__})") \
            from None
    try:
        with _os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            _os.fsync(f.fileno())
        _os.link(tmp, path)
    except FileExistsError:
        return False
    except OSError as exc:
        raise VaultPreconditionError(f"exclusive record creation is unavailable ({type(exc).__name__})") from None
    finally:
        try:
            _os.unlink(tmp)
        except OSError:
            pass
    return True


def _bar_from_record(row: dict[str, _Any]) -> _Bar:
    return _Bar(row["market"], row["interval"], _datetime.fromisoformat(row["start_utc"].replace("Z", "+00:00")),
               _Decimal(row["open"]), _Decimal(row["high"]), _Decimal(row["low"]), _Decimal(row["close"]),
               _Decimal(row["value_krw"]), _Decimal(row["volume"]), row.get("last_tick_ms"))


def _read_locked(path: _Path, expected_sha256: str, expected_bars: int, market: str, interval: str) -> tuple[_Bar, ...]:
    """Read a sealed bar file once into memory, re-check the hash of that buffer, parse the same buffer and check
    that it is exactly the canonical rows of the expected number of bars."""
    data = path.read_bytes()
    if _sha(data) != expected_sha256:
        raise VaultIntegrityError(f"{path.name} does not match its recorded hash")
    try:
        bars = tuple(_bar_from_record(_json.loads(line)) for line in data.decode("utf-8").splitlines())
    except (ValueError, KeyError, TypeError) as exc:
        raise VaultIntegrityError(f"{path.name}: unreadable rows ({type(exc).__name__})") from None
    if _canonical_bar_rows(bars) != data or len(bars) != expected_bars or \
            any(b.market != market or b.interval != interval for b in bars):
        raise VaultIntegrityError(f"{path.name}: rows do not match the recorded content")
    return bars


@_dataclass(frozen=True)
class _LabeledBar:
    label: str  # "HOLDOUT_EVAL" or "EXCLUDED"
    bar: _Bar


# --- build --------------------------------------------------------------------------------------------------------

@_dataclass(frozen=True)
class _Plan:
    vault_id: str
    content_sha256: str
    manifest_sha256: str
    files: dict[str, bytes]  # sealed set: relative path -> exact bytes, including the top-level SHA256SUMS.txt
    provenance: str


def _plan_vault(daily_dir: _Path, hourly_dir: _Path, spec: VaultSpec) -> _Plan:
    if not isinstance(spec, VaultSpec):
        raise VaultPreconditionError("spec must be a VaultSpec")
    dirs = {"day": _Path(daily_dir), "hour": _Path(hourly_dir)}
    src_manifest_bytes: dict[str, bytes] = {}
    for iv, d in dirs.items():  # provenance first, from the input manifest only (no row is read)
        try:
            src_manifest_bytes[iv] = (d / _BARS_MANIFEST_FILE).read_bytes()
            kind_of_input = _json.loads(src_manifest_bytes[iv].decode("utf-8")).get("provenance")
        except (OSError, ValueError, AttributeError) as exc:
            raise VaultPreconditionError(f"{iv} input is not a readable bars/1 directory "
                                         f"({type(exc).__name__})") from None
        _check_kind(kind_of_input, f"{iv} input")
    series: dict[str, _BarSeries] = {}
    for iv, d in dirs.items():  # the whole input is validated before anything is split
        try:
            series[iv] = _load_bars(d)
            same_manifest = (d / _BARS_MANIFEST_FILE).read_bytes() == src_manifest_bytes[iv]
        except (_DataIntegrityError, OSError) as exc:  # the message may quote input rows: keep the type only
            raise VaultPreconditionError(f"{iv} input is not a valid bars/1 directory ({type(exc).__name__})") from None
        if not same_manifest:
            raise VaultPreconditionError(f"{iv} input manifest changed while the vault was being planned")
    for iv, s in series.items():
        if s.interval != iv:
            raise VaultPreconditionError(f"{dirs[iv].name} holds {s.interval} bars, expected {iv}")
    if series["day"].market != series["hour"].market:
        raise VaultPreconditionError("daily and hourly inputs are of different markets")
    kind = series["day"].provenance.kind
    if series["hour"].provenance.kind != kind:
        raise VaultPreconditionError("daily and hourly inputs have different provenance kinds")
    _check_kind(kind, "input")
    if dirs["day"].name == dirs["hour"].name:
        raise VaultPreconditionError("daily and hourly input directories must have different names")
    market = series["day"].market
    c, h, lk = spec.confirmatory_data_end_utc, spec.holdout_end_utc, spec.locked_end_utc

    files: dict[str, bytes] = {}
    intervals: dict[str, dict[str, _Any]] = {}
    lineage: dict[str, dict[str, _Any]] = {}
    for iv in _INTERVALS:
        bars = series[iv].bars
        late = sum(1 for b in bars if b.end_utc > lk)
        if late:
            raise VaultPreconditionError(f"{iv} input has {late} bars ending after locked_end_utc; forward bars "
                                         "enter only through ForwardVault.seal")
        public = [b for b in bars if b.end_utc <= c]
        hold = [b for b in bars if c < b.end_utc <= h]
        excl = [b for b in bars if h < b.end_utc <= lk]
        if not public:
            raise VaultPreconditionError(f"no {iv} bar ends at or before confirmatory_data_end_utc")
        if not hold:
            raise VaultPreconditionError(f"no {iv} bar falls in the historical holdout")
        src_manifest = _json.loads(src_manifest_bytes[iv].decode("utf-8"))
        body = _canonical_bar_rows(public)
        bars_file = _public_file(iv)
        child = {"schema": _BARS_SCHEMA, "evidence": src_manifest.get("evidence", _NOT_EVIDENCE), "provenance": kind,
                 "market": market, "interval": iv, "bars": len(public), "first_start": _utc_iso(public[0].start_utc),
                 "last_start": _utc_iso(public[-1].start_utc), "bars_file": bars_file, "bars_sha256": _sha(body)}
        for key in ("source_pull", "confirmation_rule"):  # copied as is (bars_io reads source_pull for descriptions)
            if key in src_manifest:
                child[key] = src_manifest[key]
        child_bytes = _json_bytes(child)
        name = dirs[iv].name
        files[f"{_PUBLIC_DIR}/{name}/{bars_file}"] = body
        files[f"{_PUBLIC_DIR}/{name}/{_BARS_MANIFEST_FILE}"] = child_bytes
        files[f"{_PUBLIC_DIR}/{name}/{_SUMS_FILE}"] = _sums_bytes({bars_file: body, _BARS_MANIFEST_FILE: child_bytes})
        locked = _canonical_bar_rows(hold + excl)
        if _sha(locked) != _bars_sha256(hold + excl):
            raise VaultIntegrityError("locked rows do not hash to their bar content hash")
        files[_locked_file(iv)] = locked
        # identity payload: exactly the D6 fields (file names follow from the interval and are not identity)
        intervals[iv] = {"public_dir": name, "public_bars_sha256": _sha(body), "public_bars": len(public),
                         "locked_sha256": _sha(locked), "holdout_eval_bars": len(hold), "excluded_bars": len(excl)}
        lineage[iv] = {"input_bars_sha256": series[iv].provenance.bars_sha256, "input_bars": len(bars),
                       "input_bars_manifest_sha256": _sha(src_manifest_bytes[iv])}

    payload = {"schema": _SCHEMA, "market": market, "provenance": kind, "spec": spec.to_dict(), "intervals": intervals}
    content_sha = _sha256_of(payload)
    vid = _vault_id(market, lk, content_sha)
    manifest = {**payload, "lineage": lineage, "evidence": _NOT_EVIDENCE, "vault_content_sha256": content_sha,
                "vault_id": vid}
    manifest_bytes = _json_bytes(manifest)
    files[_VAULT_MANIFEST] = manifest_bytes
    files[_SUMS_FILE] = _sums_bytes(dict(files))
    return _Plan(vid, content_sha, _sha(manifest_bytes), files, kind)


@_dataclass(frozen=True)
class _VaultBuild:
    dir: _Path
    status: str  # CREATED or ALREADY_SEALED_IDENTICAL
    vault_id: str
    content_sha256: str
    manifest_sha256: str
    state: dict[str, _Any]  # vault_status of the vault (counts, hashes and pass/fail only)


def _entries(root: _Path) -> set[str]:
    return {p.relative_to(root).as_posix() for p in root.rglob("*")}


def _expected_entries(names: list[str]) -> set[str]:
    out: set[str] = set()
    for name in names:
        parts = name.split("/")
        out.update("/".join(parts[:i]) for i in range(1, len(parts) + 1))
    return out


def _check_identical_vault(final: _Path, plan: _Plan) -> None:
    """D14: read only; sealed-set bytes and structure must match exactly; state entries are not compared."""
    try:
        top = set(_os.listdir(final))
        if top - set(_SEALED_TOP) - set(_STATE_TOP) or not set(_SEALED_TOP) <= top:
            raise VaultExistsError(f"{final.name} exists with an unexpected top-level structure")
        sealed_dirs = [n for n in plan.files if n.split("/")[0] in (_PUBLIC_DIR, _LOCKED_DIR)]
        found: set[str] = set()
        for d in (_PUBLIC_DIR, _LOCKED_DIR):
            found |= {f"{d}/{e}" for e in _entries(final / d)} | {d}
        if found != _expected_entries(sealed_dirs):
            raise VaultExistsError(f"{final.name} exists with different sealed files")
        if (final / _SUMS_FILE).read_bytes() != plan.files[_SUMS_FILE]:
            raise VaultExistsError(f"{final.name} exists with a different {_SUMS_FILE}")
        for name, data in plan.files.items():
            if (final / name).read_bytes() != data:
                raise VaultExistsError(f"{final.name} exists with different sealed bytes ({name})")
    except OSError as exc:
        raise VaultExistsError(f"{final.name} exists and cannot be compared ({type(exc).__name__})") from None


def _write_tree(tmp: _Path, files: dict[str, bytes]) -> None:
    for name, data in files.items():
        path = tmp / name
        path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write_bytes(path, data)
    for name, data in files.items():
        if _sha256_file(tmp / name) != _sha(data):
            raise VaultIntegrityError(f"written {name} does not match its planned bytes")


def _remove_own_tmp(tmp: _Path) -> None:
    """Remove a temporary directory this call created (bottom up). Leftovers of earlier crashes are not touched."""
    for p in sorted(tmp.rglob("*"), key=lambda q: len(q.parts), reverse=True):
        try:
            p.unlink() if p.is_file() else p.rmdir()
        except OSError:
            pass
    try:
        tmp.rmdir()
    except OSError:
        pass


def _publish(parent: _Path, prefix: str, files: dict[str, bytes], extra: tuple[str, bytes] | None,
             final: _Path) -> None:
    """Write `files` (and an unhashed `extra` state file) into a new temporary directory under `parent`, check
    the sealed bytes, then publish with one rename that never overwrites. A failure removes only this call's
    temporary directory. Filesystem failures surface as VaultPreconditionError (nothing published, nothing
    consumed); a target that appeared meanwhile is VaultExistsError."""
    tmp: _Path | None = None
    try:
        parent.mkdir(parents=True, exist_ok=True)
        tmp = _Path(_tempfile.mkdtemp(prefix=prefix, dir=parent))
        _write_tree(tmp, files)
        if extra is not None:
            _atomic_write_bytes(tmp / extra[0], extra[1])
        _os.rename(tmp, final)  # never overwrites
    except BaseException as exc:
        if tmp is not None:
            _remove_own_tmp(tmp)
        if isinstance(exc, FileExistsError):
            raise VaultExistsError(f"{final.name} appeared while it was being written; nothing was published") \
                from None
        if isinstance(exc, OSError):
            raise VaultPreconditionError(f"{final.name} could not be written ({type(exc).__name__}); nothing was "
                                         "published") from None
        raise


def build_vault(daily_dir: _Path, hourly_dir: _Path, spec: VaultSpec, out_root: _Path, *,
                code_state: dict[str, _Any] | None = None) -> _VaultBuild:
    """Build and seal <out_root>/<vault_id>/ (temporary directory, then one rename). An existing directory is
    accepted only when its sealed set is byte-identical (D14); then nothing is written and its state is kept."""
    out_root = _Path(out_root)
    plan = _plan_vault(daily_dir, hourly_dir, spec)
    if not out_root.name.endswith(_FIXTURE_ROOT_SUFFIX):
        raise VaultPreconditionError(f"fixture/synthetic vaults must go under a '*{_FIXTURE_ROOT_SUFFIX}' root")
    final = out_root / plan.vault_id
    if final.exists():
        _check_identical_vault(final, plan)
        return _VaultBuild(final, ALREADY_SEALED_IDENTICAL, plan.vault_id, plan.content_sha256, plan.manifest_sha256,
                          vault_status(final))
    record = {"schema": _BUILD_SCHEMA, "vault_id": plan.vault_id, "python": _platform.python_version(),
              "code_state": code_state, "built_at_utc": _now(), "evidence": _NOT_EVIDENCE}
    try:
        record_bytes = _json_bytes(record)
    except (TypeError, ValueError) as exc:
        raise VaultPreconditionError(f"code_state is not JSON-serializable ({type(exc).__name__})") from None
    _publish(out_root, ".tmp-vault-", plan.files, (_BUILD_RECORD, record_bytes), final)
    return _VaultBuild(final, CREATED, plan.vault_id, plan.content_sha256, plan.manifest_sha256, vault_status(final))


# --- reading and checking ---------------------------------------------------------------------------------------

@_dataclass(frozen=True)
class _View:
    dir: _Path
    manifest: dict[str, _Any]
    spec: VaultSpec
    sums: dict[str, str]


def _sealed_names(manifest: dict[str, _Any]) -> set[str]:
    names = {_VAULT_MANIFEST}
    for iv, rec in manifest["intervals"].items():
        base = f"{_PUBLIC_DIR}/{rec['public_dir']}"
        names |= {f"{base}/{_public_file(iv)}", f"{base}/{_BARS_MANIFEST_FILE}", f"{base}/{_SUMS_FILE}",
                  _locked_file(iv)}
    return names


def _load(vault_dir: _Path) -> _View:
    """Check the sealed set: manifest identity, SHA256SUMS listing and every file hash (hash only, nothing parsed
    from the locked files). Raises VaultIntegrityError or, for a refused provenance, VaultPreconditionError."""
    d = _Path(vault_dir)
    try:
        manifest = _json.loads((d / _VAULT_MANIFEST).read_bytes().decode("utf-8"))
        sums = _parse_sums((d / _SUMS_FILE).read_bytes(), d.name)
    except VaultError:
        raise
    except (OSError, ValueError) as exc:
        raise VaultIntegrityError(f"{d.name}: cannot read {_VAULT_MANIFEST} / {_SUMS_FILE} "
                                  f"({type(exc).__name__})") from None
    try:
        if manifest.get("schema") != _SCHEMA:
            raise VaultIntegrityError(f"{d.name}: not a {_SCHEMA} vault")
        _check_kind(manifest["provenance"], d.name)
        if set(sums) != _sealed_names(manifest) or set(manifest["intervals"]) != set(_INTERVALS):
            raise VaultIntegrityError(f"{d.name}: {_SUMS_FILE} does not list exactly the sealed files")
        for name, digest in sums.items():
            try:
                actual = _sha256_file(d / name)
            except OSError:
                raise VaultIntegrityError(f"{d.name}: cannot read {name}") from None
            if actual != digest:
                raise VaultIntegrityError(f"{d.name}: {name} does not match {_SUMS_FILE}")
        content_sha = _sha256_of(_content_payload(manifest))
        spec = VaultSpec.from_dict(manifest["spec"])
        if content_sha != manifest["vault_content_sha256"] or \
                manifest["vault_id"] != _vault_id(manifest["market"], spec.locked_end_utc, content_sha):
            raise VaultIntegrityError(f"{d.name}: manifest identity does not match its content")
        for iv, rec in manifest["intervals"].items():
            pub = f"{_PUBLIC_DIR}/{rec['public_dir']}/{_public_file(iv)}"
            if sums[pub] != rec["public_bars_sha256"] or sums[_locked_file(iv)] != rec["locked_sha256"]:
                raise VaultIntegrityError(f"{d.name}: file hashes do not match the manifest")
    except VaultError:
        raise
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise VaultIntegrityError(f"{d.name}: malformed vault manifest ({type(exc).__name__})") from None
    return _View(d, manifest, spec, sums)


def _record_state(path: _Path, kind: str, content_sha256: str | None) -> str:
    if not path.exists():
        return UNOPENED
    try:  # exact D7 key set and bindings; anything else, or an unknown vault identity, is RECORD_UNREADABLE
        doc = _json.loads(path.read_bytes().decode("utf-8"))
        ok = isinstance(doc, dict) and set(doc) == set(_ACCESS_KEYS) and doc["kind"] == kind and \
            content_sha256 is not None and doc["vault_content_sha256"] == content_sha256
    except (OSError, ValueError, KeyError, TypeError):
        ok = False
    return OPENED if ok else RECORD_UNREADABLE


def _record_present(path: _Path) -> bool:
    return path.exists() or path.is_symlink()


def _evidence_doc(view: _View, kind: str) -> dict[str, _Any]:
    """A recorded evidence reference, checked for format and binding (not for truth)."""
    path = view.dir / _EVIDENCE_DIR / f"{kind}.json"
    if not path.exists():
        raise VaultPreconditionError(f"evidence {kind} is not recorded")
    try:
        doc = _json.loads(path.read_bytes().decode("utf-8"))
        ok = doc["schema"] == _EVIDENCE_SCHEMA and doc["kind"] == kind and _HEX64.fullmatch(doc["sha256"]) and \
            doc["vault_content_sha256"] == view.manifest["vault_content_sha256"] and \
            (doc["detail"] is None if kind != "row9_strategy" else _valid_ids(doc["detail"]))
    except (OSError, ValueError, KeyError, TypeError):
        ok = False
    if not ok:
        raise VaultPreconditionError(f"evidence {kind} is unreadable or malformed")
    return doc


def _valid_ids(detail: _Any) -> bool:
    return isinstance(detail, (list, tuple)) and len(detail) > 0 and \
        all(isinstance(x, str) and x for x in detail)


def _check_hashes(view: _View, preregistration_sha256: str, config_sha256: str) -> None:
    _require_hex(preregistration_sha256, "preregistration_sha256")
    _require_hex(config_sha256, "config_sha256")
    if (preregistration_sha256, config_sha256) != (view.spec.preregistration_sha256, view.spec.config_sha256):
        raise VaultPreconditionError("preregistration/config hash differs from the one the vault was sealed with")


def _access_doc(view: _View, kind: str, preregistration_sha256: str, config_sha256: str, evidence: dict[str, str],
                files: dict[str, str], caller: str) -> bytes:
    values = (kind, view.manifest["vault_content_sha256"], preregistration_sha256, config_sha256, evidence, files,
              _now(), str(caller))
    return _json_bytes(dict(zip(_ACCESS_KEYS, values, strict=True)))  # exactly the D7 keys, nothing else


def _commit_access(view: _View, kind: str, data: bytes) -> None:
    if not _create_exclusive(view.dir / _ACCESS_DIR / f"{kind}.json", data):
        raise VaultLockedError(f"{kind} of {view.manifest['vault_id']} was already used; it is single-use")


def _read_holdout(view: _View) -> dict[str, tuple[_LabeledBar, ...]]:
    h = view.spec.holdout_end_utc
    out: dict[str, tuple[_LabeledBar, ...]] = {}
    for iv in _INTERVALS:
        rec = view.manifest["intervals"][iv]
        bars = _read_locked(view.dir / _locked_file(iv), rec["locked_sha256"],
                            rec["holdout_eval_bars"] + rec["excluded_bars"], view.manifest["market"], iv)
        labeled = tuple(_LabeledBar(_HOLDOUT_EVAL if b.end_utc <= h else _EXCLUDED, b) for b in bars)
        if sum(1 for x in labeled if x.label == _HOLDOUT_EVAL) != rec["holdout_eval_bars"]:
            raise VaultIntegrityError(f"{iv} locked rows do not match the recorded holdout count")
        out[iv] = labeled
    return out


def _after_record(fn, *args):
    """Run a read that follows an access record: every failure consumes the use (the record stays)."""
    try:
        return fn(*args)
    except VaultError:
        raise
    except Exception as exc:  # noqa: BLE001 - reported as an integrity failure, the use is consumed
        raise VaultIntegrityError(f"read failed after the access record ({type(exc).__name__}); "
                                  "the single use is consumed") from None


# --- evidence -------------------------------------------------------------------------------------------------------

def record_evidence(vault_dir: _Path, kind: str, sha256: str, *, detail: list[str] | None = None) -> str:
    """Record an evidence reference once (D8). Same content again: ALREADY_RECORDED_IDENTICAL, nothing written;
    different content: VaultExistsError. Only presence, format and binding to the vault are checked."""
    if kind not in _EVIDENCE_KINDS:
        raise VaultPreconditionError(f"unknown evidence kind {kind!r}")
    _require_hex(sha256, "sha256")
    if kind == "row9_strategy":
        if not _valid_ids(detail):
            raise VaultPreconditionError("row9_strategy needs a non-empty list of strategy ids")
        detail = list(detail)
    elif detail is not None:
        raise VaultPreconditionError(f"evidence {kind} takes no detail")
    view = _load(vault_dir)
    data = _json_bytes({"schema": _EVIDENCE_SCHEMA, "kind": kind, "sha256": sha256, "detail": detail,
                        "vault_content_sha256": view.manifest["vault_content_sha256"],
                        "evidence_label": _NOT_EVIDENCE})
    path = view.dir / _EVIDENCE_DIR / f"{kind}.json"
    if _create_exclusive(path, data):
        return RECORDED
    try:
        same = path.read_bytes() == data
    except OSError:
        same = False
    if same:
        return ALREADY_RECORDED_IDENTICAL
    raise VaultExistsError(f"evidence {kind} is already recorded with different content")


# --- holdout --------------------------------------------------------------------------------------------------------

@_dataclass(frozen=True)
class _HoldoutOpening:
    vault_id: str
    rows: dict[str, tuple[_LabeledBar, ...]]  # interval -> "HOLDOUT_EVAL" and "EXCLUDED" bars, in start order


class HistoricalHoldoutVault:
    """The only reader of the locked holdout (draft 19.2). One use per vault."""

    def __init__(self, vault_dir: _Path):
        self.vault_dir = _Path(vault_dir)

    def open_once(self, *, preregistration_sha256: str, config_sha256: str, caller: str = "") -> _HoldoutOpening:
        view = _load(self.vault_dir)  # 1-2: sealed set, provenance, every hash (locked files hashed, not parsed)
        record = view.dir / _ACCESS_DIR / f"{_HOLDOUT_OPEN}.json"
        if _record_present(record):  # 3
            raise VaultLockedError(f"the holdout of {view.manifest['vault_id']} was already opened; it is single-use")
        _check_hashes(view, preregistration_sha256, config_sha256)  # 4
        evidence = {k: _evidence_doc(view, k)["sha256"] for k in _EVIDENCE_KINDS}  # 5
        files = {_locked_file(iv): view.manifest["intervals"][iv]["locked_sha256"]
                 for iv in _INTERVALS}  # 6 (checked by _load)
        _commit_access(view, _HOLDOUT_OPEN, _access_doc(view, _HOLDOUT_OPEN, preregistration_sha256, config_sha256,
                                                       evidence, files, caller))
        rows = _after_record(_read_holdout, view)
        return _HoldoutOpening(view.manifest["vault_id"], rows)


# --- forward --------------------------------------------------------------------------------------------------------

@_dataclass(frozen=True)
class _ForwardSeal:
    dir: _Path
    status: str  # CREATED or ALREADY_SEALED_IDENTICAL
    month: str
    content_sha256: str
    bars: dict[str, int]  # interval -> sealed bars
    outside_window: dict[str, int]  # interval -> input bars outside the month window (not sealed)
    sha256: dict[str, str]  # interval -> sealed file hash


@_dataclass(frozen=True)
class _ForwardAnalysis:
    kind: str
    vault_id: str
    analysis_end_utc: _datetime
    lookback: dict[str, tuple[_LabeledBar, ...]]  # the locked holdout rows ("HOLDOUT_EVAL" and "EXCLUDED")
    forward: dict[str, tuple[_Bar, ...]]  # L < end_utc <= analysis_end_utc, in start order


def _forward_file(interval: str) -> str:
    return f"forward_{interval}.jsonl"


def _seal_payload(seal: dict[str, _Any]) -> dict[str, _Any]:
    """The D6 forward identity payload: month, vault_content_sha256, per interval sha256 and bar count."""
    return {"month": seal["month"], "vault_content_sha256": seal["vault_content_sha256"],
            "intervals": {iv: {"sha256": seal["intervals"][iv]["sha256"], "bars": seal["intervals"][iv]["bars"]}
                          for iv in _INTERVALS}}


def _load_seal(view: _View, month: _datetime) -> dict[str, _Any]:
    """Check one sealed forward month (structure, hashes, identity, binding). Missing: VaultPreconditionError."""
    name = f"forward_{_month_name(month)}"
    d = view.dir / _FORWARD_DIR / name
    if not d.is_dir():
        raise VaultPreconditionError(f"forward month {_month_name(month)} is not sealed")
    expected = {_forward_file(iv) for iv in _INTERVALS} | {_SEAL_FILE, _SUMS_FILE}
    try:
        if set(_os.listdir(d)) != expected:
            raise VaultIntegrityError(f"{name}: unexpected files")
        sums = _parse_sums((d / _SUMS_FILE).read_bytes(), name)
        if set(sums) != expected - {_SUMS_FILE}:
            raise VaultIntegrityError(f"{name}: {_SUMS_FILE} does not list exactly the sealed files")
        for n, digest in sums.items():
            if _sha256_file(d / n) != digest:
                raise VaultIntegrityError(f"{name}: {n} does not match {_SUMS_FILE}")
        seal = _json.loads((d / _SEAL_FILE).read_bytes().decode("utf-8"))
        if seal["schema"] != _SEAL_SCHEMA or seal["month"] != _month_name(month) or \
                seal["vault_content_sha256"] != view.manifest["vault_content_sha256"] or \
                _sha256_of(_seal_payload(seal)) != seal["forward_seal_content_sha256"] or \
                any(sums[_forward_file(iv)] != seal["intervals"][iv]["sha256"] for iv in _INTERVALS):
            raise VaultIntegrityError(f"{name}: seal identity does not match its content")
    except VaultError:
        raise
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise VaultIntegrityError(f"{name}: unreadable seal ({type(exc).__name__})") from None
    return seal


class ForwardVault:
    """Monthly forward seals and the two single-use forward analyses (draft 19.3). The monthly risk-limit check
    is deferred to a later task; no method returns forward rows for it."""

    def __init__(self, vault_dir: _Path):
        self.vault_dir = _Path(vault_dir)

    def seal(self, day_series: _BarSeries, hour_series: _BarSeries, month: str) -> _ForwardSeal:
        view = _load(self.vault_dir)
        m = _parse_month(month)
        lk = view.spec.locked_end_utc
        if m < _month_start(lk):
            raise VaultPreconditionError("month is before the month of locked_end_utc")
        series = {"day": day_series, "hour": hour_series}
        for iv, s in series.items():
            if not isinstance(s, _BarSeries) or s.interval != iv:
                raise VaultPreconditionError(f"{iv} input must be a BarSeries of {iv} bars")
            if s.market != view.manifest["market"]:
                raise VaultPreconditionError(f"{iv} input is of another market")
            _check_kind(s.provenance.kind, f"{iv} input")
            try:
                s.verify()
            except _DataIntegrityError as exc:
                raise VaultPreconditionError(f"{iv} input does not match its provenance hash "
                                             f"({type(exc).__name__})") from None
        if day_series.provenance.kind != hour_series.provenance.kind:
            raise VaultPreconditionError("daily and hourly inputs have different provenance kinds")
        lo, hi = max(m, lk), _next_month(m)
        files: dict[str, bytes] = {}
        intervals: dict[str, dict[str, _Any]] = {}
        lineage: dict[str, dict[str, _Any]] = {}
        for iv, s in series.items():
            if not any(b.end_utc >= hi for b in s.bars):
                raise VaultPreconditionError(f"month {_month_name(m)} has not ended in the {iv} input")
            window = [b for b in s.bars if lo < b.end_utc <= hi]
            if not window:
                raise VaultPreconditionError(f"no {iv} bar falls in the window of month {_month_name(m)}")
            body = _canonical_bar_rows(window)
            files[_forward_file(iv)] = body
            intervals[iv] = {"sha256": _sha(body), "bars": len(window)}
            lineage[iv] = {"input_bars_sha256": s.provenance.bars_sha256, "input_bars": len(s),
                           "outside_window_bars": len(s) - len(window), "input_provenance": s.provenance.kind}
        payload = {"month": _month_name(m), "vault_content_sha256": view.manifest["vault_content_sha256"],
                   "intervals": intervals}  # exactly the D6 forward identity fields
        seal_sha = _sha256_of(payload)
        files[_SEAL_FILE] = _json_bytes({"schema": _SEAL_SCHEMA, **payload, "lineage": lineage,
                                        "evidence": _NOT_EVIDENCE, "forward_seal_content_sha256": seal_sha})
        files[_SUMS_FILE] = _sums_bytes(dict(files))
        result = dict(month=_month_name(m), content_sha256=seal_sha,
                      bars={iv: intervals[iv]["bars"] for iv in _INTERVALS},
                      outside_window={iv: lineage[iv]["outside_window_bars"] for iv in _INTERVALS},
                      sha256={iv: intervals[iv]["sha256"] for iv in _INTERVALS})
        parent = view.dir / _FORWARD_DIR
        final = parent / f"forward_{_month_name(m)}"
        if final.exists():
            try:
                same = final.is_dir() and set(_os.listdir(final)) == set(files) and \
                    all((final / n).is_file() and (final / n).read_bytes() == data for n, data in files.items())
            except OSError:
                same = False
            if not same:
                raise VaultExistsError(f"forward month {_month_name(m)} is already sealed with different content")
            return _ForwardSeal(final, ALREADY_SEALED_IDENTICAL, **result)
        _publish(parent, ".tmp-fwd-", files, None, final)
        return _ForwardSeal(final, CREATED, **result)

    def open_analysis(self, kind: str, *, preregistration_sha256: str, config_sha256: str,
                      caller: str = "") -> _ForwardAnalysis:
        if kind not in _ANALYSIS_KINDS:
            raise VaultPreconditionError(f"unknown analysis kind {kind!r}")
        view = _load(self.vault_dir)
        w_end = view.spec.analysis_end(kind)
        if w_end is None:
            raise VaultPreconditionError(f"the {kind} analysis has no end boundary in the vault spec")
        if not _record_present(view.dir / _ACCESS_DIR / f"{_HOLDOUT_OPEN}.json"):
            raise VaultPreconditionError("the historical holdout must be opened before a forward analysis")
        access = f"forward_{kind}"
        if _record_present(view.dir / _ACCESS_DIR / f"{access}.json"):
            raise VaultLockedError(f"the {kind} analysis of {view.manifest['vault_id']} was already opened")
        _check_hashes(view, preregistration_sha256, config_sha256)
        months: list[_datetime] = []
        m, last = _month_start(view.spec.locked_end_utc), _month_start(w_end - _timedelta(seconds=1))
        while m <= last:
            months.append(m)
            m = _next_month(m)
        seals = {mm: _load_seal(view, mm) for mm in months}
        files = {_locked_file(iv): view.manifest["intervals"][iv]["locked_sha256"]
                 for iv in _INTERVALS}
        for mm, seal in seals.items():
            for iv in _INTERVALS:
                files[f"{_FORWARD_DIR}/forward_{_month_name(mm)}/{_forward_file(iv)}"] = seal["intervals"][iv]["sha256"]
        _commit_access(view, access, _access_doc(view, access, preregistration_sha256, config_sha256, {},
                                                 files, caller))
        return _after_record(self._read, view, kind, w_end, seals)

    @staticmethod
    def _read(view: _View, kind: str, w_end: _datetime, seals: dict[_datetime, dict[str, _Any]]) -> _ForwardAnalysis:
        lookback = _read_holdout(view)
        lk = view.spec.locked_end_utc
        forward: dict[str, tuple[_Bar, ...]] = {}
        for iv in _INTERVALS:
            rows: list[_Bar] = []
            for mm, seal in sorted(seals.items()):
                rec = seal["intervals"][iv]
                path = view.dir / _FORWARD_DIR / f"forward_{_month_name(mm)}" / _forward_file(iv)
                rows.extend(_read_locked(path, rec["sha256"], rec["bars"], view.manifest["market"], iv))
            forward[iv] = tuple(b for b in rows if lk < b.end_utc <= w_end)
        return _ForwardAnalysis(kind, view.manifest["vault_id"], w_end, lookback, forward)


# --- status -----------------------------------------------------------------------------------------------------

def vault_status(vault_dir: _Path) -> dict[str, _Any]:
    """Exactly the D16 categories: id, content SHA, provenance, spec values, public counts, per interval
    holdout_eval / excluded counts and locked file SHA, integrity PASS/FAIL (sealed set and every sealed month),
    access state, evidence presence (RECORDED / ABSENT; validity is checked only when opening), sealed month list
    with per-month counts (None for a month that fails integrity). No locked prices, returns or bar times."""
    d = _Path(vault_dir)
    ok = True
    try:
        view: _View | None = _load(d)
        manifest = view.manifest
    except VaultError:
        ok, view = False, None
        try:
            manifest = _json.loads((d / _VAULT_MANIFEST).read_bytes().decode("utf-8"))
        except (OSError, ValueError):
            manifest = {}
        if not isinstance(manifest, dict):
            manifest = {}
    content = manifest.get("vault_content_sha256")
    ivs = manifest.get("intervals") if isinstance(manifest.get("intervals"), dict) else {}
    months: dict[str, dict[str, int | None]] = {}
    try:
        entries = sorted((d / _FORWARD_DIR).iterdir()) if (d / _FORWARD_DIR).is_dir() else []
    except OSError:
        ok, entries = False, []
    for p in entries:
        mt = _FORWARD_NAME.fullmatch(p.name)
        if not mt:
            continue  # temporary directories and anything else are not seals
        counts: dict[str, int | None] = {iv: None for iv in _INTERVALS}
        try:
            if view is None:
                raise VaultIntegrityError("vault integrity failed")
            seal = _load_seal(view, _parse_month(mt.group(1)))
            counts = {iv: seal["intervals"][iv]["bars"] for iv in _INTERVALS}
        except VaultError:
            ok = False
        months[mt.group(1)] = counts
    return {
        "vault_id": manifest.get("vault_id"),
        "vault_content_sha256": content,
        "provenance": manifest.get("provenance"),
        "spec": manifest.get("spec"),
        "public_bars": {iv: rec.get("public_bars") for iv, rec in ivs.items() if isinstance(rec, dict)},
        "locked": {iv: {"holdout_eval_bars": rec.get("holdout_eval_bars"), "excluded_bars": rec.get("excluded_bars"),
                        "sha256": rec.get("locked_sha256")} for iv, rec in ivs.items() if isinstance(rec, dict)},
        "integrity": PASS if ok else FAIL,
        "access": {k: _record_state(d / _ACCESS_DIR / f"{k}.json", k, content)
                   for k in (_HOLDOUT_OPEN, "forward_interim", "forward_final")},
        "evidence_records": {k: RECORDED if (d / _EVIDENCE_DIR / f"{k}.json").exists() else ABSENT
                             for k in _EVIDENCE_KINDS},
        "forward_months": months,
    }
