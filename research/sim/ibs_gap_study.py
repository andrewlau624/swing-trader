"""Round 27: Study BE — skip IBS entries indicated to open well above the prior close (09:28 indicative price).

    PYTHONPATH=. .venv/bin/python -m research.sim.ibs_gap_study fetch     # ~$1 of Databento, cached
    PYTHONPATH=. .venv/bin/python -m research.sim.ibs_gap_study

Pre-registration: research/drafts/round1_prose.md, "Round 27" (commit 24463d9, before any data).
"""
from __future__ import annotations

import dataclasses
import json
import pathlib
import sys
import time

import numpy as np
import pandas as pd

from swingtrader.config import get_env

from . import book as B
from . import data as D
from . import max_edge as M
from .auction_audit import with_rets
from .program_books import dsr
from .validate import load_sim

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/ibs_gap_study_out.txt"
CACHE = ROOT / "data/research/night/ibs_open_imbalance.parquet"
ETF_AUC = ROOT / "data/research/night/auctions_etf.json"
ET = "America/New_York"
N_TRIALS = 705


def entry_days() -> dict:
    """entry session (d+1) -> symbols bought at its open."""
    I = B.ibs_days()
    cal = list(D.etf()["close"].index)
    nxt = {a: b for a, b in zip(cal[:-1], cal[1:])}
    out = {}
    for d, legs in I.items():
        e = nxt.get(d)
        if e is not None and e >= pd.Timestamp("2018-05-01"):
            out[e] = sorted({s for s, _, _ in legs})
    return out


def fetch():
    import warnings
    import databento as db
    warnings.filterwarnings("ignore")
    c = db.Historical(get_env("DATABENTO_API_KEY"))
    meta = json.load(open(ROOT / "data/research/night/asset_meta.json"))
    ds_of = {"ARCA": "ARCX.PILLAR", "NASDAQ": "XNAS.ITCH"}
    have = pd.read_parquet(CACHE) if CACHE.exists() else pd.DataFrame(columns=["day"])
    done = set(have["day"]) if len(have) else set()
    rows = have.to_dict("records") if len(have) else []
    E = entry_days()
    t0 = time.time()
    for i, (e, syms) in enumerate(sorted(E.items())):
        if str(e.date()) in done:
            continue
        st = pd.Timestamp(f"{e.date()} 09:27:00", tz=ET).tz_convert("UTC").isoformat()
        en = pd.Timestamp(f"{e.date()} 09:29:00", tz=ET).tz_convert("UTC").isoformat()
        for ds in set(ds_of.get(meta.get(s, {}).get("exchange")) for s in syms) - {None}:
            sub = [s for s in syms if ds_of.get(meta.get(s, {}).get("exchange")) == ds]
            for k in range(4):
                try:
                    df = c.timeseries.get_range(dataset=ds, symbols=sub, schema="imbalance", start=st, end=en).to_df()
                    break
                except Exception:                                        # noqa: BLE001
                    time.sleep(3 * (k + 1)); df = pd.DataFrame()
            if df.empty:
                continue
            df = df[df.auction_type == "O"].reset_index().sort_values("ts_recv")
            for sym, g in df.groupby("symbol"):
                r = g.iloc[-1]
                px = next((float(r[f]) for f in ("ind_match_price", "cont_book_clr_price", "ref_price") if float(r[f]) > 0), np.nan)
                rows.append(dict(day=str(e.date()), sym=sym, ind=px, ts=str(r.ts_recv)))
        rows.append(dict(day=str(e.date()), sym="__done__", ind=np.nan, ts=""))
        if i % 100 == 0:
            pd.DataFrame(rows).to_parquet(CACHE)
            print(f"{i}/{len(E)} {time.time()-t0:.0f}s", flush=True)
    pd.DataFrame(rows).to_parquet(CACHE)
    print("done")


def gaps() -> dict:
    """(entry day, sym) -> indicative open / prior official close - 1 (raw prices)."""
    X = pd.read_parquet(CACHE)
    X = X[X.sym != "__done__"].dropna(subset=["ind"])
    auc = json.load(open(ETF_AUC))
    close = {}
    for s, v in auc.items():
        for x in v:
            c = x.get("c") or []
            if c:
                close[(x["d"], s)] = max(c, key=lambda q: q.get("s", 0))["p"]
    cal = [str(d.date()) for d in D.etf()["close"].index]
    prv = {b: a for a, b in zip(cal[:-1], cal[1:])}
    out = {}
    for r in X.itertuples():
        pc = close.get((prv.get(r.day), r.sym))
        if pc and pc > 0 and r.ind > 0:
            g = r.ind / pc - 1
            if abs(g) < 0.2:
                out[(pd.Timestamp(r.day), r.sym)] = g
    return out


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "fetch":
        return fetch()
    t0 = time.time()
    fh = open(OUT, "w")

    def log(*a):
        x = " ".join(str(i) for i in a)
        print(x, flush=True); fh.write(x + "\n"); fh.flush()

    log("== Round 27: Study BE (IBS entry vs 09:28 indicative gap); started", pd.Timestamp.now(), "==")
    G = gaps()
    I = B.ibs_days()
    cal = list(D.etf()["close"].index)
    nxt = {a: b for a, b in zip(cal[:-1], cal[1:])}
    rows = [(d, s, r - 2e-4, G.get((nxt.get(d), s), np.nan)) for d, legs in I.items() for s, _, r in legs]
    T = pd.DataFrame(rows, columns=["d", "sym", "net", "gap"])
    T = T[T.d >= pd.Timestamp("2018-04-30")]
    log(f"IBS entries since 2018-05: {len(T)}; with an indicative gap {T.gap.notna().mean():.1%}; "
        f"gap median {T.gap.median()*1e4:+.1f}bp, share >= +0.5% {(T.gap >= 0.005).mean():.1%}, >= +1% {(T.gap >= 0.01).mean():.1%}")
    q = T[T.d <= "2023-12-31"].gap.quantile([1 / 3, 2 / 3]).values
    for lab, a, z in (("2018-05..20", "2018-01-01", "2020-12-31"), ("2021-23", "2021-01-01", "2023-12-31"),
                      ("2024-26", "2024-01-01", "2026-12-31")):
        x = T[(T.d >= a) & (T.d <= z) & T.gap.notna()]
        b = np.digitize(x.gap, q)
        log(f"  {lab}: " + " ".join(f"T{k+1} {x.net[b == k].mean()*1e4:+6.1f}bp n{(b == k).sum()}" for k in range(3))
            + f" | gap>=0.5%: {x.net[x.gap >= 0.005].mean()*1e4:+.1f}bp n{(x.gap >= 0.005).sum()}"
            + f" | gap>=1%: {x.net[x.gap >= 0.01].mean()*1e4:+.1f}bp n{(x.gap >= 0.01).sum()}")
    s = load_sim(raw_price=True)
    s.N = with_rets(B.night_days(raw_price=True, max_corr=0.7),
                    pd.read_pickle(ROOT / "data/research/program/auction_audit_picks.pkl"), "ret_auc")
    verdict = {}
    for k, thr in (("BE1", 0.005), ("BE2", 0.01)):
        keep = lambda d, sym, thr=thr: not (G.get((nxt.get(d), sym), -1) >= thr)
        verdict[k] = []
        hold = M.unit_ibs({d: [lg for lg in legs if keep(d, lg[0])] for d, legs in I.items() if any(keep(d, lg[0]) for lg in legs)},
                          pd.Timestamp("2018-05-01"), pd.Timestamp("2020-12-31"))
        base16 = M.unit_ibs(I, pd.Timestamp("2018-05-01"), pd.Timestamp("2020-12-31"))
        log(f"\n  {k} (skip gap >= {thr:.1%}): 2018-05..20 unit IBS leg increment {(hold - base16).mean()*25200:+.2f}pp/yr")
        from .discord_ideas import replay_at
        for cost in M.COSTS:
            for bk, bp in M.BOOKS.items():
                p0 = B.Params(**{**bp, "night_cost": cost})
                log(f"   [{bk}, night {cost}/side]")
                for E in M.SIZES:
                    s.I = I
                    base = M.replay(s, E, p0)
                    r = replay_at(s, E, p0, I, keep)
                    pdd = M.p_dd50(r) if (E == 10000.0 and cost == 2.5) else None
                    ok, _ = M.judge(log, f"${E/1e3:.1f}k", r, base, judged=(cost == 2.5), pdd=pdd)
                    if cost == 2.5:
                        verdict[k].append(ok)
        s.I = I
        p0 = B.Params(**{**M.BOOKS["V7"], "night_cost": 2.5})
        base = M.replay(s, 10000.0, p0)
        r = replay_at(s, 10000.0, p0, I, keep)
        act = (r - base).mean()
        rng = np.random.default_rng(27)
        sims = []
        for _ in range(200):
            flags = {}
            for d, legs in I.items():
                f = [not keep(d, lg[0]) for lg in legs]
                perm = rng.permutation(f)
                flags.update({(d, lg[0]): bool(x) for lg, x in zip(legs, perm)})
            sims.append((replay_at(s, 10000.0, p0, I, lambda d, sym, fl=flags: not fl.get((d, sym), False)) - base).mean())
        pct = float((np.array(sims) < act).mean() * 100)
        log(f"  {k} within-day flag shuffle (200): actual {act*25200:+.2f}pp/yr, pct {pct:.0f}%; DSR {dsr(r - base, n_trials=N_TRIALS)['dsr']:.3f}")
        verdict[k].append(pct >= 95)
    log("\n######## verdicts")
    for k, v in verdict.items():
        log(f"   {k}: {sum(v)}/{len(v)} checks pass -> {'SHADOW' if all(v) else 'DEAD'}")
    log(f"\ndone {time.time()-t0:.0f}s")
    fh.close()


if __name__ == "__main__":
    main()
