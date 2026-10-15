"""QI-HIST: 15:40 NBBO quote imbalance vs night bounce, 2016-20 exact picks. Pre-reg: round1_prose.md "Study QI-HIST".
    PYTHONPATH=. .venv/bin/python -m research.sim.qi_hist fetch   # cached quote pull
    PYTHONPATH=. .venv/bin/python -m research.sim.qi_hist          # judge once
"""
from __future__ import annotations
import json, pathlib, sys, time
import numpy as np, pandas as pd, requests
from concurrent.futures import ThreadPoolExecutor
from .auction_fetch import _env

ROOT = pathlib.Path(__file__).resolve().parents[2]
PICKS = ROOT / "data/research/program/night_exact_pre2021.parquet"
CACHE = ROOT / "data/research/program/qi_hist_quotes.json"
OUT = ROOT / "data/research/program/qi_hist_out.txt"
H = None


def one(sym, d):
    t0 = pd.Timestamp(d).tz_localize("America/New_York")
    q = {"start": (t0 + pd.Timedelta(hours=15, minutes=30)).isoformat(),
         "end": (t0 + pd.Timedelta(hours=15, minutes=40)).isoformat(),
         "feed": "sip", "limit": 50, "sort": "desc"}
    for _ in range(6):
        r = requests.get(f"https://data.alpaca.markets/v2/stocks/{sym}/quotes", params=q, headers=H, timeout=30)
        if r.status_code == 429:
            time.sleep(10); continue
        if r.status_code >= 400:
            return None
        v = [x for x in (r.json().get("quotes") or []) if x.get("bp", 0) > 0 and x.get("ap", 0) > x.get("bp", 0)]
        return {"bs": v[0]["bs"], "as": v[0]["as"], "t": v[0]["t"]} if v else {}
    return None


def fetch():
    global H
    H = _env()
    P = pd.read_parquet(PICKS).reset_index()
    got = json.load(open(CACHE)) if CACHE.exists() else {}
    todo = [(r.sym, r.date) for r in P.itertuples() if f"{r.sym}_{r.date.date()}" not in got]
    print(len(todo), "to fetch", flush=True)
    def w(a):
        time.sleep(0.25); return a, one(*a)
    n = 0
    with ThreadPoolExecutor(4) as ex:
        for (s, d), v in ex.map(w, todo):
            if v is not None:
                got[f"{s}_{d.date()}"] = v
            n += 1
            if n % 300 == 0:
                json.dump(got, open(CACHE, "w")); print(n, flush=True)
    json.dump(got, open(CACHE, "w"))


def judge():
    P = pd.read_parquet(PICKS).reset_index()
    got = json.load(open(CACHE))
    P["q"] = [got.get(f"{r.sym}_{r.date.date()}") for r in P.itertuples()]
    n0 = len(P)
    nofetch = P.q.isna().sum(); noq = P.q.apply(lambda x: x == {}).sum()
    P = P[P.q.apply(lambda x: bool(x))].copy()
    P["qi"] = [(x["bs"] - x["as"]) / (x["bs"] + x["as"]) if (x["bs"] + x["as"]) > 0 else np.nan for x in P.q]
    P = P.dropna(subset=["qi"])
    P = P[P.ret.abs() < 1].reset_index(drop=True)
    lines = [f"picks {n0}, not fetched {nofetch}, no valid quote {noq}, scored {len(P)}"]
    cuts = P.qi.quantile([1 / 3, 2 / 3]).values
    P["b"] = np.digitize(P.qi, cuts, right=True)
    lines.append(f"QI tercile cuts {cuts[0]:+.3f} {cuts[1]:+.3f}")
    yr = P.date.dt.year
    for lab, c in (("1x(7.5bp/side)", 15e-4), ("2x(15bp/side)", 30e-4)):
        P["net"] = P.ret - c
        lines.append(f"-- costs {lab}")
        for k, nm in enumerate(["T1 sell-heavy", "T2 middle", "T3 buy-heavy"]):
            x = P.net[P.b == k]
            lines.append(f"  {nm}: n {len(x)} mean {x.mean()*1e4:+.1f}bp median {x.median()*1e4:+.1f} hit {(x>0).mean()*100:.0f}%")
        def gain(df):
            return (df.net[df.b != 0].mean() - df.net.mean()) * 1e4
        def clus_t(df):
            y = df.net.values; s = (df.b == 0).values.astype(float)
            X = np.c_[np.ones(len(df)), s]; XtXi = np.linalg.inv(X.T @ X)
            beta = XtXi @ X.T @ y; e = y - X @ beta
            meat = np.zeros((2, 2))
            for _, ix in df.groupby("date").indices.items():
                u = X[ix].T @ e[ix]; meat += np.outer(u, u)
            se = np.sqrt((XtXi @ meat @ XtXi)[1, 1]); return beta[1] / se
        g = gain(P); t = clus_t(P)
        h1 = P[yr <= 2018]; h2 = P[yr >= 2019]
        ex5 = P.drop(P.net.nlargest(5).index)
        rng = np.random.default_rng(898)
        pl = []
        for _ in range(1000):
            bb = rng.permutation(P.b.values); pl.append((P.net[bb != 0].mean() - P.net.mean()) * 1e4)
        pl = np.array(pl); pct = (pl < g).mean() * 100
        lines.append(f"  skip-T1 gain {g:+.1f}bp/trade; T1-vs-rest clustered t {t:+.2f} (T1 minus rest: sign {'negative' if t<0 else 'positive'}; skip helps if t<0)")
        lines.append(f"  halves 2016-18 {gain(h1):+.1f} / 2019-20 {gain(h2):+.1f}; ex-top-5 {gain(ex5):+.1f}; placebo pct {pct:.0f}")
        lines.append(f"  by year gain: " + " ".join(f"{y} {gain(P[yr==y]):+.0f}" for y in sorted(yr.unique())))
        if c == 15e-4:
            ok = g >= 30 and t <= -2 and gain(h1) > 0 and gain(h2) > 0 and gain(ex5) > 0 and pct >= 95
            lines.append(f"  GATE (1x): {'PASS' if ok else 'DEAD'}")
    txt = "\n".join(lines); print(txt); OUT.write_text(txt + "\n")


if __name__ == "__main__":
    fetch() if sys.argv[1:] == ["fetch"] else judge()
