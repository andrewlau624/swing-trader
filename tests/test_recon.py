"""swingtrader/daily/recon.py: live-vs-backtest reconciliation on small synthetic fixtures."""
import json
import random
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from swingtrader.daily import recon as r

D = SimpleNamespace(night_day_ret_max=-0.08, night_ibs_max=0.10, night_price_min=5.0, night_price_max=2000.0,
                    night_vol_min=0.60, night_max_corr=0.7, night_crowd_n=30, night_max_name_pct=0.15,
                    night_tilt_model="v1", night_tilt_k=0.25, night_tilt_tow=False,
                    ibs_symbols=["SPY", "QQQ", "IWM"], ibs_top_k=0, ibs_max=0.2)


def fill(coid, sym, leg, side, qty, px, at, ref=None):
    ref = px if ref is None else ref
    return dict(coid=coid, sym=sym, leg=leg, side=side, qty=qty, fill_px=px, ref_px=ref,
                slippage_bps=r.fill_gap_bp(side, px, ref), filled_at=at)


def loaded(tmp_path, rows, book="live"):
    (tmp_path / f"daily-fills-{book}.jsonl").write_text("".join(json.dumps(x) + "\n" for x in rows))
    return r.load_fills(tmp_path, book)


# ------------------------------------------------------------ decomposition
def test_decomposition_sums_exactly_on_random_days():
    rng = random.Random(7)
    for _ in range(500):
        rule = [dict(sym=f"R{i}", w=rng.random() + .01, bt=rng.gauss(0, .05)) for i in range(rng.randint(0, 6))]
        live = [dict(sym=f"L{i}", w=rng.random() * 900 + 1, bt_rh=rng.gauss(0, .05), bt_same=rng.gauss(0, .05),
                     ret=rng.gauss(0, .05)) for i in range(rng.randint(0, 6))]
        d = r.decompose(rule, live)
        assert d["pick"] + d["sizing"] + d["timing"] + d["fill"] == pytest.approx(d["total"], abs=1e-15)
        assert d["total"] == pytest.approx(d["A"] - d["C"], abs=1e-15)
        assert d["residual"] == pytest.approx(d["sizing"] + d["timing"], abs=1e-15)


def test_known_fill_cost_case_is_all_fill_and_positive_means_live_worse():
    # same name, same weight, rule and live hold the same night; live paid 10.10 vs the 10.00 closing cross
    rule = [dict(sym="A", w=1.0, bt=10.50 / 10.00 - 1)]
    live = [dict(sym="A", w=1010.0, bt_rh=10.50 / 10.00 - 1, bt_same=10.50 / 10.00 - 1, ret=10.50 / 10.10 - 1)]
    d = r.decompose(rule, live)
    assert d["pick"] == 0 and d["sizing"] == 0 and d["timing"] == 0
    assert d["fill"] == pytest.approx(0.05 - (10.50 / 10.10 - 1))
    assert d["total"] == d["fill"] > 0                                     # live worse -> positive
    assert r.fill_gap_bp("buy", 10.10, 10.00) == pytest.approx(100.0)      # paid 1% above the print
    assert r.fill_gap_bp("sell", 9.90, 10.00) == pytest.approx(100.0)      # sold 1% below the print
    assert r.fill_gap_bp("sell", 10.10, 10.00) == pytest.approx(-100.0)    # sold above: live better
    with pytest.raises(ValueError):
        r.fill_gap_bp("short", 1, 1)


def test_pick_mismatch_case():
    # rule A, B; live A, C; everything at the prints -> fill 0, timing 0, pick = EW(A,B) - EW(A,C)
    a, b, c = 0.02, 0.06, -0.04
    rule = [dict(sym="A", w=1, bt=a), dict(sym="B", w=1, bt=b)]
    live = [dict(sym="A", w=500, bt_rh=a, bt_same=a, ret=a), dict(sym="C", w=500, bt_rh=c, bt_same=c, ret=c)]
    d = r.decompose(rule, live)
    assert d["fill"] == 0 and d["timing"] == 0 and d["sizing"] == pytest.approx(0, abs=1e-15)
    assert d["pick"] == pytest.approx((a + b) / 2 - (a + c) / 2) == pytest.approx(d["total"])
    assert r.jaccard(["A", "B"], ["A", "C"]) == pytest.approx(1 / 3)
    assert r.jaccard([], []) is None


def test_timing_case_late_exit_is_timing_not_fill():
    # live sold a session late at that session's print: rule-period +3%, live-period -1%
    live = [dict(sym="A", w=100, bt_rh=0.03, bt_same=-0.01, ret=-0.01)]
    d = r.decompose([dict(sym="A", w=1, bt=0.03)], live)
    assert d["fill"] == 0 and d["timing"] == pytest.approx(0.04) == pytest.approx(d["total"])


def test_empty_sides_are_cash():
    d = r.decompose([dict(sym="A", w=1, bt=0.02)], [])
    assert d["C"] == 0 and d["total"] == pytest.approx(0.02) == pytest.approx(d["pick"])
    d = r.decompose([], [dict(sym="A", w=1, bt_rh=0.01, bt_same=0.01, ret=0.005)])
    assert d["A"] == 0 and d["total"] == pytest.approx(-0.005)


def test_night_days_uses_official_prints_and_signs(tmp_path):
    f = loaded(tmp_path, [fill("dlv.A.2026-10-01.night-buy-entry", "A", "night", "buy", 10, 10.10, "2026-10-01T20:00:01+0000"),
                          fill("dlv.A.2026-10-02.night-sell-exit", "A", "night", "sell", 10, 10.40, "2026-10-02T13:30:01+0000")])
    trips, open_ = r.round_trips(f, "night")
    assert len(trips) == 1 and not open_
    X = {"A": {"2026-10-01": (9.9, 100, 10.00, 500), "2026-10-02": (10.50, 300, 10.6, 400)}}
    days, trades = r.night_days(trips, {"2026-10-01": [("A", 1.0)]}, X, "live", {})
    t = trades[0]
    assert t["buy_bp"] == pytest.approx(100.0) and t["sell_bp"] == pytest.approx(-(10.40 / 10.50 - 1) * 1e4)
    d = days[0]
    assert d["jaccard"] == 1.0 and d["pick"] == 0
    assert d["total"] == pytest.approx((10.5 / 10.0 - 10.4 / 10.1) * 1e4)   # bp, + = live worse
    s = r.summarize(days, trades, "live", "night")
    text = "\n".join(r.fmt(s))
    assert "+ = live worse" in text and f"{s['total']['mean']:+.1f}bp" in text   # value printed next to its label


# ------------------------------------------------------------ no lookahead
def _minutes(price, high, low):
    return pd.DataFrame({"price": price, "high": high, "low": low})


def test_night_rule_and_superset_use_only_decision_time_data():
    elig = pd.DataFrame({"prev_close": [20.0, 20.0, 20.0], "vol20": [0.9, 0.9, 0.3], "adv20": [5e7] * 3,
                         "rets": [list(np.random.default_rng(i).normal(0, .03, 20)) for i in range(3)],
                         "tow": [5, 5, 5]}, index=["A", "B", "Q"])
    # 15:39 rows: A -10% at its low (pick), B -5% (no), Q -12% but quiet (vol floor)
    rows = _minutes([18.0, 19.0, 17.6], [20.5, 20.2, 20.0], [18.0, 18.9, 17.6])
    rows.index = ["A", "B", "Q"]
    p, why = r.night_rule(rows, elig, D)
    assert list(p.index) == ["A"] and "Q" in why and "vol20" in why["Q"]
    # the full-day bars may contain later prints (B crashes at 15:55): the superset prunes with the day low, but
    # the picks come only from the 15:39 rows, so they cannot change
    day = pd.Timestamp("2026-10-01")
    raw = {"A": pd.DataFrame({"low": [18.0]}, index=[day]), "B": pd.DataFrame({"low": [15.0]}, index=[day]),
           "Q": pd.DataFrame({"low": [17.6]}, index=[day])}
    sup = r.night_superset(raw, elig, day, -0.08)
    assert set(sup) == {"A", "B", "Q"}
    p2, _ = r.night_rule(rows.loc[sup], elig, D)
    assert list(p2.index) == list(p.index)
    # pruning never drops a name that qualifies at 15:39 (its day low <= its 15:39 price)
    assert all(raw[s].at[day, "low"] <= elig.at[s, "prev_close"] * 0.92 for s in p.index)


def test_ibs_targets_ignore_the_mornings_own_bar_and_later():
    idx = pd.bdate_range("2026-09-01", "2026-10-05")
    bars = {s: pd.DataFrame({"open": 10.0, "high": 11.0, "low": 9.0, "close": 10.5, "volume": 1e6}, index=idx)
            for s in D.ibs_symbols}
    day = pd.Timestamp("2026-10-02")
    bars["SPY"].loc[bars["SPY"].index == pd.Timestamp("2026-10-01"), ["close"]] = 9.1      # IBS 0.05 on the prior bar
    before = r.ibs_targets_on(bars, day, D)
    assert before == ["SPY"]
    for s in D.ibs_symbols:                                       # rewrite the morning's own bar and every later one
        bars[s].loc[bars[s].index >= day, ["close", "low"]] = [9.0, 9.0]
    assert r.ibs_targets_on(bars, day, D) == before


def test_pref_rule_prices_from_the_previous_close_cross():
    ev = [dict(sym="X.PRA", ex="2026-10-02", div=0.30, cls="pref"), dict(sym="Y.PRB", ex="2026-10-02", div=0.20, cls="pref")]
    days = [f"2026-09-{d:02d}" for d in range(15, 31)] + ["2026-10-01"]
    X = {s: {d: (20.0, 100, 20.0, 1000) for d in days} for s in ("X.PRA", "Y.PRB")}
    picks, why = r.pref_rule(ev, X, "2026-10-01", "2026-10-02")
    assert [p["sym"] for p in picks] == ["X.PRA", "Y.PRB"] and picks[0]["px"] == 20.0
    X["X.PRA"]["2026-10-01"] = (5.0, 100, 5.0, 1000)              # the decision day's own cross is not known at 15:25
    picks2, _ = r.pref_rule(ev, X, "2026-10-01", "2026-10-02")
    assert [p["sym"] for p in picks2] == ["X.PRA", "Y.PRB"] and picks2[0]["px"] == 20.0


# ------------------------------------------------------------ data quality
def test_duplicate_fill_id_fails_loudly(tmp_path):
    a = fill("dlv.A.2026-10-01.night-buy-entry", "A", "night", "buy", 1, 10.0, "2026-10-01T20:00:01+0000")
    f = loaded(tmp_path, [a, a])
    iss = r.check_fills(f)
    assert any(i["sev"] == "error" and i["check"] == "duplicate fill" for i in iss)
    with pytest.raises(r.ReconDataError):
        r.raise_on_errors(iss, log=lambda s: None)


def test_unit_drift_and_auction_window_and_trade_date(tmp_path):
    bad = fill("dlv.B.2026-10-01.night-buy-entry", "B", "night", "buy", 1, 10.05, "2026-10-01T20:04:50+0000", ref=10.0)
    bad["slippage_bps"] = 0.5                                     # 50bp stored as a percent: does not recompute
    late_open = fill("dlv.C.2026-11-03.night-sell-exit", "C", "night", "sell", 1, 5.0, "2026-11-03T14:33:04+0000")
    est_ok = fill("dlv.D.2026-11-03.night-buy-entry", "D", "night", "buy", 1, 5.0, "2026-11-03T21:00:01+0000")
    f = loaded(tmp_path, [bad, late_open, est_ok])
    iss = r.check_fills(f)
    msgs = [(i["sev"], i["check"], i["detail"]) for i in iss]
    assert any(s == "error" and c == "units" for s, c, _ in msgs)
    win = [d for s, c, d in msgs if c == "auction window"]
    assert len(win) == 2 and any("16:04:50" in d for d in win) and any("09:33:04" in d for d in win)
    assert [x["td"] for x in f] == ["2026-10-01", "2026-11-03", "2026-11-03"]   # 16:00 EST after DST is still that day
    assert not any(c == "trade date" for _, c, _ in msgs)


def test_decision_qty_mismatch_and_missing_decision(tmp_path):
    f = loaded(tmp_path, [fill("dlv.A.2026-10-02.night-buy-entry", "A", "night", "buy", 3, 10.0, "2026-10-02T20:00:01+0000"),
                          fill("dlv.B.2026-10-02.night-buy-entry", "B", "night", "buy", 1, 10.0, "2026-10-02T20:00:01+0000")])
    iss = r.check_decisions([dict(date="2026-10-01", sym="Z", qty=1), dict(date="2026-10-02", sym="A", qty=4)], f, "live")
    assert {i["check"] for i in iss} == {"qty mismatch", "missing decision"}


def test_round_trips_fifo_partial(tmp_path):
    f = loaded(tmp_path, [fill("1", "A", "night", "buy", 3, 10.0, "2026-10-01T20:00:01+0000"),
                          fill("2", "A", "night", "sell", 2, 11.0, "2026-10-02T13:30:01+0000"),
                          fill("3", "A", "night", "sell", 1, 12.0, "2026-10-05T13:30:01+0000")])
    t, o = r.round_trips(f, "night")
    assert [(x["qty"], x["exit"], x["sell_px"]) for x in t] == [(2, "2026-10-02", 11.0), (1, "2026-10-05", 12.0)] and not o


# ------------------------------------------------------------ stats, reasons, reader
def test_ex_top_flags_concentration_and_t():
    days = [dict(day=f"d{i}", total=v) for i, v in enumerate([400, 300, 250, 200, 150] + [-5] * 15)]
    e = r.ex_top(days)
    assert e["concentrated"] and e["mean"] == pytest.approx(-5.0)
    flat = [dict(day=f"d{i}", total=10 + (i % 3)) for i in range(30)]
    assert not r.ex_top(flat)["concentrated"]
    assert r.tstat([1, 2, 3])["t"] == pytest.approx(2 / (1 / np.sqrt(3)))
    c = r.clustered([10, 10, -2, -2], ["a", "a", "b", "b"])
    assert c["days"] == 2 and c["mean"] == pytest.approx(4.0)


def test_night_reasons_from_logs():
    txt = ("[20:41:54] [night] 2 duplicate bet(s) dropped (20d corr > 0.7): UVXY ~ UVIX, SQQQ ~ UVIX\n"
           "[20:41:57]   skip BWET: $109 buys 0 shares at 574.00\n"
           "[20:41:57]   skip ZZZ: book cash exhausted\n")
    out = r.night_reasons(["BWET", "ZZZ", "UVXY", "NEW", "WASH"], ["LIVE1"], txt, {"BWET", "ZZZ", "UVXY", "WASH"},
                          {}, {"LIVE1": dict(day_ret=-0.07, ibs=0.2)}, {"LIVE1": dict(day_ret=-0.085, ibs=0.05)}, {"WASH"})
    assert out["BWET"].startswith("zero shares") and out["ZZZ"] == "book cash exhausted"
    assert out["UVXY"].startswith("live dedupe") and out["NEW"].startswith("data difference")
    assert out["WASH"].startswith("wash guard") and "SIP 15:39 -7.0%" in out["LIVE1"] and "live -8.5%" in out["LIVE1"]


def test_line_reads_latest_run():
    s = r.summarize([dict(day="2026-10-01", total=12.0, A=50.0, C=38.0, pick=2.0, sizing=1.0, timing=0.0, fill=9.0,
                          residual=1.0, jaccard=0.5)], [], "all", "night")
    rows = [dict(s, run="2026-11-01"), dict(s, run="2026-11-08")]
    ln = r.line(rows)
    assert ln.startswith("2026-11-08") and "night +12bp" in ln and "+ = live worse" in ln
    assert r.line([]).startswith("no recon run")


def test_reasons_tiny_universe_and_ibs_wash():
    out = r.night_reasons(["A"], [], "[14:15:38] [night] 43 names eligible today (close >= $5)\n", set(), {}, {}, {}, set())
    assert "only 43 names" in out["A"]
    txt = ("[ibs] IBS last bar: SMH 0.05, XBI 0.07, XLE 0.96 -> hold ['SOXQ']\n"
           "[wash] roth_first: roth night blocks 57 (...), IBS look-alikes SMH->SOXQ, skipped ['XBI']\n")
    base = {"SOXQ": "SMH"}
    assert r.ibs_reason(txt, "XBI", base).startswith("wash guard (roth_first skipped")
    assert r.ibs_reason(txt, "SMH", base).startswith("live held it")
    assert r.ibs_reason(txt, "XLE", base).startswith("data difference")
