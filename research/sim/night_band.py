"""Study NIGHT-BAND (round1_prose.md, N 1039 -> 1040): the night rule below the -8% cutoff, daily-close proxy on Sharadar.

Reuses sel_night.load_bars / nx.build_panel / nx masks (primary universe). Rule per row: day_ret = c/c_prev - 1, daily IBS < 0.10,
closeunadj in [5, 2000], vol20 >= 0.60, ADV20 >= $10M; r = next open / close - 1. Pool = day_ret <= -8% (live); band(c) = [c, -8%).

Run:  PYTHONPATH=. .venv/bin/python research/sim/night_band.py
Out:  data/research/program/night_band_out.txt, night_band_rows.parquet
"""
from __future__ import annotations

import time

import numpy as np
import pandas as pd

from research.sim import nx
from research.sim.sel_night import FULL_CHUNKS, PROG, load_bars

CUTS = [-0.04, -0.05, -0.06, -0.07]
LIVE = -0.08
W = 0.65
CAP = 0.15
COST = 15.0  # bp round trip (7.5/side)


def clus_t(x: np.ndarray) -> float:
    x = np.asarray(x, float)
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 and x.std(ddof=1) > 0 else float("nan")


def build() -> pd.DataFrame:
    master = nx.load_master(nx.Paths())
    parts = []
    t0 = time.time()
    for lo, hi in FULL_CHUNKS:
        bars = load_bars(pd.Timestamp(lo) - pd.Timedelta(days=45), pd.Timestamp(hi) + pd.Timedelta(days=10))
        pn = nx.build_panel(bars)
        keep = nx.eligible_mask(pn) & nx.universe_mask(pn, master, "primary")
        d = pn["date"]
        keep &= (d >= np.datetime64(lo)) & (d <= np.datetime64(hi))
        with np.errstate(invalid="ignore", divide="ignore"):
            dr = pn["c"] / pn["c_prev"] - 1.0
            rng = pn["h"] - pn["l"]
            ibs = (pn["c"] - pn["l"]) / rng
        m = keep & np.isfinite(dr) & (dr <= CUTS[0]) & np.isfinite(ibs) & (rng > 0) & (ibs < 0.10) \
            & (pn["cu"] >= 5) & (pn["cu"] <= 2000) & (pn["vol20"] >= 0.60) & np.isfinite(pn["ovn"])
        idx = np.flatnonzero(m)
        parts.append(pd.DataFrame({"date": d[idx], "ticker": pn["tickers"][idx], "day_ret": dr[idx],
                                   "r": pn["ovn"][idx] * 1e4, "adv": pn["adv"][idx], "vol20": pn["vol20"][idx]}))
        print(f"{lo}..{hi}: rows {len(idx):,} sessions {len(np.unique(d[keep]))} {time.time()-t0:.0f}s", flush=True)
        del bars, pn
    x = pd.concat(parts, ignore_index=True)
    x = x[x.r.abs() < 6000]
    x["date"] = pd.to_datetime(x.date)
    return x


def main() -> int:
    rows = PROG / "night_band_rows.parquet"
    if rows.exists():
        x = pd.read_parquet(rows)
    else:
        x = build()
        x.to_parquet(rows, index=False)
    sessions = pd.DatetimeIndex(np.sort(x.date.unique()))   # sessions with any <= -4% candidate; others have zero legs either way
    pool = x[x.day_ret <= LIVE]
    yr = sessions.year
    L = [f"NIGHT-BAND: night rule below -8%, Sharadar daily proxy 1999-2026 (primary universe); candidate rows {len(x):,}, "
         f"sessions with any <= -4% candidate {len(sessions)}", "",
         f"  live pool (<= -8%): n {len(pool):,} nights {pool.date.nunique()} mean {pool.r.mean():+.1f} med {pool.r.median():+.1f} "
         f"net {pool.r.mean()-COST:+.1f} hit {(pool.r>0).mean():.3f} t(day) {clus_t(pool.groupby('date').r.mean().to_numpy()):.2f}", ""]
    pool_by = pool.groupby("date").r.agg(["mean", "size"])
    pool_leg = pd.Series(0.0, index=sessions)
    pool_leg.loc[pool_by.index] = np.minimum(1.0, CAP * pool_by["size"]) * pool_by["mean"]
    L.append(f"  live-pool leg proxy: {pool_leg.mean():+.2f} bp/night over {len(sessions)} sessions "
             f"(= {pool_leg.mean()*250/100*W:+.2f}pp/yr at w .65); nights with picks {len(pool_by)}")
    L.append("")
    for c in CUTS:
        b = x[(x.day_ret > LIVE) & (x.day_ret <= c)]      # band (-8%, c]
        by = b.groupby("date").r.agg(["mean", "size"])
        years = b.date.dt.year
        h1, h2 = b[years <= 2012].r, b[years >= 2013].r
        s = np.sort(by["mean"].to_numpy())
        L.append(f"== band (-8%, {c:+.0%}] ==")
        L.append(f"  n {len(b):,} nights {len(by)} mean {b.r.mean():+.1f} med {b.r.median():+.1f} net {b.r.mean()-COST:+.1f} "
                 f"hit {(b.r>0).mean():.3f} t(day) {clus_t(by['mean'].to_numpy()):.2f} | halves {h1.mean():+.1f} / {h2.mean():+.1f} "
                 f"| ex-top-5 nights {s[:-5].mean():+.1f} | by year " +
                 " ".join(f"{y}:{g.r.mean():+.0f}" for y, g in b.groupby(years)))
        # paired contrast on common nights
        common = by.index.intersection(pool_by.index)
        dlt = (by.loc[common, "mean"] - pool_by.loc[common, "mean"]).to_numpy()
        L.append(f"  paired band - pool on {len(common)} common nights: {dlt.mean():+.1f}bp t {clus_t(dlt):.2f} med {np.median(dlt):+.1f}")
        # union leg replay
        u = x[x.day_ret <= c]
        uby = u.groupby("date").r.agg(["mean", "size"])
        uleg = pd.Series(0.0, index=sessions)
        uleg.loc[uby.index] = np.minimum(1.0, CAP * uby["size"]) * uby["mean"]
        d = (uleg - pool_leg).to_numpy()
        sd = np.sort(d)
        L.append(f"  union-leg replay vs live pool: delta {d.mean():+.2f} bp/night t {clus_t(d):.2f} med {np.median(d):+.2f} "
                 f"h1 {d[yr <= 2012].mean():+.2f} h2 {d[yr >= 2013].mean():+.2f} ex-top-5 {sd[:-5].mean():+.2f} "
                 f"= {d.mean()*250/100*W:+.2f}pp/yr at w .65 | union nights {len(uby)} vs pool {len(pool_by)} | "
                 f"net of {COST:.0f}bp on added exposure: {(d.mean() - COST*np.maximum(0, np.minimum(1, CAP*uby['size']).reindex(sessions).fillna(0) - np.minimum(1, CAP*pool_by['size']).reindex(sessions).fillna(0)).mean()):+.2f} bp/night")
        # band alone on nights without a pool pick
        alone = by[~by.index.isin(pool_by.index)]
        aleg = np.minimum(1.0, CAP * alone["size"]) * alone["mean"]
        L.append(f"  band alone on {len(alone)} no-pool nights: mean r {alone['mean'].mean():+.1f}bp, leg {aleg.mean():+.2f} bp/night "
                 f"t {clus_t(aleg.to_numpy()):.2f}")
        L.append("")
    L.append("== deflation: 4 cutoffs; max-of-4 null t ~2.2 ==")
    txt = "\n".join(L) + "\n"
    (PROG / "night_band_out.txt").write_text(txt)
    print(txt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
