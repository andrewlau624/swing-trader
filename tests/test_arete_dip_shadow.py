import json

import numpy as np
import pandas as pd

from swingtrader.daily import arete_dip_shadow as W

N = 100
DATES = pd.bdate_range("2026-05-01", periods=N)
DAY = 90                       # signal session index (d+5 = 95 exists)


def _bars(close: np.ndarray, volume=2_000_000, rng=0.01) -> pd.DataFrame:
    return pd.DataFrame({"open": close, "high": close * (1 + rng), "low": close * (1 - rng), "close": close,
                         "volume": [volume] * N}, index=DATES)


def _universe():
    r = np.random.default_rng(0)
    bars = {f"S{i:02d}": _bars(50 * np.cumprod(1 + r.normal(0, 0.004, N))) for i in range(12)}
    bars["SPY"] = _bars(500 * np.cumprod(1 + np.full(N, 0.0005)))
    # HOT: strong, volatile uptrend, then a -4 % day closing on its low at DAY, then +3 %/day for 5 days
    hot = 20 * np.cumprod(1 + np.r_[r.normal(0.008, 0.03, DAY), [-0.04], np.full(N - DAY - 1, 0.03)])
    b = _bars(hot)
    b.iloc[DAY, b.columns.get_loc("low")] = hot[DAY]          # IBS = 0
    bars["HOT"] = b
    # same shape but cheap (< $5) and thin (< $20M) -> never eligible
    bars["CHEAP"] = _bars(hot / 10)
    bars["THIN"] = _bars(hot, volume=10)
    return bars


def test_pick_day_finds_the_profile_dip_and_respects_filters():
    Wd = W.wide(_universe())
    res = W.pick_day(str(DATES[DAY].date()), Wd)
    syms = [r["sym"] for r in res["rows"]]
    assert syms == ["HOT"]
    assert res["rows"][0]["ibs"] == 0.0 and res["rows"][0]["r1"] <= -0.02
    assert "CHEAP" not in syms and "THIN" not in syms


def test_no_pick_without_the_dip():
    Wd = W.wide(_universe())
    res = W.pick_day(str(DATES[DAY - 1].date()), Wd)
    assert "HOT" not in [r["sym"] for r in res["rows"]]


def test_score_is_excess_over_eligible_universe_net_of_cost():
    Wd = W.wide(_universe())
    row = W.pick_day(str(DATES[DAY].date()), Wd)["rows"][0]
    s = W.score(row, Wd)
    C = Wd["close"]
    el = W.eligible(DAY, Wd)
    want = C["HOT"].iloc[DAY + 5] / C["HOT"].iloc[DAY] - 1 - (C[el].iloc[DAY + 5] / C[el].iloc[DAY] - 1).mean() - W.COST
    assert s["status"] == "scored" and abs(s["xs5"] - want) < 1e-6 and s["xs3"] is not None


def test_score_waits_for_d_plus_5():
    Wd = W.wide({k: v.iloc[:DAY + 3] for k, v in _universe().items()})
    row = W.pick_day(str(DATES[DAY].date()), Wd)["rows"][0]
    assert W.score(row, Wd) is None


def test_verdict_thresholds():
    def rows(vals):
        return [dict(date=f"2026-11-{i:02d}", sym="X", status="scored", xs3=v, xs5=v) for i, v in enumerate(vals, 1)]
    assert W.verdict(W.summary(rows([0.01] * 10))) == ""                       # under NEED
    up = list(np.r_[np.full(W.NEED, 0.01)] + np.linspace(-0.004, 0.004, W.NEED))
    assert "PASS" in W.verdict(W.summary(rows(up)))
    assert "FAIL" in W.verdict(W.summary(rows([-0.001] * W.NEED)))


def test_run_end_to_end_with_fake_bars(tmp_path):
    bars = _universe()
    (tmp_path / "daily-universe-2026-09-01.json").write_text(json.dumps([{"symbol": s} for s in bars if s != "SPY"]))

    def bars_fn(syms, start, end):
        return {s: bars[s][(bars[s].index >= pd.Timestamp(start)) & (bars[s].index < pd.Timestamp(end))]
                for s in syms if s in bars}

    old = W.START
    W.START = str(DATES[DAY].date())
    try:
        # day after the signal: HOT is logged as pending; a week later the cached panel is extended and it is scored
        W.run(tmp_path, tmp_path, log=lambda *_: None, today=DATES[DAY + 1].date(), bars_fn=bars_fn)
        first = [json.loads(x) for x in (tmp_path / W.LOG_NAME).read_text().splitlines()]
        s = W.run(tmp_path, tmp_path, log=lambda *_: None, today=DATES[DAY + 7].date(), bars_fn=bars_fn)
    finally:
        W.START = old
    assert any(r.get("sym") == "HOT" and r["status"] == "pending" for r in first)
    lines = [json.loads(x) for x in (tmp_path / W.LOG_NAME).read_text().splitlines()]
    assert any(r.get("sym") == "HOT" and r["status"] == "scored" for r in lines)
    assert s["picks"] >= 1 and s["days"] >= 1
