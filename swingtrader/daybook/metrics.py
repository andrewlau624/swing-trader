"""Performance reporting for the intraday day book."""
from __future__ import annotations

import numpy as np
import pandas as pd


def _ann(daily: pd.Series, ppy: int = 252):
    x = daily.dropna()
    if len(x) == 0:
        return dict(n=0)
    mu, sd = x.mean(), x.std(ddof=1)
    t = mu / (sd / np.sqrt(len(x))) if sd > 0 else np.nan
    sh = mu / sd * np.sqrt(ppy) if sd > 0 else np.nan
    eq = (1 + x).cumprod()
    dd = (eq / eq.cummax() - 1).min()
    yrs = len(x) / ppy
    cagr = eq.iloc[-1] ** (1 / yrs) - 1 if eq.iloc[-1] > 0 else -1.0
    active = x[x != 0]
    return dict(n=len(x), active=len(active), mean_bp=mu * 1e4, t=t, sharpe=sh,
                cagr=cagr, maxdd=dd, worst_day=x.min(), best_day=x.max(),
                win=(active > 0).mean() if len(active) else np.nan)


def line(label: str, d: dict) -> str:
    if d.get("n", 0) == 0:
        return f"{label:28s} no data"
    return (f"{label:28s} days {d['n']:4d} act {d['active']:4d}  mean {d['mean_bp']:+6.2f}bp  "
            f"t {d['t']:+5.2f}  Sh {d['sharpe']:+5.2f}  CAGR {d['cagr']*100:+6.1f}%  "
            f"maxDD {d['maxdd']*100:6.1f}%  worstD {d['worst_day']*100:+6.2f}%")


def annual_dollars(cagr: float, sizes=(1000, 2500, 5000, 10000, 25000, 100000)) -> str:
    return "  ".join(f"${s/1000:.1f}k:${cagr*s:+,.0f}" for s in sizes)


def year_by_year(daily: pd.Series) -> pd.DataFrame:
    x = daily.dropna()
    g = x.groupby(x.index.year)
    rows = []
    for y, v in g:
        a = _ann(v)
        rows.append(dict(year=y, days=a["n"], mean_bp=a["mean_bp"], t=a["t"],
                         sharpe=a["sharpe"], cagr=a["cagr"], maxdd=a["maxdd"]))
    return pd.DataFrame(rows)


def worst_week(daily: pd.Series) -> float:
    return daily.dropna().resample("W").apply(lambda x: (1 + x).prod() - 1).min()


def robustness(daily: pd.Series, label: str = ""):
    x = daily.dropna()
    base = x.mean()
    sort = x.sort_values()
    out = [f"  {label} gross-mean {base*1e4:+.2f}bp"]
    out.append(f"  50% haircut: {base*0.5*1e4:+.2f}bp")
    for k in (1, 5, 10):
        v = sort.iloc[: len(sort) - k].mean() if len(sort) > k else np.nan
        out.append(f"  ex-best{k}: {v*1e4:+.2f}bp")
    return "\n".join(out)
