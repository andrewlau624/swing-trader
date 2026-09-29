"""Program combine stage (candidate addendum NN, 2026-09-28): the shipped books vs the books
with every verified survivor (final verdict shadow/adopt) added.

    PYTHONPATH=. .venv/bin/python -m research.sim.program_books          # ~10-15 min, no heavy lock
    PYTHONPATH=. .venv/bin/python -m research.sim.program_books --raw    # same books on the RAW-price pool
    PYTHONPATH=. .venv/bin/python -m research.sim.program_books --joint-eh [--raw]
    (--raw: every night pool from addendum 30's cache_rawprice.pkl, i.e. night_days(raw_price=True),
     incl. the 2020 raw rebuild for COVID/holdouts; outputs get a _rawpool suffix)
    (reads the scratchpad caches built by roth_opt_extract, macro_events, taxable_frontier and
     the new_listings verifier's raw closes; nothing here loads panel()/night_candidates())

Survivors (verified, 9 studies, 543 variants in total):
  macro_events   F3  ADOPT   QQQ close->open with the night leg's unused cash on scheduled FOMC eves
  roth_opt           SHADOW  M2L Roth night sizing pro-rata on the real 15:40 cash (SGOV held);
                             A2 V6 oversold overnight on all idle Roth overnight money;
                             G4s Roth-first wash guard with different-index look-alikes only
  ops_capital        SHADOW  logging/ops only (G1 lever-gate log, Roth IBS entry 09:50): no book effect
Not survivors (borderline/dead): taxable_frontier (borderline: moderate is still the pre-planned
profile, used here as the TAXABLE BOOK's leverage because the frontier put the knee there),
index_mechanics P2 (borderline), opex, new_listings, regime_robust (dead).

Books
  TAXABLE shipped   V7 1.0x, name cap .10, conviction 0.5 (growth.V7 via Sim.replay); references:
                    live today (no conviction), gate 1.3x cap .10, moderate 1.3x cap .15
  TAXABLE proposed  moderate 1.3x cap .15 (the after-tax knee) + F3
  ROTH shipped      roth.py b1 as modelled (roth_opt 'asis'); live-accurate M3 (executor greedy skip,
                    SGOV held at 15:40) is the baseline increments are measured from
  ROTH proposed     M2L + A2 + F3
  JOINT             both books side by side under the live symmetric guard G1 vs the G4s guard

Sensitivity (repo-wide bug found by the new_listings verifier): the night pool uses split-adjusted
prices, so names that later reverse-split pass the live $5 floor in the sim when they did not live.
Every book is also re-run on the raw-price >= $5 pool.
Deflated Sharpe (Bailey & Lopez de Prado 2014) for each survivor's daily increment and each book.
"""
from __future__ import annotations

import copy
import pickle
import sys

import numpy as np
import pandas as pd
from scipy import stats as SS

from swingtrader.daily import signals as sg

from . import book as B
from . import growth as G
from . import macro_events as ME
from . import roth_opt as RO
from . import taxable_frontier as TF
from . import crash as CR

SCR = RO.SCR
N_TRIALS = 543
COSTS = (3.0, "tier_hi")
PER = (("2021-23", "2021-01-01", "2023-12-31"), ("2024-26", "2024-01-01", "2026-12-31"))
F3C = ME.ETF_COST            # QQQ per side: 3bp / tier_hi 7.5bp


# ------------------------------------------------------------------ helpers
def st(r):
    return B.stats(r)


def cell(r):
    c, s, d = st(r)
    return f"{c*100:5.1f}/{s:4.2f}/{d*100:4.0f}"


def halves(r):
    return " | ".join(cell(r[a:b]) for _, a, b in PER) + " | " + cell(r)


def ep(r, a, b):
    x = r[a:b]
    return ((1 + x).prod() - 1) if len(x) else np.nan


def worst_month(r):
    return float((1 + r.fillna(0)).groupby([r.index.year, r.index.month]).prod().min() - 1)


def dsr(r, n_trials=N_TRIALS, sr_var=None):
    """Deflated Sharpe ratio on daily returns.
    SR0 = sqrt(V) * ((1-g) * Z^-1(1 - 1/N) + g * Z^-1(1 - 1/(N e))),  g = Euler-Mascheroni
    DSR = Phi( (SR - SR0) * sqrt(T-1) / sqrt(1 - skew*SR + (kurt-1)/4 * SR^2) )
    SR, SR0 per day; V = cross-trial variance of SR estimates, default 1/T (the null sampling
    variance, i.e. all 543 trials pure noise with this sample length)."""
    x = r.dropna().values
    T = len(x)
    sr = x.mean() / x.std(ddof=1)
    sk = SS.skew(x); ku = SS.kurtosis(x, fisher=False)
    V = 1.0 / T if sr_var is None else sr_var
    g = 0.5772156649
    sr0 = np.sqrt(V) * ((1 - g) * SS.norm.ppf(1 - 1 / n_trials) + g * SS.norm.ppf(1 - 1 / (n_trials * np.e)))
    z = (sr - sr0) * np.sqrt(T - 1) / np.sqrt(max(1e-12, 1 - sk * sr + (ku - 1) / 4 * sr ** 2))
    return dict(T=T, sr_ann=sr * np.sqrt(252), sr0_ann=sr0 * np.sqrt(252), skew=sk, kurt=ku,
                t=sr * np.sqrt(T), psr0=SS.norm.cdf(sr * np.sqrt(T - 1) / np.sqrt(max(1e-12, 1 - sk * sr + (ku - 1) / 4 * sr ** 2))),
                dsr=SS.norm.cdf(z))


# ------------------------------------------------------------------ raw-price $5 pool (bug sensitivity)
def raw_bad():
    raw = pickle.load(open(f"{SCR}/nl_rawclose.pkl", "rb"))
    raw = raw[raw.close < 5.0]
    return set(zip(pd.to_datetime(raw.date), raw.symbol))


def exclude_raw(N, bad, cap):
    out = {}
    for d, nd in N.items():
        m = np.array([(d, sy) in bad for sy in nd.syms])
        if not m.any():
            out[d] = nd; continue
        k = ~m
        if not k.any():
            continue
        frac = min(1.0 / k.sum(), cap) * min(1.0, 30 / max(nd.n_raw, 1))
        out[d] = B.NightDay(nd.syms[k], nd.price[k], nd.close[k], nd.ret[k], nd.adv[k], nd.vol20[k],
                            nd.ret20[k], nd.day_ret[k], frac, nd.n_raw)
    return out


# ------------------------------------------------------------------ RAW-price pool (addendum 30)
RAW = "--raw" in sys.argv
SUF = "_rawpool" if RAW else ""


def night2020(d20, cap):
    """growth.covid_legs' night leg for one name cap, from a (rawprice.days_2020) rebuild."""
    o = {}
    for d in sorted(d20):
        ret, vol20, day_ret, n_raw, gap = d20[d]
        keep = np.nan_to_num(vol20) >= 0.6
        if not keep.any():
            o[d] = 0.0; continue
        r, v, dr = ret[keep], vol20[keep], day_ret[keep]
        per = min(1 / len(r), cap) * min(1.0, 30 / max(n_raw, 1))
        x = per * sg.night_tilt(v, dr) * (0.5 if gap > 1 else 1.0)
        val = float((x * (np.nan_to_num(r) - 2 * CR.COST / 1e4)).sum())
        o[d] = val - 9.1e-4 * (val != 0)
    return pd.Series(o)


def pool_inputs(Ns, c_ro, covid, legs):
    """--raw: swap every night pool for the raw-price one (2021-26 pools and the 2020 rebuild).
    The adjusted rebuild through night2020 reproduces the cached legs exactly (checked)."""
    if not RAW:
        return Ns, c_ro, covid, legs
    from . import rawprice as RP
    rp = pickle.load(open(RP.CACHE, "rb"))
    Ns = dict(rp["raw"])
    night = {cap: night2020(rp["y2020"]["raw"][0], cap) for cap in (0.10, 0.15, 0.20)}
    n10 = night[0.10][night[0.10].index < "2020-11-05"]
    c_ro = dict(c_ro); c_ro["N"] = Ns[0.10]
    c_ro["legs"] = (n10,) + tuple(c_ro["legs"][1:])
    covid = (night,) + tuple(covid[1:]) if covid is not None else None
    legs = (n10,) + tuple(legs[1:]) if legs is not None else None
    return Ns, c_ro, covid, legs


# ------------------------------------------------------------------ taxable books
def tax_replay(s, N, g, cap, conv, cost, fe=None, start=3000.0, monthly=1000.0):
    """taxable_frontier.replay, plus F3 on FOMC eves (Params.filler = QQQ, macro_events costs)."""
    s.N = N
    ix = s.C.index
    pos = {d: i for i, d in enumerate(ix)}
    nxt = lambda d, k: ix[min(pos[d] + k, len(ix) - 1)]
    p = TF._params(g, cap, conv, None, cost)
    p3 = copy.copy(p); p3.filler, p3.filler_cost_bps = "QQQ", F3C[cost]
    E, rows, T = start, [], []
    for i, d in enumerate(s.days):
        if i and i % 21 == 0:
            E += monthly
        q = p3 if (fe is not None and bool(fe.get(d, False))) else p
        pl, info = s.day_pnl(E, d, q)
        for t in TF.day_trades(s, E, d, p, nxt):
            T.append((d,) + t + (E,))
        k = E if E else 1.0
        rows.append((d, E, pl / k, info["night"] / k, info["ibs"] / k, info["noise"] / k,
                     (info["idle"] + info["margin"]) / k, info["night_v"] / (p.night_w * k)))
        E += pl
    df = pd.DataFrame(rows, columns=["date", "E", "r", "r_night", "r_ibs", "r_noise", "r_cash",
                                     "night_used"]).set_index("date")
    tr = pd.DataFrame(T, columns=["book", "sym", "buy", "sell", "qty", "pnl", "E"])
    tr["frac"] = tr.pnl / tr.E
    return df, tr


def tax_holdout(legs, g, conv, fe, spare, a="2016-02-01", b="2020-12-31", ix=None, on_=None):
    """2016-20 returns book (macro_events.holdout generalised to the profile's weights; the 2020
    night rebuild exists only at name cap .10; before 2020 the night half is in T-bills)."""
    night, ibs, bil, nz, bo = legs
    p = G.cfg(g, conv, 2)
    days = ix[(ix >= a) & (ix <= b)]
    out = {}
    for d in days:
        bl = float(np.nan_to_num(bil.get(d, 0.0)))
        nv = night.get(d, np.nan)
        x = p["night_w"] * float(nv) if np.isfinite(nv) else p["night_w"] * bl * (d < pd.Timestamp("2020-01-02"))
        if fe is not None and bool(fe.get(d, False)):
            sp = p["night_w"] * spare
            if not np.isfinite(nv):
                x -= sp * bl
            x += sp * (float(on_.at[d, "QQQ"]) - 2 * 3.0 / 1e4)
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


# ------------------------------------------------------------------ Roth with F3
class RothF3(RO.Roth):
    """roth_opt.Roth + F3: on a scheduled-FOMC eve the Roth's spare night-half cash that is really
    free at 15:40 (after the night leg and V6) buys QQQ at the close, sells at the next open."""
    FE: pd.Series | None = None
    ON: pd.DataFrame | None = None

    def step(self, d, n_excl=frozenset(), i_excl=frozenset()):
        E = self.E + (self.monthly if (self.i and self.i % 21 == 0) else 0.0)
        ibs_prev = self.ibs_prev_v
        trades, pl = super().step(d, n_excl, i_excl)
        x = 0.0
        if self.FE is not None and bool(self.FE.get(d, False)) and E > 0:
            v, s = self.v, self.s
            row = self.rows[-1]
            gross, night_idle = row[8] * E, row[9] * E
            nused = 0.5 * E - night_idle
            v6_used = max(0.0, gross - nused - self.ibs_prev_v)
            free = E - ibs_prev
            cash3x = min(0.5 * E, free) if v.budget == "night" else free
            cap = min(v.L, 3.0 * cash3x / E)
            held3x = 0.0
            for sym, share in RO.S2.items():
                z = self.nz[sym]
                if d in z.index and cap > 0 and z.at[d, "pos40"] != 0:
                    held3x += E * min(float(z.at[d, "lev"]), cap) * share / 3.0
            if v.mech in ("M2L", "M3"):
                cash40 = E - (ibs_prev if ibs_prev > 0 else 0.5 * E) - held3x
            elif v.mech == "M2":
                cash40 = E - ibs_prev - held3x
            else:
                cash40 = E - ibs_prev
            spare = max(0.0, min(0.5 * E - nused, cash40 - nused - v6_used))
            r = self.ON.at[d, "QQQ"] if d in self.ON.index else np.nan
            if spare > 0 and np.isfinite(r):
                px = float(s.C.at[d, "QQQ"])
                val = np.floor(spare / px) * px
                net = float(r) - 2 * F3C[self.cost] / 1e4
                x = val * net
                if val > 0:
                    trades["night"] = list(trades["night"]) + [("QQQ", val, net)]
        self.rows[-1] = self.rows[-1][:1] + ((self.rows[-1][1] * E + x) / E,) + self.rows[-1][2:] + (x / E,)
        self.E += x
        return trades, pl + x

    def frame(self):
        rows = [r if len(r) == 12 else r + (0.0,) for r in self.rows]
        return pd.DataFrame(rows, columns=["date", "r", "r_night", "r_ibs", "r_noise", "r_v6", "r_conv",
                                           "r_idle", "gross", "night_idle", "ibs_idle", "r_f3"]).set_index("date")


def roth_run(ctx, v, cost, f3):
    s, c, nz, held = ctx
    RothF3.FE = F3FLAG if f3 else None
    R = RothF3(s, nz, held, v, cost)
    for d in s.days:
        R.step(d)
    return R.frame()


def roth_eh(df):
    cut = 0.5 * sum(df[k].mean() for k in ("r_night", "r_ibs", "r_noise", "r_v6", "r_conv", "r_f3"))
    return df["r"] - cut


# ------------------------------------------------------------------ joint (guard) run
def night_leg_cap(s, nd, leg, cost, excl=frozenset(), weekend=0.5, d=None, cap=0.10):
    """roth_opt.night_leg with the name cap as a parameter (it hardcodes 0.10 after exclusions)."""
    if nd is None or leg <= 0:
        return 0.0, 0.0, []
    keep = np.array([x not in excl for x in nd.syms])
    if not keep.any():
        return 0.0, 0.0, []
    n_raw = max(nd.n_raw - int((~keep).sum()), 1)
    frac = min(1.0 / keep.sum(), cap) * min(1.0, 30 / n_raw) if (~keep).any() else nd.frac
    w = sg.night_tilt(nd.vol20[keep], nd.day_ret[keep], 0.25)
    c = B.cost_bps(cost, nd.price[keep], nd.adv[keep])
    per = leg * frac * w * (weekend if s._gap(d) > 1 else 1.0)
    sh = np.floor(per / nd.price[keep])
    v = sh * nd.close[keep]
    net = nd.ret[keep] - 2 * c / 1e4
    tr = [(sy, vv, rr) for sy, vv, rr in zip(nd.syms[keep], v, net) if vv > 0]
    return float((v * net).sum()), float(v.sum()), tr


def make_tax(g, cap, conv, N, f3):
    kw = G.cfg(g, conv, 2)

    class TaxP(RO.Taxable):
        def step(self, d, n_excl=frozenset(), i_excl=frozenset()):
            s = self.s
            if self.i and self.i % 21 == 0:
                self.E += self.monthly
            self.i += 1
            E = self.E
            out = dict(night=0.0, ibs=0.0, noise=0.0, idle=0.0, margin=0.0)
            trades = {"noise": []}
            for sym, share in RO.S2.items():
                z = s.NZ[sym]
                if d in z.index:
                    lev = min(float(z.at[d, "lev"]), kw["noise_cap"]) * share
                    x = E * lev * float(z.at[d, "ret"])
                    out["noise"] += x
                    if z.at[d, "trades"] > 0:
                        trades["noise"].append((sym, E * lev, x))
            if kw["conviction_w"] and d in s.BO.index:
                out["noise"] += E * kw["conviction_w"] * float(s.BO.at[d])
            leg = kw["night_w"] * E
            pn, nused, trn = night_leg_cap(s, N.get(d), leg, self.cost, n_excl, d=d, cap=cap)
            trn = list(trn)
            if f3 and bool(F3FLAG.get(d, False)) and "QQQ" not in n_excl:
                r = ON.at[d, "QQQ"] if d in ON.index else np.nan
                spare = max(0.0, leg - nused)
                if np.isfinite(r) and spare > 0:
                    px = float(s.C.at[d, "QQQ"]); val = np.floor(spare / px) * px
                    net = float(r) - 2 * F3C[self.cost] / 1e4
                    pn += val * net; nused += val
                    if val > 0:
                        trn.append(("QQQ", val, net))
            pi, iused, tri = RO.ibs_leg(s.I.get(d, []), kw["ibs_w"] * E, i_excl)
            out["night"], out["ibs"] = pn, pi
            out["idle"] = (kw["ibs_w"] * E - iused) * RO.bil(s, d)
            debit = nused + iused - E
            if debit > 0:
                out["margin"] = -debit * 0.12 / 252
            trades["night"], trades["ibs"] = trn, tri
            pl = sum(out.values())
            self.rows.append((d, pl / E, out["night"] / E, out["ibs"] / E, out["noise"] / E, pl))
            self.E += pl
            return trades, pl
    return TaxP


def joint(ctx, guard, cost, taxcls, vroth, f3roth, scale=1.0, rate=0.35):
    o_T, o_R, o_tax = RO.Taxable, RO.Roth, RO.TAX
    RothF3.FE = F3FLAG if f3roth else None
    try:
        RO.Taxable, RO.Roth, RO.TAX = taxcls, RothF3, rate
        Tdf, Rdf, dis, dis_si, gl = RO.run_pair(ctx, guard, cost, vroth, scale=scale)
        Tend = RO.taxable_end(Tdf, dis, RO.TAX0 * scale, RO.TAX_MO * scale)
    finally:
        RO.Taxable, RO.Roth, RO.TAX = o_T, o_R, o_tax
    Rend = RO.dollars_end(Rdf.r, RO.ROTH0 * scale, RO.ROTH_MO * scale)
    te = Tdf.r - 0.5 * (Tdf.r_night.mean() + Tdf.r_ibs.mean() + Tdf.r_noise.mean())
    return dict(T=Tdf, R=Rdf, Tend=Tend, Rend=Rend, dis=sum(dis.values()) / max(sum(gl.values()), 1e-9),
                dis_si=sum(dis_si.values()) / max(sum(gl.values()), 1e-9),
                Teh=st(te)[0], Reh=st(roth_eh(Rdf))[0])


# ------------------------------------------------------------------ main
F3FLAG: pd.Series = None
ON: pd.DataFrame = None


def main():
    global F3FLAG, ON
    raw_only = "--raw-only" in sys.argv
    ctx = RO.load_ctx()
    s0, c_ro, nz, held = ctx
    _, Ns, covid = TF.load()
    me = pickle.load(open(ME.CACHE, "rb"))
    legs = me["legs"]
    Ns, c_ro, covid, legs = pool_inputs(Ns, c_ro, covid, legs)
    print(f"night pool: {'RAW prices (addendum 30)' if RAW else 'adjusted (as published)'}", flush=True)
    ctxR = (copy.copy(s0), c_ro, nz, held)
    ctxR[0].N = c_ro["N"]
    s = copy.copy(s0); s.BO = c_ro["BO"]
    ix = s.C.index
    F3FLAG = ME.flags(ix)["fomc_eve"]
    ON = s.O.shift(-1) / s.C - 1
    RothF3.ON = ON
    res = {}

    TAXP = {  # label: (gross, cap, conv, F3)
        "T0 V7 shipped 1.0x cap.10 conv.5": (1.0, 0.10, 0.5, False),
        "T0L live today 1.0x cap.10 no conv": (1.0, 0.10, 0.0, False),
        "T0+F3": (1.0, 0.10, 0.5, True),
        "T1 gate 1.3x cap.10": (1.3, 0.10, 0.5, False),
        "T2 moderate 1.3x cap.15": (1.3, 0.15, 0.5, False),
        "T2b moderate as built 1.0x cap.15": (1.0, 0.15, 0.5, False),
        "TP PROPOSED moderate 1.3x cap.15 + F3": (1.3, 0.15, 0.5, True),
    }
    ROTHP = {  # label: (RV, F3)
        "R0 shipped b1 as modelled (asis)": (RO.RV(mech="asis"), False),
        "R0L live-accurate M3": (RO.RV(mech="M3"), False),
        "R0L+F3": (RO.RV(mech="M3"), True),
        "R1 M2L": (RO.RV(mech="M2L"), False),
        "R1+A2": (RO.RV(mech="M2L", v6="all"), False),
        "RP PROPOSED M2L + A2 + F3": (RO.RV(mech="M2L", v6="all"), True),
    }
    TKEY = ["T0 V7 shipped 1.0x cap.10 conv.5", "T0L live today 1.0x cap.10 no conv", "T1 gate 1.3x cap.10",
            "T2 moderate 1.3x cap.15", "T2b moderate as built 1.0x cap.15", "TP PROPOSED moderate 1.3x cap.15 + F3"]
    RKEY = ["R0 shipped b1 as modelled (asis)", "R0L live-accurate M3", "RP PROPOSED M2L + A2 + F3"]

    # spare night share for the 2016-20 F3 holdout: 2021-26 mean unused share of the V7 night half
    if not raw_only:
        base = tax_replay(s, Ns[0.10], 1.0, 0.10, 0.5, 3.0)[0]
        spare = float(1 - base.night_used.clip(0, 1).mean())
        print(f"spare night share (V7, 3bp, 2021-26): {spare:.2f}")

        # ================= taxable
        for lab, (g, cap, conv, f3) in TAXP.items():
            for cost in COSTS:
                df, tr = tax_replay(s, Ns[cap], g, cap, conv, cost, F3FLAG if f3 else None)
                at, info = TF.after_tax(df.r, 0.35, trades=tr)
                e = G.eh(df)
                eat, _ = TF.after_tax(e, 0.35, trades=tr)
                res[("T", lab, cost)] = dict(df=df, r=df.r, at=at, acct=info["r_account"], eh=e, eh_at=eat)
                print(f"  {lab:40s}{str(cost):>8s} pre {halves(df.r)} | AT {halves(at)} | EH {cell(e)} EH-AT {cell(eat)}", flush=True)
            ho = tax_holdout(legs, g, conv, F3FLAG if f3 else None, spare, ix=ix, on_=ON)
            cv = TF.covid_series(covid, lambda d, h, g=g: g, cap, conv)
            res[("T", lab, "ho")] = ho; res[("T", lab, "covid")] = cv
            print(f"  {lab:40s} 2016-20 HO {cell(ho)}   COVID {ep(cv, '2020-02-19', '2020-03-23')*100:+.1f}%", flush=True)
        # ================= Roth
        for lab, (v, f3) in ROTHP.items():
            for cost in COSTS:
                df = roth_run(ctxR, v, cost, f3)
                res[("R", lab, cost)] = dict(df=df, r=df.r, eh=roth_eh(df))
                print(f"  {lab:40s}{str(cost):>8s} {halves(df.r)} | EH {cell(roth_eh(df))}", flush=True)
            hv = RO.RV(mech="M2", v6=v.v6) if v.mech != "asis" else RO.RV(mech="asis")
            ho = RO.holdout(ctxR, hv)
            if f3:
                add = pd.Series(0.0, index=ho.index)
                for d in ho.index:
                    if bool(F3FLAG.get(d, False)):
                        bl = float(np.nan_to_num(legs[2].get(d, 0.0)))
                        nv = legs[0].get(d, np.nan)
                        add[d] = 0.5 * spare * (float(ON.at[d, "QQQ"]) - 2 * 3.0 / 1e4 - (bl if not np.isfinite(nv) else 0.0))
                ho = ho + add
            res[("R", lab, "ho")] = ho
            print(f"  {lab:40s} 2016-20 HO {cell(ho)}   COVID {ep(ho, '2020-02-19', '2020-03-23')*100:+.1f}%", flush=True)
        pickle.dump(res, open(f"{SCR}/program_books_res{SUF}.pkl", "wb"))

        # ================= report tables
        print("\n== A. books: CAGR/Sharpe/maxDD  2016-20 HO | 2021-23 | 2024-26 | 2021-26 full")
        for acct, keys in (("T", TKEY), ("R", RKEY)):
            for lab in keys:
                for cost in COSTS:
                    x = res[(acct, lab, cost)]
                    print(f"  {lab:40s}{str(cost):>8s}  HO {cell(res[(acct, lab, 'ho')])} | {halves(x['r'])}"
                          + (f" | after-tax {halves(x['at'])}" if acct == "T" else ""))
        print("\n== B. edge-halves, crashes, worst day/month (tier_hi; COVID from the 2016-20 rebuild)")
        for acct, keys in (("T", TKEY), ("R", RKEY)):
            for lab in keys:
                for cost in COSTS:
                    x = res[(acct, lab, cost)]; r = x["r"]
                    cv = res[(acct, lab, "covid")] if acct == "T" else res[(acct, lab, "ho")]
                    print(f"  {lab:40s}{str(cost):>8s} EH {cell(x['eh'])}" + (f" EH-AT {cell(x['eh_at'])}" if acct == "T" else "")
                          + f" | COVID {ep(cv, '2020-02-19', '2020-03-23')*100:+6.1f}% 2022 {ep(r, '2022-01-01', '2022-12-31')*100:+6.1f}%"
                          f" Apr25 {ep(r, '2025-04-02', '2025-04-08')*100:+5.1f}% worst day {r.min()*100:5.1f}% worst month {worst_month(r)*100:5.1f}%")
        print("\n== C. 5y MC (21-day blocks) under EH, $3k + $1k/mo: median / P(DD>30%) / P(DD>50%)"
              " (taxable: after tax, DD net of liability | raw balance)")
        for acct, keys in (("T", TKEY), ("R", RKEY)):
            for lab in keys:
                for cost in COSTS:
                    x = res[(acct, lab, cost)]
                    if acct == "T":
                        m = TF.mc_tax(x["eh"], 0.35, start=3000, monthly=1000)
                        print(f"  {lab:40s}{str(cost):>8s} med ${m['med']:>9,.0f}  P30 {m['dd30']:4.0%} ({m['dd30_acct']:4.0%})  P50 {m['dd50']:4.0%} ({m['dd50_acct']:4.0%})")
                    else:
                        m = G.mc(x["eh"], 3000, 1000)
                        print(f"  {lab:40s}{str(cost):>8s} med ${m['med']:>9,.0f}  P30 {m['dd30']:4.0%}  P50 {m['dd50']:4.0%}")
        print("\n== D. $ projections, EH (tier_hi and 3bp): p10 / median / p90; taxable after 35% tax")
        for acct, keys, start in (("T", TKEY, 3000.0), ("R", RKEY, 7800.0)):
            for lab in (keys[0], keys[1], keys[-1]):
                for cost in COSTS:
                    x = res[(acct, lab, cost)]
                    parts = []
                    for mo in (0.0, 1000.0):
                        for days in (252, 1260):
                            m = (TF.mc_tax(x["eh"], 0.35, start=start, monthly=mo, days=days) if acct == "T"
                                 else G.mc(x["eh"], start, mo, days=days))
                            parts.append(f"{'+1k' if mo else 'lump'} {days//252}y ${m['p10']:,.0f}/${m['med']:,.0f}/${m['p90']:,.0f}")
                    print(f"  {lab:40s}{str(cost):>8s}  " + "  ".join(parts), flush=True)

        # ================= deflated Sharpe
        print(f"\n== E. deflated Sharpe (N = {N_TRIALS} trials; V[SR] = 1/T; sensitivity N = 50), daily 2021-26 at 3bp")
        inc = {
            "F3 taxable (T0+F3 - T0)": res[("T", "T0+F3", 3.0)]["r"] - res[("T", TKEY[0], 3.0)]["r"],
            "F3 Roth (M3+F3 - M3)": res[("R", "R0L+F3", 3.0)]["r"] - res[("R", "R0L live-accurate M3", 3.0)]["r"],
            "M2L sizing (M2L - M3)": res[("R", "R1 M2L", 3.0)]["r"] - res[("R", "R0L live-accurate M3", 3.0)]["r"],
            "A2 V6 idle Roth (M2L+A2 - M2L)": res[("R", "R1+A2", 3.0)]["r"] - res[("R", "R1 M2L", 3.0)]["r"],
            "moderate profile (T2 - T0), borderline": res[("T", TKEY[3], 3.0)]["r"] - res[("T", TKEY[0], 3.0)]["r"],
            "TAXABLE proposed - shipped": res[("T", TKEY[-1], 3.0)]["r"] - res[("T", TKEY[0], 3.0)]["r"],
            "ROTH proposed - live M3": res[("R", RKEY[-1], 3.0)]["r"] - res[("R", RKEY[1], 3.0)]["r"],
            "TAXABLE proposed book": res[("T", TKEY[-1], 3.0)]["r"],
            "ROTH proposed book": res[("R", RKEY[-1], 3.0)]["r"],
            "TAXABLE shipped book": res[("T", TKEY[0], 3.0)]["r"],
            "ROTH live M3 book": res[("R", RKEY[1], 3.0)]["r"],
        }
        for k, r in inc.items():
            a, b = dsr(r), dsr(r, 50)
            print(f"  {k:40s} SR_ann {a['sr_ann']:5.2f} t {a['t']:5.2f} skew {a['skew']:6.2f} kurt {a['kurt']:7.1f} "
                  f"SR0_ann {a['sr0_ann']:4.2f}  PSR(0) {a['psr0']:.3f}  DSR(543) {a['dsr']:.3f}  DSR(50) {b['dsr']:.3f}")
        # tier_hi versions of the increments
        for k, (acct, l1, l0) in {"F3 taxable tier_hi": ("T", "T0+F3", TKEY[0]),
                                  "A2 Roth tier_hi": ("R", "R1+A2", "R1 M2L"),
                                  "F3 Roth tier_hi": ("R", "R0L+F3", "R0L live-accurate M3")}.items():
            a = dsr(res[(acct, l1, "tier_hi")]["r"] - res[(acct, l0, "tier_hi")]["r"])
            print(f"  {k:40s} SR_ann {a['sr_ann']:5.2f} t {a['t']:5.2f}  DSR(543) {a['dsr']:.3f}")
        pickle.dump(res, open(f"{SCR}/program_books_res{SUF}.pkl", "wb"))

    # ================= joint books under the guards
    print("\n== F. JOINT: taxable $3k+$1k/mo and Roth $7.8k+$625/21d side by side (run_pair; tax 35%, "
          "permanent disallowance applied)")
    N15 = Ns[0.15]
    cfgs = {
        "J0 shipped books, live guard G1 (V7 live no conv | Roth M3)": ("G1", make_tax(1.0, 0.10, 0.0, Ns[0.10], False), RO.RV(mech="M3"), False),
        "J1 proposed books, live guard G1": ("G1", make_tax(1.3, 0.15, 0.5, N15, True), RO.RV(mech="M2L", v6="all"), True),
        "J2 proposed books, G4s Roth-first guard": ("G4s", make_tax(1.3, 0.15, 0.5, N15, True), RO.RV(mech="M2L", v6="all"), True),
        "J3 shipped books, G4s guard": ("G4s", make_tax(1.0, 0.10, 0.0, Ns[0.10], False), RO.RV(mech="M3"), False),
    }
    J = {}
    if not raw_only:
        for lab, (gd, tc, vr, f3r) in cfgs.items():
            for cost in COSTS:
                for sc, sl in ((1.0, "user"), (100000 / RO.ROTH0, "100k")):
                    out = joint(ctxR, gd, cost, tc, vr, f3r, scale=sc)
                    J[(lab, cost, sl)] = out
                    ft = lambda r: "/".join(f"{st(x)[0]*100:4.1f}" for x in (r[:"2023-12-31"], r["2024-01-01":], r))
                    print(f"  {lab:58s}{str(cost):>8s} {sl:>5s} taxable {ft(out['T'].r)} Roth {ft(out['R'].r)} "
                          f"| EH T {out['Teh']*100:4.1f} R {out['Reh']*100:4.1f} | disallowed {out['dis']:.1%} (+{out['dis_si']:.1%}) "
                          f"| end AT T ${out['Tend']:,.0f} + R ${out['Rend']:,.0f} = ${out['Tend'] + out['Rend']:,.0f}", flush=True)
        pickle.dump({k: {kk: vv for kk, vv in v.items() if kk not in ("T", "R")} | {"Tr": v["T"].r, "Rr": v["R"].r}
                     for k, v in J.items()}, open(f"{SCR}/program_books_joint{SUF}.pkl", "wb"))

    if RAW:     # section G's $5 exclusion is superseded by the full raw pool
        return
    # ================= raw-price $5 pool sensitivity
    print("\n== G. SENSITIVITY: raw-price >= $5 night pool (split-adjustment lookahead removed)")
    bad = raw_bad()
    s.N = None
    NR = {cap: exclude_raw(Ns[cap], bad, cap) for cap in (0.10, 0.15)}
    for lab in TKEY:
        g, cap, conv, f3 = TAXP[lab]
        for cost in COSTS:
            df, tr = tax_replay(s, NR[cap], g, cap, conv, cost, F3FLAG if f3 else None)
            at, _ = TF.after_tax(df.r, 0.35, trades=tr); e = G.eh(df); eat, _ = TF.after_tax(e, 0.35, trades=tr)
            m = TF.mc_tax(e, 0.35)
            res[("Traw", lab, cost)] = dict(r=df.r, at=at, eh=e, eh_at=eat)
            print(f"  {lab:40s}{str(cost):>8s} pre {halves(df.r)} | AT {cell(at)} | EH {cell(e)} EH-AT {cell(eat)} "
                  f"| MC P30 {m['dd30']:.0%} P50 {m['dd50']:.0%} ({m['dd50_acct']:.0%} raw)", flush=True)
    ctxRR = (copy.copy(ctxR[0]), c_ro, nz, held)
    ctxRR[0].N = exclude_raw(c_ro["N"], bad, 0.10)
    for lab in ["R0L live-accurate M3", "R1 M2L", "R1+A2", "RP PROPOSED M2L + A2 + F3", "R0 shipped b1 as modelled (asis)"]:
        v, f3 = ROTHP[lab]
        for cost in COSTS:
            df = roth_run(ctxRR, v, cost, f3)
            m = G.mc(roth_eh(df), 3000, 1000)
            res[("Rraw", lab, cost)] = dict(r=df.r, eh=roth_eh(df))
            print(f"  {lab:40s}{str(cost):>8s} {halves(df.r)} | EH {cell(roth_eh(df))} | MC P30 {m['dd30']:.0%} P50 {m['dd50']:.0%}", flush=True)
    if not raw_only:
        for lab in ("J0 shipped books, live guard G1 (V7 live no conv | Roth M3)", "J2 proposed books, G4s Roth-first guard",
                    "J1 proposed books, live guard G1"):
            gd, tc, vr, f3r = cfgs[lab]
            tc = make_tax(*{"J0": (1.0, 0.10, 0.0, NR[0.10], False)}.get(lab[:2], (1.3, 0.15, 0.5, NR[0.15], True)))
            for cost in COSTS:
                out = joint(ctxRR, gd, cost, tc, vr, f3r)
                print(f"  RAW {lab:54s}{str(cost):>8s} taxable {st(out['T'].r)[0]*100:4.1f} Roth {st(out['R'].r)[0]*100:4.1f} "
                      f"| EH T {out['Teh']*100:4.1f} R {out['Reh']*100:4.1f} | end AT ${out['Tend'] + out['Rend']:,.0f}", flush=True)
    pickle.dump(res, open(f"{SCR}/program_books_res{'_raw' if raw_only else ''}.pkl", "wb"))


def joint_eh():
    """POST-HOC follow-up to section F: combined end $ with each book's edge halved (EH), and J2b =
    J2 without the Roth's F3 (Roth F3 buys QQQ, which taxable's noise leg sells at a loss almost
    daily, so under G4s it creates permanent cross-account wash sales)."""
    global F3FLAG, ON
    ctx = RO.load_ctx()
    s0, c_ro, nz, held = ctx
    _, Ns, _ = TF.load()
    Ns, c_ro, _, _ = pool_inputs(Ns, c_ro, None, None)
    ctxR = (copy.copy(s0), c_ro, nz, held); ctxR[0].N = c_ro["N"]
    F3FLAG = ME.flags(s0.C.index)["fomc_eve"]; ON = s0.O.shift(-1) / s0.C - 1; RothF3.ON = ON
    bad = raw_bad()
    ctxRR = (copy.copy(ctxR[0]), c_ro, nz, held); ctxRR[0].N = exclude_raw(c_ro["N"], bad, 0.10)
    NR = {cap: exclude_raw(Ns[cap], bad, cap) for cap in (0.10, 0.15)}
    pools = (("RAW", ctxR, Ns),) if RAW else (("adj", ctxR, Ns), ("raw$5", ctxRR, NR))
    for pool, cx, NN in pools:
        cfgs = {
            "J0 shipped, G1": ("G1", make_tax(1.0, 0.10, 0.0, NN[0.10], False), RO.RV(mech="M3"), False),
            "J1 proposed, G1": ("G1", make_tax(1.3, 0.15, 0.5, NN[0.15], True), RO.RV(mech="M2L", v6="all"), True),
            "J1b proposed, G1, no Roth F3": ("G1", make_tax(1.3, 0.15, 0.5, NN[0.15], True), RO.RV(mech="M2L", v6="all"), False),
            "J2b proposed, G4s, no Roth F3": ("G4s", make_tax(1.3, 0.15, 0.5, NN[0.15], True), RO.RV(mech="M2L", v6="all"), False),
            "J4 shipped taxable + proposed Roth, G4s, no Roth F3": ("G4s", make_tax(1.0, 0.10, 0.0, NN[0.10], False), RO.RV(mech="M2L", v6="all"), False),
        }
        for lab, (gd, tc, vr, f3r) in cfgs.items():
            for cost in COSTS:
                for sc, sl in ((1.0, "user"), (100000 / RO.ROTH0, "100k")):
                    if pool == "raw$5" and sl == "100k":
                        continue
                    o_T, o_R, o_tax = RO.Taxable, RO.Roth, RO.TAX
                    RothF3.FE = F3FLAG if f3r else None
                    try:
                        RO.Taxable, RO.Roth, RO.TAX = tc, RothF3, 0.35
                        Tdf, Rdf, dis, dis_si, gl = RO.run_pair(cx, gd, cost, vr, scale=sc)
                        te = Tdf.r - 0.5 * (Tdf.r_night.mean() + Tdf.r_ibs.mean() + Tdf.r_noise.mean())
                        Tend = RO.taxable_end(Tdf, dis, RO.TAX0 * sc, RO.TAX_MO * sc)
                        TendE = RO.taxable_end(pd.DataFrame({"r": te}), dis, RO.TAX0 * sc, RO.TAX_MO * sc)
                    finally:
                        RO.Taxable, RO.Roth, RO.TAX = o_T, o_R, o_tax
                    re_ = roth_eh(Rdf)
                    Rend = RO.dollars_end(Rdf.r, RO.ROTH0 * sc, RO.ROTH_MO * sc)
                    RendE = RO.dollars_end(re_, RO.ROTH0 * sc, RO.ROTH_MO * sc)
                    pct = sum(dis.values()) / max(sum(gl.values()), 1e-9)
                    print(f"  {pool:6s}{lab:52s}{str(cost):>8s}{sl:>5s} CAGR T {st(Tdf.r)[0]*100:5.1f} R {st(Rdf.r)[0]*100:5.1f}"
                          f" | EH T {st(te)[0]*100:5.1f} R {st(re_)[0]*100:5.1f} | disallowed {pct:5.1%}"
                          f" | end AT ${Tend + Rend:>12,.0f} | EH end AT T ${TendE:>11,.0f} + R ${RendE:>11,.0f} = ${TendE + RendE:>12,.0f}",
                          flush=True)


if __name__ == "__main__":
    if "--joint-eh" in sys.argv:
        joint_eh()
    else:
        main()
