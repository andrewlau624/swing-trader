"""Monthly momentum sleeve: PAPER SHADOW ONLY (Lab-BT passed on 1963-2015 history with a faded modern era; Lab-BR's
rule). Logs the picks each month and their realised return vs the universe. Places no orders.

Rule (Lab-BR): universe = common stock, raw close >= $5 at the last completed month, top 500 by trailing-12-month
dollar volume; score = close(m-2) / close(m-13) - 1 on adjusted monthly closes; hold the top 20 equal weight from the
last month-end close to the next.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pandas as pd

from .settings import STATE

TOP, UNIV = 20, 500
LOG = STATE / "momentum-shadow.jsonl"
# Lab-BX's fixed industry-ETF list (Lab Round 46): one liquid US ETF per industry; top 5 by 12-1 momentum
INDUSTRY_ETFS = ["XBI", "XHB", "XRT", "KRE", "KIE", "XME", "XOP", "OIH", "SMH", "IGV", "ITA", "IYT", "XPH", "IHI", "XHS",
                 "GDX", "IYR", "IYZ", "JETS", "TAN"]
INDUSTRY_LOG = STATE / "industry-momentum-shadow.jsonl"


def industry_picks(C: pd.DataFrame, last: str, etfs=INDUSTRY_ETFS, top: int = 5) -> list:
    """Top `top` ETFs by 12-1 momentum as of the completed month `last` (Lab-BX's rule)."""
    k = C.index.get_loc(last)
    if k < 12:
        return []
    score = (C.iloc[k - 1] / C.iloc[k - 12] - 1)[[e for e in etfs if e in C.columns]].dropna()
    return list(score.sort_values(ascending=False).index[:top])


def picks(C: pd.DataFrame, V: pd.DataFrame, RAW: pd.DataFrame, last: str, top: int = TOP, univ: int = UNIV) -> tuple[list, list]:
    """(picks, universe) for the month after `last` (the last completed month), from monthly frames indexed by 'YYYY-MM'."""
    k = C.index.get_loc(last)
    if k < 12:
        return [], []
    dv = (C * V).iloc[max(0, k - 11):k + 1].mean()
    ok = RAW.loc[last][RAW.loc[last] >= 5].index
    u = list(dv[ok].dropna().sort_values(ascending=False).index[:univ])
    score = (C.iloc[k - 1] / C.iloc[k - 12] - 1)[u].dropna()
    return list(score.sort_values(ascending=False).index[:top]), u


def vol_weight(rows, target: float = 0.12, months: int = 6) -> float | None:
    """Lab-BU's crash control, REPORTED only: min(1, 12% / annualised vol of the shadow's last 6 scored monthly
    excess returns). None until 6 months are scored. (Lab-BU missed its bar by 0.02 Sharpe in 1963-89 but halved the
    worst 12-month crash; see study_lab_bt_momentum_history.md.)"""
    ex = [r["realised"]["picks"] - r["realised"]["universe"] for r in rows if r.get("realised")][-months:]
    if len(ex) < months:
        return None
    import statistics
    vol = statistics.stdev(ex) * (12 ** 0.5)
    return round(min(1.0, target / vol), 3) if vol > 0 else 1.0


def trend_on(last: str) -> bool | None:
    """Lab-BY's crash filter, REPORTED only: SPY's month-end close above its 10-month average at `last`."""
    try:
        x = _monthly(["SPY"], "all", months_back=13)
        c = x.set_index("month").close.sort_index()
        c = c[c.index <= last]
        return bool(c.iloc[-1] > c.iloc[-10:].mean()) if len(c) >= 10 else None
    except Exception:
        return None


def _monthly(symbols, adjustment, months_back=15):
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
    from swingtrader.data import _clients
    data, _ = _clients()
    start = (pd.Timestamp.now(tz="UTC") - pd.DateOffset(months=months_back)).normalize()
    end = pd.Timestamp.now(tz="UTC") - pd.Timedelta(minutes=16)
    parts = []
    for i in range(0, len(symbols), 500):
        df = data.get_stock_bars(StockBarsRequest(symbol_or_symbols=symbols[i:i + 500], timeframe=TimeFrame(1, TimeFrameUnit.Month),
                                                  start=start, end=end, feed="sip", adjustment=adjustment)).df
        if df is not None and len(df):
            parts.append(df.reset_index())
    x = pd.concat(parts)
    x["month"] = x.timestamp.dt.tz_convert("America/New_York").dt.strftime("%Y-%m")
    return x


def run_industry(log: Path = INDUSTRY_LOG) -> int:
    """Industry-ETF momentum PAPER SHADOW (Lab-BW passed 1963-2015; Lab-BX's ETF version tied SPY in 2017-26)."""
    adj = _monthly(INDUSTRY_ETFS + ["SPY"], "all")
    C = adj.pivot_table(index="month", columns="symbol", values="close")
    this = dt.date.today().strftime("%Y-%m")
    last = [m for m in C.index if m < this][-1]
    R = C / C.shift(1) - 1
    rows = [json.loads(x) for x in log.read_text().splitlines() if x.strip()] if log.exists() else []
    for r in rows:
        if r.get("realised") is None and r["hold_month"] in R.index and r["hold_month"] < this:
            m = r["hold_month"]
            r["realised"] = {"picks": float(R.loc[m, r["picks"]].mean()), "spy": float(R.loc[m, "SPY"])}
    nxt = (pd.Period(last, "M") + 1).strftime("%Y-%m")
    if not any(r["hold_month"] == nxt for r in rows):
        rows.append({"decided": dt.date.today().isoformat(), "signal_month": last, "hold_month": nxt,
                     "picks": industry_picks(C, last), "realised": None, "mode": "paper shadow (no orders)"})
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("".join(json.dumps(r) + "\n" for r in rows))
    print(f"industry momentum shadow: holding {nxt}: {rows[-1]['picks']}")
    return 0


def run(log: Path = LOG) -> int:
    from .research.as_replay import universe
    syms = universe()
    adj, raw = _monthly(syms, "all"), _monthly(syms, "raw")
    C = adj.pivot_table(index="month", columns="symbol", values="close")
    V = adj.pivot_table(index="month", columns="symbol", values="volume")
    RAW = raw.pivot_table(index="month", columns="symbol", values="close").reindex(index=C.index, columns=C.columns)
    this = dt.date.today().strftime("%Y-%m")
    done = [m for m in C.index if m < this]                 # completed months only
    last = done[-1]
    rows = [json.loads(x) for x in log.read_text().splitlines() if x.strip()] if log.exists() else []
    R = C / C.shift(1) - 1
    for r in rows:                                          # score held months that have completed
        if r.get("realised") is None and r["hold_month"] in R.index and r["hold_month"] < this:
            m = r["hold_month"]
            r["realised"] = {"picks": float(R.loc[m, r["picks"]].fillna(0).mean()),
                             "universe": float(R.loc[m, r["universe"]].mean(skipna=True))}
    nxt = (pd.Period(last, "M") + 1).strftime("%Y-%m")
    if not any(r["hold_month"] == nxt for r in rows):
        p, u = picks(C, V, RAW, last)
        rows.append({"decided": dt.date.today().isoformat(), "signal_month": last, "hold_month": nxt,
                     "picks": p, "universe": u, "realised": None, "mode": "paper shadow (no orders)",
                     "vol_scaled_weight": vol_weight(rows), "trend_filter_on": trend_on(last)})
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("".join(json.dumps(r) + "\n" for r in rows))
    scored = [r for r in rows if r.get("realised")]
    print(f"momentum shadow: holding {nxt}: {rows[-1]['picks']}")
    if scored:
        ex = [r["realised"]["picks"] - r["realised"]["universe"] for r in scored]
        print(f"  scored months {len(scored)}: mean excess {sum(ex) / len(ex) * 1e4:+.0f}bp/month")
    return 0
