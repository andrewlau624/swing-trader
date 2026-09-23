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
    monkeypatch.setenv("DAILY_LIVE_CAPITAL", "")


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
    monkeypatch.setattr(E.md, "live_rows", lambda syms, *a, **k: pd.DataFrame(
        {"price": [9.0], "high": [10.0], "low": [8.99]}, index=["LOSER"]))
    monkeypatch.setattr(E, "all_assets", lambda: SimpleNamespace(symbols=["LOSER"]))
    a = adapter()
    ex = E.DailyExecutor(Config.load(), account="live", broker=a, state_dir=tmp_path, log_dir=tmp_path)
    ex.notifier.send = lambda *x, **k: "skipped"
    ex.d.quote_source = "alpaca"
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
    monkeypatch.setenv("DAILY_LIVE_CAPITAL", "1000")
    assert ex2._sizing_equity(book) == 1000, ".env cap wins (survives make pull)"



class QuoteClient:
    def __init__(self, payload):
        self.payload, self.calls = payload, 0

    def get_quotes(self, syms):
        self.calls += 1
        return Resp({k: v for k, v in self.payload.items() if k in syms})


def test_schwab_quote_rows_parse_and_freshness():
    from swingtrader.daily import marketdata as md
    now = pd.Timestamp.now(tz="UTC").value / 1e6
    c = QuoteClient({
        "LOSER": {"quote": {"lastPrice": 9.01, "highPrice": 10.0, "lowPrice": 8.9, "tradeTime": now},
                  "regular": {"regularMarketLastPrice": 9.0, "regularMarketTradeTime": now}},
        "STALE": {"quote": {"lastPrice": 5, "highPrice": 6, "lowPrice": 4, "tradeTime": now - 3.6e6}},
        "NOHILO": {"quote": {"lastPrice": 5, "tradeTime": now}}})
    r = md.schwab_rows(["LOSER", "STALE", "NOHILO"], client=c)
    assert list(r.index) == ["LOSER"], "stale (1h old) and incomplete quotes are dropped"
    assert r.loc["LOSER", "price"] == 9.0, "regular-session last, not an extended-hours print"
    assert (r.loc["LOSER", "high"], r.loc["LOSER", "low"]) == (10.0, 8.9)
    md.schwab_rows([f"S{i}" for i in range(450)], client=c)
    assert c.calls == 1 + 3, "batched 200 per request"


def test_decision_rows_falls_back_to_alpaca(monkeypatch):
    from swingtrader.daily import marketdata as md
    def boom(*a, **k): raise RuntimeError("token expired")
    monkeypatch.setattr(md, "schwab_rows", boom)
    monkeypatch.setattr(md, "live_rows", lambda syms, *a, **k: pd.DataFrame({"price": [1.0]}, index=["X"]))
    rows, src = md.decision_rows(["X"], "auto", log=lambda *a: None)
    assert src == "alpaca" and list(rows.index) == ["X"]


# ---------------------------------------------------------- login reminders
class FakeNotifier:
    def __init__(self):
        self._seen, self.sent = set(), []

    def send(self, subject, html, dedupe_key=None):
        if dedupe_key in self._seen:
            return "email skipped (already sent)"
        self.sent.append(subject); self._seen.add(dedupe_key); return "email sent"

    def _remember(self, k):
        self._seen.add(k)


def test_reminder_stages_fire_once_each(tmp_path):
    from swingtrader.daily.schwab_reminder import check
    created = dt.datetime(2026, 9, 23, 14, 0, tzinfo=ET)          # expires Wed Sep 30 14:00 ET
    p = tmp_path / "tok.json"
    p.write_text(json.dumps({"creation_timestamp": created.timestamp(), "token": {}}))
    n = FakeNotifier()
    at = lambda d, h: dt.datetime(2026, 9, d, h, 0, tzinfo=ET)
    ok = lambda: None
    assert "days left" in check(n, at(26, 12), p, probe_fn=ok) and n.sent == []       # 4 days out: quiet
    check(n, at(28, 15), p, probe_fn=ok); check(n, at(28, 17), p, probe_fn=ok)                     # 47h left, twice
    check(n, at(29, 15), p, probe_fn=ok)                                              # 23h left
    check(n, at(30, 9), p, probe_fn=ok)                                               # 5h left: day of
    check(n, at(30, 15), p); check(n, at(30, 17), p)                     # expired, twice
    assert [s.split("login ")[1].split(" -")[0] for s in n.sent] == [
        "expires in 2 days", "expires TOMORROW", "expires in a few HOURS", "has EXPIRED"]


def test_reminder_after_downtime_sends_only_the_most_urgent(tmp_path):
    from swingtrader.daily.schwab_reminder import check
    created = dt.datetime(2026, 9, 23, 14, 0, tzinfo=ET)
    p = tmp_path / "tok.json"
    p.write_text(json.dumps({"creation_timestamp": created.timestamp(), "token": {}}))
    n = FakeNotifier()
    check(n, dt.datetime(2026, 9, 30, 10, 0, tzinfo=ET), p, probe_fn=lambda: None)              # box was off until 4h left
    assert len(n.sent) == 1 and "HOURS" in n.sent[0]
    check(n, dt.datetime(2026, 9, 30, 11, 0, tzinfo=ET), p, probe_fn=lambda: None)
    assert len(n.sent) == 1, "skipped stages must not arrive late"


def test_new_login_restarts_the_sequence(tmp_path):
    from swingtrader.daily.schwab_reminder import check
    p = tmp_path / "tok.json"; n = FakeNotifier()
    for day in (23, 30):
        created = dt.datetime(2026, 9, day, 14, 0, tzinfo=ET)
        p.write_text(json.dumps({"creation_timestamp": created.timestamp(), "token": {}}))
        check(n, created + dt.timedelta(days=6, hours=1), p, probe_fn=lambda: None)
    assert len(n.sent) == 2, "each login gets its own reminders"



def test_revoked_login_is_caught_before_it_expires(tmp_path):
    from swingtrader.daily.schwab_reminder import check
    created = dt.datetime(2026, 9, 23, 14, 0, tzinfo=ET)
    p = tmp_path / "tok.json"
    p.write_text(json.dumps({"creation_timestamp": created.timestamp(), "token": {}}))
    n = FakeNotifier()
    revoked = lambda: "invalid_grant: Refresh token is invalid, expired or revoked"
    out = check(n, dt.datetime(2026, 9, 24, 9, 0, tzinfo=ET), p, probe_fn=revoked)
    assert "REVOKED" in out and len(n.sent) == 1 and "REVOKED" in n.sent[0]
    check(n, dt.datetime(2026, 9, 24, 11, 0, tzinfo=ET), p, probe_fn=revoked)
    assert len(n.sent) == 1, "one revocation email per login"



def test_live_book_created_before_selling_still_trades_after(tmp_path, monkeypatch):
    """Book first runs while the account is all your holdings ($2.48 free);
    you then sell $2,000 of them. The bot must see the $2,000."""
    from swingtrader.daily import executor as E
    monkeypatch.setattr(E.md, "eligibility", lambda *a, **k: pd.DataFrame(
        {"prev_close": [10.0], "vol20": [0.9]}, index=["LOSER"]))
    monkeypatch.setattr(E.md, "live_rows", lambda syms, *a, **k: pd.DataFrame(
        {"price": [9.0], "high": [10.0], "low": [8.99]}, index=["LOSER"]))
    monkeypatch.setattr(E, "all_assets", lambda: SimpleNamespace(symbols=["LOSER"]))
    before = adapter(positions=[("AAA", 35, 100.0)], equity=3502.48)
    ex = E.DailyExecutor(Config.load(), account="live", broker=before, state_dir=tmp_path, log_dir=tmp_path)
    ex.d.quote_source = "alpaca"
    book = DailyBook(cash=2.48, start_equity=2.48)         # created at the 09:50 run, before selling
    after = adapter(positions=[("AAA", 15, 100.0)], equity=3502.48)   # sold 20 AAA = $2,000
    ex.broker = after
    ex._sync_live_cash(book)
    assert book.cash == pytest.approx(2002.48) and book.start_equity == pytest.approx(2002.48)
    ex.phase_close(book, "2026-09-24", dt.datetime(2026, 9, 24, 15, 40, tzinfo=ET), after.clock())
    assert after.c.placed, "must buy with the freed cash, not report 'cash exhausted'"
    assert leg(after.c.placed[0])["quantity"] == int(2002.48 * 0.5 * 0.10 // 9.0)



def test_fresh_fills_are_not_counted_as_your_holdings(tmp_path, monkeypatch):
    """16:10 run: Schwab already shows the 19 new night positions; the book has
    them as pending orders. They must count as the bot's, not as yours."""
    from swingtrader.daily import executor as E
    a = adapter(positions=[("AAPL", 3, 340.0), ("JAGX", 2, 8.91)], equity=1020 + 1227.14)
    ex = E.DailyExecutor(Config.load(), account="live", broker=a, state_dir=tmp_path, log_dir=tmp_path)
    book = DailyBook(cash=1000, start_equity=1000)
    book.register("dlv.JAGX.x", sym="JAGX", side="buy", leg="night", ref_px=9.0, tif="cls")
    assert ex.free_equity(book) == pytest.approx(1227.14), "JAGX is the bot's (pending order), AAPL is yours"
