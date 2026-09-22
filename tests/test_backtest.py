"""Engine tests: no-lookahead, cost accounting, and fold disjointness.

These are the tests that decide whether the headline numbers mean anything.
"""
import numpy as np
import pandas as pd
import pytest

from swingtrader.backtest import make_folds, run
from swingtrader.config import Config
from swingtrader.portfolio import Portfolio
from swingtrader.strategy import LONG, SHORT


def bars_from_close(close, dates=None, spread=0.005):
    n = len(close)
    idx = dates if dates is not None else pd.bdate_range("2021-01-04", periods=n)
    c = np.asarray(close, dtype=float)
    return pd.DataFrame(
        {"open": c, "high": c * (1 + spread), "low": c * (1 - spread),
         "close": c, "volume": np.full(n, 5_000_000.0)},
        index=pd.DatetimeIndex(idx),
    )


# ------------------------------------------------------------------ costs
def test_slippage_always_works_against_us():
    pf = Portfolio(100_000, 4, slippage_bps=20.0)
    assert pf.fill_price(100.0, LONG, opening=True) == pytest.approx(100.20)
    assert pf.fill_price(100.0, LONG, opening=False) == pytest.approx(99.80)
    assert pf.fill_price(100.0, SHORT, opening=True) == pytest.approx(99.80)
    assert pf.fill_price(100.0, SHORT, opening=False) == pytest.approx(100.20)


def test_round_trip_pnl_matches_hand_calculation():
    pf = Portfolio(100_000, 4, slippage_bps=20.0)
    d0, d1 = pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-20")
    pos = pf.open("FOO", LONG, 100.0, d0, equity_now=100_000, stop_pct=None)
    assert pos.entry_px == pytest.approx(100.20)
    assert pos.qty == pytest.approx(25_000 / 100.20)          # equity/max_positions
    t = pf.close("FOO", 110.0, d1, "reversion")
    assert t.exit_px == pytest.approx(109.78)
    assert t.pnl == pytest.approx((109.78 - 100.20) * pos.qty)
    # the 20bps each way must cost real money vs a frictionless fill
    frictionless = (110.0 - 100.0) * pos.qty
    assert t.pnl < frictionless
    # entry slip = 20bps of 100 = 0.20; exit slip = 20bps of 110 = 0.22
    assert frictionless - t.pnl == pytest.approx((0.20 + 0.22) * pos.qty)


def test_equity_is_conserved_through_a_round_trip():
    pf = Portfolio(100_000, 4, slippage_bps=0.0)
    d0, d1 = pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-20")
    pf.open("FOO", LONG, 50.0, d0, equity_now=100_000, stop_pct=None)
    assert pf.equity({"FOO": 50.0}) == pytest.approx(100_000)   # no instant P&L
    assert pf.equity({"FOO": 55.0}) == pytest.approx(100_000 + 25_000 * 0.10)
    pf.close("FOO", 55.0, d1, "reversion")
    assert pf.equity({}) == pytest.approx(102_500)


# ------------------------------------------------------------------ folds
def test_folds_are_disjoint_and_ordered():
    cfg = Config.load()
    dates = pd.bdate_range("2021-01-04", periods=600)
    folds = make_folds(dates, cfg)
    assert folds, "no folds produced"
    for f in folds:
        assert f.form_end < f.trade_start, "formation window overlaps the trade window"
        assert f.trade_start <= f.trade_end
        n_form = len(dates[(dates >= f.form_start) & (dates <= f.form_end)])
        assert n_form == cfg.walkforward.formation_days


# ------------------------------------------------------------------ lookahead
def _oscillator(n=400, period=30, amp=0.18, base=20.0, seed=0):
    rng = np.random.default_rng(seed)
    x = np.arange(n)
    return base * (1 + amp * np.sin(2 * np.pi * x / period)) * (
        1 + 0.01 * rng.standard_normal(n))


def _cfg_for_toy():
    cfg = Config.load()
    cfg.walkforward.formation_days = 120
    cfg.walkforward.trade_days = 60
    cfg.walkforward.step_days = 60
    cfg.selection.top_n = 2
    cfg.selection.min_amplitude_pct = 0.0
    cfg.selection.max_abs_drift_t = 99.0
    cfg.selection.halflife_min = 0.5
    cfg.selection.halflife_max = 200.0
    cfg.selection.hurst_max = 2.0
    cfg.selection.max_efficiency_ratio = 1.0
    cfg.cohorts["toy"] = cfg.cohorts["broad"]
    cfg.cohorts["toy"].min_iex_dollar_vol = 0.0
    cfg.portfolio.max_positions = 2
    return cfg


def test_entry_fills_at_next_open_never_the_decision_bar():
    """The decisive no-lookahead check.

    Price falls hard through day t (so the signal fires on t's close), then
    gaps UP on t+1's open. A leaky engine fills at t's low close and books the
    gap as free profit. A correct engine pays t+1's open.
    """
    cfg = _cfg_for_toy()
    cfg.portfolio.slippage_bps = 0.0
    n = 200
    close = np.full(n, 20.0)
    rng = np.random.default_rng(3)
    close = close * (1 + 0.004 * rng.standard_normal(n))
    close[150] = 14.0           # crash -> z << -2 at the close of bar 150
    df = bars_from_close(close)
    df.loc[df.index[151], ["open", "high", "low", "close"]] = [19.0, 19.5, 18.9, 19.2]

    res = run({"FOO": df}, cfg, "toy", verbose=False)
    entries = [t for t in res.trades if t.symbol == "FOO"]
    assert entries, "expected at least one trade"
    first = entries[0]
    assert first.entry_date == df.index[151], (
        f"filled on {first.entry_date.date()}, expected the bar AFTER the signal")
    assert first.entry_px == pytest.approx(19.0), (
        f"filled at {first.entry_px}, expected next open 19.00 - engine saw the crash bar")


def test_no_trade_before_the_first_trade_window():
    cfg = _cfg_for_toy()
    df = bars_from_close(_oscillator(400))
    res = run({"FOO": df}, cfg, "toy", verbose=False)
    first_trade_start = min(f.trade_start for f in res.folds)
    for t in res.trades:
        assert t.entry_date >= first_trade_start, (
            "a trade was opened inside the formation window")


def test_selection_cannot_see_the_trade_window():
    """Mutating bars strictly inside the trade window must not change picks."""
    cfg = _cfg_for_toy()
    base = {f"S{i}": bars_from_close(_oscillator(400, period=25 + i, seed=i))
            for i in range(6)}
    r1 = run(base, cfg, "toy", verbose=False)
    picks1 = [f.candidates for f in r1.folds]

    mutated = {k: v.copy() for k, v in base.items()}
    f0 = r1.folds[0]
    for k, v in mutated.items():
        m = (v.index >= f0.trade_start) & (v.index <= f0.trade_end)
        v.loc[m, ["open", "high", "low", "close"]] *= 3.0     # violent, obvious
    r2 = run(mutated, cfg, "toy", verbose=False)
    assert picks1[0] == [f.candidates for f in r2.folds][0], (
        "fold 0 selection changed when only its TRADE window was altered - "
        "the scanner is reading the future")


def test_stop_can_trigger_on_the_fill_bar():
    """Skipping the fill bar would hand every position a free day."""
    cfg = _cfg_for_toy()
    cfg.portfolio.slippage_bps = 0.0
    n = 200
    rng = np.random.default_rng(5)
    close = 20.0 * (1 + 0.004 * rng.standard_normal(n))
    close[150] = 14.0
    df = bars_from_close(close)
    # next bar opens at 19 then collapses intraday, through a -10% stop
    df.loc[df.index[151], ["open", "high", "low", "close"]] = [19.0, 19.0, 10.0, 10.5]
    res = run({"FOO": df}, cfg, "toy", stop_pct=10.0, verbose=False)
    stops = [t for t in res.trades if t.exit_reason == "stop"]
    assert stops, "stop did not trigger on the entry bar"
    assert stops[0].entry_date == stops[0].exit_date == df.index[151]


def test_position_cannot_outlive_its_time_stop():
    """Regression: a symbol dropped from the candidate set must still exit.

    Previously the exit check was gated on a z-score being present, and the
    z-cache only held current candidates -- so a position in a dropped symbol
    became immortal and was only closed at end_of_test. Eight such positions
    once supplied 99% of a run's profit.
    """
    cfg = _cfg_for_toy()
    cfg.selection.top_n = 1
    cfg.portfolio.max_positions = 4
    # two symbols that alternate being attractive, so candidates churn
    a = bars_from_close(_oscillator(400, period=21, amp=0.25, seed=1))
    b = bars_from_close(_oscillator(400, period=34, amp=0.25, seed=2))
    res = run({"AAA": a, "BBB": b}, cfg, "toy", verbose=False)
    assert res.trades, "expected trades"
    over = [t for t in res.trades
            if t.bars_held > cfg.strategy.time_stop_days and t.exit_reason != "end_of_test"]
    assert not over, f"{len(over)} trades outlived the time stop: {[t.bars_held for t in over][:5]}"
    eot = [t for t in res.trades if t.exit_reason == "end_of_test"]
    assert len(eot) <= cfg.portfolio.max_positions, (
        f"{len(eot)} positions survived to end_of_test; exits are not firing")


def test_short_equity_is_not_conjured_from_thin_air():
    """Regression: opening a short must not create equity.

    The short sale credits cash, so the open position is a liability. Valuing
    it positively double-counted and minted 50k of equity on a 25k short --
    which is how long/short runs reported a 1.09 Sharpe on a -24% CAGR.
    """
    pf = Portfolio(100_000, 4, slippage_bps=0.0)
    d0 = pd.Timestamp("2024-01-02")
    pf.open("FOO", SHORT, 50.0, d0, equity_now=100_000, stop_pct=None)
    assert pf.equity({"FOO": 50.0}) == pytest.approx(100_000), "short minted equity"
    assert pf.equity({"FOO": 45.0}) == pytest.approx(102_500)   # -10% -> +10% on 25k
    assert pf.equity({"FOO": 55.0}) == pytest.approx(97_500)
    assert pf.equity({"FOO": 100.0}) == pytest.approx(75_000)   # doubled against us
    t = pf.close("FOO", 45.0, pd.Timestamp("2024-01-20"), "reversion")
    assert t.pnl == pytest.approx(2_500)
    assert pf.equity({}) == pytest.approx(102_500)


def test_ruin_is_reported_not_ratio_ed():
    from swingtrader.report import curve_stats
    eq = pd.Series([100_000.0, 50_000.0, -5_000.0, 10_000.0],
                   index=pd.bdate_range("2024-01-02", periods=4))
    st = curve_stats(eq)
    assert "RUINED_on" in st
    assert np.isnan(st["sharpe"]), "a blown account must not report a Sharpe ratio"


def test_gross_exposure_cap_binds():
    pf = Portfolio(100_000, 8, slippage_bps=0.0, position_pct=0.50, max_gross_pct=100.0)
    d = pd.Timestamp("2024-01-02")
    assert pf.open("A", LONG, 10.0, d, 100_000, None) is not None
    assert pf.open("B", LONG, 10.0, d, 100_000, None) is not None
    # 2 x 50% = 100% gross; a third must be refused, not silently levered
    assert pf.open("C", LONG, 10.0, d, 100_000, None) is None
    gross = sum(p.qty * p.entry_px for p in pf.positions.values())
    assert gross <= 100_000 * 1.0001


def test_cash_accrual_uses_the_series_not_a_flat_guess():
    idx = pd.bdate_range("2024-01-02", periods=3)
    rets = pd.Series([0.0, 0.01, 0.02], index=idx)
    pf = Portfolio(100_000, 8, slippage_bps=0.0, cash_returns=rets)
    pf.accrue_cash(idx[1])
    assert pf.cash == pytest.approx(101_000)
    pf.accrue_cash(pd.Timestamp("2099-01-01"))   # unknown date -> no accrual
    assert pf.cash == pytest.approx(101_000)


def test_trailing_stop_ratchets_up_and_captures_the_run():
    """Price runs up then gives back; the trail must exit near the peak.

    Also guards the ratchet: a trailing stop that can loosen is just a wider
    fixed stop with extra steps.
    """
    cfg = _cfg_for_toy()
    cfg.portfolio.slippage_bps = 0.0
    n = 200
    rng = np.random.default_rng(11)
    close = 20.0 * (1 + 0.004 * rng.standard_normal(n))
    close[150] = 14.0                      # the dip that triggers entry
    df = bars_from_close(close)
    # after entry: run 19 -> 40 over 7 bars, then sell off INTRADAY to 20
    path = [19.0, 22.0, 26.0, 30.0, 34.0, 38.0, 40.0, 36.0]
    for k, px in enumerate(path):
        i = df.index[151 + k]
        df.loc[i, ["open", "high", "low", "close"]] = [px, px * 1.01, px * 0.99, px]
    # the give-back bar opens near the prior close and falls through the trail
    df.loc[df.index[159], ["open", "high", "low", "close"]] = [35.5, 35.5, 20.0, 20.5]

    res = run({"FOO": df}, cfg, "toy", stop_pct=10.0, exit_mode="trail",
              trail_pct=15.0, time_stop_days=0, verbose=False)
    tr = [t for t in res.trades if t.exit_reason == "trail"]
    assert tr, f"trailing exit never fired; got {[t.exit_reason for t in res.trades]}"
    t0 = tr[0]
    # peak high was 40*1.01 = 40.4; a 15% trail exits near 34.3, not at 20
    assert t0.exit_px > 30.0, f"gave back the whole run, exited at {t0.exit_px:.2f}"
    assert t0.pnl_pct > 50.0, f"captured only {t0.pnl_pct:.1f}% of a 19->40 run"


def test_trailing_stop_fills_at_the_open_when_price_gaps_through_it():
    """A gap below the trail fills at the open, not at the stop price.

    Modelling a gap as if it filled at the stop invents money that a real
    order could never have gotten -- exactly the flattery this repo exists to
    avoid. These names gap on news, so it matters.
    """
    cfg = _cfg_for_toy()
    cfg.portfolio.slippage_bps = 0.0
    n = 200
    rng = np.random.default_rng(11)
    close = 20.0 * (1 + 0.004 * rng.standard_normal(n))
    close[150] = 14.0
    df = bars_from_close(close)
    for k, px in enumerate([19.0, 26.0, 34.0, 40.0]):
        i = df.index[151 + k]
        df.loc[i, ["open", "high", "low", "close"]] = [px, px * 1.01, px * 0.99, px]
    # overnight disaster: opens at 20 having closed at 40
    df.loc[df.index[155], ["open", "high", "low", "close"]] = [20.0, 20.5, 19.0, 19.5]
    res = run({"FOO": df}, cfg, "toy", stop_pct=10.0, exit_mode="trail",
              trail_pct=15.0, time_stop_days=0, verbose=False)
    t0 = [t for t in res.trades if t.exit_reason == "trail"][0]
    assert t0.exit_px == pytest.approx(20.0), (
        f"gap filled at {t0.exit_px:.2f}; a stop cannot beat the opening print")


def test_reversion_mode_still_exits_at_the_mean():
    """The default exit must be unaffected by the trailing machinery."""
    cfg = _cfg_for_toy()
    df = bars_from_close(_oscillator(400))
    res = run({"FOO": df}, cfg, "toy", verbose=False)
    assert res.trades, "fixture produced no trades"
    assert any(t.exit_reason == "reversion" for t in res.trades)
    assert not any(t.exit_reason == "trail" for t in res.trades)


def test_controls_are_wired_into_every_selection_mode():
    """A control that silently does nothing is worse than no control.

    The momentum branch once built its Signal directly, bypassing
    apply_control, so a 'flip' run returned byte-identical results to the real
    one -- and the sleeve looked falsified when it had never been tested.
    """
    cfg = _cfg_for_toy()
    df = bars_from_close(_oscillator(400))
    for mode in ("reversion", "momentum"):
        kw = dict(select_mode=mode, verbose=False)
        if mode == "momentum":
            kw.update(z_entry_override=-1.0, exit_mode="trail", trail_pct=20.0)
        base = run({"FOO": df}, cfg, "toy", **kw)
        flip = run({"FOO": df}, cfg, "toy", control="flip", **kw)
        if not base.trades:
            continue
        sides_base = {t.side for t in base.trades}
        sides_flip = {t.side for t in flip.trades}
        assert sides_flip != sides_base or not flip.trades, (
            f"control='flip' had no effect in select_mode={mode!r}")
