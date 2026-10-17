"""MC-V06 research risk model (research/v06/risk_model.py, docs/tasks/MC-V06/WORK_ORDER.md EQUIVALENCE_TEST_CONTRACT).

Pure semantics (MAX_DRAWDOWN_LOG, calendar months, CUMULATIVE_FROM_L, MONTH_ONLY, gt, ge, threshold boundary) and the
cross-package equivalence with the BT-3e mechanism through public behaviour only: ForwardVault.check_risk, the
public engine (portfolio.simulate) and performance.max_drawdown_log. The private backtest/risk_check.py is not used.

The vault fixtures keep prices flat for 4 days on each side of every month boundary, so no result depends on the
excluded ENGINE_WINDOW_BT3B shifts (F = P - 2 days, last_day = N - 3 days). This is equivalence of the risk
semantics on given daily returns, not engine-level equivalence, and it does not resolve BT4-Q18.
SYNTHETIC / NOT_EVIDENCE, offline.
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
import math
import random
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from backtest_helpers import DAY, HOUR, T0, flat_bar, series

from moneylab.backtest.costs import CostModel
from moneylab.backtest.performance import max_drawdown_log as engine_max_drawdown_log
from moneylab.backtest.portfolio import RunConfig, simulate
from moneylab.backtest.vault import (
    PASS,
    RECORDED,
    VIOLATION,
    ForwardVault,
    HistoricalHoldoutVault,
    VaultSpec,
    build_vault,
    record_evidence,
    record_risk_policy,
    record_risk_strategies,
)
from moneylab.domain.bars import NOT_EVIDENCE, canonical_bar_rows, utc_iso
from moneylab.research.v06 import risk_model as RM
from moneylab.storage.atomic import sha256_file

SRC = Path(__file__).resolve().parents[1] / "src" / "moneylab"


def pol(mode=RM.CUMULATIVE_FROM_L, op=RM.GT, ratio=1.5):
    return RM.RiskPolicy(RM.MAX_DRAWDOWN_LOG, ratio, op, mode)


# --- pure semantics -------------------------------------------------------------------------------------------------

def test_vault_and_research_constants_agree():
    assert (RM.PASS, RM.VIOLATION) == (PASS, VIOLATION)
    assert RM.ACCUMULATION_MODES == ("CUMULATIVE_FROM_L", "MONTH_ONLY") and RM.COMPARISONS == ("gt", "ge")
    assert RM.METRIC_IDS == ("MAX_DRAWDOWN_LOG",)


def test_max_drawdown_log_is_one_minus_exp_of_the_worst_log_loss():
    assert RM.max_drawdown_log([]) == 0.0
    assert RM.max_drawdown_log([0.1, 0.2]) == 0.0
    r = [0.1, -0.05, -0.15, 0.3, -0.1]
    assert RM.max_drawdown_log(r) == pytest.approx(1 - math.exp(-0.2))
    assert RM.max_drawdown_log([-0.1]) == pytest.approx(1 - math.exp(-0.1))   # wealth starts at 1: first loss counts
    with pytest.raises(ValueError):
        RM.max_drawdown_log([0.1, math.nan])


def test_max_drawdown_log_matches_the_public_engine_metric_bit_for_bit():
    rng = random.Random(7)
    for _ in range(50):
        r = [rng.gauss(0, 0.03) for _ in range(rng.randrange(1, 400))]
        assert RM.max_drawdown_log(r) == engine_max_drawdown_log(r)["value"]
    assert RM.max_drawdown_log([0.01] * 5) == engine_max_drawdown_log([0.01] * 5)["value"] == 0.0


def test_running_drawdown_equals_every_prefix_exactly():
    rng = random.Random(3)
    r = [rng.gauss(0, 0.04) for _ in range(200)]
    run = RM.running_max_drawdown_log(r)
    assert run == [RM.max_drawdown_log(r[:k]) for k in range(1, len(r) + 1)]


def test_calendar_months_group_observations_by_utc_calendar_date():
    assert RM.calendar_months(date(2026, 12, 1), 62) == [("202612", 0, 31), ("202701", 31, 62)]
    assert RM.calendar_months(date(2028, 2, 1), 30) == [("202802", 0, 29), ("202803", 29, 30)]  # leap February
    assert RM.calendar_months(date(2026, 12, 16), 20) == [("202612", 0, 16), ("202701", 16, 20)]  # mid-month L
    assert RM.calendar_months(date(2026, 12, 1), 0) == []
    groups = RM.calendar_months(date(2026, 12, 1), RM.forward_days(date(2026, 12, 1), 36))
    assert len(groups) == 36 and groups[0][0] == "202612" and groups[-1][0] == "202911"
    assert all(hi - lo == (RM.next_month(date(int(n[:4]), int(n[4:]), 1)) - date(int(n[:4]), int(n[4:]), 1)).days
               for n, lo, hi in groups)


def test_forward_days_and_add_months():
    L = date(2026, 12, 1)
    assert [RM.forward_days(L, m) for m in (12, 24, 36)] == [365, 731, 1096]   # 2028 is a leap year
    assert RM.add_months(date(2027, 1, 31), 1) == date(2027, 2, 28)
    assert RM.add_months(date(2026, 12, 16), 12) == date(2027, 12, 16)
    with pytest.raises(ValueError):
        RM.parse_date("2026-12-1")


def _days(n, at=None):
    """n zero returns with {index: return} overrides."""
    r = [0.0] * n
    for i, x in (at or {}).items():
        r[i] = x
    return r


def test_cumulative_from_l_spans_months_and_month_only_restarts_each_month():
    L = date(2026, 12, 1)   # December 31 days, January 31 days
    r = _days(62, {27: -0.10, 35: -0.10})   # 2026-12-28 and 2027-01-05, no recovery in between
    cum = dict(RM.monthly_values(r, L, RM.CUMULATIVE_FROM_L))
    mon = dict(RM.monthly_values(r, L, RM.MONTH_ONLY))
    assert cum["202612"] == pytest.approx(1 - math.exp(-0.10)) and cum["202701"] == pytest.approx(1 - math.exp(-0.20))
    assert mon["202612"] == pytest.approx(1 - math.exp(-0.10)) and mon["202701"] == pytest.approx(1 - math.exp(-0.10))
    ref = 0.12   # limit 0.18: cumulative January violates, month-only does not
    assert RM.monthly_decisions(r, L, ref, pol(RM.CUMULATIVE_FROM_L)) == {"202612": PASS, "202701": VIOLATION}
    assert RM.monthly_decisions(r, L, ref, pol(RM.MONTH_ONLY)) == {"202612": PASS, "202701": PASS}
    assert RM.first_violation(r, L, ref, pol(RM.CUMULATIVE_FROM_L)) == 1
    assert RM.first_violation(r, L, ref, pol(RM.MONTH_ONLY)) is None


def test_month_only_ignores_earlier_months_and_a_peak_before_the_month():
    L = date(2027, 1, 1)
    r = _days(59, {10: 0.5, 40: -0.05})   # gain in January, small loss in February
    assert dict(RM.monthly_values(r, L, RM.MONTH_ONLY))["202702"] == pytest.approx(1 - math.exp(-0.05))
    r2 = _days(59, {30: -0.2, 31: 0.2})   # loss on Jan 31 recovered on Feb 1: February's own path has no drawdown
    assert dict(RM.monthly_values(r2, L, RM.MONTH_ONLY)) == {"202701": pytest.approx(1 - math.exp(-0.2)), "202702": 0.0}


def test_mid_month_start_month_only_starts_at_l():
    Ls = date(2026, 12, 16)
    r = _days(30, {3: -0.1})
    assert RM.monthly_values(r, Ls, RM.MONTH_ONLY)[0] == ("202612", pytest.approx(1 - math.exp(-0.1)))
    assert [n for n, _ in RM.monthly_values(r, Ls, RM.MONTH_ONLY)] == ["202612", "202701"]


def test_gt_and_ge_differ_exactly_at_the_threshold():
    ref = 0.1
    limit = 1.5 * ref
    assert RM.decide(limit, ref, pol(op=RM.GT)) == PASS
    assert RM.decide(limit, ref, pol(op=RM.GE)) == VIOLATION
    above, below = math.nextafter(limit, 1.0), math.nextafter(limit, 0.0)
    for op in (RM.GT, RM.GE):
        assert RM.decide(above, ref, pol(op=op)) == VIOLATION
        assert RM.decide(below, ref, pol(op=op)) == PASS


def test_zero_reference_boundary():
    """A confirmatory path without drawdown gives reference 0: ge violates even at value 0, gt only above 0."""
    assert RM.decide(0.0, 0.0, pol(op=RM.GE)) == VIOLATION
    assert RM.decide(0.0, 0.0, pol(op=RM.GT)) == PASS
    assert RM.decide(1e-12, 0.0, pol(op=RM.GT)) == VIOLATION


def test_threshold_is_the_ratio_times_the_reference():
    assert RM.decide(0.199, 0.1, pol(ratio=2.0)) == PASS and RM.decide(0.201, 0.1, pol(ratio=2.0)) == VIOLATION


def test_policy_values_are_explicit_and_validated():
    params = inspect.signature(RM.RiskPolicy).parameters
    assert all(p.default is inspect.Parameter.empty for p in params.values())
    for bad in (dict(metric_id="MDD"), dict(comparison_operator="gte"), dict(accumulation_mode="ROLLING"),
                dict(threshold_ratio=0), dict(threshold_ratio=True), dict(threshold_ratio=math.inf),
                dict(threshold_ratio="1.5")):
        args = dict(metric_id=RM.MAX_DRAWDOWN_LOG, threshold_ratio=1.5, comparison_operator=RM.GT,
                    accumulation_mode=RM.CUMULATIVE_FROM_L) | bad
        with pytest.raises(ValueError):
            RM.RiskPolicy(**args)
    assert pol().key == "MAX_DRAWDOWN_LOG|1.5|gt|CUMULATIVE_FROM_L"


def _imports(path: Path) -> set[str]:
    mods = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            mods.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module)
    return mods


def test_no_runtime_import_between_research_v06_and_backtest():
    for f in sorted((SRC / "research" / "v06").glob("*.py")):
        assert not any(m == "moneylab.backtest" or m.startswith("moneylab.backtest.") for m in _imports(f)), f
    for f in sorted((SRC / "backtest").rglob("*.py")):
        assert not any(m.startswith("moneylab.research") for m in _imports(f)), f


# --- cross-package equivalence through the public ForwardVault ------------------------------------------------------
# Timeline (T0 = 2020-01-01): confirmatory engine interval 2020-01-26 .. 2020-02-25, C = 2020-03-01,
# H = 2020-04-01, L = 2020-05-01 (month start), forward months 202005, 202006, 202007.

C, H, L = T0 + 60 * DAY, T0 + 91 * DAY, T0 + 121 * DAY
W_I, W_F = T0 + 182 * DAY, T0 + 213 * DAY
BOUNDARIES = (121, 152, 182, 213)
FLAT = {d for b in BOUNDARIES for d in range(b - 4, b + 4)}
LAST_DAY = 225
PRE, CFG, EV = "a" * 64, "b" * 64, "e" * 64
ENGINE_ID = "moneylab.backtest.engine/gap-free-window-signal+bt3b-boundary+scenario-ref-time/1"
CAND = {"scenario": "E0", "initial_cash": "1000000", "fee_bps": 0, "kappa_bps": "0", "impact_bps": "0",
        "fill_substitution": "none", "capacity_verified": True}
CONF_FIRST, CONF_LAST = T0 + 25 * DAY, T0 + 55 * DAY
MONTHS = ("202005", "202006", "202007")

# day -> daily price factor; every other day rises 1 % (flat around month boundaries). Events stay >= 4 days away
# from every month boundary, so the engine window shifts cannot move a loss into another month.
DESIGNS = {
    # conf dip 10 % (reference ~0.10, limit ~0.15); 8 % on 2020-06-26 and 8 % on 2020-07-05 with only flat days
    # between: cumulative July ~0.154 > limit, month-only July ~0.08
    "cross_month": {40: 0.90, 136: 0.92, 177: 0.92, 186: 0.92},
    # one 18 % loss on 2020-06-15: June violates in both modes, July only cumulatively
    "single": {40: 0.90, 166: 0.82},
    # no confirmatory drawdown: reference 0 (the gt / ge boundary), 5 % loss on 2020-06-15 only
    "zero_reference": {166: 0.95},
}


def _prices(events: dict[int, float]) -> list[Decimal]:
    p, out = 100.0, []
    for d in range(LAST_DAY):
        if d:
            p *= events.get(d, 1.0 if d in FLAT else 1.01)
        out.append(Decimal(f"{p:.2f}"))
    return out


def _bars(prices, first, last):
    daily = [flat_bar("day", T0 + d * DAY, prices[d]) for d in range(first, last)]
    hourly = [flat_bar("hour", T0 + d * DAY + h * HOUR, prices[d]) for d in range(first, last) for h in range(24)]
    return daily, hourly


def _write_bars(root: Path, name: str, rows) -> Path:
    d = root / name
    d.mkdir(parents=True)
    interval = rows[0].interval
    data = canonical_bar_rows(rows)
    srt = sorted(rows, key=lambda b: b.start_utc)
    bars_file = f"bars_{interval}.jsonl"
    manifest = {"schema": "moneylab.backtest.bars/1", "evidence": NOT_EVIDENCE, "provenance": "fixture",
                "market": "KRW-BTC", "interval": interval, "bars": len(srt),
                "first_start": utc_iso(srt[0].start_utc), "last_start": utc_iso(srt[-1].start_utc),
                "bars_file": bars_file, "bars_sha256": hashlib.sha256(data).hexdigest(),
                "source_pull": {"pull_id": name}, "confirmation_rule": "hand written (tests)"}
    (d / bars_file).write_bytes(data)
    (d / "bars_manifest.json").write_bytes((json.dumps(manifest, sort_keys=True, indent=1) + "\n").encode())
    sums = "".join(f"{sha256_file(d / n)}  {n}\n" for n in sorted([bars_file, "bars_manifest.json"]))
    (d / "SHA256SUMS.txt").write_text(sums, encoding="utf-8", newline="\n")
    return d


def _vault_decisions(tmp: Path, prices, mode: str, op: str) -> dict[str, str]:
    """Month -> decision of M20 from the public BT-3e mechanism (one vault, each month checked once)."""
    daily, hourly = _bars(prices, 0, 121)
    src = tmp / "src"
    spec = VaultSpec(C, H, L, W_I, W_F, PRE, CFG)
    v = build_vault(_write_bars(src, "day_src", daily), _write_bars(src, "hour_src", hourly), spec,
                    tmp / "vault-fixture").dir
    policy = dict(preregistration_sha256=PRE, config_sha256=CFG, metric_id="MAX_DRAWDOWN_LOG", threshold_ratio="1.5",
                  comparison_operator=op, accumulation_mode=mode, window_mapping_id="ENGINE_WINDOW_BT3B",
                  engine_semantics_id=ENGINE_ID, confirmatory_first_day=CONF_FIRST, confirmatory_last_day=CONF_LAST,
                  check_window_end_utc=W_F, candidates={"M20": dict(CAND)}, f_rule_sha256="f" * 64)
    assert record_risk_policy(v, **policy) == RECORDED
    record_evidence(v, "confirmatory_results", EV)
    record_evidence(v, "row9_strategy", EV, detail=["M20"])
    record_evidence(v, "q12_done", EV)
    HistoricalHoldoutVault(v).open_once(preregistration_sha256=PRE, config_sha256=CFG, caller="tests")
    assert record_risk_strategies(v, strategies=["M20"], basis_sha256="c" * 64, preregistration_sha256=PRE,
                                  config_sha256=CFG) == RECORDED
    fd, fh = _bars(prices, 121, LAST_DAY)
    fwd = (series(fd, "fixture"), series(fh, "fixture"))
    for m in MONTHS:
        ForwardVault(v).seal(*fwd, m)
    return {m: ForwardVault(v).check_risk(m, preregistration_sha256=PRE, config_sha256=CFG, caller="tests")["M20"]
            for m in MONTHS}


def _engine_returns(prices, first: datetime, last: datetime) -> list[tuple[date, float]]:
    """(UTC date of the reference time, log return) of the public engine's daily equity (first from initial cash)."""
    daily, hourly = _bars(prices, 0, LAST_DAY)
    rc = RunConfig("M20", first, last, Decimal(CAND["initial_cash"]), CostModel.scenario(0, Decimal(0), Decimal(0)),
                   scenario="E0", fill_substitution="none", capacity_verified=True)
    result = simulate(series(daily, "fixture"), series(hourly, "fixture"), rc)
    prev, out = float(rc.initial_cash), []
    for row in result.ledger.daily:
        eq = float(row.equity)
        out.append((row.ref_time.astimezone(UTC).date(), math.log(eq / prev)))
        prev = eq
    return out


def _research_decisions(prices, mode: str, op: str) -> dict[str, str]:
    reference = RM.max_drawdown_log([x for _, x in _engine_returns(prices, CONF_FIRST, CONF_LAST)])
    rows = [(d, x) for d, x in _engine_returns(prices, L - 2 * DAY, W_F - 3 * DAY) if d >= L.date()]
    assert [d for d, _ in rows] == [date.fromordinal(L.date().toordinal() + i) for i in range(len(rows))]
    out = RM.monthly_decisions([x for _, x in rows], L.date(), reference, pol(mode, op))
    return {m: out[m] for m in MONTHS}


EXPECTED = {
    ("cross_month", RM.CUMULATIVE_FROM_L, RM.GT): {"202005": PASS, "202006": PASS, "202007": VIOLATION},
    ("cross_month", RM.MONTH_ONLY, RM.GT): {"202005": PASS, "202006": PASS, "202007": PASS},
    ("single", RM.CUMULATIVE_FROM_L, RM.GT): {"202005": PASS, "202006": VIOLATION, "202007": VIOLATION},
    ("single", RM.MONTH_ONLY, RM.GT): {"202005": PASS, "202006": VIOLATION, "202007": PASS},
    ("zero_reference", RM.CUMULATIVE_FROM_L, RM.GT): {"202005": PASS, "202006": VIOLATION, "202007": VIOLATION},
    ("zero_reference", RM.MONTH_ONLY, RM.GT): {"202005": PASS, "202006": VIOLATION, "202007": PASS},
    ("zero_reference", RM.CUMULATIVE_FROM_L, RM.GE): {"202005": VIOLATION, "202006": VIOLATION, "202007": VIOLATION},
    ("zero_reference", RM.MONTH_ONLY, RM.GE): {"202005": VIOLATION, "202006": VIOLATION, "202007": VIOLATION},
}


@pytest.mark.parametrize("design, mode, op", sorted(EXPECTED))
def test_research_model_matches_the_public_forward_vault(tmp_path, design, mode, op):
    prices = _prices(DESIGNS[design])
    research = _research_decisions(prices, mode, op)
    assert research == EXPECTED[(design, mode, op)]
    assert _vault_decisions(tmp_path, prices, mode, op) == research


def test_fixture_losses_are_held_and_away_from_month_boundaries():
    """The fixture is meaningful only if the engine holds through every loss and no loss is near a boundary."""
    for events in DESIGNS.values():
        assert all(min(abs(d - b) for b in BOUNDARIES) >= 4 for d in events)
    prices = _prices(DESIGNS["cross_month"])
    rows = dict(_engine_returns(prices, L - 2 * DAY, W_F - 3 * DAY))
    assert rows[date(2020, 6, 26)] == pytest.approx(math.log(0.92), abs=1e-3)   # 2020-06-26 loss, held
    assert rows[date(2020, 7, 5)] == pytest.approx(math.log(0.92), abs=1e-3)    # 2020-07-05 loss, held
    reference = RM.max_drawdown_log([x for _, x in _engine_returns(prices, CONF_FIRST, CONF_LAST)])
    assert reference == pytest.approx(0.10, abs=1e-3)
    zero = RM.max_drawdown_log([x for _, x in _engine_returns(_prices(DESIGNS["zero_reference"]), CONF_FIRST,
                                                               CONF_LAST)])
    assert zero == 0.0
