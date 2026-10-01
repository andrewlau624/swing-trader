"""Day-trading lab: account guard, risk limits, flat-by-close, HALT, mode independence, fills,
strategies, recorder. No network."""
import ast
import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from daytrade import guard
from daytrade.engine import Engine
from daytrade.events import Bar, Clock, DayInfo, Order, Quote, Trade
from daytrade.feeds import rows_to_events
from daytrade.fills import SimBroker
from daytrade.recorder import Recording, select_gappers, token_copy
from daytrade.review import decide
from daytrade.risk import AccountModel
from daytrade.session import session_times
from daytrade.settings import Limits
from daytrade.strategies import REGISTRY
from daytrade.strategies.base import Strategy
from daytrade.strategies.gap_vwap_reclaim import GapVwapReclaim
from daytrade.strategies.open_imbalance import OpenImbalance

ET = ZoneInfo("America/New_York")
DAY = dt.date(2026, 10, 1)


def sessions(day=DAY, close_h=16):
    days = [day + dt.timedelta(days=i) for i in range(6)]
    days = [d for d in days if d.weekday() < 5]
    return [(dt.datetime.combine(d, dt.time(9, 30), ET),
             dt.datetime.combine(d, dt.time(close_h if d == day else 16, 0), ET)) for d in days]


def st(close_h=16):
    return session_times(DAY, sessions(close_h=close_h))


def t(hhmm, s=0):
    h, m = map(int, hhmm.split(":"))
    return dt.datetime(2026, 10, 1, h, m, s, tzinfo=ET)


def bar(sym, start, o, h, l, c, v=1000):
    s = t(start)
    return Bar(s + dt.timedelta(minutes=1), sym, o, h, l, c, v, s)


def env_of(d):
    return lambda name, default=None: d.get(name, default)


# ------------------------------------------------------------------ account guard
@pytest.mark.parametrize("lab,main,roth,leap", [
    (None, "12345678", "", ""),            # unset
    ("12345678", "12345678", "", ""),      # same as the live book
    ("5678", "12345678", "", ""),          # last-4 of the live book
    ("12345678", "", "99995678", "5678"),  # same as the leap book (suffix)
    ("11112222", "", "11112222", ""),      # same as the Roth
    ("12", "", "", ""),                    # too short to be sure
])
def test_account_guard_refuses(lab, main, roth, leap):
    e = env_of({"SCHWAB_DAYTRADE_ACCOUNT_NUMBER": lab, "SCHWAB_ACCOUNT_NUMBER": main,
                "SCHWAB_ROTH_ACCOUNT_NUMBER": roth, "SCHWAB_LEAP_ACCOUNT_NUMBER": leap})
    with pytest.raises(guard.AccountGuardError):
        guard.check_lab_account(e)
    with pytest.raises(guard.AccountGuardError):
        guard.check_mode("live", e)


def test_account_guard_accepts_a_distinct_account_and_replay_needs_none():
    e = env_of({"SCHWAB_DAYTRADE_ACCOUNT_NUMBER": "...4444", "SCHWAB_ACCOUNT_NUMBER": "12345678",
                "SCHWAB_ROTH_ACCOUNT_NUMBER": "87654321"})
    assert guard.check_lab_account(e) == "4444"
    guard.check_mode("replay", env_of({}))
    with pytest.raises(guard.AccountGuardError):
        guard.check_resolved("99994444", {"SCHWAB_ACCOUNT_NUMBER": "99994444"})
    guard.check_resolved("99994444", {"SCHWAB_ACCOUNT_NUMBER": "12345678"})


def test_paper_needs_its_own_alpaca_keys():
    base = {"SCHWAB_DAYTRADE_ACCOUNT_NUMBER": "4444", "SCHWAB_ACCOUNT_NUMBER": "12345678"}
    with pytest.raises(guard.AccountGuardError):
        guard.check_mode("paper", env_of(base))
    same = {**base, "ALPACA_DAYTRADE_API_KEY": "K", "ALPACA_DAYTRADE_SECRET_KEY": "S", "ALPACA_API_KEY": "K"}
    with pytest.raises(guard.AccountGuardError):
        guard.check_mode("paper", env_of(same))
    ok = {**same, "ALPACA_API_KEY": "OTHER"}
    guard.check_mode("paper", env_of(ok))


def test_live_needs_flag_approval_and_cap(monkeypatch, tmp_path):
    from daytrade import brokers
    monkeypatch.setenv("SCHWAB_DAYTRADE_ACCOUNT_NUMBER", "4444")
    monkeypatch.setenv("SCHWAB_ACCOUNT_NUMBER", "12345678")
    monkeypatch.setenv("SCHWAB_ROTH_ACCOUNT_NUMBER", "")
    monkeypatch.setenv("SCHWAB_LEAP_ACCOUNT_NUMBER", "")
    monkeypatch.setenv("DAYTRADE_LIVE", "")
    monkeypatch.setattr(brokers, "LIVE_APPROVAL", tmp_path / "LIVE_APPROVED")
    with pytest.raises(guard.AccountGuardError, match="DAYTRADE_LIVE"):
        brokers.live_allowed(500)
    monkeypatch.setenv("DAYTRADE_LIVE", "on")
    with pytest.raises(guard.AccountGuardError, match="approval"):
        brokers.live_allowed(500)
    (tmp_path / "LIVE_APPROVED").write_text("ok")
    with pytest.raises(guard.AccountGuardError, match="cap"):
        brokers.live_allowed(501)
    brokers.live_allowed(500)


# ------------------------------------------------------------------ helpers
class Scripted(Strategy):
    """Emits given orders at given times; records what it emitted."""
    name = "scripted"

    def __init__(self, plan):
        self.plan_ = sorted(plan, key=lambda x: x[0])
        self.emitted = []

    def on_clock(self, ctx):
        out = []
        while self.plan_ and ctx.now >= self.plan_[0][0]:
            out.append(self.plan_.pop(0)[1]())
        self.emitted += [(ctx.now, o.sym, o.side, o.entry) for o in out]
        return out


def minute_bars(sym, start, end, px=100.0, path=None):
    out, cur = [], t(start)
    i = 0
    while cur < t(end):
        p = path(i) if path else px
        out.append(Bar(cur + dt.timedelta(minutes=1), sym, p, p + 0.05, p - 0.05, p, 1000, cur))
        cur += dt.timedelta(minutes=1); i += 1
    return out


def engine(strats, tmp_path, equity=10_000, kind="margin", broker=None, s=None, **kw):
    return Engine(strats, broker or SimBroker(latency_s=1, cost_bp=0), equity=equity, session=s or st(),
                  account_kind=kind, halt_path=tmp_path / "HALT", **kw)


# ------------------------------------------------------------------ risk limits
def test_size_from_stop_and_notional_cap(tmp_path):
    s = Scripted([(t("10:00"), lambda: Order("AAA", "buy", ref_price=100.0, stop=99.0))])
    e = engine([s], tmp_path).run(minute_bars("AAA", "09:30", "10:30"))
    # 0.5% of 10k = $50 risk / $1 per share = 50 shares (notional 5k < 10k cap)
    assert e.trades[0]["qty"] == 50
    s = Scripted([(t("10:00"), lambda: Order("AAA", "buy", ref_price=100.0, stop=99.95))])
    e = engine([s], tmp_path).run(minute_bars("AAA", "09:30", "10:30"))
    assert e.trades[0]["qty"] == 100           # 1000 by risk, capped at 1.0x equity notional


def test_entry_needs_a_stop_on_the_right_side(tmp_path):
    s = Scripted([(t("10:00"), lambda: Order("AAA", "buy", ref_price=100.0)),
                  (t("10:01"), lambda: Order("AAA", "buy", ref_price=100.0, stop=101.0))])
    e = engine([s], tmp_path).run(minute_bars("AAA", "09:30", "10:30"))
    assert not e.trades and len([x for x in e.events if x["kind"] == "rejected"]) == 2


def test_daily_loss_limit_flattens_and_stops(tmp_path):
    # price falls 4% after entry; stop is far below; -2% of equity triggers the flatten
    s = Scripted([(t("10:00"), lambda: Order("AAA", "buy", ref_price=100.0, stop=60.0)),
                  (t("11:00"), lambda: Order("BBB", "buy", ref_price=50.0, stop=49.0))])
    path = lambda i: 100.0 if i < 31 else 100.0 - 0.5 * (i - 30)  # noqa: E731
    bars = sorted(minute_bars("AAA", "09:30", "12:00", path=path) + minute_bars("BBB", "09:30", "12:00", 50.0),
                  key=lambda b: (b.ts, b.sym))
    lim = Limits(risk_per_trade_pct=1.0)       # size by the notional cap: 100 shares
    e = engine([s], tmp_path, equity=10_000, limits=lim).run(bars)
    kinds = [x["kind"] for x in e.events]
    assert "daily loss limit" in kinds
    assert e.trades[0]["exit_reason"] == "daily loss limit"
    assert len(e.trades) == 1                   # BBB at 11:00 was refused: stopped for the day
    assert any("stopped for the day" in x["detail"] for x in e.events)


def test_no_adding_to_a_loser(tmp_path):
    s = Scripted([(t("10:00"), lambda: Order("AAA", "buy", ref_price=100.0, stop=95.0)),
                  (t("10:30"), lambda: Order("AAA", "buy", ref_price=99.0, stop=95.0))])
    path = lambda i: 100.0 if i < 45 else 99.0  # noqa: E731
    e = engine([s], tmp_path).run(minute_bars("AAA", "09:30", "11:00", path=path))
    assert any("averaging down" in x["detail"] for x in e.events)
    assert e.trades[0]["qty"] == 10             # $50 risk / $5 stop; never added to


def test_entry_cutoff_and_flat_by_close(tmp_path):
    s = Scripted([(t("15:00"), lambda: Order("AAA", "buy", ref_price=100.0, stop=99.0)),
                  (t("15:46"), lambda: Order("BBB", "buy", ref_price=100.0, stop=99.0))])
    bars = sorted(minute_bars("AAA", "14:50", "16:00") + minute_bars("BBB", "14:50", "16:00"),
                  key=lambda b: (b.ts, b.sym))
    e = engine([s], tmp_path).run(bars)
    assert [x["sym"] for x in e.trades] == ["AAA"]
    assert e.trades[0]["exit_reason"] == "flat by close"
    assert dt.datetime.fromisoformat(e.trades[0]["exit_ts"]) <= t("15:56")
    assert any("cutoff" in x["detail"] for x in e.events)
    assert not e.positions


def test_half_day_flat_time_comes_from_the_calendar(tmp_path):
    s13 = st(close_h=13)
    assert s13.flat_by == t("12:55") and s13.entry_cutoff == t("12:45")
    s = Scripted([(t("12:00"), lambda: Order("AAA", "buy", ref_price=100.0, stop=99.0))])
    e = engine([s], tmp_path, s=s13).run(minute_bars("AAA", "11:50", "13:00"))
    assert e.trades[0]["exit_reason"] == "flat by close"


def test_cash_account_uses_settled_cash_only(tmp_path):
    acct = AccountModel(1_500, "margin")        # under $2k: forced to cash
    assert acct.is_cash
    s = Scripted([(t("10:00"), lambda: Order("AAA", "buy", ref_price=10.0, stop=9.0)),
                  (t("10:10"), lambda: Order("AAA", "sell", entry=False)),
                  (t("10:20"), lambda: Order("BBB", "buy", ref_price=10.0, stop=9.9))])
    bars = sorted(minute_bars("AAA", "09:30", "11:00", 10.0) + minute_bars("BBB", "09:30", "11:00", 10.0),
                  key=lambda b: (b.ts, b.sym))
    lim = Limits(risk_per_trade_pct=0.5, max_position_pct=1.0)
    e = engine([s], tmp_path, account=acct, limits=lim, settle_day=DAY + dt.timedelta(days=1)).run(bars)
    assert e.trades[0]["qty"] == 150            # all settled cash
    assert len(e.trades) == 1                   # the proceeds are unsettled: the BBB buy is refused
    assert any("rounds to 0" in x["detail"] for x in e.events)
    acct.new_day(DAY + dt.timedelta(days=1))
    assert acct.buying_power() == pytest.approx(1_500, abs=1)


def test_no_shorts_in_a_cash_account(tmp_path):
    s = Scripted([(t("10:00"), lambda: Order("AAA", "sell", ref_price=100.0, stop=101.0))])
    e = engine([s], tmp_path, equity=1_000).run(minute_bars("AAA", "09:30", "10:30"))
    assert not e.trades and any("cash" in x["detail"] for x in e.events)


# ------------------------------------------------------------------ HALT
def test_halt_file_cancels_flattens_and_stops(tmp_path):
    halt = tmp_path / "HALT"

    class HaltAt(Scripted):
        def on_clock(self, ctx):
            if ctx.now >= t("10:30") and not halt.exists():
                halt.write_text("x")
            return super().on_clock(ctx)

    s = HaltAt([(t("10:00"), lambda: Order("AAA", "buy", ref_price=100.0, stop=99.0, target=110.0)),
                (t("10:45"), lambda: Order("BBB", "buy", ref_price=100.0, stop=99.0))])
    bars = sorted(minute_bars("AAA", "09:30", "11:00") + minute_bars("BBB", "09:30", "11:00"),
                  key=lambda b: (b.ts, b.sym))

    class Recording_(SimBroker):
        cancelled_all = False

        def cancel_all(self):
            self.cancelled_all = True
            self.open.clear()

    b = Recording_(latency_s=1, cost_bp=0)
    e = engine([s], tmp_path, broker=b).run(bars)
    assert e.halted and b.cancelled_all
    assert [x["exit_reason"] for x in e.trades] == ["halt"]
    assert not e.positions
    assert any(x["kind"] == "halt" for x in e.events)
    assert "BBB" not in {x["sym"] for x in e.trades}  # strategies are not even called once halted


def test_a_late_fill_of_a_cancelled_leg_is_flattened(tmp_path):
    """Real brokers can fill both legs of a stop/target pair inside one poll."""
    class Late(SimBroker):
        def __init__(self):
            super().__init__(latency_s=1, cost_bp=0)
            self.ghost = None

        def submit(self, o, qty, now):
            o.oco = None                                 # a real broker does not cancel the pair for us
            return super().submit(o, qty, now)

        def cancel(self, oid):
            o = self.open.get(oid)
            if o is not None and o.kind == "limit" and self.ghost is None:
                self.ghost = (o, self.qty[oid])          # pretend the cancel lost the race
            super().cancel(oid)

        def on_event(self, ev):
            out = super().on_event(ev)
            if self.ghost and isinstance(ev, Bar) and ev.sym == self.ghost[0].sym:
                o, q = self.ghost
                self.ghost = False
                out.append(self._fill(o, q, o.limit, ev.ts, "late"))
            return out

    s = Scripted([(t("10:00"), lambda: Order("AAA", "buy", ref_price=100.0, stop=99.0, target=105.0))])
    path = lambda i: 100.0 if i < 40 else 98.0  # noqa: E731
    e = engine([s], tmp_path, broker=Late()).run(minute_bars("AAA", "09:30", "11:00", path=path))
    assert any(x["kind"] == "late fill after cancel" for x in e.events)
    assert not e.positions                          # the accidental short was bought back
    assert [x["exit_reason"] for x in e.trades][-1] == "late fill after cancel"


# ------------------------------------------------------------------ mode independence
FORBIDDEN = {"mode", "paper", "live", "replay", "broker", "SimBroker", "AlpacaLabPaper", "SchwabLabLive",
             "os", "environ", "getenv", "account_number", "HALT"}


def test_strategy_code_cannot_see_the_mode():
    root = Path(__file__).resolve().parent.parent / "daytrade" / "strategies"
    for f in root.glob("*.py"):
        tree = ast.parse(f.read_text())
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | \
                {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)} | \
                {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))
                 for a in n.names}
        mods = {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        assert not (names & FORBIDDEN), (f.name, names & FORBIDDEN)
        assert all(m in ("", "base", "events", "__future__", "math", "pathlib", "gap_vwap_reclaim",
                                 "open_imbalance", "orb_in_play", "vwap_trend", "late_mover", "halt_resume")
                   or m.endswith(("events", "base")) for m in mods), (f.name, mods)


def test_plans_exist_for_every_strategy():
    for name, cls in REGISTRY.items():
        assert cls().plan_path().exists(), name


class InstantBroker(SimBroker):
    """A stand-in for a real broker: different fill behaviour, same interface."""
    def __init__(self):
        super().__init__(latency_s=0, cost_bp=3)


def gap_day_bars():
    """GAPX: prev close 10, opens 10.80 (+8%), fades to VWAP, reclaims, then runs to the target."""
    closes = ([10.80, 10.85, 10.90, 10.80, 10.70, 10.60, 10.55] + [10.52, 10.60, 10.75] +
              [10.80 + 0.03 * i for i in range(60)])
    out, prev = [], 10.80
    for i, c in enumerate(closes):
        s = t("09:30") + dt.timedelta(minutes=i)
        o = prev if i else 10.80
        out.append(Bar(s + dt.timedelta(minutes=1), "GAPX", o, max(o, c) + 0.02, min(o, c) - 0.02, c,
                       50_000 if i < 5 else 20_000, s))
        prev = c
    return out


def run_gap(broker, tmp_path):
    strat = GapVwapReclaim()
    seen = []
    orig = strat.on_bar

    def spy(ctx, b):
        out = orig(ctx, b)
        seen.extend((b.ts, o.sym, o.side, o.ref_price, o.stop, o.target) for o in out)
        return out

    strat.on_bar = spy
    info = {"GAPX": DayInfo("GAPX", 10.0, 20e6, 900_000)}
    e = engine([strat], tmp_path, broker=broker, day_info=info).run(gap_day_bars())
    return e, seen


def test_same_strategy_same_orders_under_different_brokers(tmp_path):
    e1, o1 = run_gap(SimBroker(latency_s=1, cost_bp=10), tmp_path)
    e2, o2 = run_gap(InstantBroker(), tmp_path)
    assert o1 and o1 == o2
    assert e1.trades[0]["entry_px"] != e2.trades[0]["entry_px"]   # fills differ, decisions do not


def test_gap_strategy_trades_the_reclaim_and_hits_the_target(tmp_path):
    e, orders = run_gap(SimBroker(latency_s=1, cost_bp=0), tmp_path)
    assert len(orders) == 1
    ts, sym, side, ref, stop, target = orders[0]
    assert ts >= t("09:36") and stop < ref < target
    assert e.trades[0]["exit_reason"] == "target" and e.trades[0]["r"] > 1.5


def test_gap_strategy_ignores_small_gaps_and_thin_premarket(tmp_path):
    strat = GapVwapReclaim()
    info = {"GAPX": DayInfo("GAPX", 10.6, 20e6, 900_000)}      # gap +1.9%
    e = engine([strat], tmp_path, day_info=info).run(gap_day_bars())
    assert not e.trades
    info = {"GAPX": DayInfo("GAPX", 10.0, 20e6, 100_000)}      # premarket 100k < 250k
    e = engine([GapVwapReclaim()], tmp_path, day_info=info).run(gap_day_bars())
    assert not e.trades


def test_open_imbalance_long_on_bid_heavy_open_and_exits_at_1005(tmp_path):
    evs = []
    for sec in range(0, 300):
        ts = t("09:30") + dt.timedelta(seconds=sec)
        evs.append(Quote(ts, "QQQ", 500.00, 500.01, 900, 100))
        if sec % 10 == 0:
            evs.append(Trade(ts, "QQQ", 500.01, 100))           # lifts the offer
    for sec in range(300, 2400, 5):
        ts = t("09:30") + dt.timedelta(seconds=sec)
        evs.append(Quote(ts, "QQQ", 500.10, 500.11, 500, 500))
    e = engine([OpenImbalance()], tmp_path, equity=25_000).run(evs)
    assert len(e.trades) == 1 and e.trades[0]["side"] == "long"
    assert e.trades[0]["exit_reason"] == "10:05 exit"
    assert t("10:05") <= dt.datetime.fromisoformat(e.trades[0]["exit_ts"]) < t("10:06")


# ------------------------------------------------------------------ fills
def test_limit_needs_trade_through_or_the_queue(tmp_path):
    b = SimBroker(latency_s=1)
    b.on_event(Quote(t("10:00"), "AAA", 99.99, 100.00, 100, 300))
    o = Order("AAA", "sell", "limit", limit=100.00, entry=False)
    b.submit(o, 10, t("10:00"))
    assert not b.on_event(Trade(t("10:00", 1), "AAA", 100.00, 200))      # 100 of 300 ahead left
    f = b.on_event(Trade(t("10:00", 2), "AAA", 100.00, 200))
    assert f and f[0].price == 100.00
    b.submit(o2 := Order("AAA", "sell", "limit", limit=101.00, entry=False), 10, t("10:01"))
    assert not b.on_event(bar("AAA", "10:01", 100, 101.00, 99.9, 100.5))  # touched, not through
    assert b.on_event(bar("AAA", "10:02", 100.5, 101.01, 100.4, 101))[0].order_id == o2.id


def test_stop_gap_through_and_same_bar_stop_first():
    b = SimBroker(latency_s=1, cost_bp=0)
    st_ = Order("AAA", "sell", "stop", stop_px=99.0, entry=False, oco="g")
    tg = Order("AAA", "sell", "limit", limit=101.0, entry=False, oco="g")
    b.submit(st_, 10, t("10:00")); b.submit(tg, 10, t("10:00"))
    f = b.on_event(bar("AAA", "10:00", 98.5, 101.5, 98.0, 100.0))       # opens below stop, hits both
    assert len(f) == 1 and f[0].order_id == st_.id and f[0].price == 98.5
    assert not b.open_orders()


def test_latency_settings_on_bars():
    for lat, want in ((0, 100.0), (1, 101.0), (60, 102.0)):
        b = SimBroker(latency_s=lat, cost_bp=0)
        o = Order("AAA", "buy", ref_price=100.0, stop=99.0)
        b.submit(o, 1, t("10:01"))
        fills = b.on_event(Clock(t("10:01")))
        for i, px in enumerate((101.0, 102.0, 103.0)):
            fills += b.on_event(bar("AAA", f"10:0{1 + i}", px, px, px, px))
        assert fills[0].price == want, lat


# ------------------------------------------------------------------ feeds and recorder
def test_rows_to_events_builds_regular_hours_bars():
    s = st()
    rows = [{"ts": t("09:29", 50), "sym": "QQQ", "bid": 1, "ask": 1.01, "last": 1.0, "volume": 5000,
             "trade_ms": 1},
            {"ts": t("09:30", 1), "sym": "QQQ", "bid": 1, "ask": 1.01, "last": 1.01, "volume": 5600,
             "trade_ms": 2},
            {"ts": t("09:30", 30), "sym": "QQQ", "bid": 1, "ask": 1.01, "last": 1.03, "volume": 5700,
             "trade_ms": 3},
            {"ts": t("09:31", 5), "sym": "QQQ", "bid": 1, "ask": 1.01, "last": 1.02, "volume": 5750,
             "trade_ms": 4}]
    evs = list(rows_to_events(rows, s))
    bars = [e for e in evs if isinstance(e, Bar)]
    assert bars[0].start == t("09:30") and bars[0].open == 1.01 and bars[0].high == 1.03
    assert bars[0].volume == 700                 # premarket volume is the baseline, not counted
    trades = [e for e in evs if isinstance(e, Trade)]
    assert [x.size for x in trades] == [600, 100, 50]
    assert all(e.ts >= s.open for e in evs)


def test_recording_merges_deltas_and_keeps_one_preopen_row(tmp_path):
    o = dt.datetime(2026, 10, 1, 13, 30, tzinfo=dt.timezone.utc)
    rec = Recording(DAY, o, o + dt.timedelta(hours=6, minutes=30), tmp_path)
    ms = lambda d: int(d.timestamp() * 1000)  # noqa: E731
    rec.on_message({"timestamp": ms(o - dt.timedelta(seconds=30)),
                    "content": [{"key": "QQQ", "BID_PRICE": 500.0, "ASK_PRICE": 500.01, "TOTAL_VOLUME": 10}]})
    rec.on_message({"timestamp": ms(o - dt.timedelta(seconds=5)),
                    "content": [{"key": "QQQ", "BID_SIZE": 300}]})
    rec.on_message({"timestamp": ms(o + dt.timedelta(seconds=1)),
                    "content": [{"key": "QQQ", "ASK_PRICE": 500.02}]})
    rec.on_message({"timestamp": ms(o + dt.timedelta(hours=7)), "content": [{"key": "QQQ", "BID_PRICE": 1}]})
    assert len(rec.buf) == 2 and rec.dropped_outside == 1
    pre, first = rec.buf
    assert pre[3] == 500.0 and pre[5] == 300 and first[4] == 500.02 and first[3] == 500.0
    rec.flush(); rec.write_meta(final=True)
    import pyarrow.parquet as pq
    tbl = pq.read_table(next((tmp_path / "l1" / "trade_date=2026-10-01").glob("*.parquet")))
    assert tbl.num_rows == 2
    assert json.loads((tmp_path / "meta" / "2026-10-01.json").read_text())["flagged"] is False


def test_recording_flags_a_gap_in_session(tmp_path):
    o = dt.datetime(2026, 10, 1, 13, 30, tzinfo=dt.timezone.utc)
    rec = Recording(DAY, o, o + dt.timedelta(hours=6, minutes=30), tmp_path)
    s = (o + dt.timedelta(hours=1)).timestamp()
    rec.gap(s, s + 12, "reconnect")
    rec.gap(o.timestamp() - 100, o.timestamp() - 50, "before open")      # ignored
    rec.write_meta()
    m = json.loads((tmp_path / "meta" / "2026-10-01.json").read_text())
    assert m["flagged"] and len(m["gaps"]) == 1


def test_select_gappers_ranks_by_premarket_volume_and_caps():
    q = {f"S{i}": {"quote": {"lastPrice": 20 * 1.05, "closePrice": 20, "totalVolume": 1000 * i}}
         for i in range(1, 15)}
    q["CHEAP"] = {"quote": {"lastPrice": 3.3, "closePrice": 3, "totalVolume": 10**9}}
    q["FLAT"] = {"quote": {"lastPrice": 20.2, "closePrice": 20, "totalVolume": 10**9}}
    q["QQQ"] = {"quote": {"lastPrice": 600, "closePrice": 500, "totalVolume": 10**9}}
    picks = select_gappers(q, cap=10)
    assert len(picks) == 10 and picks[0]["sym"] == "S14"
    assert not {"CHEAP", "FLAT", "QQQ"} & {p["sym"] for p in picks}


def test_recorder_writes_only_its_own_token_copy(tmp_path, monkeypatch):
    import swingtrader.daily.brokers as b
    live = tmp_path / "schwab-token.json"
    live.write_text(json.dumps({"creation_timestamp": 123, "token": {}}))
    before = live.read_bytes()
    monkeypatch.setattr(b, "schwab_token_path", lambda: live)
    dest = tmp_path / "daytrade" / "schwab-token.json"
    assert token_copy(dest) == dest and dest.read_bytes() == before
    dest.write_text(json.dumps({"creation_timestamp": 123, "token": {"refreshed": True}}))
    token_copy(dest)                             # same login: the refreshed copy is kept
    assert "refreshed" in dest.read_text() and live.read_bytes() == before


# ------------------------------------------------------------------ review
def test_review_drops_after_40_bad_paper_trades():
    bad = [{"net_bp": -3.0} for _ in range(40)]
    assert decide("gap_vwap_reclaim", "paper", bad, 20.0)[0] == "drop"
    assert decide("gap_vwap_reclaim", "paper", bad[:39], 20.0)[0] == "continue"
    good = [{"net_bp": 15.0, "entry_drift_bp": 30.0} for _ in range(40)]
    assert decide("gap_vwap_reclaim", "paper", good, 20.0)[0] == "drop"           # drift > edge
    ok = [{"net_bp": 15.0, "entry_drift_bp": 2.0} for _ in range(40)]
    assert decide("gap_vwap_reclaim", "paper", ok, 20.0)[0] == "continue"


# ------------------------------------------------------------------ ORB on Stocks in Play
def orb_bars(sym, o, up=True, after=None):
    """Five opening minutes trending one way, then a path."""
    out, px = [], o
    for i in range(5):
        nxt = px + (0.10 if up else -0.10)
        s = t("09:30") + dt.timedelta(minutes=i)
        out.append(Bar(s + dt.timedelta(minutes=1), sym, px, max(px, nxt), min(px, nxt), nxt, 200_000, s))
        px = nxt
    for i, c in enumerate(after or []):
        s = t("09:35") + dt.timedelta(minutes=i)
        out.append(Bar(s + dt.timedelta(minutes=1), sym, px, max(px, c) + 0.01, min(px, c) - 0.01, c, 50_000, s))
        px = c
    return out


def test_orb_long_breakout_stops_and_short_side_respects_long_only(tmp_path):
    from daytrade.strategies.orb_in_play import OrbInPlay
    info = {s: DayInfo(s, 20.0, 0, 0, atr14=1.0, avg_volume14=2e6, or_volume_avg14=200_000) for s in ("UP", "DN")}
    up = orb_bars("UP", 20.0, True, [20.6, 20.4, 20.9, 21.5] + [21.5] * 30)      # breaks 20.50, runs
    dn = orb_bars("DN", 20.0, False, [19.4, 19.6, 19.3, 18.9] + [18.9] * 30)
    bars = sorted(up + dn, key=lambda b: (b.ts, b.sym))
    e = engine([OrbInPlay()], tmp_path, equity=1e6, limits=Limits(max_positions=99), day_info=info).run(bars)
    sides = {x["sym"]: x["side"] for x in e.trades}
    assert sides == {"UP": "long", "DN": "short"}
    up_t = next(x for x in e.trades if x["sym"] == "UP")
    assert up_t["stop"] == pytest.approx(20.50 - 0.10) and up_t["entry_px"] == pytest.approx(20.50)
    e2 = engine([OrbInPlay(long_only=True)], tmp_path, equity=1e6, limits=Limits(max_positions=99),
                day_info=info).run(bars)
    assert {x["sym"] for x in e2.trades} == {"UP"}


def test_orb_needs_relative_volume(tmp_path):
    from daytrade.strategies.orb_in_play import OrbInPlay
    info = {"UP": DayInfo("UP", 20.0, 0, 0, atr14=1.0, avg_volume14=2e6, or_volume_avg14=5_000_000)}
    e = engine([OrbInPlay()], tmp_path, day_info=info).run(orb_bars("UP", 20.0, True, [20.6] * 10))
    assert not e.trades


def test_pending_entries_hold_slots(tmp_path):
    """Resting stop entries count toward max positions, so 20 orders cannot become 20 positions."""
    from daytrade.strategies.orb_in_play import OrbInPlay
    syms = [f"S{i}" for i in range(6)]
    info = {s: DayInfo(s, 20.0, 0, 0, atr14=1.0, avg_volume14=2e6, or_volume_avg14=100_000) for s in syms}
    bars = sorted([b for s in syms for b in orb_bars(s, 20.0, True, [20.6] + [20.7] * 20)],
                  key=lambda b: (b.ts, b.sym))
    e = engine([OrbInPlay()], tmp_path, equity=100_000, day_info=info).run(bars)
    assert len(e.trades) == 3
    assert sum("max 3 positions" in x["detail"] for x in e.events) == 3


# ------------------------------------------------------------------ VWAP trend
def test_vwap_trend_reverses_on_a_cross_and_is_flat_at_the_close(tmp_path):
    from daytrade.strategies.vwap_trend import VwapTrend
    path = lambda i: 100 + 0.05 * i if i < 60 else 103 - 0.05 * (i - 60)  # noqa: E731
    e = engine([VwapTrend()], tmp_path, equity=100_000).run(minute_bars("QQQ", "09:30", "16:00", path=path))
    sides = [x["side"] for x in e.trades]
    assert sides[:2] == ["long", "short"] and not e.positions
    assert e.trades[0]["exit_reason"] == "VWAP cross" and e.trades[-1]["exit_reason"] == "flat by close"
    assert not [x for x in e.events if x["kind"] == "rejected" and "against" in x["detail"]]


def test_vwap_trend_trades_tqqq_on_qqq_signal(tmp_path):
    from daytrade.strategies.vwap_trend import VwapTrend
    path = lambda i: 100 + 0.05 * i  # noqa: E731
    bars = sorted(minute_bars("QQQ", "09:30", "11:00", path=path) + minute_bars("TQQQ", "09:30", "11:00", 50.0),
                  key=lambda b: (b.ts, b.sym))
    e = engine([VwapTrend(trade="TQQQ")], tmp_path, equity=100_000).run(bars)
    assert {x["sym"] for x in e.trades} == {"TQQQ"} and e.trades[0]["side"] == "long"


def test_late_mover_buys_big_up_movers_at_1500_and_exits_1555(tmp_path):
    from daytrade.strategies.late_mover import LateMover
    info = {"UPX": DayInfo("UPX", 10.0), "FLAT": DayInfo("FLAT", 10.0)}
    bars = sorted(minute_bars("UPX", "09:30", "16:00", 13.0) + minute_bars("FLAT", "09:30", "16:00", 10.5),
                  key=lambda b: (b.ts, b.sym))
    bars = [Bar(b.ts, b.sym, b.open, b.high, b.low, b.close, 1_000_000, b.start) for b in bars]
    e = engine([LateMover()], tmp_path, equity=100_000, day_info=info).run(bars)
    assert [x["sym"] for x in e.trades] == ["UPX"]
    assert dt.datetime.fromisoformat(e.trades[0]["entry_ts"]) == t("15:00")
    assert e.trades[0]["exit_reason"] == "flat by close"


def test_halt_resume_buys_the_reopening_after_a_halt_up(tmp_path):
    from daytrade.strategies.halt_resume import HaltResume
    path = lambda i: 20.0 if i < 30 else 20.0 * (1 + 0.012 * (i - 29))  # noqa: E731  (+6% in 5 min by 10:05)
    pre = minute_bars("HLT", "09:30", "10:05", path=path)
    post = minute_bars("HLT", "10:10", "11:00", 22.0)                     # silent 10:05-10:09: halted
    clocks = [Clock(t("09:30") + dt.timedelta(minutes=m)) for m in range(0, 91)]
    evs = sorted(pre + post + clocks, key=lambda e: (e.ts, 0 if isinstance(e, Bar) else 1))
    e = engine([HaltResume("up")], tmp_path, equity=100_000).run(evs)
    assert len(e.trades) == 1
    tr = e.trades[0]
    assert dt.datetime.fromisoformat(tr["entry_ts"]) == t("10:10") and tr["entry_px"] == pytest.approx(22.0)
    assert tr["exit_reason"] == "30-minute exit"
    e2 = engine([HaltResume("down")], tmp_path, equity=100_000).run(evs)
    assert not e2.trades


def test_a_stop_already_through_the_market_fills_at_the_market_not_the_stop():
    """Regression (Lab-AY2): a stop placed above a long's entry must not fill at the stop price."""
    b = SimBroker(latency_s=1, cost_bp=0)
    o = Order("AAA", "sell", "stop", stop_px=22.5, entry=False, ref_price=2.17)
    o.ts = t("10:00", 30)
    b.submit(o, 10, t("10:00", 30))
    f = b.on_event(bar("AAA", "10:00", 2.17, 2.30, 2.10, 2.20))
    assert f and f[0].price == pytest.approx(2.17)


def test_stop_pct_is_measured_from_the_fill(tmp_path):
    """The plan's 10% catastrophe stop sits 10% below the actual fill, not below the decision price."""
    s = Scripted([(t("10:00"), lambda: Order("AAA", "buy", ref_price=25.0, stop=22.5, stop_pct=0.10))])
    path = lambda i: 25.0 if i < 31 else 2.0  # noqa: E731   (fills after a collapse)
    e = engine([s], tmp_path, equity=100_000).run(minute_bars("AAA", "09:30", "11:00", path=path))
    assert e.trades and e.trades[0]["stop"] == pytest.approx(round(e.trades[0]["entry_px"] * 0.9, 2))


def test_halt_short_sells_the_reopening_with_a_stop_above(tmp_path):
    from daytrade.strategies.halt_resume import HaltResume
    path = lambda i: 20.0 if i < 30 else 20.0 * (1 + 0.012 * (i - 29))  # noqa: E731
    pre = minute_bars("HLT", "09:30", "10:05", path=path)
    post = minute_bars("HLT", "10:10", "11:00", 22.0)
    clocks = [Clock(t("09:30") + dt.timedelta(minutes=m)) for m in range(0, 91)]
    evs = sorted(pre + post + clocks, key=lambda e: (e.ts, 0 if isinstance(e, Bar) else 1))
    e = engine([HaltResume("up", side="sell")], tmp_path, equity=100_000).run(evs)
    tr = e.trades[0]
    assert tr["side"] == "short" and tr["stop"] == pytest.approx(round(tr["entry_px"] * 1.1, 2))
    assert tr["exit_reason"] == "30-minute exit"
    e2 = engine([HaltResume("up", side="sell")], tmp_path, equity=1_500).run(evs)   # cash: no shorts
    assert not e2.trades


def test_momentum_shadow_picks_rank_12_1_inside_the_liquid_universe():
    import numpy as np
    import pandas as pd
    from daytrade.momentum import picks
    months = [f"2025-{m:02d}" for m in range(1, 13)] + ["2026-01", "2026-02"]
    syms = ["A", "B", "C", "D", "THIN", "CHEAP"]
    C = pd.DataFrame(100.0, index=months, columns=syms)
    C.loc[months[1]:months[-2], "A"] = np.linspace(100, 200, 12)      # strongest 12-1
    C.loc[months[1]:months[-2], "B"] = np.linspace(100, 150, 12)
    C.loc[months[1]:months[-2], "THIN"] = np.linspace(100, 400, 12)    # strongest, but illiquid
    C.loc[months[1]:months[-2], "CHEAP"] = np.linspace(100, 300, 12)
    C.loc[months[-1], "A"] = 50                                        # last month is skipped (12-1)
    V = pd.DataFrame(1e6, index=months, columns=syms); V["THIN"] = 1.0
    RAW = C.copy(); RAW["CHEAP"] = 3.0                                 # under $5 at the decision
    p, u = picks(C, V, RAW, months[-1], top=2, univ=4)
    assert "THIN" not in u and "CHEAP" not in u
    assert p == ["A", "B"]


def test_momentum_vol_weight_is_reported_after_six_scored_months():
    from daytrade.momentum import vol_weight
    calm = [{"realised": {"picks": 0.01 + 0.001 * (i % 2), "universe": 0.0}} for i in range(6)]
    wild = [{"realised": {"picks": 0.15 * (-1) ** i, "universe": 0.0}} for i in range(6)]
    assert vol_weight(calm[:5]) is None
    assert vol_weight(calm) == 1.0 and vol_weight(wild) < 0.3


# ------------------------------------------------------------------ paper loop, end to end
class FakeAlpacaTrading:
    """Fills a market order at the price the test sets; limits/stops stay open."""
    def __init__(self):
        self.orders, self.px = {}, 100.0

    def submit_order(self, req):
        from types import SimpleNamespace
        oid = f"o{len(self.orders) + 1}"
        kind = type(req).__name__
        self.orders[oid] = SimpleNamespace(id=oid, req=req, kind=kind, status="new", filled_qty=0, filled_avg_price=None,
                                           filled_at=None)
        if kind == "MarketOrderRequest":
            o = self.orders[oid]
            o.status, o.filled_qty, o.filled_avg_price = "filled", req.qty, self.px
        return self.orders[oid]

    def get_order_by_id(self, oid):
        return self.orders[oid]

    def cancel_order_by_id(self, oid):
        self.orders[oid].status = "canceled"

    def cancel_orders(self):
        for o in self.orders.values():
            if o.status == "new":
                o.status = "canceled"

    def get_account(self):
        from types import SimpleNamespace
        return SimpleNamespace(equity="100000")


def test_paper_session_end_to_end_with_shadow_fills_and_flat_by_close(tmp_path):
    from daytrade.brokers import AlpacaLabPaper
    from daytrade.runner import run_session
    s = st()
    rows = []
    for k in range(0, 6 * 3600 + 1800, 5):          # a quote every 5s, 09:30 -> 16:00
        ts = (s.open + dt.timedelta(seconds=k)).astimezone(dt.timezone.utc)
        px = 100 + 0.001 * k
        rows.append({"ts": ts, "sym": "QQQ", "bid": px - 0.01, "ask": px + 0.01, "bid_size": 100, "ask_size": 100,
                     "last": px, "last_size": 10, "volume": 1000 + k, "trade_ms": k})
    fake = FakeAlpacaTrading()
    broker = AlpacaLabPaper(poll_s=0, trading=fake)
    strat = Scripted([(t("10:00"), lambda: Order("QQQ", "buy", ref_price=103.6, stop=100.0))])
    eng = run_session("paper", s, broker, 25_000, "margin", {}, [strat], rows, journal_root=tmp_path,
                      halt_path=tmp_path / "HALT")
    assert len(eng.trades) == 1 and eng.trades[0]["exit_reason"] == "flat by close"
    j = [json.loads(x) for x in (tmp_path / "journal-paper.jsonl").read_text().splitlines()]
    assert j[0]["replay_entry_px"] is not None and "entry_drift_bp" in j[0]       # the drift report has data
    kinds = {o.kind for o in fake.orders.values()}
    assert "StopOrderRequest" in kinds and "MarketOrderRequest" in kinds           # the stop rested at the broker
    assert not eng.positions


def test_paper_session_halts_on_the_halt_file(tmp_path):
    from daytrade.brokers import AlpacaLabPaper
    from daytrade.runner import run_session
    s = st()
    (tmp_path / "HALT").write_text("x")
    rows = [{"ts": (s.open + dt.timedelta(seconds=k)).astimezone(dt.timezone.utc), "sym": "QQQ", "bid": 99.99,
             "ask": 100.01, "bid_size": 1, "ask_size": 1, "last": 100, "last_size": 1, "volume": k, "trade_ms": k}
            for k in range(0, 600, 5)]
    fake = FakeAlpacaTrading()
    strat = Scripted([(t("09:31"), lambda: Order("QQQ", "buy", ref_price=100.0, stop=99.0))])
    eng = run_session("paper", s, AlpacaLabPaper(poll_s=0, trading=fake), 25_000, "margin", {}, [strat], rows,
                      journal_root=tmp_path, halt_path=tmp_path / "HALT")
    assert eng.halted and not eng.trades and not fake.orders


# ------------------------------------------------------------------ live Schwab broker (fake client)
class FakeSchwabLab:
    def __init__(self):
        self.placed = []

    class _R:
        def __init__(self, data=None, status=200, headers=None):
            self._d, self.status_code, self.headers, self.text = data, status, headers or {}, ""

        def json(self):
            return self._d

        def raise_for_status(self):
            pass

    def get_account_numbers(self):
        return self._R([{"accountNumber": "11112222", "hashValue": "LIVEHASH"},
                        {"accountNumber": "99994444", "hashValue": "LABHASH"}])

    def get_account(self, h, fields=None):
        return self._R({"securitiesAccount": {"type": "CASH", "accountNumber": "99994444",
                                              "currentBalances": {"liquidationValue": 480.0, "cashBalance": 480.0}}})

    def place_order(self, h, order):
        self.placed.append((h, order))
        return self._R(status=201, headers={"Location": f"/orders/{len(self.placed)}"})

    def get_order(self, oid, h):
        return self._R({"status": "FILLED", "orderActivityCollection": [
            {"executionLegs": [{"quantity": 2, "price": 101.0, "time": "2026-10-01T14:00:00Z"}]}]})

    def cancel_order(self, oid, h):
        return self._R()


def _live_env(monkeypatch, tmp_path, lab="4444", main="2222"):
    from daytrade import brokers
    monkeypatch.setenv("SCHWAB_DAYTRADE_ACCOUNT_NUMBER", lab)
    monkeypatch.setenv("SCHWAB_ACCOUNT_NUMBER", main)
    monkeypatch.setenv("SCHWAB_ROTH_ACCOUNT_NUMBER", "")
    monkeypatch.setenv("SCHWAB_LEAP_ACCOUNT_NUMBER", "")
    monkeypatch.setenv("DAYTRADE_LIVE", "on")
    monkeypatch.setattr(brokers, "LIVE_APPROVAL", tmp_path / "LIVE_APPROVED")
    (tmp_path / "LIVE_APPROVED").write_text("approved for test")


def test_live_broker_trades_only_the_lab_account(monkeypatch, tmp_path):
    from daytrade.brokers import SchwabLabLive
    _live_env(monkeypatch, tmp_path)
    c = FakeSchwabLab()
    b = SchwabLabLive(500, client=c, poll_s=0)
    assert b.a.hash == "LABHASH" and b.equity() == 480.0
    b.submit(Order("QQQ", "buy", ref_price=100.0, stop=99.0), 2, t("10:00"))
    b.submit(Order("QQQ", "sell", "limit", limit=105.0, entry=False), 2, t("10:00"))
    b.submit(Order("QQQ", "sell", "stop", stop_px=99.0, entry=False), 2, t("10:00"))
    assert {h for h, _ in c.placed} == {"LABHASH"}
    kinds = [o["orderType"] for _, o in c.placed]
    assert kinds == ["MARKET", "LIMIT", "STOP"]
    assert c.placed[2][1]["stopPrice"] in ("99.00", "99.0", 99.0)
    fills = b.on_event(Clock(t("10:01")))
    assert fills and fills[0].price == 101.0 and fills[0].qty == 2


def test_live_broker_refuses_the_live_books_account_and_short_entries(monkeypatch, tmp_path):
    from daytrade.brokers import SchwabLabLive
    _live_env(monkeypatch, tmp_path, lab="99994444", main="4444")      # main's last 4 = the lab's account
    with pytest.raises(guard.AccountGuardError):
        SchwabLabLive(500, client=FakeSchwabLab())
    _live_env(monkeypatch, tmp_path)
    b = SchwabLabLive(500, client=FakeSchwabLab(), poll_s=0)
    with pytest.raises(guard.AccountGuardError, match="long-only"):
        b.submit(Order("QQQ", "sell", ref_price=100.0, stop=101.0), 1, t("10:00"))


def test_industry_momentum_shadow_ranks_the_fixed_list():
    import numpy as np
    import pandas as pd
    from daytrade.momentum import industry_picks
    months = [f"2025-{m:02d}" for m in range(1, 13)] + ["2026-01", "2026-02"]
    C = pd.DataFrame(100.0, index=months, columns=["XBI", "SMH", "KRE", "GDX", "NOTALIST"])
    C.loc[months[1]:months[-2], "SMH"] = np.linspace(100, 180, 12)
    C.loc[months[1]:months[-2], "GDX"] = np.linspace(100, 140, 12)
    C.loc[months[1]:months[-2], "NOTALIST"] = np.linspace(100, 900, 12)
    assert industry_picks(C, months[-1], top=2) == ["SMH", "GDX"]


def test_gapper_sweep_skips_corporate_actions():
    from daytrade.recorder import looks_like_corporate_action, select_gappers
    assert looks_like_corporate_action(14.58 / 77.65)          # CTVA 2026-10-01 (-81%)
    assert looks_like_corporate_action(0.5) and looks_like_corporate_action(10.2)
    assert not looks_like_corporate_action(1.06) and not looks_like_corporate_action(0.92)
    q = {"CTVA": {"quote": {"lastPrice": 14.58, "closePrice": 77.65, "totalVolume": 3_313_483}},
         "REAL": {"quote": {"lastPrice": 21.0, "closePrice": 20.0, "totalVolume": 500_000}}}
    assert [g["sym"] for g in select_gappers(q)] == ["REAL"]
