"""Micro index futures (MNQ, MES): do our intraday/overnight edges carry over?

    .venv/bin/python -m research.sim.futures

The ask (2026-09-24): futures as a real strategy at sane leverage, not a
one-day 5x. Same standards as every addendum: tier and tier_hi costs, no
lookahead, 2021-23 and 2024-26 both positive, parameters picked on one half
and judged on the other (and reversed), 2016-20 reported as a holdout,
day-clustered t, placebo controls, +1 tick and 1-minute-late stress.

PROXY. We have no futures data. QQQ minute bars stand in for NQ and SPY for
ES, regular session only (09:30-16:00). So: no signal can use the Globex
session (18:00-09:30), no roll or basis is modelled, and index level is a
fixed multiple of the ETF price (NQ ~ 41 x QQQ, ES ~ 10 x SPY; the ratios
drift a few % over a decade, which moves the $ cost per trade, not returns).
An overnight hold uses the ETF's close -> open gap, which a futures holder
bears too (plus Globex moves the proxy does not see, which net out).

PRE-REGISTERED CANDIDATES AND PRIORS (written before any run)

A. Opening-range breakout on NQ / ES, long or short (futures can short),
   range 5 / 15 / 30 min, stop at the other side, out at 15:57, 1x notional.
   Prior: NEGATIVE / ~0. Addendum 6/8 had QQQ ORB decaying to ~3%/yr after
   2021 and SPY ~0; SOXL ORB15 (addendum 24) was fragile and ~0 in 2016-20.
   Futures costs are lower than the ETF's, so a small edge could survive,
   but I expect it to fail one half. 6 variants.

B. The daily book's noise-band leg (swingtrader/daily/signals.py, the live
   functions) on MNQ and MES instead of QQQ: decisions every 30 min, flat at
   the close, vol-targeted size capped at 2x. Prior: POSITIVE both halves on
   NQ (it is the live leg, Sharpe ~1 on QQQ), weaker on ES. The question is
   not a new edge but whether futures beat the ETF after costs and 60/40
   tax. Parameters were fixed in 2016-23 research, so 2016-20 is NOT a
   holdout here. 2 variants.

C. IBS overnight on NQ / ES: IBS < 0.2 from the day's bars through 15:54,
   buy the 15:59 close, sell the next open or the next close. 1x notional.
   Prior: POSITIVE both halves (IBS is the book's steadiest leg on QQQ/SPY),
   small: ~5-10%/yr at 1x, exposure ~20% of days. 4 variants (2 x 2 exits).

Count: A 6 + B 2 + C 4 = 12 variants.

CONTRACT ECONOMICS (assumptions, stated):
  MNQ = $2 x NQ, tick 0.25 = $0.50.  MES = $5 x ES, tick 0.25 = $1.25.
  Commission + exchange/NFA fees per micro per side: tier $1.00, tier_hi $1.50
  (Schwab's published futures commission is ~$2.25/contract for standard;
  micros are cheaper -- I did not verify the current Schwab micro rate).
  Slippage: 1 tick per side (tier), 2 ticks (tier_hi); market/stop orders.
  Margin: overnight initial ~7% of notional (CME-ish; MNQ ~$4.3k, MES ~$2.7k
  at 2026 levels); intraday ~25% of that. Whole contracts only.
  ETF comparison: QQQ/SPY at 1bp/side (tier), 2bp (tier_hi), no commission.
TAX (assumed combined rates): ordinary/short-term 30%, long-term 15%.
  Section 1256 futures: 60% LT / 40% ST = 21% blended, marked to market
  yearly, no wash-sale rule. ETF day trades: all short-term, 30%.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg
from swingtrader.leap import signals as LS

from . import book as B
from . import data as D

H0 = ("2016-01-01", "2020-12-31")
H1 = ("2021-01-01", "2023-12-31")
H2 = ("2024-01-01", "2026-12-31")

# contract specs: ETF proxy, index/ETF ratio, $ multiplier, tick $ value
SPEC = {"MNQ": dict(etf="QQQ", ratio=41.0, mult=2.0, tick=0.50),
        "MES": dict(etf="SPY", ratio=10.0, mult=5.0, tick=1.25)}
COST = {"tier": dict(comm=1.00, ticks=1), "tier_hi": dict(comm=1.50, ticks=2),
        "stress": dict(comm=1.50, ticks=3)}       # tier_hi + 1 tick
ETF_COST = {"tier": 1.0, "tier_hi": 2.0}           # bps per side, QQQ/SPY
MARGIN_ON = 0.07                                   # overnight initial, fraction of notional
MARGIN_DAY = 0.25 * MARGIN_ON                      # intraday
TAX_ST, TAX_LT = 0.30, 0.15
TAX_1256 = 0.6 * TAX_LT + 0.4 * TAX_ST             # 21%
NOISE_CAP = 2.0


def notional(fut: str, etf_px) -> np.ndarray:
    s = SPEC[fut]
    return np.asarray(etf_px, float) * s["ratio"] * s["mult"]


def side_bps(fut: str, etf_px, model: str) -> np.ndarray:
    """Cost of one side of one contract in bps of its notional."""
    c = COST[model]
    return (c["comm"] + c["ticks"] * SPEC[fut]["tick"]) / notional(fut, etf_px) * 1e4


# --------------------------------------------------------------- A. ORB
def orb(fut: str, orm: int, rng=None, delay: int = 0) -> pd.DataFrame:
    """Gross trade return per day (1x notional, long or short) + entry price."""
    M = D.minutes(SPEC[fut]["etf"])
    O, H, L, C = (M[k].values for k in ("open", "high", "low", "close"))
    days = M["close"].index
    T = []
    for i in range(len(days)):
        b = LS.orb_break(H[i], L[i], orm)
        if b is None:
            continue
        d, m, level, stop = b
        e = LS.orb_fill(d, level, O[i, m])
        if rng is not None:                        # placebo: same day/minute/price, random side
            d = rng.choice((-1, 1))
            stop = e * (1 - d * abs(level - stop) / e)
        if delay:
            m = min(m + delay, 386); e = O[i, m]
        x = C[i, 386]
        for k in range(m, LS.LAST_MINUTE):
            if LS.orb_stopped(d, stop, H[i, k], L[i, k]):
                x = (min(stop, O[i, k]) if d == 1 else max(stop, O[i, k])) if k > m else stop
                break
        if np.isfinite(e) and np.isfinite(x) and e > 0:
            T.append((days[i], d * (x / e - 1), e, 2))
    return pd.DataFrame(T, columns=["date", "g", "px", "sides"])


# ---------------------------------------------------------- B. noise leg
def noise(fut: str, lookback: int = 14, target_vol: float = 0.02, rng=None,
          delay: int = 0) -> pd.DataFrame:
    """The live noise-band rule. g = unlevered gross day return, lev = the
    vol-target size (capped later), sides = contracts traded per unit."""
    M = D.minutes(SPEC[fut]["etf"])
    C, V = M["close"].values, M["volume"].values
    O = M["open"].values[:, 0]
    days = M["close"].index
    move = np.abs(C / O[:, None] - 1)
    dclose = pd.Series(C[:, -1], index=days)
    prevc = np.r_[np.nan, C[:-1, -1]]
    vwap = np.cumsum(C * V, axis=1) / np.maximum(np.cumsum(V, axis=1), 1)
    T = []
    for i in range(lookback + 1, len(days)):
        j = i if rng is None else int(rng.integers(lookback + 1, len(days)))   # placebo: another window's sigma
        sigma = sg.noise_sigma(move[j - lookback:j])
        ub, lb = sg.noise_bounds(O[i], prevc[i], sigma)
        lev = sg.noise_leverage(dclose.iloc[:i], target_vol, 1e9)
        pos, entry, g, sides = 0, None, 0.0, 0
        for m in range(sg.NOISE_FIRST, 390, sg.NOISE_STEP):
            new = sg.noise_decide(pos, C[i, m], ub[m], lb[m], vwap[i, m])
            if new != pos:
                p = C[i, min(m + delay, 389)]
                if pos != 0:
                    g += pos * (p / entry - 1); sides += 1
                if new != 0:
                    entry = p; sides += 1
                pos = new
        if pos != 0:
            g += pos * (C[i, 389] / entry - 1); sides += 1
        T.append((days[i], g, O[i], sides, lev))
    return pd.DataFrame(T, columns=["date", "g", "px", "sides", "lev"])


# ----------------------------------------------------------- C. IBS
def ibs_on(fut: str, exit_: str, th: float = 0.2, rng=None) -> pd.DataFrame:
    """IBS from bars through 15:54, buy the 15:59 close, out next open/close."""
    M = D.minutes(SPEC[fut]["etf"])
    O, H, L, C = (M[k].values for k in ("open", "high", "low", "close"))
    days = M["close"].index
    hit = np.array([LS.ibs_entry(np.nanmax(H[i, :385]), np.nanmin(L[i, :385]), C[i, 384], th)
                    for i in range(len(days))])
    if rng is not None:                            # placebo: same count of random days
        hit = rng.permutation(hit)
    T = []
    for i in np.where(hit[:-1])[0]:
        e = C[i, 389]
        x = O[i + 1, 0] if exit_ == "open" else C[i + 1, 389]
        if np.isfinite(e) and np.isfinite(x):
            T.append((days[i], x / e - 1, e, 2))
    return pd.DataFrame(T, columns=["date", "g", "px", "sides"])


# ---------------------------------------------------------- accounting
def net(tr: pd.DataFrame, fut: str, model: str, etf: bool = False) -> pd.Series:
    """Net trade return per unit of notional, futures or ETF costs."""
    c = ETF_COST[model if model in ETF_COST else "tier_hi"] if etf else side_bps(fut, tr.px, model)
    return tr.g - tr.sides * c / 1e4


def daily(tr: pd.DataFrame, r: pd.Series, idx, lev=None) -> pd.Series:
    w = 1.0 if lev is None else np.minimum(tr["lev"].values, lev)
    return pd.Series((r.values * w), index=tr.date.values).groupby(level=0).sum().reindex(idx).fillna(0.0)


def tday(tr: pd.DataFrame, r: pd.Series, lo, hi) -> tuple[float, float]:
    x = pd.Series(r.values, index=pd.to_datetime(tr.date.values))[lo:hi]
    x = x.groupby(level=0).mean()
    return (x.mean() * 1e4, x.mean() / x.std() * np.sqrt(len(x))) if len(x) > 10 else (np.nan, np.nan)


def row(r: pd.Series):
    return [B.stats(r[a:b]) for a, b in (H0, H1, H2)]


def fmt(parts):
    return "  ".join(f"{c*100:6.1f}/{s:5.2f}/{d*100:4.0f}" for c, s, d in parts)


def after_tax(r: pd.Series, rate: float) -> float:
    """CAGR after a yearly tax on net gains, losses carried forward (2021-26)."""
    r = r["2021-01-01":]
    eq, carry = 1.0, 0.0
    for _, g in r.groupby(r.index.year):
        start = eq
        eq *= float((1 + g).prod())
        gain = eq - start - carry
        if gain > 0:
            eq -= rate * gain; carry = 0.0
        else:
            carry = -gain
    return eq ** (252 / len(r)) - 1


def account_mc(g: np.ndarray, sides: np.ndarray, lev: np.ndarray, fut: str, E0: float,
               target: float, margin: float, n: int = 3000, days: int = 252,
               block: int = 21, seed: int = 11) -> dict:
    """Whole contracts at TODAY's notional: contracts = floor(target x E / N),
    and at least 1 while E covers the margin (a small account is forced to
    the leverage of one contract). Ruin = E below the margin for one contract."""
    rng = np.random.default_rng(seed)
    Nn = float(notional(fut, [D.minutes(SPEC[fut]["etf"])["close"].values[-1, -1]])[0])
    cost = (COST["tier"]["comm"] + COST["tier"]["ticks"] * SPEC[fut]["tick"])
    need = margin * Nn
    st = rng.integers(0, len(g) - block, size=(n, days // block))
    ix = (st[:, :, None] + np.arange(block)[None, None, :]).reshape(n, -1)
    E = np.full(n, E0); peak = E.copy(); dd50 = np.zeros(n, bool); ruin = np.zeros(n, bool)
    for t in range(ix.shape[1]):
        k = ix[:, t]
        want = np.floor(np.minimum(target, lev[k]) * E / Nn)
        q = np.where(E >= need, np.maximum(want, 1), 0)
        E = E + q * (Nn * g[k] - sides[k] * cost)
        ruin |= E < need
        peak = np.maximum(peak, E); dd50 |= E <= 0.5 * E0
    return dict(lev1=Nn / E0, tradable=E0 >= need, med=float(np.median(E) / E0 - 1),
                p50=float(dd50.mean()), ruin=float(ruin.mean()))


def main():
    rng = np.random.default_rng(3)
    idx = D.minutes("QQQ")["close"].index
    out = {}

    print("per-contract cost at 2026 levels, bps/side:",
          {f: {m: round(float(side_bps(f, [D.minutes(SPEC[f]['etf'])['close'].values[-1, -1]], m)[0]), 2)
               for m in COST} for f in SPEC})
    print("\nCAGR/Sharpe/maxDD  2016-20 (holdout)  2021-23  2024-26   | bp/trade & t per half (21-23, 24-26)")

    def show(name, tr, fut, lev=None, etf=False):
        res = {}
        for m in ("tier", "tier_hi"):
            r = net(tr, fut, m, etf)
            res[m] = daily(tr, r, idx, lev)
        r = net(tr, fut, "tier", etf)
        t1, t2 = tday(tr, r, *H1), tday(tr, r, *H2)
        print(f"{name:28} tier    {fmt(row(res['tier']))} | {t1[0]:+6.1f}bp t{t1[1]:+.1f}  {t2[0]:+6.1f}bp t{t2[1]:+.1f}")
        print(f"{'':28} tier_hi {fmt(row(res['tier_hi']))}")
        return res

    # ---- A
    print("\nA. ORB (1x notional, long/short)")
    A = {}
    for fut in SPEC:
        for orm in (5, 15, 30):
            tr = orb(fut, orm); A[(fut, orm)] = tr
            out[f"A {fut} ORB{orm}"] = show(f"{fut} ORB{orm}", tr, fut)
    for fut in SPEC:                                # pick on one half, judge on the other
        m1 = {o: B.stats(out[f"A {fut} ORB{o}"]["tier"][H1[0]:H1[1]])[0] for o in (5, 15, 30)}
        m2 = {o: B.stats(out[f"A {fut} ORB{o}"]["tier"][H2[0]:H2[1]])[0] for o in (5, 15, 30)}
        b1, b2 = max(m1, key=m1.get), max(m2, key=m2.get)
        print(f"  {fut}: best on 21-23 = ORB{b1} -> 24-26 {m2[b1]*100:+.1f}%;  best on 24-26 = ORB{b2} -> 21-23 {m1[b2]*100:+.1f}%")
    for fut in SPEC:
        tr = A[(fut, 15)]
        real = net(tr, fut, "tier").mean() * 1e4
        pl = [net(orb(fut, 15, rng=np.random.default_rng(s)), fut, "tier").mean() * 1e4 for s in range(20)]
        print(f"  placebo {fut} ORB15: real {real:+.2f}bp/trade vs random side max {max(pl):+.2f}, "
              f"beats {sum(real > p for p in pl)}/20")

    # ---- B
    print(f"\nB. noise leg, vol-target capped {NOISE_CAP}x")
    NZ = {}
    for fut in SPEC:
        tr = noise(fut); NZ[fut] = tr
        out[f"B {fut} noise"] = show(f"{fut} noise (futures)", tr, fut, lev=NOISE_CAP)
        out[f"B {fut} noise ETF"] = show(f"{SPEC[fut]['etf']} noise (ETF)", tr, fut, lev=NOISE_CAP, etf=True)
    for fut in SPEC:
        tr = NZ[fut]
        real = net(tr, fut, "tier").mean() * 1e4
        pl = [net(noise(fut, rng=np.random.default_rng(s)), fut, "tier").mean() * 1e4 for s in range(10)]
        print(f"  placebo {fut}: real {real:+.2f}bp/day vs other-window sigma max {max(pl):+.2f}, "
              f"beats {sum(real > p for p in pl)}/10")

    # ---- C
    print("\nC. IBS overnight (1x notional)")
    IB = {}
    for fut in SPEC:
        for ex in ("open", "close"):
            tr = ibs_on(fut, ex); IB[(fut, ex)] = tr
            out[f"C {fut} IBS {ex}"] = show(f"{fut} IBS->{ex} (n={len(tr)})", tr, fut)
    for fut in SPEC:
        m1 = {e: B.stats(out[f"C {fut} IBS {e}"]["tier"][H1[0]:H1[1]])[0] for e in ("open", "close")}
        m2 = {e: B.stats(out[f"C {fut} IBS {e}"]["tier"][H2[0]:H2[1]])[0] for e in ("open", "close")}
        b1, b2 = max(m1, key=m1.get), max(m2, key=m2.get)
        print(f"  {fut}: best on 21-23 = {b1} -> 24-26 {m2[b1]*100:+.1f}%;  best on 24-26 = {b2} -> 21-23 {m1[b2]*100:+.1f}%")
        for ex in ("open", "close"):
            tr = IB[(fut, ex)]
            real = net(tr, fut, "tier").mean() * 1e4
            pl = [net(ibs_on(fut, ex, rng=np.random.default_rng(s)), fut, "tier").mean() * 1e4 for s in range(20)]
            print(f"  placebo {fut} ->{ex}: real {real:+.2f}bp vs random days max {max(pl):+.2f}, beats {sum(real > p for p in pl)}/20")

    # ---- stress
    print("\nStress (2016-20 / 21-23 / 24-26 CAGR at stress = $1.50 + 3 ticks; delay = +1 min fill)")
    for name, tr, fut, lev, fn in [
            ("MNQ noise", NZ["MNQ"], "MNQ", NOISE_CAP, lambda: noise("MNQ", delay=1)),
            ("MES noise", NZ["MES"], "MES", NOISE_CAP, lambda: noise("MES", delay=1)),
            ("MNQ ORB15", A[("MNQ", 15)], "MNQ", None, lambda: orb("MNQ", 15, delay=1)),
            ("MES ORB15", A[("MES", 15)], "MES", None, lambda: orb("MES", 15, delay=1))]:
        s = daily(tr, net(tr, fut, "stress"), idx, lev)
        dl = fn(); d = daily(dl, net(dl, fut, "tier"), idx, lev)
        print(f"  {name:10} stress {'/'.join(f'{c*100:+.1f}' for c, _, _ in row(s))}   "
              f"delay {'/'.join(f'{c*100:+.1f}' for c, _, _ in row(d))}")

    # ---- tax
    print(f"\nAfter-tax CAGR 2021-26 (futures {TAX_1256:.0%} blended 1256, ETF {TAX_ST:.0%} short-term)")
    for k in ("B MNQ noise", "B MES noise", "C MNQ IBS open", "C MES IBS open", "C MNQ IBS close", "C MES IBS close"):
        fut = k.split()[1]
        r = out[k]["tier"]
        if k.startswith("B"):
            re = out[f"B {fut} noise ETF"]["tier"]
        else:
            tr = IB[(fut, k.split()[-1])]
            re = daily(tr, net(tr, fut, "tier", etf=True), idx)
        pre_f, pre_e = B.stats(r["2021-01-01":])[0], B.stats(re["2021-01-01":])[0]
        print(f"  {k:18} futures pre {pre_f*100:5.1f}% -> {after_tax(r, TAX_1256)*100:5.1f}%   "
              f"ETF pre {pre_e*100:5.1f}% -> {after_tax(re, TAX_ST)*100:5.1f}%")

    # ---- account size
    print("\nAccount size, 1 year MC (21-day blocks, 2021-26, whole contracts at 2026 notional, tier costs)")
    print("  rule        E0      1-contract lev  tradable  median  P(-50%)  P(ruin)")
    for name, tr, fut, target, margin in [
            ("MNQ noise", NZ["MNQ"], "MNQ", NOISE_CAP, MARGIN_DAY),
            ("MES noise", NZ["MES"], "MES", NOISE_CAP, MARGIN_DAY),
            ("MES IBS", IB[("MES", "open")], "MES", 1.0, MARGIN_ON),
            ("MNQ IBS", IB[("MNQ", "open")], "MNQ", 1.0, MARGIN_ON)]:
        t = tr.set_index("date").reindex(idx)["2021-01-01":]
        g = t.g.fillna(0).values; sd = t.sides.fillna(0).values
        lev = t["lev"].fillna(0).values if "lev" in t else np.where(np.isfinite(t.g.values), 1.0, 0.0)
        for E0 in (1_000, 5_000, 10_000, 25_000, 50_000):
            m = account_mc(g, sd, lev, fut, E0, target, margin)
            print(f"  {name:10} ${E0:>7,}  {m['lev1']:8.1f}x      {'yes' if m['tradable'] else 'NO ':3}     "
                  f"{m['med']*100:+6.1f}%  {m['p50']*100:5.1f}%  {m['ruin']*100:5.1f}%")


if __name__ == "__main__":
    main()
