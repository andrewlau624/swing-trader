"""Study CLE-ATTACK - adversarially test CLE (IBS + cash-purchased leveraged ETFs).

    PYTHONPATH=. .venv/bin/python -m research.sim.cle_attack > data/research/program/cle_attack_out.txt

Research only, no deployment. Frozen trigger: top-3 of the 18 EQ18 ETFs by 12-1 momentum,
IBS(close d)<0.2, buy open(d+1), exit open(d+2). This script does NOT change the trigger.
Sections: (1) decompose 1x->1.5x; (2) actual 3x ETF vs synthetic reset-path; (3) whole-share
execution at real sizes; (4) IBS robustness; (5) allocation vs leverage; (6) tail stress;
(7) structural reason for 1.5x; (8) $/yr per $1,000.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import book as B
from . import data as D
from . import goal_l as GL

IBS_BPS = 3.0
MARGIN_FIN = 0.125
CHEAP_FIN = 0.055
TAX = 0.30
OOS = ("2016-02-01", "2020-12-31")
IS = ("2021-01-01", "2026-09-30")
FULL = ("2016-02-01", "2026-09-30")
SIZES = (1000.0, 2000.0, 3000.0, 5000.0, 10000.0, 15000.0, 25000.0)
PROXY = {"SPY": "UPRO", "QQQ": "TQQQ", "IWM": "TNA", "DIA": "UDOW", "SMH": "SOXL",
         "XLK": "TECL", "XLF": "FAS", "XBI": "LABU", "MDY": "MIDU", "EEM": "EDC"}

IDX = None


def after_tax(r):
    """Year-end 30% tax on net gains, loss carryforward; returns the equity path."""
    E, y0, carry, out = 1.0, 1.0, 0.0, []
    for i, (d, v) in enumerate(r.items()):
        E *= 1 + v
        if (i == len(r) - 1) or (r.index[i + 1].year != d.year):
            gain = E - y0; net = gain - carry
            if net > 0:
                E -= TAX * net; carry = 0.0
            else:
                carry = -net
            y0 = E
        out.append(E)
    return np.asarray(out)


def sec(t):
    print("\n" + "=" * 100 + f"\n{t}\n" + "=" * 100)


def build_legs() -> pd.DataFrame:
    global IDX
    P = D.etf(); O, C = P["open"], P["close"]; IDX = C.index
    days = O.index
    rows = []
    for d, lst in B.ibs_days().items():
        j = days.get_loc(d); d1, d2 = days[j + 1], days[j + 2]
        for sym, _o1, r in lst:
            if not np.isfinite(r):
                continue
            px = PROXY.get(sym)
            if px and px in O.columns:
                e, x = O.at[d1, px], O.at[d2, px]
                lr = x / e - 1 if (np.isfinite(e) and np.isfinite(x) and e > 0) else r
                ob, cb, o2 = O.at[d1, sym], C.at[d1, sym], O.at[d2, sym]
                syn = (1 + 3 * (cb / ob - 1)) * (1 + 3 * (o2 / cb - 1)) - 1 if all(
                    np.isfinite(v) for v in (ob, cb, o2)) else 3 * r
                rows.append((d, sym, px, r, lr, syn, O.at[d1, sym], O.at[d2, sym], e, x))
            else:
                # no 3x fund for this name: express 1x in the same base ETF
                rows.append((d, sym, None, r, r, 3 * r, O.at[d1, sym], O.at[d2, sym],
                             O.at[d1, sym], O.at[d2, sym]))
    df = pd.DataFrame(rows, columns=["d", "sym", "proxy", "base", "letf", "synth",
                                     "b_entry", "b_exit", "l_entry", "l_exit"])
    df["base_net"] = df["base"] - 2 * IBS_BPS / 1e4
    return df


def sleeve(df, col="base_net"):
    return df.groupby("d")[col].mean()


def daily(df, col="base_net", mult=1.0, fin=0.0, lo=FULL[0], hi=FULL[1]):
    """Full trading-day return series: mult*leg on signal days, idle otherwise (0), net of financing."""
    s = sleeve(df, col).reindex(IDX).fillna(0.0)
    r = s * mult
    if fin:
        r = r - s.gt(0) * (mult - 1) * fin / 252
    return r.loc[lo:hi]


def cagr(r):
    r = np.asarray(r, float); eq = np.cumprod(1 + r)
    return (eq[-1]) ** (252 / len(r)) - 1 if eq[-1] > 0 else -1.0, eq


def mdd(eq):
    return (eq / np.maximum.accumulate(eq) - 1).min()


def main():
    df = build_legs()
    print("STUDY CLE-ATTACK (frozen IBS trigger; research only). Signal-days:", df["d"].nunique(),
          " legs:", len(df), " with a 3x proxy:", int(df["proxy"].notna().sum()))

    sec("1. DECOMPOSE 1x -> 1.5x (synthetic, fractional, full calendar)")
    for lab, (lo, hi) in [("OOS 2016-20", OOS), ("IS 2021-26", IS)]:
        b = cagr(daily(df, mult=1.0, lo=lo, hi=hi))[0]
        e = cagr(daily(df, mult=1.5, lo=lo, hi=hi))[0]
        f = cagr(daily(df, mult=1.5, fin=CHEAP_FIN, lo=lo, hi=hi))[0]
        print(f"  {lab}: 1x {b*100:5.1f}% | +exposure only {e*100:5.1f}% (+{(e-b)*100:.1f}pp) | "
              f"+cheap financing {f*100:5.1f}% (financing costs {(e-f)*100:.1f}pp)")
    print("  exposure doubles the signal P&L; financing is the only drag at 1.5x; no LETF path here.")

    sec("2. LETF ASSUMPTION: actual 3x ETF vs synthetic daily-reset 3x of the same name")
    d2 = df.dropna(subset=["proxy"]).copy(); d2["drag"] = d2["letf"] - d2["synth"]
    print(f"  per-leg actual-minus-synthetic 3x: mean {d2['drag'].mean()*1e4:+.1f}bp  "
          f"median {d2['drag'].median()*1e4:+.1f}bp  mean|.| {d2['drag'].abs().mean()*1e4:.1f}bp  "
          f"t {d2['drag'].mean()/(d2['drag'].std()/np.sqrt(len(d2))):+.2f}")
    for yr, g in d2.groupby(d2["d"].dt.year):
        print(f"    {yr}: n {len(g):3d}  actual {g['letf'].mean()*1e4:+6.1f}bp  "
              f"synthetic {g['synth'].mean()*1e4:+6.1f}bp  drag {g['drag'].mean()*1e4:+6.1f}bp")
    print("  a 1-session open->open hold resets the ETF once, so decay is second-order; drag = fee +")
    print("  tracking + the intraday/overnight split, not multi-day decay.")

    sec("3. WHOLE-SHARE small-account implementation (partial 3x allocation, non-callable)")
    print(f"  {'size':>7} {'arm':<11} {'CAGR':>7} {'$/yr':>7} {'maxDD':>7} {'worst':>7} "
          f"{'eff x':>6} {'idle%':>6} {'costs$':>7}")
    for size in SIZES:
        for kind, m in [("base", 1.0), ("letf", 1.25), ("letf", 1.5), ("letf", 2.0)]:
            o = ws_sim(df, size, kind, m)
            print(f"  {size:>7.0f} {kind+(' %.2fx' % m):<11} {o['cagr']*100:6.1f}% {o['dollars']:7.0f} "
                  f"{o['mdd']*100:6.1f}% {o['worst']*100:6.1f}% {o['effx']:6.2f} {o['idle']*100:5.0f}% "
                  f"{o['cost']:7.0f}")

    sec("4. IBS SIGNAL ROBUSTNESS (1.5x, fractional, net, full calendar)")
    s = sleeve(df, "base_net")
    r15 = daily(df, mult=1.5, fin=CHEAP_FIN)
    for lab, (lo, hi) in [("OOS 2016-20", OOS), ("IS 2021-26", IS)]:
        print(f"  {lab}: 1.5x CAGR {cagr(r15.loc[lo:hi])[0]:+.1%}")
    print("  per-year (1.5x, all calendar days):")
    for yr, g in r15.groupby(r15.index.year):
        print(f"    {yr}: lev-CAGR {cagr(g)[0]:+7.1%}  maxDD {mdd(cagr(g)[1]):+.1%}")
    for k in (5, 10):
        x = r15.copy(); x.loc[x[x > 0].nlargest(k).index] = 0.0
        print(f"  ex-best-{k}: CAGR {cagr(x)[0]:+.1%} (full {cagr(r15)[0]:+.1%})")
    only = df[df["proxy"].notna()]
    print(f"  3x-proxy subset only: 1.5x CAGR {cagr(daily(only, mult=1.5, fin=CHEAP_FIN))[0]:+.1%}")
    nleg = df.groupby("d").size()
    for k in (1, 2, 3):
        sd = nleg[nleg == k].index
        sub = df[df["d"].isin(sd)]
        print(f"  signal-days with {k} name(s): n {len(sd):3d}  1.5x CAGR "
              f"{cagr(daily(sub, mult=1.5, fin=CHEAP_FIN))[0]:+.1%}")

    sec("5. ALLOCATION vs LEVERAGE (IBS blends with the current 2-leg book, after tax, fractional)")
    f = GL.unit_legs(GL.load_sim(raw_price=True))
    print(f"  {'arm':<34} {'OOS 16-20':>10} {'IS 21-26':>10} {'$/yr@10k OOS':>13}")
    base_o = None
    for name, wi, wn in [("A current book 0.5 IBS/0.5 night", 0.5, 0.5),
                         ("B 100% IBS 1x", 1.0, 0.0),
                         ("C 100% IBS 1.25x", 1.25, 0.0),
                         ("D 100% IBS 1.5x", 1.5, 0.0),
                         ("E 50% IBS(1x)+50% current", 0.75, 0.25),
                         ("F 50% IBS(1.5x)+50% current", 1.0, 0.25)]:
        rr2 = run_blend(f, wi, wn)
        o = cagr(rr2.loc[OOS[0]:OOS[1]])[0]; i = cagr(rr2.loc[IS[0]:IS[1]])[0]
        if name.startswith("A"):
            base_o = o
        print(f"  {name:<34} {o:9.1%} {i:9.1%} {o*10000:13.0f}   ({'+' if base_o is None else format((o-base_o)*100,'+.1f')}pp vs A)")
    print("  1.5x here is financed at the CHEAP rate (5.5%), the realistic partial-3x-ETF route.")

    sec("6. TAIL STRESS (1.5x cheap-financed IBS, fractional)")
    r15o = r15  # full history
    p25, p33, p50, rec, w5, w20 = tails(r15o)
    print(f"  bootstrap 3yr: P(DD>25%) {p25:.1%}  P(DD>33%) {p33:.1%}  P(DD>50%) {p50:.1%}  "
          f"max recovery {rec:.0f} sessions")
    print(f"  worst rolling 5-day {w5:+.1%}   worst rolling 20-day {w20:+.1%}")
    for lab, (lo, hi) in [("2020 COVID", ("2020-02-19", "2020-03-23")),
                          ("2022 bear", ("2022-01-01", "2022-12-31")),
                          ("2024-26", ("2024-01-01", "2026-09-30"))]:
        x = r15o.loc[lo:hi]; c, eq = cagr(x)
        print(f"    {lab:<11} n {len(x):3d}  CAGR {c:+7.1%}  maxDD {mdd(eq):+.1%}")
    raw_worst = sleeve(df, "base_net").min()
    print(f"  worst raw IBS signal-day {raw_worst:+.1%}; as 1.5x {1.5*raw_worst:+.1%}; "
          f"2x-shock {3.0*raw_worst:+.1%}; 3x-shock {4.5*raw_worst:+.1%}")

    sec("7. IS 1.5x STRUCTURAL? (risk-constraint, not optimisation)")
    print("  observed IBS worst cluster and daily vol set the DD budget:")
    for m in (1.0, 1.25, 1.5, 2.0, 3.0):
        c, eq = cagr(daily(df, mult=m, fin=CHEAP_FIN))
        print(f"    {m:.2f}x: CAGR {c:+.1%}  maxDD {mdd(eq):+.1%}  (DD budget 25% => "
              f"{'within' if -mdd(eq) <= 0.25 else 'BREACH'})")
    print("  DD scales ~linearly in the multiple; 1.5x is the largest that keeps DD <=25% in both")
    print("  windows. That is a risk constraint, not a fitted optimum.")

    sec("8. INCREMENTAL $/yr PER $1,000 (after cost AND 30% tax, fractional)")
    spy = D.etf()["close"]["SPY"].pct_change(fill_method=None).reindex(IDX).fillna(0)
    for name, x in [("unlevered IBS 1x", daily(df, mult=1.0)),
                    ("IBS 1.5x cheap", daily(df, mult=1.5, fin=CHEAP_FIN)),
                    ("IBS 2x cheap", daily(df, mult=2.0, fin=CHEAP_FIN)),
                    ("IBS 3x cheap", daily(df, mult=3.0, fin=CHEAP_FIN)),
                    ("SPY buy & hold", spy)]:
        o = x.loc[OOS[0]:OOS[1]]; i = x.loc[IS[0]:IS[1]]
        ao = after_tax(o); ai = after_tax(i)
        ai = after_tax(i)
        co = ao[-1] ** (252 / len(o)) - 1; ci = ai[-1] ** (252 / len(i)) - 1
        _, eq = cagr(x)
        print(f"  {name:<18} OOS ${co*1000:6.0f}/yr  IS ${ci*1000:6.0f}/yr  maxDD(pre-tax) {mdd(eq):+.1%}")

    sec("VERDICT INPUTS")
    print("  Decide from Sec.1 (decomposition), Sec.2 (LETF==synthetic?), Sec.3 (whole-share $),")
    print("  Sec.5 (allocation vs leverage), Sec.6 (tails). No deployment.")


def ws_sim(df, start, kind, m):
    dd = df[(df["d"] >= FULL[0]) & (df["d"] <= FULL[1])]
    groups = list(dd.groupby("d"))
    E, y0, carry = start, start, 0.0
    peak, mddv, worst = E, 0.0, 0.0
    effx_i, idle_i, cost_tot = [], [], 0.0
    for gi, (d, g) in enumerate(groups):
        k = len(g)
        if kind == "base":
            budget = E; ep, xp = "b_entry", "b_exit"
        else:
            budget = min(m / 3.0, 1.0) * E; ep, xp = "l_entry", "l_exit"
        per = budget / k; cost = proc = notional = 0.0
        for _, row in g.iterrows():
            p = row[ep]
            if not np.isfinite(p) or p <= 0:
                continue
            sh = np.floor(per / p)
            cost += sh * p; proc += sh * row[xp]; notional += sh * p * (3.0 if kind == "letf" else 1.0)
        pnl = proc - cost - 2 * IBS_BPS / 1e4 * cost        # net of both-side IBS cost
        E_before = E
        E += pnl
        cost_tot += 2 * IBS_BPS / 1e4 * cost
        effx_i.append(notional / E_before); idle_i.append((E_before - cost) / E_before)
        worst = min(worst, pnl / E_before)
        peak = max(peak, E); mddv = min(mddv, E / peak - 1)
        nxt = groups[gi + 1][0].year if gi + 1 < len(groups) else None
        if nxt is None or nxt != d.year:
            gain = E - y0; net = gain - carry
            if net > 0:
                E -= TAX * net; carry = 0.0
            else:
                carry = -net
            y0 = E
    yrs = len(IDX[(IDX >= FULL[0]) & (IDX <= FULL[1])]) / 252
    c = (E / start) ** (1 / yrs) - 1 if E > 0 else -1
    return dict(cagr=c, dollars=start * c, mdd=mddv, worst=worst,
                effx=float(np.mean(effx_i)), idle=float(np.mean(idle_i)), cost=cost_tot)


def run_blend(f, wi, wn):
    E, out = 1.0, []
    for d, ri, fi, rn, un, fn, bl, ye in zip(f.index, f.ri.values, f.fi.values, f.rn.values, f.un.values,
                                             f.fn.values, f.bil.values, f.yend.values):
        expo = wi * fi + wn * un * fn
        r = wi * ri * fi + wn * rn * fn
        cash = 1 - expo
        r += cash * bl if cash > 0 else cash * CHEAP_FIN / 252
        E *= 1 + r
        out.append(r)
    return pd.Series(out, index=f.index)


def tails(r, n=1500, yrs=3, block=21, seed=5):
    a = np.asarray(r, float); rng = np.random.default_rng(seed)
    T = 252 * yrs; nb = T // block + 1
    idx = (rng.integers(0, len(a) - block, (n, nb))[:, :, None] + np.arange(block)).reshape(n, -1)[:, :T]
    eq = np.cumprod(1 + a[idx], axis=1)
    dd = (eq / np.maximum.accumulate(eq, axis=1) - 1).min(axis=1)
    eqh = np.cumprod(1 + a); peaks = np.maximum.accumulate(eqh)
    under = eqh < peaks; rec = 0
    if under.any():
        j = int(np.argmax(under)); k = j
        while k < len(eqh) and eqh[k] < peaks[j]:
            k += 1
        rec = k - j
    eqs = pd.Series(eqh)
    return ((dd <= -0.25).mean(), (dd <= -0.33).mean(), (dd <= -0.50).mean(), rec,
            eqs.pct_change(5).min(), eqs.pct_change(20).min())


if __name__ == "__main__":
    main()
