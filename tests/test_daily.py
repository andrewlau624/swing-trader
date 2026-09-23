"""Daily-book tests. Nothing here touches the network."""
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
    b = _live_noise_book(pos=-1, lev=2.0)
    b.positions["QQQ"] = {"qty": 3, "avg_px": 500.0, "leg": "ibs", "entry_date": "2026-09-23"}
    ex._sync_noise_live(b, "2026-09-24", 500.0)
    r = ex.broker.client.submitted[0]
    assert r.symbol == "QQQM", "two legs must never share a symbol: Alpaca nets per symbol"
    assert r.side.value == "sell" and r.qty == math.floor(2.0 * b.equity({"QQQ": 500}) / 200.0)


def test_live_noise_flattens_its_own_instrument_at_the_close(tmp_path, monkeypatch):
    ex = _executor(tmp_path, monkeypatch)
    b = _live_noise_book()
    b.noise["instrument"] = "QQQM"
    b.positions["QQQM"] = {"qty": -12, "avg_px": 200.0, "leg": "noise", "entry_date": "2026-09-24"}
    ex._flatten_noise(b, "2026-09-24")
    r = ex.broker.client.submitted[0]
    assert r.symbol == "QQQM" and r.side.value == "buy" and r.qty == 12
    assert r.time_in_force.value == "cls"
