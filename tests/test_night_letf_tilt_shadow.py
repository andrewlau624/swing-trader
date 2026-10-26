import datetime as dt
import json

import numpy as np
import pandas as pd

from swingtrader.daily import night_letf_tilt_shadow as W

N = 40
DATES = [str(d.date()) for d in pd.bdate_range("2026-09-01", periods=N)]
T = DATES[-2]


def _bars(close=20.0, volume=5_000_000, seed=0, skip=()):
    rng = np.random.default_rng(seed)
    idx = pd.DatetimeIndex([d for d in DATES if d not in skip])
    c = close * (1 + rng.normal(0, 0.01, len(idx))).cumprod()
    v = (volume * rng.uniform(0.5, 1.5, len(idx))).round()
    return pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99, "close": c, "volume": v}, index=idx)


def _ss_letf_I(T, sym, bars, funds):
    """Independent re-statement of research/sim/ss_letf.panel(): fund dv20 = shift(1).rolling(20, min 5).median per fund,
    fdv = sum(w x dv20) over funds with a row on T, udv20 = shift(1).rolling(20, min 15).median, I = fdv / udv20, NaN -> 0."""
    fp = pd.concat([bars[f].assign(ticker=f, w=w) for f, w in funds.items()]).reset_index(names="date").sort_values(["ticker", "date"])
    fp["dv"] = fp.close * fp.volume
    fp["dv20"] = fp.groupby("ticker").dv.transform(lambda s: s.shift(1).rolling(20, min_periods=5).median())
    fp["wdv"] = fp.w * fp.dv20
    fdv = fp.groupby("date").wdv.sum()
    b = bars[sym].copy()
    b["udv20"] = (b.close * b.volume).shift(1).rolling(20, min_periods=15).median()
    d = pd.Timestamp(T)
    v = fdv.get(d, np.nan) / b.udv20.loc[d]
    return 0.0 if np.isnan(v) else float(v)


def test_pressure_equals_the_ss_letf_formula(tmp_path):
    bars = {"UND": _bars(seed=1), "UNDL": _bars(close=30, volume=400_000, seed=2), "UNDS": _bars(close=10, volume=150_000, seed=3)}
    funds = {"UNDL": 1.0, "UNDS": 3.0}                       # 2x long (w 1) and -2x (w 3)
    fmap = {"UND": funds}
    p = W.pressure(T, "UND", bars, fmap)
    want = _ss_letf_I(T, "UND", bars, funds)
    assert p["n_funds"] == 2 and want > 0 and abs(p["I"] - want) < 1e-5
    # a fund with no bar on T does not count (the panel's (fund, date) merge), the other still does
    bars2 = dict(bars, UNDS=_bars(close=10, volume=150_000, seed=3, skip=(T,)))
    p2 = W.pressure(T, "UND", bars2, fmap)
    assert p2["n_funds"] == 1 and abs(p2["I"] - _ss_letf_I(T, "UND", bars2, {"UNDL": 1.0})) < 1e-5 and p2["I"] < p["I"]
    # no funds -> I = 0; too little history -> I = 0
    assert W.pressure(T, "UND", bars, {})["I"] == 0.0
    short = {"UND": bars["UND"].iloc[-10:], "UNDL": bars["UNDL"]}
    assert W.pressure(T, "UND", short, fmap)["I"] == 0.0 and W.pressure(T, "UND", short, fmap)["udv20"] is None


def test_map_round_trip(tmp_path):
    p = tmp_path / "letf_map.csv"
    p.write_text("# built today\nfund,underlying,lev,w,sign,name\nABCL,ABC,2.0,1.0,1,X 2X LONG ABC\nABCS,ABC,-2.0,3.0,-1,X 2X SHORT ABC\n")
    assert W.load_map(p) == {"ABC": {"ABCL": 1.0, "ABCS": 3.0}}
    assert W.load_map(tmp_path / "missing.csv") == {}


def _pick(Tn, sym, I, ret, backfill=False, status="scored"):
    return dict(T=Tn, sym=sym, I=I, tilt=I >= W.I_MIN, backfill=backfill, status=status, ret=ret)


def test_summary_and_line():
    rows = [_pick("2026-11-02", "A", 0.10, 0.02), _pick("2026-11-02", "B", 0.0, 0.01), _pick("2026-11-02", "C", 0.02, 0.0),
            _pick("2026-11-03", "A", 0.06, 0.03), _pick("2026-11-03", "D", 0.0, -0.01),
            _pick("2026-11-04", "E", 0.0, 0.005),                                     # night without a tilt pick
            _pick("2026-11-05", "A", 0.2, 0.01), _pick("2026-11-05", "F", 0.0, 0.0),
            _pick("2026-11-06", "G", 0.3, 0.0, status="pending"),
            _pick("2026-10-20", "H", 0.3, 0.05, backfill=True), _pick("2026-10-20", "J", 0.0, 0.0, backfill=True)]
    s = W.summary(rows)
    assert s["picks"] == 8 and s["pending"] == 1 and s["tilt_nights"] == 3
    assert s["tilt"]["n"] == 3 and s["tilt"]["nights"] == 3 and abs(s["tilt"]["ew_bp"] - 200.0) < 1e-6
    assert s["rest"]["n"] == 5 and abs(s["rest"]["ew_bp"] - 1e4 * np.mean([0.005, -0.01, 0.005, 0.0])) < 1e-6
    assert s["zero"]["n"] == 4 and s["low"]["n"] == 1
    p = s["paired"]
    assert p["nights"] == 3 and abs(p["mean_bp"] - 1e4 * np.mean([0.015, 0.04, 0.01])) < 0.1 and p["hit"] == 1.0
    assert abs(s["tilt"]["net_bp"] - (200.0 - W.RT_BP)) < 1e-6
    b = W.summary(rows, True)
    assert b["picks"] == 2 and b["paired"]["nights"] == 1 and abs(b["paired"]["mean_bp"] - 500.0) < 1e-6
    ln = W.line(rows)
    assert "3/40 tilt nights" in ln and "paired tilt-rest" in ln
    assert "0 forward picks" in W.line([r for r in rows if r["backfill"]])


def test_verdict_at_the_gate():
    rows = [_pick(d, "A", 0.1, 0.01) for d in DATES] + [_pick(d, "B", 0.0, 0.0 + 0.0001 * i) for i, d in enumerate(DATES)]
    s = W.summary(rows)
    assert s["tilt_nights"] == 40 and "PASS" in W.verdict(s)
    rows = [_pick(d, "A", 0.1, 0.0) for d in DATES] + [_pick(d, "B", 0.0, 0.01) for d in DATES]
    assert "FAIL" in W.verdict(W.summary(rows))


def test_run_tags_scores_from_candidates_and_is_idempotent(tmp_path):
    state = tmp_path / "state"
    state.mkdir()
    mp = tmp_path / "letf_map.csv"
    mp.write_text("fund,underlying,lev,w,sign,name\nAAAL,AAA,2.0,1.0,1,n\nAAAS,AAA,-2.0,3.0,-1,n\n")
    bars = {"AAA": _bars(seed=1), "AAAL": _bars(close=30, volume=2_000_000, seed=2), "AAAS": _bars(close=10, volume=900_000, seed=3),
            "BBB": _bars(seed=4)}
    T0, T1 = DATES[-3], DATES[-2]
    cands = [dict(date=T0, sym="AAA", account="live", price=20, day_ret=-0.09, ibs=0.05, status="scored", exit=DATES[-2],
                  close_cross=20.0, open_cross=20.4, ret=0.02),
             dict(date=T0, sym="BBB", account="live", price=20, day_ret=-0.1, ibs=0.02, status="scored", exit=DATES[-2],
                  close_cross=10.0, open_cross=10.05, ret=0.005),
             dict(date=T1, sym="AAA", account="roth", price=20, day_ret=-0.085, ibs=0.01, status="pending"),
             dict(date=DATES[-1], sym="BBB", account="live", price=20, day_ret=-0.09, ibs=0.03, status="pending")]   # today: not yet
    (state / "night-candidates.jsonl").write_text("".join(json.dumps(c) + "\n" for c in cands))
    today = dt.date.fromisoformat(DATES[-1])
    pulled = []

    def bars_fn(syms, start, end=None):
        pulled.extend(syms)
        return {s: bars[s] for s in syms if s in bars}

    W.START_T, old = T0, W.START_T
    try:
        s = W.run(state, tmp_path, log=lambda *_: None, today=today, bars_fn=bars_fn, map_path=mp)
        rows = [json.loads(x) for x in (state / W.LOG_NAME).read_text().splitlines()]
        assert set(pulled) == {"AAA", "BBB", "AAAL", "AAAS"}
        picks = {(r["T"], r["sym"]): r for r in rows if r.get("sym")}
        assert set(picks) == {(T0, "AAA"), (T0, "BBB"), (T1, "AAA")}
        assert picks[(T0, "AAA")]["tilt"] and picks[(T0, "AAA")]["n_funds"] == 2 and picks[(T0, "AAA")]["I"] > 0.05
        assert not picks[(T0, "BBB")]["tilt"] and picks[(T0, "BBB")]["I"] == 0.0 and picks[(T0, "BBB")]["n_funds"] == 0
        assert picks[(T0, "AAA")]["status"] == "scored" and abs(picks[(T0, "AAA")]["ret"] - 0.02) < 1e-9
        assert abs(picks[(T0, "AAA")]["net"] - (0.02 - 0.001)) < 1e-9 and picks[(T0, "AAA")]["o1"] == 20.4
        assert picks[(T1, "AAA")]["status"] == "pending" and picks[(T1, "AAA")]["account"] == "roth"
        nights = {r["T"]: r for r in rows if r["status"] == "night"}
        assert nights[T0]["n_picks"] == 2 and nights[T0]["n_tilt"] == 1 and nights[T1]["n_tilt"] == 1
        assert s["tilt_nights"] == 1 and s["paired"]["nights"] == 1 and abs(s["paired"]["mean_bp"] - 150.0) < 1e-6
        # next morning: repeat_shadow scored the T1 candidate; no bars are pulled again, the score is copied
        cands[2].update(status="scored", exit=DATES[-1], close_cross=20.0, open_cross=19.8, ret=-0.01)
        (state / "night-candidates.jsonl").write_text("".join(json.dumps(c) + "\n" for c in cands))
        pulled.clear()
        s2 = W.run(state, tmp_path, log=lambda *_: None, today=today + dt.timedelta(days=1), bars_fn=bars_fn, map_path=mp)
        rows2 = [json.loads(x) for x in (state / W.LOG_NAME).read_text().splitlines()]
        assert len(rows2) == len(rows) + 2 and set(pulled) == {"BBB"}            # today's BBB becomes yesterday's pick
        p1 = next(r for r in rows2 if r.get("sym") == "AAA" and r["T"] == T1)
        assert p1["status"] == "scored" and abs(p1["ret"] + 0.01) < 1e-9 and s2["tilt_nights"] == 2
    finally:
        W.START_T = old


def test_backfill_rows_are_labelled_and_not_gated(tmp_path):
    state = tmp_path / "state"
    state.mkdir()
    mp = tmp_path / "letf_map.csv"
    mp.write_text("fund,underlying,lev,w,sign,name\nAAAL,AAA,2.0,1.0,1,n\n")
    bars = {"AAA": _bars(seed=1), "AAAL": _bars(close=30, volume=2_000_000, seed=2)}
    T0 = DATES[-3]
    (state / "night-candidates.jsonl").write_text(json.dumps(dict(date=T0, sym="AAA", account="live", price=20, day_ret=-0.09,
                                                                  ibs=0.05, status="scored", ret=0.02)) + "\n")
    today = dt.date.fromisoformat(DATES[-1])
    s = W.run(state, tmp_path, log=lambda *_: None, today=today, bars_fn=lambda syms, start, end=None: {k: bars[k] for k in syms if k in bars},
              map_path=mp, backfill=5)
    rows = [json.loads(x) for x in (state / W.LOG_NAME).read_text().splitlines()]
    assert all(r["backfill"] for r in rows) and s["picks"] == 0 and W.summary(rows, True)["picks"] == 1
    assert "0 forward picks" in W.line(rows) and "backfill 1 picks" in W.line(rows)
