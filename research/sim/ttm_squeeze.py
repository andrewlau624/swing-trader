"""TTM Squeeze diagnostic (no N): does the YouTube TTM Squeeze rule time the market or a stock?

Claim tested (video, Thinkorswim): long while the TTM Squeeze histogram is above zero, flat
below; length 100 beats the default 20; red->green zero-line ("squeeze fires") entries are a
promising variant. The video tuned on SPY + the Magnificent 7 + one ticker with no costs.

Not a pre-registered study: it replicates the video's rules on data the video never saw and
checks them against two classes this repo already killed (vol-compression -> direction, Study
PB N 826; ETF trend/TSMOM sleeve, add. 26b). No tuning; the parameters are the video's.

Indicator (ToS TTM_Squeeze): hist = Inertia(close - ((HH(n)+LL(n))/2 + EMA(close,n))/2, n),
Inertia = the n-bar linear-regression value at the last bar. Squeeze on (red dot) when
nBB*stdev(close,n) < nK*ATR(n) (BB inside KC). Signals at close d, trades at open d+1.

Data: Sharadar SFP (13 index/sector ETFs, 1999+) and SEP (random 1200 common stocks incl.
delisted, seed 0); total-return adjusted (closeadj/close factor). Delisting returns are not
added (the last bar is the exit), which flatters a long rule on dying names. Costs 5bp/side.
Daily bars are regular-hours official open/close.

Run: PYTHONPATH=. .venv/bin/python -m research.sim.ttm_squeeze > data/research/program/ttm_squeeze_out.txt
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from sharadar import prices, tickers

ETFS = ["SPY", "QQQ", "IWM", "DIA", "XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLI", "XLU", "XLB"]
COST = 5e-4
RNG = np.random.default_rng(0)


def load(tks, source):
    df = prices(tks, adjust="split", source=source)
    f = df["closeadj"] / df["close"]
    for c in ("open", "high", "low", "close"):
        df[c] = df[c] * f
    df["dv"] = df["closeunadj"] * df["volume"]
    df["date"] = pd.to_datetime(df["date"])
    return {t: g.set_index("date").sort_index() for t, g in df.groupby("ticker")}


def linreg_last(x: pd.Series, n: int) -> pd.Series:
    # value of the OLS line at the last bar of each n-window
    t = np.arange(n, dtype=float)
    tc = t - t.mean()
    w = (tc * (n - 1 - t.mean()) / (tc @ tc) + 1.0 / n)  # weights giving fitted value at t=n-1
    v = x.values.astype(float)
    out = np.full(len(v), np.nan)
    if len(v) >= n:
        out[n - 1:] = np.convolve(v, w[::-1], mode="valid")
    return pd.Series(out, index=x.index)


def ttm(d: pd.DataFrame, n: int, nk: float = 1.5, nbb: float = 2.0) -> pd.DataFrame:
    c, h, l = d["close"], d["high"], d["low"]
    mid = ((h.rolling(n).max() + l.rolling(n).min()) / 2 + c.ewm(span=n, adjust=False).mean()) / 2
    hist = linreg_last(c - mid, n)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    sq = nbb * c.rolling(n).std() < nk * tr.rolling(n).mean()
    return pd.DataFrame({"hist": hist, "sq": sq})


def trades(d, pos):
    """pos: 0/1 Series decided at close d; held open(d+1)->open(exit+1). Returns list of trade dicts."""
    o = d["open"].values
    p = pos.fillna(0).astype(int).values
    out, i, N = [], 0, len(p)
    while i < N - 1:
        if p[i] == 1 and (i == 0 or p[i - 1] == 0):
            j = i
            while j < N - 1 and p[j] == 1:
                j += 1
            ent, ex = i + 1, min(j + 1, N - 1)
            if ex > ent:
                out.append({"date": d.index[ent], "ret": o[ex] / o[ent] - 1, "days": ex - ent,
                            "drift": (o[-1] / o[0]) ** (1 / max(N - 1, 1)) - 1})
            i = j
        i += 1
    return out


def equity(d, pos):
    """daily open-to-open strategy returns (position decided at close d earns open(d+1)->open(d+2))."""
    r = d["open"].pct_change().shift(-1)  # open(d)->open(d+1), indexed d
    held = pos.fillna(0).shift(1)  # decided at close d-1, held over open(d)->open(d+1)
    turn = held.diff().abs().fillna(0)
    return (held * r - turn * COST).fillna(0), r.fillna(0)


def stats(r: pd.Series):
    eq = (1 + r).cumprod()
    yrs = len(r) / 252
    cagr = eq.iloc[-1] ** (1 / yrs) - 1 if yrs > 0 else np.nan
    dd = (eq / eq.cummax() - 1).min()
    sh = r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else np.nan
    return cagr, dd, sh


def tstats(x):
    x = np.asarray(x)
    return x.mean(), np.median(x), (x > 0).mean(), x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 else np.nan


RULES = {
    "zero20": lambda d: ttm(d, 20)["hist"] > 0,
    "zero100": lambda d: ttm(d, 100)["hist"] > 0,
    "sma100": lambda d: d["close"] > d["close"].rolling(100).mean(),  # plain trend filter, for comparison
}


def fire_pos(d, n, nk, min_dur):
    """video variant: enter when the squeeze turns off (red->green) after >= min_dur red bars with
    hist > 0 and rising; exit when hist crosses below zero."""
    t = ttm(d, n, nk)
    sq = t["sq"].values
    h = t["hist"].values
    dur = np.zeros(len(sq), int)
    for i in range(1, len(sq)):
        dur[i] = dur[i - 1] + 1 if sq[i] else 0
    pos = np.zeros(len(sq))
    on = False
    for i in range(1, len(sq)):
        if not on and sq[i - 1] and not sq[i] and dur[i - 1] >= min_dur and h[i] > 0 and h[i] > h[i - 1]:
            on = True
        elif on and h[i] < 0:
            on = False
        pos[i] = on
    return pd.Series(pos, index=d.index)


def section_etfs(px, start, end):
    print(f"\n## ETFs {start}..{end}: strategy vs buy-and-hold (open-to-open, 5bp/side)")
    print(f"{'tk':5s} {'rule':10s} {'CAGR':>7s} {'maxDD':>7s} {'Sharpe':>6s} {'expo':>5s} | {'B&H CAGR':>8s} {'maxDD':>7s} {'Sh':>5s}")
    agg = {}
    for tk in ETFS:
        d = px[tk]
        rules = dict(RULES)
        rules["fire20"] = lambda d: fire_pos(d, 20, 1.5, 5)
        rules["fire100k5"] = lambda d: fire_pos(d, 100, 5.0, 5)
        for name, f in rules.items():
            pos = f(d).astype(float)
            s, bh = equity(d, pos)
            m = (s.index >= pd.Timestamp(start)) & (s.index <= pd.Timestamp(end))
            c, dd, sh = stats(s[m])
            bc, bdd, bsh = stats(bh[m])
            expo = pos.shift(1)[m].mean()
            agg.setdefault(name, []).append((c - bc, sh - bsh, dd - bdd, expo))
            if tk in ("SPY", "QQQ", "IWM"):
                print(f"{tk:5s} {name:10s} {c:7.1%} {dd:7.1%} {sh:6.2f} {expo:5.2f} | {bc:8.1%} {bdd:7.1%} {bsh:5.2f}")
    print("mean over 13 ETFs: CAGR - B&H | Sharpe - B&H | maxDD - B&H (positive = shallower) | exposure | #ETFs beating B&H CAGR")
    for name, v in agg.items():
        a = np.array(v)
        print(f"  {name:10s} {a[:,0].mean():+7.1%} {a[:,1].mean():+6.2f} {a[:,2].mean():+7.1%} {a[:,3].mean():5.2f}  {(a[:,0]>0).sum():2d}/13")


def exposure_placebo(px, rule, start, end, draws=200):
    """timing skill = strategy in-market mean daily ret minus the same exposure placed at random
    (circular shift of the position series per ETF)."""
    real, plac = [], []
    for tk in ETFS:
        d = px[tk]
        pos = rule(d).astype(float).fillna(0)
        r = d["open"].pct_change().shift(-1)
        m = (d.index >= pd.Timestamp(start)) & (d.index <= pd.Timestamp(end))
        held = pos.shift(1)
        real.append((held * r)[m].mean())
        n = len(pos)
        sh = [(pd.Series(np.roll(pos.values, RNG.integers(100, n - 100)), index=pos.index).shift(1) * r)[m].mean()
              for _ in range(draws)]
        plac.append(sh)
    real = np.mean(real)
    plac = np.mean(np.array(plac), axis=0)
    return real, (plac < real).mean()


def section_stocks(sp, start, end):
    print(f"\n## Stocks (random 1200 incl. delisted; signal needs price>$5, 20d $ADV>$10M) {start}..{end}")
    print("per-trade, 5bp/side; 'excess' = trade ret - the stock's own full-sample drift x days held")
    res = {k: [] for k in ("zero20", "zero100", "fire20", "fire100k5")}
    for tk, d in sp.items():
        if len(d) < 300:
            continue
        ok = (d["closeunadj"] > 5) & (d["dv"].rolling(20).mean() > 1e7)
        rules = {"zero20": RULES["zero20"], "zero100": RULES["zero100"],
                 "fire20": lambda d: fire_pos(d, 20, 1.5, 5), "fire100k5": lambda d: fire_pos(d, 100, 5.0, 5)}
        for name, f in rules.items():
            pos = f(d).astype(bool)
            # entries only when tradable; once in, hold to the rule's exit
            ent = pos & ~pos.shift(1, fill_value=False)
            pos2 = pos.copy()
            block = ent & ~ok
            # drop whole trades whose entry bar is untradable
            tid = ent.cumsum()
            bad = tid[block].unique()
            pos2[tid.isin(bad) & pos] = False
            for t in trades(d, pos2):
                if start <= t["date"] <= end:
                    t["ret"] -= 2 * COST
                    t["ex"] = t["ret"] - ((1 + t["drift"]) ** t["days"] - 1)
                    res[name].append(t)
    for name, v in res.items():
        if not v:
            continue
        df = pd.DataFrame(v)
        mn, md, hit, t = tstats(df["ret"])
        emn, emd, ehit, et = tstats(df["ex"])
        top5 = df["ret"].nlargest(5).index
        ex5 = df["ret"].drop(top5).mean()
        yr = df.groupby(df["date"].dt.year)["ex"].mean()
        print(f"  {name:10s} n {len(df):6d} days {df['days'].median():4.0f} | ret mean {mn:+.2%} med {md:+.2%} hit {hit:.0%} "
              f"ex-top5 {ex5:+.2%} | excess mean {emn:+.2%} med {emd:+.2%} t {et:+.2f} | years excess>0 {(yr>0).sum()}/{len(yr)}")


def section_fire_events(px, sp):
    """lesson L1: test the pattern traders read (squeeze duration, fire direction) at natural horizons.
    Event = squeeze turns off (red->green), len 20 / nK 1.5. Forward open(d+1)->open(d+1+h)."""
    print("\n## Squeeze-fire events (len20, nK1.5): forward return by squeeze duration and histogram sign at fire")
    print("   up/down tails = P(fwd20 >= +10%) / P(fwd20 <= -10%); 'all days' = the same names, every day")
    rows, base = [], []
    for tk, d in list(sp.items()) + [(k, px[k]) for k in ETFS]:
        if len(d) < 300:
            continue
        t = ttm(d, 20)
        sq = t["sq"].values
        dur = np.zeros(len(sq), int)
        for i in range(1, len(sq)):
            dur[i] = dur[i - 1] + 1 if sq[i] else 0
        o = d["open"].values
        ok = ((d["closeunadj"] > 5) & (d["dv"].rolling(20).mean() > 1e7)).values
        for h in (5, 20):
            f = np.full(len(o), np.nan)
            f[: len(o) - 1 - h] = o[1 + h:] / o[1: len(o) - h] - 1
            if h == 5:
                f5 = f
            else:
                f20 = f
        b = f20[ok & ~np.isnan(f20)]
        base.append(b[:: 5])
        for i in range(1, len(sq)):
            if sq[i - 1] and not sq[i] and ok[i] and not np.isnan(f20[i]):
                rows.append((dur[i - 1], np.sign(t["hist"].values[i]), f5[i], f20[i], d.index[i].year))
    ev = pd.DataFrame(rows, columns=["dur", "sgn", "f5", "f20", "yr"])
    b = np.concatenate(base)
    print(f"  all days      n {len(b):7d} fwd20 mean {b.mean():+.2%} med {np.median(b):+.2%} up {np.mean(b>=.1):.1%} dn {np.mean(b<=-.1):.1%}")
    ev["db"] = pd.cut(ev["dur"], [0, 4, 9, 19, 10_000], labels=["1-4", "5-9", "10-19", "20+"])
    for (db, s), g in ev.groupby(["db", "sgn"], observed=True):
        if s == 0 or len(g) < 30:
            continue
        print(f"  dur {db:>5s} hist{'+' if s>0 else '-'} n {len(g):6d} fwd5 {g.f5.mean():+.2%} fwd20 mean {g.f20.mean():+.2%} "
              f"med {g.f20.median():+.2%} up {np.mean(g.f20>=.1):.1%} dn {np.mean(g.f20<=-.1):.1%}")


def main():
    px = load(ETFS, "funds")
    t = tickers()
    t = t[(t["table"] == "SEP") & (t["category"].str.startswith("Domestic Common Stock", na=False))]
    t = t[pd.to_datetime(t["lastpricedate"]) >= "2001-01-01"]
    pick = RNG.choice(t["ticker"].unique(), 1200, replace=False)
    sp = load(list(pick), None)
    print(f"stocks loaded: {len(sp)} (delisted {t.set_index('ticker').loc[list(sp)].isdelisted.eq('Y').sum()})")
    for s, e in (("1999-06-01", "2015-12-31"), ("2016-01-01", "2026-10-05")):
        section_etfs(px, s, e)
        print("  exposure-matched placebo (random circular shift, 200 draws), mean daily in-market ret over 13 ETFs:")
        for name in ("zero20", "zero100", "sma100"):
            real, pct = exposure_placebo(px, RULES[name], s, e)
            print(f"    {name:8s} {real*1e4:+.2f}bp/day  placebo pct {pct:.0%}")
        section_stocks(sp, pd.Timestamp(s), pd.Timestamp(e))
    section_fire_events(px, sp)


if __name__ == "__main__":
    main()
