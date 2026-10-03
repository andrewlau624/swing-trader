"""Goal hunt Study G13 (pre-registered in round1_prose.md, commit dbb87bc): issuers whose XBRL facts show >= 2% of shares
outstanding repurchased in one quarter; buy the session after the filing, hold 63 sessions, vs SPY.

    PYTHONPATH=. .venv/bin/python -m research.sim.goal_g13 build
    PYTHONPATH=. .venv/bin/python -m research.sim.goal_g13 select     # filings 2021-23, one look

Output: data/research/program/goal_g13_out.txt
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

import numpy as np
import pandas as pd
import requests

from . import book as B
from . import event_fetch as F

ROOT = pathlib.Path(__file__).resolve().parents[2]
PROG = ROOT / "data/research/program"
EVF = PROG / "goal_g13_events.parquet"
UA = {"User-Agent": "swing-trader research andrewlau2007@gmail.com"}
CONC = ("StockRepurchasedDuringPeriodShares", "TreasuryStockSharesAcquired")
HOLD, THR = 63, 0.02
SEL = ("2021-01-01", "2023-12-31")


def out():
    f = open(PROG / "goal_g13_out.txt", "a")

    def log(*a):
        x = " ".join(str(i) for i in a)
        print(x, flush=True); f.write(x + "\n"); f.flush()
    return log


def facts(cik: str) -> dict | None:
    f = F._cache("xbrl", f"{cik}.json")
    if f.exists():
        t = f.read_text()
        return json.loads(t) if t else None
    for _ in range(3):
        try:
            r = requests.get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cik):010d}.json", headers=UA, timeout=30)
            time.sleep(0.13)
            if r.status_code == 404:
                f.write_text(""); return None
            if r.ok:
                j = r.json()
                slim = {"usgaap": {k: j["facts"].get("us-gaap", {}).get(k) for k in CONC},
                        "so": j["facts"].get("dei", {}).get("EntityCommonStockSharesOutstanding")}
                f.write_text(json.dumps(slim)); return slim
        except Exception:
            time.sleep(2)
    return None


def events_of(cik: str, j: dict) -> list[dict]:
    so = pd.DataFrame((j.get("so") or {}).get("units", {}).get("shares", []))
    if not len(so):
        return []
    so["filed"] = pd.to_datetime(so.filed)
    so = so.sort_values("filed")
    rows = []
    for k in CONC:
        c = j["usgaap"].get(k)
        if not c:
            continue
        q = pd.DataFrame(c.get("units", {}).get("shares", []))
        if not len(q) or "start" not in q:
            continue
        q["start"], q["end"], q["filed"] = pd.to_datetime(q.start), pd.to_datetime(q.end), pd.to_datetime(q.filed)
        q = q[((q.end - q.start).dt.days.between(80, 100)) & (q.val > 0)]
        q = q.sort_values("filed").drop_duplicates(["start", "end"])   # first filing of each quarter
        for r in q.itertuples():
            s = so[so.filed <= r.filed]
            if not len(s):
                continue
            rows.append(dict(cik=cik, end=r.end, filed=r.filed, rep=r.val, so=s.val.iloc[-1], form=r.form, concept=k))
        if rows:
            break                                                   # first concept that exists wins
    return rows


def build():
    log = out()
    log(f"=== G13 build {pd.Timestamp.now():%Y-%m-%d %H:%M} ===")
    tk = F.company_tickers()
    rows = []
    for i, cik in enumerate(tk):
        j = facts(cik)
        if j:
            for r in events_of(cik, j):
                r["sym"] = tk[cik][0]
                rows.append(r)
        if i % 1000 == 0:
            print(f"  ciks {i}/{len(tk)} quarters {len(rows)}", flush=True)
    Q = pd.DataFrame(rows)
    Q["int"] = Q.rep / Q.so
    Q = Q[(Q.so > 0) & (Q.int < 0.5)]
    log(f"  quarters with repurchases {len(Q)}; filers {Q.cik.nunique()}; by year {Q.groupby(Q.filed.dt.year).size().to_dict()}")
    E = Q[Q.int >= THR].copy()
    bars = F.raw_bars(sorted(E.sym.unique()))
    out_rows = []
    for r in E.itertuples():
        b = bars.get(r.sym)
        if b is None or not len(b):
            continue
        b = b.sort_index(); idx = pd.DatetimeIndex(b.index)
        i = idx.searchsorted(r.filed + pd.Timedelta(days=1))
        if i < 20 or i + HOLD - 1 >= len(idx) or (idx[i] - r.filed).days > 7:
            continue
        h = b.iloc[i - 20:i]
        pc, adv = b.close.iloc[i - 1], (h.close * h.volume).mean()
        if pc < 5 or adv < 5e6:
            continue
        o = b.open.iloc[i]
        # split guard: skip if any |daily close ratio| > 1.8 or < 0.55 inside the hold (raw bars, splits not adjusted)
        seg = b.close.iloc[i - 1:i + HOLD]
        rr = (seg / seg.shift(1)).dropna()
        if ((rr > 1.8) | (rr < 0.55)).any():
            continue
        out_rows.append(dict(sym=r.sym, filed=r.filed, d=idx[i], dx=idx[i + HOLD - 1], int=r.int, o=o,
                             c=b.close.iloc[i + HOLD - 1], adv=adv))
    T = pd.DataFrame(out_rows)
    T.to_parquet(EVF)
    log(f"  events (int >= {THR:.0%}) with bars {len(T)} by year {T.groupby(T.d.dt.year).size().to_dict()}")


def select():
    from .goal_g2 import spy_adj
    from .taxable_frontier import nw_t
    log = out()
    log(f"\n=== G13 SELECT filings 2021-23 {pd.Timestamp.now():%Y-%m-%d %H:%M} (one look) ===")
    T = pd.read_parquet(EVF)
    V = T[(T.filed >= SEL[0]) & (T.filed <= SEL[1])].copy()
    S = spy_adj(); S.index = pd.DatetimeIndex(S.index)
    bars = F.raw_bars(sorted(V.sym.unique()))
    daily = {}
    for r in V.itertuples():
        b = bars[r.sym].sort_index(); b.index = pd.DatetimeIndex(b.index)
        seg = b.close.loc[r.d:r.dx]
        rs = seg.pct_change()
        rs.iloc[0] = seg.iloc[0] / r.o - 1
        cb = B.cost_bps("tier", np.array([r.o]), np.array([r.adv]))[0] / 1e4
        rs.iloc[0] -= cb; rs.iloc[-1] -= cb
        sp = S.reindex(seg.index).pct_change()
        sp.iloc[0] = S.reindex(seg.index).iloc[0] / S.loc[:r.d].iloc[-2] - 1
        daily[(r.sym, r.d)] = rs - sp
    X = pd.DataFrame(daily)                                           # days x positions, excess vs SPY
    port = X.mean(axis=1).dropna()
    mon = port.groupby(port.index.to_period("M")).apply(lambda x: (1 + x).prod() - 1)
    tr = np.array([(1 + X[c].dropna()).prod() - 1 for c in X.columns])
    log(f"  positions {X.shape[1]}, months {len(mon)}; monthly excess mean {mon.mean():+.2%} NW t {nw_t(mon, 3):+.2f} | "
        f"per-trade excess mean {tr.mean():+.2%} median {np.median(tr):+.2%} hit {(tr > 0).mean():.0%}")
    log("  by year: " + " ".join(f"{y}:{m:+.2%}" for y, m in mon.groupby(mon.index.year).mean().items()))
    ok = mon.mean() >= 0.005 and nw_t(mon, 3) >= 2
    log(f"  select gate {'PASS -> judge' if ok else 'FAIL -> dead'}")


if __name__ == "__main__":
    {"build": build, "select": select}[sys.argv[1]]()
