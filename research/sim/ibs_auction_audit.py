"""IBS leg on official opening crosses (Round 19 follow-up to Study AW; report, no N).

    PYTHONPATH=. .venv/bin/python -m research.sim.ibs_auction_audit

The IBS leg is bought at the open d+1 and sold at the open d+2 (vendor daily opens). Fetch the 18
ETFs' official opening crosses (Alpaca /v2/stocks/auctions, SIP; cached in
data/research/night/auctions_etf.json) and restate the unit leg and the books (returns only: sizing keeps the vendor price,
because vendor ETF opens are dividend-adjusted and the crosses are raw).
"""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pandas as pd

from . import book as B
from . import max_edge as M
from .auction_audit import with_rets
from .auction_fetch import _env, fetch
from .validate import load_sim

ROOT = pathlib.Path(__file__).resolve().parents[2]
CACHE = ROOT / "data/research/night/auctions_etf.json"
OUT = ROOT / "data/research/program/ibs_auction_audit_out.txt"


def opens():
    if not CACHE.exists():
        H = _env(); rows = {}
        for y in range(2016, 2027):
            got = fetch(B.EQ18, f"{y}-01-01", min(f"{y}-12-31", "2026-09-30"), H)
            for s, v in got.items():
                rows.setdefault(s, []).extend(v)
        json.dump(rows, open(CACHE, "w"))
    rows = json.load(open(CACHE))
    out = {}
    for s, v in rows.items():
        for x in v:
            o = x.get("o") or []
            if o:
                out[(pd.Timestamp(x["d"]), s)] = max(o, key=lambda q: q.get("s", 0))["p"]
    return out


def main():
    f = open(OUT, "w")

    def log(x=""):
        print(x, flush=True); f.write(x + "\n"); f.flush()

    OA = opens()
    O = B.D.etf()["open"]; days = O.index
    nxt = {a: b for a, b in zip(days[:-1], days[1:])}
    I = B.ibs_days()
    Ia, diffs, miss = {}, [], 0
    for d, legs in I.items():
        d1 = nxt.get(d); d2 = nxt.get(d1) if d1 is not None else None
        new = []
        for s, o1, r in legs:
            a1, a2 = OA.get((d1, s)), OA.get((d2, s))
            if a1 and a2 and abs(a2 / a1 - 1 - r) < 0.2:
                new.append((s, o1, a2 / a1 - 1)); diffs.append((d, s, (a2 / a1 - 1 - r) * 1e4))
            else:
                new.append((s, o1, r)); miss += 1
        Ia[d] = new
    D = pd.DataFrame(diffs, columns=["d", "s", "dret_bp"])
    log(f"IBS legs {sum(len(v) for v in I.values())}, both crosses found {len(D)}, kept vendor {miss}")
    for lab, a, z in (("2016-20", "2016", "2020"), ("2021-23", "2021", "2023"), ("2024-26", "2024", "2026")):
        x = D[(D.d >= a) & (D.d <= z + "-12-31")]
        log(f"  {lab}: n {len(x)}  leg ret diff (cross - vendor) mean {x.dret_bp.mean():+.2f}bp "
            f"median {x.dret_bp.median():+.2f}  share |diff| > 5bp {(x.dret_bp.abs() > 5).mean():.0%}")
    for s_, g in D.groupby("s"):
        if abs(g.dret_bp.mean()) > 1:
            log(f"    {s_}: n {len(g)} mean diff {g.dret_bp.mean():+.1f}bp")
    s = load_sim(raw_price=True)
    N0 = B.night_days(raw_price=True, max_corr=0.7)
    Na = with_rets(N0, pd.read_pickle(ROOT / "data/research/program/auction_audit_picks.pkl"), "ret_auc")
    for bk in ("V7", "Roth"):
        p = B.Params(**{**M.BOOKS[bk], "night_cost": 2.5})
        line = []
        for E in M.SIZES:
            s.N, s.I = N0, I; v = B.stats(M.replay(s, E, p))[0]
            s.N, s.I = Na, Ia; a = B.stats(M.replay(s, E, p))[0]
            line.append(f"${E/1e3:.1f}k {v*100:.1f} -> {a*100:.1f}")
        log(f"  [{bk}, 2.5bp/side] vendor -> night AND IBS on crosses: " + " | ".join(line))
    f.close()


if __name__ == "__main__":
    main()
