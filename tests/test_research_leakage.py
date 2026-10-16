"""Look-ahead and leakage: features at t never see anything received after t; labels are the only
forward-looking values; train/validation/test do not share information. SYNTHETIC events."""

import math
from dataclasses import replace

import pytest

from moneylab.research.features import REGISTRY
from moneylab.research.labels import compute_labels, label_names
from moneylab.research.leaderboard import fit_train
from moneylab.research.sampling import build_grid
from moneylab.research.split import compute_boundaries, split_rows
from research_helpers import T0, book, session, span, study_config, trade


def same(a: float, b: float) -> bool:
    return (a != a and b != b) or a == b


def grid_of(evs, **kw):
    start, end = span(evs)
    return build_grid(evs, start, end, **kw)


def perturb_after(evs, cut: float):
    """Change every event received after `cut`: prices, sizes, trade sides and volumes; add trades."""
    out = []
    for e in evs:
        if e.received_timestamp <= cut:
            out.append(e)
        elif e.event_type == "book":
            out.append(replace(e, bids=tuple((p - 7000, s * 3) for p, s in e.bids),
                               asks=tuple((p + 9000, s / 2) for p, s in e.asks)))
        elif e.event_type == "trade":
            out.append(replace(e, trade=replace(e.trade, side="sell" if e.trade.side == "buy" else "buy",
                                                volume=e.trade.volume * 10)))
        else:
            out.append(e)
    seq = max(e.local_sequence for e in out)
    for i in range(20):  # extra future trades
        out.append(trade(seq + 1 + i, cut + 0.3 + i * 0.4, "sell", 5.0))
    return sorted(out, key=lambda e: e.received_timestamp)


@pytest.mark.parametrize("cut_offset", [20.0, 45.5, 89.0])
def test_features_at_t_are_unchanged_when_events_after_t_change(cut_offset):
    evs = session(120)
    g1 = grid_of(evs)
    cut = T0 + cut_offset
    evs2 = [replace(e, local_sequence=i + 1) for i, e in enumerate(perturb_after(evs, cut))]
    g2 = build_grid(evs2, *span(evs), )
    rows = [k for k, t in enumerate(g1.times) if t <= cut]
    assert rows and g1.times[: len(rows)] == g2.times[: len(rows)]
    for name in REGISTRY:
        for k in rows:
            assert same(g1.cols[name][k], g2.cols[name][k]), (name, k)
    for k in rows:
        assert g1.reasons[k] == g2.reasons[k] and same(g1.book_age[k], g2.book_age[k])
    # sanity: the perturbation does change later features
    later = [k for k, t in enumerate(g1.times) if t > cut + 2]
    assert any(not same(g1.cols["mid_price"][k], g2.cols["mid_price"][k]) for k in later)


def test_labels_are_the_only_values_that_see_the_future():
    evs = session(120)
    g1 = grid_of(evs)
    cut = T0 + 60.0
    evs2 = [replace(e, local_sequence=i + 1) for i, e in enumerate(perturb_after(evs, cut))]
    g2 = build_grid(evs2, *span(evs))
    l1, l2 = compute_labels(g1, (5,)), compute_labels(g2, (5,))
    k = next(i for i, t in enumerate(g1.times) if t == math.floor(cut) - 2)  # t+5 is after the cut
    assert all(same(g1.cols[n][k], g2.cols[n][k]) for n in REGISTRY)
    assert not same(l1["future_mid_move_bps_h5"][k], l2["future_mid_move_bps_h5"][k])
    early = next(i for i, t in enumerate(g1.times) if t + 5 + 0.25 < cut)  # whole label window before the cut
    for name in l1:
        assert same(l1[name][early], l2[name][early]), name


def test_event_with_backward_receive_clock_is_not_visible_early():
    """Arrival order: B arrives after A but carries an earlier receive time. At A's time it may become
    visible, never before."""
    a = book(1, T0 + 10.5, 100_000_000, 100_002_000)
    b = book(2, T0 + 10.2, 90_000_000, 90_002_000)  # clock stepped back
    evs = [book(0, T0 + 0.05, 100_000_000, 100_002_000, stream="REALTIME")] + [a, b]
    g = build_grid(evs, T0, T0 + 12)
    t10 = g.times.index(T0 + 10)
    t11 = g.times.index(T0 + 11)
    assert g.cols["mid_price"][t10] == 100_001_000  # neither A nor B yet
    assert g.cols["mid_price"][t11] == 90_001_000  # both applied by 11 (A then B, arrival order)


def test_trade_window_excludes_trades_received_after_t():
    evs = [book(1, T0 + 0.05, 100_000_000, 100_002_000)]
    evs += [trade(2, T0 + 9.999, "buy", 1.0), trade(3, T0 + 10.0, "buy", 2.0), trade(4, T0 + 10.001, "sell", 4.0)]
    evs += [book(5, T0 + 11.5, 100_000_000, 100_002_000)]
    g = build_grid(evs, T0, T0 + 11.5)
    k = g.times.index(T0 + 10)
    assert g.cols["signed_volume_1s"][k] == 3.0  # 9.999 and 10.000 in (9, 10]; 10.001 is the future


def make_split(seconds=1200.0, embargo=60.0):
    cfg = study_config(embargo_seconds=embargo)
    evs = session(seconds)
    g = grid_of(evs)
    labels = compute_labels(g, cfg.horizons)
    b = compute_boundaries(g.times[0], g.times[-1], cfg.train, cfg.validation, cfg.embargo_seconds)
    hz = {n: h for h in cfg.horizons for n in label_names((h,), cfg.sizes_btc, cfg.delays_ms)}
    rows, counts = split_rows(g.times, {**g.cols, **labels}, hz, b, cfg.max_delay_seconds,
                              {"reasons": [sorted(r) for r in g.reasons]})
    return cfg, b, rows, counts, hz


def test_split_is_chronological_with_embargo_and_no_overlap():
    cfg, b, rows, counts, _ = make_split()
    segs = [r["segment"] for r in rows]
    order = {"train": 0, "validation": 1, "test": 2}
    assert [order[s] for s in segs] == sorted(order[s] for s in segs)  # never interleaved
    tr = [r["t"] for r in rows if r["segment"] == "train"]
    va = [r["t"] for r in rows if r["segment"] == "validation"]
    te = [r["t"] for r in rows if r["segment"] == "test"]
    assert max(tr) < b.train_end <= b.validation_start - 60 + 1e-9
    assert min(va) >= b.validation_start and max(va) < b.validation_end
    assert min(te) >= b.test_start and b.test_start - b.validation_end == pytest.approx(60)
    assert not [r for r in rows if b.train_end <= r["t"] < b.validation_start]  # embargo rows dropped
    assert counts["embargo_rows"] > 0


def test_no_train_label_window_overlaps_a_validation_feature_window():
    cfg, b, rows, _, hz = make_split()
    latest_train_label = max(r["t"] + hz[n] + cfg.max_delay_seconds for r in rows if r["segment"] == "train"
                             for n in hz if r[n] == r[n])
    earliest_val_feature = min(r["t"] - REGISTRY[n].lookback_seconds for r in rows if r["segment"] == "validation"
                               for n in REGISTRY if r[n] == r[n])
    assert latest_train_label <= b.train_end + 1e-9 <= earliest_val_feature + 1e-9
    latest_val_label = max(r["t"] + hz[n] + cfg.max_delay_seconds for r in rows if r["segment"] == "validation"
                           for n in hz if r[n] == r[n])
    earliest_test_feature = min(r["t"] - REGISTRY[n].lookback_seconds for r in rows if r["segment"] == "test"
                                for n in REGISTRY if r[n] == r[n])
    assert latest_val_label <= b.validation_end + 1e-9 <= earliest_test_feature + 1e-9


def test_lookback_is_cut_at_segment_start_when_embargo_is_short():
    """With a 60 s embargo, 300 s realized vol may not reach back into train: NaN at validation start."""
    _, b, rows, counts, _ = make_split(embargo=60.0)
    first_val = next(r for r in rows if r["segment"] == "validation")
    assert first_val["realized_vol_300s"] != first_val["realized_vol_300s"]
    assert first_val["return_30s"] == first_val["return_30s"]  # 30 s < 60 s embargo: allowed
    assert counts["feature_values_cut_at_segment_start"] > 0


def test_train_fit_does_not_depend_on_validation_rows():
    cfg, _, rows, _, _ = make_split()
    train = [r for r in rows if r["segment"] == "train"]
    val = [r for r in rows if r["segment"] == "validation"]
    f1 = fit_train(train, "obi_5", 5, cfg)
    for r in val:
        r["obi_5"] = 123.0
        r["future_mid_move_bps_h5"] = -99.0
    f2 = fit_train(train, "obi_5", 5, cfg)
    assert f1 == f2


def test_boundaries_refuse_a_session_too_short_for_the_registered_split():
    from moneylab.research.split import InsufficientDataError

    with pytest.raises(InsufficientDataError):
        compute_boundaries(T0, T0 + 600, 0.6, 0.2, 300)
