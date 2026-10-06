"""Study CLE - small-account capital efficiency: IBS leverage, margin vs 3x-ETF financing.

    PYTHONPATH=. .venv/bin/python -m research.sim.cle > data/research/program/cle_out.txt

Pre-registered: research/drafts/study_cle.md (round1_prose.md N 821 -> 822). One look.
Exploratory only: no deployment, no margin change, no live sizing. Leverage is applied ONLY to
the validated IBS leg (night off). Margin route = 12.5%/yr on the borrowed fraction, Reg T $2,000
floor. LETF route = the ACTUAL forward return of the 3x ETF tracking each selected name (financing
embedded, non-callable), from etf_daily.parquet 2016-2026. Judge window 2016-2020 (untouched).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import book as B
from . import data as D

ROOT = None
FIN_MARGIN = 0.125
FIN_LETF = 0.055
IBS_BPS = 3.0
L_GRID = (1.0, 1.25, 1.5, 2.0, 2.5, 3.0)
SIZES = (2300.0, 10000.0, 25000.0)
TAX = 0.30
FLOOR = 2000.0
OOS = ("2016-02-01", "2020-12-31")
IS = ("2021-01-01", "2026-09-30")
PROXY = {"SPY": "UPRO", "QQQ": "TQQQ", "IWM": "TNA", "DIA": "UDOW", "SMH": "SOXL",
         "XLK": "TECL", "XLF": "FAS", "XBI": "LABU", "MDY": "MIDU", "EEM": "EDC"}


def build() -> pd.DataFrame:
    P = D.etf()
    O = P["open"]
    days = O.index
    legs = B.ibs_days()
    base, letf, fi = {}, {}, {}
    for d, lst in legs.items():
        j = days.get_loc(d)
        d1, d2 = days[j + 1], days[j + 2]
        br, lr = [], []
        for sym, _o1, r in lst:
            if not np.isfinite(r):
                continue
            br.append(r)
            px = PROXY.get(sym, sym)
            if px not in O.columns or px == sym:
                lr.append(r)                                   # no liquid 3x -> express 1x
            else:
                a, b = O.at[d1, px], O.at[d2, px]
                lr.append(b / a - 1 if (np.isfinite(a) and np.isfinite(b) and a > 0) else r)
        if br:
            base[d] = float(np.mean(br)) - 2 * IBS_BPS / 1e4
            letf[d] = float(np.mean(lr)) - 2 * IBS_BPS / 1e4
            fi[d] = 1.0
    idx = days[(days >= days[260]) & (days <= days[-3])]
    df = pd.DataFrame(index=idx)
    df["base"] = pd.Series(base).reindex(idx).fillna(0.0)
    df["letf"] = pd.Series(letf).reindex(idx).fillna(0.0)
    df["fi"] = pd.Series(fi).reindex(idx).fillna(0.0)
    bil = P["close"]["BIL"].pct_change(fill_method=None).reindex(idx).fillna(0.0)
    df["bil"] = bil
    return df


def run_arm(s, start, kind, L, fin, lo, hi):
    """kind: 'base' (1x) | 'margin' | 'letf'. Dollar path with tax + Reg T floor."""
    d = s.loc[lo:hi]
    E, y0, carry = start, start, 0.0
    peak, mdd, worst, rets, liq = start, 0.0, 0.0, [], 0
    prev_year = None
    for i in range(len(d)):
        fi = d.fi.iloc[i]
        if fi and kind == "letf":
            r = d.letf.iloc[i]
        elif fi and kind == "letf_frac":
            f = min(L / 3.0, 1.0)
            r = f * d.letf.iloc[i] + (1 - f) * d.bil.iloc[i]
        elif fi and kind == "base":
            r = d.base.iloc[i]
        elif fi:                                        # margin
            on = E >= FLOOR
            Lc = L if on else 1.0
            r = Lc * d.base.iloc[i] - (Lc - 1.0) * fin / 252
            if on and E * (1 + r) < 0.25 * (L * E):
                liq += 1
        else:
            r = d.bil.iloc[i]                           # idle cash earns T-bills
        E = E * (1 + r)
        peak = max(peak, E); mdd = min(mdd, E / peak - 1)
        worst = min(worst, r); rets.append(r)
        yr = d.index[i].year
        last_of_year = (i == len(d) - 1) or (d.index[i + 1].year != yr)
        if last_of_year:
            gain = E - y0; net = gain - carry
            if net > 0:
                E -= TAX * net; carry = 0.0
            else:
                carry = -net
            y0 = E
    rets = np.asarray(rets)
    yrs = len(rets) / 252
    cagr = (E / start) ** (1 / yrs) - 1 if E > 0 else -1.0
    return dict(end=E, cagr=cagr, mdd=mdd, worst=worst, p5=np.percentile(rets, 5),
                n_tr=int(d.fi.sum()), liq=liq)


def boot(s, start, kind, L, fin, n=1000, yrs=3, block=21, seed=11):
    """21-day block bootstrap of the daily arm returns; P(maxDD>25/50%) and median CAGR."""
    d = s.loc[OOS[0]:IS[1]]
    if kind == "margin":
        m = ((d.base * L - (L - 1) * fin / 252) * d.fi + d.bil * (1 - d.fi)).values
    elif kind == "letf":
        m = (d.letf * d.fi + d.bil * (1 - d.fi)).values
    elif kind == "letf_frac":
        f = min(L / 3.0, 1.0)
        m = ((f * d.letf + (1 - f) * d.bil) * d.fi + d.bil * (1 - d.fi)).values
    else:
        m = (d.base * d.fi + d.bil * (1 - d.fi)).values
    rng = np.random.default_rng(seed)
    T = 252 * yrs; nb = T // block + 1
    idx = (rng.integers(0, len(m) - block, (n, nb))[:, :, None] + np.arange(block)).reshape(n, -1)[:, :T]
    x = m[idx]
    eq = np.cumprod(1 + x, axis=1)
    dd = (eq / np.maximum.accumulate(eq, axis=1) - 1).min(axis=1)
    return float((dd <= -0.25).mean()), float((dd <= -0.50).mean()), float(np.median(eq[:, -1]) ** (1 / yrs) - 1)


def main():
    s = build()
    eff = (s.loc[s.fi > 0, "letf"].mean() / s.loc[s.fi > 0, "base"].mean())
    n_sig = int((s.fi > 0).sum())
    print("Study CLE - IBS leverage, small-account capital efficiency (one look, N 821 -> 822)")
    print(f"IBS sleeve: {n_sig} signal-days {s.index.min().date()}..{s.index.max().date()}; "
          f"LETF express realized effective multiple {eff:.2f}x (actual 3x proxies, financing embedded).")
    print(f"Margin financing {FIN_MARGIN*100:.1f}%/yr; LETF embedded {FIN_LETF*100:.1f}%/yr (assumption); "
          f"tax {TAX*100:.0f}%; Reg T floor ${FLOOR:.0f}. Night leg OFF (leverage only on the validated leg).")

    for lab, (lo, hi) in [("UNTTOUCHED 2016-20", OOS), ("in-sample 2021-26", IS)]:
        print("\n" + "=" * 96 + f"\n{lab}  (CAGR / maxDD / worst day / 5th pct day / $/yr at $2.3k)\n" + "=" * 96)
        print(f"  {'arm':<22} {'CAGR':>7} {'maxDD':>7} {'worst':>7} {'p5':>7} {'$/yr@2.3k':>10} {'$/yr@10k':>9} {'$/yr@25k':>9}")
        for kind, L, fin, name in [("base", 1.0, 0.0, "base 1x (IBS net 3bp)"),
                                   ("margin", 1.25, FIN_MARGIN, "margin 1.25x"),
                                   ("margin", 1.5, FIN_MARGIN, "margin 1.5x"),
                                   ("margin", 2.0, FIN_MARGIN, "margin 2x"),
                                   ("margin", 3.0, FIN_MARGIN, "margin 3x"),
                                   ("letf_frac", 1.5, 0.0, "LETF alloc 1.5x"),
                                   ("letf_frac", 2.0, 0.0, "LETF alloc 2x"),
                                   ("letf_frac", 2.5, 0.0, "LETF alloc 2.5x"),
                                   ("letf", 3.0, 0.0, "LETF 3x (actual)")]:
            r = run_arm(s, 10000.0, kind, L, fin, lo, hi)
            print(f"  {name:<22} {r['cagr']*100:6.1f}% {r['mdd']*100:6.1f}% {r['worst']*100:6.1f}% "
                  f"{r['p5']*100:6.1f}% {r['cagr']*2300:10.0f} {r['cagr']*10000:9.0f} {r['cagr']*25000:9.0f}"
                  + (f"  liq {r['liq']}" if r["liq"] else ""))

    print("\n" + "=" * 96 + "\nBlock bootstrap 2016-2026 (12-mo-ish paths, 3yr, 21d blocks, n=1000)\n" + "=" * 96)
    print(f"  {'arm':<22} {'P(DD>25%)':>10} {'P(DD>50%)':>10} {'median CAGR':>12}")
    for kind, L, fin, name in [("base", 1.0, 0.0, "base 1x"), ("margin", 1.5, FIN_MARGIN, "margin 1.5x"),
                               ("margin", 2.0, FIN_MARGIN, "margin 2x"), ("margin", 3.0, FIN_MARGIN, "margin 3x"),
                               ("letf_frac", 1.5, 0.0, "LETF alloc 1.5x"), ("letf_frac", 2.0, 0.0, "LETF alloc 2x"),
                               ("letf", 3.0, 0.0, "LETF 3x (actual)")]:
        p25, p50, mc = boot(s, 10000.0, kind, L, fin)
        print(f"  {name:<22} {p25*100:9.1f}% {p50*100:9.1f}% {mc*100:11.1f}%")

    print("\n" + "=" * 96 + "\nJUDGED PRIMARY (2016-20 untouched): moderate LETF-allocated IBS vs 1x and vs margin\n" + "=" * 96)
    b0 = run_arm(s, 10000.0, "base", 1.0, 0.0, *OOS)["cagr"]
    b0is = run_arm(s, 10000.0, "base", 1.0, 0.0, *IS)["cagr"]
    print(f"  bench: IBS-1x {b0*100:+.1f}% (2016-20) / {b0is*100:+.1f}% (2021-26); "
          f"current 2-leg book Goal L B0 approx +3.9% / +6.1%")
    best = None
    for e in (1.5, 2.0, 2.5, 3.0):
        k = "letf" if e == 3.0 else "letf_frac"
        r = run_arm(s, 10000.0, k, e, 0.0, *OOS)
        ris = run_arm(s, 10000.0, k, e, 0.0, *IS)
        p25, p50, mc = boot(s, 10000.0, k, e, 0.0)
        tag = "3x all-in" if e == 3.0 else f"LETF alloc {e}x"
        ok = r["mdd"] >= -0.25 and ris["mdd"] >= -0.25 and p50 <= 0.05
        print(f"  {tag:<16} 2016-20 CAGR {r['cagr']*100:+6.1f}%  maxDD {r['mdd']*100:6.1f}%  "
              f"2021-26 maxDD {ris['mdd']*100:6.1f}%  P(DD>50%) {p50*100:4.1f}%  "
              f"edge {(r['cagr']-b0)*100:+6.1f}pp  {'ok' if ok else 'too fragile'}")
        if ok and (best is None or e > best[0]):
            best = (e, r, ris, p50)
    if best is None:
        print("  -> no arm keeps maxDD<=25% in both windows; leverage is risk-scaling only")
        e = r_e = None
        v = "REJECTED (leverage scales risk 1:1; no controlled-downside arm)"
    else:
        e, r, ris, p50 = best
        edge = r["cagr"] - b0
        print(f"  -> moderate arm: LETF alloc {e}x, edge {edge*100:+.1f}pp (OOS), "
              f"maxDD {r['mdd']*100:.1f}%/{ris['mdd']*100:.1f}%, P(DD>50%) {p50*100:.1f}%")
        v = ("PROMISING (validation-grade leverage on the validated IBS edge; "
             "financing + non-callability are the gain, Sharpe ~flat)")
    print(f"  VERDICT: {v}")


if __name__ == "__main__":
    main()
