"""Range-behaviour metrics, computed on a formation window ONLY.

Every function takes a slice of history and returns a scalar describing how that
slice behaved. Nothing here may see a bar outside the window it is handed -- the
walk-forward driver relies on that to keep selection honest.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

LN2 = float(np.log(2.0))


def halflife(close: pd.Series) -> float:
    """Ornstein-Uhlenbeck mean-reversion half-life in trading days.

    Regress dy_t on y_{t-1}: dy = lambda*y_{t-1} + c. For a mean-reverting
    series lambda < 0 and halflife = -ln2/lambda. This is the metric that
    encodes "the bounce shouldn't take too long".

    Returns inf when the series trends or random-walks (lambda >= 0).
    """
    y = np.log(close.astype(float).values)
    y = y[np.isfinite(y)]
    if len(y) < 30:
        return float("inf")
    lag, dy = y[:-1], np.diff(y)
    lag_c = lag - lag.mean()
    denom = float((lag_c**2).sum())
    if denom <= 0:
        return float("inf")
    lam = float((lag_c * (dy - dy.mean())).sum() / denom)
    if lam >= 0:
        return float("inf")
    return -LN2 / lam


def hurst(close: pd.Series, max_lag: int = 40) -> float:
    """Hurst exponent via the aggregated-dispersion method.

    H < 0.5 anti-persistent (mean reverting), 0.5 random walk, > 0.5 trending.
    Fits log(std of tau-step differences) against log(tau); the slope is H.
    """
    y = np.log(close.astype(float).values)
    y = y[np.isfinite(y)]
    n = len(y)
    if n < 40:
        return float("nan")
    hi = int(min(max_lag, n // 3))
    if hi < 4:
        return float("nan")
    lags = np.arange(2, hi + 1)
    taus = []
    for lag in lags:
        d = y[lag:] - y[:-lag]
        taus.append(np.sqrt(np.mean(d**2)) if len(d) else np.nan)
    taus = np.asarray(taus, dtype=float)
    ok = np.isfinite(taus) & (taus > 0)
    if ok.sum() < 4:
        return float("nan")
    return float(np.polyfit(np.log(lags[ok]), np.log(taus[ok]), 1)[0])


def drift_t(close: pd.Series) -> float:
    """t-stat of the OLS slope of log price on time, with Newey-West HAC errors.

    Near zero means the window has no net direction. A stock that "ranged"
    while grinding down 40% is not ranging -- it is falling in steps, and
    buying its dips is a slow bleed.

    The HAC correction is not optional here. Mean-reverting series are heavily
    autocorrelated by construction, which inflates the plain OLS t-stat: on
    synthetic OU series with a true slope of zero, plain OLS returns |t| as
    high as 5.9. Screening on that would reject precisely the stocks this
    strategy wants. Newey-West with the standard 4*(n/100)^(2/9) bandwidth
    brings those back under 2.
    """
    y = np.log(close.astype(float).values)
    y = y[np.isfinite(y)]
    n = len(y)
    if n < 30:
        return float("nan")
    x = np.arange(n, dtype=float)
    xc = x - x.mean()
    sxx = float((xc**2).sum())
    if sxx <= 0:
        return float("nan")
    beta = float((xc * (y - y.mean())).sum() / sxx)
    resid = y - (y.mean() + beta * xc)

    # Newey-West HAC variance of beta
    lag = int(np.floor(4.0 * (n / 100.0) ** (2.0 / 9.0)))
    lag = max(1, min(lag, n - 2))
    u = xc * resid
    s_hac = float((u**2).sum())
    for l in range(1, lag + 1):
        w = 1.0 - l / (lag + 1.0)
        s_hac += 2.0 * w * float((u[l:] * u[:-l]).sum())
    if s_hac <= 0:
        return float("nan")
    se = np.sqrt(s_hac) / sxx
    return float(beta / se) if se > 0 else float("nan")


def amplitude_pct(close: pd.Series) -> float:
    """Expected gross round-trip size, in percent of price.

    The trade being modelled runs from z = -2 back to z = 0, i.e. two standard
    deviations of price. So 2*sigma/price is exactly the gross move a winning
    trade captures, before costs. This is the filter mega-caps fail.
    """
    c = close.astype(float)
    if len(c) < 20 or c.mean() <= 0:
        return 0.0
    return float(2.0 * c.std(ddof=1) / c.mean() * 100.0)


def efficiency_ratio(close: pd.Series) -> float:
    """Kaufman efficiency ratio: |net move| / total path length, on log price.

    Near 0 means the price wandered a long way but ended where it started --
    a range. Near 1 means every step went the same direction -- a trend.

    This replaces a static mean +/- 2*sigma containment measure, which turned
    out to be worthless: a strong trend inflates sigma so much that the band
    swallows the entire path (a 15 -> 75 trend scored 0.965 containment against
    a genuine range's 0.960). Path-vs-displacement has no such degeneracy.
    """
    y = np.log(close.astype(float).dropna().values)
    if len(y) < 20:
        return 1.0
    path = float(np.abs(np.diff(y)).sum())
    if path <= 0:
        return 1.0
    return float(abs(y[-1] - y[0]) / path)


def annual_vol(close: pd.Series) -> float:
    r = np.log(close.astype(float)).diff().dropna()
    return float(r.std(ddof=1) * np.sqrt(252)) if len(r) > 5 else 0.0


def dollar_volume(bars: pd.DataFrame) -> float:
    """Median daily dollar volume. On the IEX feed this is IEX's share only."""
    if bars.empty:
        return 0.0
    return float((bars["close"] * bars["volume"]).median())


def zscore(close: pd.Series, window: int) -> pd.Series:
    """Rolling z-score. Uses only bars at or before each point by construction."""
    c = close.astype(float)
    mu = c.rolling(window).mean()
    sd = c.rolling(window).std(ddof=1)
    return (c - mu) / sd.replace(0.0, np.nan)


def describe(bars: pd.DataFrame) -> dict:
    """All selection metrics for one symbol over one formation window."""
    c = bars["close"]
    return {
        "halflife": halflife(c),
        "hurst": hurst(c),
        "drift_t": drift_t(c),
        "amplitude_pct": amplitude_pct(c),
        "efficiency_ratio": efficiency_ratio(c),
        "annual_vol": annual_vol(c),
        "dollar_vol": dollar_volume(bars),
        "last_close": float(c.iloc[-1]) if len(c) else np.nan,
        "n_bars": int(len(c)),
    }
