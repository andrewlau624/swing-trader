"""Addendum NN: recurring INDEX MECHANICS as structural, ticker-agnostic flows.

    # once, under the heavy lock (panel + night candidates):
    PYTHONPATH=. .venv/bin/python -m research.sim.index_mechanics_data
    PYTHONPATH=. .venv/bin/python -m research.sim.index_mechanics_data night
    PYTHONPATH=. .venv/bin/python -m research.sim.index_mechanics_data d2020
    # then (no lock; ~20 s):
    PYTHONPATH=. .venv/bin/python -m research.sim.index_mechanics q1 q2 q3 q4 q5 q6 q7

Pre-registered (scratchpad addenda/index_mechanics.md, stamped Mon Sep 28 20:53:38 PDT 2026),
12 variants, all reported:
  Q1 S&P 500 changes. A = press-release date (after the close), T = last session before the
     effective date (index funds trade its close auction).
     S1 adds: long  A+1 close -> T close        S2 adds: SHORT T close -> T+5 close
     S3 dels: long  T close -> T+1 open         S4 dels: long  T close -> T+5 close
     S5 dels: SHORT A+1 close -> T close
     placebo: random same-vol20-decile names (price > $5, ADV >= $20M), same dates, 50 seeds
  Q2 Russell recon: single-name membership UNTESTABLE (no lists, no shares outstanding).
     R1 IWM-SPY recon-day close->close, R2 IWM(-SPY) recon close -> next open. Descriptive, n~10.
  Q3 LETF rebalancing flow, flow day = |instrument prev close -> 15:30| > 2%
     L1 noise leg flattens at 15:30 on flow days (own instrument, QQQ and SMH)
     L2 night per-name fraction x1.5 (cap 0.15) when QQQ prev close -> 15:30 <= -2%
  Q4 month-end pension rebalancing, rel = SPY MTD - TLT MTD at the IBS signal close; window =
     IBS entries (d+1 open) in the last 3 sessions of the month; |rel| > 3%
     M1 IBS x1.5 if rel < -3%, x0.5 if rel > +3%     M2 skip IBS if rel > +3%
     M3 SPY open(L-2) -> close(L): long rel < -3%, short rel > +3% (signal at close L-3)
POST-HOC (added after seeing Q1-Q4; at most SHADOW):
  P1 (q5) M3 as a taxable SPY sleeve on V7, w 0.5, noise cap cut on sleeve days
  P2 (q5-q7) night per-name x0.5 when QQQ prev close -> 15:30 <= -2% (the opposite of L2):
     taxable V7, 2020 holdout (per name), placebo, Roth b1, COVID episode
  P3 (q5) S5 pooled 2016-26 robustness (median, drop top-5)
Costs: 3bp/side flat, tier, tier_hi (single names: book.cost_bps; ETFs 1bp tier / 3bp tier_hi).
"""
from __future__ import annotations

import copy
import dataclasses
import pickle
import sys

import numpy as np
import pandas as pd

from . import book as B
from . import data as D
from . import growth as G
from . import index_mechanics_data as IM

PER = [("2016-20", "2016-01-01", "2020-12-31"), ("2021-23", "2021-01-01", "2023-12-31"),
       ("2024-26", "2024-01-01", "2026-12-31")]
COSTS = [3.0, "tier", "tier_hi"]
L = []


def say(s=""):
    print(s, flush=True); L.append(s)


def cl_t(x: pd.Series) -> tuple[float, float, int]:
    """Day-clustered mean (bp) and t: average events on the same date first."""
    x = x.dropna()
    if len(x) < 3:
        return np.nan, np.nan, len(x)
    g = x.groupby(level=0).mean()
    t = g.mean() / (g.std(ddof=1) / np.sqrt(len(g))) if len(g) > 2 and g.std() > 0 else np.nan
    return x.mean() * 1e4, t, len(x)


def nw_t(x: pd.Series, lags: int = 5) -> float:
    x = np.asarray(x.fillna(0), float); n = len(x); m = x.mean(); e = x - m
    v = e @ e / n
    for k in range(1, lags + 1):
        v += 2 * (1 - k / (lags + 1)) * (e[k:] @ e[:-k]) / n
    return m / np.sqrt(v / n) if v > 0 else np.nan


def fmt3(r: pd.Series, a="2021-02-01", z="2026-09-30") -> str:
    r = r[a:z]
    x, y, f = B.stats(r[:"2023-12-31"]), B.stats(r["2024-01-01":]), B.stats(r)
    return (f"{x[0]*100:5.1f}/{x[1]:4.2f}/{x[2]*100:3.0f}  {y[0]*100:5.1f}/{y[1]:4.2f}/{y[2]*100:3.0f}  "
            f"{f[0]*100:5.1f}/{f[1]:4.2f}/{f[2]*100:3.0f}")


# ======================================================== Q1 S&P 500
Q1 = {  # name: (kind, window, side)
    "S1 adds run-up A+1c->Tc (long)": ("add", "S1", 1),
    "S2 adds post T c->T+5c (SHORT)": ("add", "S4", -1),
    "S3 dels T c->T+1 open (long)": ("del", "S3", 1),
    "S4 dels T c->T+5c (long)": ("del", "S4", 1),
    "S5 dels pre A+1c->Tc (SHORT)": ("del", "S1", -1),
}


def spy_window(ev: pd.DataFrame, win: str) -> pd.Series:
    P = D.etf(); C, O = P["close"]["SPY"], P["open"]["SPY"]
    ix = C.index
    out = []
    for e in ev.itertuples():
        t = ix.get_indexer([e.T])[0]; a = ix.get_indexer([e.a1])[0]
        if t < 0 or a < 0 or t + 5 >= len(ix):
            out.append(np.nan); continue
        out.append({"S1": C.iloc[t] / C.iloc[a] - 1, "S3": O.iloc[t + 1] / C.iloc[t] - 1,
                    "S4": C.iloc[t + 5] / C.iloc[t] - 1, "gapA": O.iloc[a] / C.iloc[a - 1] - 1}[win])
    return pd.Series(out, index=ev.index)


def q1():
    ev = pickle.load(open(IM.CACHE, "rb"))
    ev = ev[ev.found & ev["T"].notna()].copy()
    say("== Q1 S&P 500 additions / deletions (Wikipedia changes table, press-release dates)")
    say(f"events with bars: adds {int((ev.kind=='add').sum())}, dels {int((ev.kind=='del').sum())}; "
        f"median A->T sessions {ev.n_run.median():.0f}; T moved to the listed date by volume: "
        f"{ev.shifted.mean():.0%}; T-day volume / ADV median adds {ev[ev.kind=='add'].volT.median():.1f}x, "
        f"dels {ev[ev.kind=='del'].volT.median():.1f}x")
    g = ev.dropna(subset=["gapA"])
    for k in ("add", "del"):
        x = g[g.kind == k]
        say(f"  diagnostic: announcement gap (A close -> A+1 open, not tradable) {k}: "
            + "  ".join(f"{lab} {x[(x.a1>=a)&(x.a1<=z)].gapA.mean()*1e4:+.0f}bp n{int(((x.a1>=a)&(x.a1<=z)).sum())}"
                        for lab, a, z in PER))
    rng = np.random.default_rng(3)
    res = {}
    say(f"\n{'variant':34s} {'period':8s} {'n':>4s} {'gross':>7s} {'3bp':>7s} {'tier':>7s} {'tier_hi':>8s} "
        f"{'t(cl)':>6s} {'SPYadj':>7s} {'placebo':>8s}")
    for name, (kind, win, side) in Q1.items():
        x = ev[(ev.kind == kind) & ev[win].notna()].copy()
        x["spy"] = spy_window(x, win)
        x = x.set_index("T").sort_index()
        for lab, a, z in PER:
            y = x[a:z]
            if len(y) < 3:
                say(f"{name:34s} {lab:8s} {len(y):4d}  (too few)"); continue
            gross = side * y[win]
            out = [gross.mean() * 1e4]
            for c in COSTS:
                cb = B.cost_bps(c, y.price.values, y.adv.values)
                out.append((gross - 2 * cb / 1e4).mean() * 1e4)
            net = gross - 2 * B.cost_bps("tier", y.price.values, y.adv.values) / 1e4
            m, t, n = cl_t(net)
            adj = (side * (y[win] - y.spy)).mean() * 1e4
            pools = y[win + "_pool"].values
            beats = 0
            for _ in range(50):
                pl = np.array([side * p[rng.integers(len(p))] if isinstance(p, np.ndarray) and len(p) else np.nan
                               for p in pools])
                beats += np.nanmean(gross.values) > np.nanmean(pl)
            res[(name, lab)] = (out[2], t, beats / 50, n)
            say(f"{name:34s} {lab:8s} {n:4d} {out[0]:+7.1f} {out[1]:+7.1f} {out[2]:+7.1f} {out[3]:+8.1f} "
                f"{t:+6.2f} {adj:+7.1f} {beats/50:8.0%}")
    say("\n  fit/judge: best variant by tier bp in 2021-23 -> its 2024-26; and the reverse")
    for fit, jud in (("2021-23", "2024-26"), ("2024-26", "2021-23")):
        best = max(Q1, key=lambda k: res.get((k, fit), (-1e9,))[0])
        say(f"    fit {fit}: {best} {res[(best, fit)][0]:+.1f}bp -> judge {jud} {res[(best, jud)][0]:+.1f}bp "
            f"(t {res[(best, jud)][1]:+.2f}, placebo {res[(best, jud)][2]:.0%})")
    # the book-relevant yardstick: events per year and what a pass would be worth
    yrs = (ev["T"].max() - ev["T"].min()).days / 365.25
    say(f"  frequency: {len(ev[ev.kind=='add'])/yrs:.0f} adds/yr, {len(ev[ev.kind=='del'])/yrs:.0f} dels/yr "
        f"(clustered on quarterly rebalance dates)")
    return res


# ======================================================== Q2 Russell
def q2(s):
    P = D.etf(); C, O = P["close"], P["open"]
    ix = C.index
    say("\n== Q2 Russell reconstitution (fourth Friday of June). Single-name membership: UNTESTABLE here")
    rows = []
    for d in IM.RUSSELL_RECON:
        d = pd.Timestamp(d)
        if d not in ix:
            continue
        t = ix.get_loc(d)
        if t + 1 >= len(ix):
            continue
        r1 = (C.at[d, "IWM"] / C.iloc[t - 1]["IWM"] - 1) - (C.at[d, "SPY"] / C.iloc[t - 1]["SPY"] - 1)
        iw = O.iloc[t + 1]["IWM"] / C.at[d, "IWM"] - 1
        sp = O.iloc[t + 1]["SPY"] / C.at[d, "SPY"] - 1
        nd = s.N.get(d)
        night = float(np.mean(nd.ret - 2 * B.cost_bps("tier", nd.price, nd.adv) / 1e4)) if nd is not None else np.nan
        rows.append((d.date(), r1 * 1e4, iw * 1e4, (iw - sp) * 1e4, night * 1e4 if np.isfinite(night) else np.nan,
                     len(nd.syms) if nd is not None else 0))
    df = pd.DataFrame(rows, columns=["recon", "R1 IWM-SPY c->c", "R2 IWM c->o", "R2 IWM-SPY c->o",
                                     "night leg tier bp/name", "night n"])
    say(df.round(1).to_string(index=False))
    # base rate: all Fridays
    fr = ix[ix.weekday == 4]
    base = []
    for d in fr:
        t = ix.get_loc(d)
        if t < 1 or t + 1 >= len(ix):
            continue
        base.append(((C.at[d, "IWM"] / C.iloc[t-1]["IWM"]) - (C.at[d, "SPY"] / C.iloc[t-1]["SPY"])) * 1e4)
    base = np.array(base)
    m1 = df["R1 IWM-SPY c->c"]
    say(f"  R1 mean {m1.mean():+.1f}bp (t {m1.mean()/(m1.std()/np.sqrt(len(m1))):+.2f}, n {len(m1)}); all Fridays "
        f"{np.nanmean(base):+.1f}bp sd {np.nanstd(base):.0f}. R2 IWM-SPY mean {df['R2 IWM-SPY c->o'].mean():+.1f}bp "
        f"(t {df['R2 IWM-SPY c->o'].mean()/(df['R2 IWM-SPY c->o'].std()/np.sqrt(len(df))):+.2f})")
    return df


# ======================================================== shared book helpers
def v7_params(cost, **over):
    kw = {**G.V7, **G.cfg(1.0, 0.5, 2, None), "night_cost": cost}
    kw.update(over)
    return B.Params(**kw)


def load_book_sim():
    from .validate import load_sim
    s = load_sim()
    N = pickle.load(open(IM.NCACHE, "rb"))
    s.N = N["N10"]; s._N15 = N["N15"]
    return s


def book_report(tag, df, base=None):
    r = df["r"]
    line = f"  {tag:44s} {fmt3(r)}"
    if base is not None:
        d = r - base["r"]
        dsh = [B.stats(r[a:z])[1] - B.stats(base["r"][a:z])[1]
               for a, z in (("2021-02-01", "2023-12-31"), ("2024-01-01", "2026-12-31"))]
        line += f"  dSharpe {dsh[0]:+.2f}/{dsh[1]:+.2f}  NW t(diff) {nw_t(d):+.2f}  {d.mean()*252*100:+.2f}pp/yr"
    say(line)
    return r


def stress(tag, df):
    e = G.eh(df)
    es = B.stats(e)
    m1 = G.mc(e, 3000, 1000); m2 = G.mc(e, 10000, 0)
    r = df["r"]
    ep = {k: float((1 + r[a:b]).prod() - 1) for k, (a, b) in
          {"2022": ("2022-01-01", "2022-12-31"), "Apr25": ("2025-04-02", "2025-04-08")}.items()}
    say(f"  {tag:44s} EH {es[0]*100:5.1f}/{es[1]:4.2f}/{es[2]*100:3.0f} | MC $3k+1k med ${m1['med']:,.0f} "
        f"P30 {m1['dd30']:.0%} P50 {m1['dd50']:.0%} | $10k med ${m2['med']:,.0f} P30 {m2['dd30']:.0%} | "
        f"2022 {ep['2022']*100:+.1f}% Apr25 {ep['Apr25']*100:+.1f}% worst day {r.min()*100:.1f}% "
        f"worst month {G.monthly_worst(r)*100:.1f}%")


# ======================================================== Q3 LETF flow
def flow_frame(sym: str) -> pd.DataFrame:
    M = D.minutes(sym)
    C = M["close"]
    pc = C.iloc[:, 389].shift(1)
    f = pd.DataFrame(index=C.index)
    f["d1530"] = C.iloc[:, 360] / pc - 1
    f["late"] = C.iloc[:, 389] / C.iloc[:, 360] - 1          # what the noise leg holds after 15:30
    auc = D.etf()["close"][sym].reindex(C.index)
    f["late_auc"] = auc / C.iloc[:, 360] - 1
    f["night"] = (D.etf()["open"][sym].shift(-1) / D.etf()["close"][sym]).reindex(C.index) - 1
    return f


def q3(s):
    from .late_momentum import noise_pos_1530
    say("\n== Q3 LETF rebalancing flow: flow day = |prev close -> 15:30| > 2%")
    F = {k: flow_frame(k) for k in ("QQQ", "SMH")}
    pos = {k: noise_pos_1530(k) for k in ("QQQ", "SMH")}
    for k, f in F.items():
        flow = f.d1530.abs() > 0.02
        sg_ = np.sign(f.d1530)
        say(f"  {k}: flow days/yr {flow.mean()*252:.0f}")
        for lab, a, z in PER:
            ff = f[a:z]; fl = flow[a:z]
            mom = (sg_[a:z] * ff.late)[fl]
            ngt = (sg_[a:z] * ff.night)[fl]
            p = pos[k].reindex(ff.index).fillna(0)
            held = (p * ff.late)[fl]
            say(f"    {lab}: n {int(fl.sum()):3d} | 15:30->close in day's direction {mom.mean()*1e4:+6.1f}bp "
                f"(t {mom.mean()/(mom.std()/np.sqrt(len(mom))):+.2f}) | close->open in day's dir "
                f"{ngt.mean()*1e4:+6.1f}bp (t {ngt.mean()/(ngt.std()/np.sqrt(len(ngt))):+.2f}) | noise leg "
                f"15:30->close P&L unlevered {held.mean()*1e4:+6.1f}bp, in position {(p[fl]!=0).mean():.0%}")
    # ---- book
    say("\n  V7 book (Sim.replay, $3k + $1k/21 sessions)          2021-23          2024-26          2021-26")
    out = {}
    for c in COSTS:
        base = s.replay(v7_params(c))
        book_report(f"V7 shipped @{c}", base)
        # L1: remove the post-15:30 part of the noise P&L on flow days (turnover unchanged: the
        # close exit moves to 15:30)
        s1 = copy.copy(s); s1.NZ = {}
        for k, z in s.NZ.items():
            f = F[k].reindex(z.index); p = pos[k].reindex(z.index).fillna(0)
            fl = (f.d1530.abs() > 0.02).fillna(False)
            z2 = z.copy(); z2.loc[fl, "ret"] = z.loc[fl, "ret"] - (p * f.late)[fl]
            s1.NZ[k] = z2
        l1 = s1.replay(v7_params(c))
        book_report(f"L1 flatten noise at 15:30 on flow days @{c}", l1, base)
        # L2: night x1.5 per name (cap 0.15) on QQQ <= -2% at 15:30
        q = F["QQQ"].d1530
        s2 = copy.copy(s); s2.N = dict(s.N)
        ndays = 0
        for d in s.N:
            if d in q.index and q.at[d] <= -0.02 and d in s._N15:
                n15 = s._N15[d]
                s2.N[d] = dataclasses.replace(n15, frac=min(n15.frac * 1.5, 0.15)) if len(n15.syms) else s.N[d]
                ndays += 1
        l2 = s2.replay(v7_params(c))
        book_report(f"L2 night x1.5 on QQQ<=-2% days ({ndays}) @{c}", l2, base)
        out[c] = (base, l1, l2)
    # night leg per-name return on flow-down days vs others (tier)
    q = F["QQQ"].d1530
    for lab, a, z in PER[1:]:
        xs = {True: [], False: []}
        for d, nd in s.N.items():
            if not (pd.Timestamp(a) <= d <= pd.Timestamp(z)) or d not in q.index:
                continue
            net = nd.ret - 2 * B.cost_bps("tier", nd.price, nd.adv) / 1e4
            xs[bool(q.at[d] <= -0.02)].append(float(np.mean(net)))
        say(f"  night leg mean per-name tier, {lab}: QQQ<=-2% nights {np.mean(xs[True])*1e4:+.1f}bp "
            f"(n {len(xs[True])}) vs other nights {np.mean(xs[False])*1e4:+.1f}bp (n {len(xs[False])})")
    return out


# ======================================================== Q4 month-end
def month_frame():
    P = D.etf(); C, O = P["close"], P["open"]
    ix = C.index
    per = ix.to_period("M")
    pos_from_end = pd.Series(ix, index=ix).groupby(per).cumcount(ascending=False)   # 0 = last session
    f = pd.DataFrame(index=ix)
    f["from_end"] = pos_from_end.values
    # MTD from the prior month's last close
    cl = C[["SPY", "TLT"]]
    pm = cl.groupby(per).tail(1)
    pm.index = pm.index.to_period("M") + 1
    b = pm.reindex(per).values
    mtd = cl.values / b - 1
    f["rel"] = mtd[:, 0] - mtd[:, 1]
    return f


def ibs_window_days(s, f):
    """IBS signal days d whose entry session d+1 is one of the month's last 3 sessions."""
    ix = f.index
    nxt = pd.Series(ix[1:].tolist() + [pd.NaT], index=ix)
    out = {}
    for d in s.I:
        if d not in ix:
            continue
        e = nxt.at[d]
        if pd.isna(e) or f.at[e, "from_end"] > 2:
            continue
        out[d] = f.at[d, "rel"]
    return pd.Series(out)


def replay_scaled(s, p0: B.Params, scale: dict, start=3000.0, monthly=1000.0):
    """Sim.replay with a per-day IBS weight multiplier (daytime noise cap recomputed, never above V7's)."""
    ps = {}
    for k in set(scale.values()):
        w = p0.ibs_w * k
        room = 1 - w * 0.5 - p0.conviction_w * G.R3X
        ps[k] = dataclasses.replace(p0, ibs_w=w, noise_cap=min(p0.noise_cap, max(0.0, room / 0.5)))
    E, dep, rows = start, start, []
    for i, d in enumerate(s.days):
        if i and i % 21 == 0:
            E += monthly; dep += monthly
        p = ps[scale[d]] if d in scale else p0
        before = E
        pl, info = s.day_pnl(E, d, p)
        E += pl
        k = before if before else 1.0
        rows.append((d, E, pl / k, info["night"] / k, info["ibs"] / k, info["noise"] / k))
    return pd.DataFrame(rows, columns=["date", "E", "r", "r_night", "r_ibs", "r_noise"]).set_index("date")


def q4(s):
    say("\n== Q4 month-end pension rebalancing: rel = SPY MTD - TLT MTD at the IBS signal close, |rel| > 3%")
    f = month_frame()
    W = ibs_window_days(s, f)
    # trade-level: IBS trades in the window by rel bucket (all periods; s.I starts 2017)
    for lab, a, z in PER:
        w = W[a:z]
        cells = []
        for nm, m in (("rel<-3%", w < -0.03), ("mid", w.abs() <= 0.03), ("rel>+3%", w > 0.03)):
            rr = [np.mean([r for _, _, r in s.I[d]]) - 2e-4 for d in w.index[m]]
            cells.append(f"{nm} {np.mean(rr)*1e4:+6.1f}bp n{len(rr):3d}" if rr else f"{nm}   n  0")
        allr = [np.mean([r for _, _, r in v]) - 2e-4 for d, v in s.I.items() if pd.Timestamp(a) <= d <= pd.Timestamp(z)]
        say(f"  IBS trades in window {lab}: " + " | ".join(cells) + f" | all IBS days {np.mean(allr)*1e4:+.1f}bp")
    # M3 mechanism, SPY
    P = D.etf(); C, O = P["close"]["SPY"], P["open"]["SPY"]
    ix = f.index
    sig_days = ix[f.from_end.values == 3]
    rows = []
    for d in sig_days:
        t = ix.get_loc(d)
        if t + 3 >= len(ix):
            continue
        rel = f.at[d, "rel"]
        side = 1 if rel < -0.03 else (-1 if rel > 0.03 else 0)
        rows.append((d, side, C.iloc[t + 3] / O.iloc[t + 1] - 1))
    m3 = pd.DataFrame(rows, columns=["d", "side", "r"]).set_index("d")
    # placebo: random non-window 3-session spans (open t+1 -> close t+3), same sides
    allr = pd.Series(C.shift(-3).values / O.shift(-1).values - 1, index=ix)
    nonw = allr[(f.from_end > 5) & allr.notna()]
    rng = np.random.default_rng(5)
    say(f"  M3 SPY open(L-2)->close(L), side by rel (short allowed), {'':6s} n     gross    3bp   t   placebo")
    m3res = {}
    for lab, a, z in PER:
        y = m3[a:z]; y = y[y.side != 0]
        g = y.side * y.r
        net = g - 2 * 3.0 / 1e4
        pv = nonw[a:z]
        beats = np.mean([g.mean() > (y.side.values * rng.choice(pv.values, len(y))).mean() for _ in range(200)])
        t = g.mean() / (g.std() / np.sqrt(len(g))) if len(g) > 2 else np.nan
        m3res[lab] = net.mean()
        say(f"    {lab}: n {len(y):3d} (long {int((y.side>0).sum())}, short {int((y.side<0).sum())})  "
            f"{g.mean()*1e4:+6.1f}bp {net.mean()*1e4:+6.1f}bp  t {t:+.2f}  placebo {beats:.0%}")
    # book: M1 / M2 on V7
    say("\n  V7 book                                                2021-23          2024-26          2021-26")
    out = {}
    Wb = W["2021-02-01":]
    for c in COSTS:
        p0 = v7_params(c)
        base = s.replay(p0)
        book_report(f"V7 shipped @{c}", base)
        sc1 = {d: (1.5 if r < -0.03 else 0.5) for d, r in Wb.items() if abs(r) > 0.03}
        m1 = replay_scaled(s, p0, sc1)
        book_report(f"M1 IBS x1.5/x0.5 ({len(sc1)} days) @{c}", m1, base)
        sc2 = {d: 0.0 for d, r in Wb.items() if r > 0.03}
        m2 = replay_scaled(s, p0, sc2)
        book_report(f"M2 skip IBS rel>+3% ({len(sc2)} days) @{c}", m2, base)
        out[c] = (base, m1, m2, sc1, sc2)
    # placebo for M1/M2 at tier: the same multipliers on random IBS days outside the window
    base, m1, m2, sc1, sc2 = out["tier"]
    pool = [d for d in s.I if d >= pd.Timestamp("2021-02-01") and d not in W.index and d in set(s.days)]
    rng = np.random.default_rng(9)
    for nm, sc, real in (("M1", sc1, m1), ("M2", sc2, m2)):
        dr = [B.stats(real["r"][a:z])[1] for a, z in (("2021-02-01", "2023-12-31"), ("2024-01-01", "2026-12-31"))]
        beats = np.zeros(2)
        vals = list(sc.values())
        for k in range(30):
            pick = rng.choice(len(pool), len(vals), replace=False)
            scp = {pool[i]: v for i, v in zip(pick, vals)}
            pr = replay_scaled(s, v7_params("tier"), scp)["r"]
            ps = [B.stats(pr[a:z])[1] for a, z in (("2021-02-01", "2023-12-31"), ("2024-01-01", "2026-12-31"))]
            beats += np.array(dr) > np.array(ps)
        say(f"  {nm} placebo (same multipliers on random non-window IBS days, 30 seeds): Sharpe beats "
            f"{beats[0]/30:.0%} / {beats[1]/30:.0%}")
    return out


def main():
    args = set(sys.argv[1:]) or {"q1", "q2", "q3", "q4"}
    if "q1" in args:
        q1()
    s = None
    if args & {"q2", "q3", "q4", "q5", "q6", "q7"}:
        s = load_book_sim()
    if "q2" in args:
        q2(s)
    if "q3" in args:
        out3 = q3(s)
        say("\n  stress (tier_hi)")
        base, l1, l2 = out3["tier_hi"]
        for nm, df in (("V7", base), ("L1", l1), ("L2", l2)):
            stress(nm, df)
    if "q4" in args:
        out4 = q4(s)
        say("\n  stress (tier_hi)")
        base, m1, m2, _, _ = out4["tier_hi"]
        for nm, df in (("V7", base), ("M1", m1), ("M2", m2)):
            stress(nm, df)
    if "q5" in args:
        s = s or load_book_sim()
        q5(s)
    if "q6" in args:
        s = s or load_book_sim()
        q6(s)
    if "q7" in args:
        s = s or load_book_sim()
        q7(s)
    open(IM.SCR / f"index_mechanics_{'_'.join(sorted(args))}.txt", "w").write("\n".join(L))



# ======================================================== POST-HOC (after seeing Q1-Q4; max verdict SHADOW)
def m3_trades():
    f = month_frame()
    P = D.etf(); C, O = P["close"]["SPY"], P["open"]["SPY"]
    ix = f.index
    rows = []
    for d in ix[f.from_end.values == 3]:
        t = ix.get_loc(d)
        if t + 3 >= len(ix):
            continue
        rel = f.at[d, "rel"]
        side = 1 if rel < -0.03 else (-1 if rel > 0.03 else 0)
        if side:
            rows.append((d, ix[t + 1], ix[t + 3], side, rel, O.iloc[t + 1], C.iloc[t + 3]))
    return pd.DataFrame(rows, columns=["d", "e", "x", "side", "rel", "po", "pc"])


def q5(s):
    say("\n== POST-HOC P1: M3 detail (pooled t, by side), and M3 as a taxable sleeve on V7")
    m = m3_trades()
    m["r"] = m.side * (m.pc / m.po - 1)
    for lab, a, z in PER + [("2016-26", "2016-01-01", "2026-12-31")]:
        y = m[(m.d >= a) & (m.d <= z)]
        for sd, nm in ((1, "long"), (-1, "short")):
            q = y[y.side == sd].r
            say(f"  {lab} {nm:5s} n {len(q):3d} gross {q.mean()*1e4:+6.1f}bp" +
                (f" t {q.mean()/(q.std()/np.sqrt(len(q))):+.2f}" if len(q) > 2 else ""))
        q = y.r
        say(f"  {lab} both  n {len(q):3d} gross {q.mean()*1e4:+6.1f}bp t {q.mean()/(q.std()/np.sqrt(len(q))):+.2f}")
    # also: dose-response in rel (not a variant, a diagnostic) - all month ends, SPY L-2 open -> L close
    f = month_frame(); P = D.etf(); C, O = P["close"]["SPY"], P["open"]["SPY"]; ix = f.index
    rr = []
    for d in ix[f.from_end.values == 3]:
        t = ix.get_loc(d)
        if t + 3 < len(ix):
            rr.append((f.at[d, "rel"], C.iloc[t + 3] / O.iloc[t + 1] - 1))
    rr = pd.DataFrame(rr, columns=["rel", "r"])
    rr["b"] = pd.cut(rr.rel, [-1, -0.03, -0.01, 0.01, 0.03, 1])
    say("  SPY L-2 open -> L close by rel bucket, 2016-26 (bp, n): " +
        "  ".join(f"{k} {g.r.mean()*1e4:+.0f} ({len(g)})" for k, g in rr.groupby("b", observed=True)))
    # sleeve: M3 notional w x equity from the entry open to the exit close (3 sessions), taxable
    # (short needs margin). Daytime margin: SPY at 50% eats w x 0.5 of room -> noise cap cut on those days.
    for w in (0.5,):
        for c in COSTS:
            p0 = v7_params(c)
            base = s.replay(p0)
            cb = {3.0: 3.0, "tier": 1.0, "tier_hi": 3.0}[c]
            room = 1 - p0.ibs_w * 0.5 - p0.conviction_w * G.R3X - w * 0.5
            p1 = dataclasses.replace(p0, noise_cap=min(p0.noise_cap, max(0.0, room / 0.5)))
            dayset, add = {}, {}
            for t in m.itertuples():
                span = C.loc[t.e:t.x].index
                prev = None
                for i, d in enumerate(span):
                    dayset[d] = p1
                    ref = O.at[d] if i == 0 else C.loc[:d].iloc[-2]
                    r = t.side * (C.at[d] / ref - 1)
                    if i == 0:
                        r -= cb / 1e4
                    if i == len(span) - 1:
                        r -= cb / 1e4
                    add[d] = add.get(d, 0.0) + w * r
            E, dep, rows = 3000.0, 3000.0, []
            for i, d in enumerate(s.days):
                if i and i % 21 == 0:
                    E += 1000; dep += 1000
                before = E
                pl, info = s.day_pnl(E, d, dayset.get(d, p0))
                x = before * add.get(d, 0.0)
                E += pl + x
                k = before or 1.0
                rows.append((d, E, (pl + x) / k, info["night"] / k, info["ibs"] / k, (info["noise"] + x) / k))
            df = pd.DataFrame(rows, columns=["date", "E", "r", "r_night", "r_ibs", "r_noise"]).set_index("date")
            book_report(f"P1 V7 + M3 SPY sleeve w{w} @{c}", df, base)
            if c == "tier_hi":
                stress("P1 (tier_hi)", df)
    say("\n== POST-HOC P2: night leg x0.5 per name when QQQ prev close -> 15:30 <= -2% (the opposite of L2)")
    q = flow_frame("QQQ").d1530
    for c in COSTS:
        base = s.replay(v7_params(c))
        s2 = copy.copy(s); s2.N = dict(s.N)
        for d, nd in s.N.items():
            if d in q.index and q.at[d] <= -0.02:
                s2.N[d] = dataclasses.replace(nd, frac=nd.frac * 0.5)
        df = s2.replay(v7_params(c))
        book_report(f"P2 night x0.5 on QQQ<=-2% @{c}", df, base)
        if c == "tier_hi":
            stress("P2 (tier_hi)", df)
    say("\n== POST-HOC P3: S5 (short deletions A+1 close -> T close), pooled 2016-26")
    ev = pickle.load(open(IM.CACHE, "rb"))
    ev = ev[ev.found & ev["T"].notna() & (ev.kind == "del") & ev.S1.notna()].set_index("T").sort_index()
    net = -ev.S1 - 2 * B.cost_bps("tier", ev.price.values, ev.adv.values) / 1e4
    mu, t, n = cl_t(net)
    med = net.median() * 1e4
    say(f"  tier net mean {mu:+.1f}bp, median {med:+.1f}bp, day-clustered t {t:+.2f}, n {n}, "
        f"share positive {(net > 0).mean():.0%}; without the 5 largest |moves|: "
        f"{net.drop(net.abs().nlargest(5).index).mean()*1e4:+.1f}bp")


def p2_sim(s, flag, k=0.5):
    s2 = copy.copy(s); s2.N = dict(s.N)
    for d, nd in s.N.items():
        if d in flag:
            s2.N[d] = dataclasses.replace(nd, frac=nd.frac * k)
    return s2


def q6(s):
    """POST-HOC P2 follow-ups: 2020 holdout, placebo, Roth book."""
    from . import roth as RO
    q = flow_frame("QQQ").d1530
    flag = set(q.index[q <= -0.02])
    say("\n== POST-HOC P2 follow-ups: night x0.5 when QQQ prev close -> 15:30 <= -2%")
    d20 = pickle.load(open(IM.D20CACHE, "rb"))
    for lab, a, z in (("2020 (close-signal rebuild, biased +9bp/day)", "2020-01-01", "2020-10-31"),):
        xs = {True: [], False: []}
        for d, (ret, vol20, day_ret, n_raw, gap) in d20.items():
            if not (pd.Timestamp(a) <= d <= pd.Timestamp(z)):
                continue
            keep = np.nan_to_num(vol20) >= 0.6
            if keep.any():
                xs[d in flag].append(float(np.nanmean(ret[keep])) - 2 * 10 / 1e4)
        say(f"  {lab}: per-name night 10bp/side on flag nights {np.mean(xs[True])*1e4:+.1f}bp (n {len(xs[True])}) "
            f"vs other {np.mean(xs[False])*1e4:+.1f}bp (n {len(xs[False])})")
        cov = [d for d in d20 if pd.Timestamp("2020-02-19") <= d <= pd.Timestamp("2020-03-23")]
        say(f"  COVID crash window: {sum(d in flag for d in cov)} of {len(cov)} night-leg days flagged")
    # placebo: x0.5 on random night days, same count, 30 seeds (tier)
    base = s.replay(v7_params("tier"))
    real = p2_sim(s, flag).replay(v7_params("tier"))
    H = (("2021-02-01", "2023-12-31"), ("2024-01-01", "2026-12-31"))
    dr = np.array([B.stats(real["r"][a:z])[1] for a, z in H])
    nd_days = [d for d in s.N if d in set(s.days)]
    nflag = sum(d in flag for d in nd_days)
    rng = np.random.default_rng(13); beats = np.zeros(2)
    for _ in range(30):
        fl = set(rng.choice(nd_days, nflag, replace=False))
        pr = p2_sim(s, fl).replay(v7_params("tier"))["r"]
        beats += dr > np.array([B.stats(pr[a:z])[1] for a, z in H])
    say(f"  placebo (x0.5 on {nflag} random night-leg days, 30 seeds): Sharpe beats {beats[0]/30:.0%} / {beats[1]/30:.0%}")
    # Roth b1
    s07 = copy.copy(s)
    if not hasattr(s07, "BO"):
        s07.BO = B.breakout_days()
    rb = dict(tilt="live", weekend_scale=0.5, noise_on=False, conviction_w=0.0, margin_rate=0.0)
    for c in COSTS:
        r0 = RO.replay(s07, s.days, B.Params(night_cost=c, **rb), budget="night", noise_cap=1.5)
        s2 = p2_sim(s07, flag); s2.BO = s07.BO
        r1 = RO.replay(s2, s.days, B.Params(night_cost=c, **rb), budget="night", noise_cap=1.5)
        book_report(f"Roth b1 @{c}", r0)
        book_report(f"Roth b1 + P2 @{c}", r1, r0)


def q7(s):
    """POST-HOC P2: COVID 2020 crash episode, legs rebuilt as growth.covid_legs (cap 0.10)."""
    from swingtrader.daily import signals as sg
    from . import crash as CR
    q = flow_frame("QQQ").d1530
    flag = set(q.index[q <= -0.02])
    d20 = pickle.load(open(IM.D20CACHE, "rb"))
    ibs = pd.Series({d: float(np.mean([r for _, _, r in v])) - 2e-4 for d, v in s.I.items() if v})
    bo = B.breakout_days()
    say("\n== POST-HOC P2 COVID 2020 (Feb 19 - Mar 23), V7 weights, close-signal night rebuild (bias-corrected)")
    for k, lab in ((1.0, "V7"), (0.5, "V7 + P2")):
        night = {}
        for d in sorted(d20):
            ret, vol20, day_ret, n_raw, gap = d20[d]
            keep = np.nan_to_num(vol20) >= 0.6
            if not keep.any():
                night[d] = 0.0; continue
            r, v, dr = ret[keep], vol20[keep], day_ret[keep]
            per = min(1 / len(r), 0.10) * min(1.0, 30 / max(n_raw, 1)) * (k if d in flag else 1.0)
            x = per * sg.night_tilt(v, dr) * (0.5 if gap > 1 else 1.0)
            val = float((x * (np.nan_to_num(r) - 2 * CR.COST / 1e4)).sum())
            night[d] = val - 9.1e-4 * (val != 0)
        legs = ({0.10: pd.Series(night)}, ibs, s.bil, s.NZ, bo)
        p = dict(night_w=0.5, ibs_w=0.5, noise_cap=0.75, conviction_w=0.5, _cap=0.10)
        tot, dd, worst = G.covid_book(legs, p)
        say(f"  {lab:10s} COVID crash {tot*100:+.1f}%  maxDD {dd*100:.1f}%  worst day {worst*100:.1f}%")


if __name__ == "__main__":
    main()
