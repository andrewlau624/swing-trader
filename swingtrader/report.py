"""Performance statistics, benchmarks, and the controls that decide the question.

llm-trader computes max drawdown from cumulative trade PnL, which has no time
axis and therefore cannot yield Sharpe, Sortino or CAGR. These work off a
time-indexed daily equity curve instead.

The headline return is the least informative number in here. What decides
whether this strategy is real is further down: the buy-and-hold control (is
this edge, or just exposure to volatile stocks that went up?), the bootstrap
(can a sample this size support the claim at all?), and the falsification runs.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


# ---------------------------------------------------------------- curve stats
def curve_stats(equity: pd.Series, rf: float = 0.0) -> dict:
    if equity is None or len(equity) < 3:
        return {}
    eq = equity.astype(float)
    # A ruined account makes every ratio meaningless: pct_change across a sign
    # flip produces garbage, and a "Sharpe" computed from it is noise wearing a
    # respectable number. Report the ruin instead of the ratio.
    if (eq <= 0).any():
        first = eq.index[eq <= 0][0]
        return {"start_equity": float(eq.iloc[0]), "end_equity": float(eq.iloc[-1]),
                "RUINED_on": str(pd.Timestamp(first).date()),
                "total_return_pct": -100.0, "cagr_pct": np.nan, "sharpe": np.nan,
                "sortino": np.nan, "max_drawdown_pct": -100.0, "calmar": np.nan,
                "ann_vol_pct": np.nan, "pct_time_underwater": 100.0,
                "years": max((eq.index[-1] - eq.index[0]).days / 365.25, 1e-9)}
    ret = eq.pct_change().dropna()
    years = max((eq.index[-1] - eq.index[0]).days / 365.25, 1e-9)
    total = eq.iloc[-1] / eq.iloc[0] - 1.0
    cagr = (eq.iloc[-1] / eq.iloc[0]) ** (1 / years) - 1.0 if eq.iloc[0] > 0 else np.nan
    vol = ret.std(ddof=1) * np.sqrt(TRADING_DAYS)
    sharpe = ((ret.mean() * TRADING_DAYS) - rf) / vol if vol > 0 else np.nan
    downside = ret[ret < 0].std(ddof=1) * np.sqrt(TRADING_DAYS)
    sortino = ((ret.mean() * TRADING_DAYS) - rf) / downside if downside > 0 else np.nan
    dd = eq / eq.cummax() - 1.0
    maxdd = float(dd.min())
    underwater = float((dd < -0.01).mean())
    return {
        "start_equity": float(eq.iloc[0]), "end_equity": float(eq.iloc[-1]),
        "total_return_pct": total * 100, "cagr_pct": cagr * 100,
        "ann_vol_pct": vol * 100, "sharpe": sharpe, "sortino": sortino,
        "max_drawdown_pct": maxdd * 100,
        "calmar": (cagr / abs(maxdd)) if maxdd < 0 else np.nan,
        "pct_time_underwater": underwater * 100, "years": years,
        # the tail describes a dip-buyer better than any ratio does
        "skew_daily": float(ret.skew()),
        "cvar5_daily_pct": float(ret[ret <= ret.quantile(0.05)].mean() * 100),
        "worst_month_pct": float((eq.resample("ME").last().pct_change().dropna().min()
                                  if len(eq) > 40 else np.nan) * 100),
    }


def trade_stats(trades: list) -> dict:
    if not trades:
        return {"n_trades": 0}
    df = pd.DataFrame([t.to_dict() for t in trades])
    pnl = df["pnl"]
    wins, losses = pnl[pnl > 0], pnl[pnl <= 0]
    gross_w, gross_l = float(wins.sum()), float(abs(losses.sum()))
    return {
        "n_trades": len(df),
        "win_rate_pct": 100.0 * len(wins) / len(df),
        "avg_pnl": float(pnl.mean()),
        "avg_pnl_pct": float(df["pnl_pct"].mean()),
        "avg_win": float(wins.mean()) if len(wins) else 0.0,
        "avg_loss": float(losses.mean()) if len(losses) else 0.0,
        "profit_factor": gross_w / gross_l if gross_l > 0 else np.inf,
        "expectancy": float(pnl.mean()),
        "best": float(pnl.max()), "worst": float(pnl.min()),
        "avg_bars_held": float(df["bars_held"].mean()),
        "total_pnl": float(pnl.sum()),
    }


def exit_breakdown(trades: list) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame()
    df = pd.DataFrame([t.to_dict() for t in trades])
    g = df.groupby("exit_reason")["pnl"].agg(["count", "mean", "sum"])
    g["share_pct"] = 100 * g["count"] / len(df)
    return g.sort_values("count", ascending=False)


def worst_trades(trades: list, n: int = 10) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame()
    df = pd.DataFrame([t.to_dict() for t in trades])
    cols = ["symbol", "side", "entry_date", "exit_date", "entry_px", "exit_px",
            "pnl", "pnl_pct", "bars_held", "exit_reason", "mae"]
    return df.nsmallest(n, "pnl")[cols]


# ---------------------------------------------------------------- bootstrap
def bootstrap_edge(trades: list, n_paths: int = 5000, seed: int = 11) -> dict:
    """P(mean trade <= 0) under iid, block and stationary resampling.

    The original observation was ten trades. Ten trades cannot distinguish a
    real edge from a good run, and this says by how much -- the block and
    stationary variants preserve the serial dependence that iid resampling
    would wish away, so they are the honest ones.
    """
    if len(trades) < 10:
        return {"n": len(trades), "note": "too few trades to bootstrap"}
    x = np.array([t.pnl_pct for t in trades], dtype=float)
    rng = np.random.default_rng(seed)
    n = len(x)
    out: dict = {"n": n, "observed_mean_pct": float(x.mean())}

    def p_le_zero(means):
        return float((np.asarray(means) <= 0).mean())

    out["p_mean_le_0_iid"] = p_le_zero(
        [rng.choice(x, n, replace=True).mean() for _ in range(n_paths)]
    )

    blk = max(2, int(round(n ** (1 / 3))))
    def block_path():
        parts = []
        while sum(len(p) for p in parts) < n:
            i = rng.integers(0, max(1, n - blk))
            parts.append(x[i : i + blk])
        return np.concatenate(parts)[:n]
    out["block_size"] = blk
    out["p_mean_le_0_block"] = p_le_zero([block_path().mean() for _ in range(n_paths // 2)])

    # stationary bootstrap (Politis-Romano), geometric block lengths
    p_geo = 1.0 / blk
    def stat_path():
        idx = np.empty(n, dtype=int)
        i = rng.integers(0, n)
        for j in range(n):
            idx[j] = i
            i = rng.integers(0, n) if rng.random() < p_geo else (i + 1) % n
        return x[idx]
    out["p_mean_le_0_stationary"] = p_le_zero(
        [stat_path().mean() for _ in range(n_paths // 2)]
    )
    return out


def bootstrap_daily(equity: pd.Series, n_paths: int = 2000, mean_block: int = 20,
                    seed: int = 11) -> dict:
    """P(mean daily return <= 0) from a stationary bootstrap of the PORTFOLIO's
    daily returns. Trade-level resampling treats trades open in the same week
    as independent, but they share the market; daily portfolio returns already
    net that out, and 20-day blocks keep volatility clustering intact."""
    r = equity.pct_change().dropna().to_numpy(dtype=float)
    n = len(r)
    if n < 60:
        return {"n_days": n, "note": "too few days to bootstrap"}
    rng = np.random.default_rng(seed)
    p = 1.0 / mean_block
    means, sharpes = np.empty(n_paths), np.empty(n_paths)
    for k in range(n_paths):
        starts = rng.integers(0, n, n)
        new = rng.random(n) < p
        new[0] = True
        # index = start of the current block + offset into it, wrapped
        blk = np.cumsum(new) - 1
        first = np.flatnonzero(new)
        off = np.arange(n) - first[blk]
        idx = (starts[first][blk] + off) % n
        x = r[idx]
        means[k] = x.mean()
        sd = x.std(ddof=1)
        sharpes[k] = x.mean() / sd * np.sqrt(TRADING_DAYS) if sd > 0 else 0.0
    return {"n_days": n, "p_mean_le_0_daily": float((means <= 0).mean()),
            "sharpe_p05": float(np.percentile(sharpes, 5)),
            "sharpe_p50": float(np.percentile(sharpes, 50))}


def deflated_sharpe(equity: pd.Series, n_trials: int) -> dict:
    """Deflated Sharpe ratio (Bailey & Lopez de Prado 2014): the probability
    that the true Sharpe is above zero AFTER allowing for having kept the best
    of `n_trials` configurations. Trials are treated as independent, which
    over-penalises correlated variants of one idea -- read it as a floor.
    n_trials = 1 gives the plain probabilistic Sharpe ratio."""
    from statistics import NormalDist
    nd = NormalDist()
    r = equity.pct_change().dropna().to_numpy(dtype=float)
    t = len(r)
    if t < 60 or r.std(ddof=1) <= 0:
        return {}
    sr = r.mean() / r.std(ddof=1)                      # per day
    g3 = float(pd.Series(r).skew())
    g4 = float(pd.Series(r).kurt()) + 3.0              # pandas reports excess
    n = max(int(n_trials), 1)
    if n > 1:
        em = 0.5772156649
        z = (1 - em) * nd.inv_cdf(1 - 1.0 / n) + em * nd.inv_cdf(1 - 1.0 / (n * np.e))
        sr0 = z / np.sqrt(t)                          # expected max of n null Sharpes
    else:
        sr0 = 0.0
    den = np.sqrt(max(1 - g3 * sr + (g4 - 1) / 4 * sr * sr, 1e-12))
    dsr = float(nd.cdf((sr - sr0) * np.sqrt(t - 1) / den))
    return {"n_trials": n, "sharpe_ann": sr * np.sqrt(TRADING_DAYS),
            "sharpe_hurdle_ann": sr0 * np.sqrt(TRADING_DAYS), "deflated_sharpe_prob": dsr}


def cost_shock(trades: list, extra_bps_list=(0, 2, 4, 6, 10)) -> pd.DataFrame:
    """Re-price every trade under higher slippage. Two sides per round trip."""
    if not trades:
        return pd.DataFrame()
    base = np.array([t.pnl_pct for t in trades], dtype=float)
    rows = []
    for b in extra_bps_list:
        adj = base - 2.0 * b / 100.0  # bps -> pct, entry + exit
        rows.append({"extra_bps": b, "mean_pct": adj.mean(),
                     "total_pct": adj.sum(),
                     "win_rate_pct": 100.0 * (adj > 0).mean()})
    return pd.DataFrame(rows).set_index("extra_bps")


def months_to_significance(trades: list, target_t: float = 2.0,
                           years: float = 1.0) -> float:
    """Months of live trading before the edge is distinguishable from luck.

    Ported from llm-trader's economics.py. Worth knowing BEFORE funding it.
    """
    if len(trades) < 5:
        return float("nan")
    x = np.array([t.pnl_pct for t in trades], dtype=float)
    mu, sd = x.mean(), x.std(ddof=1)
    if mu <= 0 or sd <= 0:
        return float("inf")
    n_needed = (target_t * sd / mu) ** 2
    per_month = len(x) / max(years * 12.0, 1e-9)
    return float(n_needed / per_month) if per_month > 0 else float("inf")


# ---------------------------------------------------------------- benchmarks
def buy_and_hold_candidates(bars: dict, result, equity0: float) -> pd.Series:
    """Equal-weight buy-and-hold of every symbol the scanner ever picked.

    This is the control most likely to kill the strategy. If simply holding
    the names the scanner selected does as well, the timing adds nothing and
    the "edge" was exposure to volatile stocks in a rising market.
    """
    syms = sorted({s for f in result.folds for s in f.candidates})
    if not syms or result.equity.empty:
        return pd.Series(dtype=float)
    idx = result.equity.index
    cols = {}
    for s in syms:
        if s not in bars:
            continue
        c = bars[s]["close"].reindex(idx).ffill()
        if c.notna().sum() > 2:
            cols[s] = c / c.dropna().iloc[0]
    if not cols:
        return pd.Series(dtype=float)
    return pd.DataFrame(cols).mean(axis=1) * equity0


def benchmark(bars: dict, index: pd.DatetimeIndex, symbol: str,
              equity0: float) -> pd.Series:
    if symbol not in bars:
        return pd.Series(dtype=float)
    c = bars[symbol]["close"].reindex(index).ffill().dropna()
    if c.empty:
        return pd.Series(dtype=float)
    return c / c.iloc[0] * equity0


def concurrent_correlation(bars: dict, result) -> dict:
    """Are N positions really N bets, or one bet wearing N tickers?

    The compounding premise in the original idea assumes independence. If the
    selected names move together, position count is an illusion and the real
    drawdown is far worse than the position limit suggests.
    """
    syms = sorted({s for f in result.folds for s in f.candidates})
    rets = {}
    for s in syms:
        if s in bars and len(bars[s]) > 30:
            rets[s] = np.log(bars[s]["close"]).diff()
    if len(rets) < 2:
        return {"n_symbols": len(rets)}
    df = pd.DataFrame(rets).dropna(how="all")
    corr = df.corr(min_periods=30)
    vals = corr.values[np.triu_indices_from(corr.values, k=1)]
    vals = vals[np.isfinite(vals)]
    if not len(vals):
        return {"n_symbols": len(rets)}
    return {
        "n_symbols": len(rets),
        "mean_pairwise_corr": float(np.mean(vals)),
        "median_pairwise_corr": float(np.median(vals)),
        "pct_pairs_over_0_5": float(100.0 * (vals > 0.5).mean()),
    }


# ---------------------------------------------------------------- rendering
def _fmt(d: dict, keys=None) -> str:
    keys = keys or list(d)
    out = []
    for k in keys:
        if k not in d:
            continue
        v = d[k]
        out.append(f"  {k:26} {v:>12.2f}" if isinstance(v, (int, float, np.floating))
                   else f"  {k:26} {v!s:>12}")
    return "\n".join(out)


def render(result, bars: dict, title: str = "run", n_trials: int | None = None) -> str:
    """n_trials: how many configurations were tried before this one was
    picked. Pass it and the report adds the deflated Sharpe ratio."""
    L = [f"{'='*72}", f" {title}", f"{'='*72}"]
    L.append(" config: " + ", ".join(f"{k}={v}" for k, v in result.config.items()))
    L.append("")

    cs = curve_stats(result.equity)
    L.append("-- portfolio " + "-" * 59)
    L.append(_fmt(cs, ["start_equity", "end_equity", "total_return_pct", "cagr_pct",
                       "ann_vol_pct", "sharpe", "sortino", "max_drawdown_pct",
                       "calmar", "pct_time_underwater", "years",
                       "skew_daily", "cvar5_daily_pct", "worst_month_pct"]))
    L.append("")

    ts = trade_stats(result.trades)
    L.append("-- trades " + "-" * 62)
    L.append(_fmt(ts))
    if result.rejected_no_slot:
        L.append(f"  {'signals_dropped_no_slot':26} {result.rejected_no_slot:>12}")
    L.append("")

    eb = exit_breakdown(result.trades)
    if not eb.empty:
        L.append("-- exits " + "-" * 63)
        L.append(eb.to_string(float_format=lambda v: f"{v:10.2f}"))
        L.append("")

    wt = worst_trades(result.trades)
    if not wt.empty:
        L.append("-- worst 10 trades (the tail IS the result in a short-vol strategy) " + "-" * 5)
        L.append(wt.to_string(index=False, float_format=lambda v: f"{v:9.2f}"))
        L.append("")

    L.append("-- controls " + "-" * 60)
    bh = buy_and_hold_candidates(bars, result, result.equity.iloc[0] if len(result.equity) else 100000)
    if len(bh) > 2:
        b = curve_stats(bh)
        L.append(f"  buy&hold same candidates : return {b.get('total_return_pct', float('nan')):8.1f}%  "
                 f"CAGR {b.get('cagr_pct', float('nan')):7.2f}%  sharpe {b.get('sharpe', float('nan')):6.2f}  "
                 f"maxDD {b.get('max_drawdown_pct', float('nan')):7.1f}%")
    spy = benchmark(bars, result.equity.index, "SPY",
                    result.equity.iloc[0] if len(result.equity) else 100000)
    if len(spy) > 2:
        b = curve_stats(spy)
        L.append(f"  SPY buy&hold             : return {b.get('total_return_pct', float('nan')):8.1f}%  "
                 f"CAGR {b.get('cagr_pct', float('nan')):7.2f}%  sharpe {b.get('sharpe', float('nan')):6.2f}  "
                 f"maxDD {b.get('max_drawdown_pct', float('nan')):7.1f}%")
    cc = concurrent_correlation(bars, result)
    if "mean_pairwise_corr" in cc:
        L.append(f"  candidate correlation    : mean {cc['mean_pairwise_corr']:.3f}  "
                 f"median {cc['median_pairwise_corr']:.3f}  "
                 f"{cc['pct_pairs_over_0_5']:.0f}% of pairs > 0.5  "
                 f"(n={cc['n_symbols']})")
    L.append("")

    be = bootstrap_edge(result.trades)
    L.append("-- is the sample big enough to support the claim? " + "-" * 22)
    L.append(_fmt(be))
    yrs = cs.get("years", 1.0) or 1.0
    m2s = months_to_significance(result.trades, years=yrs)
    L.append(f"  {'months_to_significance':26} {m2s:>12.1f}")
    L.append(_fmt(bootstrap_daily(result.equity)))
    if n_trials:
        L.append(_fmt(deflated_sharpe(result.equity, n_trials)))
    L.append("")

    csk = cost_shock(result.trades)
    if not csk.empty:
        L.append("-- cost shock (extra bps per side) " + "-" * 37)
        L.append(csk.to_string(float_format=lambda v: f"{v:10.3f}"))
    return "\n".join(L)
