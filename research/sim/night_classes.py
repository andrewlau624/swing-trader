"""Study U: where the night leg's edge lives (ETP / operating live / operating gone / unmapped).

    PYTHONPATH=. .venv/bin/python -m research.sim.night_classes

Pre-registration: research/drafts/round1_prose.md, "Round 7" (commit 874c815). Needs Study T's
EDGAR cache (`night_filings fetch`). OPER-GONE and UNMAPPED use today's ticker index and
last-filing dates: lookahead, report only. U1 (drop ETPs) / U2 (ETPs only) are the rules.
"""
from __future__ import annotations

import json
import pickle
import time

import numpy as np
import pandas as pd

from . import book as B
from .night_filings import CACHE, FULL, PER, PERIODIC, ROOT
from .night_short import nw_t

OUT = ROOT / "data/research/program/night_classes_out.txt"
GONE_BEFORE = pd.Timestamp("2026-03-01", tz="UTC")
N_PLACEBO = 200


def classify(mp: dict) -> dict:
    """symbol -> class, from the cached EDGAR submissions."""
    out = {}
    for sym, c in mp.items():
        if not c:
            out[sym] = ("UNMAPPED", None)
            continue
        f = CACHE / f"{int(c):010d}.pkl"
        if not f.exists():
            out[sym] = ("UNMAPPED", None)
            continue
        s = pickle.load(open(f, "rb"))
        fl = s["filings"]
        t = pd.to_datetime(fl.acceptanceDateTime, utc=True, errors="coerce")
        n424 = (fl.form.str.startswith("424B") & (t >= "2021-01-01")).sum() / 5.75
        if s["entityType"] != "operating" or s.get("sic") == "6221" or n424 > 100:
            out[sym] = ("ETP", None)
            continue
        last = t[fl.form.isin(PERIODIC)].max()
        out[sym] = ("OPER-LIVE", last) if pd.notna(last) and last >= GONE_BEFORE \
            else ("OPER-GONE", last)
    return out


def main():
    t0 = time.time()
    fs = open(OUT, "w")

    def log(*a):
        s_ = " ".join(str(x) for x in a)
        print(s_, flush=True)
        fs.write(s_ + "\n")
        fs.flush()

    log("== Study U: where the night leg's edge lives, started", pd.Timestamp.now(), "\n")
    N = B.night_days(raw_price=True, max_corr=0.7)
    cls = classify(json.loads((CACHE / "ticker_cik.json").read_text()))
    rows = [dict(d=pd.Timestamp(d), sym=s, ret=nd.ret[j], price=nd.price[j], adv=nd.adv[j],
                 w=min(nd.frac, 0.10), cls=cls.get(s, ("UNMAPPED", None))[0],
                 last=cls.get(s, (None, None))[1])
            for d, nd in N.items() for j, s in enumerate(nd.syms)]
    T = pd.DataFrame(rows)
    T = T[(T.d >= FULL[0]) & (T.d <= FULL[1])].reset_index(drop=True)
    sess = B.D.returns20().index
    alld = sess[(sess >= FULL[0]) & (sess <= FULL[1])]
    classes = ["ETP", "OPER-LIVE", "OPER-GONE", "UNMAPPED"]
    rng = np.random.default_rng(5)
    verdict = {}

    for cost in ("tier", "tier_hi"):
        T["net"] = T.ret - 2 * B.cost_bps(cost, T.price.values, T.adv.values) / 1e4
        T["pnl"] = 0.5 * T.w * T.net
        log(f"## cost {cost}")
        log(f"{'class':10s} {'n':>5s} {'share':>6s} | {'net bp 21-23':>12s} {'24-26':>7s} {'all':>7s}"
            f" | {'% of leg P&L 21-23':>18s} {'24-26':>7s}")
        for c in classes + ["ALL"]:
            m = T if c == "ALL" else T[T.cls == c]
            hs = [m[(m.d >= a) & (m.d <= b)] for _, a, b in PER]
            tot = [T[(T.d >= a) & (T.d <= b)].pnl.sum() for _, a, b in PER]
            log(f"{c:10s} {len(m):5d} {len(m) / len(T):6.1%} | {hs[0].net.mean() * 1e4:+12.1f} "
                f"{hs[1].net.mean() * 1e4:+7.1f} {m.net.mean() * 1e4:+7.1f} | "
                f"{hs[0].pnl.sum() / tot[0] * 100:+17.0f}% {hs[1].pnl.sum() / tot[1] * 100:+6.0f}%")
        if cost == "tier":
            g = T[T.cls == "OPER-GONE"]
            gap = (pd.to_datetime(g["last"]).dt.tz_localize(None) - g.d).dt.days
            log(f"  OPER-GONE: median {gap.median():.0f} calendar days from the pick to the last "
                f"periodic filing (p25 {gap.quantile(.25):.0f}, p75 {gap.quantile(.75):.0f})")

        def inc(keep):
            return (T.pnl * keep).groupby(T.d).sum().reindex(alld).fillna(0)
        base = inc(np.ones(len(T)))
        isetp = (T.cls == "ETP").values
        by_night = T.groupby("d").indices
        for name, keep in (("U1 drop ETP", ~isetp), ("U2 ETP only", isetp)):
            diff = inc(keep.astype(float)) - base
            yr = [diff[a:b].sum() / (len(diff[a:b]) / 252) * 100 for _, a, b in PER]
            t = nw_t(diff.values)
            # placebo: drop the same number of picks at random within each night
            real = diff.sum()
            draws = np.empty(N_PLACEBO)
            for k in range(N_PLACEBO):
                kp = np.ones(len(T))
                for ix in by_night.values():
                    nd_ = int((~keep[ix]).sum())
                    if nd_:
                        kp[rng.choice(ix, nd_, replace=False)] = 0
                draws[k] = (inc(kp) - base).sum()
            pct = (draws < real).mean() * 100
            ok = all(y > 0 for y in yr) and t >= 2.0 and pct >= 95
            verdict.setdefault(name, []).append(ok)
            log(f"  {name:12s} vs baseline pp/yr 2021-23 {yr[0]:+.2f}  2024-26 {yr[1]:+.2f}  "
                f"NW t {t:+.2f}  placebo pct {pct:.0f}  {'PASS' if ok else ''}")
        log("")

    log("## verdict (pass at tier AND tier_hi)")
    for k, v in verdict.items():
        log(f"  {k:12s} {'PASS' if all(v) else 'fail'}")
    log(f"\ndone in {time.time() - t0:4.0f} s")


if __name__ == "__main__":
    main()
