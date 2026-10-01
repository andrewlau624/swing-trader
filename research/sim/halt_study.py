"""Round 28: Study BF — night picks that LULD-halted that day (the lab's halt rule), dropped (BF1) or halved (BF2).

    PYTHONPATH=. .venv/bin/python -m research.sim.halt_study fetch     # free Alpaca SIP minute bars, cached
    PYTHONPATH=. .venv/bin/python -m research.sim.halt_study

Pre-registration: research/drafts/round1_prose.md, "Round 28" (commit 214b606, before any minute bar).
"""
from __future__ import annotations

import dataclasses
import pathlib
import sys
import time

import numpy as np
import pandas as pd
import requests

from swingtrader.daily import signals as sg

from . import book as B
from . import max_edge as M
from .auction_audit import with_rets
from .auction_fetch import _env
from .imbalance_study import drop_tilt
from .program_books import dsr
from .validate import load_sim

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/halt_study_out.txt"
BARS = ROOT / "data/research/night/pick_minutes"
ET = "America/New_York"
N_TRIALS = 719


def halt_flags(minutes: list[int], closes: list[float], move=0.05, window=5, silent=5, lag=2) -> tuple[bool, bool]:
    """(any halt, down halt) from one symbol's bars: minute index 0..379 (09:30=0) and closes, sorted.
    A halt = >= `silent` consecutive minutes with no bar, starting within `lag` minutes after a `window`-minute
    move of >= `move` (close vs the close `window` minutes earlier among the bars present)."""
    if len(minutes) < window + 1:
        return False, False
    m = np.asarray(minutes); c = np.asarray(closes, float)
    present = dict(zip(m.tolist(), c.tolist()))
    any_h = down_h = False
    for i in range(len(m) - 1):
        gap = m[i + 1] - m[i] - 1                      # empty minutes after bar i
        if gap < silent:
            continue
        t = m[i]
        for k in range(0, lag + 1):                    # the window ended at t-k
            end = t - k
            st = end - window
            if end in present and st in present and present[st] > 0:
                r = present[end] / present[st] - 1
                if abs(r) >= move:
                    any_h = True
                    down_h = down_h or r < 0
                    break
    return any_h, down_h


def fetch():
    H = _env()
    BARS.mkdir(parents=True, exist_ok=True)
    N = B.night_days(raw_price=True, max_corr=0.7)
    t0 = time.time()
    for i, (d, nd) in enumerate(sorted(N.items())):
        f = BARS / f"{d.date()}.parquet"
        if f.exists():
            continue
        syms = sorted({str(s) for s in nd.syms})
        st = pd.Timestamp(f"{d.date()} 09:30", tz=ET).tz_convert("UTC").isoformat()
        en = pd.Timestamp(f"{d.date()} 15:50", tz=ET).tz_convert("UTC").isoformat()
        rows, tok = [], None
        while True:
            q = {"symbols": ",".join(syms), "timeframe": "1Min", "start": st, "end": en, "feed": "sip",
                 "limit": 10000, "adjustment": "raw"}
            if tok:
                q["page_token"] = tok
            for k in range(5):
                r = requests.get("https://data.alpaca.markets/v2/stocks/bars", params=q, headers=H, timeout=30)
                if r.status_code == 429:
                    time.sleep(5 * (k + 1)); continue
                r.raise_for_status(); break
            j = r.json()
            for s, v in (j.get("bars") or {}).items():
                rows += [(s, b["t"], b["c"]) for b in v]
            tok = j.get("next_page_token")
            if not tok:
                break
        pd.DataFrame(rows, columns=["sym", "t", "c"]).to_parquet(f)
        time.sleep(0.25)
        if i % 100 == 0:
            print(f"{i}/{len(N)} {time.time()-t0:.0f}s", flush=True)
    print("done", f"{time.time()-t0:.0f}s")


def flags_all(N) -> dict:
    out = {}
    for d, nd in N.items():
        f = BARS / f"{d.date()}.parquet"
        if not f.exists():
            continue
        X = pd.read_parquet(f)
        if X.empty:
            continue
        t = pd.to_datetime(X.t, utc=True).dt.tz_convert(ET)
        X = X.assign(m=(t.dt.hour * 60 + t.dt.minute - 570)).sort_values("m")
        for s, g in X.groupby("sym"):
            out[(d, s)] = halt_flags(g.m.tolist(), g.c.tolist())
    return out


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "fetch":
        return fetch()
    t0 = time.time()
    fh = open(OUT, "w")

    def log(*a):
        x = " ".join(str(i) for i in a)
        print(x, flush=True); fh.write(x + "\n"); fh.flush()

    log("== Round 28: Study BF (halted night picks); started", pd.Timestamp.now(), "==")
    s = load_sim(raw_price=True)
    N0 = B.night_days(raw_price=True, max_corr=0.7)
    Na = with_rets(N0, pd.read_pickle(ROOT / "data/research/program/auction_audit_picks.pkl"), "ret_auc")
    s.N = Na; s.I = B.ibs_days()
    Fl = flags_all(N0)
    Fau = M.au_features(N0)
    rows = []
    for d, nd in Na.items():
        for j, sym in enumerate(map(str, nd.syms)):
            h, dn = Fl.get((d, sym), (False, False))
            rows.append(dict(d=d, sym=sym, halt=h, down=dn, has=(d, sym) in Fl, net=nd.ret[j] - 5e-4,
                             depth=nd.day_ret[j], vol20=nd.vol20[j], tow=Fau[(d, sym)][1]))
    A = pd.DataFrame(rows)
    log(f"picks {len(A)}; with minute bars {A.has.mean():.1%}; halted {A.halt.mean():.1%} (down {A.down.mean():.1%})")
    for lab, a, z in (("2021-23", "2021-01-01", "2023-12-31"), ("2024-26", "2024-01-01", "2026-12-31")):
        x = A[(A.d >= a) & (A.d <= z)]
        h, n = x[x.halt], x[~x.halt]
        tt = (h.net.mean() - n.net.mean()) / np.sqrt(h.net.var() / max(len(h), 1) + n.net.var() / len(n)) if len(h) > 1 else np.nan
        log(f"  {lab}: halted {h.net.mean()*1e4:+6.1f}bp n{len(h)} | down-halt {x[x.down].net.mean()*1e4:+6.1f}bp "
            f"n{int(x.down.sum())} | not halted {n.net.mean()*1e4:+6.1f}bp n{len(n)} | diff t {tt:+.2f}")
    log("  Spearman halt: " + "  ".join(f"{k} {v:+.2f}" for k, v in
                                        A[["halt", "depth", "vol20", "tow"]].astype(float).corr(method="spearman")["halt"].drop("halt").items()))
    flags = {(r.d, r.sym): bool(r.halt) for r in A.itertuples()}
    date_of = {id(nd): d for d, nd in Na.items()}

    def half_tilt(fl):
        def f(nd):
            d = date_of[id(nd)]
            live = sg.night_tilt(nd.vol20, nd.day_ret, 0.25)
            return np.array([w * (0.5 if fl.get((d, str(sy)), False) else 1.0) for sy, w in zip(nd.syms, live)])
        return f

    verdict = {"BF1": [], "BF2": []}
    mk = {"BF1": lambda fl: drop_tilt(Na, fl), "BF2": half_tilt}
    for cost in M.COSTS:
        for bk, bp in M.BOOKS.items():
            p0 = B.Params(**{**bp, "night_cost": cost})
            log(f"\n  [{bk}, night {cost}/side]  full CAGR/Sh/DD")
            for E in M.SIZES:
                base = M.replay(s, E, p0); sb = B.stats(base)
                log(f"   ${E/1e3:5.1f}k shipped    {sb[0]*100:5.1f}/{sb[1]:4.2f}/{sb[2]*100:4.0f}")
                for k in ("BF1", "BF2"):
                    r = M.replay(s, E, dataclasses.replace(p0, tilt=mk[k](flags)))
                    pdd = M.p_dd50(r) if (E == 10000.0 and cost == 2.5) else None
                    ok, _ = M.judge(log, k, r, base, judged=(cost == 2.5), pdd=pdd)
                    if cost == 2.5:
                        verdict[k].append(ok)
    p0 = B.Params(**{**M.BOOKS["V7"], "night_cost": 2.5})
    base = M.replay(s, 10000.0, p0)
    rng = np.random.default_rng(28)
    by = {}
    for (d, sym), f in flags.items():
        by.setdefault(d, []).append((sym, f))
    for k in ("BF1", "BF2"):
        r = M.replay(s, 10000.0, dataclasses.replace(p0, tilt=mk[k](flags)))
        act = (r - base).mean()
        sims = []
        for _ in range(200):
            sh = {}
            for d, v in by.items():
                perm = rng.permutation([f for _, f in v])
                sh.update({(d, sym): bool(p) for (sym, _), p in zip(v, perm)})
            sims.append((M.replay(s, 10000.0, dataclasses.replace(p0, tilt=mk[k](sh))) - base).mean())
        pct = float((np.array(sims) < act).mean() * 100)
        log(f"  {k} within-night flag shuffle (200): actual {act*25200:+.2f}pp/yr, pct {pct:.0f}%; "
            f"DSR at N {N_TRIALS} {dsr(r - base, n_trials=N_TRIALS)['dsr']:.3f}")
        verdict[k].append(pct >= 95)
    log("\n######## verdicts")
    for k, v in verdict.items():
        log(f"   {k}: {sum(v)}/{len(v)} checks pass -> {'SHADOW' if all(v) else 'DEAD'}")
    log(f"\ndone {time.time()-t0:.0f}s")
    fh.close()


if __name__ == "__main__":
    main()
