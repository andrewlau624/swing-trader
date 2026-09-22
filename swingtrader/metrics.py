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


def overnight_share(bars: pd.DataFrame, window: int = 5) -> float:
    """What fraction of the recent move happened overnight rather than intraday.

    Decomposes each day into prev_close -> open (overnight) and open -> close
    (intraday), after Lou, Polk & Skouras. The hypothesis this tests: a dip
    created by overnight gaps is a liquidity/sentiment shock that reverts,
    while a dip ground out intraday is informed selling that continues.

    Returns the overnight fraction of the total move. For a decline, values
    near 1 mean the drop happened almost entirely in gaps; near 0 or negative
    means it was intraday selling.
    """
    if len(bars) < window + 2:
        return float("nan")
    c, o = bars["close"].astype(float), bars["open"].astype(float)
    overnight = np.log(o / c.shift())
    total = np.log(c / c.shift())
    on = float(overnight.iloc[-window:].sum())
    tot = float(total.iloc[-window:].sum())
    if tot == 0 or not np.isfinite(tot) or not np.isfinite(on):
        return float("nan")
    return on / tot


def factor_returns(bars: dict) -> pd.DataFrame:
    """FF3-style daily factor proxies built from liquid ETFs.

    MKT = SPY, SMB = IWM - IWB (small minus broad), HML = IWD - IWF
    (value minus growth). Proxies, not Ken French's series, but they capture
    the same variation and need no extra data source.
    """
    need = ("SPY", "IWM", "IWB", "IWD", "IWF")
    if any(s not in bars for s in need):
        return pd.DataFrame()
    r = {s: np.log(bars[s]["close"]).diff() for s in need}
    df = pd.DataFrame(r).dropna()
    return pd.DataFrame({
        "MKT": df["SPY"],
        "SMB": df["IWM"] - df["IWB"],
        "HML": df["IWD"] - df["IWF"],
    })


def residual_zscore(close: pd.Series, factors: pd.DataFrame, window: int,
                    fit_end: pd.Timestamp, min_obs: int = 60) -> pd.Series:
    """Z-score of CUMULATIVE RESIDUAL return rather than of raw price.

    Both the academic and the open-source surveys land on this independently as
    the single largest documented improvement to short-term reversal: a raw
    price z-score is contaminated by factor and industry momentum, so part of
    what looks like an oversold stock is really an oversold *market*. Blitz,
    Huij, Lansdorp & Verbeek report Sharpe 0.62 -> 1.28 moving to residuals,
    and find plain reversal insignificant post-1990 while the residual version
    survives costs.

    Betas are fitted ONLY on data up to fit_end (the formation window), then
    held fixed through the trading window -- both to avoid lookahead and
    because refitting daily is not what a real desk would do.
    """
    r = np.log(close.astype(float)).diff()
    fx = factors.reindex(r.index)
    fit = pd.concat([r, fx], axis=1).dropna()
    fit = fit[fit.index <= fit_end]
    if len(fit) < min_obs:
        return pd.Series(index=close.index, dtype=float)

    y = fit.iloc[:, 0].values
    X = np.column_stack([np.ones(len(fit)), fit.iloc[:, 1:].values])
    try:
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    except np.linalg.LinAlgError:
        return pd.Series(index=close.index, dtype=float)

    full = pd.concat([r, fx], axis=1).dropna()
    Xf = np.column_stack([np.ones(len(full)), full.iloc[:, 1:].values])
    resid = pd.Series(full.iloc[:, 0].values - Xf @ beta, index=full.index)

    cum = resid.cumsum()
    mu = cum.rolling(window).mean()
    sd = cum.rolling(window).std(ddof=1)
    return ((cum - mu) / sd.replace(0.0, np.nan)).reindex(close.index)
