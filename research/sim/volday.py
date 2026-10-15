"""VOLDAY: standard day-trading alerts on a point-in-time volatile-liquid watchlist (pre-reg round1_prose.md, N 988 -> 993).
  PYTHONPATH=. .venv/bin/python -m research.sim.volday fetch | run"""
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from .auction_fetch import _env

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "data/research/volday"
OUT = ROOT / "data/research/program/volday_out.txt"
SHAR = Path("/Users/andrewlau/data/sharadar")
TOPN, ADV_MIN, PX_MIN = 10, 5e8, 10.0
C1, C2 = 5.0, 10.0  # bp per side
ARMS = ["A1_ORB15", "A2_VWAP", "A3_HOD", "A4_FLUSH", "A5_GAPFADE"]


def watchlist():
    f = D / "watchlist.parquet"
    if f.exists():
        return pd.read_parquet(f)
    tk = pd.read_parquet(SHAR / "tickers.parquet", columns=["table", "ticker", "category"])
    ok = set(tk[(tk.table == "SEP") & tk.category.fillna("").str.startswith("Domestic Common Stock")].ticker)
    st = pd.read_parquet(SHAR / "stocks.parquet", columns=["ticker", "date", "volume", "closeadj", "closeunadj"])
    st = st[st.ticker.isin(ok)]
    st["date"] = pd.to_datetime(st.date)
    st = st[st.date >= "2015-10-01"].sort_values(["ticker", "date"])
    g = st.groupby("ticker")
    st["ret"] = g.closeadj.pct_change()
    st["dv"] = st.closeunadj * st.volume
    st["adv"] = g.dv.transform(lambda x: x.rolling(20, min_periods=15).median())
    st["vol"] = g.ret.transform(lambda x: x.rolling(20, min_periods=15).std())
    st["pc"] = g.closeunadj.shift(1)
    st[["ticker", "date", "pc"]].to_parquet(D / "prevclose.parquet")
    me = st.groupby(st.date.dt.to_period("M")).date.max()
    rows = []
    for per, d in me.items():
        x = st[(st.date == d) & (st.closeunadj >= PX_MIN) & (st.adv >= ADV_MIN)].nlargest(TOPN, "vol")
        nxt = (per + 1)
        if nxt > pd.Period("2026-09", "M") or nxt < pd.Period("2016-01", "M"):
            continue
        rows += [dict(month=str(nxt), ticker=t, vol=v) for t, v in zip(x.ticker, x.vol)]
    w = pd.DataFrame(rows)
    w.to_parquet(f)
    return w


def fetch():
    import requests
    D.mkdir(parents=True, exist_ok=True)
    w = watchlist()
    H = _env()
    for month, g in w.groupby("month"):
        f = D / f"m1_{month}.parquet"
        if f.exists():
            continue
        p = pd.Period(month, "M")
        alias = {re.sub(r"\d+$", "", t): t for t in g.ticker}  # Sharadar suffixes reused tickers (APC1 = Anadarko as APC)
        params = dict(symbols=",".join(alias), timeframe="1Min", start=f"{p.start_time.date()}T13:00:00Z",
                      end=f"{(p.end_time + pd.Timedelta(days=1)).date()}T01:00:00Z", feed="sip", adjustment="raw", limit=10000)
        bars, tok = [], None
        while True:
            if tok:
                params["page_token"] = tok
            for k in range(5):
                r = requests.get("https://data.alpaca.markets/v2/stocks/bars", headers=H, params=params, timeout=60)
                if r.status_code == 429:
                    time.sleep(5 * (k + 1))
                    continue
                if r.status_code == 400 and "invalid symbol" in r.text.lower():
                    bad = re.findall(r"invalid symbol[s]?:? ?([A-Z.\-]+)", r.text, re.I)
                    print(month, "drop", bad or r.text[:80], flush=True)
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
                    bars.append((alias.get(s, s), x["t"], x["o"], x["h"], x["l"], x["c"], x["v"]))
            tok = js.get("next_page_token")
            if not tok:
                break
        df = pd.DataFrame(bars, columns=["sym", "t", "o", "h", "l", "c", "v"])
        df.to_parquet(f)
        print(month, len(g), len(df), flush=True)


def path_exit(h, l, c, k0, side, entry, stop, target, k_end):
    """Walk 1m bars k0..k_end; stop-first. Returns exit price."""
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


def signals(day, pc):
    """day: one name-day of RTH 1m bars (index minute-of-session). Returns list of (arm, k_entry, side, entry, stop, target_rule)."""
    o, h, l, c, v = (day[x].values for x in "ohlcv")
    mins = day.mos.values
    n = len(c)
    out = []
    pos = {m: i for i, m in enumerate(mins)}
    tp = (h + l + c) / 3
    vwap = np.cumsum(tp * v) / np.maximum(np.cumsum(v), 1)
    k15 = np.searchsorted(mins, 15)
    # A1 ORB15
    if k15 > 5:
        hi, lo = h[:k15].max(), l[:k15].min()
        for k in range(k15, n):
            if mins[k] > 90:
                break
            if c[k] > hi:
                out.append(("A1_ORB15", k, 1, c[k], lo, ("R", 2)))
                break
            if c[k] < lo:
                out.append(("A1_ORB15", k, -1, c[k], hi, ("R", 2)))
                break
    # A2 VWAP reclaim (long)
    below = False
    for k in range(n):
        if mins[k] >= 90:
            break
        if l[k] <= vwap[k] * 0.99:
            below = True
        elif below and c[k] > vwap[k]:
            out.append(("A2_VWAP", k, 1, c[k], l[:k + 1].min(), ("R", 2)))
            break
    # A3 HOD break with volume (long)
    cv = np.cumsum(v)
    for k in range(1, n):
        if mins[k] < 90:
            continue
        if mins[k] > 330:
            break
        if c[k] > h[:k].max() and v[k] >= 2 * cv[k - 1] / k:
            out.append(("A3_HOD", k, 1, c[k], l[max(0, k - 14):k + 1].min(), ("R", 2)))
            break
    # A4 flush reversal at 10:30 (long, hold to close)
    k = pos.get(60)
    if k is not None:
        hi, lo = h[:k + 1].max(), l[:k + 1].min()
        if c[k] <= o[0] * 0.985 and hi > lo and (c[k] - lo) / (hi - lo) < 0.15:
            out.append(("A4_FLUSH", k, 1, c[k], lo - 0.25 * (hi - lo), None))
    # A5 gap fade (short) at 09:35
    k = pos.get(4)
    if k is not None and pc and pc > 0 and o[0] / pc - 1 >= 0.03 and c[k] < o[0]:
        out.append(("A5_GAPFADE", k, -1, c[k], h[:k + 1].max(), ("P", pc)))
    return out


def realize(day, sig, side):
    arm, k, _, entry, stop0, trg = sig
    h, l, c, mins = day.h.values, day.l.values, day.c.values, day.mos.values
    dist = abs(entry - stop0)
    if dist <= 0:
        return None
    stop = entry - side * dist
    target = None
    if trg and trg[0] == "R":
        target = entry + side * trg[1] * dist
    elif trg and trg[0] == "P":
        target = trg[1] if (trg[1] - entry) * side > 0 else None
    k_end = int(np.searchsorted(mins, 385, side="right") - 1)
    if k_end <= k:
        return None
    px = path_exit(h, l, c, k + 1, side, entry, stop, target, k_end)
    gross = side * (px / entry - 1) * 1e4
    return gross, dist / entry * 1e4


def run():
    files = sorted(D.glob("m1_*.parquet"))
    pcs = pd.read_parquet(D / "prevclose.parquet")
    pcs = pcs.set_index(["ticker", pcs.date.dt.date]).pc.to_dict()
    rng = np.random.default_rng(42)
    rows, plac = [], []
    ndays = 0
    for f in files:
        m = pd.read_parquet(f)
        if m.empty:
            continue
        t = pd.to_datetime(m.t, utc=True).dt.tz_convert("America/New_York")
        m["date"] = t.dt.date
        m["mos"] = (t.dt.hour * 60 + t.dt.minute) - 570
        m = m[(m.mos >= 0) & (m.mos < 390)]
        for (sym, d), day in m.groupby(["sym", "date"]):
            if len(day) < 300:
                continue
            day = day.sort_values("mos")
            ndays += 1
            oc = (day.c.values[-1] / day.o.values[0] - 1) * 1e4
            for sig in signals(day, pcs.get((sym, d))):
                r = realize(day, sig, sig[2])
                if r is None:
                    continue
                flips = rng.integers(0, 2, 200) * 2 - 1
                pr = [realize(day, sig, s)[0] for s in (1, -1)]
                plac.append((sig[0], [pr[0] if s > 0 else pr[1] for s in flips]))
                rows.append(dict(arm=sig[0], sym=sym, date=pd.Timestamp(d), side=sig[2], gross=r[0], risk_bp=r[1], oc=oc))
    df = pd.DataFrame(rows)
    df.to_parquet(D / "trades.parquet")
    lines = [f"VOLDAY (N 993). name-days {ndays}, months {len(files)}, trades {len(df)}"]
    for arm in ARMS:
        x = df[df.arm == arm]
        if len(x) < 3:
            lines.append(f"{arm}: n {len(x)}")
            continue
        n1, n2 = x.gross - 2 * C1, x.gross - 2 * C2
        dd = n1.groupby(x.date).mean()
        t = dd.mean() / (dd.std(ddof=1) / np.sqrt(len(dd)))
        yr = x.date.dt.year
        h1, h2 = n1[yr <= 2020].mean(), n1[yr >= 2021].mean()
        ex5 = n1.drop(n1.nlargest(5).index).mean()
        P = np.array([p for a, p in plac if a == arm])
        pm = P.mean(axis=0)
        lines.append(f"{arm}: n {len(x)} ({len(x) / 10.75:.0f}/yr) gross {x.gross.mean():+.1f}bp | net1 {n1.mean():+.1f} t {t:.2f} "
                     f"| net2 {n2.mean():+.1f} | median net1 {n1.median():+.1f} | hit {(n1 > 0).mean():.0%} | ex-top5 {ex5:+.1f}")
        lines.append(f"   halves net1 2016-20 {h1:+.1f} (n {(yr <= 2020).sum()}) / 2021-26 {h2:+.1f} (n {(yr >= 2021).sum()}) | "
                     f"risk median {x.risk_bp.median():.0f}bp | mean R {(x.gross / x.risk_bp).mean():+.3f}")
        lines.append(f"   placebo gross mean {pm.mean():+.1f}, 95th {np.percentile(pm, 95):+.1f} -> real pct {(pm < x.gross.mean()).mean():.0%}"
                     + (f" | minus same-day open->close {(x.gross - x.side * x.oc).mean():+.1f}" if arm in ("A4_FLUSH", "A5_GAPFADE") else ""))
        lines.append("   by year net1: " + " ".join(f"{y}:{v:+.0f}" for y, v in n1.groupby(yr).mean().items()))
        tpy = len(x) / 10.75
        for acct in (2300, 10_000, 25_000):
            pct = tpy * n1.mean() / 1e4 * 0.5 * 100
            lines.append(f"   ceiling ${acct:,}: {tpy:.0f} trades/yr x {n1.mean():+.1f}bp x 100% x 50% = {pct:+.1f}%/yr pre-tax") if acct == 10_000 else None
    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    {"fetch": fetch, "run": run, "wl": lambda: print(watchlist().groupby("month").ticker.apply(",".join).tail(12))}[sys.argv[1]]()
