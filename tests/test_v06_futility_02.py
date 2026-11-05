"""BT4-FUTILITY-02 (Work Order D0-D13, TEST_GATES T1-T10): synthetic FUTDIAG-TEST fixtures only.

No test reads SOURCE_OUTPUT_ROOT or any G7 output; git is a fake runner, and every run directory is built in tmp_path.
"""

import hashlib
import io
import json
import math
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import replace
from pathlib import Path as FsPath

import pytest

from moneylab.research.v06 import futility_02 as f2
from moneylab.research.v06 import futility_diag as fd

REPO = FsPath(f2.__file__).resolve().parents[4]
HEAD = "e" * 40
MARKER = "MARKER-7f3c-must-not-leak"
E1 = fd.e1_cell(0.73, 0.70 / math.sqrt(365))
P0 = fd.p0_cell()
NS = "FUTDIAG-TEST"
V4_YEARS = 40


def _spec(**over):
    kw = dict(mode="core", code_sha="a" * 40, code_tree="b" * 40, config_sha256="c" * 64, prereg_sha256="d" * 64,
              cells=list(fd.CORE_CELLS), windows=list(fd.WINDOWS), rules=list(fd.RULES), reps=5, bootstrap=9,
              unit_size=2)
    kw.update(over)
    return fd.build_run_spec(**kw)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


@pytest.fixture(scope="module")
def source(tmp_path_factory):
    """A FUTDIAG-TEST stand-in for SOURCE_OUTPUT_ROOT: one-cell CORE runs, a pilot with G6, V-4 (40 years),
    calibration, UDR and lock files, all under the Work Order names."""
    root = tmp_path_factory.mktemp("source") / "research_v06_futility_diag"
    root.mkdir()
    cal = fd.build_calibration(fd.TEST_FIXTURE, fd.fixture_e1(), fd.sigma_calibration(3, NS), fd.fixture_identity())
    cal_bytes = fd.calibration_bytes(cal)
    cal_sha = _sha(cal_bytes)
    prov = fd.calibration_provenance(cal, cal_sha)
    for run, cell in ((f2.E1_RUN, E1), (f2.P0_RUN, P0)):
        spec = _spec(cells=[cell.name])
        fd.run_units(root / run, spec, fd.build_run_inputs(spec, [cell], NS, prov), workers=1)
    pspec = _spec(mode="pilot", windows=["conf", "f12", "f36"], reps=6, unit_size=3)
    fd.run_units(root / f2.PILOT_RUN, pspec,
                 fd.build_run_inputs(pspec, [fd.e1_cell(fd.E_CAL, fd.P0_DAILY_SD), P0], NS, prov), workers=1)
    fd.write_g6(root / f2.PILOT_RUN, cal, cal_sha)
    fd.write_v4_run(root / f2.V4_RUN, {"git_head": "1" * 40}, [], years=V4_YEARS)
    (root / f2.CAL_RUN).mkdir()
    (root / f2.CAL_RUN / fd.CALIBRATION_FILE).write_bytes(cal_bytes)
    (root / fd.UDR_DIR).mkdir()
    (root / fd.UDR_DIR / f2.UDR_FILE).write_bytes(b"udr\n")
    (root / fd.LOCK_DIR).mkdir()
    (root / fd.LOCK_DIR / "000001.lock").write_bytes(b"lock\n")
    (root / fd.LOCK_DIR / f2.LOCK_RELEASED).write_bytes(b"released\n")
    rows = {rel: _sha((root / rel).read_bytes()) for rel in f2.DATA_ROWS}
    return root, rows, cal_sha


def fake_git(source_root_wt, *, dirty=False, source_dirty=False, head=HEAD, branch=f2.F2Config.target_branch,
             ancestor=True, changed=("tests/test_v06_futility_02.py",), ignored=True):
    def run(cwd, args):
        target = os.path.normcase(str(cwd)) == os.path.normcase(str(REPO))
        a = list(args)
        if a == ["rev-parse", "HEAD"]:
            return 0, ((head if target else f2.SOURCE_CODE_SHA) + "\n").encode()
        if a == ["rev-parse", "--abbrev-ref", "HEAD"]:
            return 0, ((branch if target else f2.F2Config.source_branch) + "\n").encode()
        if a == ["status", "--porcelain"]:
            return 0, b" M x\n" if (dirty if target else source_dirty) else b""
        if a[:2] == ["cat-file", "blob"]:
            p = REPO / a[2].split(":", 1)[1]
            return (0, fd._lf(p.read_bytes())) if p.is_file() else (128, b"")
        if a[:2] == ["merge-base", "--is-ancestor"]:
            return (0 if ancestor else 1), b""
        if a[:2] == ["diff", "--name-only"]:
            return 0, "".join(f"{c}\n" for c in changed).encode()
        if a[:2] == ["check-ignore", "-q"]:
            return (0 if ignored else 1), b""
        return 1, b""
    return run


def _cfg(source, tmp_path, **over):
    root, rows, cal_sha = source
    new_root = tmp_path / "research_v06_futility_02"
    new_root.mkdir(exist_ok=True)
    code_rows = {p: f2.lf_sha256(REPO / p) for p in f2.CODE_ROWS}
    contract_rows = {p: f2.lf_sha256(REPO / p) for p in f2.CONTRACT_ROWS}
    kw = dict(target_worktree=REPO, source_worktree=FsPath("SOURCE-WT"), source_output_root=root,
              new_output_root=new_root, module_root=REPO / "src", python_version=platform.python_version(),
              platform=sys.platform, code_rows=code_rows, contract_rows=contract_rows, data_rows=rows,
              calibration_sha256=cal_sha, v4_years=V4_YEARS, expected_n=f2.expected_return_count(V4_YEARS),
              git=fake_git(None))
    kw.update(over)
    return replace(f2.DEFAULT_CONFIG, **kw)


def _attempt(cfg, prefix, n=1, head=HEAD):
    d = cfg.new_output_root / f"{prefix}-{head[:12]}-a{n}"
    d.mkdir()
    (d / f2.STDERR_FILE).write_bytes(b"")
    return d


def _main(argv, cfg):
    buf = io.StringIO()
    rc = f2.main(argv, cfg, buf)
    lines = buf.getvalue().splitlines()
    assert len(lines) == 1 and buf.getvalue().endswith("\n")
    return rc, json.loads(lines[0]), buf.getvalue()


def _g5_argv(d, head=HEAD, python=None):
    return ["verify-inputs", "--out", str(d), "--expected-python", python or sys.executable, "--expected-head", head]


def _g6_argv(d, g5, head=HEAD):
    return ["analyze", "--out", str(d), "--expected-python", sys.executable, "--expected-head", head,
            "--input-verification", str(g5)]


@pytest.fixture(scope="module")
def completed(source, tmp_path_factory):
    """G5 then G6 on the synthetic tree; returns the config and both attempt directories."""
    cfg = _cfg(source, tmp_path_factory.mktemp("done"))
    g5 = _attempt(cfg, "g5-input")
    rc5, out5, _ = _main(_g5_argv(g5), cfg)
    g6 = _attempt(cfg, "g6-analysis")
    rc6, out6, _ = _main(_g6_argv(g6, g5), cfg)
    return cfg, g5, g6, (rc5, out5), (rc6, out6)


# --- T2 / T3: end to end and the unchanged primary decision ------------------------------------------------------

def test_t2_end_to_end_complete(completed):
    cfg, g5, g6, (rc5, out5), (rc6, out6) = completed
    assert (rc5, out5["status"], out5["stage"]) == (0, "COMPLETE", "verify-inputs")
    assert (rc6, out6["status"], out6["regeneration"]) == (0, "COMPLETE", "MATCH")
    assert sorted(p.name for p in g5.iterdir()) == ["SHA256SUMS", "input_verification.json", "stderr.bin"]
    assert sorted(p.name for p in g6.iterdir()) == ["SHA256SUMS", "analysis.json", "stderr.bin"]
    a = json.loads((g6 / "analysis.json").read_bytes())
    assert set(a) == {"schema_version", "evidence", "classification", "provenance", "input_verification_sha256",
                      "regeneration", "primary", "rd", "alpha", "pd4", "v4_k20", "lag1", "conf_ratio"}
    assert a["evidence"] == "SYNTHETIC / NOT_EVIDENCE" and a["classification"]["independent_confirmation"] is False
    assert a["classification"]["research_classification"] == "POST_HOC_DIAGNOSTIC"
    assert a["input_verification_sha256"] == _sha((g5 / "input_verification.json").read_bytes())
    assert a["provenance"]["analysis_code_sha"] == HEAD and a["provenance"]["source_code_sha"] == f2.SOURCE_CODE_SHA
    assert (g6 / "analysis.json").read_bytes() == fd.canonical_bytes(a)


def test_t3_primary_equals_decision_summary(completed, source):
    cfg, _, g6, _, _ = completed
    root, _, cal_sha = source
    by_cell = f2.read_core_records(cfg)
    v4 = fd.verify_v4_run(root / f2.V4_RUN)["v4"]
    cal, _ = fd.load_calibration(root / f2.CAL_RUN / fd.CALIBRATION_FILE, cal_sha)
    want = fd.decision_summary(by_cell, v4, cal["sigma"])
    a = json.loads((g6 / "analysis.json").read_bytes())
    assert fd.canonical_bytes(a["primary"]) == fd.canonical_bytes(want)
    assert sorted(a["primary"]["labels"]) == ["V-1", "V-2", "V-3", "V-4", "V-8"]
    assert sorted(a["primary"]["holm"]["p"]) == ["V-1", "V-2", "V-3", "V-4", "V-8"]   # Holm family exactly 5


def test_t2_stdout_has_no_result_values(completed):
    _, _, _, (_, out5), (_, out6) = completed
    allowed = {"status", "stage", "elapsed_s", "warnings_count", "python_executable", "output_dir", "output_sha256s",
               "regeneration"}
    assert set(out5) <= allowed and set(out6) <= allowed
    assert set(out6["output_sha256s"]) == {"analysis.json", "SHA256SUMS"}


def test_t2_rerun_in_same_directory_stops(completed):
    cfg, g5, g6, _, _ = completed
    rc, out, _ = _main(_g6_argv(g6, g5), cfg)
    assert (rc, out["failure_code"]) == (2, "OUTPUT_DIR_NOT_FRESH")


# --- T4: RD, alpha, PD-4 ----------------------------------------------------------------------------------------

def _rec(cell, rep, window, *, d=0, sd=False, v0=1.0, v0d=1.0, v60=1.0, lo=1.0, hi=1.0):
    return {"cell": cell, "rep": rep, "window": window, "sd": sd,
            "variants": {"V0": {"p": v0}, "V0d": {"p": v0d}, "V0b60": {"p": v60},
                         "S1": {"p_lo": lo, "p_hi": hi, "d": d}}}


def _by_cell(e1_f12, n=None):
    n = len(e1_f12) if n is None else n
    e1 = []
    for i in range(n):
        for w in fd.WINDOWS:
            e1.append(e1_f12[i] if w == "f12" else _rec(fd.E1_CELL, i, w))
    p0 = [_rec(fd.P0_CELL, i, w) for i in range(n) for w in fd.WINDOWS]
    return {fd.E1_CELL: e1, fd.P0_CELL: p0}


def test_t4_rd_distribution_counts_quantiles_and_sd():
    ds = [0, 0, 3, 5, 5, 1, 0, 2, 9, 4]
    recs = [_rec(fd.E1_CELL, i, "f12", d=d) for i, d in enumerate(ds)]
    recs.append(_rec(fd.E1_CELL, 10, "f12", d=0, sd=True))
    out = f2.rd_distribution(_by_cell(recs), 9)
    assert (out["reps_R"], out["sd_count"], out["n_nonsd"], out["status"]) == (11, 1, 10, "OK")
    assert out["counts"] == [[0, 3], [1, 1], [2, 1], [3, 1], [4, 1], [5, 2], [9, 1]]
    s = out["summary"]
    assert s["share_d0"] == 0.3 and s["mean"] == sum(ds) / 10 and s["max"] == 9
    assert (s["q50"], s["q90"], s["q99"]) == (2, 5, 9)          # nearest rank on 0 0 0 1 2 3 4 5 5 9


def test_t4_rd_empty_and_invalid():
    out = f2.rd_distribution(_by_cell([_rec(fd.E1_CELL, 0, "f12", sd=True)]), 9)
    assert (out["status"], out["summary"], out["n_nonsd"]) == ("EMPTY", None, 0)
    for bad in (10, -1, True, 1.0):
        with pytest.raises(f2.F2Stop) as e:
            f2.rd_distribution(_by_cell([_rec(fd.E1_CELL, 0, "f12", d=bad)]), 9)
        assert e.value.code == "RECORD_INVALID"


def test_t4_nearest_rank_is_exact():
    assert f2._quantile(list(range(10)), "0.9") == 8            # ceil(0.9 * 10) = 9 exactly, not 10
    assert f2._quantile(list(range(100)), "0.99") == 98


def test_t4_alpha_contrasts_at_both_alphas():
    recs = [_rec(fd.E1_CELL, i, "f12", v0=p, v0d=1.0) for i, p in enumerate([0.02, 0.05, 0.09, 0.5])]
    out = f2.alpha_contrasts(_by_cell(recs))
    assert [o["alpha"] for o in out] == [0.025, 0.10]
    r025, r010 = out[0]["rates"][fd.E1_CELL]["f12"]["V0"], out[1]["rates"][fd.E1_CELL]["f12"]["V0"]
    assert (r025["rate"], r010["rate"]) == (0.25, 0.75)
    assert [c["name"] for c in out[0]["contrasts"]] == list(fd.CONTRASTS)
    v2 = next(c for c in out[1]["contrasts"] if c["name"] == "V-2")
    assert (v2["n10"], v2["n01"]) == (3, 0) and "u_d" not in v2 and "eff" not in v2
    assert set(v2) == {"name", "d_hat", "se", "n10", "n01", "reason", "p_one_sided_unadjusted"}


def test_t4_pd4_subset_and_empty():
    recs = [_rec(fd.E1_CELL, 0, "f12", sd=True, v0d=0.001), _rec(fd.E1_CELL, 1, "f12", v0=0.01),
            _rec(fd.E1_CELL, 2, "f12")]
    out = f2.pd4_sensitivity(_by_cell(recs))
    assert (out["R_total"], out["R_sd"], out["R_subset"], out["status"]) == (3, 1, 2, "OK")
    assert out["contrast"]["n10"] == 1 and "u_d" in out["contrast"]
    empty = f2.pd4_sensitivity(_by_cell([_rec(fd.E1_CELL, 0, "f12", sd=True)]))
    assert (empty["status"], empty["contrast"]) == ("NOT_COMPUTABLE_EMPTY_SUBSET", None)


# --- T5: regeneration and K = 20 --------------------------------------------------------------------------------

def test_t5_regeneration_equals_v4_evaluation():
    ev, rets = f2.regenerate_v4(3, ("FUTDIAG-TEST", "v4eval-test"), fd.E_CAL)
    want = fd.v4_evaluation(3, ("FUTDIAG-TEST", "v4eval-test"))
    assert {k: ev[k] for k in want} == want and ev["seed"] == fd.explicit_seed(["FUTDIAG-TEST", "v4eval-test"])
    assert len(rets) == f2.expected_return_count(3) == sum(ev["batch_lengths"])


def test_t5_code_derived_lengths():
    n = f2.expected_return_count(4000)
    assert n == 1_459_876 and n % 40 == 36 and n % 20 == 16
    assert f2.expected_batch_lengths(n, 40) == [36_497] * 36 + [36_496] * 4
    assert f2.expected_batch_lengths(n, 20) == [72_994] * 16 + [72_993] * 4


def test_t5_canonical_comparison_has_no_tolerance():
    assert fd.canonical_bytes({"x": -0.0}) != fd.canonical_bytes({"x": 0.0})
    assert fd.canonical_bytes({"x": 0.1 + 0.2}) != fd.canonical_bytes({"x": 0.3})


def test_t5_regeneration_mismatch_stops_before_any_analysis(completed, source, tmp_path, monkeypatch):
    cfg = _cfg(source, tmp_path)
    shutil.copytree(completed[1], cfg.new_output_root / completed[1].name)
    g6 = _attempt(cfg, "g6-analysis")
    real = f2.regenerate_v4

    def drifted(*a):
        ev, rets = real(*a)
        return {**ev, "sr_eval": ev["sr_eval"] + 1e-15}, rets
    monkeypatch.setattr(f2, "regenerate_v4", drifted)
    for name in ("read_core_records", "primary_labels", "v4_k20", "lag1", "conf_ratio"):
        monkeypatch.setattr(f2, name, lambda *a, _n=name: (_ for _ in ()).throw(AssertionError(_n)))
    rc, out, _ = _main(_g6_argv(g6, cfg.new_output_root / completed[1].name), cfg)
    assert (rc, out["failure_code"], out["stage"]) == (2, "REGEN_MISMATCH", "regeneration")
    assert sorted(p.name for p in g6.iterdir()) == ["stderr.bin"]


def test_t5_length_mismatch_stops(completed, source, tmp_path):
    cfg = _cfg(source, tmp_path, expected_n=f2.expected_return_count(V4_YEARS) + 1)
    shutil.copytree(completed[1], cfg.new_output_root / completed[1].name)
    g6 = _attempt(cfg, "g6-analysis")
    rc, out, _ = _main(_g6_argv(g6, cfg.new_output_root / completed[1].name), cfg)
    assert (rc, out["failure_code"]) == (2, "LENGTH_MISMATCH")


def test_t5_k20_output_and_no_label(completed):
    a = json.loads((completed[2] / "analysis.json").read_bytes())
    k = a["v4_k20"]
    n = f2.expected_return_count(V4_YEARS)
    assert (k["k"], k["df"], k["batch_lengths"]) == (20, 19, f2.expected_batch_lengths(n, 20))
    assert set(k) == {"k", "df", "batch_lengths", "se", "t_quantile", "delta_lower", "delta_upper", "p_one_sided",
                      "se_ratio_vs_k40"}
    assert k["t_quantile"] == fd.t_ppf(1 - fd.V4_GAMMA_DELTA, 19)
    assert a["regeneration"]["k40_batch_lengths"] == f2.expected_batch_lengths(n, 40)


# --- T6 / T7: lag-1 and conf ratio ------------------------------------------------------------------------------

def test_t6_acf1_known_constant_nonfinite_short():
    assert f2.acf1([1.0, 2.0, 3.0, 4.0]) == pytest.approx(0.25, abs=1e-15)
    assert f2.acf1([0.1, 0.1, 0.1]) is None
    for bad, code in (([1.0, float("nan"), 2.0], "NONFINITE"), ([1.0, float("inf"), 2.0], "NONFINITE"),
                      ([1.0, 2.0], "LENGTH_MISMATCH")):
        with pytest.raises(f2.F2Stop) as e:
            f2.acf1(bad)
        assert e.value.code == code
    out = f2.lag1([0.3] * 40, [float(i) for i in range(20)])
    assert [(o["k"], o["status"], o["batch_source"]) for o in out] == [(40, "UNDEFINED_CONSTANT", "v4.json"),
                                                                        (20, "OK", "regenerated")]


def _v4b(dh, dl, du, s_lo=0.2, s_hi=0.3):
    return {"delta_hat": dh, "delta_lower": dl, "delta_upper": du, "sigma_L": s_lo, "sigma_U": s_hi}


def test_t7_conf_ratio_values_and_flags():
    out = f2.conf_ratio(_v4b(0.0, -0.01, 0.01))
    assert out["denominator"] == 0.066 and all(abs(p["ratio"]) < 1e-12 for p in out["point_range"])
    assert "APPROX_OUT_OF_RANGE" not in out["flags"] and "RATIO_ABOVE_ONE" not in out["flags"]
    big = f2.conf_ratio(_v4b(-0.2, -0.3, -0.1))                     # Delta / sigma_L = -1: DeltaRej > 0.066
    assert "RATIO_ABOVE_ONE" in big["flags"] and "APPROX_OUT_OF_RANGE" in big["flags"]
    p = big["point_range"][0]
    assert p["delta_rej"] == fd.delta_rej(-0.2, 0.2) and p["ratio"] == p["delta_rej"] / 0.066
    assert p["delta_rej_prime"] == pytest.approx(0.116 - f2._N.cdf(f2._N.inv_cdf(0.116) - 1.0), abs=1e-15)
    neg = f2.conf_ratio(_v4b(0.05, 0.0, 0.1))
    assert "RATIO_NEGATIVE" in neg["flags"] and neg["point_ratio_max"] < 0
    lo, hi = fd.rect_extrema(0.0, 0.1, 0.2, 0.3)
    assert (neg["descriptive_bounds"]["ratio_min"], neg["descriptive_bounds"]["ratio_max"]) == (lo / 0.066, hi / 0.066)
    assert "causal" in out["interpretation"]


def test_t7_conf_ratio_stops():
    for v4b, code in ((_v4b(0.0, 0.0, 0.0, s_lo=0.0), "SIGMA_NONPOSITIVE"),
                      (_v4b(0.0, 0.0, 0.0, s_hi=-1.0), "SIGMA_NONPOSITIVE"),
                      (_v4b(float("nan"), 0.0, 0.0), "NONFINITE")):
        with pytest.raises(f2.F2Stop) as e:
            f2.conf_ratio(v4b)
        assert e.value.code == code


# --- T8: identity and input verification ------------------------------------------------------------------------

def test_t8_lf_rule(tmp_path):
    body = b"line one\nline two\n"
    lf, crlf, changed, lone = (tmp_path / n for n in ("lf", "crlf", "changed", "lone"))
    lf.write_bytes(body)
    crlf.write_bytes(body.replace(b"\n", b"\r\n"))
    changed.write_bytes(b"line one\nline 2wo\n")
    lone.write_bytes(b"line one\rline two\n")
    want = _sha(body)
    assert f2.lf_sha256(lf) == want and f2.lf_sha256(crlf) == want
    assert f2.lf_sha256(changed) != want and f2.lf_sha256(lone) != want     # a lone CR is never removed
    assert crlf.read_bytes() == body.replace(b"\n", b"\r\n")               # the file is not changed


@pytest.mark.parametrize("case", ["python", "platform", "interpreter", "head", "dirty", "branch", "module",
                                  "code_blob", "ancestry", "changed", "missing_head", "missing_python", "bad_head"])
def test_t8_identity_failures(case, source, tmp_path, monkeypatch):
    cfg = _cfg(source, tmp_path)
    d = _attempt(cfg, "g5-input")
    argv = _g5_argv(d)
    if case == "python":
        monkeypatch.setattr(f2.platform, "python_version", lambda: "3.14.7")
    elif case == "platform":
        cfg = replace(cfg, platform="linux-other")
    elif case == "interpreter":
        argv = _g5_argv(d, python=str(tmp_path / "other_python.exe"))
    elif case == "head":
        argv = _g5_argv(d, head="f" * 40)
    elif case == "dirty":
        cfg = replace(cfg, git=fake_git(None, dirty=True))
    elif case == "branch":
        cfg = replace(cfg, git=fake_git(None, branch="feature/other"))
    elif case == "module":
        cfg = replace(cfg, module_root=tmp_path / "elsewhere" / "src")
    elif case == "code_blob":
        cfg = replace(cfg, code_rows={**cfg.code_rows, "src/moneylab/research/stats.py": "0" * 64})
    elif case == "ancestry":
        cfg = replace(cfg, git=fake_git(None, ancestor=False))
    elif case == "changed":
        cfg = replace(cfg, git=fake_git(None, changed=("src/moneylab/research/v06/futility_diag.py",)))
    elif case == "missing_head":
        argv = argv[:-2]
    elif case == "missing_python":
        argv = argv[:3] + argv[5:]
    elif case == "bad_head":
        argv = argv[:-1] + ["E" * 40]
    rc, out, text = _main(argv, cfg)
    assert (rc, out["status"], out["failure_code"]) == (2, "STOP", "IDENTITY_FAILED")
    assert sorted(p.name for p in d.iterdir()) == ["stderr.bin"]


ERRATA_001_PATHS = ("docs/tasks/BT4-FUTILITY-02/WORK_ORDER.md", "docs/tasks/BT4-FUTILITY-02/ERRATA-001.md",
                    "src/moneylab/research/v06/futility_02.py", "tests/test_v06_futility_02.py")


def test_t8_allowed_files_are_the_errata_001_paths():
    assert f2.ALLOWED_FILES == ERRATA_001_PATHS


@pytest.mark.parametrize("changed,ok", [(ERRATA_001_PATHS, True), (("docs/tasks/BT4-FUTILITY-02/ERRATA-001.md",), True),
                                        (ERRATA_001_PATHS + ("docs/tasks/BT4-FUTILITY-02/ERRATA-002.md",), False)])
def test_t8_changed_paths_against_errata_001(changed, ok, source, tmp_path):
    cfg = _cfg(source, tmp_path, git=fake_git(None, changed=changed))
    d = _attempt(cfg, "g5-input")
    rc, out, _ = _main(_g5_argv(d), cfg)
    if ok:
        assert (rc, out["status"]) == (0, "COMPLETE")
    else:
        assert (rc, out["status"], out["failure_code"]) == (2, "STOP", "IDENTITY_FAILED")


@pytest.mark.parametrize("case,code", [("source_dirty", "SOURCE_WORKTREE_CHANGED"), ("data_row", "INPUT_HASH_MISMATCH"),
                                       ("contract_row", "INPUT_HASH_MISMATCH"), ("not_ignored", "OUTPUT_NOT_IGNORED"),
                                       ("calibration", "CALIBRATION_MISMATCH")])
def test_t8_input_failures(case, code, source, tmp_path):
    cfg = _cfg(source, tmp_path)
    if case == "source_dirty":
        cfg = replace(cfg, git=fake_git(None, source_dirty=True))
    elif case == "data_row":
        cfg = replace(cfg, data_rows={**cfg.data_rows, f"{f2.V4_RUN}/v4.json": "0" * 64})
    elif case == "contract_row":
        cfg = replace(cfg, contract_rows={**cfg.contract_rows, "configs/bt4_futility_diag.toml": "0" * 64})
    elif case == "not_ignored":
        cfg = replace(cfg, git=fake_git(None, ignored=False))
    elif case == "calibration":
        cfg = replace(cfg, calibration_sha256="0" * 64)
    d = _attempt(cfg, "g5-input")
    rc, out, _ = _main(_g5_argv(d), cfg)
    assert (rc, out["failure_code"]) == (2, code)


def test_t8_g8a_udr_and_lock(source, tmp_path):
    root = tmp_path / "copy"
    shutil.copytree(source[0], root)
    base = _cfg(source, tmp_path, source_output_root=root)
    for mutate, code in ((lambda: (root / "g8a-x").mkdir(), "G8A_DIR_PRESENT"),
                         (lambda: (root / fd.UDR_DIR / "000002-X.json").write_bytes(b"x"), "UDR_OR_LOCK_INVALID")):
        mutate()
        d = _attempt(base, "g5-input", n=len(list(base.new_output_root.iterdir())) + 1)
        rc, out, _ = _main(_g5_argv(d), base)
        assert (rc, out["failure_code"]) == (2, code)
        shutil.rmtree(root / "g8a-x") if code == "G8A_DIR_PRESENT" else None


# --- T9: output control -----------------------------------------------------------------------------------------

G5_STAGES = [("check_identity", "IDENTITY_FAILED"), ("check_output_ignored", "OUTPUT_NOT_IGNORED"),
             ("check_output_fresh", "OUTPUT_DIR_NOT_FRESH"), ("check_source_worktree", "SOURCE_WORKTREE_CHANGED"),
             ("check_input_hashes", "INPUT_HASH_MISMATCH"), ("check_runs", "VERIFY_RUN_FAILED"),
             ("check_v4", "VERIFY_V4_FAILED"), ("check_calibration", "CALIBRATION_MISMATCH"),
             ("check_udr_lock", "UDR_OR_LOCK_INVALID"), ("check_g8a_absent", "G8A_DIR_PRESENT"),
             ("write_outputs", "WRITE_FAILED")]
G6_STAGES = [("check_input_verification", "INPUT_HASH_MISMATCH"), ("load_v4", "VERIFY_V4_FAILED"),
             ("regeneration_check", "REGEN_MISMATCH"), ("load_calibration", "CALIBRATION_MISMATCH"),
             ("read_core_records", "RECORD_INVALID"), ("primary_labels", "RECORD_INVALID"),
             ("rd_distribution", "RECORD_INVALID"), ("alpha_contrasts", "RECORD_INVALID"),
             ("pd4_sensitivity", "RECORD_INVALID"), ("v4_k20", "SE_ZERO"), ("lag1", "NONFINITE"),
             ("conf_ratio", "SIGMA_NONPOSITIVE"), ("write_outputs", "WRITE_FAILED")]


def _raiser(exc):
    def f(*a, **k):
        raise exc
    return f


def _g6_setup(completed, source, tmp_path):
    cfg = _cfg(source, tmp_path)
    g5 = cfg.new_output_root / completed[1].name
    shutil.copytree(completed[1], g5)
    return cfg, g5, _attempt(cfg, "g6-analysis")


@pytest.mark.parametrize("fn,code", G5_STAGES)
@pytest.mark.parametrize("exc_type", [RuntimeError, ValueError])
def test_t9_g5_failure_code_by_stage(fn, code, exc_type, source, tmp_path, monkeypatch, capsys):
    cfg = _cfg(source, tmp_path)
    d = _attempt(cfg, "g5-input")
    monkeypatch.setattr(f2, fn, _raiser(exc_type(f"{MARKER} {exc_type.__name__}")))
    rc, out, text = _main(_g5_argv(d), cfg)
    assert (rc, out["status"], out["failure_code"]) == (2, "STOP", code)
    assert MARKER not in text and capsys.readouterr() == ("", "")


@pytest.mark.parametrize("fn,code", G6_STAGES)
def test_t9_g6_failure_code_by_stage(fn, code, completed, source, tmp_path, monkeypatch, capsys):
    cfg, g5, g6 = _g6_setup(completed, source, tmp_path)
    monkeypatch.setattr(f2, fn, _raiser(fd.StopImplementation(MARKER)))
    rc, out, text = _main(_g6_argv(g6, g5), cfg)
    assert (rc, out["failure_code"]) == (2, code)
    assert MARKER not in text and capsys.readouterr() == ("", "")
    assert not (g6 / "analysis.json").exists() or fn == "write_outputs"


@pytest.mark.parametrize("code", ["LENGTH_MISMATCH", "NONFINITE", "SE_ZERO", "SIGMA_NONPOSITIVE", "RECORD_INVALID"])
def test_t9_explicit_code_wins_over_stage(code, completed, source, tmp_path, monkeypatch):
    cfg, g5, g6 = _g6_setup(completed, source, tmp_path)
    monkeypatch.setattr(f2, "regeneration_check", _raiser(f2.F2Stop(code, MARKER)))
    rc, out, text = _main(_g6_argv(g6, g5), cfg)
    assert (rc, out["failure_code"]) == (2, code) and MARKER not in text


def test_t9_exception_outside_a_stage_is_internal_error(source, tmp_path, monkeypatch):
    cfg = _cfg(source, tmp_path)
    d = _attempt(cfg, "g5-input")
    real = f2._g
    monkeypatch.setattr(f2, "_g", lambda name: _raiser(RuntimeError(MARKER))() if name == "check_runs" else real(name))
    rc, out, text = _main(_g5_argv(d), cfg)
    assert (rc, out["failure_code"], out["stage"]) == (2, "INTERNAL_ERROR", "after-input-hashes")
    assert MARKER not in text


def test_t9_warnings_are_counted_not_printed(source, tmp_path, monkeypatch, capsys):
    import warnings
    cfg = _cfg(source, tmp_path)
    d = _attempt(cfg, "g5-input")
    real = f2.check_g8a_absent

    def warn(c):
        warnings.warn(MARKER, UserWarning)
        return real(c)
    monkeypatch.setattr(f2, "check_g8a_absent", warn)
    rc, out, text = _main(_g5_argv(d), cfg)
    assert (rc, out["warnings_count"]) == (0, 1) and MARKER not in text and capsys.readouterr() == ("", "")


@pytest.mark.parametrize("argv", [[], ["analyze"], ["verify-inputs", "--bogus", MARKER],
                                  ["verify-inputs", "--out", "x", "--expected-python", "p", "--expected-head", MARKER]])
def test_t9_subprocess_one_json_line_and_empty_stderr(argv):
    env = {**os.environ, "PYTHONPATH": str(REPO / "src")}
    r = subprocess.run([sys.executable, "-m", "moneylab.research.v06.futility_02", *argv], capture_output=True,
                       cwd=str(REPO), env=env, timeout=120)
    assert r.returncode == 2 and r.stderr == b""
    lines = r.stdout.decode("ascii").splitlines()
    assert len(lines) == 1
    out = json.loads(lines[0])
    assert (out["status"], out["failure_code"], out["stage"]) == ("STOP", "IDENTITY_FAILED", "arguments")
    assert MARKER.encode() not in r.stdout


# --- T10: partial output ----------------------------------------------------------------------------------------

def test_t10_sums_last_and_excludes_stderr(completed):
    g6 = completed[2]
    raw = (g6 / "analysis.json").read_bytes()
    assert (g6 / "SHA256SUMS").read_bytes() == f"{_sha(raw)}  analysis.json\n".encode()


def test_t10_write_failure_leaves_no_sums(completed, source, tmp_path, monkeypatch):
    cfg, g5, g6 = _g6_setup(completed, source, tmp_path)
    real = f2.write_atomic

    def fail_sums(path, data):
        if path.name == "SHA256SUMS":
            raise OSError(MARKER)
        return real(path, data)
    monkeypatch.setattr(f2, "write_atomic", fail_sums)
    rc, out, text = _main(_g6_argv(g6, g5), cfg)
    assert (rc, out["failure_code"]) == (2, "WRITE_FAILED") and MARKER not in text
    assert (g6 / "analysis.json").exists() and not (g6 / "SHA256SUMS").exists()
    assert [f[0] for f in out["files"]] == ["analysis.json", "stderr.bin"]


@pytest.mark.parametrize("case", ["extra_file", "stderr_not_empty", "root_stray_file", "wrong_name", "wrong_head"])
def test_t10_attempt_directory_must_be_fresh(case, source, tmp_path):
    cfg = _cfg(source, tmp_path)
    d = _attempt(cfg, "g5-input")
    head = HEAD
    if case == "extra_file":
        (d / "x.txt").write_bytes(b"")
    elif case == "stderr_not_empty":
        (d / "stderr.bin").write_bytes(b"x")
    elif case == "root_stray_file":
        (cfg.new_output_root / "stray.txt").write_bytes(b"")
    elif case == "wrong_name":
        d = _attempt(cfg, "g6-analysis")
    elif case == "wrong_head":
        d = _attempt(cfg, "g5-input", head="f" * 40)
    rc, out, _ = _main(_g5_argv(d, head=head), cfg)
    assert (rc, out["failure_code"]) == (2, "OUTPUT_DIR_NOT_FRESH")


def test_parse_args_rejects_everything_unexpected():
    ok = ["verify-inputs", "--out", "o", "--expected-python", "p", "--expected-head", HEAD]
    assert f2.parse_args(ok)[0] == "verify-inputs"
    for bad in ([], ["x"], ok + ["--out", "o"], ok[:-1], ok + ["--input-verification", "g"],
                ["analyze", *ok[1:]], ok[:2] + ["", *ok[3:]]):
        with pytest.raises(f2.F2Stop) as e:
            f2.parse_args(bad)
        assert e.value.code == "IDENTITY_FAILED"


def test_default_config_matches_work_order():
    c = f2.DEFAULT_CONFIG
    assert len(c.code_rows) == 7 and len(c.contract_rows) == 10 and len(c.data_rows) == 18
    assert c.source_code_sha == "d2fcaf64b5fb87f502afba29572be340f653be24" and c.python_version == "3.14.8"
    assert c.expected_n == 1_459_876 and tuple(c.v4_seed_parts) == ("FUTDIAG", "v4eval") and c.v4_years == 4000
    assert c.calibration_sha256 == "a1bbada5821f7ae33707a8818927d3929d05a1ac4019946c15a7eac06e73531c"
    assert len(f2.FAILURE_CODES) == 18 and f2.ALPHAS == (0.025, 0.10) and f2.RATIO_DENOMINATOR == 0.066
    assert abs(f2.R_OBS_CONF - fd.PRIMARY_ALPHA - f2.RATIO_DENOMINATOR) < 1e-15
