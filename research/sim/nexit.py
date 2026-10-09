"""Study NEXIT (round1_prose.md, N 901 -> 907): indicator-gated intraday exits for the night leg vs the 09:30 auction.
Judge 2016-20 exact 15:40 picks; report 2020-11..2026-09 (dtime T=1540, vol20>=.6). Rules frozen in the prose; one run, no tuning.
Run: PYTHONPATH=. .venv/bin/python research/sim/nexit.py fetch|eval"""
import sys, os, glob, time
REPO = "/Users/andrewlau/Documents/Code/Projects/swing-trader"; sys.path.insert(0, REPO); os.chdir(REPO)
import numpy as np, pandas as pd
N = f"{REPO}/data/research/night"; FM = f"{N}/fm1"; os.makedirs(FM, exist_ok=True)
OUT = f"{REPO}/data/research/program/nexit_out.txt"


def picks():
    e = pd.read_parquet(f"{N}/etf_daily.parquet")
    cal = pd.DatetimeIndex(sorted(pd.to_datetime(e.timestamp).dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize().unique()))
    nxt = {d: cal[i + 1] for i, d in enumerate(cal[:-1])}
    a = pd.read_parquet(f"{REPO}/data/research/program/night_exact_pre2021.parquet").reset_index()
    a = a.rename(columns={"ret": "ovn"})[["date", "sym", "ovn"]]; a["era"] = "judge"
    x = pd.read_pickle(f"{N}/dtime.pkl"); x = x[(x["T"] == 1540) & (x.vol20 >= 0.6)][["date", "sym"]].copy()
    P = pd.read_pickle(f"{N}/panel.pkl"); C, O = P["close"], P["open"]
    x["ovn"] = [O[s].shift(-1).get(d, np.nan) / C.at[d, s] - 1 if s in C else np.nan for d, s in zip(x.date, x.sym)]
    x["era"] = "report"
    df = pd.concat([a, x]); df["date"] = pd.to_datetime(df.date)
    df["nd"] = df.date.map(nxt); return df.dropna(subset=["nd", "ovn"])


def fetch():
    from swingtrader.data import _clients
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    df = picks(); c, _ = _clients()
    for nd, g in df.groupby("nd"):
        p = f"{FM}/{nd.date()}.parquet"
        if os.path.exists(p): continue
        st = (nd + pd.Timedelta(hours=9, minutes=30)).tz_localize("America/New_York").tz_convert("UTC")
        en = (nd + pd.Timedelta(hours=16)).tz_localize("America/New_York").tz_convert("UTC")
        for k in range(4):
            try:
                r = c.get_stock_bars(StockBarsRequest(symbol_or_symbols=sorted(set(g.sym)), timeframe=TimeFrame.Minute,
                                                      start=st, end=en, feed="sip", adjustment="all")).df; break
            except Exception as e:
                print("err", nd.date(), str(e)[:100], flush=True); time.sleep(5); r = None
        (r.reset_index() if r is not None and len(r) else pd.DataFrame({"symbol": []})).to_parquet(p)
    print("DONE", flush=True)


def ema(v, n): return pd.Series(v).ewm(span=n, adjust=False).mean().values


def rsi(v, n=14):
    d = np.diff(v, prepend=v[0]); up = pd.Series(np.clip(d, 0, None)).ewm(alpha=1 / n, adjust=False).mean()
    dn = pd.Series(np.clip(-d, 0, None)).ewm(alpha=1 / n, adjust=False).mean()
    return (100 - 100 / (1 + up / dn.replace(0, np.nan))).fillna(50).values


def exits(g):
    """g: one symbol's minute bars 09:30-15:59 (hm, open, high, low, close). Returns {rule: exit price ratio vs 09:30 open or None for close}."""
    o0 = g.open.iloc[0]; cl = g.close.values; op = g.open.values; hm = g.hm.values; n = len(g)
    fill = lambda i: op[i + 1] / o0 if i + 1 < n else cl[-1] / o0
    res = {"CLOSE": cl[-1] / o0}
    runhi = np.maximum.accumulate(cl)
    # R1 trailing 1%
    i = np.argmax(cl <= runhi * 0.99) if (cl <= runhi * 0.99).any() else None
    res["R1"] = fill(i) if i is not None else cl[-1] / o0
    # R2/R3 gated local max
    r2 = r3 = None; armed = False; hi = -np.inf
    for i in range(n):
        if not armed:
            if r3 is None and cl[i] <= o0 * 0.98: r3 = fill(i)
            if cl[i] >= o0 * 1.02: armed = True; hi = cl[i]
            continue
        hi = max(hi, cl[i])
        if cl[i] <= hi * 0.99: r2 = fill(i); r3 = r3 if r3 is not None else r2; break
    res["R2"] = r2 if r2 is not None else cl[-1] / o0
    res["R3"] = r3 if r3 is not None else res["R2"]
    # 5-min bars
    g5 = g.assign(b=(np.arange(n) // 5)).groupby("b").agg(hm=("hm", "last"), high=("high", "max"), low=("low", "min"), close=("close", "last"), last=("i", "last"))
    c5 = g5.close.values; m5 = len(g5)
    h = ema(c5, 12) - ema(c5, 26); hist = h - ema(h, 9)
    r4 = None; pos = 0
    for j in range(m5):
        if hist[j] > 0: pos += 1; continue
        if pos >= 3 and g5.hm.values[j] >= 945: r4 = fill(int(g5["last"].values[j])); break
        pos = 0
    res["R4"] = r4 if r4 is not None else cl[-1] / o0
    s = pd.Series(c5); ma = s.rolling(20).mean(); sd = s.rolling(20).std(ddof=0)
    tr = pd.concat([g5.high - g5.low, (g5.high - s.shift()).abs(), (g5.low - s.shift()).abs()], axis=1).max(axis=1).values
    atr = pd.Series(tr).rolling(20).mean()
    sq = ((ma + 2 * sd) < (ma + 1.5 * atr)) & ((ma - 2 * sd) > (ma - 1.5 * atr))
    e5 = ema(c5, 5); r5 = None; run = 0; released = False
    for j in range(m5):
        if sq.iloc[j]: run += 1; continue
        if run >= 6: released = True
        run = 0
        if released and c5[j] < e5[j] and c5[j] > o0: r5 = fill(int(g5["last"].values[j])); break
    res["R5"] = r5 if r5 is not None else cl[-1] / o0
    rs = rsi(cl); r6 = None; above = 0
    for i in range(n):
        if rs[i] > 70: above += 1; continue
        if above >= 3 and cl[i] > o0: r6 = fill(i); break
        above = 0
    res["R6"] = r6 if r6 is not None else cl[-1] / o0
    return res


def evaluate():
    df = picks(); rows = []; miss = 0
    for nd, g in df.groupby("nd"):
        p = f"{FM}/{nd.date()}.parquet"
        if not os.path.exists(p): miss += len(g); continue
        m = pd.read_parquet(p)
        if not len(m): miss += len(g); continue
        t = pd.to_datetime(m.timestamp).dt.tz_convert("America/New_York"); m["hm"] = t.dt.hour * 100 + t.dt.minute
        m = m[(m.hm >= 930) & (m.hm <= 1559)]
        for r in g.itertuples():
            b = m[m.symbol == r.sym].reset_index(drop=True)
            if len(b) < 30 or b.hm.iloc[0] != 930: miss += 1; continue
            b["i"] = np.arange(len(b))
            e = exits(b); rows.append({"date": r.date, "era": r.era, "ovn": r.ovn, **e})
    R = pd.DataFrame(rows)
    L = [f"NEXIT  picks scored {len(R)} (judge {sum(R.era=='judge')}, report {sum(R.era=='report')}); dropped (no/short minute bars) {miss}"]
    for era in ["judge", "report"]:
        X = R[R.era == era]; L.append(f"\n== {era} {X.date.min().date()}..{X.date.max().date()}  n {len(X)}  days {X.date.nunique()}")
        L.append(f"B0 open auction: mean {X.ovn.mean()*1e4:+.1f}bp median {X.ovn.median()*1e4:+.1f}")
        for k in ["CLOSE", "R1", "R2", "R3", "R4", "R5", "R6"]:
            for cost in ([5, 10, 20] if k != "CLOSE" else [0]):
                d = (1 + X.ovn) * (X[k] - 1) - cost / 1e4
                dm = d.groupby(X.date).mean(); t = dm.mean() / dm.std() * np.sqrt(len(dm))
                h1 = d[X.date < ("2019" if era == "judge" else "2024")].mean(); h2 = d[X.date >= ("2019" if era == "judge" else "2024")].mean()
                ex5 = dm.drop(dm.nlargest(5).index).mean()
                ok = (d.mean() >= 15e-4 and t >= 2.5 and h1 > 0 and h2 > 0 and d.median() > 0 and ex5 > 0) if cost == 10 else None
                L.append(f"  {k:5s} cost {cost:2d}  paired vs B0 {d.mean()*1e4:+7.1f}bp  med {d.median()*1e4:+7.1f}  t {t:+5.2f}  halves {h1*1e4:+6.1f}/{h2*1e4:+6.1f}"
                         f"  ex-top5d {ex5*1e4:+6.1f}  hold-to-close {100*(X[k]==X.CLOSE).mean():3.0f}%" + ("" if ok is None else f"  GATE {'PASS' if ok else 'fail'}"))
    open(OUT, "w").write("\n".join(L) + "\n"); print("\n".join(L))


if __name__ == "__main__":
    fetch() if sys.argv[1] == "fetch" else evaluate()
