import datetime as dt
import json

import numpy as np
import pandas as pd

from swingtrader.daily import ovn_mom_shadow as W

N = 300
DATES = [str(d.date()) for d in pd.bdate_range("2025-06-02", periods=N)]
DAY = DATES[-3]            # signal day with two later sessions in the frame


def _bars(drift, volume=5_000_000, close=20.0):
    """close flat at `close`; open = close_prev*(1+drift) so each overnight return == drift."""
    idx = pd.DatetimeIndex(DATES)
    c = np.full(N, close)
    o = np.r_[close, c[:-1] * (1 + drift)]
    return pd.DataFrame({"open": o, "high": o, "low": o, "close": c, "volume": [volume] * N}, index=idx)


def _universe():
    # 20 names with increasing drift; HOT is the best score; FUNDX is a fund and is skipped
    bars = {f"S{i:02d}": _bars(0.0001 * i) for i in range(20)}
    bars["FUNDX"] = _bars(0.01)
    bars["CHEAP"] = _bars(0.005, close=3.0)         # < $5
    bars["THIN"] = _bars(0.005, volume=100)         # < $20M
    return bars


def test_score_uses_only_nights_ending_at_signal_open_and_decile():
    bars = _universe()
    # a huge overnight AFTER the signal day must not change the ranking: make S00 jump on the last night
    b = bars["S00"].copy()
    b.iloc[-1, b.columns.get_loc("open")] = 29.8
    bars["S00"] = b
    R, C, U = W.wide(bars)
    res = W.pick_day(DAY, R, C, U, fund=lambda s: s == "FUNDX")
    assert res["n_elig"] == 20
    syms = [r["sym"] for r in res["rows"]]
    assert syms == ["S19", "S18"]                      # decile of 20 = 2, best score first
    assert res["rows"][0]["top10"] and res["rows"][0]["decile"]
    assert abs(res["rows"][0]["score"] - 0.0019) < 1e-6
    assert "FUNDX" not in syms and "CHEAP" not in syms and "THIN" not in syms
    # the same window ending 2 sessions later (jump included) would rank S00 first
    late = W.pick_day(DATES[-1], R, C, U, fund=lambda s: s == "FUNDX")
    assert late["rows"][0]["sym"] == "S00"


def test_score_row_excess_vs_spy():
    X = {"AAA": {"2026-10-08": (18.0, 1, 20.0, 1), "2026-10-09": (20.2, 1, 20.0, 1)},
         "SPY": {"2026-10-08": (500.0, 1, 500.0, 1), "2026-10-09": (501.0, 1, 502.0, 1)}}
    r = W.score(dict(date="2026-10-08", sym="AAA", status="pending"), X)
    assert r["exit"] == "2026-10-09" and abs(r["ret"] - 0.01) < 1e-9
    assert abs(r["bench"] - 0.002) < 1e-9 and abs(r["xs"] - 0.008) < 1e-9
    assert W.score(dict(date="2026-10-09", sym="AAA", status="pending"), X) is None


def test_line_gate():
    rows = []
    for i in range(W.NEED):
        d = str(dt.date(2026, 10, 1) + dt.timedelta(days=i))
        rows.append(dict(date=d, sym="A", rank=1, top10=True, status="scored", xs=0.0010 + (0.0004 if i % 2 else -0.0004)))
    assert W.line(rows).endswith("-> PASS (mean >= +5bp, t >= 2, median > 0)")
    assert "-> FAIL" in W.line([dict(r, xs=-r["xs"]) for r in rows])
    assert W.line(rows[:10]).startswith("10/120 nights")


def test_run_scans_scores_and_is_idempotent(tmp_path, monkeypatch):
    bars = _universe()
    (tmp_path / "daily-universe-2026-01-01.json").write_text(json.dumps([{"symbol": s} for s in bars if s != "FUNDX"]))
    monkeypatch.setattr(W, "START", DATES[-3])
    today = pd.Timestamp(DATES[-1]).date()
    bars["SPY"] = _bars(0.0)

    def bars_fn(syms, start, end=None):
        return {s: bars[s] for s in syms if s in bars}

    X = {s: {DATES[-3]: (None, None, 20.0, 1), DATES[-2]: (20.1, 1, 20.0, 1)} for s in bars}
    crosses_fn = lambda syms, a, b, H: {s: X[s] for s in syms if s in X}  # noqa: E731
    out = W.run(tmp_path, tmp_path, log=lambda *_: None, today=today, H={}, bars_fn=bars_fn, crosses_fn=crosses_fn,
                fund_fn=lambda s: False)
    rows = [json.loads(x) for x in (tmp_path / W.LOG_NAME).read_text().splitlines()]
    picks = [r for r in rows if "sym" in r]
    assert {r["date"] for r in rows} == {DATES[-3], DATES[-2]}
    assert picks and all(r["status"] == "scored" for r in picks if r["date"] == DATES[-3])
    assert out["days"] >= 1 and (tmp_path / W.PANEL).exists()
    before = (tmp_path / W.LOG_NAME).read_text()
    W.run(tmp_path, tmp_path, log=lambda *_: None, today=today, H={}, bars_fn=bars_fn, crosses_fn=crosses_fn, fund_fn=lambda s: False)
    assert (tmp_path / W.LOG_NAME).read_text() == before
