import datetime as dt
import json
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from swingtrader.daily import cef_rv_live as C

ET = ZoneInfo("America/New_York")
TODAY = dt.date(2026, 10, 19)                  # Mon; first session after the Fri 10-16 signal week
NOW = dt.datetime(2026, 10, 19, 9, 5, tzinfo=ET)
SIG = "2026-10-16"                             # Friday signal week -> execute Mon 10-19
OLD_SIG = "2026-10-09"                         # Friday -> executed Mon 10-12 (missed by TODAY)


class Resp:
    def __init__(self, d):
        self.d = d

    def json(self):
        return self.d


class FakeClient:
    def __init__(self, quotes, orders=None):
        self.quotes, self.orders = quotes, orders or {}

    def get_quotes(self, syms):
        return Resp({s: {"quote": {"lastPrice": self.quotes[s]}} for s in syms if s in self.quotes})

    def get_order(self, oid, h):
        return Resp(self.orders[int(oid)])


class FakeAd:
    hash = "HASH"

    def __init__(self, quotes, settled=2000.0, equity=3000.0, positions=None, orders=None):
        self.c = FakeClient(quotes, orders)
        self.settled, self.equity, self.pos, self.submitted = settled, equity, positions or {}, []

    def account(self):
        return SimpleNamespace(equity=self.equity, cash=self.settled + 500.0, settled_cash=self.settled)

    def positions(self):
        return {s: SimpleNamespace(qty=q) for s, q in self.pos.items()}

    def submit(self, sym, side, tif, coid, qty=None, **kw):
        self.submitted.append((sym, side, tif, qty))
        return str(3000 + len(self.submitted))


def crosses(syms, start, end, H):
    days = [(dt.date(2026, 10, 1) + dt.timedelta(days=i)).isoformat() for i in range(25)]
    return {s: {d: (10.0, 5000, 10.1, 500) for d in days} for s in syms}


def sig(sym, signal=SIG, exit_signal=None, **kw):
    return dict(sym=sym, signal=signal, exit_signal=exit_signal, status="pending", **kw)


def signals(tmp_path, *rows):
    (tmp_path / C.SIGNALS_NAME).write_text("\n".join(json.dumps(r) for r in rows) + "\n")


def panel(tmp_path, **disc):
    """disc: sym -> discount at the signal week; the trailing median is 0 for every fund."""
    weeks = [(dt.date(2025, 10, 17) + dt.timedelta(days=7 * i)).isoformat() for i in range(53)]
    p = {s: [[w, 0.0] for w in weeks[:-1]] + [[weeks[-1], d]] for s, d in disc.items()}
    assert weeks[-1] == SIG
    (tmp_path / C.PANEL_NAME).write_text(json.dumps(p))


def run(mode, tmp_path, ad, today=TODAY, now=NOW):
    return C.run(mode, tmp_path, tmp_path, log=lambda *_: None, today=today, now=now, ad=ad, crosses_fn=crosses, H={})


def rows(tmp_path):
    return [json.loads(x) for x in (tmp_path / C.LOG_NAME).read_text().splitlines()]


def test_off_mode_is_a_no_op(tmp_path):
    out = C.run("off", tmp_path, tmp_path, log=lambda *_: None, today=TODAY, now=NOW, ad=None)
    assert out["skipped"] == "off" and not (tmp_path / C.LOG_NAME).exists()


def test_entries_are_forward_signals_executing_today_only():
    held = {"HELD": dict(signal_week=SIG, qty=10)}
    rs = [sig("A"), sig("HELD"), sig("B", signal=OLD_SIG), sig("C", signal="2026-10-02"),   # C = backfill (< FORWARD_FROM)
          sig("D", exit_signal="2026-10-16"), sig("E", signal="2026-10-23")]                 # D exited; E future
    buy, missed = C.entries(rs, TODAY, held)
    assert [r["sym"] for r in buy] == ["A"] and [r["sym"] for r in missed] == ["B"]
    assert C.exec_session("2026-10-09") == dt.date(2026, 10, 12)                            # Fri signal -> Monday


def test_exits_need_a_matching_held_signal_week():
    held = {"X": dict(signal_week=OLD_SIG, qty=10), "Y": dict(signal_week="2026-09-25", qty=5)}
    rs = [sig("X", signal=OLD_SIG, exit_signal="2026-10-16"), sig("Y", signal=OLD_SIG, exit_signal="2026-10-16"),
          sig("X", signal="2026-10-16", exit_signal="2026-10-23")]
    ex = C.exits(rs, TODAY, held)
    assert [(r["sym"], r["exit_session"]) for r in ex] == [("X", "2026-10-19")]


def test_slots_and_sizing_deepest_discount_first():
    assert C.slot_usd(2300) == 500 and C.slot_usd(10_000) == 1000 and C.slot_usd(25_000) == 1000 and C.slot_usd(7000) == 700
    assert C.max_positions(2300) == 2 and C.max_positions(10_000) == 5 and C.max_positions(25_000) == 12
    pan = {s: [["2026-10-09", 0.0], [SIG, d]] for s, d in {"SHALLOW": -0.05, "DEEP": -0.20, "MID": -0.10}.items()}
    cands = [sig("SHALLOW"), sig("DEEP"), sig("MID")]
    last = {"SHALLOW": 10.0, "DEEP": 10.0, "MID": 10.0}
    out = C.size(cands, last, pan, settled=5000, equity=10_000, n_held=0)
    assert [(o["sym"], o["qty"], o["usd"]) for o in out] == [("DEEP", 100, 1000.0), ("MID", 100, 1000.0), ("SHALLOW", 100, 1000.0)]
    out = C.size(cands, last, pan, settled=1500, equity=10_000, n_held=0)          # settled binds: 1000 + 500
    assert [(o["sym"], o["qty"]) for o in out] == [("DEEP", 100), ("MID", 50)]
    out = C.size(cands, last, pan, settled=5000, equity=10_000, n_held=4)          # room: 5 - 4 = 1 position
    assert [o["sym"] for o in out] == ["DEEP"]
    assert C.size(cands, {"DEEP": 2000.0}, pan, settled=5000, equity=10_000, n_held=0) == []   # 1 share > slot


def test_pref_ex_reservation_reduces_the_budget_today_only(tmp_path):
    signals(tmp_path, sig("A"), sig("B"))
    panel(tmp_path, A=-0.2, B=-0.1)
    (tmp_path / C.RESERVED_NAME).write_text(json.dumps({"date": TODAY.isoformat(), "usd": 1200.0}))
    ad = FakeAd({"A": 10.0, "B": 10.0}, settled=2000, equity=10_000)
    out = run("dry", tmp_path, ad)
    buys = [r for r in rows(tmp_path) if r["cmd"] == "buy"]
    assert out["bought"] == ["A"] and buys[0]["qty"] == 80                          # $2000 - $1200 = $800 -> 80 shares
    (tmp_path / C.RESERVED_NAME).write_text(json.dumps({"date": "2026-10-16", "usd": 1200.0}))   # stale: ignored
    (tmp_path / C.STATE_NAME).unlink()
    ad = FakeAd({"A": 10.0, "B": 10.0}, settled=2000, equity=10_000)
    out = run("dry", tmp_path, ad)
    assert out["bought"] == ["A", "B"]


def test_dry_run_logs_sizes_and_holdings_value_but_places_nothing(tmp_path):
    signals(tmp_path, sig("A"), sig("B"), sig("OLD", signal=OLD_SIG))
    panel(tmp_path, A=-0.2, B=-0.1, OLD=-0.3)
    ad = FakeAd({"A": 10.0, "B": 10.0}, settled=2000, equity=3000)   # slot 500, max 3 positions, settled 2000
    out = run("dry", tmp_path, ad)
    assert ad.submitted == [] and out["bought"] == ["A", "B"] and out["missed"] == ["OLD"]
    rs = rows(tmp_path)
    buys = [r for r in rs if r["cmd"] == "buy"]
    assert all(r["dry_run"] for r in buys) and [r["qty"] for r in buys] == [50, 50]
    assert any(r["cmd"] == "missed" and r["sym"] == "OLD" and r["session"] == "2026-10-12" for r in rs)
    st = json.loads((tmp_path / C.STATE_NAME).read_text())
    assert set(st["open"]) == {"A", "B"} and st["open"]["A"]["signal_week"] == SIG
    held = json.loads((tmp_path / C.HELD_NAME).read_text())
    assert held["usd"] == 1000.0 and held["n"] == 2 and out["held_usd"] == 1000.0
    run("dry", tmp_path, ad)                                           # second run: no re-buy, one missed row only
    assert sum(1 for r in rows(tmp_path) if r["cmd"] == "missed") == 1 and len([r for r in rows(tmp_path) if r["cmd"] == "buy"]) == 2


def test_live_submits_pre_open_market_buys(tmp_path):
    signals(tmp_path, sig("A"))
    panel(tmp_path, A=-0.2)
    ad = FakeAd({"A": 10.0}, settled=2000, equity=3000)
    out = run("live", tmp_path, ad)
    assert ad.submitted == [("A", "buy", "opg", 50)] and out["bought"] == ["A"]
    assert [r for r in rows(tmp_path) if r["cmd"] == "buy"][0]["order_id"] == "3001"


def test_exit_sells_at_most_what_is_held_and_never_shorts(tmp_path):
    (tmp_path / C.STATE_NAME).write_text(json.dumps({"open": {
        "X": dict(qty=50, entry_px=10.0, entry_date="2026-10-12", signal_week=OLD_SIG),
        "GONE": dict(qty=20, entry_px=10.0, entry_date="2026-10-12", signal_week=OLD_SIG),
        "KEEP": dict(qty=20, entry_px=10.0, entry_date="2026-10-12", signal_week=OLD_SIG)}}))
    signals(tmp_path, sig("X", signal=OLD_SIG, exit_signal="2026-10-16"), sig("GONE", signal=OLD_SIG, exit_signal="2026-10-16"),
            sig("KEEP", signal=OLD_SIG, exit_signal=None))
    ad = FakeAd({"KEEP": 11.0}, positions={"X": 30.0})               # holds fewer than recorded: sell 30, never 50
    out = run("live", tmp_path, ad)
    assert ad.submitted == [("X", "sell", "opg", 30)] and out["sold"] == ["X"]
    st = json.loads((tmp_path / C.STATE_NAME).read_text())
    assert set(st["open"]) == {"KEEP"}
    assert any(r["cmd"] == "sell-skip" and r["sym"] == "GONE" for r in rows(tmp_path))
    assert out["held_usd"] == 220.0                                   # KEEP marked at the quote


def test_no_orders_outside_the_pre_open_window_or_on_a_non_session(tmp_path):
    signals(tmp_path, sig("A"))
    panel(tmp_path, A=-0.2)
    ad = FakeAd({"A": 10.0})
    run("live", tmp_path, ad, now=dt.datetime(2026, 10, 19, 9, 29, tzinfo=ET))
    run("live", tmp_path, ad, now=dt.datetime(2026, 10, 19, 7, 59, tzinfo=ET))
    run("live", tmp_path, ad, today=dt.date(2026, 10, 17), now=dt.datetime(2026, 10, 17, 9, 5, tzinfo=ET))   # Saturday
    assert ad.submitted == []


def test_score_compares_yesterdays_fills_to_the_opening_cross(tmp_path):
    (tmp_path / C.LOG_NAME).write_text(json.dumps(dict(ts="2026-10-16T09:05:00-04:00", mode="live", cmd="buy", sym="A",
                                                       qty=50, order_id="3001")) + "\n")
    order = {"orderActivityCollection": [{"executionLegs": [{"price": 10.02, "quantity": 50, "time": "2026-10-16T13:30:01Z"}]}]}
    ad = FakeAd({}, orders={3001: order})
    out = run("live", tmp_path, ad)
    sc = [r for r in rows(tmp_path) if r["cmd"] == "score"]
    assert out["scored"] == 1 and len(sc) == 1 and sc[0]["diff_bp"] == 20.0 and sc[0]["open_cross"] == 10.0
    run("live", tmp_path, ad)                                          # no re-score
    assert sum(1 for r in rows(tmp_path) if r["cmd"] == "score") == 1
    assert "buy +20.0bp" in C.line(rows(tmp_path)) and C.line(rows(tmp_path)).startswith("0/30")


def test_executor_roth_night_cash_subtracts_fresh_cef_holdings(tmp_path):
    import json
    from swingtrader.config import Config
    from swingtrader.daily import executor as E
    from test_daily import FakeBroker
    ex = E.DailyExecutor(Config.load(), account="roth", broker=FakeBroker(), state_dir=tmp_path, log_dir=tmp_path)
    assert ex._cef_rv_held("2026-10-14") == 0.0
    (tmp_path / "cef-rv-held.json").write_text(json.dumps({"date": "2026-10-13", "usd": 1980.0, "n": 2}))
    assert ex._cef_rv_held("2026-10-14") == 1980.0                       # yesterday's file: fresh
    assert ex._cef_rv_held("2026-10-25") == 0.0                          # > 7 days: stale, ignored
    assert ex._cef_rv_held("2026-10-12") == 0.0                          # dated in the future: ignored
    ex.cash_account = False
    assert ex._cef_rv_held("2026-10-14") == 0.0                          # taxable book: never
