"""Window combos (2026-10-08 /loop, after the user's correction): A and B are WINDOW patterns (duration, sequence,
alignment of B inside A's window), and every arm exits at its indicator's NATURAL exit, not a fixed day 5.

Trade: signal on close t, buy open t+1, sell the close of the first bar j >= t+1 where the arm's exit condition is
true (cap kmax bars; a name that ends first exits at its last bar). Excess = trade total return minus the EW liquid
universe's open t+1 -> close t+k return for the SAME k (exact horizon match). Close-of-exit-bar is a daily-close
proxy for an MOC exit, identical for every arm. Gate = COMBO LOOP gate in window_signals_loop_2026-10-07.md.
Usage: python -m research.sim.combo_win W1 [--confirm]
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from research.sim import winsig as w, winsig_fam as F

OUT = w.CACHE.parent / "program" / "combo_out.txt"
KMAX = 15


class Panel:
    """Arrays for exit search and exact-horizon EW benchmarks (cached per k)."""

    def __init__(self, t, uni="liq"):
        self.t, self.uni = t, uni
        self.code = t.ticker.astype("category").cat.codes.to_numpy()
        self.n = len(t)
        adjf = (t.closeadj / t.close).to_numpy("float64")
        o = t.open.to_numpy("float64") * adjf
        self.cadj = t.closeadj.to_numpy("float64")
        nxt = np.arange(self.n) + 1
        ok = (nxt < self.n)
        ok[ok] = self.code[nxt[ok]] == self.code[ok.nonzero()[0]]
        self.entry = np.full(self.n, np.nan)
        self.entry[ok] = o[nxt[ok]]
        self.bench = {}

    def fk(self, k):
        j = np.arange(self.n) + k
        ok = j < self.n
        ok[ok] = self.code[j[ok]] == self.code[ok.nonzero()[0]]
        f = np.full(self.n, np.nan)
        f[ok] = self.cadj[j[ok]] / self.entry[ok] - 1
        return f

    def bench_k(self, k):
        if k not in self.bench:
            f = pd.Series(self.fk(k), index=self.t.index)
            m = self.t[self.uni]
            self.bench[k] = f[m].groupby(self.t.date[m]).mean()
        return self.bench[k]

    def trades(self, sig, exit_cond, kmax=KMAX):
        """Per signal row: holding k (bars) and excess vs the EW universe over the same open t+1 -> close t+k."""
        idx = np.flatnonzero(sig.fillna(False).to_numpy(bool) & self.t[self.uni].to_numpy(bool))
        ec = exit_cond.fillna(False).to_numpy(bool)
        k = np.zeros(len(idx), int)
        alive = np.ones(len(idx), bool)
        for s in range(1, kmax + 1):
            j = idx + s
            same = (j < self.n)
            same[same] = self.code[j[same]] == self.code[idx[same]]
            ended = alive & ~same
            k[ended] = s - 1           # name ended: exit at its last bar (0 = no next bar, dropped)
            alive &= same
            hit = alive & ec[np.minimum(j, self.n - 1)]
            k[hit] = s
            alive &= ~hit
        k[alive] = kmax
        keep = k >= 1
        idx, k = idx[keep], k[keep]
        r = self.cadj[idx + k] / self.entry[idx] - 1
        dates = self.t.date.to_numpy()[idx]
        b = np.array([self.bench_k(kk).get(pd.Timestamp(d), np.nan) for kk, d in zip(k, dates)])
        out = pd.DataFrame({"date": dates, "k": k, "x": r - b}, index=idx).dropna()
        return out


def stats(tr, lo, hi, cost):
    s = tr[(tr.date >= pd.Timestamp(lo)) & (tr.date <= pd.Timestamp(hi))]
    x = s.x - cost
    d = x.groupby(s.date).mean()
    mid = pd.Timestamp(lo) + (pd.Timestamp(hi) - pd.Timestamp(lo)) / 2
    return dict(n=len(x), net=x.mean() * 1e4, med=x.median() * 1e4, t=w.nw_t(d, KMAX), k=s.k.mean(),
                perday=(x / s.k).mean() * 1e4,
                h=(d[d.index < mid].mean() * 1e4, d[d.index >= mid].mean() * 1e4),
                ex5=d.sort_values().iloc[:-5].mean() * 1e4 if len(d) > 10 else np.nan)


def paired(c, rest, lo, hi):
    f = lambda s: s[(s.date >= pd.Timestamp(lo)) & (s.date <= pd.Timestamp(hi))].groupby("date").x.mean()
    a, b = f(c), f(rest)
    j = a.index.intersection(b.index)
    d = a[j] - b[j]
    return dict(n=len(d), mean=d.mean() * 1e4, t=w.nw_t(d, KMAX))


def judge(P, arms, lo, hi, cost):
    """arms = dict(A=(sig, exit, label), B=(...), C=(sig, exit, label)); diagnostics D* printed, not gated."""
    tr = {k: P.trades(s, e) for k, (s, e, _) in arms.items()}
    S = {k: stats(v, lo, hi, cost) for k, v in tr.items()}
    best = "A" if S["A"]["net"] >= S["B"]["net"] else "B"
    other = "B" if best == "A" else "A"
    # better single's trades that are NOT combo entries (same entry rows excluded)
    rest = tr[best][~tr[best].index.isin(tr["C"].index)]
    p = paired(tr["C"], rest, lo, hi)
    sc, sb = S["C"], S[best]
    imp, imp_h = sc["net"] - sb["net"], (sc["h"][0] - sb["h"][0], sc["h"][1] - sb["h"][1])
    ok = (imp >= 15 and p["t"] >= 3 and sc["t"] >= 3 and min(sc["h"]) > 0 and sc["med"] > 0
          and sc["ex5"] > 0 and min(imp_h) > 0)
    f = lambda k: (f"  {arms[k][2]:52} n {S[k]['n']:7} hold {S[k]['k']:4.1f} net {S[k]['net']:+6.1f} "
                   f"({S[k]['perday']:+5.1f}/day) med {S[k]['med']:+6.1f} t {S[k]['t']:+5.2f} "
                   f"halves {S[k]['h'][0]:+6.1f}/{S[k]['h'][1]:+6.1f} ex5 {S[k]['ex5']:+6.1f}")
    lines = [f(k) for k in arms]
    lines.append(f"  improvement vs better single ({best}) {imp:+.1f}bp (halves {imp_h[0]:+.1f}/{imp_h[1]:+.1f}); "
                 f"date-paired combo - {best}-only {p['mean']:+.1f}bp t {p['t']:+.2f} (n dates {p['n']}) "
                 f"-> {'PASS' if ok else 'KILL'}")
    return ok, "\n".join(lines)


# ---------------------------------------------------------------- indicators
def ibs(t):
    return (t.close - t.low) / (t.high - t.low).replace(0, np.nan)


def ttm(t):
    """Squeeze-on flag and the TTM momentum histogram (as F1)."""
    m20, sd = F.sma(t, t.close, 20), F.std(t, t.close, 20)
    atr = F.sma(t, F.true_range(t), 20)
    sq = (2 * sd) < (1.5 * atr)
    mid = (F.rmax(t, t.high, 20) + F.rmin(t, t.low, 20)) / 2
    mom = F.linreg_end(t, t.close - (mid + m20) / 2, 20)
    return sq, mom


def W1(t):
    """TTM squeeze fire read as a window x a selling window in IBS (stocks)."""
    sq, mom = ttm(t)
    mp = w.lag(t, mom)
    rising, falling = mom > mp, mom < mp
    dur = w.lag(t, w.run_count(t, sq))                       # squeeze duration ending t-1
    fall_run = w.lag(t, w.run_count(t, falling))             # dark-red bars before today
    # A: squeeze held >= 6 bars, fires today, histogram < 0 and turns light red after >= 3 dark red bars
    a = (dur >= 6) & ~sq & (mom < 0) & rising & (fall_run >= 3)
    a_exit = falling                                          # natural exit: first bar the histogram stops rising
    # B: selling window - >= 3 of the last 5 closes with IBS < 0.25, today included
    low = (ibs(t) < 0.25).astype("float64")
    b = F.sma(t, low, 5) >= 0.6
    b_exit = ibs(t) > 0.5                                     # natural exit: first close in the top half of range
    c = a & b
    return {"A": (a, a_exit, "A squeeze>=6 fires, hist<0 dark->light red (exit: hist falls)"),
            "B": (b, b_exit, "B >=3 of last 5 closes IBS<0.25 (exit: IBS>0.5)"),
            "C": (c, a_exit, "COMBO A inside B's selling window (A's exit)"),
            "D1": (b, a_exit, "diag: B with A's exit"),
            "D2": (a, b_exit, "diag: A with B's exit")}


def W2(t):
    """TMO turn after >= 5 bars oversold x >= 2 days <= -8% in the last 10 bars (stocks)."""
    main, sig = F.tmo(t)
    a = (w.lag(t, w.run_count(t, main <= -10)) >= 5) & (main > sig) & (w.lag(t, main) <= w.lag(t, sig))
    a_exit = main < sig
    r = t.closeadj / w.lag(t, t.closeadj) - 1
    b = w.roll(t, (r <= -0.08).astype("float64"), 10, "sum") >= 2
    b_exit = r > 0
    return {"A": (a, a_exit, "A TMO>=5 bars <=-10 then cross-up (exit: cross down)"),
            "B": (b, b_exit, "B >=2 days <=-8% in last 10 (exit: first up close)"),
            "C": (a & b, a_exit, "COMBO A during B's episode (A's exit)"),
            "D1": (b, a_exit, "diag: B with A's exit"),
            "D2": (a, b_exit, "diag: A with B's exit")}


def W3(t):
    """Ex-date on bars t+5..t+10 (exit at the ex-date) x >= 4 of the last 5 closes down (prefs + baby bonds)."""
    from research.sim.combo import pre_ex
    a, a_exit = pre_ex(t, 5, 10), pre_ex(t, 0, 0)
    r = t.closeadj / w.lag(t, t.closeadj) - 1
    b = w.roll(t, (r < 0).astype("float64"), 5, "sum") >= 4
    b_exit = r > 0
    return {"A": (a, a_exit, "A ex-date in t+5..t+10 (exit: ex-date close)"),
            "B": (b, b_exit, "B >=4 of last 5 closes down (exit: first up close)"),
            "C": (a & b, a_exit, "COMBO selling run inside pre-ex window (A's exit)"),
            "D1": (b, a_exit, "diag: B with A's exit"),
            "D2": (a, b_exit, "diag: A with B's exit")}


def W4(t):
    """IBS selling window (>= 3 of 5 closes IBS<0.25) x >= 60 bars above the 200-bar SMA (ETFs)."""
    a = F.sma(t, (ibs(t) < 0.25).astype("float64"), 5) >= 0.6
    a_exit = ibs(t) > 0.5
    up = t.closeadj > F.sma(t, t.closeadj, 200)
    b, b_exit = w.run_count(t, up) >= 60, ~up
    return {"A": (a, a_exit, "A >=3 of last 5 IBS<0.25 (exit: IBS>0.5)"),
            "B": (b, b_exit, "B >=60 bars above SMA200 (exit: close < SMA200)"),
            "C": (a & b, a_exit, "COMBO selling window in long uptrend (A's exit)"),
            "D1": (b, a_exit, "diag: B with A's exit"),
            "D2": (a, b_exit, "diag: A with B's exit")}


def W5(t):
    """RSI bullish divergence (F6) x a new 252-bar low on bars t-9..t (stocks)."""
    r = F.rsi(t)
    a, a_exit = F.F6(t)["F6 RSI bullish divergence (RSI<40)"], r > 50
    b = F.rmax(t, (t.low <= F.rmin(t, t.low, 252)).astype("float64"), 10) > 0
    b_exit = t.close > F.sma(t, t.close, 20)
    return {"A": (a, a_exit, "A RSI bullish divergence (exit: RSI>50)"),
            "B": (b, b_exit, "B 52w low in last 10 (exit: close > SMA20)"),
            "C": (a & b, a_exit, "COMBO divergence at a fresh 52w low (A's exit)"),
            "D1": (b, a_exit, "diag: B with A's exit"),
            "D2": (a, b_exit, "diag: A with B's exit")}


def W6(t):
    """IBS selling window x the ETF's 5-session return <= SPY's - 3% while SPY's >= 0 (ETFs)."""
    a = F.sma(t, (ibs(t) < 0.25).astype("float64"), 5) >= 0.6
    r5 = t.closeadj / w.lag(t, t.closeadj, 5) - 1
    spy = t.ticker == "SPY"
    s5 = t.date.map(r5[spy].groupby(t.date[spy]).first())
    b, b_exit = (s5 >= 0) & (r5 - s5 <= -0.03), r5 >= s5
    return {"A": (a, ibs(t) > 0.5, "A >=3 of last 5 IBS<0.25 (exit: IBS>0.5)"),
            "B": (b, b_exit, "B 5d lag <= SPY-3%, SPY 5d >= 0 (exit: lag closed)"),
            "C": (a & b, ibs(t) > 0.5, "COMBO selling window in a lagging ETF (A's exit)"),
            "D1": (b, ibs(t) > 0.5, "diag: B with A's exit"),
            "D2": (a, b_exit, "diag: A with B's exit")}


COMBOS = {"W6": ("etf", 10e-4, W6), "W5": ("stock", 10e-4, W5), "W4": ("etf", 10e-4, W4), "W3": ("pref", 8e-4, W3), "W1": ("stock", 10e-4, W1), "W2": ("stock", 10e-4, W2)}


def main(argv):
    name = argv[0]
    kind, cost, fn = COMBOS[name]
    t = w.load_panel(kind=kind)
    P = Panel(t)
    arms = fn(t)
    ok, txt = judge(P, arms, *w.DISC, cost)
    txt = f"{name} [window combo, 2016-26 discovery, cost {cost*1e4:.0f}bp RT, natural exits, kmax {KMAX}]\n{txt}"
    if ok and "--confirm" in argv:
        _, t2 = judge(P, arms, *w.CONF, cost)
        txt += f"\n{name} [CONFIRM 2003-15, one look]\n{t2}"
    print(txt)
    with open(OUT, "a") as fh:
        fh.write(f"# {name} {pd.Timestamp.now():%Y-%m-%d %H:%M}\n{txt}\n\n")


if __name__ == "__main__":
    main(sys.argv[1:])
