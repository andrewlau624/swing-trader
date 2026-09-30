"""Round 16, Study AG: confidence and confirmation signals at the conviction breakout minute
(round1_prose.md Round 16 AG).

    PYTHONPATH=. .venv/bin/python -m research.sim.conviction_ag        # ~1 min

Each confirmation is bucketed on the 2016-23 trades (terciles, or fixed categories). If net EV per trade is monotone
across the buckets in 2016-23, variant AG_k drops the worst end bucket; judged on 2024-26 and the full-period bars.
Breadth (NDX-100 members) and NQ-leads-QQQ are untestable here: no data.
"""
from __future__ import annotations

import pickle

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import book as B
from . import conv2 as CV
from . import data as D
from . import program_books as PB
from . import taxable_frontier as TF
from .conviction_af import BP_RES, HALVES, SCR, SIZES, conv_trades

N_PROGRAM = 629          # upper bound; the writeup states the count actually run
IS = ("2016-01-01", "2023-12-31")
C_SHIP, C_TH = 3e-4, 6e-4   # round trip


def band_dir(sym: str, lookback: int = 14) -> dict:
    """date -> direction (+1 above / -1 below / 0 inside) of sym vs its own noise band at every minute."""
    M = D.minutes(sym)
    C = M["close"].values
    O = M["open"].values[:, 0]
    days = M["close"].index
    move = np.abs(C / O[:, None] - 1)
    prevc = np.r_[np.nan, C[:-1, -1]]
    out = {}
    for i in range(lookback + 1, len(days)):
        sig = sg.noise_sigma(move[i - lookback:i])
        ub, lb = sg.noise_bounds(O[i], prevc[i], sig)
        out[days[i]] = np.where(C[i] > ub, 1, np.where(C[i] < lb, -1, 0))
    return out


def cboe(name: str) -> pd.Series:
    x = pd.read_csv(SCR / "cboe" / f"{name}.csv")
    return pd.Series(x["CLOSE"].values, index=pd.to_datetime(x["DATE"], format="%m/%d/%Y"))


def features(T: pd.DataFrame) -> pd.DataFrame:
    F = pd.DataFrame(index=T.index)
    F["C1 strength"] = T["strength"]
    bd = {s: band_dir(s) for s in ("SMH", "SPY", "IWM")}
    agree = []
    for d, r in T.iterrows():
        agree.append(sum(int(d in bd[s] and bd[s][d][int(r.m0)] == r.dir) for s in bd))
    F["C2 cross-ETF agree"] = np.minimum(agree, 2)          # 0 / 1 / 2-3
    Mq = D.minutes("QQQ")
    V = Mq["volume"]; pos = {d: i for i, d in enumerate(V.index)}
    Vv = V.values
    rv = []
    for d, r in T.iterrows():
        i, m = pos.get(d), int(r.m0)
        if i is None or i < 14:
            rv.append(np.nan); continue
        now = Vv[i, m - 29:m + 1].sum()
        past = Vv[i - 14:i, m - 29:m + 1].sum(axis=1).mean()
        rv.append(now / past if past > 0 else np.nan)
    F["C3 rel volume"] = rv
    ix = T.index
    vix, v9 = cboe("VIX"), cboe("VIX9D")
    prev = lambda s: s.reindex(s.index.union(ix)).ffill().shift(1).reindex(ix)
    F["C4 VIX"] = prev(vix)
    F["C5 VIX9D/VIX"] = prev(v9) / prev(vix)
    F["C6 time"] = np.select([T.m0 <= 30, T.m0 <= 120], [0, 1], 2)
    return F


CATEGORICAL = {"C2 cross-ETF agree", "C6 time"}


def buckets(F: pd.DataFrame) -> pd.DataFrame:
    Bk = pd.DataFrame(index=F.index)
    for c in F:
        if c in CATEGORICAL:
            Bk[c] = F[c]
        else:
            cuts = np.nanquantile(F.loc[IS[0]:IS[1], c], [1 / 3, 2 / 3])
            Bk[c] = np.where(F[c].isna(), np.nan, np.digitize(F[c].values, cuts))
    return Bk


def ev_table(net: pd.Series, b: pd.Series, a: str, z: str):
    out = []
    for k in range(3):
        u = net[a:z][b[a:z] == k]
        t = u.mean() / u.std(ddof=1) * np.sqrt(len(u)) if len(u) > 2 else np.nan
        out.append((len(u), u.mean(), (u > 0).mean() if len(u) else np.nan, t))
    return out


def main():
    T = conv_trades()
    net = T["gross"] - C_SHIP
    net_th = T["gross"] - C_TH
    F = features(T)
    Bk = buckets(F)

    print("== C1 report: EV by strength quintile over ALL first breakouts (TQQQ, incl. < 0.341), 1.5bp/side")
    fb = CV.first_breakouts("TQQQ")
    q = np.quantile(fb.loc[IS[0]:IS[1], "strength"], [.2, .4, .6, .8])
    fb["q"] = np.digitize(fb.strength, q); fb["net"] = fb.gross - C_SHIP
    print(f"   quintile cuts {np.round(q, 3)} (shipped threshold 0.341)")
    for lab, a, z in HALVES:
        u = fb[a:z]
        print(f"   {lab}: " + " | ".join(f"Q{k+1} {u[u.q==k].net.mean()*1e4:+6.1f}bp (n {len(u[u.q==k])})" for k in range(5)))

    print("\n== confirmations: net EV per trade by bucket (1.5bp/side): n / EV / win / t")
    sel = {}
    for c in Bk:
        print(f"  {c}" + (f"  cuts {np.round(np.nanquantile(F.loc[IS[0]:IS[1], c], [1/3, 2/3]), 3)}" if c not in CATEGORICAL else ""))
        for lab, a, z in HALVES:
            tb = ev_table(net, Bk[c], a, z)
            print(f"    {lab}: " + " | ".join(f"B{k} n {n:3d} {m*1e4:+6.1f}bp w {w:4.0%} t {t:+5.2f}" for k, (n, m, w, t) in enumerate(tb)))
        ins = [m for _, m, _, _ in ev_table(net, Bk[c], *IS)]
        up, dn = ins[0] < ins[1] < ins[2], ins[0] > ins[1] > ins[2]
        if up or dn:
            sel[c] = 0 if up else 2
            print(f"    -> monotone {'rising' if up else 'falling'} in 2016-23: variant drops bucket B{sel[c]}")
        else:
            print("    -> not monotone in 2016-23: no variant")

    bp = pickle.load(open(BP_RES, "rb"))["res"]
    b3 = bp[("B3 moderate10c", "M2 base", "tier_hi")]
    days = pd.DatetimeIndex(sorted(set(D.minutes("QQQ")["close"].index[15:])))
    print(f"\n== variants run: {len(sel)} (program N 623 -> {623 + len(sel)})")
    res = {}
    for c, worst in sel.items():
        drop = Bk[c] == worst
        inc = pd.Series(0.0, index=days)
        inc.loc[drop[drop].index] = -0.5 * net_th[drop]
        # placebo: drop the same number of trades per year at random
        rng = np.random.default_rng(17)
        yrs = T.index.year
        nd = pd.Series(drop.values, index=yrs).groupby(level=0).sum()
        sims = []
        for _ in range(1000):
            s = 0.0
            for y, k in nd.items():
                cand = net_th[yrs == y].values
                s += -0.5 * rng.choice(cand, size=int(k), replace=False).sum()
            sims.append(s / len(days))
        pct = float((np.array(sims) < inc.mean()).mean() * 100)
        r0, e0 = b3["r"], b3["eh"]
        i2 = inc.reindex(r0.index).fillna(0.0)
        rv, ev = r0 + i2, e0 + i2 - 0.5 * i2.mean()
        mc = TF.mc_tax(ev, 0.35, start=3000, monthly=1000)
        ds = PB.dsr(inc, n_trials=623 + len(sel))
        res[c] = dict(inc=inc, pct=pct, mc=mc, dsr=ds)
        print(f"  AG drop {c} B{worst} ({int(drop.sum())} trades): " +
              "  ".join(f"{lab} {inc[a:z].mean()*252*100:+5.2f}pp" for lab, a, z in HALVES) +
              f" | NW t {TF.nw_t(inc):+5.2f} | placebo {pct:5.1f} | B3 maxDD {B.stats(rv)[2]*100:5.1f} (base {B.stats(r0)[2]*100:5.1f}) "
              f"| P50 {mc['dd50']:.1%} (base {b3['mc']['dd50']:.1%}) | DSR {ds['dsr']:.2f}")
        a, b = inc.mean() * 252, inc["2024":].mean() * 252
        print("      $/yr " + " | ".join(f"${E/1e3:g}k {a*E:+7,.0f} ({b*E:+7,.0f})" for E in SIZES))
    pickle.dump(dict(F=F, Bk=Bk, sel=sel, res=res), open(SCR / "conviction_ag_res.pkl", "wb"))


if __name__ == "__main__":
    main()
