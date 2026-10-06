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


def test_payout_counts_cash_in_lieu_when_the_cap_set_the_ratio():
    s = dict(held=10, cost=859.30)
    p = b.payout(s, 45, 19.56, 4.5939)                     # 10 x 4.5939 = 45.939 -> 45 shares + 0.939 in cash
    assert p["cash_in_lieu"] == round(0.939 * 19.56, 2)
    assert p["pnl"] == round(45.939 * 19.56 - 859.30, 2)
    q = b.payout(s, 47, 19.56, 4.5939)                     # cap did not bind: fraction unknown, left out
    assert q["cash_in_lieu"] is None and q["pnl"] == round(47 * 19.56 - 859.30, 2)


def test_track_tendered_to_delivered_reopens_a_wrong_missed_and_completes_the_ledger(tmp_path):
    import json
    from types import SimpleNamespace as NS
    from swingtrader.daily import cpc_ledger as L
    from swingtrader.daily.splitoff_watch import LOG_NAME
    (tmp_path / LOG_NAME).write_text(json.dumps(dict(MDT, date="2026-10-02")) + "\n")
    led = tmp_path / L.LOG_NAME
    at = dt.datetime(2026, 10, 4, 19, tzinfo=dt.timezone(dt.timedelta(hours=-4)))
    L.add_event(led, dict(family="SPLIT_OFF", issuer="MDT", security="MDT->MMED", event_date="2026-10-02",
                          deadline="2026-10-09T16:00:00-04:00", status="ACTION_REQUIRED"), now=at)
    eid = "SPLIT-OFF:MDT:2026-10-02"
    L.failed(led, eid, "MISSED", note="declined", now=at)
    (tmp_path / b.ORDERS_NAME).write_text(json.dumps({"MDT-2026-10-09": dict(
        ticker="MDT", recv="MMED", expires="2026-10-09", status="bought", account="roth", qty=10, held=10,
        cost=859.30, bought="2026-10-06")}))

    class Ad:
        def __init__(self, pos): self.pos = pos
        def positions(self): return self.pos
    mails = []
    b.track(tmp_path, dt.date(2026, 10, 7), adapters={"roth": Ad({})}, log=lambda *_: None)
    o = json.loads((tmp_path / b.ORDERS_NAME).read_text())["MDT-2026-10-09"]
    assert o["status"] == "tendered" and o["recv_before"] == 0.0
    b.track(tmp_path, dt.date(2026, 10, 13), adapters={"roth": Ad({"MMED": NS(qty=45.0, current_price=20.0)})},
            notify=lambda subj, html: mails.append(subj), log=lambda *_: None)
    o = json.loads((tmp_path / b.ORDERS_NAME).read_text())["MDT-2026-10-09"]
    assert o["status"] == "delivered" and o["pnl"] == round(45.939 * 20.0 - 859.30, 2) and o["ledger"] == eid
    e = L.fold(L.read(led))[eid]
    assert e["status"] == "COMPLETED" and e["realized_pnl"] == o["pnl"]
    assert [h["rec"] for h in e["history"]] == ["transition", "reopen", "transition"]
    assert mails and "payout" in mails[0]
    b.track(tmp_path, dt.date(2026, 10, 14), adapters={"roth": Ad({"MMED": NS(qty=45.0, current_price=21.0)})},
            log=lambda *_: None)                                  # delivered is final: no second ledger write
    assert L.fold(L.read(led))[eid]["realized_pnl"] == o["pnl"]
