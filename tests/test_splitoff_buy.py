"""Round 32 B2 approved split-off buy: the plan re-checks gain, time to expiry and the 99-share total. No network."""
import datetime as dt

from swingtrader.daily import splitoff_buy as b

MDT = dict(parent="MDT", recv="MMED", expires="2026-10-09", per100=107.53, cap=4.5939)
TODAY = dt.date(2026, 10, 2)


def test_plan_buys_up_to_99_roth_first():
    p, why = b.plan(MDT, {"roth": 0, "live": 0}, {"roth": 500.0, "live": 9000.0}, 86.44, 19.60, TODAY)
    assert why == "" and p["account"] == "roth" and p["qty"] == 5 and p["implied"] > 0.04
    p, _ = b.plan(MDT, {"roth": 0, "live": 0}, {"roth": 0.0, "live": 9000.0}, 86.44, 19.60, TODAY)
    assert p["account"] == "live" and p["qty"] == 99


def test_plan_refuses():
    assert b.plan(MDT, {"live": 99}, {"live": 9e3}, 86.44, 19.60, TODAY)[0] is None          # already 99
    assert b.plan(MDT, {"live": 0}, {"live": 9e3}, 86.44, 18.50, TODAY)[0] is None           # capped gain < 1%
    assert b.plan(MDT, {"live": 0}, {"live": 9e3}, 86.44, 19.60, dt.date(2026, 10, 7))[0] is None   # too late
