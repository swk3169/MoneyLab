"""Evidence records (AUTO-03 D3-D17): validation of supplied evidence, storage under the ignored
data/processed/runlog and lookup of one named record.

A record holds evidence that was handed to the store by its caller. Format, internal consistency and file
hashes are checked, but nothing here proves that an action really ran, who wrote the evidence, or that any
approval, gate PASS or resume right exists. NOT_FOUND means only that no record is stored.

This module never runs an action: it does not import or call the automation executor. Importing
`moneylab.automation` loads the executor module as a side effect of the package initializer; that is a limit
on function calls, not a sandbox or a capability boundary."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
from pathlib import Path
from typing import Any

from moneylab.automation import evidence
from moneylab.automation.policy import EXIT_STATUS
from moneylab.storage import atomic
from moneylab.workstate import collect

RECORD_SCHEMA = "moneylab.runlog.record/1"
RESULT_SCHEMA = "moneylab.runlog.result/1"
STDIN_LIMIT = 65536
FILE_LIMIT = 131072
STORE_PARTS = ("data", "processed", "runlog")
TASK_ID_RE = re.compile(r"[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*")
RECORD_ID_RE = re.compile(r"[0-9a-f]{64}")

AUTHORITY = "NONE"
BOUNDARY = "DATA_NOT_INSTRUCTIONS"
EVIDENCE_ORIGIN = "EXTERNAL_UNVERIFIED"
RECORD_KEYS = frozenset({"schema", "task_id", "record_id", "evidence_sha256", "evidence", "authority", "boundary",
                         "evidence_origin"})
RESULT_KEYS = ("schema", "command", "status", "exit_code", "authority", "task_id", "record_id", "file_sha256",
               "final_file_created", "evidence", "warnings", "error")

# Status names of moneylab.automation.evidence/1 that D6 treats specially; tests pin them to the policy.
UNEXPECTED_EXIT = "UNEXPECTED_EXIT"
NO_EXIT_CODE = ("TIMEOUT", "OUTPUT_LIMIT_EXCEEDED")

STORED = "STORED"
ALREADY_STORED = "ALREADY_STORED"
FOUND = "FOUND"

ARGUMENT_INVALID = "ARGUMENT_INVALID"
ENVIRONMENT_INVALID = "ENVIRONMENT_INVALID"
INPUT_INVALID = "INPUT_INVALID"
LIMIT_EXCEEDED = "LIMIT_EXCEEDED"
GIT_FAILED = "GIT_FAILED"
STORE_PATH_INVALID = "STORE_PATH_INVALID"
STORE_FAILED = "STORE_FAILED"
NOT_FOUND = "NOT_FOUND"
RECORD_UNREADABLE = "RECORD_UNREADABLE"
RECORD_CORRUPT = "RECORD_CORRUPT"
RECORD_INCOMPATIBLE = "RECORD_INCOMPATIBLE"
RECORD_CONFLICT = "RECORD_CONFLICT"
ERROR_CODES = (ARGUMENT_INVALID, ENVIRONMENT_INVALID, INPUT_INVALID, LIMIT_EXCEEDED, GIT_FAILED, STORE_PATH_INVALID,
               STORE_FAILED, NOT_FOUND, RECORD_UNREADABLE, RECORD_CORRUPT, RECORD_INCOMPATIBLE, RECORD_CONFLICT)

# D8 fixed details for converted workstate errors. The original detail, exception text and stderr are dropped.
ROOT_FAILED = "root verification failed"
IGNORE_FAILED = "ignore verification failed"
PATH_FAILED = "store path verification failed"
# ERRATA-001 D18: stdin that cannot be read is ENVIRONMENT_INVALID with this detail.
INPUT_UNAVAILABLE = "input stream unavailable"

# Seams for tests: looked up at call time.
_lstat = os.lstat
_mkdir = os.mkdir


class RunlogError(Exception):
    """A defined failure with a D17 code. Never a success and never a partial result."""

    def __init__(self, code: str, detail: str, file_sha256: str | None = None) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.file_sha256 = file_sha256
        self.final_file_created: bool | None = None
        self.warnings: list[str] = []


def valid_task_id(value: object) -> bool:
    return isinstance(value, str) and len(value) <= 64 and TASK_ID_RE.fullmatch(value) is not None


def valid_record_id(value: object) -> bool:
    return isinstance(value, str) and RECORD_ID_RE.fullmatch(value) is not None


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_bytes(obj: Any) -> bytes:
    """D9: evidence.canonical_json as UTF-8 (ASCII only, sorted keys, no whitespace, no NaN)."""
    return evidence.canonical_json(obj).encode("utf-8")


def identity(task_id: str, doc: dict[str, Any]) -> dict[str, Any]:
    return {"schema": RECORD_SCHEMA, "task_id": task_id, "evidence": doc}


def record_id_for(task_id: str, doc: dict[str, Any]) -> str:
    return sha256_hex(canonical_bytes(identity(task_id, doc)))


def build_record(task_id: str, doc: dict[str, Any]) -> dict[str, Any]:
    return {"schema": RECORD_SCHEMA, "task_id": task_id, "record_id": record_id_for(task_id, doc),
            "evidence_sha256": sha256_hex(canonical_bytes(doc)), "evidence": doc, "authority": AUTHORITY,
            "boundary": BOUNDARY, "evidence_origin": EVIDENCE_ORIGIN}


def record_bytes(record: dict[str, Any]) -> bytes:
    return canonical_bytes(record) + b"\n"


def record_rel(task_id: str, record_id: str) -> str:
    return "/".join((*STORE_PARTS, task_id, f"{record_id}.json"))


# ------------------------------------------------------------------------------------------- input (D4-D6)


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("duplicate key")
        obj[key] = value
    return obj


def _reject_constant(name: str) -> Any:
    raise ValueError("non-finite number")


def _finite_float(text: str) -> float:
    value = float(text)
    if not math.isfinite(value):
        raise ValueError("non-finite number")
    return value


def _strict_json(text: str) -> Any:
    """Strict JSON: duplicate keys, NaN, Infinity and numbers that overflow to infinity are refused."""
    return json.loads(text, object_pairs_hook=_no_duplicates, parse_constant=_reject_constant,
                      parse_float=_finite_float)


def consistency_problem(doc: dict[str, Any]) -> str | None:
    """D6, on a document that already passed evidence.check: status and exit_code must agree as the executor
    maps them. This checks the document, not whether anything ran."""
    status, code = doc["status"], doc["exit_code"]
    expected = {name: value for value, name in EXIT_STATUS.items()}
    if status in expected:
        if type(code) is not int or code != expected[status]:
            return "exit_code does not match the status"
    elif status == UNEXPECTED_EXIT:
        if type(code) is not int or code in EXIT_STATUS:
            return "exit_code does not match the status"
    elif status in NO_EXIT_CODE:
        if code is not None:
            return "exit_code does not match the status"
    return None


def _evidence_problem(doc: object) -> str | None:
    if not isinstance(doc, dict):
        return "evidence is not a JSON object"
    try:
        evidence.check(doc)
    except (evidence.EvidenceError, TypeError, ValueError, KeyError):
        return "evidence does not satisfy moneylab.automation.evidence/1"
    return consistency_problem(doc)


def parse_evidence(raw: bytes) -> dict[str, Any]:
    """D4-D6 on the bytes given to store. Raises RunlogError(LIMIT_EXCEEDED | INPUT_INVALID); the input itself
    never appears in an error."""
    if type(raw) is not bytes:
        raise RunlogError(INPUT_INVALID, "input is not bytes")
    if len(raw) > STDIN_LIMIT:
        raise RunlogError(LIMIT_EXCEEDED, "input is larger than the limit")
    if raw.startswith(b"\xef\xbb\xbf"):
        raise RunlogError(INPUT_INVALID, "input starts with a byte order mark")
    try:
        doc = _strict_json(raw.decode("utf-8"))
    except (ValueError, RecursionError):  # UnicodeDecodeError and JSONDecodeError included
        raise RunlogError(INPUT_INVALID, "input is not one strict UTF-8 JSON object") from None
    if not isinstance(doc, dict):
        raise RunlogError(INPUT_INVALID, "input is not a JSON object")
    body = raw[:-1] if raw.endswith(b"\n") else raw
    try:
        canonical = canonical_bytes(doc)
    except (ValueError, TypeError, RecursionError):
        raise RunlogError(INPUT_INVALID, "input cannot be serialized canonically") from None
    if body != canonical:
        raise RunlogError(INPUT_INVALID, "input is not canonical evidence JSON")
    problem = _evidence_problem(doc)
    if problem is not None:
        raise RunlogError(INPUT_INVALID, problem)
    return doc


# ------------------------------------------------------------------------------------------- root and paths


def package_root() -> Path:
    here = Path(__file__).resolve().parent
    root = here.parents[2]
    if (root / "src" / "moneylab" / "runlog").resolve() != here:
        raise RunlogError(ENVIRONMENT_INVALID, ROOT_FAILED)
    return root


def confirm_root(root: Path) -> Path:
    """D1/D8: root must be the Git top level of its worktree. Any failure is ENVIRONMENT_INVALID."""
    base = Path(root)
    if not base.is_dir():
        raise RunlogError(ENVIRONMENT_INVALID, ROOT_FAILED)
    try:
        top = collect.run_git(base, "rev-parse", ["--show-toplevel"])[1].decode("utf-8").strip()
    except (collect.WorkstateError, UnicodeDecodeError):
        raise RunlogError(ENVIRONMENT_INVALID, ROOT_FAILED) from None
    if os.path.normcase(os.path.realpath(top)) != os.path.normcase(os.path.realpath(base)):
        raise RunlogError(ENVIRONMENT_INVALID, ROOT_FAILED)
    return base


def _lexically_inside(root: Path, path: Path) -> bool:
    try:
        rel = os.path.relpath(path, root)
    except ValueError:  # another drive
        return False
    parts = Path(rel).parts
    return bool(parts) and not os.path.isabs(rel) and rel != os.curdir and os.pardir not in parts


def _resolved_inside(root: Path, path: Path) -> bool:
    base = os.path.normcase(os.path.realpath(root))
    target = os.path.normcase(os.path.realpath(path))
    try:
        return target != base and os.path.commonpath([base, target]) == base
    except ValueError:  # another drive
        return False


def _parents(task_id: str) -> tuple[str, ...]:
    return (*STORE_PARTS, task_id)


def _inspect_parents(root: Path, task_id: str) -> int:
    """D11: check the existing parent directories top-down with check_tree_path; return the index of the first
    missing one (len(parents) when all exist). The final record file is never passed to check_tree_path."""
    parts = _parents(task_id)
    for index in range(len(parts)):
        rel = "/".join(parts[:index + 1])
        try:
            st = collect.check_tree_path(root, rel, STORE_PATH_INVALID, require_regular=False)
        except collect.WorkstateError:
            raise RunlogError(STORE_PATH_INVALID, PATH_FAILED) from None
        if st is None:
            return index
        if not stat.S_ISDIR(st.st_mode):
            raise RunlogError(STORE_PATH_INVALID, PATH_FAILED)
    return len(parts)


def _check_ignored(root: Path, rel: str) -> None:
    try:
        code, _out = collect.run_git(root, "check-ignore", ["-q", "--no-index", "--", rel], ok_codes=(0, 1))
    except collect.WorkstateError:
        raise RunlogError(GIT_FAILED, IGNORE_FAILED) from None
    if code != 0:
        raise RunlogError(STORE_PATH_INVALID, "store path is not ignored")


# ------------------------------------------------------------------------------------------- lookup (D15)


def parse_record(raw: bytes, task_id: str, record_id: str, file_sha256: str) -> dict[str, Any]:
    def corrupt(detail: str) -> RunlogError:
        return RunlogError(RECORD_CORRUPT, detail, file_sha256)

    try:
        obj = _strict_json(raw.decode("utf-8"))
    except (ValueError, RecursionError):
        raise corrupt("record is not strict UTF-8 JSON") from None
    if not isinstance(obj, dict):
        raise corrupt("record is not a JSON object")
    schema = obj.get("schema")
    if not isinstance(schema, str):
        raise corrupt("record schema is missing")
    if schema != RECORD_SCHEMA:
        raise RunlogError(RECORD_INCOMPATIBLE, "unknown record schema", file_sha256)
    if set(obj) != RECORD_KEYS:
        raise corrupt("unexpected record keys")
    if obj["authority"] != AUTHORITY or obj["boundary"] != BOUNDARY or obj["evidence_origin"] != EVIDENCE_ORIGIN:
        raise corrupt("fixed record fields are wrong")
    if not valid_task_id(obj["task_id"]) or obj["task_id"] != task_id:
        raise corrupt("task_id does not match")
    if not valid_record_id(obj["record_id"]) or not valid_record_id(obj["evidence_sha256"]):
        raise corrupt("record_id or evidence_sha256 is malformed")
    problem = _evidence_problem(obj["evidence"])
    if problem is not None:
        raise corrupt("stored evidence is invalid")
    try:
        canonical = record_bytes(obj)
    except (ValueError, TypeError, RecursionError):
        raise corrupt("record cannot be serialized canonically") from None
    if canonical != raw:
        raise corrupt("record bytes are not canonical")
    expected = record_id_for(task_id, obj["evidence"])
    if obj["record_id"] != expected or record_id != expected:
        raise corrupt("record_id does not match the content or the file name")
    if obj["evidence_sha256"] != sha256_hex(canonical_bytes(obj["evidence"])):
        raise corrupt("evidence_sha256 does not match the evidence")
    return obj


def _read_limited(path: Path) -> bytes:
    with open(path, "rb") as handle:
        return handle.read(FILE_LIMIT + 1)


def load_record(root: Path, task_id: str, record_id: str) -> tuple[dict[str, Any], str]:
    """D15 for exactly one record on a confirmed root; returns (record, file_sha256). Creates and changes
    nothing and runs no check-ignore."""
    if _inspect_parents(root, task_id) < len(_parents(task_id)):
        raise RunlogError(NOT_FOUND, "no such record")
    path = Path(root) / record_rel(task_id, record_id)
    try:
        st = _lstat(path)
    except FileNotFoundError:
        raise RunlogError(NOT_FOUND, "no such record") from None
    except OSError:
        raise RunlogError(RECORD_UNREADABLE, "cannot inspect the record") from None
    if collect.is_link_like(path, st) or not _lexically_inside(root, path) or not _resolved_inside(root, path):
        raise RunlogError(STORE_PATH_INVALID, "the record is a link or outside the root")
    if not stat.S_ISREG(st.st_mode):
        raise RunlogError(RECORD_CORRUPT, "the record is not a regular file")
    if st.st_size > FILE_LIMIT:
        raise RunlogError(RECORD_CORRUPT, "the record is larger than the limit")
    try:
        raw = _read_limited(path)
    except OSError:
        raise RunlogError(RECORD_UNREADABLE, "cannot read the record") from None
    if len(raw) > FILE_LIMIT:
        raise RunlogError(RECORD_CORRUPT, "the record is larger than the limit")
    file_sha = sha256_hex(raw)
    return parse_record(raw, task_id, record_id, file_sha), file_sha


# ------------------------------------------------------------------------------------------- store (D11-D14)


def _create(root: Path, record: dict[str, Any], data: bytes, path: Path) -> dict[str, Any]:
    task_id, record_id = record["task_id"], record["record_id"]
    try:
        atomic.atomic_create_new_bytes(path, data)
    except atomic.CreateNewError as exc:
        warnings = [] if exc.tmp_leftover is None else [f"TMP_LEFTOVER:{exc.tmp_leftover.name}"]
        if exc.final_created:
            return {"status": STORED, "file_sha256": sha256_hex(data), "final_file_created": True,
                    "warnings": warnings}
        if isinstance(exc.cause, FileExistsError):
            try:
                existing, file_sha = load_record(root, task_id, record_id)
            except RunlogError as err:
                err.final_file_created = False
                err.warnings.extend(warnings)
                raise
            if identity(existing["task_id"], existing["evidence"]) != identity(task_id, record["evidence"]):
                conflict = RunlogError(RECORD_CONFLICT, "an existing record with this id differs", file_sha)
                conflict.final_file_created = False
                conflict.warnings.extend(warnings)
                raise conflict from None
            return {"status": ALREADY_STORED, "file_sha256": file_sha, "final_file_created": False,
                    "warnings": warnings}
        failure = RunlogError(STORE_FAILED, "the record could not be created")
        failure.final_file_created = False
        failure.warnings.extend(warnings)
        raise failure from None
    return {"status": STORED, "file_sha256": sha256_hex(data), "final_file_created": True, "warnings": []}


def save_record(root: Path, record: dict[str, Any]) -> dict[str, Any]:
    """D11-D14 on a confirmed root: path checks before check-ignore, missing parents created top-down, the
    record created without ever replacing a file. Directories this call created stay on error and are
    reported as DIR_LEFT warnings."""
    data = record_bytes(record)  # at most STDIN_LIMIT plus fixed fields: always below FILE_LIMIT
    task_id = record["task_id"]
    rel = record_rel(task_id, record["record_id"])
    path = Path(root) / rel
    if not _lexically_inside(root, path):
        raise RunlogError(STORE_PATH_INVALID, PATH_FAILED)
    parts = _parents(task_id)
    first_missing = _inspect_parents(root, task_id)
    _check_ignored(root, rel)
    created: list[str] = []
    try:
        current = Path(root).joinpath(*parts[:first_missing])
        for index in range(first_missing, len(parts)):
            current = current / parts[index]
            shown = "/".join(parts[:index + 1])
            try:
                _mkdir(current)
                created.append(shown)
            except FileExistsError:
                pass
            except OSError:
                raise RunlogError(STORE_FAILED, "cannot create a store directory") from None
            if _inspect_parents(root, task_id) <= index:
                raise RunlogError(STORE_PATH_INVALID, PATH_FAILED)
        if _inspect_parents(root, task_id) < len(parts) or not _resolved_inside(root, current):
            raise RunlogError(STORE_PATH_INVALID, PATH_FAILED)
        return _create(root, record, data, path)
    except RunlogError as exc:
        exc.warnings.extend(f"DIR_LEFT:{shown}" for shown in created)
        raise


# ------------------------------------------------------------------------------------------- results (D16-D17)


def result(command: str | None, status: str, *, warnings: list[str] | None = None, error: dict[str, str] | None
           = None, **fields: Any) -> dict[str, Any]:
    warnings = list(warnings or [])
    if error is not None:
        exit_code = 2
    elif status in (STORED, ALREADY_STORED, FOUND):
        exit_code = 1 if warnings else 0
    else:
        raise ValueError("unknown success status")
    out: dict[str, Any] = {"schema": RESULT_SCHEMA, "command": command, "status": status, "exit_code": exit_code,
                           "authority": AUTHORITY, "task_id": None, "record_id": None, "file_sha256": None,
                           "final_file_created": None, "evidence": None, "warnings": warnings, "error": error}
    unknown = set(fields) - set(out)
    if unknown:
        raise KeyError("unknown result fields")
    out.update(fields)
    return out


def failure(command: str | None, exc: RunlogError, **fields: Any) -> dict[str, Any]:
    fields.setdefault("file_sha256", exc.file_sha256)
    if exc.final_file_created is not None:
        fields["final_file_created"] = exc.final_file_created
    return result(command, exc.code, warnings=exc.warnings, error={"code": exc.code, "detail": exc.detail},
                  **fields)


def store_at(root: Path | None, task_id: str, raw: bytes) -> dict[str, Any]:
    """Store on `root` (None: the production root of this package). Tests pass a tmp repository."""
    if not valid_task_id(task_id):
        return failure("store", RunlogError(ARGUMENT_INVALID, "invalid task id"))
    try:
        doc = parse_evidence(raw)
    except RunlogError as exc:
        return failure("store", exc, task_id=task_id)
    record = build_record(task_id, doc)
    try:
        confirmed = confirm_root(package_root() if root is None else root)
        outcome = save_record(confirmed, record)
    except RunlogError as exc:
        return failure("store", exc, task_id=task_id, record_id=record["record_id"])
    return result("store", outcome["status"], warnings=outcome["warnings"], file_sha256=outcome["file_sha256"],
                  final_file_created=outcome["final_file_created"], task_id=task_id, record_id=record["record_id"])


def show_at(root: Path | None, task_id: str, record_id: str) -> dict[str, Any]:
    """Look up one record on `root` (None: the production root of this package)."""
    if not valid_task_id(task_id):
        return failure("show", RunlogError(ARGUMENT_INVALID, "invalid task id"))
    if not valid_record_id(record_id):
        return failure("show", RunlogError(ARGUMENT_INVALID, "invalid record id"), task_id=task_id)
    try:
        confirmed = confirm_root(package_root() if root is None else root)
        record, file_sha = load_record(confirmed, task_id, record_id)
    except RunlogError as exc:
        return failure("show", exc, task_id=task_id, record_id=record_id)
    return result("show", FOUND, file_sha256=file_sha, evidence=record["evidence"], task_id=task_id,
                  record_id=record_id)


def store_evidence(task_id: str, raw: bytes) -> dict[str, Any]:
    """D1: validate and store evidence bytes under the production root; returns a runlog result object.

    Defined outcomes and errors come back as result objects. An undefined internal exception propagates to
    the caller unchanged: nothing is printed and it is never turned into a success or final_file_created=false.
    A caller that gets such an exception must not guess whether the record was created or retry on its own."""
    return store_at(None, task_id, raw)


def load_evidence(task_id: str, record_id: str) -> dict[str, Any]:
    """D1: look up one record under the production root; returns a runlog result object. Undefined internal
    exceptions propagate unchanged, as for store_evidence."""
    return show_at(None, task_id, record_id)
