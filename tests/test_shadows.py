"""Research-program shadows (addenda 31/33/38): FOMC-eve filler, Roth cash
log, Roth A2, lever gate G1, wash guard G4s. All log-only. No network."""
import datetime as dt
import json
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest

from swingtrader.config import Config
from swingtrader.daily import events as ev
from swingtrader.daily import signals as sg
from swingtrader.daily.book import DailyBook
from swingtrader.daily.executor import DailyExecutor

ET = ZoneInfo("America/New_York")


# ------------------------------------------------------------ config
def test_new_shadow_keys_default_to_shadow_and_load_without_warnings(recwarn):
    cfg = Config.load()
    d = cfg.daily
    assert (d.fomc_filler_mode, d.roth_night_cash_log, d.lever_g1_log, d.wash_guard_mode) == \
        ("shadow",) * 4
    assert not [w for w in recwarn if "unknown key" in str(w.message)]


# ------------------------------------------------------------ F3 calendar
def test_fomc_calendar_lookup():
    ds = ev.fomc_dates()
    assert all(d.weekday() < 5 for d in ds) and ds == sorted(ds)
    assert dt.date(2026, 10, 28) in ds and dt.date(2027, 12, 8) in ds
    assert ev.is_fomc_eve(dt.date(2026, 10, 28))          # tonight = Oct 27: the eve
    assert not ev.is_fomc_eve(dt.date(2026, 10, 27))
    assert ev.next_fomc(dt.date(2026, 9, 28)) == dt.date(2026, 10, 28)
    assert ev.next_fomc(dt.date(2026, 10, 28)) == dt.date(2026, 10, 28)
    assert ev.stale_warning(dt.date(2026, 9, 28)) is None
    last = ds[-1]
    w = ev.stale_warning(last - dt.timedelta(days=ev.STALE_DAYS - 1))
    assert w and "events.py" in w, "must warn loudly before the calendar runs out"
    assert ev.days_left(last + dt.timedelta(days=3)) == -3


def test_fomc_spare_cash_math():
    assert ev.filler_spare(1500.0, 900.0) == pytest.approx(600.0)            # budget - planned
    assert ev.filler_spare(1500.0, 1600.0) == 0.0                            # never negative
    assert ev.filler_spare(1500.0, 900.0, cash_left=400.0) == pytest.approx(400.0)   # cash bound
    assert ev.filler_spare(1500.0, 900.0, cash_left=400.0, floor=-300.0) == pytest.approx(600.0)
    assert ev.filler_spare(1500.0, 0.0, cash_left=-50.0) == 0.0
    assert ev.filler_shares(600.0, 550.0) == 1 and ev.filler_shares(549.0, 550.0) == 0
    assert ev.filler_shares(600.0, float("nan")) == 0


def test_fomc_auto_disable_rule():
    h = [{"ret": -0.001}] * 15
    assert ev.fomc_score(h)[2] is False, "not before 16 events"
    n, m, off = ev.fomc_score(h + [{"ret": -0.001}])
    assert n == 16 and m == pytest.approx(-10.0) and off
    assert ev.fomc_score(h + [{"ret": 0.05}])[2] is False
    assert ev.fomc_score([])[0] == 0


# ------------------------------------------------------------ helpers
class _Client:
    def __init__(self):
        self.submitted = []

    def submit_order(self, req):
        self.submitted.append(req)
        return SimpleNamespace(id=f"id{len(self.submitted)}")


class _Broker:
    key, secret = "AKTEST", "SEC"

    def __init__(self, equity="3000", mult="2", day="2026-10-27", next_day="2026-10-28"):
        self.client = _Client()
        self.eq, self.mult, self.day, self.next_day = equity, mult, day, next_day

    def clock(self):
        return SimpleNamespace(is_open=True, next_open=pd.Timestamp(f"{self.next_day} 09:30", tz=ET),
                               next_close=pd.Timestamp(f"{self.day} 16:00", tz=ET))

    def positions(self):
        return {}

    def account(self):
        return SimpleNamespace(equity=self.eq, multiplier=self.mult, trading_blocked=False,
                               account_blocked=False)


def _ex(tmp_path, account="paper", **kw):
    ex = DailyExecutor(Config.load(), account=account, broker=_Broker(**kw),
                       state_dir=tmp_path, log_dir=tmp_path)
    ex.notifier.send = lambda *a, **k: "skipped"
    ex.d.quote_source = "alpaca"
    return ex


def _market(monkeypatch, prices: dict, qqq=500.0, bars=None):
    from swingtrader.daily import executor as E
    syms = list(prices)
    elig = pd.DataFrame({"prev_close": [p / 0.9 for p in prices.values()]}, index=syms)
    live = pd.DataFrame({"price": list(prices.values()) + [qqq],
                         "high": [p / 0.9 for p in prices.values()] + [qqq * 1.01],
                         "low": [p * 0.999 for p in prices.values()] + [qqq * 0.99]},
                        index=syms + ["QQQ"])
    monkeypatch.setattr(E.md, "eligibility", lambda *a, **k: elig)
    monkeypatch.setattr(E.md, "live_rows", lambda s, *a, **k: live.loc[[x for x in s if x in live.index]])
    monkeypatch.setattr(E.md, "sip_daily", lambda *a, **k: bars or {})
    monkeypatch.setattr(E, "all_assets", lambda: SimpleNamespace(symbols=syms))


# ------------------------------------------------------------ F3 executor
def test_fomc_shadow_logs_then_scores_and_places_nothing(tmp_path, monkeypatch):
    _market(monkeypatch, {"LOSER": 9.0})
    ex = _ex(tmp_path)
    ex.d.night_tilt_k = 0
    book = DailyBook(cash=3000.0, start_equity=3000.0)
    ex.phase_close(book, "2026-10-27", dt.datetime(2026, 10, 27, 15, 40, tzinfo=ET), ex.broker.clock())
    sent = [r.symbol for r in ex.broker.client.submitted]
    assert sent == ["LOSER"], "the night leg trades as before; QQQ is shadow only"
    # budget 0.5 * 3000 = 1500; LOSER 10% cap = 150 -> 16 sh at 9 = 144; spare 1356 -> 2 QQQ at 500
    p = book.fomc["pending"]
    assert p["fomc"] == "2026-10-28" and p["shares"] == 2 and p["spare"] == pytest.approx(1500 - 144)
    assert any("[fomc] SHADOW" in l and "would buy 2 QQQ" in l for l in ex.lines)
    # next day: close 10-27 -> open 10-28, net of 2 x 3bp
    b = pd.DataFrame({"open": [499.0, 505.0], "close": [500.0, 503.0]},
                     index=pd.to_datetime(["2026-10-27", "2026-10-28"]))
    _market(monkeypatch, {"LOSER": 9.0}, bars={"QQQ": b})
    ex2 = _ex(tmp_path, day="2026-10-28", next_day="2026-10-29")
    ex2._fomc_shadow(book, "2026-10-28", dt.datetime(2026, 10, 28, 15, 40, tzinfo=ET),
                     ex2.broker.clock(), {"requested": 0.0, "planned": 0.0})
    h = book.fomc["history"]
    assert len(h) == 1 and h[0]["ret"] == pytest.approx(505.0 / 500.0 - 1 - 6e-4)
    assert "pending" not in book.fomc, "10-28 is not an FOMC eve"
    assert not ex2.broker.client.submitted


def test_fomc_shadow_is_off_on_the_roth_and_on_other_nights(tmp_path, monkeypatch):
    _market(monkeypatch, {"LOSER": 9.0})
    roth = _ex(tmp_path, account="roth", mult="1")
    book = DailyBook(cash=3000.0, start_equity=3000.0)
    roth.phase_close(book, "2026-10-27", dt.datetime(2026, 10, 27, 15, 40, tzinfo=ET), roth.broker.clock())
    assert not book.fomc, "taxable only: a Roth QQQ buy washes taxable QQQ losses"
    ex = _ex(tmp_path / "p", day="2026-10-20", next_day="2026-10-21")
    book = DailyBook(cash=3000.0, start_equity=3000.0)
    ex.phase_close(book, "2026-10-20", dt.datetime(2026, 10, 20, 15, 40, tzinfo=ET), ex.broker.clock())
    assert "pending" not in book.fomc


# ------------------------------------------------------------ Roth logs
def test_roth_cash_log_and_a2_place_no_orders(tmp_path, monkeypatch):
    monkeypatch.delenv("DAILY_ROTH_CAPITAL", raising=False)
    _market(monkeypatch, {"LOSER": 9.0, "OTHER": 20.0})
    ex = _ex(tmp_path, account="roth", mult="1", equity="3000")
    ex.d.night_tilt_k = 0
    ex.d.night_max_name_pct = 1.0
    book = DailyBook(cash=500.0, start_equity=3000.0)
    book.positions["TQQQ"] = {"qty": 20, "avg_px": 100.0, "leg": "noise", "entry_date": "2026-10-27"}
    book.positions["SGOV"] = {"qty": 5, "avg_px": 100.0, "leg": "tbill", "entry_date": "2026-10-20"}
    def fired(book, *a):                  # the oversold shadow triggers SPY with the IBS idle half
        book.oversold["pending"] = {"SPY": {"date": "2026-10-27", "usd": 1500.0}}
        ex._oversold_ibs_idle = 1500.0
    ex._oversold_shadow = fired
    ex.phase_close(book, "2026-10-27", dt.datetime(2026, 10, 27, 15, 40, tzinfo=ET), ex.broker.clock())
    line = next(l for l in ex.lines if "[roth-cash]" in l)
    assert "requested $1,500 funded" in line and "3x held $2,000" in line and "SGOV $500" in line
    assert "M2L pro-rata would size every name x0.33" in line
    sent = {r.symbol for r in ex.broker.client.submitted}
    assert sent <= {"LOSER", "OTHER"}, "no QQQ / SPY / look-alike orders from a shadow"
    a2 = book.oversold["pending"]["SPY"]["usd_a2"]
    assert a2 == pytest.approx(3000.0), "A2 = IBS idle half + the night leg's unused half"
    assert any("Roth A2" in l and "no order placed" in l for l in ex.lines)


# ------------------------------------------------------------ G1
def test_clustered_upper_bound():
    costs = [1.0, 3.0, -2.0, 4.0, 0.0, 2.0]
    days = ["a", "a", "b", "b", "c", "c"]
    m, ub, g = sg.clustered_upper_bound(costs, days)
    res = {"a": (1 - 4 / 3) + (3 - 4 / 3), "b": (-2 - 4 / 3) + (4 - 4 / 3), "c": (0 - 4 / 3) + (2 - 4 / 3)}
    se = np.sqrt(3 / 2 * sum(v * v for v in res.values()) / 36)
    assert g == 3 and m == pytest.approx(4 / 3) and ub == pytest.approx(4 / 3 + 1.645 * se)
    # perfectly correlated within a day: clustering widens the bound vs iid
    c = [5.0, 5.0, -3.0, -3.0, 8.0, 8.0, 0.0, 0.0]
    d = ["1", "1", "2", "2", "3", "3", "4", "4"]
    assert sg.clustered_upper_bound(c, d)[1] > sg.cost_upper_bound(c)
    assert np.isnan(sg.clustered_upper_bound([1.0, 2.0], ["x", "x"])[1]), "one day: no bound"


def test_lever_g1_would_open():
    rng = np.random.default_rng(0)
    good = [(f"2026-09-{i // 3 + 1:02d}", float(x)) for i, x in enumerate(rng.normal(0, 5, 30))]
    g = sg.lever_g1(good)
    assert g["n"] == 30 and g["days"] == 10 and g["ub"] < 10 and g["would_open"]
    assert not sg.lever_g1(good[:19])["would_open"], "n < 20"
    few_days = [("2026-09-01" if i % 2 else "2026-09-02", c) for i, (_, c) in enumerate(good)]
    assert not sg.lever_g1(few_days)["would_open"], "2 exit days: clustered SE unreliable"
    bad = [(d, c + 20.0) for d, c in good]
    assert not sg.lever_g1(bad)["would_open"]


def test_lever_g1_log_leaves_the_live_gate_alone(tmp_path):
    ex = _ex(tmp_path, account="live")
    ex.d.lever_weight = 0.65                                      # config.yaml may ship it off
    book = DailyBook(cash=3000.0, start_equity=3000.0)
    ex._exit_stats = (60, 2.0)                                    # G0 would open
    ex._exit_g1 = sg.lever_g1([("2026-09-01", 50.0)] * 25)        # G1 would not
    ex._lever_gate(book)
    assert book.levered, "lever_ok decides; G1 only logs"
    assert any("[lever-g1] SHADOW n 25 (1 days)" in l and "would_open no" in l for l in ex.lines)


# ------------------------------------------------------------ wash guard G4s
def _taxable_book():
    return {"positions": {"HELD": {"qty": 1, "avg_px": 10, "leg": "night"}},
            "orders": {"c1": {"sym": "PEND", "status": "new"}, "c2": {"sym": "DONE", "status": "filled"}},
            "closed": [{"sym": "LOSS", "exit_date": "2026-10-10", "pnl": -5.0},
                       {"sym": "GAIN", "exit_date": "2026-10-10", "pnl": 5.0},
                       {"sym": "SPY", "exit_date": "2026-10-20", "pnl": 2.0},
                       {"sym": "OLDLOSS", "exit_date": "2026-09-01", "pnl": -5.0},
                       {"sym": "SGOV", "exit_date": "2026-10-20", "pnl": -0.1}]}


def test_wash_g4s_would_skip_sets():
    from swingtrader.daily.book import TERMINAL
    g = sg.wash_g4s("roth", _taxable_book(), "2026-10-27", ["XLK", "SPY", "QQQ", "DIA"], "SGOV", TERMINAL)
    assert g["current"] == {"HELD", "PEND", "LOSS", "GAIN", "SPY"}, "live guard: symmetric 31d, SGOV excepted"
    assert g["night"] == {"HELD", "PEND", "LOSS"}, "Roth skips taxable LOSS sales (30d) + what it holds now"
    assert g["ibs_subs"] == {"XLK": "VGT"}, "different-index look-alike only"
    assert g["ibs_skip"] == ["SPY"], "same-index name the taxable book traded in 31d"
    assert g["ibs_take"] == ["VGT", "QQQ", "DIA"]
    roth_book = {"positions": {"TQQQ": {}}, "orders": {},
                 "closed": [{"sym": "ABC", "exit_date": "2026-10-01", "pnl": 3.0}]}
    t = sg.wash_g4s("live", roth_book, "2026-10-27", ["QQQ"], "SGOV", TERMINAL)
    assert t["night"] == t["current"] == {"TQQQ", "ABC"}, "taxable yields names the Roth traded in 31d"
    assert t["ibs_take"] == ["QQQ"] and not t["ibs_skip"]


def test_wash_shadow_logs_and_changes_no_orders(tmp_path, monkeypatch):
    monkeypatch.delenv("DAILY_ROTH_CAPITAL", raising=False)
    _market(monkeypatch, {"LOSS": 9.0, "GAIN": 20.0, "FREE": 30.0})
    (tmp_path / "book-daily-live.json").write_text(json.dumps(
        {"cash": 0, "start_equity": 0, **_taxable_book()}))
    ex = _ex(tmp_path, account="roth", mult="1", day="2026-10-20", next_day="2026-10-21")
    ex.d.night_tilt_k = 0
    ex.d.wash_guard = "symmetric"         # the shadow compares G4s against the OLD live guard
    book = DailyBook(cash=3000.0, start_equity=3000.0)
    ex.phase_close(book, "2026-10-20", dt.datetime(2026, 10, 20, 15, 40, tzinfo=ET), ex.broker.clock())
    assert {r.symbol for r in ex.broker.client.submitted} == {"FREE"}, "live guard still blocks LOSS/GAIN"
    line = next(l for l in ex.lines if "[wash-guard] SHADOW roth 15:40" in l)
    assert "G4s would take GAIN" in line and "skip LOSS" in line
