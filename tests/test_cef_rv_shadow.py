import datetime as dt

import numpy as np
import pandas as pd

from swingtrader.daily import cef_rv_shadow as W


def _weekly(n, seed):
    rng = np.random.default_rng(seed)
    dates = [str(dt.date(2020, 1, 3) + dt.timedelta(weeks=i)) for i in range(n)]
    disc = list(np.cumsum(rng.normal(0, 0.01, n)) - 0.08)
    return dates, disc


def test_signals_match_the_research_trade_builder():
    from research.sim.cef_rv import build_trades
    for seed in range(5):
        dates, disc = _weekly(260, seed)
        nav = pd.DataFrame(dict(ticker="AAA", date=pd.to_datetime(dates), disc=disc))
        days = pd.to_datetime(dates) + pd.Timedelta(days=3)            # a session after every weekly point
        fS = pd.DataFrame(dict(ticker="AAA", dt=days, closeadj=1.0, close=1.0, closeunadj=1.0))
        tr = build_trades(nav, fS)
        sg = [s for s in W.signals(dates, disc) if s["exit_signal"]]
        assert [s["signal"] for s in sg] == [str(x)[:10] for x in tr["edate"]]
        assert [s["exit_signal"] for s in sg] == [str(x)[:10] for x in tr["xdate"]]


def test_score_prices_at_the_auctions_after_each_signal_and_adds_distributions():
    X = {"AAA": {"2026-10-12": (10.0, 1, 10.1, 1), "2026-10-13": (10.2, 1, 10.2, 1),
                 "2026-11-16": (10.6, 1, 10.7, 1)}}
    divs = {"AAA": [("2026-10-20", 0.1), ("2026-12-01", 0.1)]}
    t = W.score(dict(sym="AAA", signal="2026-10-09", exit_signal="2026-11-13"), X, divs)
    assert t["status"] == "closed" and t["entry"] == "2026-10-12" and t["exit"] == "2026-11-16"
    assert abs(t["oo"] - ((10.6 + 0.1) / 10.0 - 1)) < 1e-12
    assert abs(t["cc"] - ((10.7 + 0.1) / 10.1 - 1)) < 1e-12
    assert W.score(dict(sym="AAA", signal="2026-10-09", exit_signal=None), X, divs)["status"] == "open"
    assert W.score(dict(sym="AAA", signal="2026-11-20", exit_signal=None), X, divs)["status"] == "pending"


def test_ew_comparator_and_the_gate_line():
    X = {"A": {"d1": (1, 1, 10.0, 1), "d2": (1, 1, 11.0, 1)}, "B": {"d1": (1, 1, 10.0, 1), "d2": (1, 1, 9.0, 1)},
         "C": {"d1": (1, 1, 10.0, 1)}}
    m, n = W.ew(X, {}, "d1", "d2")
    assert n == 2 and abs(m) < 1e-12
    rows = [dict(sym=f"S{i}", signal=f"2026-{11 + i % 2}-{1 + i % 20:02d}", status="closed",
                 x_oo=0.01 + 0.001 * (i % 5), x_cc=0.005, net_oo=0.03) for i in range(60)]
    assert W.line(rows).endswith("PASS (excess >= +60bp, t >= 2, median > 0)")
    assert "KILL" in W.line([dict(r, x_oo=-r["x_oo"]) for r in rows])
    assert "PASS" not in W.line(rows[:59]) and "KILL" not in W.line(rows[:59])      # below NEED: no verdict


def test_cut42_flags_a_cut_after_three_stable_payouts_within_42_days():
    from swingtrader.daily import cef_rv_shadow as W
    h = [("2026-05-15", 0.10), ("2026-06-15", 0.10), ("2026-07-15", 0.101), ("2026-08-14", 0.08)]
    assert W.cut42(h, "2026-09-20") is True                       # 37 days after the cut
    assert W.cut42(h, "2026-10-01") is False                      # 48 days: outside the window
    assert W.cut42(h[1:], "2026-09-20") is False                  # only 2 priors: not a qualifying cut
    assert W.cut42(h[:3] + [("2026-08-14", 0.095)], "2026-09-20") is False   # -5% is not a cut
