"""Study VT-IBS (pre-reg: research/drafts/round1_prose.md, N 836 -> 838).
Vol-proportional (g=+1) vs inverse-vol (g=-1) split of the IBS budget across simultaneous names.
Selection is the live code via book.ibs_days (signals.momentum_top / ibs_targets); only the weights differ.
Run: PYTHONPATH=. .venv/bin/python -m research.sim.ibs_voltilt"""
from __future__ import annotations
import pathlib
import numpy as np
import pandas as pd
from scipy.stats import norm, skew, kurtosis
from . import book as B, data as D

OUT = pathlib.Path(__file__).with_name("ibs_voltilt_out.txt")
N_PROG = 838
rng = np.random.default_rng(7)


def build():
    I = B.ibs_days()
    C = D.etf()["close"]
    sig = C.pct_change().rolling(20).std()          # known at close of d
    rows = {}
    for d, legs in I.items():
        rows[d] = [(s, r, sig.at[d, s]) for s, _, r in legs if np.isfinite(sig.at[d, s])]
    return {d: v for d, v in rows.items() if v}


def day_ret(legs, g, cost, perm=None):
    s = np.array([x[2] for x in legs]); r = np.array([x[1] for x in legs])
    w = s ** g; w = w / w.sum()
    if perm is not None:
        w = w[perm]
    return float(w @ r - 2 * cost)


def nw_t(x, L=5):
    x = np.asarray(x); n = len(x); m = x.mean(); e = x - m
    v = e @ e / n
    for l in range(1, L + 1):
        v += 2 * (1 - l / (L + 1)) * (e[l:] @ e[:-l]) / n
    return m / np.sqrt(v / n)


def dsr(x, N):
    x = np.asarray(x); T = len(x)
    sr = x.mean() / x.std()
    em = 0.5772156649
    sr0 = np.sqrt(1 / T) * ((1 - em) * norm.ppf(1 - 1 / N) + em * norm.ppf(1 - 1 / (N * np.e)))
    den = np.sqrt(1 - skew(x) * sr + (kurtosis(x, fisher=False) - 1) / 4 * sr ** 2)
    return norm.cdf((sr - sr0) * np.sqrt(T - 1) / den)


def main():
    R = build()
    days = sorted(R)
    lines = [f"Study VT-IBS: signal days {len(days)}, multi-name {sum(len(R[d])>1 for d in days)}"]
    halves = {"2016-20 (JUDGE)": ("2016", "2020"), "2021-26": ("2021", "2026"),
              "2017-19 ex-2020": ("2017", "2019")}
    for cost_bp in (1.0, 3.0):
        cost = cost_bp / 1e4
        lines.append(f"\n=== cost {cost_bp}bp/side ===")
        idx = pd.DatetimeIndex(days)
        eq = pd.Series([day_ret(R[d], 0, cost) for d in days], index=idx)
        for g, lab in ((1, "A g=+1 vol-prop"), (-1, "B g=-1 inv-vol")):
            arm = pd.Series([day_ret(R[d], g, cost) for d in days], index=idx)
            multi = pd.Series([len(R[d]) > 1 for d in days], index=idx)
            for hn, (a, b) in halves.items():
                sl = slice(a, b)
                diff = (arm - eq)[multi].loc[sl]
                if len(diff) < 20:
                    continue
                ex5 = diff.sort_values().iloc[:-5].mean()
                lines.append(f"{lab:18s} {hn:16s} multi n={len(diff):3d} paired mean={diff.mean()*1e4:6.2f}bp "
                             f"med={diff.median()*1e4:6.2f} hit={(diff>0).mean()*100:3.0f}% t={diff.mean()/diff.std()*np.sqrt(len(diff)):5.2f} "
                             f"NWt={nw_t(diff):5.2f} ex5={ex5*1e4:6.2f}bp")
                a_all, e_all = arm.loc[sl], eq.loc[sl]
                lines.append(f"{'':18s} {'':16s} all signal days n={len(a_all)}: growth arm {np.log1p(a_all).mean()*1e4:6.2f} vs eq "
                             f"{np.log1p(e_all).mean()*1e4:6.2f} bp/day; Sharpe/day arm {a_all.mean()/a_all.std():.4f} vs eq {e_all.mean()/e_all.std():.4f}")
            if cost_bp == 1.0:
                d0 = (arm - eq)[multi]
                j = d0.loc["2016":"2020"]
                # placebo: shuffle same weights across names, judge window, paired vs equal
                obs = j.mean()
                Rm = [R[d] for d in j.index]
                ge = []
                for _ in range(1000):
                    tot = 0.0
                    for legs in Rm:
                        p = rng.permutation(len(legs))
                        tot += day_ret(legs, g, cost, p) - day_ret(legs, 0, cost)
                    ge.append(tot / len(Rm))
                pct = (np.array(ge) < obs).mean() * 100
                lines.append(f"{lab:18s} placebo(2016-20): obs {obs*1e4:.2f}bp vs shuffled mean {np.mean(ge)*1e4:.2f} sd {np.std(ge)*1e4:.2f}; pctile {pct:.0f}")
                lines.append(f"{lab:18s} DSR(N={N_PROG}) on paired 2016-20 series: {dsr(j.values, N_PROG):.3f}")
                ann = d0.loc['2016':'2026'].mean() * (multi.sum() / (len(days) / 250 * 0 + 10.0)) if False else None
                per_yr = d0.mean() * multi.sum() / 10.0
                lines.append(f"{lab:18s} ceiling: paired {d0.mean()*1e4:.2f}bp x {multi.sum()/10:.0f} multi-days/yr x ibs_w0.5 = {per_yr*0.5*100:.2f} pp/yr of account")
    # Kelly fraction of the leg itself
    lines.append("\n=== IBS leg Kelly fraction f*=mean/var of equal-weight day return (1bp/side) ===")
    eq = pd.Series([day_ret(R[d], 0, 1e-4) for d in days], index=pd.DatetimeIndex(days))
    for hn, (a, b) in halves.items():
        x = eq.loc[a:b]
        lines.append(f"{hn:16s} n={len(x)} mean {x.mean()*1e4:.1f}bp sd {x.std()*1e4:.0f}bp f*={x.mean()/x.var():.1f}")
    text = "\n".join(lines) + "\n"
    OUT.write_text(text); print(text)


if __name__ == "__main__":
    main()
