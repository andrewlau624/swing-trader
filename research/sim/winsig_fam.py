"""Window-signal families F1..F11 (spec frozen in research/drafts/window_signals_loop_2026-10-07.md).

python -m research.sim.winsig_fam F1 [--confirm]   -> appends to research/sim/winsig_out.txt
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from research.sim import winsig as w

OUT = w.pathlib.Path(__file__).with_name("winsig_out.txt")


def gsum(t, s, n):
    """Rolling n-sum per ticker via cumulative sums (fast, float64)."""
    s = s.astype("float64").fillna(0.0)
    cs = s.groupby(t.ticker, sort=False).cumsum()
    prev = cs.groupby(t.ticker, sort=False).shift(n)
    out = cs - prev.fillna(0.0)
    pos = t.groupby("ticker", sort=False).cumcount()
    return out.where(pos >= n - 1)


def sma(t, s, n):
    return gsum(t, s, n) / n


def std(t, s, n):
    m = sma(t, s, n)
    return np.sqrt((gsum(t, s.astype("float64") ** 2, n) / n - m ** 2).clip(lower=0))


def linreg_end(t, y, n):
    """Endpoint of the n-bar least-squares line through y (TTM momentum)."""
    pos = t.groupby("ticker", sort=False).cumcount().astype("float64")
    sy = gsum(t, y, n); sxy = gsum(t, y * pos, n)
    x0 = pos - (n - 1)
    sx = n * x0 + n * (n - 1) / 2; sxx_c = n * (n * n - 1) / 12
    sxy_c = sxy - x0 * sy - (n - 1) / 2 * sy  # sum((x - xbar) y) with x relative to window start
    b = sxy_c / sxx_c
    return sy / n + b * (n - 1) / 2


def true_range(t):
    pc = w.lag(t, t.close)
    return pd.concat([t.high - t.low, (t.high - pc).abs(), (t.low - pc).abs()], axis=1).max(axis=1)


def rmax(t, s, n):
    return w.roll(t, s, n, "max")


def rmin(t, s, n):
    return w.roll(t, s, n, "min")


# ---------------------------------------------------------------- families: return {arm_label: mask}
def F1(t):
    m20, sd = sma(t, t.close, 20), std(t, t.close, 20)
    atr = sma(t, true_range(t), 20)
    sq = (2 * sd) < (1.5 * atr)
    run_prev = w.lag(t, w.run_count(t, sq))
    fired = (run_prev >= 5) & ~sq
    mid = (rmax(t, t.high, 20) + rmin(t, t.low, 20)) / 2
    mom = linreg_end(t, t.close - (mid + m20) / 2, 20)
    mp = w.lag(t, mom)
    return {"F1 squeeze release, hist>0 rising": fired & (mom > 0) & (mom > mp),
            "F1 control: release, hist<0 falling": fired & (mom < 0) & (mom < mp)}


def tmo(t):
    o = t.open.astype("float64"); c = t.close.astype("float64")
    data = sum(np.sign(c - w.lag(t, o, k)) for k in range(14))
    main = w.ema(t, w.ema(t, data, 5), 3)
    return main, w.ema(t, main, 3)


def F2(t):
    main, sig = tmo(t)
    cross = (main > sig) & (w.lag(t, main) <= w.lag(t, sig))
    return {"F2 TMO oversold cross-up": cross & (main <= -10)}


def F3(t):
    c = t.close.astype("float64")
    macd = w.ema(t, c, 12) - w.ema(t, c, 26)
    hist = macd - w.ema(t, macd, 9)
    neg_run = w.lag(t, w.run_count(t, hist < 0))
    return {"F3 MACD hist turns + after >=5 neg, MACD<0": (hist > 0) & (neg_run >= 5) & (macd < 0)}


def F4(t):
    lo, hi = rmin(t, t.low, 14), rmax(t, t.high, 14)
    k = sma(t, 100 * (t.close - lo) / (hi - lo).replace(0, np.nan), 3)
    d = sma(t, k, 3)
    zone = w.lag(t, w.run_count(t, k < 20))
    cross = (k > d) & (w.lag(t, k) <= w.lag(t, d))
    return {"F4 Stoch cross-up <20 after >=3 bars": cross & (k < 20) & (d < 20) & (zone >= 3)}


def F5(t):
    lower = sma(t, t.close, 20) - 2 * std(t, t.close, 20)
    below = t.close < lower
    run_prev = w.lag(t, w.run_count(t, below))
    return {"F5 BB lower re-entry after >=2 closes below": ~below & (run_prev >= 2)}


def rsi(t, n=14):
    d = t.close.astype("float64") - w.lag(t, t.close.astype("float64"))
    up = d.clip(lower=0); dn = (-d).clip(lower=0)
    au = up.groupby(t.ticker, sort=False).transform(lambda x: x.ewm(alpha=1 / n, adjust=False).mean())
    ad = dn.groupby(t.ticker, sort=False).transform(lambda x: x.ewm(alpha=1 / n, adjust=False).mean())
    return 100 - 100 / (1 + au / ad.replace(0, np.nan))


def F6(t):
    r = rsi(t)
    # prior swing low = min low over t-20..t-5; RSI at that bar approximated by min RSI over the same window
    prior_low = w.lag(t, rmin(t, t.low, 16), 5)
    prior_rsi = w.lag(t, rmin(t, r, 16), 5)
    return {"F6 RSI bullish divergence (RSI<40)": (t.low < prior_low) & (r > prior_rsi) & (r < 40)}


def adx(t, n=14):
    up = t.high - w.lag(t, t.high); dn = w.lag(t, t.low) - t.low
    pdm = up.where((up > dn) & (up > 0), 0.0); mdm = dn.where((dn > up) & (dn > 0), 0.0)
    sm = lambda s: s.astype("float64").groupby(t.ticker, sort=False).transform(lambda x: x.ewm(alpha=1 / n, adjust=False).mean())
    atr = sm(true_range(t))
    pdi, mdi = 100 * sm(pdm) / atr, 100 * sm(mdm) / atr
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return sm(dx), pdi, mdi


def F7(t):
    a, pdi, mdi = adx(t)
    e20 = w.ema(t, t.close.astype("float64"), 20)
    below = t.close < e20
    run_prev = w.lag(t, w.run_count(t, below))
    return {"F7 ADX>25 uptrend, reclaim EMA20 after >=3 below": (a > 25) & (pdi > mdi) & ~below & (run_prev >= 3)}


def F8(t):
    rng = t.high - t.low
    nr7 = rng <= rmin(t, rng, 7)
    inside = (t.high <= w.lag(t, t.high)) & (t.low >= w.lag(t, t.low))
    setup = w.lag(t, nr7 & inside)
    return {"F8 NR7 inside day, close > its high": setup & (t.close > w.lag(t, t.high))}


def F9(t):
    d = np.sign(t.close.astype("float64") - w.lag(t, t.close.astype("float64"))).fillna(0)
    obv = (d * t.volume.astype("float64")).groupby(t.ticker, sort=False).cumsum()
    low_close = t.close <= rmin(t, t.close, 20)
    return {"F9 20d low close, OBV above its 20d low": low_close & (obv > rmin(t, obv, 20))}


def F10(t):
    m, sd = sma(t, t.close, 20), std(t, t.close, 20)
    bw = 4 * sd / m
    tight = w.lag(t, bw <= rmin(t, bw, 120))
    return {"F10 BB width 120d low, close > 20d high": tight & (t.close > w.lag(t, rmax(t, t.high, 20)))}


def F11(t):
    """Weekly MACD on Friday closes; signal marked on the week's last bar (enter next open)."""
    wk = t.date.dt.to_period("W-FRI")
    last = wk != wk.groupby(t.ticker, sort=False).shift(-1)
    sub = t.loc[last, ["ticker", "close"]].copy()
    c = sub.close.astype("float64")
    e = lambda s, n: s.groupby(sub.ticker, sort=False).transform(lambda x: x.ewm(span=n, adjust=False).mean())
    macd = e(c, 12) - e(c, 26); hist = macd - e(macd, 9)
    hp = hist.groupby(sub.ticker, sort=False).shift(1)
    cnt = sub.groupby("ticker", sort=False).cumcount()
    sig = (hist > 0) & (hp <= 0) & (macd < 0) & (cnt >= 35)
    out = pd.Series(False, index=t.index); out.loc[sig.index] = sig
    return {"F11 weekly MACD hist turns +, MACD<0": out}


def H1(t):
    dn = t.close < w.lag(t, t.close, 4)
    run = w.run_count(t, dn)
    return {"H1 TD Sequential buy setup 9": run == 9}


def H2(t):
    v50 = w.lag(t, sma(t, t.volume.astype("float64"), 50))
    r3 = t.close / w.lag(t, t.close, 3) - 1
    pos = (t.close - t.low) / (t.high - t.low).replace(0, np.nan)
    return {"H2 selling climax (3d<=-5%, vol>=3x, close top 40%)": (r3 <= -0.05) & (t.volume >= 3 * v50) & (pos >= 0.6)}


def H3(t):
    c = t.close.astype("float64"); up = c > w.lag(t, c)
    dvol = t.volume.astype("float64").where(~up, 0.0)
    mx = w.lag(t, rmax(t, dvol, 10))
    return {"H3 pocket pivot": up & (t.volume > mx) & (c > sma(t, c, 50))}


def H4(t):
    hi_prev = w.lag(t, t.high)
    out = pd.Series(False, index=t.index)
    gu = t.low > hi_prev  # gap up today: today's low above yesterday's high
    for k in range(1, 6):
        # gap down k+1 bars ago -> bar j = t-k is first island bar: high_j < low_{j-1}
        island_start_gap = w.lag(t, t.high, k) < w.lag(t, t.low, k + 1)
        island_hi = w.lag(t, rmax(t, t.high, k), 1)            # max high over the island bars t-k..t-1
        pre_low = w.lag(t, t.low, k + 1)
        unfilled = island_hi < pre_low
        out |= island_start_gap & unfilled & gu & (t.low > island_hi)
    return {"H4 island reversal (1-5 bar island)": out}


def H5(t):
    o, c, h, l = (t[k].astype("float64") for k in ("open", "close", "high", "low"))
    hac = (o + h + l + c) / 4
    hao = hac.copy()
    # HA open recursion per ticker: hao_t = (hao_{t-1} + hac_{t-1}) / 2, seeded with (o+c)/2
    seed = (o + c) / 2
    vals = np.empty(len(t)); tk = t.ticker.to_numpy(); hv = hac.to_numpy(); sv = seed.to_numpy()
    for i in range(len(t)):
        vals[i] = sv[i] if i == 0 or tk[i] != tk[i - 1] else (vals[i - 1] + hv[i - 1]) / 2
    hao = pd.Series(vals, index=t.index)
    green = hac > hao
    red_run = w.lag(t, w.run_count(t, ~green))
    return {"H5 Heikin-Ashi first green after >=5 red": green & (red_run >= 5)}


FAMS = {f"F{i}": globals()[f"F{i}"] for i in range(1, 12)} | {f"H{i}": globals()[f"H{i}"] for i in range(1, 6)}


def main(argv):
    fam = argv[0]; confirm = "--confirm" in argv
    thin = "--thin" in argv   # G2: raw >= $5, $ADV $1-20M, 40bp round trip (shock 100bp)
    etf = "--etf" in argv     # G1: SFP ETFs ex leveraged/inverse, $ADV >= $20M
    cef = "--cef" in argv     # Round 10: SFP CEFs, $ADV >= $1M, 20bp RT (shock 60bp)
    pref = "--pref" in argv   # Round 11: SEP preferreds + SFP ETD, $ADV >= $200k, 40bp RT (shock 120bp)
    adr = "--adr" in argv     # Round 13: SEP ADRs, $ADV >= $1M, 20bp RT (shock 60bp)
    t = w.load_panel(kind="etf" if etf else "cef" if cef else "pref" if pref else "adr" if adr else "reit" if "--reit" in argv else "stock")
    uni, cost, shock, tag = "liq", w.COST, w.SHOCK, ""
    if thin:
        t["thin"] = (t.closeunadj >= 5) & (t.adv20 >= 1e6) & (t.adv20 < 20e6)
        uni, cost, shock, tag = "thin", 40e-4, 100e-4, " THIN"
    if etf:
        tag = " ETF"
    if cef:
        cost, shock, tag = 20e-4, 60e-4, " CEF"
    if pref:
        cost, shock, tag = 40e-4, 120e-4, " PREF"
    if adr:
        cost, shock, tag = 20e-4, 60e-4, " ADR"
    if "--reit" in argv:      # Round 14: REIT commons, $ADV >= $1M, 20bp RT; --mreit = mortgage REITs only
        cost, shock, tag = 20e-4, 60e-4, " REIT"
        if "--mreit" in argv:
            ind = pd.read_parquet(w.STORE / "tickers.parquet", columns=["table", "ticker", "industry"])
            mr = set(ind[(ind.table == "SEP") & (ind.industry == "REIT - Mortgage")].ticker)
            t["liq"] = t.liq & t.ticker.isin(mr); tag = " mREIT"
    t = w.add_bench(t, uni)
    arms = FAMS[fam](t)
    lines = []
    for lab, m in arms.items():
        m = m.fillna(False).astype(bool)
        r = w.judge(t, m, *w.DISC, lab + tag + " [2016-26]", uni=uni, cost=cost, shock=shock)
        lines.append(w.fmt(r))
        if confirm and w.passes(r):
            r2 = w.judge(t, m, *w.CONF, lab + tag + " [CONFIRM 2003-15]", uni=uni, cost=cost, shock=shock)
            lines.append(w.fmt(r2))
    txt = "\n".join(lines)
    print(txt)
    with open(OUT, "a") as f:
        f.write(f"# {fam} {pd.Timestamp.now():%Y-%m-%d %H:%M}\n{txt}\n\n")


if __name__ == "__main__":
    main(sys.argv[1:])
