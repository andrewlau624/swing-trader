"""IBS-AUC (descriptive, NOT a gate): the live IBS leg's trades (research/sim/ibs_oos._trades, EQ18, IBS<0.2, buy open(d+1),
sell open(d+2)) re-priced on official opening crosses (Alpaca SIP /v2/stocks/auctions).

    OMP_NUM_THREADS=3 PYTHONPATH=. python3 -m research.sim.exp_ibsauc        # fetch is resumable

Vendor opens = research/sim/data.etf() = data/research/night/etf_daily.parquet (Alpaca SIP daily bars, raw prices),
so the gap measured here is also the answer to "is the Alpaca daily-bar open the opening cross?".
Cross parsing: pref_noauc.day_table (open = the largest opening-auction print).
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "3")

import json
import pathlib
import time

import numpy as np
import pandas as pd

from . import data as D
from .auction_fetch import _env, fetch
from .ibs_oos import _trades
from .pref_noauc import day_table

ROOT = pathlib.Path(__file__).resolve().parents[2]
CACHE = ROOT / "data/research/ibs_auc"
OUT = pathlib.Path(__file__).resolve().parent / "exp_ibsauc_out.txt"
LO, HI = "2016-01-01", "2026-10-31"
RECORDED_OOS = 29.8        # bp, data/research/program/ibs_oos_out.txt / CLAUDE.md


def trades() -> pd.DataFrame:
    r = _trades("ibs_lo").reset_index()
    days = D.etf()["open"].index
    j = np.searchsorted(days, r.date.to_numpy())
    O = D.etf()["open"]
    r["d1"], r["d2"] = days[j + 1], days[j + 2]
    r["o1"] = [O.at[a, s] for a, s in zip(r.d1, r.sym)]
    r["o2"] = [O.at[a, s] for a, s in zip(r.d2, r.sym)]
    assert np.allclose(r.o2 / r.o1 - 1, r.ret), "reconstructed opens do not reproduce ibs_oos returns"
    return r[(r.date >= LO) & (r.date <= HI)].reset_index(drop=True)


def grab(r: pd.DataFrame) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    H, t0 = _env(), time.time()
    grp = list(r.groupby("date"))
    for i, (d, x) in enumerate(grp):
        f = CACHE / f"{pd.Timestamp(d).date()}.json"
        if f.exists():
            continue
        json.dump(fetch(sorted(set(x.sym)), str(x.d1.min().date()), str(x.d2.max().date()), H), open(f, "w"))
        time.sleep(0.2)
        if i % 200 == 0:
            print(f"fetch {i}/{len(grp)} {time.time() - t0:.0f}s", flush=True)


def divs(syms, action="dividend") -> dict:
    """Cash dividends (or split ratios, new/old shares) by (symbol, ex-date) from the Sharadar store's actions table."""
    from . import nx
    a = pd.read_parquet(nx.store_dir() / "actions.parquet", columns=["date", "action", "ticker", "value"])
    a = a[(a.action == action) & a.ticker.isin(syms)]
    return {(t, pd.Timestamp(d)): float(v) for t, d, v in zip(a.ticker, a.date, a.value)}


def crosses(r: pd.DataFrame) -> pd.DataFrame:
    x1, x2, s1, s2, c1, c2 = (np.full(len(r), np.nan) for _ in range(6))
    for d, g in r.groupby("date"):
        j = json.load(open(CACHE / f"{pd.Timestamp(d).date()}.json"))
        for k, row in zip(g.index, g.itertuples()):
            if row.sym not in j:
                continue
            t = day_table(j[row.sym])
            opn = {pd.Timestamp(e["d"]): max(e["o"], key=lambda p: p.get("s", 0)) for e in j[row.sym] if e.get("o")}
            if row.d1 in t.index:
                x1[k] = t.loc[row.d1, "op"]; c1[k] = t.loc[row.d1, "cp"]; s1[k] = opn[row.d1]["s"] if row.d1 in opn else np.nan
            if row.d2 in t.index:
                x2[k] = t.loc[row.d2, "op"]; c2[k] = t.loc[row.d2, "cp"]; s2[k] = opn[row.d2]["s"] if row.d2 in opn else np.nan
    r = r.assign(x1=x1, x2=x2, xs1=s1, xs2=s2, xc1=c1, xc2=c2)
    # etf_daily is Alpaca adjustment="all" (SPY 2016-01-04 close 170.68 vs raw 201.02): vendor = f(d) x raw, f steps at
    # ex-dates/splits. Factor-free comparisons: (1) the cross return made total-return with the ex-dividend on d2;
    # (2) the open gap after removing f(d) estimated as vendor close / closing cross on the same day.
    C = D.etf()["close"]
    r["vc1"] = [C.at[a, s] for a, s in zip(r.d1, r.sym)]
    r["vc2"] = [C.at[a, s] for a, s in zip(r.d2, r.sym)]
    dv = divs(sorted(set(r.sym)))
    r["div"] = [dv.get((s, a), 0.0) for s, a in zip(r.sym, r.d2)]
    sp = divs(sorted(set(r.sym)), "split")
    r["split"] = [sp.get((s, a), 1.0) for s, a in zip(r.sym, r.d2)]          # raw cross after a split on d2 -> pre-split basis
    r["gx_raw"] = r.x2 * r.split / r.x1 - 1
    r["gx"] = (r.x2 + r["div"]) * r.split / r.x1 - 1
    r["gap1"] = (r.o1 / (r.vc1 / r.xc1) / r.x1 - 1) * 1e4
    r["gap2"] = (r.o2 / (r.vc2 / r.xc2) / r.x2 - 1) * 1e4
    r["fac"] = (r.vc1 / r.xc1)
    r["both"] = np.isfinite(r.gx)
    return r


def dist(g: pd.Series) -> str:
    a = g.abs()
    q = g.quantile([.01, .05, .25, .5, .75, .95, .99])
    return (f"mean {g.mean():+.2f}bp | " + " ".join(f"p{int(k * 100)} {v:+.1f}" for k, v in q.items()) +
            f" | |gap|=0 {(a < 0.01).mean():.1%}, >1bp {(a > 1).mean():.1%}, >5bp {(a > 5).mean():.1%}, >25bp {(a > 25).mean():.1%}")


def stat(x: pd.Series) -> str:
    x = x.dropna()
    t = x.mean() / x.std() * np.sqrt(len(x)) if len(x) > 2 else np.nan
    s = np.sort(x.to_numpy())
    return (f"n {len(x):4d} mean {x.mean() * 1e4:+6.1f}bp med {x.median() * 1e4:+6.1f} t {t:+5.2f} hit {(x > 0).mean():.0%} "
            f"ex-top5 {s[:-5].mean() * 1e4:+6.1f}")


def main():
    r = trades()
    grab(r)
    r = crosses(r)
    L = [f"IBS-AUC (descriptive, NOT a gate): live IBS rule (ibs_oos._trades: EQ18 top-3 12-1 momentum, IBS<0.2, open(d+1) -> open(d+2)),"
         f" {len(r)} trades {r.date.min().date()}..{r.date.max().date()} (first trade needs 260 sessions of history; data start 2016-01-04)",
         "vendor = data/research/night/etf_daily.parquet (Alpaca SIP daily bars, adjustment=all); cross = largest opening-auction print, Alpaca SIP auctions",
         "",
         f"coverage: both crosses {r.both.mean():.1%} (entry {np.isfinite(r.x1).mean():.1%}, exit {np.isfinite(r.x2).mean():.1%}); "
         f"median cross size entry {np.nanmedian(r.xs1):,.0f} sh",
         f"vendor adjustment factor (vendor close / closing cross) median {r.fac.median():.3f}, range {r.fac.min():.3f}..{r.fac.max():.3f}: "
         "etf_daily is split+dividend ADJUSTED (ibs_oos's 'prices RAW' caveat is wrong)",
         f"entry open gap (vendor open / f / opening cross - 1): {dist(r.gap1.dropna())}",
         f"exit  open gap (vendor open / f / opening cross - 1): {dist(r.gap2.dropna())}",
         f"  (f = vendor close / closing cross on the same day, so a gap here is the open's mismatch net of any close mismatch)",
         f"trades spanning a split on d2: {int((r.split != 1).sum())} ({', '.join(f'{a} {b.date()} x{c:g}' for a, b, c in zip(r.sym[r.split != 1], r.d2[r.split != 1], r.split[r.split != 1]))})",
         f"trades spanning an ex-dividend (d2 = ex-date): {int((r["div"] > 0).sum())}, mean dividend {r["div"][r["div"] > 0].mean() / r.x1[r["div"] > 0].mean() * 1e4:.1f}bp",
         "  by symbol (entry|exit median, share |gap|>1bp): " + " ".join(
             f"{s}:{g.gap1.median():+.1f}|{g.gap2.median():+.1f}/{((g.gap1.abs() > 1) | (g.gap2.abs() > 1)).mean():.0%}"
             for s, g in r[r.both].groupby("sym")),
         ""]
    m = r[r.both]
    L.append("per-trade gross (trades with both crosses):")
    for name, a, b in (("2016-20 OOS", "2016", "2020"), ("2021-26 live", "2021", "2026"), ("all", "2016", "2026")):
        g = m[(m.date.dt.year >= int(a)) & (m.date.dt.year <= int(b))]
        L.append(f"  {name:13s} vendor opens: {stat(g.ret)}")
        L.append(f"  {name:13s} crosses (+div): {stat(g.gx)}   (cross - vendor {(g.gx - g.ret).mean() * 1e4:+.2f}bp/trade, "
                 f"median diff {(g.gx - g.ret).median() * 1e4:+.2f}, |diff|>1bp {((g.gx - g.ret).abs() > 1e-4).mean():.0%}, >25bp {((g.gx - g.ret).abs() > 25e-4).mean():.1%}); raw crosses no div {g.gx_raw.mean() * 1e4:+.1f}bp")
    oos_all = r[(r.date.dt.year <= 2020)]
    L.append("")
    L.append(f"2016-20 OOS: all trades on vendor opens {oos_all.ret.mean() * 1e4:+.1f}bp (recorded +{RECORDED_OOS}bp; n {len(oos_all)}); "
             f"on crosses {m[m.date.dt.year <= 2020].gx.mean() * 1e4:+.1f}bp (n {int((m.date.dt.year <= 2020).sum())})")
    yr = m.groupby(m.date.dt.year).apply(lambda g: f"{g.ret.mean() * 1e4:+.0f}/{g.gx.mean() * 1e4:+.0f}")
    L.append("by year (vendor/cross bp): " + " ".join(f"{y % 100:02d}:{v}" for y, v in yr.items()))
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
