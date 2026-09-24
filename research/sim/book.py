"""One simulator for the live daily book (NEXT.md: "consolidate research").

Every decision goes through swingtrader.daily.signals, the module the live
executor calls: loser_picks, dedupe_correlated, night_sizing, momentum_top,
ibs_targets, noise_sigma / noise_bounds / noise_decide / noise_leverage. So a
change to a live rule changes this simulator too, and a research result can
no longer come from a hand-written copy that drifted (addendum 14's lookahead
lived in exactly such a copy).

Decisions are precomputed once per day (they do not depend on the account),
then `replay` walks the days in dollars: whole shares, deposits, margin
interest, and a per-name cost model.

    from research.sim import book as B
    s = B.Sim()                       # loads the cached research data
    r = s.replay()                    # live config, $3k + $1k / 21 sessions
    B.summary(r)
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import data as D

START, END = pd.Timestamp("2021-02-01"), pd.Timestamp("2026-09-18")
EQ18 = ["SPY", "QQQ", "IWM", "DIA", "MDY", "XLK", "XLF", "XLE", "XLV", "XLI",
        "XLY", "XLP", "XLU", "XLB", "SMH", "XBI", "EEM", "EFA"]


# --------------------------------------------------------------- costs
TIERS = {  # per side, bps: (price < $10, $10-20, >$20 & ADV < $50M, rest). ASSUMED, not measured
    "tier": (15.0, 10.0, 7.5, 5.0),
    "tier_hi": (25.0, 15.0, 10.0, 7.5),     # pessimistic: open prints off the auction
}


def cost_bps(model: str | float, price: np.ndarray, adv: np.ndarray) -> np.ndarray:
    """Per-side cost of a night-leg auction order, in bps, per name.

    float -> flat (research used 7.5)
    "tier" / "tier_hi" -> by price and dollar volume. Cheap, thin names cost
    more. The tiers are assumptions until daily-decisions-live.jsonl (quoted
    spreads at 15:40) and the fill log can fit them; a daily-bar spread
    estimator was tried and rejected -- on 60-120%-vol names it measures
    volatility (median 369bp), not the spread."""
    price = np.asarray(price, float)
    if not isinstance(model, str):
        return np.full(len(price), float(model))
    a, b, c, d = TIERS[model]
    adv = np.asarray(adv, float)
    return np.where(price < 10, a, np.where(price < 20, b, np.where(adv < 5e7, c, d)))


# ----------------------------------------------------------- night leg
@dataclass
class NightDay:
    syms: np.ndarray
    price: np.ndarray      # decision price (sizing)
    close: np.ndarray      # close auction price paid
    ret: np.ndarray        # close -> next open
    adv: np.ndarray
    vol20: np.ndarray
    ret20: np.ndarray
    day_ret: np.ndarray
    frac: float            # fraction of the leg per name (sg.night_sizing)
    n_raw: int


def night_days(vol_min: float = 0.60, crowd_n: int = 30, max_name_pct: float = 0.10,
               max_corr: float | None = 0.9, price_min: float = 5.0) -> dict:
    x = D.night_candidates()
    R = D.returns20()
    idx = {d: i for i, d in enumerate(R.index)}
    out = {}
    for d, g in x.groupby("date"):
        rows = pd.DataFrame({"price": g.p50.values, "prev_close": g.pc.values,
                             "high": g.H50.values, "low": g.L50.values}, index=g.sym.values)
        keep = g.set_index("sym")
        picks = sg.loser_picks(rows, day_ret_max=-0.08, ibs_max=0.10,
                               price_min=price_min, price_max=2000.0)
        if picks.empty:
            continue
        i = idx.get(pd.Timestamp(d))
        if max_corr is not None and i is not None:
            cols = [s for s in picks.index if s in R.columns]
            win = R.iloc[max(0, i - 20):i][cols]
            rets = {s: win[s].dropna().tolist() for s in cols}
            picks, _ = sg.dedupe_correlated(picks, rets, max_corr)
        picks = picks.assign(vol20=keep.loc[picks.index, "vol20"].values)
        n_raw = len(picks)
        kept, frac = sg.night_sizing(picks, vol_min=vol_min, crowd_n=crowd_n,
                                     max_name_pct=max_name_pct)
        if kept.empty:
            continue
        k = keep.loc[kept.index]
        out[pd.Timestamp(d)] = NightDay(kept.index.values, kept.price.values, k.C.values,
                                        k.ret.values, k.adv.values, k.vol20.values, k.ret20.values,
                                        kept.day_ret.values, frac, n_raw)
    return out


# ------------------------------------------------------------- IBS leg
def ibs_days(top_k: int = 3, ibs_max: float = 0.2) -> dict:
    """day d -> [(sym, open d+1, open d+2 / open d+1 - 1)]: signal on d's
    bar, bought at the next open and re-evaluated the morning after, as live."""
    P = D.etf(); O, H, L, C = P["open"], P["high"], P["low"], P["close"]
    closes = C[EQ18]
    days = C.index
    out, mom_cache = {}, {}
    for j in range(260, len(days) - 2):
        d, today = days[j], days[j + 1]
        m = today.to_period("M")
        if m not in mom_cache:
            mom_cache[m] = sg.momentum_top(closes[closes.index < today], today, top_k)
        uni = mom_cache[m]
        last = {s: {"high": H.at[d, s], "low": L.at[d, s], "close": C.at[d, s]} for s in uni}
        tg = sg.ibs_targets(last, ibs_max)
        legs = [(s, O.at[days[j + 1], s], O.at[days[j + 2], s] / O.at[days[j + 1], s] - 1)
                for s in tg if np.isfinite(O.at[days[j + 1], s]) and np.isfinite(O.at[days[j + 2], s])]
        if legs:
            out[d] = legs
    return out


# ----------------------------------------------------------- noise leg
def noise_days(sym: str, lookback: int = 14, cost: float = 0.5,
               target_vol: float = 0.02) -> pd.DataFrame:
    """Per session: unlevered net return of the noise-area rule and the
    vol-target leverage the live code would pick (uncapped here; the cap is a
    replay parameter). Decisions every 30 min from 10:00, flat at the close."""
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
        pos, entry, pnl, trades = 0, None, 0.0, 0
        for m in range(sg.NOISE_FIRST, 390, sg.NOISE_STEP):
            p = C[i, m]
            new = sg.noise_decide(pos, p, ub[m], lb[m], vwap[i, m])
            if new != pos:
                if pos != 0:
                    pnl += pos * (p / entry - 1); trades += 1
                if new != 0:
                    entry = p; trades += 1
                pos = new
        if pos != 0:
            pnl += pos * (C[i, 389] / entry - 1); trades += 1
        rows.append((days[i], pnl - trades * cost / 1e4, lev, trades))
    return pd.DataFrame(rows, columns=["date", "ret", "lev", "trades"]).set_index("date")


# ------------------------------------------------ conviction day trade
STRENGTH_MIN = 0.341     # in-sample (2016-23) median breakout strength, fixed in addendum 8


def breakout_days(sym: str = "TQQQ", cost: float = 1.5, lookback: int = 14,
                  strength_min: float = STRENGTH_MIN) -> pd.Series:
    """Only the day's FIRST noise-area breakout, and only a strong one
    (distance past the band / sigma >= strength_min). Long above, short below
    (live: short = buy the inverse ETF). Held until the price falls back
    inside the band or through VWAP, else to the close. One round trip at
    most; most days nothing. research/daily-strategies/dt3.py, same rule,
    through the live band functions."""
    M = D.minutes(sym)
    C, V = M["close"].values, M["volume"].values
    O = M["open"].values[:, 0]
    days = M["close"].index
    move = np.abs(C / O[:, None] - 1)
    prevc = np.r_[np.nan, C[:-1, -1]]
    vwap = np.cumsum(C * V, axis=1) / np.maximum(np.cumsum(V, axis=1), 1)
    out = {}
    for i in range(lookback + 1, len(days)):
        sig = sg.noise_sigma(move[i - lookback:i])
        ub, lb = sg.noise_bounds(O[i], prevc[i], sig)
        pos, e, strength, x = 0, None, 0.0, None
        for m in range(sg.NOISE_FIRST, 390, sg.NOISE_STEP):
            p = C[i, m]
            if pos == 0:
                pos, strength = sg.breakout_strength(p, ub[m], lb[m], sig[m])
                e = p
                if pos and strength < strength_min:
                    break                                  # first breakout too weak: no trade today
            elif (pos == 1 and p < max(ub[m], vwap[i, m])) or (pos == -1 and p > min(lb[m], vwap[i, m])):
                x = p; break
        if pos == 0 or strength < strength_min:
            continue
        x = C[i, 389] if x is None else x
        out[days[i]] = pos * (x / e - 1) - 2 * cost / 1e4
    return pd.Series(out)


# --------------------------------------------------------------- replay
@dataclass
class Params:
    night_w: float = 0.5
    ibs_w: float = 0.5
    night_cost: str | float = 7.5         # per side; see cost_bps
    ibs_cost_bps: float = 1.0
    noise: dict = field(default_factory=lambda: {"QQQ": 1.0})   # instrument -> share of budget
    noise_cap: float = 1.5                # Schwab 2x standard margin minus the IBS half
    noise_on: bool = True
    whole: bool = True
    filler: str | None = None             # unused night capital, close -> open: "SPY" | "QQQ"
    filler_cost_bps: float = 1.0
    ibs_idle: str = "bil"                 # idle IBS half: bil | spy | qqq | spy_night | qqq_night | cash
    tilt: object = None                   # f(NightDay) -> weights (mean 1); "live" = signals.night_tilt; None = equal
    tilt_k: float = 0.25                  # k for tilt="live"
    margin_rate: float = 0.12             # Schwab debit rate, small balances (annual)
    min_edge_bps: float | None = None     # skip night names whose round-trip cost exceeds this
    name_cap: float | None = None         # hard cap per night name AFTER the tilt, fraction of the leg
    weekend_scale: float = 1.0            # night exposure x this when held over a weekend/holiday
    overflow_w: float | None = None       # spare night cash goes to names with tilt weight >= this
    overflow_cap: float = 0.25            # ... up to this fraction of the leg per name
    conviction_w: float = 0.0             # TQQQ strong-first-breakout trade, fraction of equity


class Sim:
    def __init__(self, noise_syms=("QQQ",), noise_cost: float = 0.5):
        self.N = night_days()
        self.I = ibs_days()
        P = D.etf(); self.O, self.C = P["open"], P["close"]
        self.bil = self.C["BIL"].pct_change(fill_method=None).shift(-1)
        self.spy = self.C["SPY"].pct_change(fill_method=None)
        on = self.O.shift(-1) / self.C - 1                      # close d -> open d+1
        self.night_idx = on
        self.oo = self.O.shift(-2) / self.O.shift(-1) - 1       # open d+1 -> open d+2 (IBS timing)
        self.NZ = {s: noise_days(s, cost=noise_cost) for s in noise_syms}
        self.days = self.C.index[(self.C.index >= START) & (self.C.index <= END)]

    # one day of P&L, in dollars
    def day_pnl(self, E: float, d, p: Params) -> tuple[float, dict]:
        pnl, info = 0.0, {"night_v": 0.0, "ibs_v": 0.0, "night": 0.0, "ibs": 0.0,
                          "noise": 0.0, "idle": 0.0, "margin": 0.0}
        # --- night leg
        leg = p.night_w * E; used = 0.0
        nd = self.N.get(d)
        if nd is not None:
            if p.tilt is None:
                w = np.ones(len(nd.syms))
            elif p.tilt == "live":
                w = sg.night_tilt(nd.vol20, nd.day_ret, p.tilt_k)
            else:
                w = np.asarray(p.tilt(nd), float)
            c = cost_bps(p.night_cost, nd.price, nd.adv)
            ok = np.ones(len(w), bool)
            if p.min_edge_bps is not None:
                ok = 2 * c <= p.min_edge_bps
            per = leg * nd.frac * w
            if p.weekend_scale != 1.0 and self._gap(d) > 1:
                per = per * p.weekend_scale
            if p.name_cap is not None:
                per = np.minimum(per, leg * p.name_cap)
            if p.overflow_w is not None:
                spare = max(0.0, leg * (p.weekend_scale if self._gap(d) > 1 else 1.0) - per.sum())
                hi = w >= p.overflow_w
                if spare > 0 and hi.any():
                    add = np.where(hi, w, 0.0); add = spare * add / add.sum()
                    per = np.minimum(per + add, np.maximum(per, leg * p.overflow_cap))
            sh = np.floor(per / nd.price) if p.whole else per / nd.price
            sh = np.where(ok, sh, 0.0)
            v = sh * nd.close
            used = float(v.sum())
            x = float((v * (nd.ret - 2 * c / 1e4)).sum())
            pnl += x; info["night"] += x
            info["night_v"] = used
        # --- filler: the night leg's unused money rides the index overnight
        if p.filler:
            spare = max(0.0, leg - used)
            r = self.night_idx.at[d, p.filler] if d in self.night_idx.index else np.nan
            if np.isfinite(r) and spare > 0:
                px = self.C.at[d, p.filler]
                sh = np.floor(spare / px) if p.whole else spare / px
                x = sh * px * (r - 2 * p.filler_cost_bps / 1e4)
                pnl += x; info["night"] += x
                info["night_v"] += sh * px
        # --- IBS leg
        ibs_leg = p.ibs_w * E; iused = 0.0
        for s, o1, r in self.I.get(d, []):
            per = ibs_leg / len(self.I[d])
            sh = np.floor(per / o1) if p.whole else per / o1
            iused += sh * o1
            x = sh * o1 * (r - 2 * p.ibs_cost_bps / 1e4)
            pnl += x; info["ibs"] += x
        idle = ibs_leg - iused
        x = idle * self._idle_ret(d, p.ibs_idle)
        pnl += x; info["idle"] += x
        info["ibs_v"] = iused + (idle if p.ibs_idle not in ("bil", "cash") else 0.0)
        # --- margin interest on an overnight debit
        debit = info["night_v"] + info["ibs_v"] - E
        if debit > 0:
            pnl -= debit * p.margin_rate / 252
            info["margin"] -= debit * p.margin_rate / 252
        # --- conviction day trade (TQQQ), uses daytime buying power only
        if p.conviction_w:
            if not hasattr(self, "BO"):
                self.BO = breakout_days()
            if d in self.BO.index:
                x = E * p.conviction_w * float(self.BO.at[d])
                pnl += x; info["noise"] += x
        # --- intraday leg
        if p.noise_on:
            for s, share in p.noise.items():
                z = self.NZ[s]
                if d in z.index:
                    lev = min(float(z.at[d, "lev"]), p.noise_cap) * share
                    x = E * lev * float(z.at[d, "ret"])
                    pnl += x; info["noise"] += x
        return pnl, info

    def _gap(self, d) -> int:
        if not hasattr(self, "_gaps"):
            ix = self.C.index
            self._gaps = {a: (b - a).days for a, b in zip(ix[:-1], ix[1:])}
        return self._gaps.get(d, 1)

    def _idle_ret(self, d, how: str) -> float:
        if how == "cash":
            return 0.0
        if how == "bil":
            b = self.bil.get(d, 0.0); return float(b) if np.isfinite(b) else 0.0
        sym, kind = (how.split("_") + ["oo"])[:2]
        sym = sym.upper()
        src = self.night_idx if kind == "night" else self.oo
        r = src.at[d, sym] if d in src.index else np.nan
        cost = 2e-4 if kind == "night" else 0.0     # overnight trades daily; open->open holds
        extra = 0.0
        if kind == "night":                          # the day part sits in T-bills
            b = self.bil.get(d, 0.0); extra = float(b) if np.isfinite(b) else 0.0
        return (float(r) - cost if np.isfinite(r) else 0.0) + extra

    def replay(self, p: Params | None = None, start: float = 3000.0, monthly: float = 1000.0,
               dates=None) -> pd.DataFrame:
        p = p or Params()
        dates = self.days if dates is None else dates
        E, dep, sp, rows = start, start, start, []
        for i, d in enumerate(dates):
            if i and i % 21 == 0:
                E += monthly; dep += monthly; sp += monthly
            before = E
            pl, info = self.day_pnl(E, d, p)
            E += pl
            s = self.spy.get(d, 0.0); sp *= 1 + (s if np.isfinite(s) else 0.0)
            k = before if before else 1.0
            rows.append((d, E, dep, sp, pl / k, info["night"] / k, info["ibs"] / k,
                         info["noise"] / k, (info["idle"] + info["margin"]) / k,
                         info["night_v"] / (p.night_w * before) if p.night_w and before else 0.0))
        return pd.DataFrame(rows, columns=["date", "E", "dep", "spy", "r", "r_night", "r_ibs",
                                           "r_noise", "r_cash", "night_used"]).set_index("date")


# ---------------------------------------------------------------- stats
def stats(r: pd.Series) -> tuple[float, float, float]:
    r = r.fillna(0)
    if len(r) < 50:
        return (np.nan, np.nan, np.nan)
    yrs = len(r) / 252
    cagr = (1 + r).prod() ** (1 / yrs) - 1
    sh = r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else 0.0
    eq = (1 + r).cumprod(); dd = (eq / eq.cummax() - 1).min()
    return cagr, sh, dd


def summary(df: pd.DataFrame, label: str = "") -> str:
    """Time-weighted (deposit-neutral) CAGR / Sharpe / maxDD: 2021-23, 2024-26, full."""
    r = df["r"]
    parts = [stats(r[: "2023-12-31"]), stats(r["2024-01-01":]), stats(r)]
    body = "  ".join(f"{c*100:5.1f}%/{s:4.2f}/{d*100:4.0f}" for c, s, d in parts)
    return f"{label:44s} {body}   end ${df.E.iloc[-1]:>9,.0f} (dep {df.dep.iloc[-1]:,.0f})"
