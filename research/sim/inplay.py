"""INPLAY: in-play scanner (RVOL + catalyst gap + two-way chop + levels) x 3 styles (pre-reg round1_prose.md, N 993 -> 996).
  PYTHONPATH=. .venv/bin/python -m research.sim.inplay pools | fetch | run"""
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from .auction_fetch import _env

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "data/research/inplay"
OUT = ROOT / "data/research/program/inplay_out.txt"
SHAR = Path("/Users/andrewlau/data/sharadar")
C1, C2 = 5.0, 10.0
STYLES = ["S1_FADE", "S2_BURST", "S3_MIX"]


def pools():
    f = D / "pools.parquet"
    if f.exists():
        return pd.read_parquet(f)
    D.mkdir(parents=True, exist_ok=True)
    tk = pd.read_parquet(SHAR / "tickers.parquet", columns=["table", "ticker", "category"])
    ok = set(tk[(tk.table == "SEP") & tk.category.fillna("").str.startswith("Domestic Common Stock")].ticker)
    st = pd.read_parquet(SHAR / "stocks.parquet", columns=["ticker", "date", "open", "high", "low", "close", "volume", "closeunadj"])
    st = st[st.ticker.isin(ok)]
    st["date"] = pd.to_datetime(st.date)
    st = st[st.date >= "2018-10-01"].sort_values(["ticker", "date"])
    g = st.groupby("ticker")
    st["dv"] = st.closeunadj * st.volume
    rng = (st.high - st.low).replace(0, np.nan)
    st["twoway"] = 1 - (st.close - st.open).abs() / rng
    st["rangep"] = rng / st.close
    for c, w in (("dv", "adv"), ("twoway", "tw20"), ("rangep", "rg20")):
        st[w] = g[c].transform(lambda x: x.rolling(20, min_periods=15).mean() if c != "dv" else x.rolling(20, min_periods=15).median())
        st[w] = g[w].shift(1)
    k = st.closeunadj / st.close
    st["pc_raw"] = g.closeunadj.shift(1)
    st["pdh_raw"] = (st.high * k).groupby(st.ticker).shift(1)
    st["pdl_raw"] = (st.low * k).groupby(st.ticker).shift(1)
    st["gap"] = st.open / g.close.shift(1) - 1
    st = st[(st.date >= "2019-01-02") & (st.date <= "2026-09-30") & (st.pc_raw >= 10) & (st.adv >= 2e8)]
    rows = []
    for d, x in st.groupby("date"):
        gp = x[x.gap.abs() >= 0.01].assign(ag=lambda y: y.gap.abs()).nlargest(25, "ag").assign(pool="G")
        rest = x[(x.adv >= 1e9) & (x.rg20 >= 0.02) & ~x.ticker.isin(gp.ticker)]
        cp = rest.nlargest(10, "tw20").assign(pool="C")  # deviation: two-way first, deep liquidity (pre-outcome)
        rows.append(pd.concat([gp, cp]))
    p = pd.concat(rows)[["date", "ticker", "pool", "gap", "adv", "pc_raw", "pdh_raw", "pdl_raw"]]
    p.to_parquet(f)
    return p


def fetch():
    import requests
    p = pools()
    H = _env()
    for month, pm in p.groupby(p.date.dt.to_period("M")):
        f = D / f"m1_{month}.parquet"
        if f.exists():
            continue
        bars = []
        for d, g in pm.groupby("date"):
            alias = {re.sub(r"\d+$", "", t): t for t in g.ticker}
            alias["SPY"] = "SPY"
            params = dict(symbols=",".join(alias), timeframe="1Min", start=f"{d.date()}T13:25:00Z", end=f"{d.date()}T21:05:00Z",
                          feed="sip", adjustment="raw", limit=10000)
            tok = None
            while True:
                if tok:
                    params["page_token"] = tok
                for k in range(6):
                    r = requests.get("https://data.alpaca.markets/v2/stocks/bars", headers=H, params=params, timeout=60)
                    if r.status_code == 429:
                        time.sleep(5 * (k + 1))
                        continue
                    if r.status_code == 400 and "invalid symbol" in r.text.lower():
                        bad = re.findall(r"invalid symbol[s]?:? ?([A-Z.\-]+)", r.text, re.I)
                        alias = {a: t for a, t in alias.items() if a not in bad}
                        params["symbols"] = ",".join(alias)
                        if not bad:
                            r.raise_for_status()
                        continue
                    r.raise_for_status()
                    break
                js = r.json()
                for s, b in (js.get("bars") or {}).items():
                    for x in b:
                        bars.append((d, alias.get(s, s), x["t"], x["o"], x["h"], x["l"], x["c"], x["v"]))
                tok = js.get("next_page_token")
                if not tok:
                    break
        pd.DataFrame(bars, columns=["date", "sym", "t", "o", "h", "l", "c", "v"]).to_parquet(f)
        print(month, pm.date.nunique(), len(bars), flush=True)


def walk(h, l, c, k0, k_end, side, entry, stop, target):
    for k in range(k0, k_end + 1):
        if side > 0:
            if l[k] <= stop:
                return stop
            if target is not None and h[k] >= target:
                return target
        else:
            if h[k] >= stop:
                return stop
            if target is not None and l[k] <= target:
                return target
    return c[k_end]


def kidx(mins, m):
    return int(np.searchsorted(mins, m, side="right") - 1)


def signals(day, spy, row):
    """Returns list of (style, k, side, entry, stop_dist, target_kind, target_val, k_end_minute, extra)."""
    o, h, l, c, v, mins = (day[x].values for x in ("o", "h", "l", "c", "v", "mos"))
    n = len(c)
    tp = (h + l + c) / 3
    cv = np.cumsum(v)
    vwap = np.cumsum(tp * v) / np.maximum(cv, 1)
    k10 = kidx(mins, 29)
    if k10 < 20:
        return [], None
    rvol = (c[:k10 + 1] * v[:k10 + 1]).sum() / row.adv
    if rvol < 0.30:
        return [], rvol
    out = []
    k_start = k10 + 1
    k_last = kidx(mins, 359)  # 15:29
    # S1 fade
    dev = c - vwap
    for k in range(max(k_start, 30), k_last):
        sd = dev[:k].std()
        if sd <= 0:
            continue
        if abs(dev[k]) >= 2 * sd and k + 1 < n and abs(dev[k + 1]) < 2 * sd:
            side = -1 if dev[k] > 0 else 1
            e = c[k + 1]
            ext = h[:k + 2].max() if side < 0 else l[:k + 2].min()
            stop = ext - side * 0.25 * abs(e - vwap[k + 1])
            dist = abs(e - stop)
            if dist > 0 and (vwap[k + 1] - e) * side > 0:
                out.append(("S1_FADE", k + 1, side, e, dist, "P", vwap[k + 1], 385, ""))
            break
    # levels
    orh, orl = h[:k10 + 1].max(), l[:k10 + 1].min()
    levels = [("PDH", row.pdh_raw), ("PDL", row.pdl_raw), ("ORH", orh), ("ORL", orl)]
    levels = [(nm, x) for nm, x in levels if x and np.isfinite(x)]
    # S2 burst
    done = False
    for k in range(k_start, k_last):
        mv = cv[k - 1] / k
        if v[k] < 3 * mv:
            continue
        for nm, lv in levels:
            if c[k] > lv >= c[k - 1]:
                side = 1
            elif c[k] < lv <= c[k - 1]:
                side = -1
            else:
                continue
            dist = (c[k] - l[k]) if side > 0 else (h[k] - c[k])
            if dist > 0:
                out.append(("S2_BURST", k, side, c[k], dist, "R", 2.0, min(385, mins[k] + 30), nm))
                done = True
            break
        if done:
            break
    # S3 mix with bot direction
    smap = dict(zip(spy.mos.values, spy.c.values))
    spy_o = spy.o.values[0] if len(spy) else np.nan
    for k in range(k_start, k_last):
        touched = [nm for nm, lv in levels + [("VWAP", vwap[k])] if l[k] <= lv <= h[k]]
        if not touched:
            continue
        sc = smap.get(mins[k])
        Dsc = np.sign(c[k] - vwap[k]) + np.sign(c[k] - o[0]) + (np.sign(sc - spy_o) if sc else 0) + np.sign(row.gap)
        if abs(Dsc) >= 2 and k >= 15:
            atr = (h[k - 14:k + 1] - l[k - 14:k + 1]).mean() * np.sqrt(15)
            if atr > 0:
                out.append(("S3_MIX", k, int(np.sign(Dsc)), c[k], 1.5 * atr, "R", 1.5, min(385, mins[k] + 60), f"{touched[0]}|D{int(abs(Dsc))}"))
        break
    return out, rvol


def realize(day, s, side):
    style, k, _, e, dist, tk, tv, mend, _x = s
    h, l, c, mins = day.h.values, day.l.values, day.c.values, day.mos.values
    stop = e - side * dist
    if tk == "R":
        target = e + side * tv * dist
    else:
        target = tv if (tv - e) * side > 0 else None
    k_end = kidx(mins, mend)
    if k_end <= k:
        return None
    return side * (walk(h, l, c, k + 1, k_end, side, e, stop, target) / e - 1) * 1e4


def run():
    p = pools()
    pk = p.set_index(["date", "ticker"])
    rng = np.random.default_rng(42)
    rows, plac = [], []
    nday = ninplay = 0
    for f in sorted(D.glob("m1_*.parquet")):
        m = pd.read_parquet(f)
        t = pd.to_datetime(m.t, utc=True).dt.tz_convert("America/New_York")
        m["mos"] = t.dt.hour * 60 + t.dt.minute - 570
        m = m[(m.mos >= 0) & (m.mos < 390)]
        for d, md in m.groupby("date"):
            spy = md[md.sym == "SPY"].sort_values("mos")
            for sym, day in md[md.sym != "SPY"].groupby("sym"):
                if len(day) < 300 or (d, sym) not in pk.index:
                    continue
                row = pk.loc[(d, sym)]
                if isinstance(row, pd.DataFrame):
                    row = row.iloc[0]
                day = day.sort_values("mos")
                nday += 1
                sigs, rvol = signals(day, spy, row)
                if rvol is not None and rvol >= 0.30:
                    ninplay += 1
                for s in sigs:
                    g = realize(day, s, s[2])
                    mir = realize(day, s, -s[2])
                    if g is None or mir is None:
                        continue
                    flips = rng.integers(0, 2, 200)
                    plac.append((s[0], np.where(flips == 1, g, mir)))
                    rows.append(dict(style=s[0], date=pd.Timestamp(d), sym=sym, side=s[2], gross=g, mirror=mir, risk_bp=s[4] / s[3] * 1e4,
                                     rvol=rvol, pool=row.pool, gap=row.gap, tag=s[8]))
    df = pd.DataFrame(rows)
    df.to_parquet(D / "trades.parquet")
    yrs = (df.date.max() - df.date.min()).days / 365.25
    L = [f"INPLAY (N 996). candidate name-days {nday}, in play (RVOL30 >= 0.30) {ninplay}, trades {len(df)}, {yrs:.2f} yrs"]
    for st in STYLES:
        x = df[df["style"] == st]
        if len(x) < 3:
            L.append(f"{st}: n {len(x)}")
            continue
        n1, n2 = x.gross - 2 * C1, x.gross - 2 * C2
        dd = n1.groupby(x.date).mean()
        t = dd.mean() / (dd.std(ddof=1) / np.sqrt(len(dd)))
        yr = x.date.dt.year
        P = np.array([p for a, p in plac if a == st]).mean(axis=0)
        L.append(f"{st}: n {len(x)} ({len(x) / yrs:.0f}/yr) gross {x.gross.mean():+.1f}bp | net1 {n1.mean():+.1f} t {t:.2f} | net2 {n2.mean():+.1f}"
                 f" | median {n1.median():+.1f} | hit {(n1 > 0).mean():.0%} | ex-top5 {n1.drop(n1.nlargest(5).index).mean():+.1f}")
        L.append(f"   halves net1 2019-22 {n1[yr <= 2022].mean():+.1f} (n {(yr <= 2022).sum()}) / 2023-26 {n1[yr >= 2023].mean():+.1f} (n {(yr >= 2023).sum()})"
                 f" | risk median {x.risk_bp.median():.0f}bp | placebo mean {P.mean():+.1f} 95th {np.percentile(P, 95):+.1f} -> pct {(P < x.gross.mean()).mean():.0%}"
                 f" | direction value (real-mirror)/2 {((x.gross - x.mirror) / 2).mean():+.1f}")
        L.append("   by year net1: " + " ".join(f"{y}:{v:+.0f}" for y, v in n1.groupby(yr).mean().items()))
        L.append(f"   ceiling $10k: {len(x) / yrs:.0f}/yr x {n1.mean():+.1f}bp x 50% = {len(x) / yrs * n1.mean() / 1e4 * 50:+.1f}%/yr pre-tax")
        x = x.assign(n1=n1, rt=pd.qcut(x.rvol, 3, labels=["rvol_lo", "rvol_mid", "rvol_hi"]), h=np.where(yr <= 2022, "h1", "h2"))
        for col in ["rt", "pool"] + (["tag"] if st != "S1_FADE" else []):
            key = x[col].astype(str).str.split("|").str[0] if col == "tag" else x[col].astype(str)
            tab = x.groupby([key, "h"]).n1.mean().unstack()
            cnt = x.groupby(key).size()
            L.append(f"   by {col}: " + "; ".join(f"{i} n{cnt[i]} {r.get('h1', np.nan):+.1f}/{r.get('h2', np.nan):+.1f}" for i, r in tab.iterrows()))
        if st == "S3_MIX":
            key = x.tag.str.split("|").str[1]
            L.append("   by |D|: " + "; ".join(f"{i} n{len(g)} net1 {g.n1.mean():+.1f} dirval {((g.gross - g.mirror) / 2).mean():+.1f}" for i, g in x.groupby(key)))
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    {"pools": lambda: print(pools().groupby("pool").size(), pools().tail(12)), "fetch": fetch, "run": run}[sys.argv[1]]()
