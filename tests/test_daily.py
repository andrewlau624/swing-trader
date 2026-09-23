"""Daily-book tests. Nothing here touches the network."""
import datetime as dt
import json
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest

from swingtrader.config import Config
from swingtrader.daily import signals as sg
from swingtrader.daily.book import DailyBook, owned_by_daily
from swingtrader.daily.executor import DailyExecutor, phase_for

ET = ZoneInfo("America/New_York")


# ------------------------------------------------------------------ signals
def test_ibs_targets_threshold_and_flat_bar():
    bars = {"QQQ": {"high": 10, "low": 9, "close": 9.1},     # 0.10 -> hold
            "SMH": {"high": 10, "low": 9, "close": 9.5},     # 0.50 -> no
            "XLK": {"high": 10, "low": 10, "close": 10}}     # no range -> no
    assert sg.ibs_targets(bars, 0.2) == ["QQQ"]


def test_loser_picks_rules_and_order():
    rows = pd.DataFrame({
        "price":      [9.0, 9.0, 8.0, 9.5, 4.0],
        "prev_close": [10., 10., 10., 10., 5.0],
        "high":       [10., 10., 10., 10., 5.0],
        "low":        [8.95, 8.0, 7.9, 9.4, 3.9],
    }, index=["AT_LOW", "OFF_LOW", "DEEPER", "SMALL_DROP", "CHEAP"])
    p = sg.loser_picks(rows, day_ret_max=-0.08, ibs_max=0.10, price_min=5, price_max=2000)
    # OFF_LOW: -10% but ibs 0.5; SMALL_DROP: -5%; CHEAP: under $5
    assert list(p.index) == ["DEEPER", "AT_LOW"], "most-beaten first"


def test_loser_picks_price_below_stale_low_extends_range():
    # delayed-SIP low can lag the live price; a new low must count as the low
    rows = pd.DataFrame({"price": [9.0], "prev_close": [10.], "high": [10.], "low": [9.2]},
                        index=["X"])
    p = sg.loser_picks(rows, day_ret_max=-0.08, ibs_max=0.10, price_min=5, price_max=2000)
    assert list(p.index) == ["X"] and p.ibs.iloc[0] == 0.0


def test_noise_decide_matches_research_rules():
    # enter above band, hold, exit when back under max(ub, vwap), flip short
    assert sg.noise_decide(0, 101, ub=100, lb=98, vwap=99) == 1
    assert sg.noise_decide(1, 100.5, ub=100, lb=98, vwap=99) == 1
    assert sg.noise_decide(1, 99.5, ub=99.8, lb=98, vwap=100) == 0   # back inside the band: out
    # exit then re-test on the same bar, exactly as research/noise.py does
    assert sg.noise_decide(1, 100.5, ub=100, lb=98, vwap=101) == 1
    assert sg.noise_decide(1, 97, ub=100, lb=98, vwap=99) == -1      # exit then short same bar
    assert sg.noise_decide(0, 99, ub=100, lb=98, vwap=99) == 0


def test_noise_decide_reproduces_research_loop():
    """Drive the research loop (research/daily-strategies/noise.py) and the
    live function over the same synthetic day; positions must agree."""
    rng = np.random.default_rng(1)
    c = 100 * np.cumprod(1 + rng.normal(0, 0.001, 390))
    ub = np.full(390, 100.2); lb = np.full(390, 99.8)
    v = rng.integers(1, 100, 390).astype(float)
    pv = np.cumsum(c * v) / np.cumsum(v)
    pos_research, pos_live = 0, 0
    for m in range(30, 390, 30):
        p = c[m]
        if pos_research == 1 and p < max(ub[m], pv[m]): pos_research = 0
        elif pos_research == -1 and p > min(lb[m], pv[m]): pos_research = 0
        if pos_research == 0:
            if p > ub[m]: pos_research = 1
            elif p < lb[m]: pos_research = -1
        pos_live = sg.noise_decide(pos_live, p, ub[m], lb[m], pv[m])
        assert pos_live == pos_research


def test_noise_leverage_caps():
    closes = pd.Series(100 * np.cumprod(1 + np.full(20, 0.0001) * np.tile([1, -1], 10)))
    assert sg.noise_leverage(closes, 0.02, 3.5) == 3.5          # tiny vol -> capped
    wild = pd.Series(100 * np.cumprod(1 + np.tile([0.05, -0.05], 10)))
    assert sg.noise_leverage(wild, 0.02, 3.5) < 1


# --------------------------------------------------------------------- book
def test_book_long_and_short_round_trips():
    b = DailyBook(cash=3000, start_equity=3000)
    b.register("a", sym="X", side="buy", leg="night", ref_px=10)
    b.apply_fill("a", 10, 10.0, "filled", "2026-09-23T20:00")
    assert b.equity({"X": 10.0}) == pytest.approx(3000)
    b.register("b", sym="X", side="sell", leg="night", ref_px=10)
    b.apply_fill("b", 10, 11.0, "filled", "2026-09-24T13:30")
    assert b.cash == pytest.approx(3010) and not b.positions
    b.register("c", sym="Q", side="sell", leg="noise", ref_px=100)
    b.apply_fill("c", 5, 100.0, "filled", "2026-09-24T14:01")
    assert b.positions["Q"]["qty"] == -5
    b.register("d", sym="Q", side="buy", leg="noise", ref_px=100)
    b.apply_fill("d", 5, 98.0, "filled", "2026-09-24T19:59")
    assert b.cash == pytest.approx(3020) and b.closed[-1]["pnl"] == pytest.approx(10)


def test_partial_fills_book_only_the_increment():
    b = DailyBook(cash=1000, start_equity=1000)
    b.register("a", sym="X", side="buy", leg="night", ref_px=10)
    assert b.apply_fill("a", 3, 10.0, "partially_filled", "t") == 3
    assert b.apply_fill("a", 3, 10.0, "partially_filled", "t") is None
    assert b.apply_fill("a", 5, 10.0, "filled", "t") == 2
    assert b.positions["X"]["qty"] == 5 and b.cash == pytest.approx(950)


def test_swing_sees_daily_symbols_as_owned(tmp_path):
    b = DailyBook(cash=3000, start_equity=3000)
    b.positions["AAA"] = {"qty": 5, "avg_px": 10, "leg": "night", "entry_date": "d"}
    b.register("x", sym="BBB", side="buy", leg="night", ref_px=10)     # still open
    b.register("y", sym="CCC", side="buy", leg="night", ref_px=10)
    b.orders["y"]["status"] = "expired"
    b.save(tmp_path)
    assert owned_by_daily(tmp_path) == {"AAA", "BBB"}


def test_phase_clock():
    at = lambda h, m: dt.datetime(2026, 9, 23, h, m, tzinfo=ET)
    assert phase_for(at(9, 15)) == "open"
    assert phase_for(at(9, 50)) == "reconcile"
    assert phase_for(at(10, 1)) == "intraday"
    assert phase_for(at(15, 31)) == "intraday"
    assert phase_for(at(15, 40)) == "close"
    assert phase_for(at(15, 52)) == "reconcile", "past the MOC cutoff: never submit"


# --------------------------------------------- executor against a fake broker
class FakeClient:
    def __init__(self):
        self.submitted = []

    def submit_order(self, req):
        self.submitted.append(req)
        return SimpleNamespace(id=f"id{len(self.submitted)}")

    def get_order_by_client_id(self, coid):
        raise AssertionError("no open orders expected in this test")


class FakeBroker:
    key, secret = "PKTEST", "SEC"

    def __init__(self, held=None):
        self.client = FakeClient()
        self._held = held or {}

    def clock(self):
        now = pd.Timestamp("2026-09-23 15:40", tz=ET)
        return SimpleNamespace(is_open=True, next_open=now + pd.Timedelta(hours=18),
                               next_close=pd.Timestamp("2026-09-23 16:00", tz=ET))

    def positions(self):
        return self._held

    def account(self):
        return SimpleNamespace(equity="97826.56")


def _executor(tmp_path, monkeypatch, held=None):
    ex = DailyExecutor(Config.load(), broker=FakeBroker(held), state_dir=tmp_path,
                       log_dir=tmp_path)
    ex.notifier.send = lambda *a, **k: "notify skipped (test)"
    return ex


def test_close_phase_places_whole_share_moc_buys(tmp_path, monkeypatch):
    from swingtrader.daily import executor as E
    elig = pd.DataFrame({"prev_close": [10.0, 50.0, 20.0, 10.0]},
                        index=["LOSER", "PRICEY", "SWINGY", "FINE"])
    live = pd.DataFrame({"price": [9.0, 45.0, 18.0, 9.9], "high": [10, 50, 20, 10],
                         "low": [8.99, 44.9, 17.9, 9.8]},
                        index=["LOSER", "PRICEY", "SWINGY", "FINE"])
    monkeypatch.setattr(E.md, "eligibility", lambda *a, **k: elig)
    monkeypatch.setattr(E.md, "live_rows", lambda syms: live.loc[[s for s in syms if s in live.index]])
    monkeypatch.setattr(E, "all_assets", lambda: SimpleNamespace(symbols=list(elig.index)))
    (tmp_path / "book-reversion.json").write_text(json.dumps(
        {"positions": {"SWINGY": {}}, "pending": {}}))
    ex = _executor(tmp_path, monkeypatch)
    book = DailyBook(cash=3000, start_equity=3000)
    ex.phase_close(book, "2026-09-23", dt.datetime(2026, 9, 23, 15, 40, tzinfo=ET), ex.broker.clock())
    reqs = {r.symbol: r for r in ex.broker.client.submitted}
    assert "SWINGY" not in reqs, "never trade a symbol the swing book holds"
    assert "FINE" not in reqs, "-1% is not a signal"
    # $3000 * 0.5 leg * 10% cap = $150 per name
    assert reqs["LOSER"].qty == 16 and reqs["LOSER"].time_in_force.value == "cls"
    assert reqs["PRICEY"].qty == 3
    assert all(r.side.value == "buy" for r in reqs.values())
    assert set(book.open_orders()) == {r.client_order_id for r in reqs.values()}


def test_open_phase_sells_night_leg_at_the_auction(tmp_path, monkeypatch):
    from swingtrader.daily import executor as E
    monkeypatch.setattr(E.md, "sip_daily", lambda syms, *a, **k: {
        s: pd.DataFrame({"open": [1.0], "high": [10.0], "low": [9.0], "close": [9.5], "volume": [1]},
                        index=[pd.Timestamp("2026-09-22")]) for s in syms})
    monkeypatch.setattr(E.md, "eligibility", lambda *a, **k: pd.DataFrame())
    monkeypatch.setattr(E, "all_assets", lambda: SimpleNamespace(symbols=[]))
    held = {"LOSER": SimpleNamespace(current_price="9.5", qty="16")}
    ex = _executor(tmp_path, monkeypatch, held=held)
    book = DailyBook(cash=3000 - 16 * 9, start_equity=3000)
    book.positions["LOSER"] = {"qty": 16, "avg_px": 9.0, "leg": "night", "entry_date": "2026-09-22"}
    ex.phase_open(book, "2026-09-23")
    reqs = ex.broker.client.submitted
    assert len(reqs) == 1, "IBS 0.5 on every ETF -> no IBS buys; only the night exit"
    r = reqs[0]
    assert r.symbol == "LOSER" and r.side.value == "sell" and r.qty == 16
    assert r.time_in_force.value == "opg"


def test_dry_run_submits_nothing(tmp_path, monkeypatch):
    from swingtrader.daily import executor as E
    ex = _executor(tmp_path, monkeypatch); ex.dry_run = True
    book = DailyBook(cash=3000, start_equity=3000)
    ex._order(book, "2026-09-23", "X", "buy", "night", tif="cls", ref_px=9, kind="entry", qty=5)
    assert ex.broker.client.submitted == [] and not book.orders
