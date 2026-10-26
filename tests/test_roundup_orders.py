"""Round 32 B1 automatic round-up buys: buy once per account before the ex-date, sell only once the post-split share
shows (>= 2 days after), cash-in-lieu after 21 days, kill switch after 2 cash outcomes. Fake broker, no network."""
import datetime as dt
from types import SimpleNamespace

from swingtrader.daily import roundup_orders as ro

ALERT = dict(ticker="VIVK", trade_date="2026-10-05", buy_by="2026-10-02", ratio=15.0, last_close=0.3181)


class Fake:
    def __init__(self, held=None):
        self.held = held or {}

    def positions(self):
        return {s: SimpleNamespace(qty=q, current_price=1.0) for s, q in self.held.items()}


def run(tmp, day, ads, alerts=(ALERT,)):
    calls = []
    st = ro.manage(tmp, list(alerts), dt.date.fromisoformat(day), adapters=ads, prices={"VIVK": 0.2983},
                   placer=lambda ad, sym, side, lim=None: calls.append((sym, side, lim)) or "id", log=lambda *a: None)
    return st, calls


def test_buys_one_share_per_account_once(tmp_path):
    ads = {"live": Fake(), "roth": Fake()}
    st, calls = run(tmp_path, "2026-10-02", ads)
    assert [(c[0], c[1]) for c in calls] == [("VIVK", "buy"), ("VIVK", "buy")]
    assert calls[0][2] == 0.3043                          # ask + 2%, 4 decimals under $1 (Schwab rejects far limits)
    _, again = run(tmp_path, "2026-10-02", ads)
    assert again == []                                    # never twice


def test_no_buy_after_buy_by_or_if_already_held(tmp_path):
    _, calls = run(tmp_path, "2026-10-05", {"live": Fake()})
    assert calls == []
    other = tmp_path / "other"
    other.mkdir()
    _, calls = run(other, "2026-10-02", {"live": Fake({"VIVK": 3})})
    assert calls == []


def test_sell_only_after_split_settles_then_cash_and_kill(tmp_path):
    live = Fake()
    run(tmp_path, "2026-10-02", {"live": live})
    live.held = {"VIVK": 1}
    st, calls = run(tmp_path, "2026-10-05", {"live": live})          # ex-date: decide nothing
    assert calls == [] and st["VIVK-2026-10-05"]["live"]["status"] == "waiting"
    st, calls = run(tmp_path, "2026-10-07", {"live": live})
    assert calls == [("VIVK", "sell", None)] and st["VIVK-2026-10-05"]["live"]["status"] == "sold"
    # two later deals paid in cash -> the account is not killed because one was rounded
    for t, ex in (("AAA", "2026-11-02"), ("BBB", "2026-11-09")):
        a = dict(ALERT, ticker=t, trade_date=ex, buy_by="2026-10-30")
        ro.manage(tmp_path, [a], dt.date(2026, 10, 30), adapters={"live": Fake()}, prices={t: 0.5},
                  placer=lambda *k, **kw: "id", log=lambda *k: None)
    st, _ = run(tmp_path, "2026-12-15", {"live": Fake()}, alerts=())
    assert st["AAA-2026-11-02"]["live"]["status"] == "cash" and not ro.killed(st, "live")


def test_kill_switch_after_two_cash_and_no_rounded():
    st = {"A-1": {"roth": {"status": "cash"}}, "B-2": {"roth": {"status": "cash"}}, "C-3": {"live": {"status": "sold"}}}
    assert ro.killed(st, "roth") and not ro.killed(st, "live")


def test_resolved_deal_books_payout_per_account_then_the_ledger(tmp_path, monkeypatch):
    from swingtrader.daily import cpc_ledger as L
    led = tmp_path / L.LOG_NAME
    at = dt.datetime(2026, 9, 30, 9, tzinfo=dt.timezone(dt.timedelta(hours=-4)))
    eid = L.add_event(led, dict(family="REVERSE_SPLIT_ROUNDUP", issuer="VIVK", security="VIVK",
                                event_date="2026-10-05", deadline="2026-10-02T16:00:00-04:00",
                                status="ACTION_REQUIRED"), now=at)[1]["event_id"]

    class Filled(Fake):
        fills = {"id": 0.30, "sell": 4.20}
        c = None
        def order_status(self, coid, info):
            px = self.fills.get(info["broker_id"])
            return ("filled", 1.0, px, "") if px else ("new", 0.0, 0.0, "")
    live, roth = Filled(), Filled()
    run(tmp_path, "2026-10-02", {"live": live, "roth": roth})
    live.held, roth.held = {"VIVK": 1}, {}
    calls = []
    st = ro.manage(tmp_path, [ALERT], dt.date(2026, 10, 7), adapters={"live": live, "roth": roth},
                   prices={"VIVK": 0.2983}, placer=lambda *a, **k: calls.append(a) or "sell", log=lambda *a: None)
    d = st["VIVK-2026-10-05"]
    assert d["live"]["status"] == "sold" and d["live"]["pnl"] == round(4.20 - 0.30, 2)
    assert d["roth"]["status"] == "waiting" and "booked" not in d["live"]    # roth unresolved: no ledger yet
    assert L.fold(L.read(led))[eid]["status"] == "ACTION_REQUIRED"
    monkeypatch.setattr(ro, "ask", lambda ad, sym: 4.50)                     # quote for the cash-in-lieu estimate
    st = ro.manage(tmp_path, [ALERT], dt.date(2026, 10, 27), adapters={"live": live, "roth": roth},
                   prices={"VIVK": 0.2983}, placer=lambda *a, **k: "x", log=lambda *a: None)
    d = st["VIVK-2026-10-05"]
    assert d["roth"]["status"] == "cash" and d["roth"]["est"] and d["roth"]["pnl"] == round(4.50 / 15 - 0.30, 2)
    e = L.fold(L.read(led))[eid]
    assert e["status"] == "COMPLETED" and e["realized_pnl"] == round(d["live"]["pnl"] + d["roth"]["pnl"], 2)
    assert d["live"]["booked"] == eid and d["roth"]["booked"] == eid


# ---- 2026-10-26: every account x deal decision is an outcome row; GTC mode (config daily.roundup_order_mode)
def test_outcomes_name_the_reason_for_every_no_order(tmp_path):
    oc = []
    def placer(ad, sym, side, lim=None, **kw):
        raise RuntimeError("Schwab rejected buy 1 VIVK: 400 price too far from market")
    ro.manage(tmp_path, [ALERT], dt.date(2026, 10, 2), adapters={"live": Fake(), "roth": Fake({"VIVK": 1})},
              prices={"VIVK": 0.2983}, placer=placer, log=lambda *a: None, outcomes=oc)
    by = {o["account"]: o for o in oc}
    assert by["live"]["outcome"] == "no-order" and "Schwab rejected" in by["live"]["reason"]
    assert by["roth"]["reason"] == "already held in the account"
    oc = []
    ro.manage(tmp_path, [ALERT], dt.date(2026, 10, 2), adapters={"live": Fake()}, prices={"VIVK": None},
              placer=lambda *a, **k: "id", log=lambda *a: None, outcomes=oc)
    assert oc[0]["reason"].startswith("no usable quote")
    oc = []
    ro.manage(tmp_path, [ALERT], dt.date(2026, 10, 2), adapters={"live": Fake()}, prices={"VIVK": 30.0},
              placer=lambda *a, **k: "id", log=lambda *a: None, outcomes=oc)
    assert "above the $25 cap" in oc[0]["reason"]
    oc = []
    ro.manage(tmp_path, [ALERT], dt.date(2026, 10, 2), adapters={"live": Fake()}, prices={"VIVK": 0.2983},
              placer=lambda *a, **k: "id7", log=lambda *a: None, outcomes=oc)
    assert oc[0]["outcome"] == "order-placed" and oc[0]["order_id"] == "id7" and oc[0]["gtc"] is False
    assert all(o["ticker"] == "VIVK" and o["trade_date"] == "2026-10-05" for o in oc)


def test_daily_cap_and_unconfirmed_are_outcomes(tmp_path):
    alerts = [dict(ALERT, ticker=t) for t in ("A1", "A2", "A3", "A4")] + [dict(ALERT, ticker="UNC", unconfirmed=True)]
    oc, calls = [], []
    ro.manage(tmp_path, alerts, dt.date(2026, 10, 2), adapters={"live": Fake()}, prices={t: 0.5 for t in "A1 A2 A3 A4".split()},
              placer=lambda ad, sym, side, lim=None, **k: calls.append(sym) or "id", log=lambda *a: None, outcomes=oc)
    assert calls == ["A1", "A2", "A3"]
    assert [o["ticker"] for o in oc if o["outcome"] == "no-order"] == ["A4"] and "daily cap" in oc[-1]["reason"]
    assert not any(o["ticker"] == "UNC" for o in oc)             # unconfirmed names are never bought


def test_gtc_mode_places_at_or_below_the_last_close_and_cancels_on_the_ex_date(tmp_path):
    calls, oc = [], []
    def placer(ad, sym, side, lim=None, gtc=False):
        calls.append((sym, side, lim, gtc)); return "11"
    live = Fake()
    st = ro.manage(tmp_path, [ALERT], dt.date(2026, 9, 29), adapters={"live": live}, prices={"VIVK": 0.35},
                   placer=placer, log=lambda *a: None, outcomes=oc, mode="gtc")
    assert calls == [("VIVK", "buy", 0.3181, True)]              # ask 0.35 > last close: limit = the last close
    assert st["VIVK-2026-10-05"]["live"]["gtc"] and oc[0]["gtc"] is True
    st = ro.manage(tmp_path, [ALERT], dt.date(2026, 10, 1), adapters={"live": live}, prices={"VIVK": 0.35},
                   placer=placer, log=lambda *a: None, mode="gtc")
    assert st["VIVK-2026-10-05"]["live"]["status"] == "ordered"  # still open: not "unfilled" like a DAY order
    assert len(calls) == 1                                       # and not re-placed
    cancelled = []
    live.c = SimpleNamespace(cancel_order=lambda oid, h: cancelled.append(oid) or SimpleNamespace(status_code=200))
    live.hash = "h"
    st = ro.manage(tmp_path, [ALERT], dt.date(2026, 10, 5), adapters={"live": live}, prices={"VIVK": 0.35},
                   placer=placer, log=lambda *a: None, mode="gtc")
    s = st["VIVK-2026-10-05"]["live"]
    assert s["status"] == "unfilled" and s["cancelled"] and cancelled == [11]
    # ask already under the last close: the DAY-style ask limit is used (fills now, below the close)
    assert ro.gtc_limit(0.3181, 0.20) == ro.buy_limit(0.20) and ro.gtc_limit(12.0, 11.0) == 11.11


def test_expired_day_order_is_unfilled_not_cash(tmp_path):
    class Expired(Fake):
        def order_status(self, coid, info):
            return ("expired", 0.0, 0.0, "")
    live = Expired()
    run(tmp_path, "2026-10-02", {"live": live})
    st, _ = run(tmp_path, "2026-10-05", {"live": live})
    assert st["VIVK-2026-10-05"]["live"]["status"] == "unfilled"
    st, _ = run(tmp_path, "2026-12-01", {"live": live})
    assert st["VIVK-2026-10-05"]["live"]["status"] == "unfilled" and not ro.killed(st, "live")
