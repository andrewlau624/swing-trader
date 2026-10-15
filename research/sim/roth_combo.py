"""ROTH-COMBO (N 997): ROTH-STACK book + PREF + a CEF-RV sleeve + a TME sleeve competing for one cash Roth. Pre-reg: round1_prose.md.

    PYTHONPATH=. .venv/bin/python -m research.sim.roth_combo
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

from . import book as B
from .cef_rv import CEF, load_sfp
from .roth_cash import PROBE_USD, nw_t
from .roth_stack import alloc, book_day, load_groups
from .tme_treasury import load as tme_load
from .validate import load_sim

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/roth_combo_out.txt"
SLOTS = 8
CONFIGS = [(0.0, 0.0), (0.25, 0.0), (0.5, 0.0), (0.0, 0.5), (0.25, 0.5), (0.5, 0.5)]
PRIMARY = (0.25, 0.5)


def cef_trades(days: pd.DatetimeIndex) -> tuple[pd.DataFrame, pd.DataFrame]:
    """CEF-RV trades with entry/exit trading days + a daily closeadj matrix (tickers x days)."""
    tr = pd.read_csv(CEF / "cef_rv_trades.csv")
    tr["edate"], tr["xdate"] = pd.to_datetime(tr.edate), pd.to_datetime(tr.xdate)
    tr = tr[(tr.edate >= days[0] - pd.Timedelta(days=7)) & (tr.edate <= days[-1])].copy()
    f = load_sfp(sorted(tr.ticker.unique()), days[0] - pd.Timedelta(days=10), days[-1] + pd.Timedelta(days=30))
    adj = f.pivot_table(index="dt", columns="ticker", values="closeadj")
    raw = f.pivot_table(index="dt", columns="ticker", values="closeunadj")
    ix = adj.index

    def nxt(t, d):
        g = adj[t].dropna()
        k = g.index.searchsorted(d, side="right")
        return g.index[k] if k < len(g) and (g.index[k] - d).days <= 14 else pd.NaT

    tr["ein"] = [nxt(t, d) for t, d in zip(tr.ticker, tr.edate)]
    tr["eout"] = [nxt(t, d) for t, d in zip(tr.ticker, tr.xdate)]
    tr = tr.dropna(subset=["ein", "eout"])
    tr = tr[tr.eout > tr.ein]
    tr["rank"] = tr.disc_in - tr.med
    tr = tr.sort_values(["ein", "rank"]).reset_index(drop=True)
    return tr, adj.reindex(ix), raw.reindex(ix)


def tme_days(days: pd.DatetimeIndex) -> tuple[set, pd.Series]:
    px = tme_load("TLT")["adjclose"]
    r = px.pct_change()
    lock, ret = set(), pd.Series(0.0, index=px.index)
    for _, g in px.groupby(px.index.to_period("M")):
        if len(g) < 8:
            continue
        lock |= set(g.index[-4:-1])          # closes T-3, T-2, T-1: cash held overnight in TLT
        ret.loc[g.index[-3:]] = r.loc[g.index[-3:]]   # returns on T-2, T-1, T
    return lock, ret


def run(s, N, groups, E, f, g, tr, adj, raw, lock, tret, mult=1.0):
    days = pd.DatetimeIndex(s.days)
    pref_rt, cef_side, tme_side = 0.0010 * mult, 0.0025 * mult, 0.0001 * mult
    slots: list[dict] = []
    taken = []
    tot, pnl_cef, pnl_tme = [], [], []
    by_ein = {d: x for d, x in tr.groupby("ein")}
    prev = None
    held_tme = False
    for d in days:
        pc = 0.0
        # mark open CEF slots from prev book day's close to today's close; exits at today's close
        for p in slots:
            a0 = adj.at[prev, p["t"]] if prev is not None and prev in adj.index else np.nan
            a1 = adj.at[d, p["t"]] if d in adj.index else np.nan
            if np.isfinite(a0) and np.isfinite(a1) and p["live"]:
                pc += p["val"] * (a1 / a0 - 1); p["val"] *= a1 / a0
        for p in [p for p in slots if p["out"] <= d]:
            pc -= p["val"] * cef_side
            taken.append((p["t"], p["ein"], p["val"] / p["usd0"] - 1 - 2 * cef_side))
            slots.remove(p)
        for p in slots:
            p["live"] = True
        sleeve = f * E
        if f > 0 and d in by_ein:
            for _, x in by_ein[d].iterrows():
                if len(slots) >= SLOTS:
                    break
                px = raw.at[d, x.ticker] if d in raw.index else np.nan
                if not np.isfinite(px) or px <= 0:
                    continue
                q = np.floor(sleeve / SLOTS / px)
                if q < 1:
                    continue
                usd = q * px
                pc -= usd * cef_side
                slots.append(dict(t=x.ticker, ein=d, out=x.eout, usd0=usd, val=usd, live=False))
        used = sum(p["usd0"] for p in slots)
        b = s.bil.get(d, 0.0); b = float(b) if np.isfinite(b) else 0.0
        pc += max(0.0, sleeve - used) * b if f > 0 else 0.0
        # TME: return on d belongs to cash locked at the previous lock close
        pt = 0.0
        if held_tme and g > 0:
            pt = g * E * float(tret.get(d, 0.0))
        gd = g if (g > 0 and d in lock) else 0.0
        if gd > 0 and not held_tme:
            pt -= g * E * tme_side
        if held_tme and gd == 0:
            pt -= g * E * tme_side
        held_tme = gd > 0
        bpnl, free, _ = book_day(s, N, E * (1 - f - gd), d, 0.5, 0.5, PROBE_USD, "tier", None, False)
        grp = groups.get(d)
        pp = 0.0
        if grp is not None:
            a = alloc(free, grp)
            pp = (a * (grp.co.values - pref_rt)).sum()
        tot.append((bpnl + pp + pc + pt) / E); pnl_cef.append(pc / E); pnl_tme.append(pt / E)
        prev = d
    return pd.Series(tot, days), pd.Series(pnl_cef, days), pd.Series(pnl_tme, days), pd.DataFrame(taken, columns=["t", "ein", "ret"])


def maxdd(x: pd.Series) -> float:
    c = (1 + x).cumprod()
    return float((c / c.cummax() - 1).min())


def main():
    s = load_sim(raw_price=True)
    N = B.night_days(raw_price=True, max_corr=0.7)
    s.N = N
    groups = load_groups()
    days = pd.DatetimeIndex(s.days)
    tr, adj, raw = cef_trades(days)
    lock, tret = tme_days(days)
    yrs = (days[-1] - days[0]).days / 365.25
    h1, h2 = days <= "2023-12-31", days >= "2024-01-01"
    y1 = (days[h1][-1] - days[h1][0]).days / 365.25
    y2 = (days[h2][-1] - days[h2][0]).days / 365.25
    L = ["ROTH-COMBO N 997: ROTH-STACK book (AL1 + PREF STRICT night-first) + CEF-RV sleeve f + TME sleeve g, fixed equity",
         f"book days {days[0].date()}..{days[-1].date()}; CEF-RV trades in window {len(tr)}; TME lock days {len([d for d in days if d in lock])}"]
    print("\n".join(L))
    for E in (3000.0, 10000.0, 25000.0):
        L.append(f"\n== equity ${E:,.0f} ==")
        res = {c: run(s, N, groups, E, *c, tr, adj, raw, lock, tret) for c in CONFIGS}
        res3 = {c: run(s, N, groups, E, *c, tr, adj, raw, lock, tret, mult=3.0) for c in CONFIGS}
        base, base3 = res[(0.0, 0.0)][0], res3[(0.0, 0.0)][0]
        for c in CONFIGS:
            tot, pc, pt, tk = res[c]
            inc = tot - base
            inc3 = res3[c][0] - base3
            tag = "PRIMARY " if c == PRIMARY else ("BASELINE" if c == (0.0, 0.0) else "        ")
            cef = (f" | CEF trades {len(tk)} net {tk.ret.mean()*1e4:+.0f}bp hit {(tk.ret>0).mean()*100:.0f}% sleeve {pc.sum()/yrs*100:+.1f}pp"
                   if len(tk) else "")
            tme = f" | TME {pt.sum()/yrs*100:+.1f}pp" if c[1] > 0 else ""
            L.append(f"{tag} f {c[0]:.2f} g {c[1]:.1f}: total {tot.sum()/yrs*100:+5.1f}%/yr maxDD {maxdd(tot)*100:5.1f}% | inc {inc.sum()/yrs*100:+5.1f}pp "
                     f"halves {inc[h1].sum()/y1*100:+5.1f} / {inc[h2].sum()/y2*100:+5.1f} | 3x {inc3.sum()/yrs*100:+5.1f} | NW t {nw_t(inc):.2f}{cef}{tme}")
        print("\n".join(L[-7:]), flush=True)
    OUT.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
