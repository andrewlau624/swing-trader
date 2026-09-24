"""Daily-book tests. Nothing here touches the network."""
import dataclasses
import datetime as dt
import math
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
    assert phase_for(at(15, 57)) == "flatten"
    assert phase_for(at(16, 10)) == "reconcile"


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
    ex.d.quote_source = "alpaca"      # never let a test reach a real Schwab login
    return ex


def test_close_phase_places_whole_share_moc_buys(tmp_path, monkeypatch):
    from swingtrader.daily import executor as E
    elig = pd.DataFrame({"prev_close": [10.0, 50.0, 20.0, 10.0]},
                        index=["LOSER", "PRICEY", "SWINGY", "FINE"])
    live = pd.DataFrame({"price": [9.0, 45.0, 18.0, 9.9], "high": [10, 50, 20, 10],
                         "low": [8.99, 44.9, 17.9, 9.8]},
                        index=["LOSER", "PRICEY", "SWINGY", "FINE"])
    monkeypatch.setattr(E.md, "eligibility", lambda *a, **k: elig)
    monkeypatch.setattr(E.md, "live_rows", lambda syms, *a, **k: live.loc[[s for s in syms if s in live.index]])
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
    reqs = {r.symbol: r for r in ex.broker.client.submitted}
    assert set(reqs) == {"LOSER", "SGOV"}, "no IBS signal -> night exit + park the IBS half in T-bills"
    r = reqs["LOSER"]
    assert r.side.value == "sell" and r.qty == 16 and r.time_in_force.value == "opg"
    t = reqs["SGOV"]
    assert t.side.value == "buy" and t.time_in_force.value == "day"
    assert t.notional == pytest.approx(0.5 * (3000 - 16 * 9 + 16 * 9.5), abs=0.01)


def test_dry_run_submits_nothing(tmp_path, monkeypatch):
    from swingtrader.daily import executor as E
    ex = _executor(tmp_path, monkeypatch); ex.dry_run = True
    book = DailyBook(cash=3000, start_equity=3000)
    ex._order(book, "2026-09-23", "X", "buy", "night", tif="cls", ref_px=9, kind="entry", qty=5)
    assert ex.broker.client.submitted == [] and not book.orders


# ---------------------------------------------------------- real-money mode
def test_broker_refuses_key_mixups(monkeypatch):
    from swingtrader.live.broker import PaperBroker
    with pytest.raises(RuntimeError, match="PAPER key"):
        PaperBroker(paper=False, key="PKABC", secret="s")
    with pytest.raises(RuntimeError, match="not a paper key"):
        PaperBroker(paper=True, key="AKABC", secret="s")


def test_live_and_paper_books_never_share_state():
    from swingtrader.daily.book import book_file
    assert book_file("paper") != book_file("live")


class LiveCashBroker(FakeBroker):
    key, secret = "AKTEST", "SEC"

    def account(self):
        return SimpleNamespace(equity="3000", multiplier="1", trading_blocked=False,
                               account_blocked=False)


def test_live_refuses_a_cash_account(tmp_path, monkeypatch):
    ex = DailyExecutor(Config.load(), account="live", broker=LiveCashBroker(),
                       state_dir=tmp_path, log_dir=tmp_path)
    ex.notifier.send = lambda *a, **k: "skipped"
    assert ex.run(phase="close") == 1
    assert any("margin" in w for w in ex.warnings)
    assert ex.broker.client.submitted == []


def test_live_ignores_the_paper_swing_book(tmp_path, monkeypatch):
    (tmp_path / "book-reversion.json").write_text(json.dumps(
        {"positions": {"SWINGY": {}}, "pending": {}}))
    live = DailyExecutor(Config.load(), account="live", broker=LiveCashBroker(),
                         state_dir=tmp_path, log_dir=tmp_path)
    paper = _executor(tmp_path, monkeypatch)
    book = DailyBook(cash=3000, start_equity=3000)
    assert "SWINGY" in paper._foreign_symbols(book)
    assert "SWINGY" not in live._foreign_symbols(book), "different account, no conflict"


def test_daytrade_mode_off_keeps_the_intraday_leg_shadow(tmp_path, monkeypatch):
    ex = _executor(tmp_path, monkeypatch)
    book = DailyBook(cash=3000, start_equity=3000)
    ex.broker.account = lambda: SimpleNamespace(equity="30000")
    ex._gate(book, 30_000)
    assert book.daytrade_live
    ex.d.daytrade_mode = "off"
    ex._gate(book, 30_000)
    assert not book.daytrade_live


def test_live_switch_edits_only_its_own_env_line(tmp_path, monkeypatch):
    import importlib, sys as _s
    _s.path.insert(0, "scripts")
    sw = importlib.import_module("daily_switch")
    env = tmp_path / ".env"
    env.write_text("ALPACA_API_KEY=PKX\nALPACA_SECRET_KEY=S\n")
    monkeypatch.setattr(sw, "ENV", env)
    sw.set_live(True)
    assert env.read_text() == "ALPACA_API_KEY=PKX\nALPACA_SECRET_KEY=S\nDAILY_LIVE=on\n"
    sw.set_live(False)
    assert env.read_text().count("DAILY_LIVE") == 1 and "DAILY_LIVE=off" in env.read_text()
    assert "ALPACA_API_KEY=PKX" in env.read_text()
    monkeypatch.setenv("DAILY_LIVE", "on")
    assert Config.load().daily.resolved_accounts() == ["paper", "live"]


# ------------------------------------------------ addendum 7: optimised legs
def test_momentum_top_uses_last_month_end_before_today():
    idx = pd.bdate_range("2025-01-01", "2026-03-20")
    up = pd.Series(np.linspace(100, 200, len(idx)), index=idx)
    flat = pd.Series(100.0, index=idx)
    down = pd.Series(np.linspace(100, 50, len(idx)), index=idx)
    c = pd.DataFrame({"UP": up, "FLAT": flat, "DOWN": down})
    assert sg.momentum_top(c, pd.Timestamp("2026-03-20"), k=1) == ["UP"]
    assert sg.momentum_top(c, pd.Timestamp("2026-03-20"), k=2) == ["FLAT", "UP"]
    # ranking must not see today's month: flip everything in March, still Feb's ranks
    c2 = c.copy(); c2.loc["2026-03-01":, "DOWN"] = 10_000
    assert sg.momentum_top(c2, pd.Timestamp("2026-03-20"), k=1) == ["UP"]


def test_night_sizing_vol_floor_and_crowding():
    picks = pd.DataFrame({"vol20": [0.3] + [0.9] * 9}, index=[f"S{i}" for i in range(10)])
    kept, per = sg.night_sizing(picks, vol_min=0.6, crowd_n=30, max_name_pct=0.10)
    assert "S0" not in kept.index and len(kept) == 9
    assert per == pytest.approx(0.10), "9 names -> capped at 10% each"
    crowd = pd.DataFrame({"vol20": [0.9] * 60}, index=[f"C{i}" for i in range(60)])
    kept, per = sg.night_sizing(crowd, vol_min=0.6, crowd_n=30, max_name_pct=0.10)
    # 60 raw signals: 1/60 each, scaled by 30/60 -> half the leg invested
    assert per == pytest.approx(1 / 60 * 0.5) and per * len(kept) == pytest.approx(0.5)


def test_tbills_sold_when_ibs_fires(tmp_path, monkeypatch):
    from swingtrader.daily import executor as E
    idx = pd.bdate_range("2025-06-01", "2026-09-22")
    def bars(syms, *a, **k):
        out = {}
        for i, s in enumerate(syms):
            c = pd.Series(np.linspace(100, 100 + 10 * (i + 1), len(idx)), index=idx)
            df = pd.DataFrame({"open": c, "high": c + 1, "low": c - 1, "close": c, "volume": 1})
            df.iloc[-1, df.columns.get_loc("close")] = df["low"].iloc[-1] + 0.1   # IBS 0.05
            out[s] = df
        return out
    monkeypatch.setattr(E.md, "sip_daily", bars)
    monkeypatch.setattr(E.md, "eligibility", lambda *a, **k: pd.DataFrame())
    monkeypatch.setattr(E, "all_assets", lambda: SimpleNamespace(symbols=[]))
    held = {"SGOV": SimpleNamespace(current_price="100.5", qty="15")}
    ex = _executor(tmp_path, monkeypatch, held=held)
    book = DailyBook(cash=1500, start_equity=3000)
    book.positions["SGOV"] = {"qty": 15, "avg_px": 100.0, "leg": "tbill", "entry_date": "2026-09-01"}
    ex.phase_open(book, "2026-09-23")
    reqs = ex.broker.client.submitted
    sells = [r for r in reqs if r.side.value == "sell"]
    buys = [r for r in reqs if r.side.value == "buy"]
    assert [r.symbol for r in sells] == ["SGOV"]
    assert len(buys) == 3 and "SGOV" not in {r.symbol for r in buys}, "top-3 momentum ETFs, all at IBS 0.05"


# ------------------------------------------- PDT rule retired (2026-06-04)
def test_gate_opens_at_3k_and_caps_leverage_by_broker(tmp_path, monkeypatch):
    ex = _executor(tmp_path, monkeypatch)
    book = DailyBook(cash=3000, start_equity=3000)
    for mult, cap in [("4", 3.5), ("2", 1.5), ("1", 0.5)]:
        ex.broker.account = lambda m=mult: SimpleNamespace(equity="3000", multiplier=m)
        ex._gate(book, 3000)
        assert book.daytrade_live, "$3k clears the $2k Reg T floor; no $25k PDT floor any more"
        assert book.noise_lev_cap == pytest.approx(cap)
    ex.broker.account = lambda: SimpleNamespace(equity="1500", multiplier="4")
    ex._gate(book, 1500)
    assert not book.daytrade_live, "below Reg T's $2,000 margin minimum"


def _live_noise_book(pos=1, lev=3.0, cap=3.5):
    b = DailyBook(cash=3000, start_equity=3000)
    b.daytrade_live, b.noise_lev_cap = True, cap
    b.noise = {"day": "2026-09-24", "pos": pos, "lev": lev, "last_m": 30, "entry": 500.0}
    return b


def test_live_noise_sizes_by_capped_leverage(tmp_path, monkeypatch):
    ex = _executor(tmp_path, monkeypatch)
    ex.d.noise_extra = {}                 # QQQ alone: the whole budget
    b = _live_noise_book(lev=3.0, cap=1.5)
    ex._sync_noise_live(b, "2026-09-24", 500.0)
    r = ex.broker.client.submitted[0]
    # 1.5x cap * $3000 / $500 = 9 shares, not the 18 the signal's 3.0x asks for
    assert r.symbol == "QQQ" and r.qty == 9 and r.side.value == "buy"
    assert r.time_in_force.value == "day"


def test_live_noise_uses_qqqm_when_ibs_holds_qqq(tmp_path, monkeypatch):
    from swingtrader.daily import executor as E
    monkeypatch.setattr(E.md, "live_rows", lambda syms, **k: pd.DataFrame(
        {"price": [200.0], "high": [201.0], "low": [199.0]}, index=syms))
    held = {"QQQ": SimpleNamespace(current_price="500", qty="3")}
    ex = _executor(tmp_path, monkeypatch, held=held)
    ex.d.noise_extra = {}
    b = _live_noise_book(pos=-1, lev=2.0)
    b.positions["QQQ"] = {"qty": 3, "avg_px": 500.0, "leg": "ibs", "entry_date": "2026-09-23"}
    ex._sync_noise_live(b, "2026-09-24", 500.0)
    r = ex.broker.client.submitted[0]
    assert r.symbol == "QQQM", "two legs must never share a symbol: Alpaca nets per symbol"
    assert r.side.value == "sell" and r.qty == math.floor(2.0 * b.equity({"QQQ": 500}) / 200.0)


def test_two_instruments_split_the_intraday_budget(tmp_path, monkeypatch):
    """QQQ + SMH share the 1.5x cap: 0.75x each (addendum 16). SMH trades
    SOXX on a day the IBS leg holds SMH."""
    from swingtrader.daily import executor as E
    monkeypatch.setattr(E.md, "live_rows", lambda syms, **k: pd.DataFrame(
        {"price": [250.0], "high": [251.0], "low": [249.0]}, index=syms))
    ex = _executor(tmp_path, monkeypatch, held={"SMH": SimpleNamespace(current_price="300", qty="2")})
    ex.d.noise_extra = {"SMH": "SOXX"}
    b = _live_noise_book(lev=3.0, cap=1.5)
    b.positions["SMH"] = {"qty": 2, "avg_px": 300.0, "leg": "ibs", "entry_date": "2026-09-23"}
    b.noise_more["SMH"] = {"day": "2026-09-24", "pos": -1, "lev": 3.0, "last_m": 30, "entry": 300.0}
    eq = b.equity({"SMH": 300})
    ex._sync_noise_live(b, "2026-09-24", 500.0)                   # QQQ
    ex._sync_noise_live(b, "2026-09-24", 300.0, "SMH")            # SMH -> SOXX
    q, x = ex.broker.client.submitted
    assert q.symbol == "QQQ" and q.qty == math.floor(0.75 * eq / 500.0) and q.side.value == "buy"
    assert x.symbol == "SOXX" and x.qty == math.floor(0.75 * eq / 250.0) and x.side.value == "sell"
    assert ex._noise_signals() == ["QQQ", "SMH"]


def test_live_noise_flattens_with_a_market_order_at_1557(tmp_path, monkeypatch):
    ex = _executor(tmp_path, monkeypatch)
    b = _live_noise_book()
    b.noise["instrument"] = "QQQM"
    b.positions["QQQM"] = {"qty": -12, "avg_px": 200.0, "leg": "noise", "entry_date": "2026-09-24"}
    ex._flatten_noise(b, "2026-09-24")
    r = ex.broker.client.submitted[0]
    assert r.symbol == "QQQM" and r.side.value == "buy" and r.qty == 12
    assert r.time_in_force.value == "day", "Alpaca paper expired a CLS flatten of QQQ: 0 of 7 filled"


def test_open_phase_closes_a_leftover_intraday_position(tmp_path, monkeypatch):
    from swingtrader.daily import executor as E
    monkeypatch.setattr(E.md, "sip_daily", lambda syms, *a, **k: {})
    monkeypatch.setattr(E.md, "eligibility", lambda *a, **k: pd.DataFrame())
    monkeypatch.setattr(E, "all_assets", lambda: SimpleNamespace(symbols=[]))
    ex = _executor(tmp_path, monkeypatch, held={"QQQ": SimpleNamespace(current_price="740", qty="-7")})
    book = DailyBook(cash=8173, start_equity=3000)
    book.positions["QQQ"] = {"qty": -7, "avg_px": 739.08, "leg": "noise", "entry_date": "2026-09-23"}
    ex.phase_open(book, "2026-09-24")
    r = [x for x in ex.broker.client.submitted if x.symbol == "QQQ"][0]
    assert r.side.value == "buy" and r.qty == 7 and r.time_in_force.value == "day"
    assert any("left over" in w for w in ex.warnings)


def test_duplicate_bets_collapse_to_one():
    rng = np.random.default_rng(0)
    spacex = rng.normal(0, 0.05, 20)
    rets = {f"SPX{i}": list(2 * spacex + rng.normal(0, 0.002, 20)) for i in range(7)}   # seven 2x SpaceX ETFs
    rets["ASTS"] = list(rng.normal(0, 0.04, 20))
    rets["ASTX"] = list(2 * np.array(rets["ASTS"]) + rng.normal(0, 0.002, 20))           # 2x ASTS
    rets["JAGX"] = list(rng.normal(0, 0.06, 20))                                          # unrelated
    picks = pd.DataFrame({"day_ret": [-0.20, -0.19, -0.18, -0.17, -0.16, -0.15, -0.14, -0.13, -0.12, -0.11]},
                         index=["SPX3", "ASTX", "SPX0", "SPX1", "JAGX", "SPX2", "ASTS", "SPX4", "SPX5", "SPX6"])
    kept, dropped = sg.dedupe_correlated(picks, rets, 0.9)
    assert list(kept.index) == ["SPX3", "ASTX", "JAGX"], "most-beaten of each bet is the one kept"
    assert dict(dropped)["ASTS"] == "ASTX" and dict(dropped)["SPX6"] == "SPX3"
    # no history -> kept (never silently dropped)
    k2, _ = sg.dedupe_correlated(pd.DataFrame(index=["NEW"]), {}, 0.9)
    assert list(k2.index) == ["NEW"]


def test_reconcile_books_a_vanished_position_at_last_price(tmp_path, monkeypatch):
    """A position the broker no longer holds must not be credited at its ENTRY
    price -- that invents cash and silently discards the P&L."""
    ex = _executor(tmp_path, monkeypatch, held={})
    ex._last_price = lambda sym, fallback: 7.0
    book = DailyBook(cash=1000, start_equity=3000)
    book.positions["X"] = {"qty": 10, "avg_px": 10.0, "leg": "night",
                           "entry_date": "2026-09-20"}
    ex.reconcile(book, "2026-09-23")
    assert "X" not in book.positions
    assert book.cash == pytest.approx(1000 + 70.0), "credited the entry price, not the last mark"
    assert book.closed and book.closed[-1]["exit_px"] == 7.0
    assert book.closed[-1]["pnl"] == pytest.approx(-30.0)


def test_fallback_clock_is_a_weekday_rth_guess():
    from swingtrader.daily.brokers import _fallback_clock
    c = _fallback_clock()
    assert isinstance(c.is_open, bool)
    assert c.next_open.weekday() < 5 and c.next_close.hour == 16
    # like Alpaca's clock: during the session the next close (today) comes
    # before the next open (tomorrow); outside it, the open comes first
    assert (c.next_close < c.next_open) == c.is_open


def test_prev_close_mismatch_catches_an_unabsorbed_split():
    rows = pd.DataFrame({"price": [10.0, 50.0, 9.0], "prev_close": [100.0, 52.0, 10.0],
                         "feed_prev_close": [10.2, 52.0, np.nan]}, index=["SPLT", "OK", "NOFEED"])
    bad = sg.prev_close_mismatch(rows)
    assert bad.to_dict() == {"SPLT": True, "OK": False, "NOFEED": False}
    assert not sg.prev_close_mismatch(rows.drop(columns="feed_prev_close")).any()


def test_night_exit_cost_scores_sells_against_the_official_open():
    fills = [
        {"sym": "AAA", "leg": "night", "side": "buy", "fill_px": 10.0, "filled_at": "2026-09-23T20:00"},
        {"sym": "AAA", "leg": "night", "side": "sell", "fill_px": 9.98, "filled_at": "2026-09-24T13:30"},
        {"sym": "BBB", "leg": "night", "side": "sell", "fill_px": 20.02, "filled_at": "2026-09-24"},
        {"sym": "CCC", "leg": "ibs", "side": "sell", "fill_px": 1.0, "filled_at": "2026-09-24"},
        {"sym": "DDD", "leg": "night", "side": "sell", "fill_px": 5.0, "filled_at": "2026-09-24"},
    ]
    opens = {("AAA", "2026-09-24"): 10.0, ("BBB", "2026-09-24"): 20.0}
    n, bps = sg.night_exit_cost(fills, opens)
    assert n == 2                                  # DDD has no open; buys and IBS ignored
    assert bps == pytest.approx((20.0 + -10.0) / 2)


def test_exit_cost_by_route_scores_auction_hits():
    from swingtrader.daily.signals import exit_cost_by_route
    opens = {("A", "2026-09-24"): 10.00, ("B", "2026-09-24"): 20.00}
    fills = [
        {"leg": "night", "side": "sell", "sym": "A", "fill_px": 10.00, "route": "NASDAQ",
         "filled_at": "2026-09-24T13:30:01+0000"},
        {"leg": "night", "side": "sell", "sym": "B", "fill_px": 19.96, "route": "AUTO",
         "filled_at": "2026-09-24T13:30:02+0000"},
        {"leg": "night", "side": "buy", "sym": "B", "fill_px": 1.0, "filled_at": "2026-09-24"},
    ]
    r = exit_cost_by_route(fills, opens)
    assert r["NASDAQ"] == (1, 0.0, 1.0)
    n, bps, hit = r["AUTO"]
    assert n == 1 and abs(bps - 20.0) < 1e-6 and hit == 0.0


def test_kill_rule_needs_enough_trades_and_a_real_loss():
    from swingtrader.daily.signals import kill_check
    rng = np.random.default_rng(0)
    lose = [{"leg": "night", "ret": x} for x in rng.normal(-0.008, 0.03, 150)]
    assert "night" in kill_check(lose)
    assert kill_check(lose[:99]) == {}, "fewer than 100 round trips: no verdict"
    flat = [{"leg": "night", "ret": x} for x in rng.normal(0.002, 0.03, 150)]
    assert kill_check(flat) == {}
    unknown = [dict(c, note="broker no longer holds") for c in lose]
    assert kill_check(unknown) == {}, "unknown-price exits are not evidence"


def test_realised_drawdown_ignores_deposits():
    from swingtrader.daily.signals import realised_drawdown
    closed = [{"pnl": 100, "exit_date": "2026-10-01"}, {"pnl": -900, "exit_date": "2026-10-02"},
              {"pnl": 50, "exit_date": "2026-10-03"}]
    assert abs(realised_drawdown(closed, 3000) - (-0.30)) < 1e-9
    assert realised_drawdown(closed, 30000) > -0.25, "same loss on a bigger account is smaller"


def test_killed_night_leg_places_no_buys(tmp_path, monkeypatch):
    import datetime as dt
    from types import SimpleNamespace
    from zoneinfo import ZoneInfo
    from swingtrader.config import Config
    from swingtrader.daily import executor as E
    from swingtrader.daily.book import DailyBook
    ex = E.DailyExecutor(Config.load(), account="paper", broker=FakeBroker(), state_dir=tmp_path,
                         log_dir=tmp_path)
    book = DailyBook(cash=3000, start_equity=3000, killed={"night": {"date": "x", "reason": "t"}})
    now = dt.datetime(2026, 9, 24, 15, 40, tzinfo=ZoneInfo("America/New_York"))
    clock = SimpleNamespace(next_close=pd.Timestamp("2026-09-24 16:00", tz="America/New_York"))
    monkeypatch.setattr(ex, "_check_exit_cost", lambda *a: None)
    ex.phase_close(book, "2026-09-24", now, clock)
    assert not book.orders and any("killed" in l for l in ex.lines)


def test_night_tilt_weights_deeper_drops_and_keeps_gross():
    w = sg.night_tilt([0.9, 0.9, 0.9], [-0.08, -0.12, -0.25])
    assert abs(w.mean() - 1) < 1e-12 and w[0] < w[1] < w[2]
    assert (sg.night_tilt([0.9, 0.9], [-0.1, -0.2], k=0) == 1).all()
    assert np.isfinite(sg.night_tilt([np.nan, 1.2], [-0.1, -0.09])).all()


def test_night_tilt_matches_the_research_simulator():
    """research/sim/experiments.py fitted these on 2021-23; the live function
    must give the same weights the addendum-16 numbers were produced with."""
    vol, day = np.array([0.7, 1.4, 2.5]), np.array([-0.09, -0.15, -0.30])
    mu, sd = np.array([0.0959, -0.1232]), np.array([0.4992, 0.061])
    z = (np.column_stack([np.log(vol), day]) - mu) / sd
    ref = np.clip(1 + 0.25 * (z @ np.array([1.14, -11.54])) / 12.07, 0.25, 2.0)
    assert np.allclose(sg.night_tilt(vol, day), ref / ref.mean())


def test_leverage_gate_needs_proven_costs():
    ok = lambda **kw: sg.lever_ok(**{**dict(n_exits=60, exit_bps=6.0, killed={}, drawdown=-0.03,
                                          multiplier=2.0), **kw})[0]
    assert ok()
    assert not ok(n_exits=49), "not enough evidence yet"
    assert not ok(exit_bps=12.0), "fills worse than the gate"
    assert not ok(exit_bps=float("nan"))
    assert not ok(killed={"noise": {}}), "any kill closes the gate"
    assert not ok(drawdown=-0.12)
    assert not ok(multiplier=1.0), "cash account"


def test_levered_book_sizes_both_overnight_legs_up(tmp_path, monkeypatch):
    ex = _executor(tmp_path, monkeypatch)
    b = DailyBook(cash=3000, start_equity=3000)
    assert ex._w_night(b) == 0.5 and ex._w_ibs(b) == 0.5
    b.levered = True
    assert ex._w_night(b) == 0.65 and ex._w_ibs(b) == 0.65
    ex.d.lever_weight = None
    assert ex._w_night(b) == 0.5


def test_gap_scale_halves_weekend_and_holiday_nights():
    assert sg.gap_scale("2026-09-25", pd.Timestamp("2026-09-28 09:30", tz=ET), 0.5) == 0.5   # Fri -> Mon
    assert sg.gap_scale("2026-09-24", pd.Timestamp("2026-09-25 09:30", tz=ET), 0.5) == 1.0   # Thu -> Fri
    assert sg.gap_scale("2026-11-25", pd.Timestamp("2026-11-27 09:30", tz=ET), 0.5) == 0.5   # Thanksgiving
    assert sg.gap_scale("2026-09-25", pd.Timestamp("2026-09-28 09:30", tz=ET), 1.0) == 1.0


def test_friday_close_buys_half_size(tmp_path, monkeypatch):
    from swingtrader.daily import executor as E
    monkeypatch.setattr(E.md, "eligibility", lambda *a, **k: pd.DataFrame(
        {"prev_close": [10.0], "vol20": [0.9]}, index=["LOSER"]))
    monkeypatch.setattr(E.md, "live_rows", lambda syms, *a, **k: pd.DataFrame(
        {"price": [9.0], "high": [10.0], "low": [8.99]}, index=["LOSER"]))
    monkeypatch.setattr(E, "all_assets", lambda: SimpleNamespace(symbols=["LOSER"]))
    ex = _executor(tmp_path, monkeypatch)
    monkeypatch.setattr(ex, "_check_exit_cost", lambda *a: None)
    qty = {}
    for day, nxt in (("2026-09-24", "2026-09-25 09:30"), ("2026-09-25", "2026-09-28 09:30")):
        ex.broker.client.submitted.clear()
        clock = SimpleNamespace(is_open=True, next_open=pd.Timestamp(nxt, tz=ET),
                                next_close=pd.Timestamp(f"{day} 16:00", tz=ET))
        book = DailyBook(cash=3000, start_equity=3000)
        ex.phase_close(book, day, dt.datetime.fromisoformat(f"{day}T15:40").replace(tzinfo=ET), clock)
        qty[day] = float(ex.broker.client.submitted[0].qty)
    assert qty["2026-09-25"] == math.floor(3000 * 0.5 * 0.10 * 0.5 / 9.0)
    assert qty["2026-09-24"] == math.floor(3000 * 0.5 * 0.10 / 9.0)


# --------------------------------------- conviction day trade (addendum 19)
def test_breakout_strength():
    assert sg.breakout_strength(101.0, 100.0, 98.0, 0.01) == (1, pytest.approx(1.0))
    d, st = sg.breakout_strength(97.0, 100.0, 98.0, 0.01)
    assert d == -1 and st == pytest.approx((1 - 97 / 98) / 0.01)
    assert sg.breakout_strength(99.0, 100.0, 98.0, 0.01) == (0, 0.0)


def _conv_minutes(path):
    """Minute bars where close[m] follows `path` {minute: price}, flat volume."""
    c = np.full(390, 100.0)
    for m, px in sorted(path.items()):
        c[m:] = px
    return {pd.Timestamp("2026-09-24"): {"close": c, "volume": np.ones(390), "last_minute": 389, "open": 100.0}}


def _conv_exec(tmp_path, monkeypatch, path, live=False):
    from swingtrader.daily import executor as E
    ex = _executor(tmp_path, monkeypatch)
    monkeypatch.setattr(E.md, "minute_today", lambda sym: _conv_minutes(path))
    monkeypatch.setattr(E.md, "live_rows", lambda syms, **k: pd.DataFrame(
        {"price": [50.0], "high": [51.0], "low": [49.0]}, index=syms))
    band = {"sigma": np.full(390, 0.01), "ub": np.full(390, 101.0), "lb": np.full(390, 99.0),
            "open": 100.0, "prev_close": 100.0, "daily": None, "src": "test"}
    monkeypatch.setattr(ex, "_day_bands", lambda sym, today: band)
    ex.d.conviction_mode = "auto" if live else "shadow"
    b = DailyBook(cash=3000, start_equity=3000)
    b.daytrade_live = live
    return ex, b


def test_conviction_takes_only_a_strong_first_breakout(tmp_path, monkeypatch):
    # 10:00 +1.5% vs band 101 at sigma 1%: strength 0.49 -> long; out at 11:00 back inside
    ex, b = _conv_exec(tmp_path, monkeypatch, {30: 101.5, 60: 102.0, 90: 100.5})
    ex._conviction_one(b, "2026-09-24")
    h = b.conviction["history"]
    assert len(h) == 1 and h[0]["dir"] == 1 and h[0]["ret"] == pytest.approx(100.5 / 101.5 - 1, abs=1e-5)
    assert not ex.broker.client.submitted, "shadow mode places nothing"


def test_conviction_skips_the_day_when_the_first_breakout_is_weak(tmp_path, monkeypatch):
    # first breakout at 10:00 is weak (0.1 sigma); a later strong one must NOT be taken
    ex, b = _conv_exec(tmp_path, monkeypatch, {30: 101.1, 60: 100.0, 90: 104.0})
    ex._conviction_one(b, "2026-09-24")
    assert b.conviction["done"] and b.conviction["pos"] == 0 and not b.conviction["history"]


def test_conviction_live_buys_sqqq_for_a_down_breakout(tmp_path, monkeypatch):
    ex, b = _conv_exec(tmp_path, monkeypatch, {30: 98.0}, live=True)
    ex._conviction_one(b, "2026-09-24")
    r = ex.broker.client.submitted[0]
    assert r.symbol == "SQQQ" and r.side.value == "buy"
    assert float(r.qty) == math.floor(0.5 * 3000 / 50.0)


def test_conviction_shares_the_daytime_budget(tmp_path, monkeypatch):
    ex = _executor(tmp_path, monkeypatch)
    ex.broker.account = lambda: SimpleNamespace(equity="3000", multiplier="2")
    book = DailyBook(cash=3000, start_equity=3000)
    ex.d.conviction_mode = "shadow"
    ex._gate(book, 3000)
    assert book.noise_lev_cap == pytest.approx(1.5), "shadow: the regular leg keeps the whole budget"
    ex.d.conviction_mode = "auto"
    ex._gate(book, 3000)
    # TQQQ is a 3x ETF: 75% house margin, so 0.5 of equity in it uses 0.375 of
    # the account, leaving 2 x 0.625 = 1.25 of buying power, minus 0.5 IBS
    assert book.noise_lev_cap == pytest.approx(0.75), "3x-ETF margin shrinks the intraday room"


# ------------------------------------- hostile review: probes, cap, Roth IRA
class LiveMarginBroker(FakeBroker):
    key, secret = "AKTEST", "SEC"

    def __init__(self, equity="1000", held=None):
        super().__init__(held)
        self.eq = equity

    def account(self):
        return SimpleNamespace(equity=self.eq, multiplier="2", trading_blocked=False,
                               account_blocked=False, account_type="MARGIN")


def _night_rows(monkeypatch, prices: dict):
    from swingtrader.daily import executor as E
    syms = list(prices)
    elig = pd.DataFrame({"prev_close": [p / 0.9 for p in prices.values()]}, index=syms)
    live = pd.DataFrame({"price": list(prices.values()),
                         "high": [p / 0.9 for p in prices.values()],
                         "low": [p * 0.999 for p in prices.values()]}, index=syms)
    monkeypatch.setattr(E.md, "eligibility", lambda *a, **k: elig)
    monkeypatch.setattr(E.md, "live_rows", lambda s, *a, **k: live.loc[[x for x in s if x in live.index]])
    monkeypatch.setattr(E, "all_assets", lambda: SimpleNamespace(symbols=syms))


def test_live_night_probe_buys_one_share_of_a_name_that_rounds_to_zero(tmp_path, monkeypatch):
    _night_rows(monkeypatch, {"CHEAP": 9.0, "MID": 80.0, "DEAR": 400.0})
    ex = DailyExecutor(Config.load(), account="live", broker=LiveMarginBroker("1000"),
                       state_dir=tmp_path, log_dir=tmp_path)
    ex.notifier.send = lambda *a, **k: "skipped"
    ex.d.quote_source = "alpaca"
    ex.d.night_probe_max_usd = 150.0
    ex.d.night_tilt_k = 0
    monkeypatch.delenv("DAILY_LIVE_CAPITAL", raising=False)
    book = DailyBook(cash=1000, start_equity=1000)
    ex.phase_close(book, "2026-09-23", dt.datetime(2026, 9, 23, 15, 40, tzinfo=ET), ex.broker.clock())
    reqs = {r.symbol: r for r in ex.broker.client.submitted}
    # $1000 * 0.5 * 10% = $50 a name
    assert reqs["CHEAP"].qty == 5
    assert reqs["MID"].qty == 1, "rounds to 0 -> one-share probe (<= $150)"
    assert "DEAR" not in reqs, "a probe never costs more than night_probe_max_usd"
    ex.d.night_probe_max_usd = None
    ex.broker.client.submitted.clear(); book = DailyBook(cash=1000, start_equity=1000)
    ex.phase_close(book, "2026-09-24", dt.datetime(2026, 9, 24, 15, 40, tzinfo=ET), ex.broker.clock())
    assert "MID" not in {r.symbol for r in ex.broker.client.submitted}


def test_paper_book_never_probes(tmp_path, monkeypatch):
    _night_rows(monkeypatch, {"MID": 400.0})
    ex = _executor(tmp_path, monkeypatch)
    ex.d.night_probe_max_usd = 1000.0
    book = DailyBook(cash=3000, start_equity=3000)
    ex.phase_close(book, "2026-09-23", dt.datetime(2026, 9, 23, 15, 40, tzinfo=ET), ex.broker.clock())
    assert ex.broker.client.submitted == []


def test_live_cap_below_2k_does_not_keep_the_intraday_leg_shadow(tmp_path, monkeypatch):
    ex = DailyExecutor(Config.load(), account="live", broker=LiveMarginBroker("5000"),
                       state_dir=tmp_path, log_dir=tmp_path)
    book = DailyBook(cash=1000, start_equity=1000)
    ex._gate(book, 1000)                  # $1,000 cap on a $5,000 margin account
    assert book.daytrade_live, "Reg T's $2,000 is an account minimum, not a bot-capital minimum"
    ex.broker.b.eq = "1500"
    ex._gate(book, 1000)
    assert not book.daytrade_live, "the account itself is under $2,000"
    ex.broker.b.eq = "5000"
    ex._gate(book, 300)
    assert not book.daytrade_live, "under live_min_capital the bot trades nothing"


class RothBroker(LiveMarginBroker):
    def account(self):
        return SimpleNamespace(equity=self.eq, multiplier="1", trading_blocked=False,
                               account_blocked=False, account_type="CASH")


def test_roth_book_is_its_own_account_and_never_levers(tmp_path, monkeypatch):
    from swingtrader.daily.book import book_file
    assert len({book_file("paper"), book_file("live"), book_file("roth")}) == 3
    ex = DailyExecutor(Config.load(), account="roth", broker=RothBroker("5000"),
                       state_dir=tmp_path, log_dir=tmp_path)
    assert ex.live and ex.cash_account and ex.tag == "-roth"
    book = DailyBook(cash=5000, start_equity=5000)
    book.levered = True
    ex._lever_gate(book)
    assert not book.levered, "never lever an IRA"
    assert ex._w_night(book) == ex.d.night_weight
    ex.d.conviction_mode = "auto"
    ex._gate(book, 5000)
    assert book.daytrade_live
    assert not ex._conviction_live(book), "conviction's TQQQ/SQQQ are the Roth's intraday ETFs"
    # daytime cash = the night half (0.5) held in 3x ETFs -> 1.5x underlying
    assert book.noise_lev_cap == pytest.approx(1.5)


def test_roth_refuses_to_trade_without_limited_margin(tmp_path, monkeypatch):
    from swingtrader.daily import executor as E
    monkeypatch.setattr(E.md, "eligibility", lambda *a, **k: pd.DataFrame())
    monkeypatch.setattr(E, "all_assets", lambda: SimpleNamespace(symbols=[]))
    for flag, rc in (("no", 1), ("yes", 0)):
        monkeypatch.setenv("ROTH_LIMITED_MARGIN", flag)
        ex = DailyExecutor(Config.load(), account="roth", broker=RothBroker("5000"),
                           state_dir=tmp_path, log_dir=tmp_path, dry_run=True)
        ex.notifier.send = lambda *a, **k: "skipped"
        ex.d.quote_source = "alpaca"
        assert ex.run(phase="reconcile") == rc
    monkeypatch.setenv("ROTH_LIMITED_MARGIN", "no")
    live = DailyExecutor(Config.load(), account="live", broker=LiveMarginBroker("5000"),
                         state_dir=tmp_path, log_dir=tmp_path, dry_run=True)
    live.notifier.send = lambda *a, **k: "skipped"
    assert live.run(phase="reconcile") == 0, "the flag is a Roth-only requirement"


def test_roth_intraday_is_long_only_in_3x_etfs(tmp_path, monkeypatch):
    from swingtrader.daily import executor as E
    px = {"TQQQ": 100.0, "SQQQ": 20.0}
    monkeypatch.setattr(E.md, "live_rows", lambda syms, *a, **k: pd.DataFrame(
        {"price": [px[s] for s in syms]}, index=syms))
    ex = DailyExecutor(Config.load(), account="roth", broker=RothBroker("6000"),
                       state_dir=tmp_path, log_dir=tmp_path)
    monkeypatch.delenv("DAILY_ROTH_CAPITAL", raising=False)
    monkeypatch.setattr(ex, "_noise_signals", lambda: ["QQQ"])
    book = DailyBook(cash=6000, start_equity=6000)
    book.noise_lev_cap = 1.5
    book.noise = {"day": "2026-09-23", "pos": -1, "lev": 3.0, "last_m": 60, "entry": 500.0}
    ex._sync_noise_live(book, "2026-09-23", 500.0, "QQQ")
    r = ex.broker.client.submitted[-1]
    # 1.5x underlying / 3 = 0.5 of $6,000 in SQQQ at $20 -> 150 shares, BOUGHT
    assert (r.symbol, r.side.value, r.qty) == ("SQQQ", "buy", 150)
    book.positions["SQQQ"] = {"qty": 150, "avg_px": 20.0, "leg": "noise", "entry_date": "2026-09-23"}
    book.orders.clear()
    book.noise["pos"], book.noise["last_m"] = 1, 90
    ex._sync_noise_live(book, "2026-09-23", 510.0, "QQQ")
    sent = [(r.symbol, r.side.value, r.qty) for r in ex.broker.client.submitted[1:]]
    assert ("SQQQ", "sell", 150) in sent and ("TQQQ", "buy", 30) in sent
    assert all(r.side.value in ("buy", "sell") for r in ex.broker.client.submitted), "never shorts"


def test_real_money_books_stay_out_of_each_others_wash_sale_window(tmp_path, monkeypatch):
    live = DailyBook(cash=1000, start_equity=1000)
    live.positions["ABC"] = {"qty": 3, "avg_px": 10.0, "leg": "night", "entry_date": "2026-09-22"}
    live.closed = [{"sym": "OLD", "leg": "night", "exit_date": "2026-08-01", "ret": -0.01, "pnl": -1},
                   {"sym": "NEW", "leg": "night", "exit_date": "2026-09-10", "ret": -0.01, "pnl": -1},
                   {"sym": "SGOV", "leg": "tbill", "exit_date": "2026-09-10", "ret": 0, "pnl": 0}]
    live.save(tmp_path, "book-daily-live.json")
    roth = DailyExecutor(Config.load(), account="roth", broker=RothBroker("5000"),
                         state_dir=tmp_path, log_dir=tmp_path)
    w = roth._wash_symbols("2026-09-23")
    assert {"ABC", "NEW"} <= w and "OLD" not in w and "SGOV" not in w
    assert "NEW" in roth._foreign_symbols(DailyBook(cash=5000, start_equity=5000))
    assert _executor(tmp_path, monkeypatch)._wash_symbols("2026-09-23") == set(), "paper is not real money"


def test_roth_capital_cap_is_its_own_env_var(tmp_path, monkeypatch):
    monkeypatch.setenv("DAILY_LIVE_CAPITAL", "1000")
    monkeypatch.setenv("DAILY_ROTH_CAPITAL", "4000")
    roth = DailyExecutor(Config.load(), account="roth", broker=RothBroker("9000"),
                         state_dir=tmp_path, log_dir=tmp_path)
    live = DailyExecutor(Config.load(), account="live", broker=LiveMarginBroker("9000"),
                         state_dir=tmp_path, log_dir=tmp_path)
    assert roth.live_cap() == 4000 and live.live_cap() == 1000


def test_roth_switch_and_accounts(tmp_path, monkeypatch):
    import importlib, sys as _s
    _s.path.insert(0, "scripts")
    sw = importlib.import_module("daily_switch")
    env = tmp_path / ".env"
    env.write_text("DAILY_LIVE=on\n")
    monkeypatch.setattr(sw, "ENV", env)
    sw.set_live(True, "roth")
    assert env.read_text() == "DAILY_LIVE=on\nDAILY_ROTH=on\n"
    monkeypatch.setenv("DAILY_LIVE", "off")
    assert Config.load().daily.resolved_accounts() == ["paper", "roth"]
    sw.set_live(False, "roth")
    assert "DAILY_ROTH=off" in env.read_text() and "DAILY_LIVE=on" in env.read_text()


def test_schwab_roth_adapter_never_guesses_the_account(monkeypatch):
    from swingtrader.daily.brokers import SchwabAdapter

    class C:
        def get_account_numbers(self):
            return SimpleNamespace(raise_for_status=lambda: None, json=lambda: [
                {"accountNumber": "11111234", "hashValue": "HBROK"},
                {"accountNumber": "22225678", "hashValue": "HROTH"}])

    monkeypatch.setenv("SCHWAB_ACCOUNT_NUMBER", "1234")
    monkeypatch.setenv("SCHWAB_ROTH_ACCOUNT_NUMBER", "5678")
    assert SchwabAdapter(client=C()).hash == "HBROK"
    assert SchwabAdapter(client=C(), account_env="SCHWAB_ROTH_ACCOUNT_NUMBER").hash == "HROTH"
    monkeypatch.setenv("SCHWAB_ROTH_ACCOUNT_NUMBER", "")
    with pytest.raises(RuntimeError, match="SCHWAB_ROTH_ACCOUNT_NUMBER"):
        SchwabAdapter(client=C(), account_env="SCHWAB_ROTH_ACCOUNT_NUMBER")


# ------------------------------------------ addendum 22: experimental profile
def test_live_profile_overrides_only_the_brokerage_book(tmp_path, monkeypatch):
    monkeypatch.setenv("DAILY_LIVE_PROFILE", "aggressive")
    cfg = Config.load()
    live = DailyExecutor(cfg, account="live", broker=LiveMarginBroker("5000"),
                         state_dir=tmp_path, log_dir=tmp_path)
    paper = _executor(tmp_path, monkeypatch)
    roth = DailyExecutor(cfg, account="roth", broker=RothBroker("5000"),
                         state_dir=tmp_path, log_dir=tmp_path)
    assert live.d.night_weight == 0.65 and live.d.night_max_name_pct == 0.20
    assert live.d.conviction_mode == "auto" and live.d.lever_weight is None
    assert paper.d.night_weight == 0.5 and roth.d.night_weight == 0.5
    assert cfg.daily.night_weight == 0.5, "the shared config is not mutated"
    book = DailyBook(cash=5000, start_equity=5000)
    live._gate(book, 5000)
    assert book.noise_lev_cap == pytest.approx(0.6)
    monkeypatch.setenv("DAILY_LIVE_PROFILE", "nope")
    with pytest.raises(ValueError, match="nope"):
        DailyExecutor(Config.load(), account="live", broker=LiveMarginBroker("5000"),
                      state_dir=tmp_path, log_dir=tmp_path)


def test_roth_never_goes_above_1x_overnight_whatever_the_weights(tmp_path, monkeypatch):
    roth = DailyExecutor(Config.load(), account="roth", broker=RothBroker("5000"),
                         state_dir=tmp_path, log_dir=tmp_path)
    roth.d = dataclasses.replace(roth.d, night_weight=0.65, ibs_weight=0.65)
    book = DailyBook(cash=5000, start_equity=5000)
    assert roth._w_night(book) + roth._w_ibs(book) == pytest.approx(1.0)


# ------------------------------------------------- addendum 23: tilt v2
def test_night_tilt_v2_weights_yesterdays_winners_up_and_keeps_gross():
    w = sg.night_tilt_v2([1.0, 1.0, 1.0], [-0.12, -0.12, -0.12], [0.30, 0.0096, np.nan])
    assert w.mean() == pytest.approx(1.0)
    assert w[0] > w[1] == pytest.approx(w[2]), "up yesterday -> bigger; unknown -> the fit mean"
    assert np.all(sg.night_tilt_v2([1, 1], [-0.1, -0.2], [0, 0], k=0) == 1)
    extreme = sg.night_tilt_v2([1.0, 1.0], [-0.12, -0.12], [5.0, 0.61])
    assert extreme[0] == pytest.approx(extreme[1]), "winsorised at the fit's 99th percentile"
