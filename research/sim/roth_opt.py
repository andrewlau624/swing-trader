"""Roth IRA optimization inside the IRA's rules (candidate addendum NN, 2026-09-28).

    # once, under the heavy lock (night leg with the live guards, 2016-20 holdout legs):
    PYTHONPATH=. .venv/bin/python -m research.sim.roth_opt_extract
    PYTHONPATH=. .venv/bin/python -m research.sim.roth_opt          # ~5 min, no panel

Baseline = shipped Roth book (addendum 20 b1): IBS 0.5 + night 0.5 (1.0x overnight, live tilt,
weekend x0.5, corr 0.7, name cap 0.10), QQQ/SMH noise leg held as TQQQ/SQQQ/SOXL/SOXS on the
night half's daytime cash, cap 1.5x underlying, +0.3bp/side leveraged-ETF extra, no conviction.
Roth account: $7,800 + $7,500/yr ($625 every 21 sessions), whole shares.

Found before running (executor.py): the Roth places its 15:40 close-auction night buys while
the 3x ETFs are held until the 15:57 flatten, and an IRA cannot go into debit. PRECISE mechanics:
  M1  flatten the 3x ETFs at 15:40 (minute 369), the proceeds fund the MOC buys
  M2  hold to 15:57; the night leg only gets the cash not in 3x ETFs at 15:40
  asis  addendum 20's model (hold to 15:57 AND full night leg) -- infeasible, reference only

Pre-registered variants (addendum draft, stamped Mon Sep 28 20:53:38 PDT 2026):
 (a) A1 V6 oversold overnight (SPY/QQQ, 15:40 either-trigger, close -> open) in the IBS idle half
     A2 V6 funded by all idle overnight money (IBS idle half + unused night leg)
 (b) B1 L 0.75  B2 L 1.0  B3 L 1.5 (shipped)  B4 L <= 3.0 on ALL daytime cash (IBS idle half too)
     B5 B3 + TQQQ/SQQQ conviction 0.5 from the IBS idle daytime cash
 (c) C1 IBS takes 1.0 of equity after a night with no night picks; C2 same at 0.75
 (d) guards, taxable V7 ($3k + $1k/mo) beside the Roth:
     G0 none   G1 live symmetric 31-day lockout, taxable first   G2 Roth IBS on look-alike ETFs
     G3 G2 + loss-aware night guard (Roth skips only names taxable holds / sold at a loss <= 30d)
     G4 POST-HOC (added after G1-G3 showed the Roth's night leg is starved): Roth runs FIRST and
        owns the night names; taxable skips every name the Roth traded in 31 days; Roth skips
        names taxable sold at a loss in 30 days; Roth IBS on look-alikes. At most SHADOW.
    --only-d  runs section (d) alone (~1 min).
 VERIFIER additions (post-hoc sensitivity, not candidates): holdout() now models A2's pool (it
 was identical to A1) at 3bp V6 cost; mech M2L (SGOV held at 15:40, as live) and M3 (the LIVE
 executor rule: full sizing, greedy skip in day_ret order once book cash < 0); guard G4s (G4 with
 look-alikes only for different-index pairs).
Pass bar: see the addendum. Costs: 3bp flat (measured), tier, tier_hi.
"""
from __future__ import annotations

import os
import pickle
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import book as B
from . import data as D
from . import growth as G
from .oversold import honest_1540, placebo_ovn, schedule_ovn
from .regime_tilt import tstat
from .validate import load_sim

SCR = str(__import__("pathlib").Path(__file__).resolve().parents[2]) + "/data/research/program"
CACHE = f"{SCR}/cache_roth_opt.pkl"
NZC = f"{SCR}/cache_roth_opt_nz.pkl"
S2 = {"QQQ": 0.5, "SMH": 0.5}
LEV_X = 0.3                     # bp/side extra for 3x ETFs, underlying terms (roth.py)
COSTS = (3.0, "tier", "tier_hi")
V6C = {3.0: 3.0, "tier": 1.0, "tier_hi": 3.0}      # bp/side on the SPY/QQQ overnight trade
TAX = 0.32
ROTH0, ROTH_MO = 7800.0, 625.0
TAX0, TAX_MO = 3000.0, 1000.0
LOOKALIKE = {"SPY": "SPLG", "QQQ": "QQQM", "IWM": "VTWO", "MDY": "IJH", "XLK": "VGT", "XLF": "VFH",
             "XLE": "VDE", "XLV": "VHT", "XLI": "VIS", "XLY": "VCR", "XLP": "VDC", "XLU": "VPU",
             "XLB": "VAW", "SMH": "SOXX", "EEM": "IEMG", "EFA": "IEFA"}   # DIA, XBI: none
SAME_INDEX = {"SPY", "QQQ", "IWM", "MDY", "EEM"}   # look-alike tracks the SAME index (riskier)


# ------------------------------------------------------------ noise leg, two exits
def noise_ext(sym: str, lookback=14, cost=0.5, target_vol=0.02) -> pd.DataFrame:
    """book.noise_days, plus the same rule flattened at 15:40 (bar 369) and the
    position held at 15:40 (after the 15:30 decision)."""
    M = D.minutes(sym)
    C, V = M["close"].values, M["volume"].values
    O = M["open"].values[:, 0]
    days = M["close"].index
    move = np.abs(C / O[:, None] - 1)
    dclose = pd.Series(C[:, -1], index=days)
    prevc = np.r_[np.nan, C[:-1, -1]]
    vwap = np.cumsum(C * V, axis=1) / np.maximum(np.cumsum(V, axis=1), 1)
    rows = []
    for i in range(lookback + 1, len(days)):
        sigma = sg.noise_sigma(move[i - lookback:i])
        ub, lb = sg.noise_bounds(O[i], prevc[i], sigma)
        lev = sg.noise_leverage(dclose.iloc[:i], target_vol, 1e9)
        pos, entry, pnl, tr = 0, None, 0.0, 0
        for m in range(sg.NOISE_FIRST, 390, sg.NOISE_STEP):
            p = C[i, m]
            new = sg.noise_decide(pos, p, ub[m], lb[m], vwap[i, m])
            if new != pos:
                if pos != 0:
                    pnl += pos * (p / entry - 1); tr += 1
                if new != 0:
                    entry = p; tr += 1
                pos = new
        p57, p40, t57, t40 = pnl, pnl, tr, tr
        if pos != 0:
            p57 += pos * (C[i, 389] / entry - 1); t57 += 1
            p40 += pos * (C[i, 369] / entry - 1); t40 += 1
        rows.append((days[i], p57 - t57 * cost / 1e4, p40 - t40 * cost / 1e4, lev, t57, t40, pos))
    return pd.DataFrame(rows, columns=["date", "r57", "r40", "lev", "t57", "t40", "pos40"]).set_index("date")


def load_ctx():
    s = load_sim()
    c = pickle.load(open(CACHE, "rb"))
    if os.path.exists(NZC):
        nz = pickle.load(open(NZC, "rb"))
    else:
        nz = {k: noise_ext(k) for k in S2}
        pickle.dump(nz, open(NZC, "wb"))
    s.N, s.BO = c["N"], c["BO"]
    held = schedule_ovn(s, honest_1540(s))
    return s, c, nz, held


# ------------------------------------------------------------ leg helpers
def night_leg(s, nd, leg, cost, excl=frozenset(), weekend=0.5, d=None, cash_cap=None):
    """V7 night leg on `leg` dollars, names in `excl` removed BEFORE sizing (as
    the live guard does). Returns pnl, used $, [(sym, value, net ret)]."""
    if nd is None or leg <= 0:
        return 0.0, 0.0, []
    keep = np.array([x not in excl for x in nd.syms])
    if not keep.any():
        return 0.0, 0.0, []
    n_raw = max(nd.n_raw - int((~keep).sum()), 1)
    frac = min(1.0 / keep.sum(), 0.10) * min(1.0, 30 / n_raw) if (~keep).any() else nd.frac
    w = sg.night_tilt(nd.vol20[keep], nd.day_ret[keep], 0.25)
    c = B.cost_bps(cost, nd.price[keep], nd.adv[keep])
    per = leg * frac * w * (weekend if s._gap(d) > 1 else 1.0)
    sh = np.floor(per / nd.price[keep])
    if cash_cap is not None:
        # verifier M3: the LIVE executor's rule -- full 0.5E sizing, names in day_ret order
        # (loser_picks sorts ascending), skip a name once book cash would go below 0.
        order = np.argsort(nd.day_ret[keep], kind="stable")
        cash = cash_cap
        for j in order:
            cst = sh[j] * nd.price[keep][j]
            if cash - cst < 0:
                sh[j] = 0.0
            else:
                cash -= cst
    v = sh * nd.close[keep]
    net = nd.ret[keep] - 2 * c / 1e4
    tr = [(sy, vv, rr) for sy, vv, rr in zip(nd.syms[keep], v, net) if vv > 0]
    return float((v * net).sum()), float(v.sum()), tr


def ibs_leg(legs, leg, excl=frozenset(), cost_bps=1.0):
    legs = [x for x in legs if x[0] not in excl]
    if not legs or leg <= 0:
        return 0.0, 0.0, []
    per = leg / len(legs); pnl = used = 0.0; tr = []
    for sy, o1, r in legs:
        sh = np.floor(per / o1)
        v = sh * o1
        if v > 0:
            pnl += v * (r - 2 * cost_bps / 1e4); used += v; tr.append((sy, v, r - 2 * cost_bps / 1e4))
    return pnl, used, tr


def bil(s, d):
    b = s.bil.get(d, 0.0)
    return float(b) if np.isfinite(b) else 0.0


# ------------------------------------------------------------ the Roth book
@dataclass
class RV:
    mech: str = "M1"            # M1 | M2 | asis
    L: float = 1.5              # intraday cap, underlying leverage
    budget: str = "night"       # night | all
    conv: float = 0.0
    v6: str | None = None       # None | ibs | all
    ibs_full: float | None = None
    ibs_days: frozenset | None = None     # placebo for C: the days IBS goes full
    v6_held: dict | None = None           # placebo for A


class Roth:
    """Step-able Roth book so the guard study can run it beside the taxable book."""

    def __init__(self, s, nz, held, v: RV, cost, start=ROTH0, monthly=ROTH_MO):
        self.s, self.nz, self.v, self.cost = s, nz, v, cost
        self.held = v.v6_held if v.v6_held is not None else held
        self.E, self.monthly = start, monthly
        self.ibs_prev_v = 0.0          # IBS $ held through today's session and tonight
        self.rows, self.i = [], 0

    def step(self, d, n_excl=frozenset(), i_excl=frozenset()):
        s, v, E = self.s, self.v, None
        if self.i and self.i % 21 == 0:
            self.E += self.monthly
        self.i += 1
        E = self.E
        out = dict(night=0.0, ibs=0.0, noise=0.0, v6=0.0, idle=0.0, conv=0.0)
        trades = {"night": [], "ibs": [], "noise": [], "buy3x": set()}
        # ---- daytime: 3x ETFs on free cash
        free = E - self.ibs_prev_v
        cash3x = min(0.5 * E, free) if v.budget == "night" else free
        cap = min(v.L, 3.0 * cash3x / E) if E > 0 else 0.0
        held3x = 0.0
        for sym, share in S2.items():
            z = self.nz[sym]
            if d not in z.index or cap <= 0:
                continue
            lev = min(float(z.at[d, "lev"]), cap) * share
            if v.mech == "M1":
                r, t = float(z.at[d, "r40"]), z.at[d, "t40"]
            else:                              # M2 / M2L / M3 / asis hold to 15:57
                r, t = float(z.at[d, "r57"]), z.at[d, "t57"]
                if z.at[d, "pos40"] != 0:
                    held3x += E * lev / 3.0
            if t > 0:
                pair = {"QQQ": ("TQQQ", "SQQQ"), "SMH": ("SOXL", "SOXS")}[sym]
                trades["buy3x"].update(pair)      # either side may be bought today
            x = E * lev * (r - t * LEV_X / 1e4)
            out["noise"] += x
            trades["noise"].append((sym, E * lev / 3, x))
        if v.conv and self.ibs_prev_v == 0 and d in s.BO.index:   # IBS idle half's daytime cash
            out["conv"] += min(v.conv, 0.5) * E * float(s.BO.at[d])
        # ---- close d: night leg on the cash free at 15:40
        cash40 = E - self.ibs_prev_v - (held3x if v.mech in ("M2", "M2L", "M3") else 0.0)
        if v.mech in ("M2L", "M3"):
            # verifier: live parks the idle IBS half in SGOV all day (executor._ibs_open), so
            # that money is NOT cash at 15:40; the 3x ETFs come out of the night half.
            cash40 = E - (self.ibs_prev_v if self.ibs_prev_v > 0 else 0.5 * E) - held3x
        nleg = 0.5 * E if v.mech in ("asis", "M3") else max(0.0, min(0.5 * E, cash40))
        nd = s.N.get(d)
        pn, nused, trn = night_leg(s, nd, nleg, self.cost, n_excl, d=d,
                                   cash_cap=max(0.0, cash40) if v.mech == "M3" else None)
        out["night"] += pn; trades["night"] = trn
        # ---- V6 oversold overnight on idle money
        v6_used = 0.0
        cur = self.held.get(d) if v.v6 else None
        if cur:
            pool = 0.5 * E if self.ibs_prev_v == 0 else 0.0
            if v.v6 == "all":
                pool = max(0.0, E - self.ibs_prev_v - nused)
            pool = min(pool, max(0.0, cash40 - nused))
            if pool > 0:
                per = pool / len(cur); c = V6C[self.cost]
                for k, (px, r) in cur.items():
                    val = np.floor(per / px) * px
                    v6_used += val
                    out["v6"] += val * (r - 2 * c / 1e4)
        # ---- IBS key d: bought at the open d+1
        w = 0.5
        if v.ibs_full is not None:
            empty = (nd is None) if v.ibs_days is None else (d in v.ibs_days)
            if empty:
                w = v.ibs_full
        pi, iused, tri = ibs_leg(s.I.get(d, []), w * E, i_excl)
        out["ibs"] += pi; trades["ibs"] = tri
        idle = max(0.0, 0.5 * E - iused)
        out["idle"] += idle * bil(s, d) - v6_used * bil(s, d)
        self.ibs_prev_v = iused
        pl = sum(out.values())
        self.rows.append((d, pl / E, out["night"] / E, out["ibs"] / E, out["noise"] / E,
                          out["v6"] / E, out["conv"] / E, out["idle"] / E,
                          (nused + v6_used + self.ibs_prev_v) / E, max(0.0, 0.5 * E - nused) / E,
                          idle / E))
        self.E += pl
        return trades, pl

    def frame(self):
        df = pd.DataFrame(self.rows, columns=["date", "r", "r_night", "r_ibs", "r_noise", "r_v6", "r_conv",
                                              "r_idle", "gross", "night_idle", "ibs_idle"]).set_index("date")
        return df


def run_roth(ctx, v: RV, cost, dates=None, **kw):
    s, c, nz, held = ctx
    R = Roth(s, nz, held, v, cost, **kw)
    for d in (s.days if dates is None else dates):
        R.step(d)
    return R.frame()


def eh(df):
    cut = 0.5 * sum(df[k].mean() for k in ("r_night", "r_ibs", "r_noise", "r_v6", "r_conv"))
    return df["r"] - cut


# ------------------------------------------------------------ 2016-20 holdout (returns book)
def holdout(ctx, v: RV, a="2016-02-01", b="2020-12-31"):
    s, c, nz, held = ctx
    night, ibs, bl_, _, bo = c["legs"]
    days = s.C.index[(s.C.index >= a) & (s.C.index <= b)]
    out, prev_ibs = {}, False
    hv = v.v6_held if v.v6_held is not None else held
    for d in days:
        bl = float(np.nan_to_num(bl_.get(d, 0.0)))
        free = 1.0 - (0.5 if prev_ibs else 0.0)
        cash3x = min(0.5, free) if v.budget == "night" else free
        cap = min(v.L, 3 * cash3x)
        x, held3x = 0.0, 0.0
        for sym, share in S2.items():
            z = nz[sym]
            if d in z.index:
                lev = min(float(z.at[d, "lev"]), cap) * share
                col, t = ("r40", "t40") if v.mech == "M1" else ("r57", "t57")
                x += lev * (float(z.at[d, col]) - z.at[d, t] * LEV_X / 1e4)
                if v.mech == "M2" and z.at[d, "pos40"] != 0:
                    held3x += lev / 3
        if v.conv and not prev_ibs:
            x += min(v.conv, 0.5) * float(bo.get(d, 0.0))
        nv = night.get(d, np.nan)
        nw = 0.5 if v.mech in ("asis", "M1") else max(0.0, 0.5 - held3x)
        x += nw * float(nv) if np.isfinite(nv) else 0.5 * bl * (d < pd.Timestamp("2020-01-02"))
        cur = hv.get(d) if v.v6 else None
        # verifier fix: A2 ("all") was modelled identically to A1 here; pool = all idle
        # overnight money (IBS idle half + unused night half), capped by cash free at 15:40,
        # V6 cost at 3bp/side (the measured planning level) instead of 1bp.
        n_used = nw if np.isfinite(nv) else 0.0
        if cur:
            pool = 0.0 if prev_ibs else 0.5
            if v.v6 == "all":
                pool = max(0.0, 1.0 - (0.5 if prev_ibs else 0.0) - n_used)
            pool = min(pool, max(0.0, 1.0 - (0.5 if prev_ibs else 0.0) - held3x - n_used))
            if pool > 0:
                x += pool * (float(np.mean([r for _, r in cur.values()])) - 2 * V6C[3.0] / 1e4 - bl)
        iv = ibs.get(d, np.nan)
        x += 0.5 * (float(iv) if np.isfinite(iv) else bl)
        prev_ibs = bool(np.isfinite(iv))
        out[d] = x
    return pd.Series(out)


# ------------------------------------------------------------ taxable V7 book (steppable)
class Taxable:
    """V7 as live today: 0.5 + 0.5 overnight, QQQ/SMH noise at cap 0.75 (TQQQ 75% margin), no
    conviction (shadow). Taxable noise switches QQQ->QQQM / SMH->SOXX when the guard blocks."""

    def __init__(self, s, cost, start=TAX0, monthly=TAX_MO, conv=0.0):
        self.s, self.cost, self.E, self.monthly, self.i = s, cost, start, monthly, 0
        self.conv = conv
        self.rows = []

    def step(self, d, n_excl=frozenset(), i_excl=frozenset()):
        s = self.s
        if self.i and self.i % 21 == 0:
            self.E += self.monthly
        self.i += 1
        E = self.E
        out = dict(night=0.0, ibs=0.0, noise=0.0, idle=0.0)
        trades = {"noise": []}
        for sym, share in S2.items():
            z = s.NZ[sym]
            if d in z.index:
                lev = min(float(z.at[d, "lev"]), 0.75) * share
                x = E * lev * float(z.at[d, "ret"])
                out["noise"] += x
                if z.at[d, "trades"] > 0:
                    trades["noise"].append((sym, E * lev, x))
        if self.conv and d in s.BO.index:
            out["noise"] += E * self.conv * float(s.BO.at[d])
        pn, nused, trn = night_leg(s, s.N.get(d), 0.5 * E, self.cost, n_excl, d=d)
        pi, iused, tri = ibs_leg(s.I.get(d, []), 0.5 * E, i_excl)
        out["night"], out["ibs"] = pn, pi
        out["idle"] = (0.5 * E - iused) * bil(s, d)
        trades["night"], trades["ibs"] = trn, tri
        pl = sum(out.values())
        self.rows.append((d, pl / E, out["night"] / E, out["ibs"] / E, out["noise"] / E, pl))
        self.E += pl
        return trades, pl

    def frame(self):
        return pd.DataFrame(self.rows, columns=["date", "r", "r_night", "r_ibs", "r_noise", "pl"]).set_index("date")


# ------------------------------------------------------------ guards (d)
def run_pair(ctx, guard: str, cost, vroth: RV, conv=0.0, scale=1.0):
    """Both books day by day. G0-G3: live order (taxable first each phase). G4 (POST-HOC):
    Roth first, taxable yields every name the Roth traded in 31 days. Tracks each symbol's last
    trade date per book and the taxable loss sales for the permanent cross-account wash-sale
    count (Roth purchase of the same symbol within +-30 calendar days of a taxable loss sale)."""
    s, c, nz, held = ctx
    T = Taxable(s, cost, TAX0 * scale, TAX_MO * scale, conv)
    R = Roth(s, nz, held, vroth, cost, ROTH0 * scale, ROTH_MO * scale)
    lastT, lastR = {}, {}
    lossT, buysR = [], []
    lossT_last = {}
    win, w30 = pd.Timedelta(days=31), pd.Timedelta(days=30)
    look = guard in ("G2", "G3", "G4", "G4s")           # Roth IBS on look-alikes
    # G4s (verifier sensitivity): G4 but the Roth uses look-alikes only for DIFFERENT-index
    # pairs; SPY/QQQ/IWM/MDY/EEM IBS days are skipped when taxable traded them in 31 days.
    safe_la = {k: v for k, v in LOOKALIKE.items() if k not in SAME_INDEX}
    for d in s.days:
        il = [x[0] for x in s.I.get(d, [])]
        recentR = {k for k, t in lastR.items() if d - t <= win}
        recentT = {k for k, t in lastT.items() if d - t <= win}
        lossy = {k for k, t in lossT_last.items() if d - t <= w30}

        def do_T(block_n, block_i):
            tt, _ = T.step(d, block_n, block_i)
            today = set()
            for sym, val, x in tt["noise"]:
                inst = sym if not (guard == "G1" and sym in recentR) else {"QQQ": "QQQM", "SMH": "SOXX"}[sym]
                today.add(inst)
                if x < 0:
                    lossT.append((d, inst, val, -x))
            for leg in ("night", "ibs"):
                for sym, val, r in tt[leg]:
                    today.add(sym)
                    if r < 0:
                        lossT.append((d + pd.Timedelta(days=1), sym, val, -val * r))
                        lossT_last[sym] = d
            for k in today:
                lastT[k] = d
            return today

        def do_R(block_n, block_i):
            rt, _ = R.step(d, block_n, block_i)
            today = set()
            for sym, val, r in rt["night"]:
                today.add(sym); buysR.append((d, sym, val))
            for sym, val, r in rt["ibs"]:
                inst = (safe_la if guard == "G4s" else LOOKALIKE).get(sym, sym) if look else sym
                today.add(inst); buysR.append((d + pd.Timedelta(days=1), inst, val))
                if look and sym in SAME_INDEX and inst != sym:
                    buysR.append((d + pd.Timedelta(days=1), "~" + sym, val))
            today |= rt["buy3x"]
            for k in today:
                lastR[k] = d
            return today

        if guard in ("G4", "G4s"):
            la = safe_la if guard == "G4s" else LOOKALIKE
            r_i = frozenset(k for k in il if k not in la and k in recentT)
            today_R = do_R(frozenset(lossy), r_i)
            do_T(frozenset(recentR | today_R), frozenset())
            continue
        if guard == "G1":
            t_n = t_i = frozenset(recentR)
        elif guard == "G2":
            t_n, t_i = frozenset(recentR), frozenset()
        else:
            t_n = t_i = frozenset()
        today_T = do_T(t_n, t_i)
        recentT |= today_T
        if guard == "G1":
            r_n = r_i = frozenset(recentT)
        elif guard in ("G2", "G3"):
            r_i = frozenset(k for k in il if k not in LOOKALIKE and k in recentT)
            r_n = frozenset(recentT) if guard == "G2" else frozenset(today_T | lossy)
        else:
            r_n = r_i = frozenset()
        do_R(r_n, r_i)
    by = {}
    for d, sym, val in buysR:
        by.setdefault(sym, []).append((d, val))
    dis, dis_si = {}, {}
    gross_loss = {}
    for d, sym, val, loss in lossT:
        gross_loss[d.year] = gross_loss.get(d.year, 0.0) + loss
        for key, acc in ((sym, dis), ("~" + sym, dis_si)):
            hit = [v for t, v in by.get(key, []) if abs((t - d).days) <= 30]
            if hit:
                acc[d.year] = acc.get(d.year, 0.0) + loss * min(1.0, max(hit) / max(val, 1e-9))
    return T.frame(), R.frame(), dis, dis_si, gross_loss


def taxable_end(Tdf, dis: dict, start, mo):
    """Taxable end $: 32% on each calendar year's net gain (losses carried forward); a
    permanently disallowed loss is simply not deductible (adds to that year's taxable gain)."""
    E, carry, year, y0, dep_y = start, 0.0, Tdf.index[0].year, start, 0.0

    def settle(E, carry, yr):
        gain = E - y0 - dep_y + carry + dis.get(yr, 0.0)
        if gain > 0:
            return E - TAX * gain, 0.0
        return E, gain
    for i, (d, x) in enumerate(Tdf.r.items()):
        if d.year != year:
            E, carry = settle(E, carry, year)
            y0, dep_y, year = E, 0.0, d.year
        if i and i % 21 == 0:
            E += mo; dep_y += mo
        E *= 1 + x
    return settle(E, carry, year)[0]


# ------------------------------------------------------------ report helpers
def fmt(r):
    a, b, f = B.stats(r[:"2023-12-31"]), B.stats(r["2024-01-01":]), B.stats(r)
    return f"{a[0]*100:5.1f}/{a[1]:4.2f}  {b[0]*100:5.1f}/{b[1]:4.2f}  {f[0]*100:5.1f}/{f[1]:4.2f}/{f[2]*100:4.0f}"


def ep(r, a, b):
    return ((1 + r[a:b]).prod() - 1) * 100


def dollars_end(r, start=ROTH0, mo=ROTH_MO):
    E = start
    for i, x in enumerate(r.fillna(0).values):
        if i and i % 21 == 0:
            E += mo
        E *= 1 + x
    return E


VARS = {
    "asis (add. 20 b1, infeasible)": RV(mech="asis"),
    "M1 base: flatten 3x at 15:40": RV(mech="M1"),
    "M2 base: hold to 15:57, night on free cash": RV(mech="M2"),
}


def main():
    ctx = load_ctx()
    s, c, nz, held = ctx
    days = s.days
    hdr = f"{'':46s}{'cost':>8s}   2021-23      2024-26      full CAGR/Sh/DD"
    res = {}

    def go(lab, v):
        res[lab] = {k: run_roth(ctx, v, k) for k in COSTS}
        for k in COSTS:
            print(f"  {lab:44s}{str(k):>8s}   {fmt(res[lab][k].r)}", flush=True)

    print("== 0. mechanics: the 15:40 cash conflict\n" + hdr)
    for lab, v in VARS.items():
        go(lab, v)
    for sym in S2:
        z = nz[sym].reindex(days)
        print(f"  {sym}: noise leg still in at 15:40 on {(z.pos40 != 0).mean():.0%} of sessions; "
              f"15:40 vs 15:57 exit, mean {((z.r40 - z.r57).mean())*1e4:+.2f}bp/day unlevered")
    b1 = res["asis (add. 20 b1, infeasible)"]["tier"]
    m2 = res["M2 base: hold to 15:57, night on free cash"]["tier"]
    print(f"  night leg used $ / equity, asis {b1.gross.mean():.3f} vs M2 {m2.gross.mean():.3f} (gross incl IBS)")
    base_lab = max(("M1 base: flatten 3x at 15:40", "M2 base: hold to 15:57, night on free cash"),
                   key=lambda k: B.stats(res[k]["tier_hi"].r)[0])
    BASE = VARS[base_lab]
    print(f"  -> precise baseline = {base_lab}")
    bm = BASE.mech

    # ---------- (a) idle cash
    df = res[base_lab][3.0]
    print(f"\n== a. idle money in the precise baseline: overnight gross mean {df.gross.mean():.2f}x; "
          f"night half idle {df.night_idle.mean()/0.5:.0%} of its money, IBS half idle "
          f"{df.ibs_idle.mean()/0.5:.0%} (T-bills); both halves: {(df.night_idle + df.ibs_idle).mean():.0%} "
          f"of equity-nights idle")
    A = {"A1 V6 in IBS idle half": RV(mech=bm, v6="ibs"), "A2 V6 on all idle overnight money": RV(mech=bm, v6="all")}
    B_ = {"B1 L 0.75": RV(mech=bm, L=0.75), "B2 L 1.0": RV(mech=bm, L=1.0), "B3 L 1.5 (shipped)": RV(mech=bm, L=1.5),
          "B4 L<=3.0 on all day cash": RV(mech=bm, L=3.0, budget="all"),
          "B5 L 1.5 + conviction 0.5 (IBS idle cash)": RV(mech=bm, conv=0.5)}
    C_ = {"C1 IBS 1.0 after a no-pick night": RV(mech=bm, ibs_full=1.0),
          "C2 IBS 0.75 after a no-pick night": RV(mech=bm, ibs_full=0.75)}
    print(hdr)
    for group in (A, B_, C_):
        for lab, v in group.items():
            go(lab, v)
        print()

    base_r = {k: res[base_lab][k].r for k in COSTS}
    ho_base = holdout(ctx, BASE)
    print("== verdict table: dSharpe vs precise baseline (21-23 / 24-26 at 3bp and tier_hi), "
          "NW t (3bp), holdout 2016-20 CAGR/Sh (and dSh), EH x tier_hi, 5y MC under EH x tier_hi")
    allv = {base_lab: BASE, **A, **B_, **C_}
    summ = {}
    for lab, v in allv.items():
        d3 = [B.stats(res[lab][3.0].r[a:b])[1] - B.stats(base_r[3.0][a:b])[1] for a, b in (("2021", "2023-12-31"), ("2024", "2026-12-31"))]
        dh = [B.stats(res[lab]["tier_hi"].r[a:b])[1] - B.stats(base_r["tier_hi"][a:b])[1] for a, b in (("2021", "2023-12-31"), ("2024", "2026-12-31"))]
        dc = [B.stats(res[lab][k].r[a:b])[0] - B.stats(base_r[k][a:b])[0] for k in (3.0, "tier_hi") for a, b in (("2021", "2023-12-31"), ("2024", "2026-12-31"))]
        t = tstat(res[lab][3.0].r - base_r[3.0], 5)
        ho = holdout(ctx, v)
        hs = B.stats(ho)
        e = eh(res[lab]["tier_hi"])
        es = B.stats(e)
        m1, m2_ = G.mc(e, 3000, 1000), G.mc(e, 10000, 0)
        summ[lab] = dict(d3=d3, dh=dh, dc=dc, t=t, ho=hs, dho=hs[1] - B.stats(ho_base)[1], eh=es, m1=m1, m2=m2_, hor=ho)
        print(f"  {lab:44s} dSh3 {d3[0]:+.2f}/{d3[1]:+.2f} dShHi {dh[0]:+.2f}/{dh[1]:+.2f} "
              f"dCAGR {'/'.join(f'{x*100:+.1f}' for x in dc)}  t {t:+.2f}  HO {hs[0]*100:5.1f}/{hs[1]:4.2f} ({summ[lab]['dho']:+.2f})"
              f"  EH {es[0]*100:5.1f}/{es[1]:4.2f}/{es[2]*100:4.0f}  MC3k med ${m1['med']:,.0f} "
              f"P30 {m1['dd30']:.0%} P50 {m1['dd50']:.0%} | 10k med ${m2_['med']:,.0f} P30 {m2_['dd30']:.0%}", flush=True)

    # ---------- placebos: A (V6 dates shuffled per symbol), C (random full-IBS days)
    print("\n== placebos (50 seeds), dSharpe vs baseline at 3bp, 2021-23 / 2024-26")
    for lab, v in A.items():
        real = summ[lab]["d3"]; ps = []
        for seed in range(50):
            ph = placebo_ovn(s, held, seed)
            r = run_roth(ctx, RV(mech=bm, v6=v.v6, v6_held=ph), 3.0).r
            ps.append([B.stats(r[a:b])[1] - B.stats(base_r[3.0][a:b])[1] for a, b in (("2021", "2023-12-31"), ("2024", "2026-12-31"))])
        ps = np.array(ps)
        print(f"  {lab:44s} real {real[0]:+.2f}/{real[1]:+.2f}  placebo mean {ps[:,0].mean():+.2f}/{ps[:,1].mean():+.2f}"
              f"  beats {(real[0] > ps[:,0]).sum()}/50, {(real[1] > ps[:,1]).sum()}/50", flush=True)
    n_empty = sum(1 for d in days if s.N.get(d) is None)
    for lab, v in C_.items():
        real = summ[lab]["d3"]; ps = []
        for seed in range(50):
            rng = np.random.default_rng(seed)
            fd = frozenset(rng.choice(np.array(days), size=n_empty, replace=False))
            r = run_roth(ctx, RV(mech=bm, ibs_full=v.ibs_full, ibs_days=fd), 3.0).r
            ps.append([B.stats(r[a:b])[1] - B.stats(base_r[3.0][a:b])[1] for a, b in (("2021", "2023-12-31"), ("2024", "2026-12-31"))])
        ps = np.array(ps)
        print(f"  {lab:44s} real {real[0]:+.2f}/{real[1]:+.2f}  placebo mean {ps[:,0].mean():+.2f}/{ps[:,1].mean():+.2f}"
              f"  beats {(real[0] > ps[:,0]).sum()}/50, {(real[1] > ps[:,1]).sum()}/50  ({n_empty} no-pick nights)", flush=True)

    # ---------- Kelly view of the intraday dial
    print("\n== b. Kelly: EH x tier_hi CAGR vs intraday cap L (night budget; L>1.5 only with all day cash)")
    for L in (0.0, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0):
        v = RV(mech=bm, L=L, budget="night" if L <= 1.5 else "all")
        df_ = run_roth(ctx, v, "tier_hi"); e = eh(df_); m = G.mc(e, 3000, 1000)
        print(f"  L {L:4.2f}  hist {fmt(df_.r)}  | EH {fmt(e)} | MC3k P30 {m['dd30']:.0%} P50 {m['dd50']:.0%}", flush=True)

    # ---------- crash episodes, worst day / month (tier_hi)
    print("\n== crash episodes (tier_hi; COVID from the 2016-20 holdout book), worst day / month")
    for lab in allv:
        r = res[lab]["tier_hi"].r; ho = summ[lab]["hor"]
        wm = (1 + r).resample("ME").prod().min() - 1
        print(f"  {lab:44s} COVID {ep(ho, '2020-02-19', '2020-03-23'):+6.1f}%  2022 {ep(r, '2022-01-03', '2022-10-12'):+6.1f}%"
              f"  Apr25 {ep(r, '2025-04-02', '2025-04-08'):+6.1f}%  worst day {r.min()*100:5.1f}%  worst month {wm*100:5.1f}%")

    main_d(ctx, BASE)
    pickle.dump({k: {c_: v.r for c_, v in d_.items()} for k, d_ in res.items()}, open(f"{SCR}/roth_opt_results.pkl", "wb"))


def main_d(ctx, BASE):
    s, c, nz, held = ctx
    days, bm = s.days, BASE.mech
    # ---------- (d) asset location and wash sales
    print("\n== d. asset location: taxable V7 per-leg pre-tax contribution (pp/yr of equity) = tax drag x 1/0.32")
    T = Taxable(s, "tier_hi")
    for d in days:
        T.step(d)
    tf = T.frame()
    for k in ("r_night", "r_ibs", "r_noise"):
        print(f"  {k:10s} {tf[k].mean()*252*100:6.1f}pp/yr  -> tax drag {TAX*tf[k].mean()*252*100:5.1f}pp/yr   "
              f"loss-sale share of round trips {(tf[k] < 0).mean():.0%} of days")
    print("  every leg holds <= 1 session: 100% short-term; no leg earns long-term treatment.")
    print(f"\n-- guards: taxable ${TAX0:,.0f}+${TAX_MO:,.0f}/mo beside Roth ${ROTH0:,.0f}+${ROTH_MO:,.0f}/21d "
          f"(Roth = precise baseline {bm}); G4 is POST-HOC")
    print(f"  {'':12s}{'cost':>8s}  taxable 21-23 / 24-26 / full    Roth 21-23 / 24-26 / full   "
          f"perm. disallowed (% of taxable gross losses; same-index look-alike risk)   after-tax end $ T + R")
    for cost in (3.0, "tier_hi"):
        for g in ("G0", "G1", "G2", "G3", "G4"):
            for sc, lab in ((1.0, "user"), (100000 / ROTH0, "100k")):
                Tdf, Rdf, dis, dis_si, gl = run_pair(ctx, g, cost, BASE, scale=sc)
                Tend = taxable_end(Tdf, dis, TAX0 * sc, TAX_MO * sc)
                Tend_si = taxable_end(Tdf, {y: dis.get(y, 0) + dis_si.get(y, 0) for y in set(dis) | set(dis_si)}, TAX0 * sc, TAX_MO * sc)
                Rend = dollars_end(Rdf.r, ROTH0 * sc, ROTH_MO * sc)
                ft = lambda r: "/".join(f"{B.stats(x)[0]*100:4.1f}" for x in (r[:"2023-12-31"], r["2024-01-01":], r))
                pct = sum(dis.values()) / max(sum(gl.values()), 1e-9)
                psi = sum(dis_si.values()) / max(sum(gl.values()), 1e-9)
                print(f"  {g:4s}{lab:>8s}{str(cost):>8s}  {ft(Tdf.r):>24s}    {ft(Rdf.r):>24s}   "
                      f"{pct:6.1%} (+{psi:5.1%})   T ${Tend:>11,.0f} (${Tend_si:>11,.0f} if look-alikes wash) "
                      f"+ R ${Rend:>11,.0f} = ${Tend + Rend:>11,.0f}", flush=True)
    # EH version of the guard choice at user size, tier_hi
    print("-- EH x tier_hi (each book's leg means halved), user size: CAGR taxable / Roth")
    for g in ("G1", "G2", "G3", "G4"):
        Tdf, Rdf, dis, dis_si, gl = run_pair(ctx, g, "tier_hi", BASE)
        te = Tdf.r - 0.5 * (Tdf.r_night.mean() + Tdf.r_ibs.mean() + Tdf.r_noise.mean())
        print(f"  {g}  taxable EH {B.stats(te)[0]*100:5.1f}%   Roth EH {B.stats(eh(Rdf))[0]*100:5.1f}%   "
              f"(taxable pre-tax; x0.68 after tax)", flush=True)


if __name__ == "__main__":
    import sys
    if "--only-d" in sys.argv:
        main_d(load_ctx(), RV(mech="M2"))
    else:
        main()
