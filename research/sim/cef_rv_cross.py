"""CEF-RV execution gate: reprice every 2016+ CEF-RV trade on official SIP auction crosses (attack on N 860).

    PYTHONPATH=. .venv/bin/python -m research.sim.cef_rv_cross fetch   # Alpaca auctions per CEF-RV fund, resumable
    PYTHONPATH=. .venv/bin/python -m research.sim.cef_rv_cross         # judge -> cef_rv_cross_out.txt

CC = closing cross of the first session after the entry signal -> closing cross of the first session after the exit
signal; OO = the opening crosses of those same sessions. Raw cross prices x that day's closeadj/closeunadj factor.
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import pandas as pd

from .auction_fetch import _env, fetch as fetch_auctions
from .exdiv_open import crosses

ROOT = pathlib.Path(__file__).resolve().parents[2]
STORE = pathlib.Path.home() / "data" / "sharadar"
CEF = ROOT / "data/research/cefconnect"
X = CEF / "x"
OUT = pathlib.Path(__file__).with_name("cef_rv_cross_out.txt")
COST = 0.005


def trades() -> pd.DataFrame:
    tr = pd.read_csv(CEF / "cef_rv_trades.csv", parse_dates=["edate", "xdate"])
    return tr[tr.edate >= "2016-01-01"].reset_index(drop=True)


def fetch():
    X.mkdir(parents=True, exist_ok=True)
    H = _env()
    for t in sorted(trades().ticker.unique()):
        f = X / f"{t}.json"
        if f.exists():
            continue
        rows = fetch_auctions([t], "2016-01-01", "2026-10-01", H)
        json.dump(rows.get(t, []), open(f, "w"))
        print(t, len(rows.get(t, [])), flush=True)
    print("DONE", flush=True)


def ct(x, keys):
    dm = pd.Series(np.asarray(x)).groupby(np.asarray(keys)).mean()
    return dm.mean(), dm.mean() / (dm.std(ddof=1) / np.sqrt(len(dm)))


def judge():
    tr = trades()
    f = pd.read_parquet(STORE / "funds.parquet", columns=["ticker", "date", "closeunadj", "closeadj"])
    f = f[f.ticker.isin(tr.ticker.unique())].copy()
    f["date"] = pd.to_datetime(f.date)
    f["fac"] = f.closeadj / f.closeunadj
    rows = []
    for t, g in tr.groupby("ticker"):
        p = X / f"{t}.json"
        if not p.exists():
            continue
        x = crosses(json.load(open(p)))
        h = f[f.ticker == t].set_index("date").sort_index()
        days = h.index.values
        for r in g.itertuples():
            i = np.searchsorted(days, np.datetime64(r.edate), side="right")
            j = np.searchsorted(days, np.datetime64(r.xdate), side="right")
            if j >= len(days):
                continue
            de, dx = pd.Timestamp(days[i]), pd.Timestamp(days[j])
            if de not in x.index or dx not in x.index:
                continue
            fe, fx = h.fac.iloc[i], h.fac.iloc[j]
            ce, cx, oe, ox = x.at[de, "cp"], x.at[dx, "cp"], x.at[de, "op"], x.at[dx, "op"]
            rows.append(dict(ticker=t, edate=r.edate, cc=cx * fx / (ce * fe) - 1, oo=ox * fx / (oe * fe) - 1,
                             adj=h.closeadj.iloc[j] / h.closeadj.iloc[i] - 1, csz=x.at[de, "cs"] * ce,
                             osz=x.at[de, "os"] * oe, cdev=ce / h.closeunadj.iloc[i] - 1))
    d = pd.DataFrame(rows).replace([np.inf, -np.inf], np.nan)
    L = []
    pr = lambda s_: (print(s_), L.append(s_))  # noqa: E731
    pr(f"CEF-RV cross repricing: {len(d)} of {len(tr)} 2016+ trades have both crosses")
    pr(f"closing cross vs Sharadar raw close at entry: median |dev| {d.cdev.abs().median()*1e4:.1f}bp, "
       f"p95 {d.cdev.abs().quantile(.95)*1e4:.1f}bp")
    wk = d.edate.dt.to_period("W").astype(str)
    for nm in ["adj", "cc", "oo"]:
        x = d[nm].dropna() - COST
        k = wk[x.index]
        m, t = ct(x, k)
        e = d.edate[x.index]
        h1, h2 = x[e < "2021-06-01"].mean(), x[e >= "2021-06-01"].mean()
        lab = {"adj": "Sharadar closeadj (reference)", "cc": "CC official closing crosses", "oo": "OO official opening crosses"}[nm]
        pr(f"{lab:32s} n {len(x):4d} net mean {x.mean()*1e4:+7.1f}bp med {x.median()*1e4:+7.1f} hit {(x>0).mean():.2f} "
           f"t_wk {t:5.2f} | halves {h1*1e4:+6.1f} / {h2*1e4:+6.1f} | 2x cost {(x-COST).mean()*1e4:+6.1f}")
    pr(f"entry closing-cross $ size: median ${d.csz.median():,.0f}, p25 ${d.csz.quantile(.25):,.0f}, p10 ${d.csz.quantile(.1):,.0f}; "
       f"opening-cross median ${d.osz.median():,.0f}")
    cc = d.cc.dropna() - COST
    e = d.edate[cc.index]
    ok = (cc.mean() >= 0.03 and ct(cc, wk[cc.index])[1] >= 5 and (d.oo.dropna() - COST).mean() >= 0.025
          and cc[e < "2021-06-01"].mean() > 0 and cc[e >= "2021-06-01"].mean() > 0 and d.csz.median() >= 20000)
    pr(f"GATE PASS={ok}")
    OUT.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    fetch() if len(sys.argv) > 1 and sys.argv[1] == "fetch" else judge()
