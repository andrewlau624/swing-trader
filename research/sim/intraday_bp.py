"""Addendum NN: how big should the intraday (noise + conviction) legs be, given what the broker
actually allows after the PDT rule's retirement?

    PYTHONPATH=. .venv/bin/python -m research.sim.intraday_bp            # ~20-30 min, no heavy lock
    (reads data/research/night/sim_cache_raw.pkl, data/research/program/cache_rawprice.pkl,
     cache_macro_events.pkl, cache_taxable_frontier.pkl; loads QQQ/SMH/TQQQ minute matrices only)

FACTS (addendum draft, section 1): FINRA Rule 4210 (Notice 26-10, effective 2026-06-04) replaced
day-trading buying power with an intraday margin deficit measured against MAINTENANCE margin.
Schwab's Intraday Margin Buying Power (from 2026-07-13, margin accounts >= $2,000) uses a default 25%
requirement: up to 4x intraday. 3x ETFs keep 75%. The live code reads the multiplier from
max(dayTradingBuyingPower, buyingPower) / liquidationValue, and has only ever seen 2.48.

PRE-REGISTERED (stamped Tue Sep 29 00:11:55 PDT 2026, before any number):
  books  B1 V7 1.0x cap .10 conv .5 | B2 moderate10 1.0x cap .15 conv 0 | B3 moderate10c cap .15 conv .5
  cap    min(3.5, mult * (1 - 0.75 conv) - ibs_w); baseline mult 2
  V1 mult 3 | V2 mult 4 | V3 Kelly: mult 4 and noise leverage x1.5 inside the cap
  refs   R1 mult 2.48 (live today) | R2 mult 3.33 (30% house maintenance)
  costs  night 3bp / tier / tier_hi; intraday as shipped (noise 0.5bp/fill, conviction 1.5bp/side),
         at tier_hi noise 1.5bp/fill and conviction 3bp/side
"""
from __future__ import annotations

import copy
import pickle
import sys

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import book as B
from . import data as D
from . import growth as G
from . import macro_events as ME
from . import program_books as PB
from . import rawprice as RP
from . import taxable_frontier as TF
from .validate import load_sim

SCR = RP.SCR
OUT = f"{SCR}/intraday_bp_res.pkl"
COSTS = (3.0, "tier", "tier_hi")
BOOKS = {  # label: (gross, name cap, conviction)
    "B1 V7": (1.0, 0.10, 0.5),
    "B2 moderate10": (1.0, 0.15, 0.0),
    "B3 moderate10c": (1.0, 0.15, 0.5),
}
VARS = {  # label: (mult, kelly)   baseline first
    "M2 base": (2.0, 1.0),
    "R1 m2.48 (live)": (2.48, 1.0),
    "V1 m3": (3.0, 1.0),
    "R2 m3.33 (30%)": (10 / 3, 1.0),
    "V2 m4": (4.0, 1.0),
    "V3 m4 Kelly x1.5": (4.0, 1.5),
}
N_VARIANTS = 5
EXTRA_TH = {"noise_fill_bps": 1.0, "conv_side_bps": 1.5}   # tier_hi add-ons for the intraday legs
DATES = ["2020-03-09", "2020-03-12", "2020-03-16", "2020-03-18", "2022-09-13", "2025-04-03",
         "2025-04-04", "2025-04-07", "2025-04-09"]


# ------------------------------------------------------------------ intraday inputs by cost
def intraday_inputs(NZ0, BO0, cost, kelly):
    NZ = {}
    for s, z in NZ0.items():
        z = z.copy()
        if cost == "tier_hi":
            z["ret"] = z["ret"] - z["trades"] * EXTRA_TH["noise_fill_bps"] / 1e4
        z["lev"] = z["lev"] * kelly
        NZ[s] = z
    BO = BO0 - (2 * EXTRA_TH["conv_side_bps"] / 1e4 if cost == "tier_hi" else 0.0)
    return NZ, BO


def params(g, conv, mult, cost):
    kw = G.cfg(g, conv, mult)
    return B.Params(**{**G.V7, **kw, "night_cost": cost}), kw


def replay(s, N, g, conv, mult, kelly, cost, start=3000.0, monthly=1000.0):
    """taxable_frontier.replay with the intraday cap at `mult` (and the trade list for wash sales)."""
    s = copy.copy(s)
    s.N = N
    s.NZ, s.BO = intraday_inputs(S_NZ0, S_BO0, cost, kelly)
    ix = s.C.index
    pos = {d: i for i, d in enumerate(ix)}
    nxt = lambda d, k: ix[min(pos[d] + k, len(ix) - 1)]
    p, kw = params(g, conv, mult, cost)
    E, rows, T = start, [], []
    for i, d in enumerate(s.days):
        if i and i % 21 == 0:
            E += monthly
        pl, info = s.day_pnl(E, d, p)
        for t in TF.day_trades(s, E, d, p, nxt):
            T.append((d,) + t + (E,))
        k = E if E else 1.0
        rows.append((d, E, pl / k, info["night"] / k, info["ibs"] / k, info["noise"] / k,
                     (info["idle"] + info["margin"]) / k))
        E += pl
    df = pd.DataFrame(rows, columns=["date", "E", "r", "r_night", "r_ibs", "r_noise", "r_cash"]).set_index("date")
    tr = pd.DataFrame(T, columns=["book", "sym", "buy", "sell", "qty", "pnl", "E"])
    tr["frac"] = tr.pnl / tr.E
    return df, tr, kw


def extra_leg(nz, g, conv, mult, kelly, mult0=2.0, kelly0=1.0):
    """Additive daily increment of the noise leg vs the baseline cap (for NW t and the placebo):
    per instrument (lev_v - lev_b) * share and its return."""
    c1, c0 = G.cfg(g, conv, mult)["noise_cap"], G.cfg(g, conv, mult0)["noise_cap"]
    dl, rr = {}, {}
    for s, share in G.S2.items():
        z = nz[s]
        lv = np.minimum(z["lev"] * kelly, c1); lb = np.minimum(z["lev"] * kelly0, c0)
        dl[s] = (lv - lb) * share; rr[s] = z["ret"]
    return pd.DataFrame(dl), pd.DataFrame(rr)


def placebo(dl, rr, idx, n=500, seed=11):
    dl, rr = dl.reindex(idx).fillna(0), rr.reindex(idx).fillna(0)
    act = float((dl * rr).sum(axis=1).mean())
    rng = np.random.default_rng(seed)
    X = (dl * rr).values
    sims = np.array([(X * rng.choice([-1, 1], size=X.shape)).sum(axis=1).mean() for _ in range(n)])
    return act, float((sims < act).mean() * 100)


# ------------------------------------------------------------------ 2016-20 holdout and COVID
def holdout(legs, g, conv, mult, kelly, cost, a="2016-02-01", b="2020-12-31", ix=None, night=None):
    """program_books.tax_holdout (no F3) with the intraday cap at `mult`; night leg: raw 2020 rebuild,
    T-bills before 2020 (the pool does not exist there)."""
    _, ibs, bil, nz0, bo0 = legs
    nz, bo = intraday_inputs(nz0, bo0, cost, kelly)
    p = G.cfg(g, conv, mult)
    days = ix[(ix >= a) & (ix <= b)]
    out = {}
    for d in days:
        bl = float(np.nan_to_num(bil.get(d, 0.0)))
        nv = night.get(d, np.nan)
        x = p["night_w"] * float(nv) if np.isfinite(nv) else p["night_w"] * bl * (d < pd.Timestamp("2020-01-02"))
        iv = ibs.get(d, np.nan)
        x += p["ibs_w"] * (float(iv) if np.isfinite(iv) else bl)
        for sym, share in G.S2.items():
            z = nz[sym]
            if d in z.index:
                x += min(float(z.at[d, "lev"]), p["noise_cap"]) * share * float(z.at[d, "ret"])
        x += p["conviction_w"] * float(bo.get(d, 0.0))
        x -= max(0.0, p["ibs_w"] + p["night_w"] - 1) * 0.12 / 252
        out[d] = x
    return pd.Series(out)


# ------------------------------------------------------------------ 1-minute intraday paths
def noise_paths(sym, lookback=14):
    """Per session: the unlevered mark-to-market path of the noise-area rule, minute by minute, at the
    ADVERSE extreme of each minute (low for a long, high for a short). Same decisions as book.noise_days."""
    M = D.minutes(sym)
    C, V, H, L = M["close"].values, M["volume"].values, M["high"].values, M["low"].values
    O = M["open"].values[:, 0]
    days = M["close"].index
    move = np.abs(C / O[:, None] - 1)
    prevc = np.r_[np.nan, C[:-1, -1]]
    vwap = np.cumsum(C * V, axis=1) / np.maximum(np.cumsum(V, axis=1), 1)
    dec = set(range(sg.NOISE_FIRST, 390, sg.NOISE_STEP))
    out = {}
    for i in range(lookback + 1, len(days)):
        sigma = sg.noise_sigma(move[i - lookback:i])
        ub, lb = sg.noise_bounds(O[i], prevc[i], sigma)
        pos, entry, real = 0, None, 0.0
        path = np.zeros(390)
        for m in range(390):
            if m in dec:
                p = C[i, m]
                new = sg.noise_decide(pos, p, ub[m], lb[m], vwap[i, m])
                if new != pos:
                    if pos != 0:
                        real += pos * (p / entry - 1)
                    if new != 0:
                        entry = p
                    pos = new
                path[m] = real
                continue
            if pos == 0:
                path[m] = real
            else:
                adv = L[i, m] if pos == 1 else H[i, m]
                path[m] = real + pos * (adv / entry - 1)
        out[days[i]] = path
    return out


def conv_paths(sym="TQQQ", lookback=14, strength_min=B.STRENGTH_MIN):
    """book.breakout_days, as a minute path (adverse extreme)."""
    M = D.minutes(sym)
    C, V, H, L = M["close"].values, M["volume"].values, M["high"].values, M["low"].values
    O = M["open"].values[:, 0]
    days = M["close"].index
    move = np.abs(C / O[:, None] - 1)
    prevc = np.r_[np.nan, C[:-1, -1]]
    vwap = np.cumsum(C * V, axis=1) / np.maximum(np.cumsum(V, axis=1), 1)
    out = {}
    for i in range(lookback + 1, len(days)):
        sig = sg.noise_sigma(move[i - lookback:i])
        ub, lb = sg.noise_bounds(O[i], prevc[i], sig)
        pos, e, strength, xm = 0, None, 0.0, 389
        m0 = None
        for m in range(sg.NOISE_FIRST, 390, sg.NOISE_STEP):
            p = C[i, m]
            if pos == 0:
                pos, strength = sg.breakout_strength(p, ub[m], lb[m], sig[m])
                e = p; m0 = m
                if pos and strength < strength_min:
                    pos = 0; break
                if not pos:
                    continue
            elif (pos == 1 and p < max(ub[m], vwap[i, m])) or (pos == -1 and p > min(lb[m], vwap[i, m])):
                xm = m; break
        if pos == 0:
            continue
        path = np.zeros(390)
        for m in range(m0 + 1, 390):
            if m > xm:
                path[m] = path[xm]; continue
            adv = L[i, m] if pos == 1 else H[i, m]
            path[m] = pos * ((C[i, m] if m == xm else adv) / e - 1)
        out[days[i]] = path
    return out


def trough(d, g, conv, mult, kelly, NP, CP, nz):
    """Worst mark-to-market of the intraday legs within session d, fraction of equity."""
    p = G.cfg(g, conv, mult)
    x = np.zeros(390)
    for s, share in G.S2.items():
        if d in NP[s] and d in nz[s].index:
            x += min(float(nz[s].at[d, "lev"]) * kelly, p["noise_cap"]) * share * NP[s][d]
    if conv and d in CP:
        x += conv * CP[d]
    return float(x.min())


# ------------------------------------------------------------------ main
S_NZ0 = S_BO0 = None


def main():
    global S_NZ0, S_BO0
    s = load_sim(raw_price=True)
    rp = pickle.load(open(RP.CACHE, "rb"))
    Ns = dict(rp["raw"])
    me = pickle.load(open(ME.CACHE, "rb"))
    legs = me["legs"]
    S_NZ0 = {k: s.NZ[k] for k in G.S2}
    S_BO0 = legs[4]
    ix = s.C.index
    n20 = {cap: PB.night2020(rp["y2020"]["raw"][0], cap) for cap in (0.10, 0.15)}
    res = {}
    print(f"books x variants: {len(BOOKS)} x {len(VARS)}; rule variants counted: {N_VARIANTS}", flush=True)
    for bl, (g, cap, conv) in BOOKS.items():
        for vl, (mult, kel) in VARS.items():
            kw = G.cfg(g, conv, mult)
            for cost in COSTS:
                df, tr, _ = replay(s, Ns[cap], g, conv, mult, kel, cost)
                at, info = TF.after_tax(df.r, 0.35, trades=tr)
                e = G.eh(df)
                eat, _ = TF.after_tax(e, 0.35, trades=tr)
                x = dict(r=df.r, at=at, eh=e, eh_at=eat, noise=df.r_noise, cap=kw["noise_cap"])
                if cost != "tier":
                    x["mc"] = TF.mc_tax(e, 0.35, start=3000, monthly=1000)
                res[(bl, vl, cost)] = x
                print(f"  {bl:15s} {vl:18s} cap {kw['noise_cap']:4.2f} {str(cost):>8s} pre {PB.halves(df.r)} | "
                      f"AT {PB.cell(at)} | EH {PB.cell(e)} EH-AT {PB.cell(eat)}"
                      + (f" | MC med ${x['mc']['med']:,.0f} P30 {x['mc']['dd30']:.0%} ({x['mc']['dd30_acct']:.0%}) "
                         f"P50 {x['mc']['dd50']:.0%} ({x['mc']['dd50_acct']:.0%})" if "mc" in x else ""), flush=True)
            for cost in (3.0, "tier_hi"):
                ho = holdout(legs, g, conv, mult, kel, cost, ix=ix,
                             night=n20[cap][n20[cap].index < "2020-11-05"])
                res[(bl, vl, "ho", cost)] = ho
            print(f"  {bl:15s} {vl:18s} 2016-20 HO 3bp {PB.cell(res[(bl, vl, 'ho', 3.0)])} tier_hi "
                  f"{PB.cell(res[(bl, vl, 'ho', 'tier_hi')])}  COVID(th) "
                  f"{PB.ep(res[(bl, vl, 'ho', 'tier_hi')], '2020-02-19', '2020-03-23')*100:+.1f}%", flush=True)
    pickle.dump(res, open(OUT, "wb"))

    # ---------------- increments vs mult 2 (tier_hi), placebo, NW t
    print("\n== increments vs M2 base, tier_hi: dCAGR 21-23 / 24-26 / full / HO | EH-AT d | NW t | placebo pct")
    inc = {}
    for bl, (g, cap, conv) in BOOKS.items():
        b = res[(bl, "M2 base", "tier_hi")]
        for vl, (mult, kel) in list(VARS.items())[1:]:
            v = res[(bl, vl, "tier_hi")]
            d = (v["r"] - b["r"]).dropna()
            nzth, _ = intraday_inputs(S_NZ0, S_BO0, "tier_hi", 1.0)
            dl, rr = extra_leg(nzth, g, conv, mult, kel)
            act, pct = placebo(dl, rr, d.index)
            hv, hb = res[(bl, vl, "ho", "tier_hi")], res[(bl, "M2 base", "ho", "tier_hi")]
            dd = [B.stats(v["r"][a:z])[0] - B.stats(b["r"][a:z])[0] for _, a, z in PB.PER]
            dho = B.stats(hv)[0] - B.stats(hb)[0]
            deat = B.stats(v["eh_at"])[0] - B.stats(b["eh_at"])[0]
            t = TF.nw_t(d)
            inc[(bl, vl)] = dict(d21=dd[0], d24=dd[1], dfull=B.stats(v["r"])[0] - B.stats(b["r"])[0], dho=dho,
                                 deat=deat, t=t, pct=pct, act=act)
            print(f"  {bl:15s} {vl:18s} {dd[0]*100:+5.1f} / {dd[1]*100:+5.1f} / "
                  f"{inc[(bl, vl)]['dfull']*100:+5.1f} / HO {dho*100:+5.1f} | EH-AT {deat*100:+5.1f}pp | t {t:5.2f} | "
                  f"placebo {pct:5.1f}", flush=True)
        # V3 vs V2
        v, b2 = res[(bl, "V3 m4 Kelly x1.5", "tier_hi")], res[(bl, "V2 m4", "tier_hi")]
        d = (v["r"] - b2["r"]).dropna()
        nzth, _ = intraday_inputs(S_NZ0, S_BO0, "tier_hi", 1.0)
        dl, rr = extra_leg(nzth, g, conv, 4.0, 1.5, 4.0, 1.0)
        act, pct = placebo(dl, rr, d.index)
        dd = [B.stats(v["r"][a:z])[0] - B.stats(b2["r"][a:z])[0] for _, a, z in PB.PER]
        dho = B.stats(res[(bl, "V3 m4 Kelly x1.5", "ho", "tier_hi")])[0] - B.stats(res[(bl, "V2 m4", "ho", "tier_hi")])[0]
        deat = B.stats(v["eh_at"])[0] - B.stats(b2["eh_at"])[0]
        inc[(bl, "V3-V2")] = dict(d21=dd[0], d24=dd[1], dho=dho, deat=deat, t=TF.nw_t(d), pct=pct)
        print(f"  {bl:15s} {'V3 vs V2':18s} {dd[0]*100:+5.1f} / {dd[1]*100:+5.1f} / HO {dho*100:+5.1f} | "
              f"EH-AT {deat*100:+5.1f}pp | t {TF.nw_t(d):5.2f} | placebo {pct:5.1f}", flush=True)

    # ---------------- crashes, worst day/month (tier_hi)
    print("\n== crashes (tier_hi): COVID (2016-20 rebuild) | 2022 | Apr 2-8 2025 | worst day | worst month")
    for bl in BOOKS:
        for vl in VARS:
            r = res[(bl, vl, "tier_hi")]["r"]; ho = res[(bl, vl, "ho", "tier_hi")]
            print(f"  {bl:15s} {vl:18s} COVID {PB.ep(ho, '2020-02-19', '2020-03-23')*100:+6.1f}% "
                  f"2022 {PB.ep(r, '2022-01-01', '2022-12-31')*100:+6.1f}% Apr25 {PB.ep(r, '2025-04-02', '2025-04-08')*100:+5.1f}% "
                  f"worst day {r.min()*100:5.1f}% ({r.idxmin().date()}) HO worst day {ho.min()*100:5.1f}% ({ho.idxmin().date()}) "
                  f"worst month {PB.worst_month(r)*100:5.1f}%", flush=True)

    # ---------------- 1-minute worst intraday paths
    print("\n== worst intraday path of the intraday legs (1-minute bars, adverse extreme), % of equity")
    NP = {s_: noise_paths(s_) for s_ in G.S2}
    CP = conv_paths()
    tro = {}
    for bl, (g, cap, conv) in BOOKS.items():
        for vl, (mult, kel) in VARS.items():
            row = {}
            for d in DATES:
                row[d] = trough(pd.Timestamp(d), g, conv, mult, kel, NP, CP, S_NZ0)
            allw = {d: trough(d, g, conv, mult, kel, NP, CP, S_NZ0) for d in NP["QQQ"]}
            wd = min(allw, key=allw.get)
            row["worst"] = (wd, allw[wd])
            row["p99"] = float(np.percentile(list(allw.values()), 1))
            tro[(bl, vl)] = row
            print(f"  {bl:15s} {vl:18s} " + " ".join(f"{d[2:]} {row[d]*100:5.1f}" for d in DATES)
                  + f" | worst {wd.date()} {allw[wd]*100:5.1f}% | 1st pct {row['p99']*100:5.1f}%", flush=True)
    pickle.dump(dict(res=res, inc=inc, tro=tro), open(OUT, "wb"))

    # ---------------- dollars
    print("\n== dollars (EH tier_hi after tax): 1y at $3k, 5y MC median $3k+$1k/mo; 1y at $100k")
    for bl in BOOKS:
        b = res[(bl, "M2 base", "tier_hi")]
        for vl in VARS:
            v = res[(bl, vl, "tier_hi")]
            c = B.stats(v["eh_at"])[0]; c0 = B.stats(b["eh_at"])[0]
            print(f"  {bl:15s} {vl:18s} EH-AT {c*100:5.1f}% (d {100*(c-c0):+5.2f}pp) | $3k: +${3000*(c-c0):6.0f}/yr | "
                  f"MC5y med ${v['mc']['med']:,.0f} (d ${v['mc']['med']-b['mc']['med']:+,.0f}) | $100k: +${1e5*(c-c0):,.0f}/yr",
                  flush=True)


if __name__ == "__main__":
    main()
