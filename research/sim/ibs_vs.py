"""Study IBS-VS (pre-reg: research/drafts/round1_prose.md, N 1068 -> 1070).
Vol-scaled GROSS of the IBS sleeve through time vs flat, at matched maxDD; L fit on 2021-26, judged on 2016-20.
Selection is the live code via book.ibs_days; only the sleeve's exposure differs.
Arms: P (g=+1, more capital when the firing names' vol is high), C (g=-1, constant-risk / inverse vol).
Data: Sharadar SFP daily bars (~/data/sharadar/funds.parquet; the local etf_daily.parquet is absent), ends 2026-10-05.
Run: PYTHONPATH=. python3 -m research.sim.ibs_vs"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import book as B
from . import data as D
from .ibs_voltilt import dsr, nw_t

ROOT = pathlib.Path(__file__).resolve().parents[2]
SH = pathlib.Path.home() / "data/sharadar"
OUT = ROOT / "data/research/program/ibs_vs_out.txt"
N_PROG = 1070
RATE = 0.125                       # margin interest on overnight debit (repo assumption)
WIN = {"2016-20 JUDGE": ("2016-01-01", "2020-12-31"), "2021-26 fit": ("2021-01-01", "2026-12-31"),
       "2017-19 ex-2020": ("2017-01-01", "2019-12-31")}
SYMS = list(B.EQ18) + ["BIL"]
rng = np.random.default_rng(11)


def etf_sharadar() -> dict:
    x = pd.read_parquet(SH / "funds.parquet", columns=["ticker", "date", "open", "high", "low", "close", "closeadj"],
                        filters=[("ticker", "in", SYMS)])
    x["date"] = pd.to_datetime(x["date"])
    x = x.drop_duplicates(["ticker", "date"])
    return {f: x.pivot(index="date", columns="ticker", values=f).sort_index()
            for f in ["open", "high", "low", "close", "closeadj"]}


P = etf_sharadar()
D.etf = lambda: P                                  # book.ibs_days reads D.etf()
C = P["close"]
DAYS = C.index
NXT = {a: b for a, b in zip(DAYS[:-1], DAYS[1:])}
BIL = P["closeadj"]["BIL"].pct_change(fill_method=None).shift(-1).fillna(0.0)   # close d -> close d+1
sig = C.pct_change(fill_method=None).rolling(20).std()
Z = sig / sig.rolling(252, min_periods=126).median()
SCALE = C.ffill().iloc[-1] / C                    # 2026 price level for whole-share rounding
I = B.ibs_days()
LEGS = {}
for d, legs in I.items():
    v = [(s, o1, r, Z.at[d, s]) for s, o1, r in legs if np.isfinite(Z.at[d, s]) and abs(r) < 0.5]
    if v:
        LEGS[d] = v
GAP = {}
for d in LEGS:
    j = DAYS.get_loc(d)
    GAP[d] = (DAYS[j + 2] - DAYS[j + 1]).days if j + 2 < len(DAYS) else 1


def sim(g, L, cap, cost_bp=1.0, lo="2016-01-01", hi="2026-12-31", E0=None, zmap=None):
    """Daily sleeve return series (key d). E0=None: fractional shares; else whole shares from E0."""
    c = cost_bp / 1e4
    E = 1.0 if E0 is None else float(E0)
    out = []
    for d in DAYS[(DAYS >= lo) & (DAYS <= hi)]:
        legs = LEGS.get(d)
        pnl, used = 0.0, 0.0
        if legs:
            zs = zmap[d] if zmap is not None else [x[3] for x in legs]
            w = np.array([L * np.clip(z ** g, 0.25, 3.0) / len(legs) for z in zs])
            if w.sum() > cap:
                w *= cap / w.sum()
            for (s, o1, r, _), wi in zip(legs, w):
                px = o1 * SCALE.at[d, s]
                dollars = wi * E if E0 is None else np.floor(wi * E / px) * px
                used += dollars
                pnl += dollars * (r - 2 * c)
            debit = used - E
            if debit > 0:
                pnl -= debit * RATE * GAP[d] / 365
        idle = max(E - used, 0.0)
        pnl += idle * BIL.get(d, 0.0)
        out.append((d, pnl / E))
        E += pnl
    return pd.Series(dict(out))


def stats(r):
    eq = (1 + r).cumprod()
    cagr = eq.iloc[-1] ** (252 / len(r)) - 1
    dd = (eq / eq.cummax() - 1).min()
    sh = r.mean() / r.std() * np.sqrt(252)
    return cagr, dd, sh


def fit_L(g, cap, target_dd):
    lo_, hi_ = 0.05, 4.0
    for _ in range(40):
        m = (lo_ + hi_) / 2
        dd = stats(sim(g, m, cap, lo=WIN["2021-26 fit"][0]))[1]
        lo_, hi_ = (m, hi_) if dd > target_dd else (lo_, m)
    return (lo_ + hi_) / 2


def frontier(cap, lo, hi, cost_bp=1.0):
    pts = []
    for G in np.arange(0.10, 2.0001, 0.05):
        cg, dd, _ = stats(sim(0, G, cap, cost_bp, lo, hi))
        pts.append((-dd, cg))
    pts.sort()
    return np.array(pts)


def excess_at_dd(cg, dd, fr):
    if -dd > fr[-1, 0]:
        return np.nan
    return cg - np.interp(-dd, fr[:, 0], fr[:, 1])


def oversold_block():
    out = ["", "=== Oversold V6 relation (descriptive, no N): SPY/QQQ 3-down or RSI(2)<10 at the close of d ==="]
    O = P["open"]; Hh = P["high"]; Ll = P["low"]
    ibs_days = set(LEGS)
    for s in ("SPY", "QQQ"):
        cl = C[s].dropna()
        rows = []
        for j in range(5, len(cl) - 2):
            d = cl.index[j]
            fire, _ = sg.oversold_trigger(cl.iloc[max(0, j - 30):j].values, cl.iloc[j])
            ibs = (cl.iloc[j] - Ll.at[d, s]) / (Hh.at[d, s] - Ll.at[d, s]) if Hh.at[d, s] > Ll.at[d, s] else np.nan
            n1, n2 = cl.index[j + 1], cl.index[j + 2]
            rows.append((d, fire, ibs, O.at[n1, s] / cl.iloc[j] - 1, O.at[n2, s] / O.at[n1, s] - 1, d in ibs_days))
        x = pd.DataFrame(rows, columns=["d", "fire", "ibs", "c2o", "o2o", "leg"]).set_index("d")
        for nm, (lo, hi) in (("2016-20", WIN["2016-20 JUDGE"]), ("2021-26", WIN["2021-26 fit"])):
            y = x.loc[lo:hi]; f = y[y.fire]; ib = y[y.ibs < 0.2]
            out.append(f"{s} {nm}: trigger days {len(f)} | of them index IBS<0.2 {np.mean(f.ibs < 0.2)*100:3.0f}%, "
                       f"IBS-leg fires {f.leg.mean()*100:3.0f}% | trigger c->o {f.c2o.mean()*1e4:5.1f}bp "
                       f"(med {f.c2o.median()*1e4:5.1f}) next o->o {f.o2o.mean()*1e4:5.1f}bp | "
                       f"index IBS<0.2 days {len(ib)}: c->o {ib.c2o.mean()*1e4:5.1f}bp o->o {ib.o2o.mean()*1e4:5.1f}bp | "
                       f"P(trigger | index IBS<0.2) {ib.fire.mean()*100:3.0f}%")
    return out


def main():
    L = []
    log = L.append
    nsig = {k: sum(1 for d in LEGS if lo <= str(d.date()) <= hi) for k, (lo, hi) in WIN.items()}
    log(f"Study IBS-VS  data {DAYS.min().date()}..{DAYS.max().date()}  signal days {nsig}  program N {N_PROG}")
    zall = np.array([x[3] for v in LEGS.values() for x in v])
    log(f"z = sigma20/median252: p10 {np.percentile(zall,10):.2f} p50 {np.median(zall):.2f} p90 {np.percentile(zall,90):.2f}")
    res = {}
    for ver, cap, G0 in (("TAXABLE cap 2.0, flat 1.25x", 2.0, 1.25), ("ROTH cap 1.0, flat 1.0x", 1.0, 1.0)):
        log(f"\n######## {ver}")
        tdd = stats(sim(0, G0, cap, lo=WIN["2021-26 fit"][0]))[1]
        Ls = {"flat": G0, "P g=+1": fit_L(1, cap, tdd), "C g=-1": fit_L(-1, cap, tdd)}
        gs = {"flat": 0, "P g=+1": 1, "C g=-1": -1}
        log(f"target 2021-26 maxDD {tdd*100:.1f}%  fitted L: " + ", ".join(f"{k} {v:.3f}" for k, v in Ls.items()))
        for cost in (1.0, 2.0, 3.0):
            log(f"-- cost {cost:g}bp/side (fractional shares): CAGR / maxDD / Sharpe ; excess CAGR vs flat frontier at same maxDD")
            for wn, (lo, hi) in WIN.items():
                fr = frontier(cap, lo, hi, cost)
                parts = []
                for a in Ls:
                    cg, dd, sh = stats(sim(gs[a], Ls[a], cap, cost, lo, hi))
                    ex = excess_at_dd(cg, dd, fr) if a != "flat" else 0.0
                    parts.append(f"{a}: {cg*100:5.1f}%/{dd*100:5.1f}%/{sh:4.2f} ex {ex*100:+5.2f}pp")
                    res[(ver, cost, wn, a)] = (cg, dd, sh, ex)
                log(f"  {wn:16s} " + " | ".join(parts))
        # paired tests on the judge window, 1bp and 3bp
        for cost in (1.0, 3.0):
            lo, hi = WIN["2016-20 JUDGE"]
            rf = sim(0, G0, cap, cost, lo, hi)
            for a in ("P g=+1", "C g=-1"):
                ra = sim(gs[a], Ls[a], cap, cost, lo, hi)
                k = ra.std() / rf.std()
                dd_ = ra - k * rf
                sd = dd_[[d in LEGS for d in dd_.index]]
                ex5 = dd_.sort_values().iloc[:-5].mean()
                log(f"  paired {a} {cost:g}bp 2016-20: mean d {dd_.mean()*1e4:+.2f}bp/day NW t {nw_t(dd_.values):+.2f} "
                    f"ex-top5 {ex5*1e4:+.2f} | signal days n {len(sd)} median {sd.median()*1e4:+.2f}bp hit {(sd>0).mean()*100:.0f}% "
                    f"| DSR(N={N_PROG}) {dsr(ra.values, N_PROG):.3f}")
        # placebo: permute z across all (day, name) slots; Sharpe rank on 2016-20, 1bp
        lo, hi = WIN["2016-20 JUDGE"]
        keys = [d for d in LEGS if lo <= str(d.date()) <= hi]
        flatz = np.array([x[3] for d in keys for x in LEGS[d]])
        for a in ("P g=+1", "C g=-1"):
            sh0 = stats(sim(gs[a], Ls[a], cap, 1.0, lo, hi))[2]
            shs = []
            for _ in range(200):
                pz = rng.permutation(flatz); i = 0; zm = {}
                for d in keys:
                    n = len(LEGS[d]); zm[d] = pz[i:i + n]; i += n
                shs.append(stats(sim(gs[a], Ls[a], cap, 1.0, lo, hi, zmap=zm))[2])
            log(f"  placebo {a}: Sharpe {sh0:.3f} rank {np.mean(np.array(shs) < sh0)*100:.0f}th pct of 200 (median {np.median(shs):.3f})")
        # whole shares at 2026 price levels
        log("-- whole shares (2026 price level), 1bp/side: CAGR / maxDD per window")
        for E0 in (2300, 10000, 25000, 100000):
            for wn in ("2016-20 JUDGE", "2021-26 fit"):
                lo, hi = WIN[wn]
                parts = []
                for a in Ls:
                    cg, dd, _ = stats(sim(gs[a], Ls[a], cap, 1.0, lo, hi, E0=E0))
                    parts.append(f"{a} {cg*100:5.1f}%/{dd*100:5.1f}%")
                log(f"  ${E0:>7,} {wn:14s} " + " | ".join(parts))
    L += oversold_block()
    text = "\n".join(L) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
