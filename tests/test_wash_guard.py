"""Live wash guard `daily.wash_guard: symmetric | roth_first` (addenda 31/39).
Reuses the fakes in test_shadows.py. No network."""
import dataclasses
import datetime as dt
import json

import numpy as np
import pandas as pd
import pytest

from swingtrader.config import Config, DailyCfg
from swingtrader.daily import signals as sg
from swingtrader.daily.book import DailyBook

from test_shadows import ET, _ex, _market

TODAY = "2026-10-20"


def _write(tmp_path, account, positions=None, orders=None, closed=None):
    (tmp_path / f"book-daily-{account}.json").write_text(json.dumps(
        {"cash": 0, "start_equity": 0, "positions": positions or {}, "orders": orders or {},
         "closed": closed or []}))


def _taxable(tmp_path):
    _write(tmp_path, "live",
           positions={"HELD": {"qty": 1, "avg_px": 10, "leg": "night"}},
           orders={"c1": {"sym": "PEND", "status": "new"}, "c2": {"sym": "DONE", "status": "filled"}},
           closed=[{"sym": "LOSS", "exit_date": "2026-10-10", "pnl": -5.0},
                   {"sym": "GAIN", "exit_date": "2026-10-10", "pnl": 5.0},
                   {"sym": "NOPNL", "exit_date": "2026-10-12"},                # unknown: treat as a loss
                   {"sym": "PXLOSS", "exit_date": "2026-10-12", "qty": 3, "entry_px": 10, "exit_px": 9},
                   {"sym": "OLDLOSS", "exit_date": "2026-09-01", "pnl": -5.0},
                   {"sym": "SGOV", "exit_date": "2026-10-15", "pnl": -0.1}])


def _roth(tmp_path, mode="roth_first", **kw):
    ex = _ex(tmp_path, account="roth", mult="1", day=TODAY, next_day="2026-10-21", **kw)
    ex.d.wash_guard = mode
    ex.d.night_tilt_k = 0
    return ex


# ------------------------------------------------------------ config / order
def test_default_is_symmetric_config_yaml_sets_roth_first_and_bad_values_fail(tmp_path):
    assert DailyCfg().wash_guard == "symmetric", "backward compatible default"
    assert Config.load().daily.wash_guard == "roth_first"
    with pytest.raises(ValueError, match="wash_guard"):
        DailyCfg(wash_guard="roth-first")
    p = tmp_path / "c.yaml"
    p.write_text("daily:\n  wash_guard: bogus\n")
    with pytest.raises(ValueError):
        Config.load(p)


def test_account_order_under_both_modes(monkeypatch):
    monkeypatch.setenv("DAILY_LIVE", "on")
    monkeypatch.setenv("DAILY_ROTH", "on")
    d = Config.load().daily
    assert dataclasses.replace(d, wash_guard="symmetric").resolved_accounts() == ["paper", "live", "roth"]
    assert dataclasses.replace(d, wash_guard="roth_first").resolved_accounts() == ["paper", "roth", "live"]
    monkeypatch.setenv("DAILY_ROTH", "off")
    assert dataclasses.replace(d, wash_guard="roth_first").resolved_accounts() == ["paper", "live"]
    monkeypatch.setenv("DAILY_ROTH", "on")
    monkeypatch.setenv("DAILY_LIVE", "off")
    assert dataclasses.replace(d, wash_guard="roth_first").resolved_accounts() == ["paper", "roth"]


def test_closed_at_loss_is_conservative():
    assert sg.closed_at_loss({"pnl": -0.01}) and not sg.closed_at_loss({"pnl": 0.0})
    assert sg.closed_at_loss({"qty": 2, "entry_px": 10, "exit_px": 9.5})
    assert not sg.closed_at_loss({"qty": -2, "entry_px": 10, "exit_px": 9.5}), "a short that made money"
    assert sg.closed_at_loss({}), "unknown = loss"


# ------------------------------------------------------------ Roth night leg
def test_roth_night_foreign_set_is_loss_sales_plus_held_now(tmp_path):
    _taxable(tmp_path)
    ex = _roth(tmp_path)
    book = DailyBook(cash=3000.0, start_equity=3000.0)
    night = ex._foreign_symbols(book, leg="night", today=TODAY)
    assert night == {"HELD", "PEND", "LOSS", "NOPNL", "PXLOSS"}
    assert "GAIN" not in night, "a taxable GAIN sale cannot be washed"
    assert "OLDLOSS" not in night and "SGOV" not in night and "DONE" not in night
    # every other leg keeps the 31-day exact-symbol symmetric set
    assert {"GAIN", "LOSS", "HELD", "PEND"} <= ex._foreign_symbols(book, today=TODAY)
    # symmetric mode: the night leg gets the old 31-day set
    ex.d.wash_guard = "symmetric"
    assert "GAIN" in ex._foreign_symbols(book, leg="night", today=TODAY)


@pytest.mark.parametrize("mode,bought", [("roth_first", {"GAIN", "FREE"}), ("symmetric", {"FREE"})])
def test_roth_night_trades_taxable_gain_names_only_under_roth_first(tmp_path, monkeypatch, mode, bought):
    monkeypatch.delenv("DAILY_ROTH_CAPITAL", raising=False)
    _market(monkeypatch, {"LOSS": 9.0, "GAIN": 20.0, "FREE": 30.0, "HELD": 12.0, "VGT": 500.0})
    _taxable(tmp_path)
    ex = _roth(tmp_path, mode)
    book = DailyBook(cash=3000.0, start_equity=3000.0)
    ex.phase_close(book, TODAY, dt.datetime(2026, 10, 20, 15, 40, tzinfo=ET), ex.broker.clock())
    assert {r.symbol for r in ex.broker.client.submitted} == bought
    wash = [l for l in ex.lines if "[wash] roth_first" in l]
    if mode == "roth_first":
        assert wash and "roth night blocks 5 (taxable loss sales 30d + held/pending" in wash[0]
        assert any("[wash-guard] SHADOW roth 15:40: the live guard IS G4s" in l for l in ex.lines)
    else:
        assert not wash


def test_taxable_night_still_blocks_everything_the_roth_traded(tmp_path, monkeypatch):
    monkeypatch.delenv("DAILY_LIVE_CAPITAL", raising=False)
    _market(monkeypatch, {"RGAIN": 20.0, "RHELD": 12.0, "FREE": 30.0})
    _write(tmp_path, "roth", positions={"RHELD": {"qty": 1, "avg_px": 10, "leg": "night"}},
           closed=[{"sym": "RGAIN", "exit_date": "2026-10-05", "pnl": 3.0}])
    ex = _ex(tmp_path, account="live", day=TODAY, next_day="2026-10-21")
    ex.d.wash_guard, ex.d.night_tilt_k = "roth_first", 0
    book = DailyBook(cash=3000.0, start_equity=3000.0)
    ex.phase_close(book, TODAY, dt.datetime(2026, 10, 20, 15, 40, tzinfo=ET), ex.broker.clock())
    assert {r.symbol for r in ex.broker.client.submitted} == {"FREE"}
    assert any("[wash] roth_first: taxable (runs after the Roth) blocks 2" in l for l in ex.lines)


# ------------------------------------------------------------ Roth IBS leg
def _ibs_bars(low: set):
    """Bars for every requested symbol; IBS 0.05 on the last bar for `low`, 0.95 otherwise."""
    idx = pd.bdate_range("2025-06-01", "2026-10-19")

    def bars(syms, *a, **k):
        out = {}
        for i, s in enumerate(syms):
            c = pd.Series(np.linspace(100, 110 + i, len(idx)), index=idx)
            df = pd.DataFrame({"open": c, "high": c + 1, "low": c - 1, "close": c, "volume": 1})
            df.iloc[-1, df.columns.get_loc("close")] = df["low"].iloc[-1] + (0.1 if s in low else 1.9)
            out[s] = df
        return out
    return bars


def _ibs_exec(tmp_path, monkeypatch, low, account="roth", mode="roth_first"):
    from swingtrader.daily import executor as E
    monkeypatch.setattr(E.md, "sip_daily", _ibs_bars(low))
    ex = _roth(tmp_path, mode) if account == "roth" else _ex(tmp_path, account=account)
    ex.d.wash_guard = mode
    ex.d.ibs_symbols = ["XLK", "SPY", "SMH", "IWM", "QQQ"]
    ex.d.ibs_top_k = None
    return ex


def test_roth_ibs_trades_lookalikes_and_skips_same_index_names_the_taxable_book_traded(tmp_path, monkeypatch):
    # taxable: sold SPY (same index, no safe look-alike) and traded SOXX (its noise stand-in for SMH)
    _write(tmp_path, "live", closed=[{"sym": "SPY", "exit_date": "2026-10-10", "pnl": 4.0},
                                     {"sym": "SOXX", "exit_date": "2026-10-15", "pnl": -1.0},
                                     {"sym": "XLK", "exit_date": "2026-10-15", "pnl": -9.0}])
    ex = _ibs_exec(tmp_path, monkeypatch, low={"XLK", "SPY", "SMH", "IWM"})
    book = DailyBook(cash=3000.0, start_equity=3000.0)
    ex._ibs_open(book, TODAY, 3000.0)
    buys = {r.symbol for r in ex.broker.client.submitted if r.side.value == "buy"}
    assert buys == {"VGT", "IWM"}, "XLK->VGT (different index); IWM free; SPY skipped; SOXX taken"
    line = next(l for l in ex.lines if "[wash] roth_first: roth night blocks" in l)
    assert "IBS look-alikes XLK->VGT" in line and "'SPY'" in line and "'SMH->SOXX'" in line
    # the look-alike is sized off its own bars (not XLK's)
    vgt = next(o for o in book.orders.values() if o["sym"] == "VGT")
    assert vgt["ref_px"] != pytest.approx(next(o for o in book.orders.values() if o["sym"] == "IWM")["ref_px"])


def test_symmetric_roth_ibs_is_unchanged(tmp_path, monkeypatch):
    _write(tmp_path, "live", closed=[{"sym": "SPY", "exit_date": "2026-10-10", "pnl": 4.0},
                                     {"sym": "XLK", "exit_date": "2026-10-15", "pnl": -9.0}])
    ex = _ibs_exec(tmp_path, monkeypatch, low={"XLK", "SPY", "SMH", "IWM"}, mode="symmetric")
    book = DailyBook(cash=3000.0, start_equity=3000.0)
    ex._ibs_open(book, TODAY, 3000.0)
    assert {r.symbol for r in ex.broker.client.submitted} == {"SMH", "IWM"}
    assert not any("[wash]" in l for l in ex.lines)


def test_paper_ibs_never_uses_lookalikes(tmp_path, monkeypatch):
    ex = _ibs_exec(tmp_path, monkeypatch, low={"XLK"}, account="paper")
    book = DailyBook(cash=3000.0, start_equity=3000.0)
    ex._ibs_open(book, TODAY, 3000.0)
    assert {r.symbol for r in ex.broker.client.submitted} == {"XLK"}


def test_roth_held_lookalike_is_kept_then_sold_when_its_target_drops(tmp_path, monkeypatch):
    held = {"VGT": {"qty": 3, "avg_px": 600.0, "leg": "ibs", "entry_date": "2026-10-19"}}
    ex = _ibs_exec(tmp_path, monkeypatch, low={"XLK"})
    book = DailyBook(cash=1200.0, start_equity=3000.0, positions=dict(held))
    ex._ibs_open(book, TODAY, 3000.0)
    assert ex.broker.client.submitted == [], "XLK still a target: hold VGT, no sell/rebuy churn"
    ex = _ibs_exec(tmp_path, monkeypatch, low=set())
    book = DailyBook(cash=1200.0, start_equity=3000.0, positions=dict(held))
    ex._ibs_open(book, TODAY, 3000.0)
    sent = [(r.symbol, r.side.value, float(r.qty)) for r in ex.broker.client.submitted]
    assert sent == [("VGT", "sell", 3.0)], "XLK dropped: sell the look-alike (SGOV only once the leg is flat)"


def test_roth_ibs_idle_goes_to_sgov_under_roth_first(tmp_path, monkeypatch):
    ex = _ibs_exec(tmp_path, monkeypatch, low=set())
    ex.d.ibs_symbols = ["XLK", "SPY"]
    book = DailyBook(cash=3000.0, start_equity=3000.0)
    ex._ibs_open(book, TODAY, 3000.0)
    assert [r.symbol for r in ex.broker.client.submitted] == ["SGOV"]
