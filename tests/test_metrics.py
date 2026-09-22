"""Metrics must recover known answers from synthetic series with known truth."""
import numpy as np
import pandas as pd
import pytest

from swingtrader.metrics import (amplitude_pct, drift_t, efficiency_ratio,
                                 halflife, hurst, zscore)


def ou_series(n=400, theta=0.10, mu=np.log(15.0), sigma=0.03, seed=0):
    """Ornstein-Uhlenbeck in log price. True halflife = ln2/theta."""
    rng = np.random.default_rng(seed)
    y = np.empty(n)
    y[0] = mu
    for i in range(1, n):
        y[i] = y[i - 1] + theta * (mu - y[i - 1]) + sigma * rng.standard_normal()
    return pd.Series(np.exp(y))


def random_walk(n=400, sigma=0.03, seed=1):
    rng = np.random.default_rng(seed)
    return pd.Series(np.exp(np.log(15.0) + np.cumsum(sigma * rng.standard_normal(n))))


def trend(n=400, slope=0.004, sigma=0.01, seed=2):
    rng = np.random.default_rng(seed)
    y = np.log(15.0) + slope * np.arange(n) + sigma * rng.standard_normal(n)
    return pd.Series(np.exp(y))


@pytest.mark.parametrize("theta", [0.05, 0.10, 0.20])
def test_halflife_recovers_known_theta(theta):
    true_hl = np.log(2) / theta
    est = np.median([halflife(ou_series(n=600, theta=theta, seed=s)) for s in range(12)])
    assert est == pytest.approx(true_hl, rel=0.25), f"true {true_hl:.2f} est {est:.2f}"


def test_halflife_infinite_for_random_walk():
    # A random walk has no mean to revert to; estimates must not look tradable.
    ests = [halflife(random_walk(seed=s)) for s in range(20)]
    finite_short = [e for e in ests if e < 15.0]
    assert len(finite_short) <= 3, f"random walk looked mean-reverting {len(finite_short)}/20"


def test_halflife_rejects_trend():
    # A noisy trend can yield a finite lambda, but it must land nowhere near the
    # 3-15 day band the scanner treats as tradable.
    hl = halflife(trend())
    assert hl > 100, f"trend produced a tradable-looking halflife of {hl:.1f}"


def test_hurst_discriminates():
    ou = np.median([hurst(ou_series(seed=s)) for s in range(10)])
    rw = np.median([hurst(random_walk(seed=s)) for s in range(10)])
    tr = np.median([hurst(trend(seed=s)) for s in range(10)])
    assert ou < 0.5, f"OU hurst {ou:.3f} should be < 0.5"
    assert rw == pytest.approx(0.5, abs=0.12), f"random walk hurst {rw:.3f}"
    assert tr > 0.5, f"trend hurst {tr:.3f} should be > 0.5"
    assert ou < rw < tr


def test_drift_t_rejects_trend_accepts_range():
    # HAC-corrected: genuine OU series must pass the configured |t| < 2 screen.
    ts = [abs(drift_t(ou_series(seed=s))) for s in range(12)]
    assert np.median(ts) < 2.0, f"median |t| on true OU series was {np.median(ts):.2f}"
    # Plain OLS gave a median near 5.5 here; HAC must be dramatically tighter.
    assert max(ts) < 5.0, f"HAC still over-rejecting OU: {[round(t,1) for t in ts]}"
    assert abs(drift_t(trend())) > 10.0, "a clear uptrend must produce a large |t|"


def test_drift_t_catches_stairstep_decline():
    # The dangerous case: oscillates, but bleeds down. Must NOT look range-bound.
    rng = np.random.default_rng(7)
    n = 400
    y = np.log(20.0) - 0.002 * np.arange(n) + 0.05 * np.sin(np.arange(n) / 8)
    s = pd.Series(np.exp(y + 0.005 * rng.standard_normal(n)))
    assert abs(drift_t(s)) > 5.0, "stair-step decline slipped through the drift filter"


def test_amplitude_scales_with_volatility():
    quiet = amplitude_pct(ou_series(sigma=0.01, seed=3))
    wild = amplitude_pct(ou_series(sigma=0.06, seed=3))
    assert wild > quiet * 2


def test_efficiency_ratio_separates_range_from_trend():
    ou = np.median([efficiency_ratio(ou_series(seed=s)) for s in range(10)])
    rw = np.median([efficiency_ratio(random_walk(seed=s)) for s in range(10)])
    tr = efficiency_ratio(trend())
    # ER is horizon-dependent (longer windows -> more path -> lower ER for
    # everything), so what must hold is the ordering and a wide separation,
    # not an absolute level. Thresholds are calibrated per window length.
    assert ou < rw < tr
    assert tr > 10 * ou, f"range {ou:.3f} vs trend {tr:.3f}: separation too weak"


def test_zscore_uses_only_past_bars():
    s = pd.Series(np.arange(100, dtype=float) + 10.0)
    z = zscore(s, 20)
    assert z.iloc[:19].isna().all(), "z-score produced a value before its window filled"
    # recompute point 50 from the first 51 bars only; must match the full-series value
    assert zscore(s.iloc[:51], 20).iloc[-1] == pytest.approx(z.iloc[50])


def test_residual_zscore_strips_the_factor_move():
    """A stock that only moved because the market moved is not oversold."""
    from swingtrader.metrics import residual_zscore
    idx = pd.bdate_range("2021-01-04", periods=400)
    rng = np.random.default_rng(5)
    mkt = pd.Series(rng.standard_normal(400) * 0.01, index=idx)
    mkt.iloc[-15:] -= 0.02                       # market-wide selloff
    factors = pd.DataFrame({"MKT": mkt,
                            "SMB": rng.standard_normal(400) * 0.002,
                            "HML": rng.standard_normal(400) * 0.002}, index=idx)
    # a pure beta-1 stock with tiny idiosyncratic noise: it falls with the market
    px = pd.Series(np.exp(np.log(30.0) + (mkt + rng.standard_normal(400) * 0.001).cumsum()),
                   index=idx)
    raw = zscore(px, 20).iloc[-1]
    res = residual_zscore(px, factors, 20, idx[-60]).iloc[-1]
    assert raw < -1.0, f"raw z-score should look oversold, got {raw:.2f}"
    assert abs(res) < abs(raw), (
        f"residual z ({res:.2f}) must be less extreme than raw ({raw:.2f}) -- "
        "the drop was the market, not the stock")
