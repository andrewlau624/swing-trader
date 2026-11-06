"""Study VRP-POST runner (pre-reg research/drafts/round1_prose.md, N 1076-1079).

Post-spike short-vol: -1x / -0.5x synthetic short-term VIX futures ETP, entered only after a VIX spike once the front
curve is back in contango and VIX is X% off the episode peak. Choose X/H on 2012-19, judge 2004-11 and 2020-26.

Run: python3 -I -c "import sys; sys.path.insert(0,'.'); import runpy; runpy.run_module('research.sim.vrp_post', run_name='__main__')"
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.sim.ibs_voltilt import dsr, nw_t
from research.sim.vrp_data import ROOT, synthetic, yclose

OUT = ROOT / "data/research/program/vrp_post_out.txt"
CHOOSE = ("2012-01-01", "2019-12-31")
JUDGE = {"2004-11": ("2004-03-01", "2011-12-31"), "2020-26": ("2020-01-01", "2026-12-31")}
GRID = [(x, h) for x in (0.20, 0.35) for h in (21, 63)]
NTOP = 1079


def panel() -> pd.DataFrame:
    C = synthetic()
    vix = yclose("^VIX")
    med = vix.shift(1).rolling(63).median()
    irx = yclose("^IRX")
    D = C[["F1", "F2", "r_long"]].copy()
    D["vix"] = vix.reindex(D.index)
    D["med"] = med.reindex(D.index)
    D["rf"] = (irx.reindex(D.index).ffill() / 100 / 252).fillna(0)
    D = D.dropna(subset=["vix", "med"])
    D["nan_r"] = D["r_long"].isna()
    D["r_long"] = D["r_long"].fillna(0.0)
    D["xs1"] = np.maximum(-1.0, -D["r_long"]) - 0.0135 / 252  # S1 excess over cash
    D["xs05"] = -0.5 * D["r_long"] - 0.0095 / 252
    return D


def run(D: pd.DataFrame, X: float, H: int, inst: str = "xs1", cap: float = 0.30):
    """Returns per-day held flag (earning day i), trade list. Signal at close i -> trade at close i+1."""
    vix, med, F1, F2, xs = (D[c].values for c in ("vix", "med", "F1", "F2", inst))
    n = len(D)
    held = np.zeros(n, bool)
    trade_day = np.zeros(n, bool)  # a trade (entry or exit) executes at close i
    trades = []
    holding = pending = False
    armed = False; last_spike = -10**9; P = 0.0; ep = -1; stopped = False
    cum = 0.0; nd = 0; t0 = None
    for i in range(n):
        if holding:
            held[i] = True
            cum = (1 + cum) * (1 + xs[i]) - 1; nd += 1
        if pending != holding:
            trade_day[i] = True
            if pending:
                cum, nd, t0 = 0.0, 0, i
            else:
                trades.append(dict(ep=ep, start=D.index[t0], end=D.index[i], i0=t0, i1=i, days=nd, cum=cum))
            holding = pending
        # episode state at close i
        if vix[i] >= 1.5 * med[i]:
            if not armed:
                armed = True; ep += 1; P = vix[i]; stopped = False
            last_spike = i
        if armed:
            P = max(P, vix[i])
            if i - last_spike > 63:
                armed = False
        # signal at close i
        if holding:
            if F1[i] >= F2[i] or nd >= H or cum <= -cap or not armed:
                if cum <= -cap:
                    stopped = True
                pending = False
        else:
            pending = bool(armed and not stopped and F2[i] > F1[i] and vix[i] <= (1 - X) * P)
    if holding:
        trades.append(dict(ep=ep, start=D.index[t0], end=D.index[n - 1], i0=t0, i1=n - 1, days=nd, cum=cum, open=True))
    return held, trade_day, pd.DataFrame(trades)


def daily(D, held, trade_day, inst, cost):
    """Instrument-level daily excess series: held-day return minus cost on trade days (cost in instrument units)."""
    r = np.where(held, D[inst].values, 0.0) - np.where(trade_day, cost, 0.0)
    return pd.Series(r, index=D.index)


def sl(s, a, b):
    return s.loc[a:b]


def main():
    D = panel()
    L = [f"Study VRP-POST (N 1076-1079). Panel {D.index[0].date()}..{D.index[-1].date()}, {len(D)} days, "
         f"r_long NaN->0 on {int(D['nan_r'].sum())} days"]
    # ---- choose
    L.append("\n== CHOOSE 2012-19 (S1, 1x cost 10bp/side) ==")
    best = None
    for X, H in GRID:
        held, td, T = run(D, X, H)
        r = sl(daily(D, held, td, "xs1", 0.001), *CHOOSE)
        hd = sl(pd.Series(held, index=D.index), *CHOOSE)
        x = r[hd | sl(pd.Series(td, index=D.index), *CHOOSE)]
        sh = x.mean() / x.std() * np.sqrt(252) if len(x) > 2 else np.nan
        L.append(f"X={X:.2f} H={H}: in-days {int(hd.sum())}, sum excess {r.sum()*100:+.1f}%, Sharpe(in-pos) {sh:.2f}, "
                 f"NW t {nw_t(x.values):.2f}, worst day {x.min()*100:.1f}%")
        if best is None or sh > best[0]:
            best = (sh, X, H)
    _, X, H = best
    L.append(f"CHOSEN: X={X} H={H}")
    held, td, T = run(D, X, H)
    heldS = pd.Series(held, index=D.index)
    tdS = pd.Series(td, index=D.index)
    worst_choose = sl(D["xs1"][heldS], *CHOOSE).min()
    w = 0.10 / abs(worst_choose)
    L.append(f"Sizing: worst in-position S1 day 2012-19 {worst_choose*100:.1f}% -> w = {w:.2f} of account")

    # ---- judge
    jmask = pd.Series(False, index=D.index)
    for a, b in JUDGE.values():
        jmask.loc[a:b] = True
    for cmult in (1, 2, 3):
        c = 0.001 * cmult
        L.append(f"\n== JUDGE, cost {cmult}x ({c*1e4:.0f}bp/side) ==")
        for inst, lab in (("xs1", "S1 -1x"), ("xs05", "S05 -0.5x Roth")):
            r = daily(D, held, td, inst, c)
            for nm, (a, b) in JUDGE.items():
                x = sl(r, a, b); hd = sl(heldS | tdS, a, b)
                yrs = len(x) / 252
                L.append(f"  {lab} {nm}: in-days {int(sl(heldS, a, b).sum())}, instrument sum excess {x.sum()*100:+.1f}%, "
                         f"{x.sum()/yrs*100:+.1f}%/yr; account at w={w:.2f}: {w*x.sum()/yrs*100:+.2f}pp/yr")
            xj = r[jmask & (heldS | tdS)]
            L.append(f"  {lab} pooled judge: mean/in-day {xj.mean()*1e4:+.1f}bp, NW t {nw_t(xj.values):.2f}, "
                     f"ex-top-5 days sum {(xj.sum()-xj.nlargest(5).sum())*100:+.1f}%, median {xj.median()*1e4:+.1f}bp, "
                     f"hit {(xj>0).mean():.2f}")
    # ---- trades / episodes (S1, 2x)
    c2 = 0.002
    T = T.copy()
    T["xs"] = [np.prod(1 + D["xs1"].values[i0 + 1:i1 + 1]) - 1 - 2 * c2 for i0, i1 in zip(T["i0"], T["i1"])]
    T["era"] = np.where(T["start"] < "2012-01-01", "2004-11", np.where(T["start"] < "2020-01-01", "choose", "2020-26"))
    L.append("\n== Trades (S1, net of 2x cost; held days; open trade flagged) ==")
    for _, t in T.iterrows():
        L.append(f"  ep{t.ep:3d} {t.era:8s} {t.start.date()} -> {t.end.date()} {t.days:3d}d  {t["xs"]*100:+6.1f}%"
                 + ("  OPEN" if t.get("open") is True else ""))
    E = T.groupby(["era", "ep"])["xs"].apply(lambda s: np.prod(1 + s) - 1).reset_index()
    Ej = E[E["era"] != "choose"]
    L.append(f"\nJudge episodes {len(Ej)}: median {Ej["xs"].median()*100:+.1f}%, positive {(Ej["xs"]>0).mean():.2f}, "
             f"sum {Ej["xs"].sum()*100:+.1f}%, ex-best-episode {(Ej["xs"].sum()-Ej["xs"].max())*100:+.1f}%")
    # ---- other contango days & placebo (S1, 2x)
    r2 = daily(D, held, td, "xs1", c2)
    cont_sig = (D["F2"] > D["F1"]).shift(2).fillna(False).astype(bool)  # signal 2 closes before the earned day
    other = D["xs1"][jmask & cont_sig & ~heldS]
    xin = D["xs1"][jmask & heldS]
    L.append(f"In-position mean {xin.mean()*1e4:+.1f}bp/day (n {len(xin)}) vs other judge contango days "
             f"{other.mean()*1e4:+.1f}bp/day (n {len(other)}); Welch t "
             f"{(xin.mean()-other.mean())/np.sqrt(xin.var()/len(xin)+other.var()/len(other)):.2f}")
    Tj = T[T["era"] != "choose"]
    rule_tot = r2[jmask].sum()
    rng = np.random.default_rng(1079)
    xsv = D["xs1"].values
    jidx = np.where(jmask.values & (D["F2"] > D["F1"]).values)[0]
    lens = Tj["days"].values
    pl = []
    for _ in range(1000):
        tot = 0.0
        for Ld in lens:
            s = rng.choice(jidx)
            tot += xsv[s + 2:s + 2 + Ld].sum() - 2 * c2
        pl.append(tot)
    pl = np.array(pl)
    L.append(f"Placebo (1000, same {len(lens)} trades/hold lengths at random judge contango starts): rule total "
             f"{rule_tot*100:+.1f}% vs placebo median {np.median(pl)*100:+.1f}%, pct {(pl < rule_tot).mean()*100:.1f}")
    # ---- account
    acc = w * r2
    for nm, (a, b) in JUDGE.items():
        x = sl(acc, a, b)
        eq = (1 + x).cumprod()
        L.append(f"Account (w={w:.2f}, S1, 2x) {nm}: {x.mean()*252*100:+.2f}pp/yr, worst day {x.min()*100:.1f}%, "
                 f"maxDD {((eq/eq.cummax())-1).min()*100:.1f}%")
    xa = acc[jmask]
    L.append(f"DSR (account daily, judge pooled, N {NTOP}): {dsr(xa.values, NTOP):.3f}")
    # Roth -0.5x with its own w (same rule)
    worst05 = sl(D["xs05"][heldS], *CHOOSE).min(); w05 = min(1.0, 0.10 / abs(worst05))
    acc05 = w05 * daily(D, held, td, "xs05", c2)
    for nm, (a, b) in JUDGE.items():
        x = sl(acc05, a, b); eq = (1 + x).cumprod()
        L.append(f"Roth S05 (w={w05:.2f}, 2x) {nm}: {x.mean()*252*100:+.2f}pp/yr, worst day {x.min()*100:.1f}%, "
                 f"maxDD {((eq/eq.cummax())-1).min()*100:.1f}%")
    # named episodes
    L.append("\nWorst S1 days while held (all eras): " + ", ".join(
        f"{d.date()} {v*100:.1f}%" for d, v in D["xs1"][heldS].nsmallest(6).items()))
    txt = "\n".join(L)
    OUT.write_text(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
