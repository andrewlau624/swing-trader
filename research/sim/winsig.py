"""Window-signal loop (2026-10-07, overnight /loop): shared panel + event-study harness.

Every family is judged the same way (gate frozen in research/drafts/window_signals_loop_2026-10-07.md):
  universe  Sharadar SEP common stocks (delisted included), price >= $5 raw, prior-20d $ADV >= $20M
  signal    computed on the close of day t from bars <= t
  trade     buy the open t+1, sell the close t+H (H = 5 primary; 1/3/10 diagnostic), total return
  excess    minus the equal-weight universe return over the same open t+1 -> close t+H window
  cost      10bp round trip (shock 30bp)
  stats     daily mean series of excess by entry date, Newey-West t (lag H), halves, median, ex-top-5 days
Discovery window 2016-01..2026-09 (touched). Confirm window 2003-2015: one look, survivors only.
Delisted names: the last bar's close is the exit (no delisting return): a small optimistic bias.
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

STORE = pathlib.Path.home() / "data" / "sharadar"
CACHE = pathlib.Path(__file__).resolve().parents[2] / "data" / "research" / "winsig"
HS = (1, 3, 5, 10)
COST, SHOCK = 10e-4, 30e-4
DISC = ("2016-01-01", "2026-09-30")
CONF = ("2003-01-01", "2015-12-31")


LEV = r"(?i)\b(2x|3x|-1x|-2x|-3x|ultra|ultrapro|ultrashort|inverse|short|bear|bull|leveraged|daily|vix|volatility)\b"


def load_panel(lo="2002-06-01", hi="2026-10-05", kind: str = "stock") -> pd.DataFrame:
    """Daily bars sorted (ticker, date) with liquidity flag and forward returns. Cached.
    kind="stock": SEP common stocks. kind="etf": SFP ETFs minus leveraged/inverse (name regex LEV)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / {"stock": "panel.parquet", "etf": "panel_etf.parquet", "cef": "panel_cef.parquet", "pref": "panel_pref.parquet", "adr": "panel_adr.parquet", "reit": "panel_reit.parquet"}[kind]
    if f.exists():
        return pd.read_parquet(f)
    tk = pd.read_parquet(STORE / "tickers.parquet", columns=["table", "ticker", "category", "name", "industry"])
    if kind == "stock":
        common = set(tk[(tk.table == "SEP") & tk.category.fillna("").str.contains("Common Stock")].ticker)
    elif kind == "etf":
        e = tk[(tk.table == "SFP") & (tk.category == "ETF")]
        common = set(e[~e.name.fillna("").str.contains(LEV)].ticker)
    elif kind == "cef":
        common = set(tk[(tk.table == "SFP") & (tk.category == "CEF")].ticker)
    elif kind == "reit":
        common = set(tk[(tk.table == "SEP") & tk.category.fillna("").str.contains("Common Stock")
                        & tk.industry.fillna("").str.startswith("REIT")].ticker)
    elif kind == "adr":
        common = set(tk[(tk.table == "SEP") & tk.category.fillna("").str.startswith("ADR Common Stock")].ticker)
    else:  # $25-par income paper: SEP preferreds + SFP ETD (two source tables, concatenated below)
        common = set(tk[((tk.table == "SEP") & (tk.category == "Domestic Preferred Stock")) | ((tk.table == "SFP") & (tk.category == "ETD"))].ticker)
    cols = ["ticker", "date", "open", "high", "low", "close", "volume", "closeadj", "closeunadj"]
    flt = [("date", ">=", pd.Timestamp(lo)), ("date", "<=", pd.Timestamp(hi))]
    srcs = {"stock": ["stocks"], "etf": ["funds"], "cef": ["funds"], "pref": ["stocks", "funds"], "adr": ["stocks"], "reit": ["stocks"]}[kind]
    t = pd.concat([pq.read_table(STORE / f"{x}.parquet", columns=cols, filters=flt).to_pandas() for x in srcs])
    t = t[t.ticker.isin(common)].dropna(subset=["open", "high", "low", "close", "closeadj", "closeunadj"])
    t = t[(t.close > 0) & (t.open > 0)]
    t["date"] = pd.to_datetime(t["date"])
    t = t.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    for c in ("open", "high", "low", "close", "volume", "closeadj", "closeunadj"):
        t[c] = t[c].astype("float32")
    g = t.groupby("ticker", sort=False)
    dv = (t.closeunadj * t.volume).astype("float32")
    t["adv20"] = dv.groupby(t.ticker, sort=False).transform(lambda s: s.shift(1).rolling(20, min_periods=20).mean())
    t["liq"] = (t.closeunadj >= 5) & (t.adv20 >= {"cef": 1e6, "pref": 2e5, "adr": 1e6, "reit": 1e6}.get(kind, 20e6))
    # entry = open t+1 on the total-return scale; exits = closeadj t+H (or the last bar if the name ends first)
    adjf = t.closeadj / t.close
    entry = (g["open"].shift(-1) * adjf.groupby(t.ticker, sort=False).shift(-1))
    last = g["closeadj"].transform("last")
    for H in HS:
        ex = g["closeadj"].shift(-H)
        has1 = g["close"].shift(-1).notna()
        ex = ex.where(ex.notna() | ~has1, last)
        t[f"f{H}"] = (ex / entry - 1).astype("float32")
    t.to_parquet(f)
    return t


def add_bench(t: pd.DataFrame, uni: str = "liq") -> pd.DataFrame:
    """Equal-weight universe (column `uni`) forward return per date, per horizon -> excess columns x{H}."""
    m = t[uni]
    for H in HS:
        b = t.loc[m].groupby("date")[f"f{H}"].mean()
        t[f"x{H}"] = (t[f"f{H}"] - t["date"].map(b)).astype("float32")
    return t


def nw_t(s: pd.Series, lag: int) -> float:
    x = s.dropna().to_numpy(float)
    n = len(x)
    if n < 30:
        return np.nan
    e = x - x.mean()
    v = e @ e / n
    for k in range(1, lag + 1):
        v += 2 * (1 - k / (lag + 1)) * (e[k:] @ e[:-k]) / n
    return x.mean() / np.sqrt(v / n)


def judge(t: pd.DataFrame, mask: pd.Series, lo: str, hi: str, label: str, primary: int = 5,
          uni: str = "liq", cost: float = COST, shock: float = SHOCK) -> dict:
    sel = t[mask & t[uni] & (t.date >= lo) & (t.date <= hi)]
    out = {"label": label, "n": len(sel), "days": sel.date.nunique()}
    for H in HS:
        x = sel[f"x{H}"].dropna()
        d = x.groupby(sel.loc[x.index, "date"]).mean()
        out[H] = dict(mean=x.mean() * 1e4, net=(x.mean() - cost) * 1e4, med=x.median() * 1e4,
                      t=nw_t(d, H), dmean=d.mean() * 1e4)
    H = primary
    x = sel[f"x{H}"].dropna(); d = x.groupby(sel.loc[x.index, "date"]).mean()
    mid = pd.Timestamp(lo) + (pd.Timestamp(hi) - pd.Timestamp(lo)) / 2
    out["halves"] = (d[d.index < mid].mean() * 1e4, d[d.index >= mid].mean() * 1e4)
    out["ex5"] = d.sort_values().iloc[:-5].mean() * 1e4 if len(d) > 10 else np.nan
    out["shock"] = (x.mean() - shock) * 1e4
    out["hit"] = (x > 0).mean()
    out["per_year"] = len(sel) / max(1, (pd.Timestamp(hi) - pd.Timestamp(lo)).days / 365.25)
    return out


def passes(r: dict, H: int = 5) -> bool:
    p = r[H]
    return (p["net"] >= 25 and p["t"] >= 3.0 and min(r["halves"]) > 0 and p["med"] > 0 and r["ex5"] > 0)


def fmt(r: dict, H: int = 5) -> str:
    cells = "  ".join(f"H{h} {r[h]['mean']:+6.1f} (t {r[h]['t']:+4.1f})" for h in HS)
    p = r[H]
    return (f"{r['label']:44} n {r['n']:6} ({r['per_year']:6.0f}/yr) | {cells} | H{H} net {p['net']:+6.1f} "
            f"med {p['med']:+5.1f} hit {r['hit']:.0%} halves {r['halves'][0]:+5.1f}/{r['halves'][1]:+5.1f} "
            f"ex5 {r['ex5']:+5.1f} shock {r['shock']:+6.1f} -> {'PASS' if passes(r, H) else 'fail'}")


# ---------------------------------------------------------------- indicator helpers (per ticker, vectorized)
def by(t, col):
    return t.groupby("ticker", sort=False)[col]


def ema(t, s: pd.Series, n: int) -> pd.Series:
    return s.groupby(t.ticker, sort=False).transform(lambda x: x.ewm(span=n, adjust=False).mean())


def roll(t, s: pd.Series, n: int, fn: str) -> pd.Series:
    return getattr(s.groupby(t.ticker, sort=False).rolling(n, min_periods=n), fn)().reset_index(level=0, drop=True)


def lag(t, s: pd.Series, k: int = 1) -> pd.Series:
    return s.groupby(t.ticker, sort=False).shift(k)


def run_count(t, cond: pd.Series) -> pd.Series:
    """Consecutive bars (ending at each bar, inclusive) where cond is True, per ticker."""
    c = cond.fillna(False).astype(int)
    grp = (c.groupby(t.ticker, sort=False).transform(lambda x: (x != x.shift()).cumsum()))
    return c.groupby([t.ticker, grp], sort=False).cumsum()
