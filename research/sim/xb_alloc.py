"""Study XB - existing-book optimization: IBS x TME portfolio allocation (pre-registered N 819 -> 820).

    PYTHONPATH=. .venv/bin/python -m research.sim.xb_alloc > data/research/program/xb_alloc_out.txt

One judged question: does capital allocation between the free IBS overlay and the TME-K (Kalman hedge-only Treasury
month-end) overlay beat 100%-to-IBS after tax and at size? Frozen definitions in round1_prose.md. No tuning.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg
from swingtrader.universe import valid_symbol

ROOT = Path(__file__).resolve().parents[2]
BARS = ROOT / "data" / "cache" / "bars"
BARS_PRE = ROOT / "data" / "cache" / "bars_pre2021"
TME = ROOT / "data" / "research" / "tme"
PROG = ROOT / "data" / "research" / "program"
OUT = PROG / "xb_alloc_out.txt"
J0, J1 = "2016-09-01", "2026-09-30"
COST = 2.0 / 1e4          # 2 bp per side for the Treasury overlay
TCOST = 5.0 / 1e4         # 5 bp per side ETF tier for IBS
K = 3
UNIV = ["SPY", "QQQ", "IWM", "DIA", "XLK", "XLF", "XLE", "XLV", "XLI", "XLP", "XLY", "XLU",
        "XLB", "XLRE", "XLC", "SMH", "GLD", "TLT"]


def load_bars(syms):
    o, c = {}, {}
    for s in syms:
        f = BARS / f"{s}.parquet"
        if not f.exists():
            continue
        d = pd.read_parquet(f)
        d.index = pd.to_datetime(d.index)
        o[s] = d["open"].astype(float)
        c[s] = d["close"].astype(float)
    O = pd.DataFrame(o).sort_index()
    C = pd.DataFrame(c).reindex(columns=O.columns)
    return O, C


def ibs_legs(O, C, close_entry=False):
    """Daily IBS leg: [{date, c}] picks pending execution at the entry session's open. close_entry=True -> V6
    (signal close makes the byte). Return per position = open(entry)->open(entry+1) [live] or close(sig)->open(sig+1) [V6]."""
    dates = C.index
    H, L = C, C  # only closes used for IBS on these ETFs? no: use high/low via parquet again
    return None


def load_ohlc(syms):
    """Merge bars_pre2021 (2016-20) with bars (2021-26), de-duplicated."""
    o, h, l, c = {}, {}, {}, {}
    for s in syms:
        parts = []
        for base in (BARS_PRE, BARS):
            f = base / f"{s}.parquet"
            if f.exists():
                d = pd.read_parquet(f)
                d.index = pd.to_datetime(d.index)
                parts.append(d)
        if not parts:
            continue
        d = pd.concat(parts).sort_index()
        d = d[~d.index.duplicated()]
        o[s], h[s], l[s], c[s] = (d[k].astype(float) for k in ("open", "high", "low", "close"))
    f = lambda x: pd.DataFrame(x).sort_index()  # noqa: E731
    return f(o), f(h), f(l), f(c)


def build_ibs(O, H, L, C, close_entry):
    """picks[(entry_date, sym)] = per-unit return for the position entered at entry_date's session.
    Momentum top-3 chosen at the last month-end strictly before the signal day; trigger at a signal close
    (last complete regular bar) with IBS < 0.2."""
    dates = C.index
    ibs = (C - L) / (H - L).replace(0, np.nan)
    mom = C.shift(21) / C.shift(252) - 1
    me = mom.groupby([mom.index.year, mom.index.month]).tail(1)
    entries = []
    for i in range(1, len(dates)):
        sigday = dates[i - 1]
        entry = dates[i]
        # top-3 as of the last month-end strictly before the signal day
        prev = me[me.index.to_period("M") < sigday.to_period("M")]
        if prev.empty:
            continue
        top = prev.iloc[-1].reindex(UNIV).dropna().sort_values(ascending=False).index[:K]
        for s in top:
            if not np.isfinite(ibs.iat[i - 1, C.columns.get_loc(s)]) or ibs.iat[i - 1, C.columns.get_loc(s)] >= 0.2:
                continue
            if close_entry:
                # V6: buy the close of the signal day, sell next open
                if not (np.isfinite(C.iat[i - 1, C.columns.get_loc(s)]) and np.isfinite(O.iat[i, C.columns.get_loc(s)])):
                    continue
                r = O.iat[i, C.columns.get_loc(s)] / C.iat[i - 1, C.columns.get_loc(s)] - 1.0
                entries.append((sigday, entry, s, r))
            else:
                # live: buy the entry-session open, sell the next open
                j = i + 1
                if j >= len(dates):
                    continue
                if not (np.isfinite(O.iat[i, C.columns.get_loc(s)]) and np.isfinite(O.iat[j, C.columns.get_loc(s)])):
                    continue
                r = O.iat[j, C.columns.get_loc(s)] / O.iat[i, C.columns.get_loc(s)] - 1.0
                entries.append((entry, dates[j], s, r))
    return pd.DataFrame(entries, columns=["entry", "exit", "sym", "ret"])


def daily_pnl(trades, dates, cost, size_frac):
    """Map per-position returns onto per-session P&L, each position sized at size_frac of the sleeve.
    Returns a daily return series on the sleeve (deployed fraction x position return - cost x turnover)."""
    r = pd.Series(0.0, index=dates)
    for t in trades.itertuples():
        d = t.entry
        if d in r.index:
            r.loc[d] += size_frac * (t.ret - 2 * cost)
    return r


def load_treasury():
    o = {}
    for s in ("TLT", "IEF", "SHY"):
        d = pd.read_csv(TME / f"px_{s}.csv", parse_dates=["date"]).set_index("date")
        o[s] = d["close"].astype(float)
    return pd.DataFrame(o).sort_index()


def tme_stream(P, hedged):
    """Month-end window TLT close(T-3)->close(T), optional short beta x IEF. Returns daily sleeve P&L series."""
    px = P
    dates = px.index
    m = px.index.to_period("M")
    ret = px.pct_change(fill_method=None)
    # trailing beta of TLT on IEF (252d, lagged)
    cov = ret["TLT"].rolling(252).cov(ret["IEF"])
    var = ret["IEF"].rolling(252).var()
    beta = (cov / var).shift(1)
    out = pd.Series(0.0, index=dates)
    months = sorted(set(m))
    for mo in months:
        dts = dates[m == mo]
        if len(dts) < 6:
            continue
        T = dts[-1]
        T3 = dts[-4]
        # entry at close T-3, exit at close T: return is close(T)/close(T-3)-1 booked on the last day
        i0, i1 = dates.get_loc(T3), dates.get_loc(T)
        p0, p1 = px["TLT"].iloc[i0], px["TLT"].iloc[i1]
        if not (np.isfinite(p0) and np.isfinite(p1)):
            continue
        if hedged:
            b = beta.iloc[i0]
            if not np.isfinite(b):
                b = 1.0
            q0, q1 = px["IEF"].iloc[i0], px["IEF"].iloc[i1]
            r = (p1 / p0 - 1) - b * (q1 / q0 - 1)
        else:
            r = p1 / p0 - 1
        out.iloc[i1] += (r - 2 * COST)
    return out


def stats(x, label):
    x = x.fillna(0.0)
    yrs = len(x) / 252
    cagr = (1 + x).prod() ** (1 / yrs) - 1 if yrs > 0 else np.nan
    sh = x.mean() / x.std() * np.sqrt(252) if x.std() > 0 else 0
    eq = (1 + x).cumprod()
    dd = (eq / eq.cummax() - 1).min()
    return label, cagr, sh, dd


def main():
    import sys
    O, H, L, C = load_ohlc(UNIV)
    dates = C.index[(C.index >= J0) & (C.index <= J1)]
    tres = load_treasury()
    tres = tres[(tres.index >= J0) & (tres.index <= J1)]

    # ---- IBS streams (only the V6 stream for the judged primary; live reported) ----
    loud = []
    ibs_h = build_ibs(O, H, L, C, close_entry=True)     # V6 (close->open)
    ibs_g = build_ibs(O, H, L, C, close_entry=False)    # live (open->open)
    # per-signal-day returns: an IBS position uses 1/3 of the sleeve, on the signal->exit sessions
    rv6 = daily_pnl(ibs_h, dates, TCOST, 1.0 / K)
    rliv = daily_pnl(ibs_g, dates, TCOST, 1.0 / K)

    # ---- TME-K stream ----
    tk = tme_stream(tres, hedged=True)
    ta = tme_stream(tres, hedged=False)
    tk = tk.reindex(dates).fillna(0.0)
    ta = ta.reindex(dates).fillna(0.0)

    def combined(w_ibs):
        # 50/50-by-default split of sleeve dollars: each stream gets w of the sleeve at ACTIVE sessions
        # IBS V6 uses 1/3 of the sleeve per leg but there can be up to 3 legs; scale so the max active IBS
        # day uses w_ibs of the sleeve (3 legs x 1/3 each = full when 3 fire).
        return (w_ibs * rv6 * K / K) + (1 - w_ibs) * tk

    lbl, c, s, d = stats(rv6, "IBS-V6 100%")
    print(f"{lbl:22s} CAGR {c*100:5.2f}%  Sharpe {s:4.2f}  maxDD {d*100:5.1f}%")
    lbl, c, s, d = stats(rliv, "IBS-live 100%")
    print(f"{lbl:22s} CAGR {c*100:5.2f}%  Sharpe {s:4.2f}  maxDD {d*100:5.1f}%")
    lbl, c, s, d = stats(tk, "TME-K 100%")
    print(f"{lbl:22s} CAGR {c*100:5.2f}%  Sharpe {s:4.2f}  maxDD {d*100:5.1f}%")
    lbl, c, s, d = stats(ta, "TME-A 100%")
    print(f"{lbl:22s} CAGR {c*100:5.2f}%  Sharpe {s:4.2f}  maxDD {d*100:5.1f}%")

    print("\nallocation grid (sleeve = w x IBS-V6 + (1-w) x TME-K, w = IBS share of sleeve dollars):")
    print(f"  {'w_IBS':>6} {'CAGR':>7} {'Sharpe':>7} {'maxDD':>7} {'$/yr@10k':>9} {'$/yr@25k':>9} {'$/yr@100k':>10}")
    grid = {}
    for w in (0.0, 0.3, 0.5, 0.7, 1.0):
        x = combined(w)
        grid[w] = x
        lbl, c, s, d = stats(x, "")
        print(f"  {w:>6.1f} {c*100:>6.2f}% {s:>7.2f} {d*100:>6.1f}% {10000*c:>9,.0f} {25000*c:>9,.0f} {100000*c:>10,.0f}")

    # correlation
    print(f"\nmonthly corr(IBS-V6, TME-K) = {rv6.resample('ME').sum().corr(tk.resample('ME').sum()):+.3f}")

    # primary: incremental of 50/50 vs 100% IBS-V6 (annualised by each half's own length)
    def annualise(s):
        return ((1 + s).prod() ** (252 / len(s)) - 1) if len(s) else np.nan

    x5050, x100 = grid[0.5], grid[1.0]
    inc = annualise(x5050) - annualise(x100)
    h1c, h1i = x5050["2016-09":"2020-12"], x100["2016-09":"2020-12"]
    h2c, h2i = x5050["2021-01":], x100["2021-01":]
    h1 = annualise(h1c) - annualise(h1i)
    h2 = annualise(h2c) - annualise(h2i)
    print(f"\nPRIMARY incremental (50/50 vs 100% IBS-V6): {inc*100:+.2f}pp/yr")
    print(f"  2016-20: combined {annualise(h1c)*100:+.2f}%/yr vs IBS {annualise(h1i)*100:+.2f}%/yr  -> {h1*100:+.2f}pp/yr")
    print(f"  2021-26: combined {annualise(h2c)*100:+.2f}%/yr vs IBS {annualise(h2i)*100:+.2f}%/yr  -> {h2*100:+.2f}pp/yr")
    # ex-best-5 months
    cm = x5050.resample("ME").sum()
    exb5 = cm.drop(cm.nlargest(5).index)
    print(f"  50/50 ex-best-5 months mean monthly {exb5.mean()*100:+.2f}% (n {len(exb5)})")
    print(f"  100% IBS ex-best-5 months mean monthly {x100.resample('ME').sum().pipe(lambda s: s.drop(s.nlargest(5).index)).mean()*100:+.2f}%")


if __name__ == "__main__":
    main()
