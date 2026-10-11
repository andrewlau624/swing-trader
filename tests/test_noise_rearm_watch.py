import datetime as dt
import json

import numpy as np
import pandas as pd

from swingtrader.daily import noise_rearm_watch as W
from swingtrader.daybook import shadow as sh


def _sessions(n_days, seed, drift=0.0):
    """Synthetic {date: {close, volume, open}} sessions with enough movement for breakouts."""
    rng = np.random.default_rng(seed)
    out = {}
    px = 100.0
    for i in range(n_days):
        d = pd.Timestamp("2026-06-01") + pd.offsets.BDay(i)
        steps = rng.normal(drift, 0.0008, 390)
        c = px * np.cumprod(1 + steps)
        out[d] = {"close": c, "volume": np.full(390, 1000.0), "open": float(c[0])}
        px = float(c[-1])
    return out


def test_lag_zero_is_the_default_and_lag_moves_fills_one_bar():
    S = _sessions(40, 1, drift=0.00004)
    cfg = sh.CFGS["PROD"]
    day = sorted(S)[-1]
    base = sh.replay_instrument(S, cfg, "QQQ", 0.5, day)
    same = sh.replay_instrument(S, cfg, "QQQ", 0.5, day, lag=0)
    assert base == same
    lagged = sh.replay_instrument(S, cfg, "QQQ", 0.5, day, lag=30)
    assert base, "synthetic day should produce at least one trade"
    C = S[day]["close"]
    for t in lagged:
        m = t["entry_minute"]
        assert t["observed_entry"] == round(float(C[min(m + 30, cfg.close_min)]), 4)
        assert t["exit_minute"] <= cfg.close_min


def test_stats_and_positive_rule():
    days = [pd.Timestamp("2026-09-01") + pd.offsets.BDay(i) for i in range(60)]
    df = pd.DataFrame(dict(date=[days[i % 60] for i in range(40)], sym="QQQ", dir=1, gross=[6.0] * 40, lev=1.0))
    base, shock = W.stats(df, days, 0.5), W.stats(df, days, 2.0)
    assert base["n"] == 40 and base["mean"] == 5.0 and shock["mean"] == 2.0 and base["sharpe"] > 0.5
    assert W.positive(base, shock)
    assert not W.positive(dict(base, n=10), shock)                 # too few trades
    assert not W.positive(base, dict(shock, mean=-0.5))             # dies at the cost shock
    assert not W.positive(dict(base, sharpe=0.2), shock)            # Sharpe below the bar
    assert W.stats(df.iloc[:0], days, 0.5)["n"] == 0


def test_run_logs_one_row_a_week_and_never_more(tmp_path):
    S = {"QQQ": _sessions(80, 2), "SMH": _sessions(80, 3)}
    out = []
    r = W.run(tmp_path, tmp_path, log=out.append, today=dt.date(2026, 10, 12), S=S)
    assert r is not None and r["sessions"] == 60 and r["lag"] == 30 and "positive" in r
    rows = [json.loads(x) for x in (tmp_path / W.LOG_NAME).read_text().splitlines()]
    assert len(rows) == 1 and rows[0]["end"] > rows[0]["start"]
    assert W.run(tmp_path, tmp_path, log=out.append, today=dt.date(2026, 10, 14), S=S) is None   # 2 days later: skip
    assert len((tmp_path / W.LOG_NAME).read_text().splitlines()) == 1
    assert W.run(tmp_path, tmp_path, log=out.append, today=dt.date(2026, 10, 19), S=S) is not None  # a week later: new row
    assert "re-arm" in W.line(rows) and ("OFF" in W.line(rows) or "candidate" in W.line(rows))
    assert any("[noise-rearm]" in x for x in out)
