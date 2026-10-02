"""Odd-lot tender buy: only after the user confirms; plan rules; fill tracking. Fake brokers, no network."""
import datetime as dt
import json
from types import SimpleNamespace

from swingtrader.daily import tender_buy as b

R = dict(alert=True, ticker="ABC", name="ABC CORP", date="2026-10-01", path="edgar/data/1/x.txt", floor=34.0,
         last_close=32.3, expires="2026-10-30", kind="fixed", lo=None, hi=None, fixed=34.0, odd_lot="Y",
         floor_gain=0.0526)
TODAY = dt.date(2026, 10, 2)


class FakeAd:
    def __init__(self, cash, held=0):
        self.cash, self.held, self.placed = cash, held, []
        self.hash = "h"
        self.c = SimpleNamespace(place_order=self._place)

    def _place(self, h, order):
        self.placed.append(order)
        return SimpleNamespace(status_code=201, headers={"Location": "/orders/777"}, text="")

    def positions(self):
        return {"ABC": SimpleNamespace(qty=self.held, current_price=33.0)} if self.held else {}

    def account(self):
        return SimpleNamespace(cash=self.cash)


def _state(tmp_path, rows=(R,)):
    (tmp_path / "tender-watch.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))


def test_plan_rules():
    p, _ = b.plan(R, {"roth": 0, "live": 0}, {"roth": 5000, "live": 0}, 32.5, TODAY)
    assert p["account"] == "roth" and p["qty"] == 99 and p["limit"] == 33.66
    p, _ = b.plan(R, {"roth": 0, "live": 40}, {"roth": 5000}, 32.5, TODAY)
    assert p["qty"] == 59                                   # 99 in TOTAL across accounts
    p, _ = b.plan(R, {"roth": 0}, {"roth": 500, "live": 9000}, 32.5, TODAY)
    assert p["account"] == "roth" and p["qty"] == 14         # Roth first, with the cash it has
    assert b.plan(R, {}, {"roth": 5000}, 33.9, TODAY)[0] is None          # no longer >= 1% under the floor
    assert b.plan(R, {}, {"roth": 5000}, 32.5, dt.date(2026, 10, 28))[0] is None   # too close to expiry
    assert b.plan({**R, "expires": None}, {}, {"roth": 5000}, 32.5, TODAY)[0] is None
    assert b.plan(R, {"live": 120}, {"roth": 5000}, 32.5, TODAY)[0] is None


def test_nothing_is_placed_without_typing_the_ticker(tmp_path):
    _state(tmp_path)
    ads = {"roth": FakeAd(5000), "live": FakeAd(0)}
    rc = b.main("ABC-2026-10-01", tmp_path, confirm=lambda _: "y", adapters=ads, quote=32.5, today=TODAY, out=lambda *_: None)
    assert rc == 1 and not ads["roth"].placed and not (tmp_path / b.ORDERS_NAME).exists()


def test_confirmed_buy_places_one_limit_order_and_tracks_it(tmp_path):
    _state(tmp_path)
    ads = {"roth": FakeAd(5000), "live": FakeAd(0)}
    rc = b.main("ABC-2026-10-01", tmp_path, confirm=lambda _: "abc", adapters=ads, quote=32.5, today=TODAY, out=lambda *_: None)
    assert rc == 0 and len(ads["roth"].placed) == 1 and not ads["live"].placed
    o = ads["roth"].placed[0]
    assert o["orderType"] == "LIMIT" and o["price"] == "33.66" and o["duration"] == "DAY"
    assert o["orderLegCollection"][0]["quantity"] == 99 and o["orderLegCollection"][0]["instruction"] == "BUY"
    sent = []
    # next morning: filled -> bought + email; later: gone -> tendered. track() never places orders.
    ads["roth"].held = 99
    st = b.track(tmp_path, TODAY + dt.timedelta(days=1), adapters=ads, notify=lambda s, body: sent.append(s))
    assert st[R["path"]]["status"] == "bought" and "TENDER NOW" in sent[0]
    ads["roth"].held = 0
    st = b.track(tmp_path, TODAY + dt.timedelta(days=5), adapters=ads)
    assert st[R["path"]]["status"] == "tendered" and len(ads["roth"].placed) == 1


def test_unknown_id(tmp_path):
    _state(tmp_path)
    assert b.main("ZZZ-2026-10-01", tmp_path, confirm=lambda _: "ZZZ", adapters={}, quote=1, out=lambda *_: None) == 2
