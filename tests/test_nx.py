"""Study NX harness on a tiny synthetic Sharadar-shaped fixture (no real data)."""
import dataclasses
import json
import os
import time

import numpy as np
import pandas as pd
import pytest

from research.sim import nx

SESS = nx.nyse_sessions(2003)
D = pd.Timestamp
E1, E4W, E5H = D("2003-06-11"), D("2003-08-15"), D("2003-07-03")      # Wed, Fri (weekend gap), Thu before Jul 4 (holiday gap)
E2, E3, ESPL = D("2003-09-10"), D("2003-10-08"), D("2003-11-12")
EDUP, EFUND = D("2003-04-16"), D("2003-05-14")


def series(start_px, events=None, vol=2e6, last=None, first=None):
    """Alternating +5% / -4.5% days (never a natural -8%), events override one day: (drop, next-day gap)."""
    events = events or {}
    rows = []; prev = start_px; pending_gap = 0.0
    for i, d in enumerate(SESS):
        if first is not None and d < first: continue
        if last is not None and d > last: break
        o = prev * (1 + pending_gap); pending_gap = 0.0
        if d in events:
            drop, gap = events[d]
            c = prev * (1 + drop); h = prev; l = c * 0.99; pending_gap = gap
        else:
            c = prev * (1.05 if i % 2 == 0 else 0.955)
            h, l = max(o, c) * 1.01, min(o, c) * 0.99
        rows.append((d, o, h, l, c, vol)); prev = c
    return pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])


def build(root, bad_holiday=False, dup_ticker=False, no_spl_action=False):
    P = nx.Paths(root)
    P.raw.mkdir(parents=True, exist_ok=True)
    sep, tick, acts = [], [], []

    def add(tk, perma, df, name="FAKE CO", cat="Domestic Common Stock", exch="NYSE", delisted="N", table="SEP", adj=None):
        df = df.copy(); df["ticker"] = tk
        df["closeunadj"] = df["close"]
        if adj is not None:   # adj: factor series by date for dates <= split (adjusted = raw / factor)
            fac = df["date"].map(lambda d: adj[1] if d <= adj[0] else 1.0)
            for c in ("open", "high", "low", "close"): df[c] = df[c] / fac
            df["volume"] = df["volume"] * fac
        df["closeadj"] = df["close"]; df["lastupdated"] = "2026-01-01"
        (sep if table == "SEP" else sfp).append(df)
        tick.append(dict(table=table, permaticker=perma, ticker=tk, name=name, exchange=exch, isdelisted=delisted, category=cat,
                         sector="Technology", firstpricedate=df["date"].min(), lastpricedate=df["date"].max()))
    sfp = []
    for k in range(3): add(f"BASE{k + 1}", 10 + k, series(50, vol=1e6), name=f"BASE {k + 1}")
    add("LOS1", 20, series(20, {E1: (-0.10, 0.03)}))
    add("LOS4", 21, series(20, {E4W: (-0.10, 0.02)}))
    add("LOS5", 22, series(20, {E5H: (-0.10, 0.02)}))
    add("LOS6", 23, series(20, {EDUP: (-0.09, 0.01)}))
    add("LOS7", 24, series(20, {EDUP: (-0.11, 0.01)}))
    add("LOS2", 25, series(20, {E2: (-0.10, 0.0)}, last=E2), name="FAKE LEHMAN BROTHERS HOLDINGS", delisted="Y")
    add("LOS3", 26, series(20, {E3: (-0.10, 0.0)}, last=E3), delisted="Y")
    add("REU", 27, series(30, last=D("2003-06-30")), delisted="Y")
    add("REU1", 28, series(30, first=D("2003-07-01")))
    spl = series(40, {ESPL: (-0.10, 0.03)})
    nxt = SESS[list(SESS).index(ESPL) + 1]
    # raw price halves at the split: open of ESPL+1 is already post-split
    spl.loc[spl.date >= nxt, ["open", "high", "low", "close"]] *= 0.5
    add("SPLT", 29, spl, adj=(ESPL, 2.0))
    acts.append(dict(date=nxt, action="" if no_spl_action else "split", ticker="SPLT", value=2.0))
    acts += [dict(date=E2, action="delisted", ticker="LOS2", value=0.5 * float(series(20, {E2: (-0.10, 0.0)}, last=E2)["close"].iloc[-1])),
             dict(date=E3, action="delisted", ticker="LOS3", value=np.nan),
             dict(date=D("2003-06-30"), action="delisted", ticker="REU", value=np.nan)]
    fund = series(25, {EFUND: (-0.10, 0.01)})
    add("FUND1", 40, fund, cat="ETF", exch="NYSEARCA", table="SFP")
    iw = series(60); iw["open"] = iw["close"].shift(1).fillna(60) * (1 + 0.002 * np.sin(np.arange(len(iw))))
    add("IWM", 41, iw, cat="ETF", exch="NYSEARCA", table="SFP")
    sep = pd.concat(sep); sfp = pd.concat(sfp)
    if bad_holiday:
        extra = sep[sep.ticker == "BASE1"].iloc[:1].copy(); extra["date"] = D("2003-07-04"); sep = pd.concat([sep, extra])
    t = pd.DataFrame(tick)
    if dup_ticker:
        t = pd.concat([t, t[t.ticker == "BASE1"]])
    sep.to_csv(P.raw / "SHARADAR_SEP.csv", index=False)
    sfp.to_csv(P.raw / "SHARADAR_SFP.csv", index=False)
    t.to_csv(P.raw / "SHARADAR_TICKERS.csv", index=False)
    pd.DataFrame(acts).to_csv(P.raw / "SHARADAR_ACTIONS.csv", index=False)
    return P


SPEC = dataclasses.replace(
    nx.SPEC, years=(2003,), cov_range=(1, 100), min_delist_cmp=2, lo="2002-12-01", min_delist_share=0.10,
    named=((r"LEHMAN", "2003-09-01", "2003-12-31", True), (r"NOSUCHNAME", None, None, False)),
    checkpoints=(("SPLT", "2003-11-12", None, 0.01),), split_pair=("SPLT", "2003-11-12", str(SESS[list(SESS).index(ESPL) + 1].date()), 2.0),
    volume_cp=("BASE1", "2003-06-10", 5e5, 2e6), div_only=("BASE1", "BASE2"))


def spec_for(P):
    raw = float(series(40, {ESPL: (-0.10, 0.03)})[lambda d: d.date == ESPL]["close"].iloc[0])
    return dataclasses.replace(SPEC, checkpoints=(("SPLT", "2003-11-12", raw, 0.01),))


def mark_valid(P):
    P.nx.mkdir(parents=True, exist_ok=True)
    P.valid_sentinel.write_text(json.dumps({"ok": True, "timestamp": "t", "git": "x", "independent": False}))
    t = time.time() + 5
    os.utime(P.valid_sentinel, (t, t))


@pytest.fixture()
def P(tmp_path): return build(tmp_path)


def by_label(res, start): return next(r for r in res if r["label"].startswith(start))


# ---------------------------------------------------------------- calendar
def test_nyse_session_counts_and_specials():
    want = {2003: 252, 2004: 252, 2005: 252, 2006: 251, 2007: 251, 2008: 253, 2009: 252, 2010: 252, 2011: 252,
            2012: 250, 2013: 252, 2014: 252, 2015: 252}
    assert {y: len(nx.nyse_sessions(y)) for y in want} == want
    for d in ("2004-06-11", "2007-01-02", "2012-10-29", "2012-10-30", "2010-12-24", "2009-07-03"):
        assert D(d) not in nx.nyse_sessions(D(d).year)
    assert D("2010-12-31") in nx.nyse_sessions(2010)      # Jan 1 2011 Saturday: no Friday holiday


# ---------------------------------------------------------------- validate
def test_validate_passes_on_clean_fixture(P):
    res = nx.validate(P, spec_for(P))
    text, ok = nx.report_validate(res)
    assert ok, text
    assert by_label(res, "4a")["ok"] and by_label(res, "5")["ok"] and by_label(res, "6")["ok"]
    assert by_label(res, "8c")["ok"] is None          # no independent series -> UNCHECKED, not a pass


def test_validate_flags_holiday_bar(tmp_path):
    P = build(tmp_path, bad_holiday=True)
    r = by_label(nx.validate(P, spec_for(P)), "6")
    assert r["ok"] is False and r["critical"]


def test_validate_flags_ambiguous_ticker(tmp_path):
    P = build(tmp_path, dup_ticker=True)
    assert by_label(nx.validate(P, spec_for(P)), "1")["ok"] is False


def test_validate_flags_ratio_change_without_split_action(tmp_path):
    P = build(tmp_path, no_spl_action=True)
    assert by_label(nx.validate(P, spec_for(P)), "4a")["ok"] is False


def test_validate_flags_bad_checkpoint_and_missing_name(P):
    bad = dataclasses.replace(spec_for(P), checkpoints=(("SPLT", "2003-11-12", 999.0, 0.01),),
                              named=((r"LEHMAN", "2008-09-01", "2009-03-31", True),))
    res = nx.validate(P, bad)
    assert by_label(res, "4b")["ok"] is False and by_label(res, "3")["ok"] is False
    assert nx.report_validate(res)[1] is False


def test_delisting_share_gate(P):
    res = nx.validate(P, dataclasses.replace(spec_for(P), min_delist_share=0.9))
    assert by_label(res, "9")["ok"] is False


# ---------------------------------------------------------------- run mechanics
def trades(P, which):
    master = nx.load_master(P); act = nx.read_table(P, "ACTIONS")
    pn = nx.build_panel(nx.load_bars(P, "2002-12-01", "2004-01-20"))
    return nx.collect_trades(pn, master, act, which, D("2003-01-02"), D("2003-12-31"))["trades"].set_index("ticker")


def test_primary_picks_sizing_and_outcomes(P):
    t = trades(P, "primary")
    assert set(t.index) == {"LOS1", "LOS4", "LOS5", "LOS7", "LOS2", "LOS3", "SPLT"}   # LOS6 deduped, fund excluded
    assert t.loc["LOS1", "ret"] == pytest.approx(0.03, abs=1e-6) and t.loc["LOS1", "per"] == pytest.approx(0.10)
    assert t.loc["LOS4", "per"] == pytest.approx(0.05) and t.loc["LOS4", "gap"] == 0.5     # weekend
    assert t.loc["LOS5", "per"] == pytest.approx(0.05)                                      # holiday gap
    assert t.loc["LOS7", "per"] == pytest.approx(0.10)                                      # most beaten of the pair
    assert t.loc["LOS2", "kind"] == "delist_price" and t.loc["LOS2", "ret"] == pytest.approx(-0.5, abs=1e-6)
    assert t.loc["LOS3", "kind"] == "delist_nopx" and t.loc["LOS3", "ret"] == -1.0
    assert t.loc["SPLT", "ret"] == pytest.approx(0.03, abs=1e-4)      # split effective at that open does not fake -48%
    assert t.loc["SPLT", "cu"] == pytest.approx(t.loc["SPLT", "cu"]) and t.loc["SPLT", "cu"] > 30   # raw price used for cost tier


def test_secondary_universe_includes_fund(P):
    assert "FUND1" in trades(P, "secondary").index and "FUND1" not in trades(P, "primary").index


def test_gap_no_bar_without_delisting_is_minus_100(P):
    sep = pd.read_csv(P.raw / "SHARADAR_SEP.csv", parse_dates=["date"])
    nxt = SESS[list(SESS).index(E1) + 1]
    sep = sep[~((sep.ticker == "LOS1") & (sep.date == nxt))]           # halted: no bar, later bars exist
    sep.to_csv(P.raw / "SHARADAR_SEP.csv", index=False)
    (P.nx / "cache_SEP.parquet").unlink(missing_ok=True)
    t = trades(P, "primary")
    assert t.loc["LOS1", "kind"] == "nobar_halt" and t.loc["LOS1", "ret"] == -1.0


def test_leg_series_costs_and_verdict(P):
    col = nx.collect_trades(nx.build_panel(nx.load_bars(P, "2002-12-01", "2004-01-20")), nx.load_master(P),
                            nx.read_table(P, "ACTIONS"), "primary", D("2003-01-02"), D("2003-12-31"))
    tr, nights = col["trades"], col["nights"]
    g = nx.leg_series(tr, nights, "tier"); hi = nx.leg_series(tr, nights, "2x_tier_hi")
    from research.sim import book
    r = tr[tr.ticker == "LOS1"].iloc[0]
    c = float(book.cost_bps("tier", np.array([r.cu]), np.array([r.adv]))[0])
    assert c in (5.0, 7.5, 10.0, 15.0)
    assert g.loc[E1] == pytest.approx(0.10 * (0.03 - 2 * c / 1e4), abs=1e-6)
    assert hi.sum() < g.sum()
    base = {"mean": 1e-4, "t": 2.5, "sub": {"a": 1, "b": 1, "c": -1}, "med_trade": 1e-3, "ex5": 1e-5, "adj_mean": 1e-5}
    assert nx.verdict(base)[0] == "PASS"
    assert nx.verdict({**base, "ex5": -1})[0] == "WEAK"
    assert nx.verdict({**base, "t": 0.5})[0] == "FAIL" and nx.verdict({**base, "mean": -1})[0] == "FAIL"
    assert nx.verdict({**base, "sub": {"a": 1, "b": -1, "c": -1}})[0] == "WEAK"


def test_run_refusals_and_output(P):
    spec = spec_for(P)
    kw = dict(spec=spec, judge=(D("2003-01-02"), D("2003-12-31")), reported={})
    with pytest.raises(SystemExit, match="validate"):
        nx.run(P, **kw)                                                     # no sentinel
    mark_valid(P)
    text = nx.run(P, **kw)
    assert "VERDICT:" in text and P.out.exists() and "REPORTED ONLY" not in text
    s = json.loads(P.run_sentinel.read_text()); assert s["git"] and s["timestamp"]
    with pytest.raises(SystemExit, match="already run"):
        nx.run(P, **kw)
    assert "VERDICT:" in nx.run(P, force=True, **kw)


def test_run_refuses_after_failed_validate(P):
    P.nx.mkdir(parents=True, exist_ok=True)
    P.valid_sentinel.write_text(json.dumps({"ok": False}))
    with pytest.raises(SystemExit, match="did not pass"):
        nx.run(P, judge=(D("2003-01-02"), D("2003-12-31")), reported={})
