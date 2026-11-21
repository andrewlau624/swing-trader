"""THIN-AUC (descriptive, NOT a gate; 2016-26 already read): N 1256 thin-band and live-band night trades re-priced
on official crosses (entry = T closing cross, exit = T+1 opening cross), Alpaca SIP /v2/stocks/auctions.

    OMP_NUM_THREADS=3 PYTHONPATH=. python3 -m research.sim.exp_thinauc        # fetch is resumable

Trades: exp_thinnight.collect (nx.collect_trades, primary, adv_band [2M,10M) and the live [10M, inf)), 2016-01..2026-10-05.
Cross parsing: pref_noauc.day_table (close = largest '6' print, else largest close print; open = largest opening print).
Question: on real crosses, does the thin band beat the live band per dollar?
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS",
           "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "3")

import json
import re
import pathlib
import time

import numpy as np
import pandas as pd
import requests

from research.sim import nx
from .auction_fetch import _env, fetch
from .exp_thinnight import collect
from .pref_noauc import day_table

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data/research/thin_auc"
OUT = pathlib.Path(__file__).resolve().parent / "exp_thinauc_out.txt"
LO, HI = "2016-01-01", "2026-10-05"
ADV_B = [(2e6, 4e6), (4e6, 7e6), (7e6, 1e7), (1e7, 5e7), (5e7, np.inf)]
PX_B = [(0, 10), (10, 20), (20, np.inf)]

L: list[str] = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    L.append(s)
    OUT.write_text("\n".join(L) + "\n")


def trades() -> dict:
    D.mkdir(parents=True, exist_ok=True)
    f = {k: D / f"trades_{k}.parquet" for k in ("thin", "live")}
    if all(p.exists() for p in f.values()):
        return {k: pd.read_parquet(p) for k, p in f.items()}
    master = nx.load_master(nx.Paths())
    act = pd.read_parquet(nx.store_dir() / "actions.parquet", columns=["date", "action", "ticker", "value"])
    act["date"] = pd.to_datetime(act["date"])
    tr, _ = collect(LO, HI, master, act)
    for k, p in f.items():
        tr[k].to_parquet(p)
    return tr


def alp(tk: str) -> str:
    """Sharadar suffixes a reused/retired ticker with digits (XONE1, CZR2); the as-traded symbol is the stem."""
    return re.sub(r"\d+$", "", tk)


def safe_fetch(syms, a, e, H) -> dict:
    """auction_fetch.fetch; on a 400 (symbol the API rejects) split the batch and drop the bad symbols."""
    try:
        return fetch(syms, a, e, H)
    except requests.HTTPError as ex:
        if ex.response is None or ex.response.status_code != 400:
            raise
        if len(syms) == 1:
            return {}
        h = len(syms) // 2
        return {**safe_fetch(syms[:h], a, e, H), **safe_fetch(syms[h:], a, e, H)}


def grab(tr: pd.DataFrame, band: str) -> None:
    (D / "x" / band).mkdir(parents=True, exist_ok=True)
    H, t0 = _env(), time.time()
    grp = list(tr.groupby("date"))
    for i, (d, x) in enumerate(grp):
        f = D / "x" / band / f"{pd.Timestamp(d).date()}.json"
        if f.exists():
            continue
        syms, rows = sorted({alp(t) for t in x.ticker}), {}
        e = str(pd.Timestamp(x.nxt.max()).date())
        for k in range(0, len(syms), 100):
            rows.update(safe_fetch(syms[k:k + 100], str(pd.Timestamp(d).date()), e, H))
        json.dump(rows, open(f, "w"))
        time.sleep(0.2)
        if i % 200 == 0:
            print(f"fetch {i}/{len(grp)} {time.time() - t0:.0f}s", flush=True)


def price(tr: pd.DataFrame, band: str) -> pd.DataFrame:
    c0x, o1x, six = np.full(len(tr), np.nan), np.full(len(tr), np.nan), np.zeros(len(tr), bool)
    for d, x in tr.groupby("date"):
        f = D / "x" / band / f"{pd.Timestamp(d).date()}.json"
        if not f.exists():
            continue
        j = json.load(open(f))
        for k, r in zip(x.index, x.itertuples()):
            sym = alp(r.ticker)
            if sym not in j:
                continue
            t = day_table(j[sym])
            d0, d1 = pd.Timestamp(r.date), pd.Timestamp(r.nxt)
            if d0 in t.index:
                c0x[k] = t.loc[d0, "cp"]; six[k] = bool(t.loc[d0, "auc"])
            if d1 in t.index:
                o1x[k] = t.loc[d1, "op"]
    tr = tr.assign(c0x=c0x, o1x=o1x, six=six)
    with np.errstate(invalid="ignore", divide="ignore"):
        tr["divp"] = tr.ret - (tr.o1u / tr.cu - 1)                       # ex-dividend part of the NX outcome
        tr["gx"] = tr.o1x / tr.c0x - 1 + tr.divp                          # gross on crosses
        tr["gap_in"] = (tr.cu / tr.c0x - 1) * 1e4                         # Sharadar close vs closing cross
        tr["gap_out"] = (tr.o1u / tr.o1x - 1) * 1e4                       # Sharadar open vs opening cross
    tr["both"] = np.isfinite(tr.gx) & (tr.kind == "open")
    return tr


def bucket_lines(x: pd.DataFrame, col: str, edges, lab) -> list[str]:
    out = []
    for a, b in edges:
        g = x[(x[col] >= a) & (x[col] < b)]
        if len(g):
            out.append(f"    {lab(a, b):>10}: n {len(g):5d} | entry gap med {g.gap_in.median():+6.1f}bp mean|.| {g.gap_in.abs().mean():6.1f} "
                       f"p90|.| {g.gap_in.abs().quantile(.9):6.1f} | exit gap med {g.gap_out.median():+6.1f} mean|.| {g.gap_out.abs().mean():6.1f} "
                       f"p90|.| {g.gap_out.abs().quantile(.9):6.1f} | gross Sharadar {g.ret.mean() * 1e4:+6.1f} cross {g.gx.mean() * 1e4:+6.1f}bp")
    return out


def tday(s: pd.Series) -> float:
    return float(s.mean() / s.std(ddof=1) * np.sqrt(len(s))) if len(s) > 2 and s.std() > 0 else float("nan")


def main():
    tr = trades()
    for k in tr:
        grab(tr[k], k)
    say("THIN-AUC (descriptive, NOT a gate): N 1256 thin [$2M,$10M) and live [$10M,inf) night trades on official crosses, "
        f"{LO}..{HI}; entry T closing cross, exit T+1 opening cross (Alpaca SIP auctions; pref_noauc.day_table parsing)")
    P = {k: price(v, k) for k, v in tr.items()}
    allnights = pd.DatetimeIndex(sorted(set(P["thin"].date) | set(P["live"].date)))
    for k, x in P.items():
        say(f"\n=== {k} band: {len(x)} trades on {x.date.nunique()} nights")
        say(f"  coverage: both crosses {x.both.mean():.1%} (close cross {np.isfinite(x.c0x).mean():.1%}, open cross {np.isfinite(x.o1x).mean():.1%}); "
            f"official '6' closing print {x.six[np.isfinite(x.c0x)].mean():.1%} of closes found; non-open NX outcomes {int((x.kind != 'open').sum())}")
        m = x[x.both]
        miss = x[~x.both & (x.kind == "open")]
        say(f"  selection check: Sharadar gross on covered {m.ret.mean() * 1e4:+.1f}bp vs uncovered {miss.ret.mean() * 1e4:+.1f}bp (n {len(miss)}); "
            f"uncovered median ADV ${miss.adv.median() / 1e6:.1f}M vs covered ${m.adv.median() / 1e6:.1f}M")
        say("  Sharadar vs cross by ADV ($M):")
        for s in bucket_lines(m, "adv", ADV_B, lambda a, b: f"{a / 1e6:.0f}-{'inf' if b == np.inf else f'{b / 1e6:.0f}'}"):
            say(s)
        say("  Sharadar vs cross by price ($):")
        for s in bucket_lines(m, "cu", PX_B, lambda a, b: f"{a:.0f}-{'inf' if b == np.inf else f'{b:.0f}'}"):
            say(s)
        for nm, gcol in (("entry", "gap_in"), ("exit", "gap_out")):
            ga = m[gcol].abs()
            say(f"  {nm} gap tails: |gap|>1bp {(ga > 1).mean():.1%}, >25bp {(ga > 25).mean():.1%}, >100bp {(ga > 100).mean():.1%}, >500bp {(ga > 500).mean():.2%}")
        mt = m[(m.gap_in.abs() <= 500) & (m.gap_out.abs() <= 500)]
        say(f"  trimmed (both |gaps| <= 500bp, n {len(mt)}): gross on crosses {mt.gx.mean() * 1e4:+.1f}bp vs Sharadar {mt.ret.mean() * 1e4:+.1f}; "
            f"the {len(m) - len(mt)} dropped trades: crosses {m.drop(mt.index).gx.mean() * 1e4:+.0f} Sharadar {m.drop(mt.index).ret.mean() * 1e4:+.0f}bp")
        say(f"  per trade (covered, n {len(m)}): gross on crosses mean {m.gx.mean() * 1e4:+.1f}bp median {m.gx.median() * 1e4:+.1f} hit {(m.gx > 0).mean():.2f}; "
            f"Sharadar same trades mean {m.ret.mean() * 1e4:+.1f} median {m.ret.median() * 1e4:+.1f}")
        w = m.per
        for c in (0, 5, 10):
            net = m.gx - 2 * c / 1e4
            leg = (w * net).groupby(m.date).sum().reindex(allnights, fill_value=0.0)
            pdol = (w * net).groupby(m.date).sum() / w.groupby(m.date).sum()      # return per $ deployed, per traded night
            srt = np.sort(leg.to_numpy())
            say(f"  at {c:2d}bp/side: per trade mean {net.mean() * 1e4:+6.1f}bp med {net.median() * 1e4:+6.1f} | per $ deployed (traded nights) "
                f"{pdol.mean() * 1e4:+6.1f}bp t {tday(pdol):+5.2f} | leg/night (NX weights, all {len(allnights)} nights) {leg.mean() * 1e4:+5.2f}bp "
                f"t {tday(leg):+5.2f} ex-top5 {srt[:-5].mean() * 1e4:+5.2f}")
        yr = m.assign(y=m.date.dt.year).groupby("y").gx.mean() * 1e4
        say("  per-trade gross on crosses by year: " + " ".join(f"{y % 100:02d}:{v:+.0f}" for y, v in yr.items()))
    t, l = P["thin"][P["thin"].both], P["live"][P["live"].both]
    for c in (0, 5, 10):
        d = (t.gx.mean() - l.gx.mean()) * 1e4
        se = np.sqrt(t.groupby("date").gx.mean().var() / t.date.nunique() + l.groupby("date").gx.mean().var() / l.date.nunique()) * 1e4
        say(f"\nANSWER at {c}bp/side both bands: thin - live per trade {d:+.1f}bp (approx se {se:.1f}); thin {(t.gx.mean() - 2 * c / 1e4) * 1e4:+.1f} vs live "
            f"{(l.gx.mean() - 2 * c / 1e4) * 1e4:+.1f}bp per $ per trade")


if __name__ == "__main__":
    main()
