"""useThinkScript round U1-U5 (2026-10-08). Spec frozen in window_signals_loop_2026-10-07.md "useThinkScript round".

Entry at open t+1 (or a limit on bar t+1), exit at the OPEN after the first close where the exit condition is true
(no same-close look-ahead), cap KMAX bars. Excess vs the EW liquid universe over the same open t+1 -> open exit span.
Usage: python -m research.sim.uts U1 [--confirm]
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from research.sim import winsig as w, winsig_fam as F

OUT = w.CACHE.parent / "program" / "combo_out.txt"
COST = 10e-4


class Eng:
    def __init__(self, t):
        self.t = t
        self.n = len(t)
        self.code = t.ticker.astype("category").cat.codes.to_numpy()
        adjf = (t.closeadj / t.close).to_numpy("float64")
        self.o = t.open.to_numpy("float64") * adjf
        self.lo = t.low.to_numpy("float64") * adjf
        self.c = t.closeadj.to_numpy("float64")
        self.liq = t.liq.to_numpy(bool)
        self.date = t.date.to_numpy()
        self.bench = {}

    def same(self, i, j):
        ok = j < self.n
        ok[ok] = self.code[j[ok]] == self.code[i[ok]]
        return ok

    def bench_k(self, k):
        """EW liquid open(t+1) -> open(t+1+k), keyed by signal date t."""
        if k not in self.bench:
            i = np.flatnonzero(self.liq)
            e, x = i + 1, i + 1 + k
            ok = self.same(i, x)
            r = self.o[x[ok]] / self.o[e[ok]] - 1
            self.bench[k] = pd.Series(r).groupby(self.date[i[ok]]).mean()
        return self.bench[k]

    def trades(self, sig, exit_cond, kmax=15, limit=None):
        i = np.flatnonzero(sig.fillna(False).to_numpy(bool) & self.liq)
        e = i + 1
        ok = self.same(i, e)
        i, e = i[ok], e[ok]
        px = self.o[e].copy()
        if limit is not None:
            L = limit.to_numpy("float64")[i] * (self.c[i] / self.t.close.to_numpy("float64")[i])  # to adj scale
            fill = self.lo[e] <= L
            i, e, px = i[fill], e[fill], np.minimum(self.o[e[fill]], L[fill])
        ec = exit_cond.fillna(False).to_numpy(bool)
        xb = np.full(len(i), -1)          # exit bar (exit at its OPEN)
        last = np.full(len(i), -1)        # last valid bar seen (for names that end)
        alive = np.ones(len(i), bool)
        for s in range(kmax):
            j = e + s
            ok = self.same(i, j) & alive
            last[ok] = j[ok]
            hit = ok & ec[np.minimum(j, self.n - 1)]
            nx = j + 1
            hit_ok = hit & self.same(i, nx)
            xb[hit_ok] = nx[hit_ok]
            alive &= ~hit & ok
        # cap: exit at the open after the kmax-th bar; ended names: last close
        cap = alive & self.same(i, e + kmax)
        xb[cap] = (e + kmax)[cap]
        r = np.full(len(i), np.nan)
        m = xb >= 0
        r[m] = self.o[xb[m]] / px[m] - 1
        endm = ~m & (last >= 0)
        r[endm] = self.c[last[endm]] / px[endm] - 1
        k = np.where(m, xb - e, np.maximum(last - e + 1, 1))
        b = np.array([self.bench_k(int(kk)).get(d, np.nan) for kk, d in zip(k, self.date[i])])
        return pd.DataFrame({"date": self.date[i], "k": k, "x": r - b}, index=i).dropna()


def stats(tr, lo, hi, kmax=15):
    s = tr[(tr.date >= pd.Timestamp(lo)) & (tr.date <= pd.Timestamp(hi))]
    x = s.x - COST
    d = x.groupby(s.date).mean()
    mid = pd.Timestamp(lo) + (pd.Timestamp(hi) - pd.Timestamp(lo)) / 2
    r = dict(n=len(x), net=x.mean() * 1e4, med=x.median() * 1e4, t=w.nw_t(d, kmax), k=s.k.mean(),
             h=(d[d.index < mid].mean() * 1e4, d[d.index >= mid].mean() * 1e4),
             ex5=d.sort_values().iloc[:-5].mean() * 1e4 if len(d) > 10 else np.nan)
    r["ok"] = r["net"] >= 25 and r["t"] >= 3 and min(r["h"]) > 0 and r["med"] > 0 and r["ex5"] > 0
    return r


def fmt(lab, s):
    return (f"  {lab:46} n {s['n']:7} hold {s['k']:4.1f} net {s['net']:+6.1f} med {s['med']:+6.1f} t {s['t']:+5.2f} "
            f"halves {s['h'][0]:+6.1f}/{s['h'][1]:+6.1f} ex5 {s['ex5']:+6.1f} -> {'PASS' if s['ok'] else 'fail'}")


# ---------------------------------------------------------------- rules: return list of (label, trades) + verdict fn
def rsi_n(t, n):
    c = t.closeadj.astype("float64")
    d = c - w.lag(t, c)
    au = d.clip(lower=0).groupby(t.ticker, sort=False).transform(lambda x: x.ewm(alpha=1 / n, adjust=False).mean())
    ad = (-d).clip(lower=0).groupby(t.ticker, sort=False).transform(lambda x: x.ewm(alpha=1 / n, adjust=False).mean())
    return 100 - 100 / (1 + au / ad.replace(0, np.nan))


def U1(t, E):
    sig = (t.close > F.sma(t, t.close, 100)) & (rsi_n(t, 2) < 10)
    ex = t.closeadj > w.lag(t, t.closeadj)
    atr = F.sma(t, F.true_range(t), 10)
    n_sig = int((sig & t.liq).sum())
    lim = E.trades(sig, ex, limit=t.close - atr)
    mkt = E.trades(sig, ex)
    return [("U1 Radge LIMIT close-ATR10 (gated)", lim), ("U1 same signal, market open t+1", mkt)], \
        f"  signals {n_sig}, limit fills {len(lim)}"


def U2(t, E):
    m20, sd = F.sma(t, t.close, 20), F.std(t, t.close, 20)
    atr = F.sma(t, F.true_range(t), 20)
    sq = (2 * sd) < (1.5 * atr)
    mid = (F.rmax(t, t.high, 20) + F.rmin(t, t.low, 20)) / 2
    mom = F.linreg_end(t, t.close - (mid + m20) / 2, 20)
    dur = w.lag(t, w.run_count(t, sq))
    fire = (dur >= 2) & ~sq & (mom > 0)
    ex = mom < w.lag(t, mom)
    out = []
    for lab, a, b in (("2-3", 2, 3), ("4-8", 4, 8), ("9-20", 9, 20), (">20", 21, 10**6)):
        out.append((f"U2 squeeze {lab} bars, fires hist>0", E.trades(fire & (dur >= a) & (dur <= b), ex)))
    return out, ""


def U3(t, E):
    lo, hi = F.rmin(t, t.low, 10), F.rmax(t, t.high, 10)
    k = F.sma(t, 100 * (t.close - lo) / (hi - lo).replace(0, np.nan), 3)
    c = t.close.astype("float64")
    macd = w.ema(t, c, 12) - w.ema(t, c, 26)
    z = (macd - w.roll(t, macd, 1000, "mean")) / w.roll(t, macd, 1000, "std")
    _, pdi, mdi = F.adx(t)
    sell = (k < 20) & (z < -1) & (pdi < 15)
    buy = (k > 80) & (z > 1) & (mdi < 15)
    sig = w.lag(t, sell).fillna(False).astype(bool) & ~sell.fillna(False)
    return [("U3 seller exhaustion ENDS", E.trades(sig, buy))], f"  exhaustion-state bars {int((sell & t.liq).sum())}"


def U4(t, E):
    c = t.close.astype("float64")
    lo, hi = F.rmin(t, t.low, 5), F.rmax(t, t.high, 5)
    v1 = 0.1 * (100 * (t.close - lo) / (hi - lo).replace(0, np.nan) - 50)
    wts = np.arange(1, 10, dtype="float64")
    v2 = v1.astype("float64").groupby(t.ticker, sort=False).transform(
        lambda x: x.rolling(9, min_periods=9).apply(lambda a: a @ wts / wts.sum(), raw=True))
    ift = (np.tanh(v2) + 1) * 50
    e21 = w.ema(t, c, 21)
    adr = F.sma(t, t.high / t.low - 1, 20)
    near = np.minimum(t.low, w.lag(t, t.low)) <= e21 * 1.01
    sig = (c > F.sma(t, c, 200)) & (c > e21) & near & (adr >= 0.05) & (w.lag(t, ift) <= 10) & (ift >= 90)
    return [("U4 Stoch-IFT 21EMA pullback", E.trades(sig, ift < 50))], ""


def U5(t, E):
    r30 = t.closeadj / w.lag(t, t.closeadj, 30) - 1
    r10 = t.closeadj / w.lag(t, t.closeadj, 10) - 1
    spy = t.ticker == "SPY"
    if spy.sum() == 0:  # SPY is an ETF: take it from the ETF panel
        e = w.load_panel(kind="etf")
        e = e[e.ticker == "SPY"].set_index("date").closeadj
        s30 = t.date.map(e / e.shift(30) - 1)
    else:
        s30 = t.date.map(r30[spy].groupby(t.date[spy]).first())
    sig = (r30 > s30) & (r10 <= -0.01) & (t.closeadj.notna()) & (t.closeunadj >= 50)
    ex = t.closeadj > w.lag(t, t.closeadj, 10)
    return [("U5 RS > SPY 30d, pullback <= -1% 10d", E.trades(sig, ex, kmax=14))], ""


def U6(t, E):
    tr = F.true_range(t)
    wrd = tr / w.lag(t, F.sma(t, tr, 10)) > 1.6
    # the range is complete on bar d+2: mark it there, live from d+3 for 8 bars
    mark = w.lag(t, wrd, 2).fillna(False).astype(bool)
    rh = F.rmax(t, t.high, 4).where(mark)
    rl = F.rmin(t, t.low, 4).where(mark)
    ff = lambda s: w.lag(t, s).groupby(t.ticker, sort=False).ffill(limit=7)
    rh, rl = ff(rh), ff(rl)
    sig = (t.close > rh) & (w.lag(t, t.close) <= w.lag(t, rh))
    return [("U6 WRD range breakout", E.trades(sig, t.close < rl))], ""


def U7(t, E):
    e = w.load_panel(kind="etf")
    e = e[e.ticker == "SPY"].set_index("date").closeadj
    up = t.date.map(e > e.rolling(50).mean()).fillna(False).astype(bool)
    r = t.closeadj / w.lag(t, t.closeadj) - 1
    rng = w.lag(t, (F.rmax(t, t.high, 10) - F.rmin(t, t.low, 10)) / t.close)
    sig = (r >= 0.04) & (t.close >= F.rmax(t, t.close, 20)) & (t.volume > w.lag(t, t.volume)) & (rng <= 0.15) & up
    return [("U7 Stockbee 4% burst", E.trades(sig, r < 0, kmax=5))], ""


def vwma(t, n):
    pv = (t.close * t.volume).astype("float64")
    return F.sma(t, pv, n) / F.sma(t, t.volume.astype("float64"), n)


def U8(t, E):
    v8, v21, v34 = vwma(t, 8), vwma(t, 21), vwma(t, 34)
    stack = (v8 > v21) & (v21 > v34)
    accum = ~stack & (t.close >= v34)
    sig = stack & ~w.lag(t, stack).fillna(False).astype(bool) & w.lag(t, accum).fillna(False).astype(bool)
    return [("U8 Market Pulse accumulation -> acceleration", E.trades(sig, ~stack))], ""


def U9(t, E):
    c = t.close.astype("float64")
    e13 = w.ema(t, c, 13)
    macd = w.ema(t, c, 12) - w.ema(t, c, 26)
    h = macd - w.ema(t, macd, 9)
    green = (e13 > w.lag(t, e13)) & (h > w.lag(t, h))
    red = (e13 < w.lag(t, e13)) & (h < w.lag(t, h))
    sig = green & (w.lag(t, w.run_count(t, red)) >= 3)
    return [("U9 Elder first green after >=3 red", E.trades(sig, red))], ""


def U10(t, E):
    mid = lambda n: (F.rmax(t, t.high, n) + F.rmin(t, t.low, n)) / 2
    tk, kj = mid(9), mid(26)
    sa, sb = w.lag(t, (tk + kj) / 2, 26), w.lag(t, mid(52), 26)
    up = (tk > kj) & (w.lag(t, tk) <= w.lag(t, kj))
    sig = up & (t.low > np.maximum(sa, sb))
    dn = (tk < kj) & (w.lag(t, tk) >= w.lag(t, kj))
    return [("U10 Ichimoku TK cross above cloud", E.trades(sig, dn))], ""


def U11(t, E):
    sig = t.close > w.lag(t, F.rmax(t, t.high, 20))
    ex = t.close < w.lag(t, F.rmin(t, t.low, 10))
    return [("U11 Turtle 20/10", E.trades(sig, ex))], ""


RULES = {"U1": U1, "U2": U2, "U3": U3, "U4": U4, "U5": U5, "U6": U6, "U7": U7, "U8": U8, "U9": U9, "U10": U10, "U11": U11}


def verdict(name, S):
    if name == "U2":
        a, b, c, d = S
        return b["ok"] and b["net"] - a["net"] >= 15 and b["net"] - d["net"] >= 15
    return S[0]["ok"]


def main(argv):
    name = argv[0]
    t = w.load_panel(kind="stock")
    E = Eng(t)
    arms, note = RULES[name](t, E)
    S = [stats(tr, *w.DISC) for _, tr in arms]
    ok = verdict(name, S)
    lines = [f"{name} [uts, 2016-26 discovery, 10bp RT, exit at next open]"] + [fmt(l, s) for (l, _), s in zip(arms, S)]
    if note:
        lines.append(note)
    lines.append(f"  -> {name} {'PASS' if ok else 'KILL'}")
    if ok and "--confirm" in argv:
        S2 = [stats(tr, *w.CONF) for _, tr in arms]
        lines += [f"{name} [CONFIRM 2003-15, one look]"] + [fmt(l, s) for (l, _), s in zip(arms, S2)]
        lines.append(f"  -> confirm {'PASS' if verdict(name, S2) else 'KILL'}")
    txt = "\n".join(lines)
    print(txt)
    with open(OUT, "a") as fh:
        fh.write(f"# {name} {pd.Timestamp.now():%Y-%m-%d %H:%M}\n{txt}\n\n")


if __name__ == "__main__":
    main(sys.argv[1:])
