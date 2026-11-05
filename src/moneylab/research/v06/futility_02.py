"""BT4-FUTILITY-02: read-only post-hoc diagnostic of the BT4-FUTILITY-01 G7 records (Work Order D0-D13).

POST_HOC_DIAGNOSTIC on the same G7 sample: not an independent confirmation, results are SYNTHETIC / NOT_EVIDENCE.
The BT4-FUTILITY-01 module and the MC-V06 sources are imported and never changed (D0). Two entrypoints:

    python -m moneylab.research.v06.futility_02 verify-inputs --out <g5 dir> --expected-python <exe> --expected-head <C2>
    python -m moneylab.research.v06.futility_02 analyze --out <g6 dir> --expected-python <exe> --expected-head <C2>
        --input-verification <g5 dir>

Each prints exactly one JSON line on stdout (status, hashes, counts, time; never a result value), writes nothing to
stderr and exits 0 (COMPLETE) or 2 (STOP). An error becomes a fixed failure_code chosen by the running stage or by
an explicit F2Stop; exception messages are discarded because they can hold values (D11). Outputs are computed in
memory and written once, data file first and SHA256SUMS last (D12). D13 (the CI tested-tree evidence) is a G4c
check done with gh, not code here.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import re
import subprocess
import sys
import time
import warnings
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from fractions import Fraction
from pathlib import Path as FsPath
from statistics import NormalDist
from typing import Any, TextIO

import moneylab
from moneylab.research.v06 import futility_diag as fd

TASK_ID = "BT4-FUTILITY-02"
ANALYSIS_SCHEMA = "moneylab.bt4_futility_02.analysis/1"
INPUT_VERIFICATION_SCHEMA = "moneylab.bt4_futility_02.input_verification/1"
RESEARCH_CLASSIFICATION = "POST_HOC_DIAGNOSTIC"
INPUT_VERIFICATION_FILE = "input_verification.json"
ANALYSIS_FILE = "analysis.json"
STDERR_FILE = "stderr.bin"
SUMS_FILE = fd.SUMS_FILE

FAILURE_CODES = ("IDENTITY_FAILED", "SOURCE_WORKTREE_CHANGED", "INPUT_HASH_MISMATCH", "VERIFY_RUN_FAILED",
                 "VERIFY_V4_FAILED", "CALIBRATION_MISMATCH", "UDR_OR_LOCK_INVALID", "G8A_DIR_PRESENT",
                 "OUTPUT_NOT_IGNORED", "OUTPUT_DIR_NOT_FRESH", "REGEN_MISMATCH", "LENGTH_MISMATCH", "RECORD_INVALID",
                 "NONFINITE", "SIGMA_NONPOSITIVE", "SE_ZERO", "WRITE_FAILED", "INTERNAL_ERROR")

# Work Order INPUT_HASH_MANIFEST (sha256 of LF bytes for code and contract files, of file bytes for outputs).
SOURCE_CODE_SHA = "d2fcaf64b5fb87f502afba29572be340f653be24"
CODE_ROWS = {
    "src/moneylab/research/v06/futility_diag.py": "2415305b4002661d982ecb9a00843ce9ff882676f91dcf0c78ee03d4d0446e50",
    "src/moneylab/research/v06/synthetic.py": "fc8c944ed3f542079ee5df2b8bf3aa208f8f492dbe726829f9d92c144a03d337",
    "src/moneylab/research/v06/montecarlo.py": "b01897591e5c70b0558c558cc7a320d0d73be0ccd2ce2db066aa3763231c5534",
    "src/moneylab/research/v06/procedures.py": "bdb261d0328d5bab71ac4b1b2fb082a8a08fd557f3363a21f854eba825f8a351",
    "src/moneylab/research/v06/risk_model.py": "296e14789f82301b26fb2659ba33f2bfd2ab368e3d6de61b504cfe6958f28e7a",
    "src/moneylab/research/v06/__init__.py": "40140983b003261e150e529f0a251046629414b68cfe66bd2704be99cd12fbe7",
    "src/moneylab/research/stats.py": "b3d9d05d9d29270cee60ce648aa4a5eb56a4213f7bb855496cc2b3d0fb9ef4e4",
}
CONTRACT_ROWS = {
    "docs/tasks/BT4-FUTILITY-01/WORK_ORDER.md": "c1e7003788d3878c8812b8bd1dd93b5d1df28d21c01b84099225a99525bf3b8b",
    "docs/tasks/BT4-FUTILITY-01/ERRATA-001.md": "9fcac5a97605a85be68612ba4a465c5f24b8c5b5594f3a801ca5e551993d24bf",
    "docs/tasks/BT4-FUTILITY-01/ERRATA-002.md": "0ca8ab961af350b10a2660ca8ee7b8c4bfab2757ee2b6b1ae61ffcfeee7308fe",
    "docs/tasks/BT4-FUTILITY-01/ERRATA-003.md": "9b8fcf9f30d8b525237a63b00f599add0a2fbcb33cb0f9ce900642a5a349823d",
    "docs/tasks/BT4-FUTILITY-01/ERRATA-004.md": "4b8de161474139cd24976897804a717ad94c9beaa89a2f74da492e0e845b2061",
    "docs/tasks/BT4-FUTILITY-01/ERRATA-005.md": "34408e04bf832446d376cc5dd679a4fc4f4afc20b8d1be472c640d75be1d194e",
    "docs/tasks/BT4-FUTILITY-01/ERRATA-006.md": "63c08d10131a71911e849f60b4ff09c542853821c1a3458a68369ffa1bc6fd11",
    "docs/tasks/BT4-FUTILITY-01/ERRATA-007.md": "25841248dae87d0f5568c72e9b35b00ea1a79530f1e546c7d5c312cb67d56cda",
    "docs/research_bt4_futility_diag_preregistration.md":
        "6da9e20088b1a6ca5c9ce9696c0baadd0850d7aa409f962f2583b188b322189f",
    "configs/bt4_futility_diag.toml": "3df664508e117ae25b05d7de49b3f62dec1c6ef55eab185ce0cf52f631351723",
}
E1_RUN, P0_RUN, V4_RUN = "g7-E1-theta0.7-d2fcaf64b5fb", "g7-P0-theta0.7-d2fcaf64b5fb", "g7-v4-d2fcaf64b5fb"
PILOT_RUN, CAL_RUN = "g5-pilot-d2fcaf64b5fb", "g5-cal-d2fcaf64b5fb"
UDR_FILE, LOCK_RELEASED = "000001-PD5_PROCEED.json", "000001.released"
DATA_ROWS = {
    f"{E1_RUN}/manifest.json": "ceecf2fa0e7c7666866e2174a2478ab115ddeefde69ca42be5a38bc07b869ea3",
    f"{E1_RUN}/SHA256SUMS": "bd4bbe60c9cc5de8f3ff36d523a6f47bc38551932a063deb5a4c0d8dcc6474f4",
    f"{E1_RUN}/run_spec.json": "db26b584d61d0a72c70f7419a1fb8756ce22a60261b47350796bfe185f257f98",
    f"{E1_RUN}/run_inputs.json": "fa0d4e5d4ede01a18d1d9f8b96e3422df09b15882a6ef1c4eccd94990a48045a",
    f"{P0_RUN}/manifest.json": "d52c355896489739621a4dbec50b84ed86c165dd5a29722f74a9f60b90e8732e",
    f"{P0_RUN}/SHA256SUMS": "59b34d901d6a25f39c1e156a38351f995521010f6e7130752e2ae9ec85a2d857",
    f"{P0_RUN}/run_spec.json": "120c42ff50b2b36648323c6aca27ab0730209051293d760722c0cda9479eb5a5",
    f"{P0_RUN}/run_inputs.json": "60e54164393b8b4f7245af1399243429036e33c5aa31463648b0b6185f7425ae",
    f"{V4_RUN}/v4.json": "517f5ddbbcbee2439e6698e636a11459269d7c2651872251a2c7a078a48137a4",
    f"{V4_RUN}/SHA256SUMS": "86c1619a3c0d127d0e5635ff2cd32bba743e0601ac57bfca6e596cb4ea4c155d",
    f"{PILOT_RUN}/manifest.json": "fb8a66f54cb0cbe7ab396a8017d70705c6e90c4078dc5c7866c8894de703b7df",
    f"{PILOT_RUN}/SHA256SUMS": "f903d3c724ba6546999f7195de52a5a6acf794563af7038aca19073585ef1575",
    f"{PILOT_RUN}/g6/g6_summary.json": "9bcec3f11fd81f8d59241caa1c1e161baa9065a79cdb3ec727abe49ed0a93cd9",
    f"{PILOT_RUN}/g6/SHA256SUMS": "92b4f1de63d8729955e5dbde27632d0529ef302457dd427e7d64671b25201682",
    f"{CAL_RUN}/calibration.json": "a1bbada5821f7ae33707a8818927d3929d05a1ac4019946c15a7eac06e73531c",
    f"{fd.UDR_DIR}/{UDR_FILE}": "b8c8e6a6ae1ecbb8c8fe242d7e211729fee89469de3a6ecbafbeff609ae7df5d",
    f"{fd.LOCK_DIR}/000001.lock": "a896ecdec6eb9f04cbdda410ee6a71f104bdec94ab91e7c2c861fefda256003b",
    f"{fd.LOCK_DIR}/{LOCK_RELEASED}": "2b8ae66ba6bb5c6494d30955eaef8c58c94956ca33cadddb8f5b486ec24ae6b9",
}
CALIBRATION_SHA256 = DATA_ROWS[f"{CAL_RUN}/calibration.json"]
ALLOWED_FILES = ("docs/tasks/BT4-FUTILITY-02/WORK_ORDER.md", "docs/tasks/BT4-FUTILITY-02/ERRATA-001.md",
                 "src/moneylab/research/v06/futility_02.py", "tests/test_v06_futility_02.py")  # ERRATA-001

V4_YEARS = 4000                     # D7-a: the G7 V-4 evaluation path
V4_SEED_PARTS = fd.V4_EVAL_SEED_PARTS
REGEN_FIELDS = ("years", "seed_parts", "seed", "edge_annual", "sr_eval", "batch_sharpes", "batch_lengths")
K20 = 20
ALPHAS = (0.025, 0.10)              # D5
RD_QUANTILES = ("0.5", "0.9", "0.99")
R_OBS_CONF = 0.116                  # D9: MC-V06 r_obs on the conf window (SYNTHETIC)
RATIO_DENOMINATOR = 0.066           # D9: r_obs,conf - 0.05
_N = NormalDist()


def expected_return_count(years: int) -> int:
    """D7-a: E0 returns on [min_warmup() + 1, days - 1) of a years * 365 day path (4,000 years -> 1,459,876)."""
    return (years * 365 - 1) - (fd.min_warmup() + 1)


def expected_batch_lengths(n: int, k: int) -> list[int]:
    """split_batches: k contiguous batches, the first n mod k one element longer."""
    size, extra = divmod(n, k)
    return [size + 1] * extra + [size] * (k - extra)


GitRunner = Callable[[FsPath, Sequence[str]], tuple[int, bytes]]


def run_git(cwd: FsPath, args: Sequence[str]) -> tuple[int, bytes]:
    """One read-only git call; output is captured, never printed."""
    proc = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True)
    return proc.returncode, proc.stdout


@dataclass(frozen=True)
class F2Config:
    """Everything the Work Order fixes. Tests replace fields; the command line always uses DEFAULT_CONFIG."""
    target_worktree: FsPath = FsPath("C:/MoneyLab-bt4-futility-02")
    target_branch: str = "feature/bt4-futility-02"
    source_worktree: FsPath = FsPath("C:/MoneyLab-bt4-futility-diag")
    source_branch: str = "feature/bt4-futility-diag"
    source_output_root: FsPath = FsPath("C:/MoneyLab-bt4-futility-diag/data/processed/research_v06_futility_diag")
    new_output_root: FsPath = FsPath("C:/MoneyLab-bt4-futility-02/data/processed/research_v06_futility_02")
    module_root: FsPath | None = None            # TARGET_WORKTREE/src when None
    source_code_sha: str = SOURCE_CODE_SHA
    python_version: str = "3.14.8"
    platform: str = "win32"
    code_rows: Mapping[str, str] = field(default_factory=lambda: dict(CODE_ROWS))
    contract_rows: Mapping[str, str] = field(default_factory=lambda: dict(CONTRACT_ROWS))
    data_rows: Mapping[str, str] = field(default_factory=lambda: dict(DATA_ROWS))
    calibration_sha256: str = CALIBRATION_SHA256
    allowed_files: Sequence[str] = ALLOWED_FILES
    v4_years: int = V4_YEARS
    v4_seed_parts: Sequence[str] = V4_SEED_PARTS
    v4_edge_annual: float = fd.E_CAL
    expected_n: int = 1_459_876
    git: GitRunner = run_git

    def src_root(self) -> FsPath:
        return self.module_root if self.module_root is not None else self.target_worktree / "src"


DEFAULT_CONFIG = F2Config()
assert expected_return_count(V4_YEARS) == DEFAULT_CONFIG.expected_n


class F2Stop(Exception):
    """A STOP with an explicit failure_code (D11). The message is never printed."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(detail)
        self.code = code if code in FAILURE_CODES else "INTERNAL_ERROR"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def lf_sha256(path: FsPath) -> str:
    """sha256 of the file bytes with CRLF -> LF only, in memory (D1); the file is not changed."""
    return _sha256(fd._lf(FsPath(path).read_bytes()))


def _norm(path: object) -> str:
    return os.path.normcase(os.path.realpath(str(path)))


def _under(path: object, root: object) -> bool:
    p, r = _norm(path), _norm(root).rstrip("\\/")
    return p.startswith(r + os.sep)


def _git_ok(cfg: F2Config, cwd: FsPath, args: Sequence[str], code: str) -> bytes:
    rc, out = cfg.git(cwd, args)
    if rc != 0:
        raise F2Stop(code, "git query failed")
    return out


def _git_text(cfg: F2Config, cwd: FsPath, args: Sequence[str], code: str) -> str:
    return _git_ok(cfg, cwd, args, code).decode("utf-8").strip()


# --- arguments --------------------------------------------------------------------------------------------------

COMMANDS = {"verify-inputs": ("--out", "--expected-python", "--expected-head"),
            "analyze": ("--out", "--expected-python", "--expected-head", "--input-verification")}
_HEX40 = re.compile(r"[0-9a-f]{40}")


def parse_args(argv: Sequence[str]) -> tuple[str, dict[str, str]]:
    """`<command> --key value ...`: every required key exactly once, nothing else. Errors raise, never print."""
    if not argv or argv[0] not in COMMANDS:
        raise F2Stop("IDENTITY_FAILED", "unknown command")
    keys, rest, opts = COMMANDS[argv[0]], list(argv[1:]), {}
    if len(rest) % 2:
        raise F2Stop("IDENTITY_FAILED", "odd arguments")
    for k, v in zip(rest[0::2], rest[1::2]):
        if k not in keys or k in opts or not v:
            raise F2Stop("IDENTITY_FAILED", "bad argument")
        opts[k] = v
    if set(opts) != set(keys) or not _HEX40.fullmatch(opts["--expected-head"]):
        raise F2Stop("IDENTITY_FAILED", "missing argument")
    return argv[0], opts


# --- D1 identity, output directory ------------------------------------------------------------------------------

_ATTEMPT_DIR = re.compile(r"(g5-input|g6-analysis)-([0-9a-f]{12})-a([1-9][0-9]*)")
_PREFIX = {"verify-inputs": "g5-input", "analyze": "g6-analysis"}


def check_identity(cfg: F2Config, opts: Mapping[str, str]) -> dict[str, Any]:
    """D1: platform, Python, interpreter path, HEAD, branch, clean worktree, module location, code blobs and LF working
    files, ancestry and changed paths. Any mismatch raises (stage code IDENTITY_FAILED)."""
    code, wt = "IDENTITY_FAILED", cfg.target_worktree
    if sys.platform != cfg.platform or platform.python_version() != cfg.python_version:
        raise F2Stop(code, "platform / python")
    if _norm(sys.executable) != _norm(opts["--expected-python"]):
        raise F2Stop(code, "interpreter")
    head = _git_text(cfg, wt, ["rev-parse", "HEAD"], code)
    if head != opts["--expected-head"]:
        raise F2Stop(code, "head")
    if _git_text(cfg, wt, ["rev-parse", "--abbrev-ref", "HEAD"], code) != cfg.target_branch:
        raise F2Stop(code, "branch")
    if _git_ok(cfg, wt, ["status", "--porcelain"], code).strip():
        raise F2Stop(code, "dirty")
    for mod in (moneylab, fd, sys.modules[__name__]):
        if not _under(mod.__file__, cfg.src_root()):
            raise F2Stop(code, "module location")
    for path, want in cfg.code_rows.items():
        if _sha256(_git_ok(cfg, wt, ["cat-file", "blob", f"HEAD:{path}"], code)) != want:
            raise F2Stop(code, "code blob")
        if lf_sha256(wt / path) != want:
            raise F2Stop(code, "code working file")
    rc, _ = cfg.git(wt, ["merge-base", "--is-ancestor", cfg.source_code_sha, "HEAD"])
    if rc != 0:
        raise F2Stop(code, "ancestry")
    changed = _git_text(cfg, wt, ["diff", "--name-only", cfg.source_code_sha, "HEAD"], code).splitlines()
    if not set(changed) <= set(cfg.allowed_files):
        raise F2Stop(code, "changed paths")
    return {"analysis_code_sha": head, "python_executable": sys.executable, "python_version": sys.version,
            "platform": sys.platform}


def check_output_ignored(cfg: F2Config, out_dir: FsPath) -> None:
    rc, _ = cfg.git(cfg.target_worktree, ["check-ignore", "-q", str(out_dir)])
    if rc != 0:
        raise F2Stop("OUTPUT_NOT_IGNORED", "not ignored")


def check_output_fresh(cfg: F2Config, out_dir: FsPath, command: str, head: str) -> None:
    """D10/D12: the attempt directory is NEW_OUTPUT_ROOT/<prefix>-<head12>-a<N>/ holding only an empty stderr.bin,
    and NEW_OUTPUT_ROOT holds attempt directories only."""
    code = "OUTPUT_DIR_NOT_FRESH"
    m = _ATTEMPT_DIR.fullmatch(out_dir.name)
    if m is None or m.group(1) != _PREFIX[command] or m.group(2) != head[:12]:
        raise F2Stop(code, "attempt name")
    if _norm(out_dir.parent) != _norm(cfg.new_output_root) or not out_dir.is_dir():
        raise F2Stop(code, "attempt location")
    entries = sorted(p.name for p in out_dir.iterdir())
    if entries != [STDERR_FILE] or not (out_dir / STDERR_FILE).is_file() or (out_dir / STDERR_FILE).stat().st_size:
        raise F2Stop(code, "attempt contents")
    for p in cfg.new_output_root.iterdir():
        if not (p.is_dir() and _ATTEMPT_DIR.fullmatch(p.name)):
            raise F2Stop(code, "root contents")


# --- D2 input verification --------------------------------------------------------------------------------------

def check_source_worktree(cfg: F2Config) -> None:
    code, wt = "SOURCE_WORKTREE_CHANGED", cfg.source_worktree
    if (_git_text(cfg, wt, ["rev-parse", "HEAD"], code) != cfg.source_code_sha
            or _git_text(cfg, wt, ["rev-parse", "--abbrev-ref", "HEAD"], code) != cfg.source_branch
            or _git_ok(cfg, wt, ["status", "--porcelain"], code).strip()):
        raise F2Stop(code, "source worktree")


def check_input_hashes(cfg: F2Config) -> list[list[str]]:
    """Contract rows (HEAD blob and LF working file) and the G7 / G5 / UDR / lock rows (file bytes)."""
    code, checks = "INPUT_HASH_MISMATCH", []
    for path, want in cfg.contract_rows.items():
        got = _sha256(_git_ok(cfg, cfg.target_worktree, ["cat-file", "blob", f"HEAD:{path}"], code))
        if got != want or lf_sha256(cfg.target_worktree / path) != want:
            raise F2Stop(code, "contract row")
        checks.append([f"contract:{path}", want, got, "PASS"])
    for rel, want in cfg.data_rows.items():
        p = cfg.source_output_root / rel
        got = _sha256(p.read_bytes()) if p.is_file() else "MISSING"
        if got != want:
            raise F2Stop(code, "data row")
        checks.append([f"data:{rel}", want, got, "PASS"])
    return checks


def check_runs(cfg: F2Config) -> dict[str, int]:
    """verify_run: both CORE runs COMPLETE on every axis; the pilot COMPLETE with g6 VERIFIED."""
    root, counts = cfg.source_output_root, {}
    for name, run in (("e1", E1_RUN), ("p0", P0_RUN)):
        v = fd.verify_run(root / run)
        if (v["status"], v["unit_status"], v["time_accounting"]) != ("COMPLETE", "COMPLETE", "COMPLETE"):
            raise F2Stop("VERIFY_RUN_FAILED", "core run")
        counts[f"{name}_units"] = int(v["units"])
    v = fd.verify_run(root / PILOT_RUN)
    if (v["status"], v["g6"]) != ("COMPLETE", "VERIFIED"):
        raise F2Stop("VERIFY_RUN_FAILED", "pilot")
    counts["pilot_units"] = int(v["units"])
    return counts


def load_v4(cfg: F2Config) -> dict[str, Any]:
    v = fd.verify_v4_run(cfg.source_output_root / V4_RUN)
    if v["status"] != "VERIFIED" or v["sha256"] != cfg.data_rows[f"{V4_RUN}/v4.json"]:
        raise F2Stop("VERIFY_V4_FAILED", "v4")
    v4: dict[str, Any] = v["v4"]
    return v4


def check_v4(cfg: F2Config) -> None:
    load_v4(cfg)


def load_calibration(cfg: F2Config) -> dict[str, Any]:
    cal, _ = fd.load_calibration(cfg.source_output_root / CAL_RUN / fd.CALIBRATION_FILE, cfg.calibration_sha256)
    return cal


def check_calibration(cfg: F2Config) -> None:
    """The calibration file has its sha256, and both CORE runs' run_inputs name that calibration."""
    load_calibration(cfg)
    for run in (E1_RUN, P0_RUN):
        inputs, _ = fd._read_canonical(cfg.source_output_root / run / fd.RUN_INPUTS_FILE, fd.RUN_INPUTS_FILE)
        if inputs["calibration_provenance"]["calibration_sha256"] != cfg.calibration_sha256:
            raise F2Stop("CALIBRATION_MISMATCH", "run_inputs")


def check_udr_lock(cfg: F2Config) -> None:
    root = cfg.source_output_root
    if sorted(p.name for p in (root / fd.UDR_DIR).iterdir()) != [UDR_FILE]:
        raise F2Stop("UDR_OR_LOCK_INVALID", "udr")
    if not (root / fd.LOCK_DIR / LOCK_RELEASED).is_file():
        raise F2Stop("UDR_OR_LOCK_INVALID", "lock")


def check_g8a_absent(cfg: F2Config) -> None:
    if any(p.name.startswith("g8a-") for p in cfg.source_output_root.iterdir()):
        raise F2Stop("G8A_DIR_PRESENT", "g8a")


# --- D3 to D9 ---------------------------------------------------------------------------------------------------

def regenerate_v4(years: int, seed_parts: Sequence[str], edge_annual: float) -> tuple[dict[str, Any], list[float]]:
    """D7-a: the steps of futility_diag.v4_evaluation, keeping the E0 returns for the K = 20 split."""
    parts = list(fd.validate_seed_parts(seed_parts))
    path = fd.make_path(replace(fd.E1_DGP, edge_annual=edge_annual), years * 365, fd.explicit_seed(parts))
    rets = fd.window_e0_returns(path, fd.signals(path.log_close, *fd.STRATEGIES[fd.E1_STRATEGY]),
                                fd.min_warmup() + 1, path.days - 1, fd.Costs().log_costs()["E0"])
    values, lengths = fd.batch_sharpes(rets, fd.V4_BATCHES)
    ev = {"years": years, "seed_parts": parts, "seed": fd.explicit_seed(parts), "edge_annual": edge_annual,
          "sr_eval": fd.finite_or_stop(fd.annual_sharpe(rets), "SR_eval"), "batch_sharpes": values,
          "batch_lengths": lengths}
    return ev, rets


def regeneration_check(cfg: F2Config, v4: Mapping[str, Any]) -> tuple[dict[str, Any], list[float]]:
    """D7-a: regenerate with the Work Order parameters, check n and the K = 40 lengths, then require the 7 fields to
    equal v4.json byte for byte (canonical_bytes, no tolerance)."""
    ev, rets = regenerate_v4(cfg.v4_years, cfg.v4_seed_parts, cfg.v4_edge_annual)
    n = len(rets)
    if n != cfg.expected_n or ev["batch_lengths"] != expected_batch_lengths(n, fd.V4_BATCHES):
        raise F2Stop("LENGTH_MISMATCH", "n / batch lengths")
    if any(f not in v4 for f in REGEN_FIELDS) or (fd.canonical_bytes({f: ev[f] for f in REGEN_FIELDS})
                                                  != fd.canonical_bytes({f: v4[f] for f in REGEN_FIELDS})):
        raise F2Stop("REGEN_MISMATCH", "fields")
    return {"status": "MATCH", "fields": list(REGEN_FIELDS), "n": n, "k40_batch_lengths": ev["batch_lengths"]}, rets


def read_core_records(cfg: F2Config) -> dict[str, list[dict[str, Any]]]:
    by_cell: dict[str, list[dict[str, Any]]] = {}
    for run in (E1_RUN, P0_RUN):
        spec, _, _, _ = fd._load_spec_inputs(cfg.source_output_root / run)
        by_cell.update(fd.read_records(cfg.source_output_root / run, spec))
    return by_cell


def bootstrap_b(cfg: F2Config) -> int:
    spec, _, _, _ = fd._load_spec_inputs(cfg.source_output_root / E1_RUN)
    return int(spec["bootstrap"])


def _sigma(cal: Mapping[str, Any]) -> tuple[float, float]:
    s_lo, s_hi = cal["sigma"]["sigma_L"], cal["sigma"]["sigma_U"]
    for s in (s_lo, s_hi):
        if not (isinstance(s, (int, float)) and math.isfinite(s) and s > 0):
            raise F2Stop("SIGMA_NONPOSITIVE", "sigma")
    return float(s_lo), float(s_hi)


def primary_labels(by_cell: Mapping[str, Sequence[Mapping[str, Any]]], v4: Mapping[str, Any],
                   cal: Mapping[str, Any]) -> dict[str, Any]:
    """D3 R4: futility_diag.decision_summary unchanged (Holm over exactly V-1, V-2, V-3, V-8, V-4)."""
    if not fd.batch_means_se(v4["batch_sharpes"]) > 0:
        raise F2Stop("SE_ZERO", "batch-means SE")
    _sigma(cal)
    out: dict[str, Any] = fd.decision_summary(by_cell, v4, cal["sigma"])
    return out


def _quantile(sorted_x: Sequence[int], p: str) -> int:
    """Nearest rank: x_(ceil(p N)), computed exactly."""
    q = Fraction(p) * len(sorted_x)
    return sorted_x[math.ceil(q) - 1]


def rd_distribution(by_cell: Mapping[str, Sequence[Mapping[str, Any]]], bootstrap: int) -> dict[str, Any]:
    """D4 R1: per-replication RD count d on E1 f12; SD replications counted apart."""
    recs = fd.window_records(by_cell, fd.E1_CELL, "f12")
    ds, sd_count = [], 0
    for r in recs:
        d, sd = r["variants"]["S1"]["d"], r["sd"]
        if isinstance(d, bool) or not isinstance(d, int) or not 0 <= d <= bootstrap or not isinstance(sd, bool):
            raise F2Stop("RECORD_INVALID", "d / sd")
        if sd:
            sd_count += 1
        else:
            ds.append(d)
    ds.sort()
    counts: dict[int, int] = {}
    for d in ds:
        counts[d] = counts.get(d, 0) + 1
    out: dict[str, Any] = {"cell": fd.E1_CELL, "window": "f12", "reps_R": len(recs), "bootstrap_B": bootstrap,
                           "sd_count": sd_count, "n_nonsd": len(ds), "counts": [[d, c] for d, c in sorted(counts.items())]}
    if not ds:
        out.update(summary=None, status="EMPTY")
        return out
    out["summary"] = {"share_d0": counts.get(0, 0) / len(ds), "mean": sum(ds) / len(ds), "max": ds[-1],
                      **{f"q{p[2:].ljust(2, '0')}": _quantile(ds, p) for p in RD_QUANTILES}}
    out["status"] = "OK"
    return out


def rejects_at(rec: Mapping[str, Any], indicator: str, alpha: float) -> bool:
    """I_v(alpha) = 1{p_v <= alpha}: as futility_diag.rejects at another alpha."""
    v = rec["variants"]
    p = v["S1"]["p_lo"] if indicator == "S1_lo" else v["S1"]["p_hi"] if indicator == "S1_hi" else v[indicator]["p"]
    return bool(p <= alpha)


def _rate(flags: Sequence[bool]) -> dict[str, Any]:
    n = len(flags)
    r = sum(1 for f in flags if f) / n
    return {"rate": r, "mc_se": math.sqrt(r * (1 - r) / n), "reps": n}


def _contrast_out(c: fd.Contrast, with_upper: bool = False) -> dict[str, Any]:
    out = {"d_hat": c.d_hat, "se": c.se, "n10": c.n10, "n01": c.n01, "reason": c.reason,
           "p_one_sided_unadjusted": c.p_one_sided}
    if with_upper:
        out["u_d"] = c.upper
    return out


def alpha_contrasts(by_cell: Mapping[str, Sequence[Mapping[str, Any]]]) -> list[dict[str, Any]]:
    """D5 R2: rates and the 5 paired contrasts at alpha 0.025 and 0.10. No EFF, U_D, Holm or label."""
    out = []
    for alpha in ALPHAS:
        rates: dict[str, dict[str, dict[str, Any]]] = {}
        for cell, recs in by_cell.items():
            for w in [w for w in fd.WINDOWS if any(r["window"] == w for r in recs)]:
                wr = fd.window_records(by_cell, cell, w)
                rates.setdefault(cell, {})[w] = {ind: _rate([rejects_at(r, ind, alpha) for r in wr])
                                                 for ind in fd.INDICATORS}
        contrasts = []
        for name, (cell, (w_a, v_a), (w_b, v_b)) in fd.CONTRASTS.items():
            a, b = fd.window_records(by_cell, cell, w_a), fd.window_records(by_cell, cell, w_b)
            if len(a) != len(b):
                raise F2Stop("RECORD_INVALID", "pairing")
            c = fd.mcnemar([rejects_at(r, v_a, alpha) for r in a], [rejects_at(r, v_b, alpha) for r in b])
            contrasts.append({"name": name, **_contrast_out(c)})
        out.append({"alpha": alpha, "rates": rates, "contrasts": contrasts})
    return out


def pd4_sensitivity(by_cell: Mapping[str, Sequence[Mapping[str, Any]]]) -> dict[str, Any]:
    """D6 R3: V-2 (E1 f12, V0 vs V0d) on the non-SD replications, primary alpha, no label."""
    recs = fd.window_records(by_cell, fd.E1_CELL, "f12")
    if any(not isinstance(r["sd"], bool) for r in recs):
        raise F2Stop("RECORD_INVALID", "sd")
    sub = [r for r in recs if not r["sd"]]
    out: dict[str, Any] = {"R_total": len(recs), "R_sd": len(recs) - len(sub), "R_subset": len(sub)}
    if not sub:
        out.update(rates=None, contrast=None, status="NOT_COMPUTABLE_EMPTY_SUBSET")
        return out
    v0, v0d = [fd.rejects(r, "V0") for r in sub], [fd.rejects(r, "V0d") for r in sub]
    out.update(rates={"V0": _rate(v0), "V0d": _rate(v0d)}, contrast=_contrast_out(fd.mcnemar(v0, v0d), True),
               status="OK")
    return out


def v4_k20(rets: Sequence[float], v4: Mapping[str, Any]) -> tuple[dict[str, Any], list[float]]:
    """D7-b: the same returns in 20 contiguous batches, t(19). Sensitivity only: no label."""
    values, lengths = fd.batch_sharpes(rets, K20)
    if lengths != expected_batch_lengths(len(rets), K20):
        raise F2Stop("LENGTH_MISMATCH", "k20 lengths")
    if not all(math.isfinite(x) for x in values):
        raise F2Stop("NONFINITE", "k20 batch")
    se40 = fd.batch_means_se(v4["batch_sharpes"])
    if not (fd.batch_means_se(values) > 0 and se40 > 0):
        raise F2Stop("SE_ZERO", "k20 se")
    inf = fd.v4_inference(v4["sr_eval"], fd.CORE_THETA, values)
    return {"k": K20, "df": K20 - 1, "batch_lengths": lengths, "se": inf.se,
            "t_quantile": fd.t_ppf(1 - fd.V4_GAMMA_DELTA, K20 - 1), "delta_lower": inf.delta_lower,
            "delta_upper": inf.delta_upper, "p_one_sided": inf.p_one_sided, "se_ratio_vs_k40": inf.se / se40}, values


def acf1(x: Sequence[float]) -> float | None:
    """D8: sum_{j<K} (x_j - m)(x_{j+1} - m) / sum_j (x_j - m)^2 with m the mean of all K; None for a constant series."""
    if len(x) < 3:
        raise F2Stop("LENGTH_MISMATCH", "K < 3")
    if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in x):
        raise F2Stop("NONFINITE", "lag-1 input")
    if all(v == x[0] for v in x):
        return None
    m = sum(x) / len(x)
    d = [v - m for v in x]
    den = sum(v * v for v in d)
    if den == 0:
        return None
    return sum(d[j] * d[j + 1] for j in range(len(d) - 1)) / den


def lag1(k40: Sequence[float], k20: Sequence[float]) -> list[dict[str, Any]]:
    out = []
    for k, values, source in ((fd.V4_BATCHES, k40, "v4.json"), (K20, k20, "regenerated")):
        if len(values) != k:
            raise F2Stop("LENGTH_MISMATCH", "lag-1 K")
        rho = acf1(values)
        out.append({"k": k, "n_pairs": k - 1, "estimator": "acf_full_mean_full_ss", "rho1": rho,
                    "status": "UNDEFINED_CONSTANT" if rho is None else "OK", "batch_source": source})
    return out


def delta_rej_prime(delta: float, sigma: float, r_obs: float = R_OBS_CONF) -> float:
    """D9 secondary numerator: r_obs - Phi(Phi^-1(r_obs) + Delta / sigma)."""
    return r_obs - _N.cdf(_N.inv_cdf(r_obs) + delta / sigma)


def _ratio_flags(*ratios: float) -> list[str]:
    flags = []
    if any(r < 0 for r in ratios):
        flags.append("RATIO_NEGATIVE")
    if any(r > 1 for r in ratios):
        flags.append("RATIO_ABOVE_ONE")
    return flags


def conf_ratio(v4_block: Mapping[str, Any]) -> dict[str, Any]:
    """D9 C7: model-implied DeltaRej against the MC-V06 conf excess 0.066; not a causal or measured share."""
    vals = [v4_block[k] for k in ("delta_hat", "delta_lower", "delta_upper", "sigma_L", "sigma_U")]
    if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in vals):
        raise F2Stop("NONFINITE", "v4 values")
    dh, dl, du, s_lo, s_hi = (float(v) for v in vals)
    if not (s_lo > 0 and s_hi > 0):
        raise F2Stop("SIGMA_NONPOSITIVE", "sigma")
    points = []
    for name, s in (("sigma_L", s_lo), ("sigma_U", s_hi)):
        num, num_p = fd.delta_rej(dh, s), delta_rej_prime(dh, s)
        r, r_p = num / RATIO_DENOMINATOR, num_p / RATIO_DENOMINATOR
        for v in (num, num_p, r, r_p):
            if not math.isfinite(v):
                raise F2Stop("NONFINITE", "ratio")
        points.append({"delta": "delta_hat", "sigma": name, "delta_rej": num, "delta_rej_prime": num_p,
                       "ratio": r, "ratio_prime": r_p, "flags": _ratio_flags(r, r_p)})
    lo, hi = fd.rect_extrema(dl, du, s_lo, s_hi)
    corners_p = [delta_rej_prime(d, s) for d in (dl, du) for s in (s_lo, s_hi)]
    bounds = {"rectangle": "[L_delta, U_delta] x [sigma_L, sigma_U]",
              "delta_rej_min": lo, "delta_rej_max": hi, "ratio_min": lo / RATIO_DENOMINATOR,
              "ratio_max": hi / RATIO_DENOMINATOR, "delta_rej_prime_min": min(corners_p),
              "delta_rej_prime_max": max(corners_p), "ratio_prime_min": min(corners_p) / RATIO_DENOMINATOR,
              "ratio_prime_max": max(corners_p) / RATIO_DENOMINATOR}
    flags = sorted({f for p in points for f in p["flags"]})
    if abs(dh) / s_lo > fd.V4_APPROX_MAX:
        flags.append("APPROX_OUT_OF_RANGE")
    return {"denominator": RATIO_DENOMINATOR, "r_obs_conf": R_OBS_CONF, "primary_numerator": "delta_rej",
            "secondary_numerator": "delta_rej_prime", "point_range": points,
            "point_ratio_min": min(p["ratio"] for p in points), "point_ratio_max": max(p["ratio"] for p in points),
            "point_ratio_prime_min": min(p["ratio_prime"] for p in points),
            "point_ratio_prime_max": max(p["ratio_prime"] for p in points), "descriptive_bounds": bounds,
            "flags": flags, "interpretation": "model-implied rejection change relative to the MC-V06 conf excess; "
                                              "not a causal or measured share of over-rejection"}


# --- D12 writing ------------------------------------------------------------------------------------------------

def write_atomic(path: FsPath, data: bytes) -> str:
    """Exclusive *.tmp then rename (rename never replaces an existing file on Windows). A leftover *.tmp is kept."""
    tmp = path.with_name(path.name + fd.TMP_SUFFIX)
    sha = fd.create_exclusive(tmp, data)
    os.rename(tmp, path)
    return sha


def write_outputs(out_dir: FsPath, name: str, payload: Mapping[str, Any]) -> dict[str, str]:
    """The data file, then SHA256SUMS listing that file only (stderr.bin is never in it)."""
    data = fd.canonical_bytes(payload)
    sha = write_atomic(out_dir / name, data)
    write_atomic(out_dir / SUMS_FILE, f"{sha}  {name}\n".encode("utf-8"))
    return {name: sha, SUMS_FILE: _sha256((out_dir / SUMS_FILE).read_bytes())}


def check_input_verification(cfg: F2Config, g5_dir: FsPath, head: str) -> str:
    """The G5 attempt this analysis depends on: complete, PASS, same code; the G7 / G5 data rows still match."""
    code = "INPUT_HASH_MISMATCH"
    m = _ATTEMPT_DIR.fullmatch(g5_dir.name)
    if m is None or m.group(1) != "g5-input" or m.group(2) != head[:12] or _norm(g5_dir.parent) != _norm(
            cfg.new_output_root):
        raise F2Stop(code, "g5 dir")
    raw = (g5_dir / INPUT_VERIFICATION_FILE).read_bytes()
    if (g5_dir / SUMS_FILE).read_bytes() != f"{_sha256(raw)}  {INPUT_VERIFICATION_FILE}\n".encode("utf-8"):
        raise F2Stop(code, "g5 sums")
    iv, _ = fd._read_canonical(g5_dir / INPUT_VERIFICATION_FILE, INPUT_VERIFICATION_FILE)
    if (iv.get("schema_version"), iv.get("status"), iv.get("analysis_code_sha")) != (
            INPUT_VERIFICATION_SCHEMA, "PASS", head):
        raise F2Stop(code, "g5 payload")
    for rel, want in cfg.data_rows.items():
        p = cfg.source_output_root / rel
        if not p.is_file() or _sha256(p.read_bytes()) != want:
            raise F2Stop(code, "data row")
    return _sha256(raw)


# --- entrypoints ------------------------------------------------------------------------------------------------

@dataclass
class _Stage:
    name: str = "startup"
    code: str = "INTERNAL_ERROR"


def _run(st: _Stage, name: str, code: str, fn: Callable[..., Any], *args: Any) -> Any:
    """Run one stage: an exception inside it takes the stage's failure_code (or an F2Stop's explicit code)."""
    st.name, st.code = name, code
    result = fn(*args)
    st.name, st.code = f"after-{name}", "INTERNAL_ERROR"
    return result


def _g(name: str) -> Callable[..., Any]:
    fn: Callable[..., Any] = globals()[name]        # looked up at call time (failure-injection tests patch these)
    return fn


def _verify_inputs(st: _Stage, cfg: F2Config, opts: Mapping[str, str]) -> dict[str, Any]:
    out_dir = FsPath(opts["--out"])
    ident = _run(st, "identity", "IDENTITY_FAILED", _g("check_identity"), cfg, opts)
    head = ident["analysis_code_sha"]
    _run(st, "output-ignored", "OUTPUT_NOT_IGNORED", _g("check_output_ignored"), cfg, out_dir)
    _run(st, "output-fresh", "OUTPUT_DIR_NOT_FRESH", _g("check_output_fresh"), cfg, out_dir, "verify-inputs", head)
    _run(st, "source-worktree", "SOURCE_WORKTREE_CHANGED", _g("check_source_worktree"), cfg)
    checks = _run(st, "input-hashes", "INPUT_HASH_MISMATCH", _g("check_input_hashes"), cfg)
    counts = _run(st, "verify-run", "VERIFY_RUN_FAILED", _g("check_runs"), cfg)
    _run(st, "verify-v4", "VERIFY_V4_FAILED", _g("check_v4"), cfg)
    _run(st, "calibration", "CALIBRATION_MISMATCH", _g("check_calibration"), cfg)
    _run(st, "udr-lock", "UDR_OR_LOCK_INVALID", _g("check_udr_lock"), cfg)
    _run(st, "g8a-absent", "G8A_DIR_PRESENT", _g("check_g8a_absent"), cfg)
    payload = {"schema_version": INPUT_VERIFICATION_SCHEMA, "task_id": TASK_ID, "evidence": fd.EVIDENCE,
               "status": "PASS", "analysis_code_sha": head, "source_code_sha": cfg.source_code_sha,
               "python_executable": ident["python_executable"], "python_version": ident["python_version"],
               "checks": checks, "counts": {**counts, "code_rows": len(cfg.code_rows),
                                            "contract_rows": len(cfg.contract_rows), "data_rows": len(cfg.data_rows)}}
    shas = _run(st, "write", "WRITE_FAILED", _g("write_outputs"), out_dir, INPUT_VERIFICATION_FILE, payload)
    return {"output_sha256s": shas}


def _analyze(st: _Stage, cfg: F2Config, opts: Mapping[str, str]) -> dict[str, Any]:
    out_dir = FsPath(opts["--out"])
    ident = _run(st, "identity", "IDENTITY_FAILED", _g("check_identity"), cfg, opts)
    head = ident["analysis_code_sha"]
    _run(st, "output-ignored", "OUTPUT_NOT_IGNORED", _g("check_output_ignored"), cfg, out_dir)
    _run(st, "output-fresh", "OUTPUT_DIR_NOT_FRESH", _g("check_output_fresh"), cfg, out_dir, "analyze", head)
    iv_sha = _run(st, "input-verification", "INPUT_HASH_MISMATCH", _g("check_input_verification"), cfg,
                  FsPath(opts["--input-verification"]), head)
    v4 = _run(st, "load-v4", "VERIFY_V4_FAILED", _g("load_v4"), cfg)
    regen, rets = _run(st, "regeneration", "REGEN_MISMATCH", _g("regeneration_check"), cfg, v4)
    cal = _run(st, "calibration", "CALIBRATION_MISMATCH", _g("load_calibration"), cfg)
    by_cell = _run(st, "records", "RECORD_INVALID", _g("read_core_records"), cfg)
    primary = _run(st, "primary", "RECORD_INVALID", _g("primary_labels"), by_cell, v4, cal)
    bootstrap = _run(st, "bootstrap", "RECORD_INVALID", _g("bootstrap_b"), cfg)
    rd = _run(st, "rd", "RECORD_INVALID", _g("rd_distribution"), by_cell, bootstrap)
    alpha = _run(st, "alpha", "RECORD_INVALID", _g("alpha_contrasts"), by_cell)
    pd4 = _run(st, "pd4", "RECORD_INVALID", _g("pd4_sensitivity"), by_cell)
    k20, k20_values = _run(st, "v4-k20", "SE_ZERO", _g("v4_k20"), rets, v4)
    lag = _run(st, "lag1", "NONFINITE", _g("lag1"), v4["batch_sharpes"], k20_values)
    ratio = _run(st, "conf-ratio", "SIGMA_NONPOSITIVE", _g("conf_ratio"), primary["v4"])
    payload = {"schema_version": ANALYSIS_SCHEMA, "evidence": fd.EVIDENCE,
               "classification": {"research_classification": RESEARCH_CLASSIFICATION,
                                  "independent_confirmation": False, "validated": False,
                                  "primary_labels": "BT4-FUTILITY-02 computation of the BT4-FUTILITY-01 rules, "
                                                    "not the BT4-FUTILITY-01 G8a result"},
               "provenance": {"task_id": TASK_ID, "source_code_sha": cfg.source_code_sha,
                              "analysis_code_sha": head, "python_executable": ident["python_executable"],
                              "python_version": ident["python_version"], "input_verification_dir": FsPath(
                                  opts["--input-verification"]).name,
                              "v4_sha256": cfg.data_rows[f"{V4_RUN}/v4.json"],
                              "calibration_sha256": cfg.calibration_sha256},
               "input_verification_sha256": iv_sha, "regeneration": regen, "primary": primary, "rd": rd,
               "alpha": alpha, "pd4": pd4, "v4_k20": k20, "lag1": lag, "conf_ratio": ratio}
    shas = _run(st, "write", "WRITE_FAILED", _g("write_outputs"), out_dir, ANALYSIS_FILE, payload)
    return {"output_sha256s": shas, "regeneration": "MATCH"}


def _files(out_dir: FsPath | None) -> list[list[Any]]:
    if out_dir is None or not out_dir.is_dir():
        return []
    return [[p.name, p.stat().st_size, _sha256(p.read_bytes())] for p in sorted(out_dir.iterdir()) if p.is_file()]


def main(argv: Sequence[str] | None = None, config: F2Config = DEFAULT_CONFIG, out: TextIO | None = None) -> int:
    """D11: one JSON line on stdout, nothing on stderr, exit 0 COMPLETE or 2 STOP."""
    out = sys.stdout if out is None else out
    t0, st, out_dir = time.monotonic(), _Stage(), None
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            command, opts = _run(st, "arguments", "IDENTITY_FAILED", parse_args,
                                 list(sys.argv[1:] if argv is None else argv))
            out_dir = FsPath(opts["--out"])
            result = (_verify_inputs if command == "verify-inputs" else _analyze)(st, config, opts)
            payload: dict[str, Any] = {"status": "COMPLETE", "stage": command, **result}
            rc = 0
        except BaseException as exc:    # noqa: BLE001 - every failure becomes a fixed code (D11)
            code = exc.code if isinstance(exc, F2Stop) else st.code
            try:
                files = _files(out_dir)
            except BaseException:       # noqa: BLE001
                files = []
            payload = {"status": "STOP", "stage": st.name, "failure_code": code, "files": files}
            rc = 2
    payload.update(elapsed_s=round(time.monotonic() - t0, 3), warnings_count=len(caught),
                   python_executable=sys.executable, output_dir=None if out_dir is None else str(out_dir))
    out.write(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n")
    out.flush()
    return rc


if __name__ == "__main__":
    sys.exit(main())
