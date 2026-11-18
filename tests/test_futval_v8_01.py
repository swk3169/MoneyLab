"""FUTVAL-V8-01 offline tests: preregistration §9 T1-T12 plus the smoke and perf output schemas.

Only the FUTVAL-V8-01-TEST namespace and small fixed inputs are used. No operational run, smoke, performance
measurement, operational seed check or operational threshold computation happens here.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import subprocess
from fractions import Fraction
from pathlib import Path

import pytest

from moneylab.research.v06 import futval_v8_01 as F
from moneylab.research.v06 import procedures as P
from moneylab.storage import atomic

REPO = Path(__file__).resolve().parents[1]
TEST_CELLS = ((40, "0.3"), (60, "0.7"))
PROV = {"commit": "0" * 40,
        "files": {path: {"blob": F.EXPECTED_SOURCE_BLOBS.get(path, "1" * 40), "sha256_lf": "2" * 64}
                  for path in F.SOURCE_FILES}}


def run_test(tmp_path: Path, name: str = "run", workers: int = 1, reps: int = 6, b: int = 19,
             cells: tuple[tuple[int, str], ...] = TEST_CELLS, prov: dict | None = None) -> dict[str, str]:
    return F.run(tmp_path / name, workers=workers, namespace=F.NS_TEST, cells=cells, reps=reps, b=b,
                 provenance=PROV if prov is None else prov)


def _rel(a: float, b: float) -> float:
    return abs(a - b) / b if b > 0 else abs(a)


# --- T1 -------------------------------------------------------------------------------------------------------------

def test_t01_dgp_truth_and_scale_invariance():
    for th in F.THETAS:
        mu, sigma = F.p0_parameters(th)
        assert sigma == F.SIGMA == 0.70 / math.sqrt(365.0)
        assert math.isclose(mu / sigma * math.sqrt(365.0), float(th), rel_tol=1e-12)
    data_seed = F.seed(F.NS_TEST, 50, "0.5", 0, "data")
    r = F.generate_p0(50, "0.5", data_seed)
    mu, sigma = F.p0_parameters("0.5")
    rng = random.Random(data_seed)
    assert r == [mu + sigma * rng.gauss(0.0, 1.0) for _ in range(50)]
    boot_seed = F.seed(F.NS_TEST, 50, "0.5", 0, "boot")
    p1 = F.v0_statistics(r, "0.5", boot_seed, 19)[3]
    p2 = F.v0_statistics([2.0 * x for x in r], "0.5", boot_seed, 19)[3]
    assert p1 == p2


# --- T2 -------------------------------------------------------------------------------------------------------------

def test_t02_v0_path_matches_procedures_and_operational_constants():
    n, th = 45, "0.7"
    r = F.generate_p0(n, th, F.seed(F.NS_TEST, n, th, 3, "data"))
    boot_seed = F.seed(F.NS_TEST, n, th, 3, "boot")
    m = P.mean(r)
    delta = P.futility_delta(0.7, r)
    boot = P.bootstrap_means([r], mean_block=20, resamples=19, seed=boot_seed)[0]
    p = P.futility_pvalue(m, boot, delta)
    assert F.v0_statistics(r, th, boot_seed, 19) == (m, P.sd(r), delta, p)
    assert F.v0_replicate(r, th, boot_seed, 19) == (F.NORMAL, 1 if p <= 0.05 else 0)
    assert (F.R, F.B, F.MEAN_BLOCK, F.ALPHA) == (10_000, 9_999, 20, Fraction(1, 20))
    assert (F.EPSILON, F.TOLERANCE, F.LAMBDA, F.BASE) == (Fraction(1, 100), Fraction(3, 50), Fraction(1, 40), 20261118)
    assert (F.NS_MAIN, F.NS_PERF, F.NS_TEST) == ("FUTVAL-V8-01", "FUTVAL-V8-01-PERF", "FUTVAL-V8-01-TEST")
    assert F.CELLS == tuple((n, t) for n in (365, 731, 1096, 2227) for t in ("0.3", "0.5", "0.7"))
    assert (1 + 499) / (F.B + 1) <= F.REJECT_P
    assert not (1 + 500) / (F.B + 1) <= F.REJECT_P


def test_t02_operational_paths_refuse_test_sized_inputs(tmp_path):
    with pytest.raises(ValueError):
        F.run(tmp_path / "m", reps=5, provenance=PROV)
    with pytest.raises(ValueError):
        F.run(tmp_path / "m", namespace=F.NS_PERF, provenance=PROV)
    with pytest.raises(ValueError):
        F.perf(tmp_path / "m", 2, namespace=F.NS_PERF, reps=1, b=9)
    assert not (tmp_path / "m").exists()


# --- T3 -------------------------------------------------------------------------------------------------------------

def test_t03_seed_serialization_and_uniqueness():
    s = F.seed_string(F.NS_TEST, 365, "0.3", 7, "boot")
    assert s == "FUTVAL-V8-01-TEST|v1|BASE=20261118|n=365|theta=0.3|rep=7|stream=boot"
    value = F.seed(F.NS_TEST, 365, "0.3", 7, "boot")
    assert value == int.from_bytes(hashlib.sha256(s.encode("utf-8")).digest()[:8], "big")
    assert 0 <= value < 2 ** 64
    assert F.seed(F.NS_TEST, 365, "0.3", 7, "data") != value
    assert F.seed_uniqueness(F.NS_TEST, TEST_CELLS, 10) == {"namespace": F.NS_TEST, "count": 40, "distinct": 40,
                                                            "pass": True}
    with pytest.raises(F.StopRun) as err:
        F.seed_uniqueness(F.NS_TEST, TEST_CELLS, 3, seed_fn=lambda *args: 1)
    assert err.value.code == "SEED_DUPLICATE"
    for bad in (("OTHER", 365, "0.3", 0, "data"), (F.NS_TEST, 365, "0.4", 0, "data"),
                (F.NS_TEST, 365, "0.3", 0, "other"), (F.NS_TEST, 365, "0.3", -1, "data")):
        with pytest.raises(ValueError):
            F.seed_string(*bad)


# --- T4 -------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("prob", [F.ALPHA, F.TOLERANCE])
def test_t04_exact_and_log_tails_agree_on_small_r(prob):
    reps = 40
    for k in range(0, reps + 1):
        up, lo = F.exact_upper_tail(reps, prob, k), F.exact_lower_tail(reps, prob, k)
        assert _rel(F.log_upper_tail(reps, float(prob), k), float(up)) <= F.REL_TOL
        assert _rel(F.log_lower_tail(reps, float(prob), k), float(lo)) <= F.REL_TOL
        assert F.exact_lower_tail(reps, prob, k - 1) + up == 1
    assert F.exact_upper_tail(reps, prob, reps + 1) == 0 and F.exact_lower_tail(reps, prob, -1) == 0


def test_t04_threshold_includes_the_equality_boundary():
    reps = 40
    level = F.exact_upper_tail(reps, F.ALPHA, 5)
    assert F.axis_a_thresholds(reps, [level]) == [5]
    assert F.axis_a_thresholds(reps, [level - Fraction(1, 10 ** 60)]) == [6]


# --- T5 -------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("reps", [30, 50])
def test_t05_threshold_conversion_equals_direct_tail_decisions(reps):
    levels = F.holm_levels(12)
    a = F.axis_a_thresholds(reps, levels)
    b = F.axis_b_threshold(reps)
    for t, aj in zip(levels, a):
        for k in range(reps + 1):
            assert (F.exact_upper_tail(reps, F.ALPHA, k) <= t) == (k >= aj)
    for x in range(reps + 1):
        assert (F.exact_lower_tail(reps, F.TOLERANCE, x) <= F.LAMBDA) == (x <= b)
    assert F.verify_thresholds(reps, a, levels, b)


# --- T6 -------------------------------------------------------------------------------------------------------------

def test_t06_holm_order_ties_and_stop():
    assert F.holm_levels(12) == [Fraction(1, 40) / (13 - j) for j in range(1, 13)]
    assert F.holm_axis_a([9, 12, 7], [10, 8, 6]) == [True, True, True]
    assert F.holm_axis_a([9, 9, 1], [9, 10, 0]) == [True, False, False]   # tie: fixed cell order, then stop
    assert F.holm_axis_a([1, 9, 9], [9, 10, 0]) == [False, True, False]
    with pytest.raises(ValueError):
        F.holm_axis_a([1], [1, 2])


# --- T7 -------------------------------------------------------------------------------------------------------------

def test_t07_decision_truth_table():
    a, b = [5, 4], 7
    k, d = [6, 2], [0, 6]
    assert F.holm_axis_a(k, a) == [True, False]
    assert F.axis_b([x + y for x, y in zip(k, d)], b) == [True, False]   # cell 0: both axes true at once
    assert F.axis_b(k, b) == [True, True]                                # D > 0 changes axis B for cell 1
    assert F.holm_axis_a([0, 0], a) == [False, False] and F.axis_b([9, 8], b) == [False, False]
    design, rows, summary = F.evaluate([(1, 0), (3, 1)], 40, TEST_CELLS)
    ra = F.holm_axis_a([1, 3], design["a"])
    rb = F.axis_b([1, 4], design["b"])
    assert [r["axis_A"] == F.SIZE_EXCESS_CONFIRMED for r in rows] == ra
    assert [r["axis_B"] == F.WITHIN_TOLERANCE_SHOWN for r in rows] == rb
    assert summary == {"ANY_SIZE_EXCESS_CONFIRMED": "YES" if any(ra) else "NO",
                       "ALL_CELLS_WITHIN_TOLERANCE_SHOWN": "YES" if all(rb) else "NO"}


# --- T8 -------------------------------------------------------------------------------------------------------------

def test_t08_degenerate_is_counted_and_an_exception_stops_without_retry(tmp_path, monkeypatch):
    assert F.v0_replicate([0.01] * 30, "0.5", 1, 19) == (F.DEGENERATE, None)
    real = F.v0_replicate
    monkeypatch.setattr(F, "v0_replicate", lambda r, th, s, b: (F.DEGENERATE, None))
    run_test(tmp_path, "deg")
    rows = json.loads((tmp_path / "deg" / "cells.json").read_bytes())["cells"]
    assert [(row["K"], row["D"]) for row in rows] == [(0, 6), (0, 6)]
    monkeypatch.setattr(F, "v0_replicate", real)
    calls = []

    def boom(n, th, s):
        calls.append(n)
        raise RuntimeError("injected")

    monkeypatch.setattr(F, "generate_p0", boom)
    with pytest.raises(RuntimeError):
        run_test(tmp_path, "boom")
    assert len(calls) == 1
    out = tmp_path / "boom"
    assert not (out / F.SUMS_FILE).exists()
    assert json.loads((out / F.EXECUTION_FILE).read_bytes())["status"] == "STOP"


# --- T9 -------------------------------------------------------------------------------------------------------------

def test_t09_computation_failure(tmp_path, monkeypatch):
    reps, levels = 30, F.holm_levels(2)
    a, b = F.axis_a_thresholds(reps, levels), F.axis_b_threshold(reps)
    real = F.log_upper_tail
    monkeypatch.setattr(F, "log_upper_tail", lambda *args: float("nan"))
    with pytest.raises(F.ComputationFailure):
        F.verify_thresholds(reps, a, levels, b)
    monkeypatch.setattr(F, "log_upper_tail", lambda *args: real(*args) * 1.001)
    with pytest.raises(F.ComputationFailure):
        F.verify_thresholds(reps, a, levels, b)
    with pytest.raises(F.ComputationFailure):
        run_test(tmp_path)
    out = tmp_path / "run"
    assert not (out / F.SUMS_FILE).exists() and not (out / "cells.json").exists()
    assert json.loads((out / F.EXECUTION_FILE).read_bytes())["code"] == "COMPUTATION_FAILURE"


# --- T10 ------------------------------------------------------------------------------------------------------------

def test_t10_cp_bisection_stop_rule():
    cp = F.cp_interval(40, 3)
    assert cp["status"] == "CONVERGED" and 0.0 < cp["lower"] < 3 / 40 < cp["upper"] < 1.0
    assert abs(F.log_upper_tail(40, cp["lower"], 3) - 0.025) < 1e-4
    assert abs(F.log_lower_tail(40, cp["upper"], 3) - 0.025) < 1e-4
    assert F.cp_interval(40, 0)["lower"] == 0.0 and F.cp_interval(40, 40)["upper"] == 1.0
    assert F.cp_interval(40, 3, max_iter=5)["status"] == "CP_NOT_CONVERGED"


# --- T11 ------------------------------------------------------------------------------------------------------------

def test_t11_worker_count_does_not_change_result_files(tmp_path):
    assert run_test(tmp_path, "w1", workers=1) == run_test(tmp_path, "w2", workers=2)
    one, two = tmp_path / "w1", tmp_path / "w2"
    for name in F.RESULT_FILES + (F.SUMS_FILE,):
        assert (one / name).read_bytes() == (two / name).read_bytes(), name
    assert sorted(os.listdir(one)) == sorted(F.RESULT_FILES + (F.SUMS_FILE, F.EXECUTION_FILE))
    lines = (one / F.SUMS_FILE).read_text(encoding="ascii").splitlines()
    assert [line.split("  ")[1] for line in lines] == list(F.RESULT_FILES)
    for line in lines:
        digest, name = line.split("  ")
        assert hashlib.sha256((one / name).read_bytes()).hexdigest() == digest
    for name in F.RESULT_FILES:
        text = (one / name).read_text(encoding="ascii")
        assert str(tmp_path.name) not in text and "workers" not in text
    assert json.loads((two / F.EXECUTION_FILE).read_bytes())["workers"] == 2
    manifest = (one / "manifest.json").read_bytes()
    assert b"cells.json" not in manifest and b"SHA256SUMS" not in manifest
    assert len(json.loads(manifest)["targets_getsource_sha256"]) == 8


# --- T12 ------------------------------------------------------------------------------------------------------------

def _git_blob_id(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def test_t12_source_blobs_atomic_writes_and_partial_output(tmp_path, monkeypatch):
    for rel, blob in F.EXPECTED_SOURCE_BLOBS.items():
        assert _git_blob_id(REPO / rel) == blob, rel
    real = atomic.atomic_write_bytes
    calls = []

    def spy(path, data):
        calls.append(Path(path).name)
        return real(path, data)

    monkeypatch.setattr(atomic, "atomic_write_bytes", spy)
    run_test(tmp_path)
    assert calls == list(F.RESULT_FILES) + [F.EXECUTION_FILE, F.SUMS_FILE]

    def fail_on_cells(path, data):
        if Path(path).name == "cells.json":
            raise OSError("injected")
        return real(path, data)

    monkeypatch.setattr(atomic, "atomic_write_bytes", fail_on_cells)
    with pytest.raises(OSError):
        run_test(tmp_path, "partial")
    out = tmp_path / "partial"
    assert (out / "manifest.json").exists() and (out / "design.json").exists()
    assert not (out / "cells.json").exists() and not (out / F.SUMS_FILE).exists()
    monkeypatch.setattr(atomic, "atomic_write_bytes", real)
    bad = {"commit": PROV["commit"], "files": {**PROV["files"], "src/moneylab/research/stats.py": {
        "blob": "0" * 40, "sha256_lf": "0" * 64}}}
    with pytest.raises(F.StopRun) as err:
        run_test(tmp_path, "badblob", prov=bad)
    assert err.value.code == "SOURCE_BLOB_MISMATCH"
    with pytest.raises(FileExistsError):
        run_test(tmp_path, "run")


# --- §10 schemas (small TEST inputs, not the preregistered smoke or performance run) --------------------------------

def test_smoke_schema_records_structure_only(tmp_path):
    out = tmp_path / "smoke"
    F.smoke(out, cells=TEST_CELLS, reps=2, b=9)
    assert sorted(os.listdir(out)) == [F.SUMS_FILE, "smoke.json"]
    doc = json.loads((out / "smoke.json").read_bytes())
    assert set(doc) == {"schema", "study", "namespace", "cells", "all_structure_ok"}
    assert doc["schema"] == F.SMOKE_SCHEMA and doc["namespace"] == F.NS_TEST and doc["all_structure_ok"] is True
    assert all(set(row) == {"n", "theta", "completed", "structure_ok"} and row["completed"] == 2
               for row in doc["cells"])
    digest = hashlib.sha256((out / "smoke.json").read_bytes()).hexdigest()
    assert (out / F.SUMS_FILE).read_text(encoding="ascii") == f"{digest}  smoke.json\n"


def test_perf_schema_and_worker_rules(tmp_path, monkeypatch):
    monkeypatch.setattr(F.os, "cpu_count", lambda: 4)
    out = tmp_path / "perf"
    F.perf(out, 2, namespace=F.NS_TEST, reps=1, b=9)
    assert os.listdir(out) == ["perf.json"]
    doc = json.loads((out / "perf.json").read_bytes())
    assert set(doc) == {"schema", "study", "namespace", "measures", "per_rep_wall_seconds_mean_by_n", "W",
                        "parallel_efficiency"}
    assert [(m["label"], m["workers"]) for m in doc["measures"]] == [("M1", 1), ("M2", 2)]
    assert all(set(m) == {"label", "workers", "wall_seconds", "cpu_seconds_sum", "max_memory_bytes"}
               for m in doc["measures"])
    assert set(doc["per_rep_wall_seconds_mean_by_n"]) == {str(n) for n in F.N_VALUES}
    for workers in (None, 1, 4):
        with pytest.raises(F.StopRun):
            F.perf(tmp_path / "bad", workers, namespace=F.NS_TEST, reps=1, b=9)
    for cpu in (None, 2):
        monkeypatch.setattr(F.os, "cpu_count", lambda c=cpu: c)
        with pytest.raises(F.StopRun):
            F.perf(tmp_path / "bad", 2, namespace=F.NS_TEST, reps=1, b=9)
    assert not (tmp_path / "bad").exists()


# --- T12 source verification through the real git path (temporary repository, protected files untouched) -----------

def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), "-c", "core.autocrlf=false", "-c", "user.name=futval-test",
                    "-c", "user.email=futval-test@example.invalid", "-c", "commit.gpgsign=false", *args],
                   check=True, capture_output=True)


@pytest.fixture
def src_repo(tmp_path):
    """A temporary repository holding LF copies of the protected sources and stand-ins for the two new files."""
    root = tmp_path / "repo"
    for rel in F.SOURCE_FILES:
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if rel in F.EXPECTED_SOURCE_BLOBS:
            dst.write_bytes((REPO / rel).read_bytes().replace(b"\r\n", b"\n"))
        else:
            dst.write_bytes(f"# stand-in for {rel}\nVALUE = 1\n".encode("ascii"))
    _git(root, "init", "-q")
    _git(root, "add", "--", *F.SOURCE_FILES)
    _git(root, "commit", "-q", "-m", "init")
    return root, {rel: root / rel for rel in F.LOADED_SOURCES}


def test_t12_real_git_provenance_accepts_matching_sources(src_repo):
    root, loaded = src_repo
    prov = F.git_provenance(root, loaded)
    assert len(prov["commit"]) == 40
    assert set(prov["files"]) == set(F.SOURCE_FILES)
    for rel, blob in F.EXPECTED_SOURCE_BLOBS.items():
        assert prov["files"][rel]["blob"] == blob
    for rel in F.SOURCE_FILES:
        assert prov["files"][rel]["sha256_lf"] == hashlib.sha256((root / rel).read_bytes()).hexdigest()


def test_t12_crlf_working_copy_is_read_as_lf_but_lone_cr_is_not(src_repo):
    root, loaded = src_repo
    rel = "src/moneylab/research/v06/futval_v8_01.py"
    lf = (root / rel).read_bytes()
    (root / rel).write_bytes(lf.replace(b"\n", b"\r\n"))
    F.git_provenance(root, loaded)
    (root / rel).write_bytes(lf.replace(b"\n", b"\r", 1))
    with pytest.raises(F.StopRun) as err:
        F.git_provenance(root, loaded)
    assert err.value.code == "SOURCE_WORKTREE_MISMATCH"


@pytest.mark.parametrize("rel", F.SOURCE_FILES)
def test_t12_working_source_differing_from_head_is_refused(src_repo, rel):
    root, loaded = src_repo
    (root / rel).write_bytes((root / rel).read_bytes() + b"# changed after commit\n")
    with pytest.raises(F.StopRun) as err:
        F.git_provenance(root, loaded)
    assert err.value.code == "SOURCE_WORKTREE_MISMATCH"


def test_t12_head_source_differing_from_the_preregistered_blob_is_refused(src_repo):
    root, loaded = src_repo
    rel = "src/moneylab/research/stats.py"
    (root / rel).write_bytes((root / rel).read_bytes() + b"# committed change\n")
    _git(root, "add", "--", rel)
    _git(root, "commit", "-q", "-m", "change")
    with pytest.raises(F.StopRun) as err:
        F.git_provenance(root, loaded)
    assert err.value.code == "SOURCE_BLOB_MISMATCH"


@pytest.mark.parametrize("rel", F.LOADED_SOURCES)
def test_t12_module_loaded_from_another_location_is_refused(src_repo, tmp_path, rel):
    root, loaded = src_repo
    elsewhere = tmp_path / "other" / rel
    elsewhere.parent.mkdir(parents=True)
    elsewhere.write_bytes((root / rel).read_bytes())
    with pytest.raises(F.StopRun) as err:
        F.git_provenance(root, {**loaded, rel: elsewhere})
    assert err.value.code == "SOURCE_LOCATION_MISMATCH"
    with pytest.raises(F.StopRun):
        F.git_provenance(root, {k: v for k, v in loaded.items() if k != rel})


def test_t12_default_loaded_modules_are_the_imported_files():
    files = F._loaded_files()
    assert set(files) == set(F.LOADED_SOURCES)
    assert files["src/moneylab/research/v06/procedures.py"] == Path(P.__file__)
    assert files["src/moneylab/research/v06/futval_v8_01.py"] == Path(F.__file__)


def test_t12_run_refuses_before_any_statistics_or_result_write(src_repo, tmp_path, monkeypatch):
    root, loaded = src_repo
    (root / "tests/test_futval_v8_01.py").write_bytes(b"# edited test file\n")
    called = []
    monkeypatch.setattr(F, "seed_uniqueness", lambda *a, **k: called.append("seed"))
    monkeypatch.setattr(F, "generate_p0", lambda *a, **k: called.append("data"))
    monkeypatch.setattr(F, "_execute", lambda *a, **k: called.append("execute"))
    with pytest.raises(F.StopRun) as err:
        F.run(tmp_path / "out", namespace=F.NS_TEST, cells=TEST_CELLS, reps=6, b=19, source_root=root,
              loaded_sources=loaded)
    assert err.value.code == "SOURCE_WORKTREE_MISMATCH" and called == []
    assert os.listdir(tmp_path / "out") == [F.EXECUTION_FILE]
    assert json.loads((tmp_path / "out" / F.EXECUTION_FILE).read_bytes())["code"] == "SOURCE_WORKTREE_MISMATCH"


def test_t12_run_through_the_real_git_path_records_verified_sources(src_repo, tmp_path):
    root, loaded = src_repo
    F.run(tmp_path / "out", namespace=F.NS_TEST, cells=TEST_CELLS, reps=6, b=19, source_root=root,
          loaded_sources=loaded)
    manifest = json.loads((tmp_path / "out" / "manifest.json").read_bytes())
    assert manifest["code"] == F.git_provenance(root, loaded)
    with pytest.raises(ValueError):
        F.run(tmp_path / "x", source_root=root)
    with pytest.raises(ValueError):
        F.run(tmp_path / "x", provenance=PROV)
    assert not (tmp_path / "x").exists()
