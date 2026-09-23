"""Schwab adapter tests against a fake Schwab client. No network."""
import datetime as dt
import json
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from swingtrader.config import Config
from swingtrader.daily.book import DailyBook
from swingtrader.daily.brokers import SchwabAdapter, schwab_token_age_s

ET = ZoneInfo("America/New_York")


@pytest.fixture(autouse=True)
def _isolate_from_real_env(monkeypatch):
    # get_env() back-fills os.environ from the real .env with setdefault, so an
    # empty value here keeps a developer's real account number out of the tests
    monkeypatch.setenv("SCHWAB_ACCOUNT_NUMBER", "")


class Resp:
    def __init__(self, data=None, status=200, headers=None):
        self._d, self.status_code, self.headers, self.text = data, status, headers or {}, ""

    def json(self):
        return self._d

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


class FakeSchwab:
    def __init__(self, positions=(), acct_type="MARGIN", equity=3000.0, bp=12000.0, orders=()):
        self.placed, self._pos, self._orders = [], list(positions), list(orders)
        self.acct_type, self.equity, self.bp = acct_type, equity, bp
        self.order_detail = {}

    def get_account_numbers(self):
        return Resp([{"accountNumber": "12345678", "hashValue": "HASH"}])

    def get_account(self, h, fields=None):
        return Resp({"securitiesAccount": {
            "type": self.acct_type, "accountNumber": "12345678",
            "currentBalances": {"liquidationValue": self.equity, "cashBalance": 1000.0,
                                "buyingPower": self.bp},
            "positions": [{"instrument": {"symbol": s, "assetType": "EQUITY"},
                           "longQuantity": max(q, 0), "shortQuantity": max(-q, 0),
                           "marketValue": q * px} for s, q, px in self._pos]}})

    def get_orders_for_account(self, h, from_entered_datetime=None, to_entered_datetime=None):
        return Resp(self._orders)

    def place_order(self, h, order):
        self.placed.append(order)
        return Resp(None, 201, {"Location": f"https://api.schwabapi.com/trader/v1/accounts/HASH/orders/{1000 + len(self.placed)}"})

    def get_order(self, oid, h):
        return Resp(self.order_detail[oid])


def adapter(**kw):
    return SchwabAdapter(client=FakeSchwab(**kw), clock_source=lambda: SimpleNamespace(
        is_open=True, next_open=pd.Timestamp("2026-09-25 09:30", tz=ET),
        next_close=pd.Timestamp("2026-09-24 16:00", tz=ET)))


def leg(o):
    return o["orderLegCollection"][0]


def test_moc_buy_payload():
    a = adapter()
    oid = a.submit("LOSER", "buy", "cls", "dlv.LOSER.x", qty=16)
    o = a.c.placed[0]
    assert o["orderType"] == "MARKET_ON_CLOSE" and o["duration"] == "DAY" and o["session"] == "NORMAL"
    assert leg(o)["instruction"] == "BUY" and leg(o)["quantity"] == 16
    assert leg(o)["instrument"]["symbol"] == "LOSER" and oid == "1001"


def test_open_exit_is_a_premarket_market_day_order():
    # Schwab has no market-on-open type
    a = adapter(positions=[("LOSER", 16, 9.5)])
    a.submit("LOSER", "sell", "opg", "c", qty=16)
    o = a.c.placed[0]
    assert o["orderType"] == "MARKET" and o["duration"] == "DAY" and leg(o)["instruction"] == "SELL"


def test_notional_becomes_whole_shares():
    a = adapter()
    a.submit("QQQ", "buy", "day", "c", notional=1500.0, ref_px=746.63)
    assert leg(a.c.placed[0])["quantity"] == 2          # no fractional shares via the API
    with pytest.raises(ValueError, match="0 whole shares"):
        a.submit("QQQ", "buy", "day", "c2", notional=500.0, ref_px=746.63)


def test_short_side_instructions():
    a = adapter(positions=[("QQQ", 5, 700.0)])
    a.submit("QQQ", "sell", "day", "c", qty=8)          # 5 long -> SELL 5 + SELL_SHORT 3
    assert [(leg(o)["instruction"], leg(o)["quantity"]) for o in a.c.placed] == [("SELL", 5), ("SELL_SHORT", 3)]
    b = adapter(positions=[("QQQ", -6, 700.0)])
    b.submit("QQQ", "buy", "cls", "c", qty=6)           # covering a short
    assert leg(b.c.placed[0])["instruction"] == "BUY_TO_COVER"
    assert b.c.placed[0]["orderType"] == "MARKET_ON_CLOSE"


def test_duplicate_guard_replaces_client_order_ids():
    existing = [{"orderId": 777, "status": "QUEUED", "orderLegCollection": [
        {"instruction": "BUY", "quantity": 16, "instrument": {"symbol": "LOSER"}}]}]
    a = adapter(orders=existing)
    assert a.submit("LOSER", "buy", "cls", "c", qty=16) == "777"
    assert a.c.placed == [], "same symbol/instruction/qty already placed today: do not send again"
    cancelled = [{**existing[0], "status": "CANCELED"}]
    b = adapter(orders=cancelled)
    b.submit("LOSER", "buy", "cls", "c", qty=16)
    assert len(b.c.placed) == 1, "a cancelled order is not a duplicate"


def test_order_status_aggregates_execution_legs():
    a = adapter()
    a.c.order_detail[1001] = {"status": "FILLED", "orderActivityCollection": [
        {"executionLegs": [{"quantity": 10, "price": 9.0, "time": "2026-09-24T20:00:01+0000"},
                           {"quantity": 6, "price": 9.2, "time": "2026-09-24T20:00:02+0000"}]}]}
    st, q, px, when = a.order_status("c", {"broker_id": "1001"})
    assert st == "filled" and q == 16 and px == pytest.approx((90 + 55.2) / 16)
    a.c.order_detail[1002] = {"status": "WORKING", "orderActivityCollection": []}
    assert a.order_status("c", {"broker_id": "1002"})[0] == "new"


def test_account_type_drives_the_multiplier():
    assert adapter(acct_type="MARGIN", equity=3000, bp=12000).account().multiplier == 4
    assert adapter(acct_type="MARGIN", equity=3000, bp=6000).account().multiplier == 2
    assert adapter(acct_type="CASH").account().multiplier == 1


def test_live_close_phase_routes_through_schwab(tmp_path, monkeypatch):
    from swingtrader.daily import executor as E
    monkeypatch.setattr(E.md, "eligibility", lambda *a, **k: pd.DataFrame(
        {"prev_close": [10.0], "vol20": [0.9]}, index=["LOSER"]))
    monkeypatch.setattr(E.md, "live_rows", lambda syms: pd.DataFrame(
        {"price": [9.0], "high": [10.0], "low": [8.99]}, index=["LOSER"]))
    monkeypatch.setattr(E, "all_assets", lambda: SimpleNamespace(symbols=["LOSER"]))
    a = adapter()
    ex = E.DailyExecutor(Config.load(), account="live", broker=a, state_dir=tmp_path, log_dir=tmp_path)
    ex.notifier.send = lambda *x, **k: "skipped"
    book = DailyBook(cash=3000, start_equity=3000)
    ex.phase_close(book, "2026-09-24", dt.datetime(2026, 9, 24, 15, 40, tzinfo=ET), a.clock())
    o = a.c.placed[0]
    assert o["orderType"] == "MARKET_ON_CLOSE" and leg(o)["quantity"] == 16   # $3000*0.5*10% / $9
    (coid, info), = book.orders.items()
    assert coid.startswith("dlv.") and info["broker_id"] == "1001"
    saved = json.loads((tmp_path / "book-daily-live.json").read_text())
    assert coid in saved["orders"], "saved right after placing: the book is the idempotency record"


def test_token_age(tmp_path):
    p = tmp_path / "t.json"
    assert schwab_token_age_s(p) is None
    p.write_text(json.dumps({"creation_timestamp": dt.datetime.now().timestamp() - 3 * 86400, "token": {}}))
    assert 2.9 * 86400 < schwab_token_age_s(p) < 3.1 * 86400


def test_account_number_accepts_last_four(monkeypatch):
    monkeypatch.setenv("SCHWAB_ACCOUNT_NUMBER", "5678")
    assert adapter().hash == "HASH"
    monkeypatch.setenv("SCHWAB_ACCOUNT_NUMBER", "12345678")
    assert adapter().hash == "HASH"
    for messy in ("...5678", " 5678 ", '"5678"', "5678\r"):
        monkeypatch.setenv("SCHWAB_ACCOUNT_NUMBER", messy)
        assert adapter().hash == "HASH", repr(messy)
    monkeypatch.setenv("SCHWAB_ACCOUNT_NUMBER", "9999")
    with pytest.raises(RuntimeError, match="matches 0"):
        adapter()


def test_live_sizes_from_free_equity_not_your_holdings(tmp_path, monkeypatch):
    from swingtrader.daily import executor as E
    # $3,514 account: $3,512 in YOUR five positions, $2.48 cash
    a = adapter(positions=[("AAA", 10, 100.0), ("BBB", 20, 50.0), ("CCC", 5, 200.0),
                           ("DDD", 4, 128.0), ("EEE", 1, 0.0)], equity=3514.60)
    ex = E.DailyExecutor(Config.load(), account="live", broker=a, state_dir=tmp_path, log_dir=tmp_path)
    ex.notifier.send = lambda *x, **k: "skipped"
    book = DailyBook(cash=0, start_equity=0)
    assert ex.free_equity() == pytest.approx(3514.60 - 3512.0)
    ex._order(book, "2026-09-24", "LOSER", "buy", "night", tif="cls", ref_px=9, kind="entry", qty=16)
    assert a.c.placed == [], "no free cash: never borrow against the user's holdings"
    assert any("free for the bot" in w for w in ex.warnings)
    # after selling AAA and BBB ($2,000): the bot has ~$2,002 to work with
    b = adapter(positions=[("CCC", 5, 200.0), ("DDD", 4, 128.0)], equity=3514.60)
    ex2 = E.DailyExecutor(Config.load(), account="live", broker=b, state_dir=tmp_path, log_dir=tmp_path)
    assert ex2._sizing_equity(book) == pytest.approx(3514.60 - 1512.0)
    ex2.d.live_capital = 1500
    assert ex2._sizing_equity(book) == 1500
