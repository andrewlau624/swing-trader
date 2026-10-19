"""Study CRYPTO-TA (round1_prose.md, N 997 -> 998): MACD / RSI pattern rules on the five Schwab-tradable coins.

Binance USDT spot daily (UTC days), long only, signal and fill at the close of day d.
Out: data/research/program/crypto_ta_out.txt
"""
import numpy as np
import pandas as pd

COINS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "LINKUSDT"]
START, END = "2018-01-01", "2026-09-30"
SPLIT = "2023-01-01"
RT = {"25bp/side": 0.005, "75bp/side (judge)": 0.015, "150bp/side (2x)": 0.03}
OUT = "data/research/program/crypto_ta_out.txt"


def rsi(c, n):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)


def frame(p):
    c = p.close
    f = pd.DataFrame({"close": c, "low": p.low})
    f["rsi14"], f["rsi2"] = rsi(c, 14), rsi(c, 2)
    f["sma200"], f["sma5"] = c.rolling(200).mean(), c.rolling(5).mean()
    m = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    f["macd"], f["sig"] = m, m.ewm(span=9, adjust=False).mean()
    f["mh"] = f.macd - f.sig
    return f.iloc[200:].loc[START:END]


# Each event rule: entry(f, i) -> bool, exit(f, i, entry_i) -> bool (checked from entry_i + 1).
def r1_in(f, i):
    r = f.rsi14.values
    return i >= 4 and r[i] > 30 and r[i - 1] <= 30 and (r[i - 3:i] < 30).all()


def r6_in(f, i):
    if i < 21:
        return False
    lo, r = f.low.values, f.rsi14.values
    w = slice(i - 20, i - 4)
    j = i - 20 + int(np.argmin(lo[w]))
    return lo[i] < lo[w].min() and r[i] > r[j] and r[i] < 40


def cross_up(a, b, i):
    return i >= 1 and a[i] > b[i] and a[i - 1] <= b[i - 1]


RULES = {
    "R1 RSI14 back above 30": (r1_in, lambda f, i, e: f.rsi14.values[i] >= 50 or i - e >= 20),
    "R2 RSI2<10 & >SMA200": (lambda f, i: f.rsi2.values[i] < 10 and f.close.values[i] > f.sma200.values[i],
                             lambda f, i, e: f.close.values[i] > f.sma5.values[i] or i - e >= 10),
    "R3 MACD x signal below 0": (lambda f, i: cross_up(f.macd.values, f.sig.values, i) and f.macd.values[i] < 0,
                                 lambda f, i, e: f.macd.values[i] < f.sig.values[i]),
    "R4 hist turns + after 5 neg": (lambda f, i: i >= 6 and f.mh.values[i] > 0 and (f.mh.values[i - 5:i] < 0).all(),
                                    lambda f, i, e: i - e >= 10),
    "R6 RSI bullish divergence": (r6_in, lambda f, i, e: i - e >= 10),
    "R7 RSI14 above 70 (momentum)": (lambda f, i: cross_up(f.rsi14.values, np.full(len(f), 70.0), i),
                                     lambda f, i, e: f.rsi14.values[i] < 50 or i - e >= 20),
}
REGIME = {
    "R5 MACD zero-line trend": lambda f: (f.macd > 0),
    "R8 MACD>0 & >SMA200": lambda f: (f.macd > 0) & (f.close > f.sma200),
}


def event_trades(f, ent, ext, mu):
    c, idx, out, i, n = f.close.values, f.index, [], 0, len(f)
    pos = np.zeros(n)
    while i < n:
        if ent(f, i):
            e = i
            j = e + 1
            while j < n and not ext(f, j, e):
                j += 1
            if j >= n:
                break  # open at the end: dropped
            ret = c[j] / c[e] - 1
            out.append((idx[e], j - e, ret, ret - (np.exp(mu * (j - e)) - 1)))
            pos[e + 1:j + 1] = 1  # exposed to returns of days e+1..j
            i = j + 1
        else:
            i += 1
    return out, pos


def stats(df, rt):
    x = df.exc - rt
    g = x.groupby(df.date).mean()  # date-clustered
    t = g.mean() / (g.std(ddof=1) / np.sqrt(len(g))) if len(g) > 2 else np.nan
    srt = np.sort(x.values)
    return dict(n=len(x), mean=x.mean() * 1e4, med=x.median() * 1e4, t=t, hit=(x > 0).mean(),
                exTop5=srt[:-5].mean() * 1e4 if len(srt) > 5 else np.nan,
                h1=x[df.date < SPLIT].mean() * 1e4, h2=x[df.date >= SPLIT].mean() * 1e4)


def perf(r, ppy=365):
    r = r.dropna()
    eq = (1 + r).cumprod()
    yrs = len(r) / ppy
    return dict(cagr=eq.iloc[-1] ** (1 / yrs) - 1, sharpe=r.mean() / r.std() * np.sqrt(ppy),
                mdd=(eq / eq.cummax() - 1).min(), expo=np.nan)


def book(pos_by, ret_by, rt):
    """Equal weight across coins live that day; cost rt/2 per side on position changes."""
    daily = []
    for s in pos_by:
        p, r = pos_by[s], ret_by[s]
        chg = p.diff().abs().fillna(p.iloc[0])
        daily.append(p * r - chg * rt / 2)
    d = pd.concat(daily, axis=1)
    return d.mean(axis=1, skipna=True)


def main():
    p = pd.read_parquet("data/research/crypto_spot/panel.parquet",
                        columns=["date", "symbol", "close", "low"])
    p = p[p.symbol.isin(COINS)]
    p["date"] = pd.to_datetime(p.date)
    F = {s: frame(g.set_index("date").sort_index()) for s, g in p.groupby("symbol")}
    R = {s: f.close.pct_change().fillna(0) for s, f in F.items()}
    MU = {s: np.log(f.close).diff().mean() for s, f in F.items()}
    lines = ["Study CRYPTO-TA  (N 998)  coins " + " ".join(c[:-4] for c in COINS) + f"  {START}..{END}", ""]

    bh = pd.concat([R[s] for s in F], axis=1).mean(axis=1)
    bperf = {h: perf(bh[m]) for h, m in [("all", bh.index >= START), ("h1", bh.index < SPLIT), ("h2", bh.index >= SPLIT)]}
    lines.append("EW buy&hold basket: " + "  ".join(
        f"{h} CAGR {v['cagr']:+.1%} Sh {v['sharpe']:.2f} mDD {v['mdd']:.0%}" for h, v in bperf.items()))
    lines.append("")
    lines.append("EVENT RULES: excess per trade vs coin drift x days held, bp, net of round trip; t date-clustered")
    for name, (ent, ext) in RULES.items():
        tr, pos = [], {}
        for s, f in F.items():
            t_, ps = event_trades(f, ent, ext, MU[s])
            tr += [(s,) + x for x in t_]
            pos[s] = pd.Series(ps, index=f.index)
        df = pd.DataFrame(tr, columns=["sym", "date", "days", "ret", "exc"])
        lines.append(f"\n{name}: trades {len(df)} ({len(df)/8.75:.0f}/yr all coins), mean hold {df.days.mean():.1f}d, "
                     f"gross raw {df.ret.mean()*1e4:+.0f}bp, gross excess {df.exc.mean()*1e4:+.0f}bp")
        for lab, rt in RT.items():
            s_ = stats(df, rt)
            lines.append(f"  {lab:18s} n {s_['n']:4d} mean {s_['mean']:+7.0f} med {s_['med']:+7.0f} t {s_['t']:+5.2f} "
                         f"hit {s_['hit']:.0%} exTop5 {s_['exTop5']:+6.0f} halves {s_['h1']:+6.0f}/{s_['h2']:+6.0f}")
        b = book(pos, R, RT["75bp/side (judge)"])
        v = perf(b)
        lines.append(f"  book @75bp: CAGR {v['cagr']:+.1%} Sh {v['sharpe']:.2f} mDD {v['mdd']:.0%}  "
                     f"time in market {np.mean([pos[s].mean() for s in pos]):.0%}")
        js = stats(df, RT["75bp/side (judge)"])
        sh = stats(df, RT["150bp/side (2x)"])
        ok = js["t"] >= 2 and js["mean"] > 0 and js["h1"] > 0 and js["h2"] > 0 and js["med"] > 0 \
            and js["exTop5"] > 0 and sh["mean"] > 0
        lines.append(f"  VERDICT: {'PASS' if ok else 'FAIL'}")

    lines.append("\nREGIME RULES (time in market; signal at close d, exposed d+1): net of cost on switches")
    for name, fn in REGIME.items():
        pos = {s: fn(f).astype(float).shift(1).fillna(0) for s, f in F.items()}
        lines.append(f"\n{name}: switches/yr/coin {np.mean([pos[s].diff().abs().sum() for s in pos])/8.75:.1f}, "
                     f"time in market {np.mean([pos[s].mean() for s in pos]):.0%}")
        res = {}
        for lab, rt in RT.items():
            b = book(pos, R, rt)
            parts = {h: perf(b[m]) for h, m in [("all", b.index >= START), ("h1", b.index < SPLIT), ("h2", b.index >= SPLIT)]}
            res[lab] = parts
            lines.append(f"  {lab:18s} " + "  ".join(
                f"{h} CAGR {v['cagr']:+.1%} Sh {v['sharpe']:.2f} mDD {v['mdd']:.0%}" for h, v in parts.items()))
        j = res["75bp/side (judge)"]
        ok = all(j[h]["sharpe"] >= bperf[h]["sharpe"] + 0.2 for h in ("h1", "h2")) and j["all"]["mdd"] > bperf["all"]["mdd"]
        lines.append(f"  VERDICT: {'PASS' if ok else 'FAIL'}  (needs Sharpe >= B&H+0.2 both halves and better maxDD)")

    txt = "\n".join(lines)
    open(OUT, "w").write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
