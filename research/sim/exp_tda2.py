"""Studies TDA-RAW (N 1246) and TDA-XS (N 1247): siblings of N 1245, one run.
Pre-reg research/drafts/round1_prose.md "Amendment - DEEP round 2a". Gates, book, timing and placebo reuse research/sim/exp_tda.py.
  OMP_NUM_THREADS=3 PYTHONPATH=. <venv with ripser+persim>/bin/python research/sim/exp_tda2.py
TDA-RAW: N 1245 with raw (unstandardised) 50-day log returns of SPY/DIA/MDY/QQQ.
TDA-XS: each day the 100 highest-ADV20 eligible common stocks (NX SEP cache, delisted kept, closeunadj >= $5, ADV20 >= $10M,
60 trailing returns present), d_ij = sqrt(2(1 - rho_ij)) on the 60-day total returns (split-adjusted close + cash dividends, as
exp_rl_universe._features), Rips H0 total persistence (= MST length) and H1 first-3-landscape L1. Primary warning z(H0) < -2.
Stock data: the NX SEP cache ends 2021-01-15, so the XS report window is 2016-01-04..2021-01-15 (after that the gate is ON).
Loaded the NX SEP cache directly (columns ticker/date/close/volume/closeunadj in float32), not exp_rl_universe.load_stocks, which
builds ~15 float64 feature columns over 36M rows; the common-stock filter and the return formula are the same."""
import os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "3")
import gc
import pathlib
import time
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from ripser import ripser

from research.sim import exp_tda as T
from research.sim.nx import is_common

ROOT = T.ROOT
NXD = ROOT / "data/research/nx"
OUT = ROOT / "research/sim/exp_tda2_out.txt"
CDIR = ROOT / "data/research/exp_tda"
NTOP, WXS, BUF = 100, 60, 160
PRICE_MIN, ADV_MIN = 5.0, 1e7
P = T.P


def load_sep_slim():
    t = pd.read_parquet(NXD / "cache_TICKERS.parquet", columns=["table", "ticker", "category"])
    t = t[t.table == "SEP"]
    common = sorted(set(t.ticker[is_common(t.category.fillna("").astype(str))]))
    tb = pq.read_table(NXD / "cache_SEP.parquet", columns=["ticker", "date", "close", "volume", "closeunadj"],
                       filters=[("ticker", "in", common)])
    tick = tb.column("ticker").to_pandas().astype("category")
    out = dict(code=tick.cat.codes.to_numpy(np.int32), names=np.asarray(tick.cat.categories),
               date=tb.column("date").to_numpy().astype("datetime64[D]"))
    for c in ("close", "volume", "closeunadj"):
        out[c] = tb.column(c).cast(pa.float32()).to_numpy(zero_copy_only=False)
    del tb, tick; gc.collect()
    o = np.lexsort((out["date"], out["code"]))
    for k in ("code", "date", "close", "volume", "closeunadj"):
        out[k] = out[k][o]
    return out


def divs(names):
    a = pd.read_parquet(NXD / "cache_ACTIONS.parquet", columns=["date", "action", "ticker", "value"])
    a = a[(a.action == "dividend") & a.ticker.isin(set(names))].copy(); a["date"] = pd.to_datetime(a["date"])
    return a.groupby(["ticker", "date"])["value"].sum()


def build_xs():
    cache = CDIR / "xs.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    t0 = time.time(); S = load_sep_slim(); n = len(S["code"])
    code = S["code"]; newg = np.r_[True, code[1:] != code[:-1]]
    start = np.maximum.accumulate(np.where(newg, np.arange(n), 0)); pos = np.arange(n) - start
    dv = (S["closeunadj"].astype(np.float64) * S["volume"]); cs = np.r_[0.0, np.cumsum(dv)]; del dv
    i = np.arange(n); adv = np.full(n, np.nan, np.float32)
    ok = pos >= 19; adv[ok] = ((cs[i[ok] + 1] - cs[i[ok] - 19]) / 20).astype(np.float32); del cs, i
    elig = (pos >= WXS) & (S["closeunadj"] >= PRICE_MIN) & (adv >= ADV_MIN)
    sessions = np.unique(S["date"]); di = np.searchsorted(sessions, S["date"]).astype(np.int32)
    ei = np.flatnonzero(elig); o = np.lexsort((-adv[ei], di[ei])); ei = ei[o]
    d_e = di[ei]; gstart = np.r_[0, np.flatnonzero(np.diff(d_e)) + 1]
    rk = np.arange(len(ei)) - np.repeat(gstart, np.diff(np.r_[gstart, len(ei)]))
    keep = ei[rk < BUF]
    cand = np.unique(code[keep]); P(f"[xs] SEP common rows {n:,}, sessions {len(sessions)} ({sessions[0]}..{sessions[-1]}), "
                                   f"eligible rows {elig.sum():,}, candidate tickers (top-{BUF} ever) {len(cand)}")
    # wide total returns for candidates
    m = np.isin(code, cand); cc = code[m]; dd = di[m]; cl = S["close"][m].astype(np.float64); cu = S["closeunadj"][m].astype(np.float64)
    pm = pos[m]
    dvt = divs(S["names"][cand]); dvs = np.zeros(len(cc))
    if len(dvt):  # match (ticker, date) -> row via integer keys code * nsess + session index
        ns = len(sessions); dcode = np.searchsorted(S["names"], dvt.index.get_level_values(0).to_numpy(str))
        dsess = np.searchsorted(sessions, dvt.index.get_level_values(1).to_numpy().astype("datetime64[D]"))
        okd = (dsess < ns) & (S["names"][np.minimum(dcode, len(S["names"]) - 1)] == dvt.index.get_level_values(0).to_numpy(str))
        okd &= sessions[np.minimum(dsess, ns - 1)] == dvt.index.get_level_values(1).to_numpy().astype("datetime64[D]")
        dk = dcode[okd].astype(np.int64) * ns + dsess[okd]; dval = dvt.to_numpy()[okd]
        rk_ = cc.astype(np.int64) * ns + dd; o_ = np.argsort(dk); dk, dval = dk[o_], dval[o_]
        j = np.searchsorted(dk, rk_); j = np.minimum(j, len(dk) - 1); hit = dk[j] == rk_
        dvs[hit] = dval[j[hit]]
    with np.errstate(divide="ignore", invalid="ignore"):
        da = np.where(cu > 0, dvs * cl / cu, 0.0)
        ret = (cl + da) / np.r_[np.nan, cl[:-1]] - 1
    ret[pm == 0] = np.nan; ret[~np.isfinite(ret)] = np.nan
    col = np.searchsorted(cand, cc); R = np.full((len(sessions), len(cand)), np.nan, np.float32); R[dd, col] = ret
    sel_d = di[keep]; sel_c = np.searchsorted(cand, code[keep])      # already ordered by (date, adv desc)
    del S, m, cc, dd, cl, cu, pm, da, ret, adv, elig, pos, di, code; gc.collect()
    P(f"[xs] wide returns {R.shape} float32 ({R.nbytes/1e6:.0f} MB), load+prep {time.time()-t0:.0f}s")
    rows = []; t1 = time.time(); bounds = np.r_[0, np.flatnonzero(np.diff(sel_d)) + 1, len(sel_d)]
    for a, b in zip(bounds[:-1], bounds[1:]):
        d = sel_d[a]
        if d < WXS:
            continue
        X = R[d - WXS + 1:d + 1, sel_c[a:b]].astype(np.float64)
        good = np.isfinite(X).all(0) & (X.std(0) > 0)
        idxs = np.flatnonzero(good)[:NTOP]
        if len(idxs) < NTOP:
            continue
        rho = np.corrcoef(X[:, idxs].T); Dm = np.sqrt(np.clip(2 * (1 - rho), 0, None)); np.fill_diagonal(Dm, 0.0)
        dg = ripser(Dm, distance_matrix=True, maxdim=1)["dgms"]
        h0 = dg[0][:, 1]; h0 = float(h0[np.isfinite(h0)].sum())
        mc = float(rho[np.triu_indices(NTOP, 1)].mean())
        rows.append((pd.Timestamp(sessions[d]), h0, T.landscape_l1(dg[1]), mc, len(dg[1])))
    s = pd.DataFrame(rows, columns=["date", "h0", "h1l1", "mcorr", "nbars1"]).set_index("date")
    CDIR.mkdir(parents=True, exist_ok=True); s.to_parquet(cache)
    P(f"[xs] {len(s)} days of Rips H0/H1 in {time.time()-t1:.0f}s")
    return s


def selftest_h0():
    """H0 total persistence of a Rips filtration = MST length: check against scipy's MST on a random distance matrix."""
    from scipy.sparse.csgraph import minimum_spanning_tree
    X = T.rng.normal(size=(100, 5)); Dm = np.sqrt(((X[:, None] - X[None]) ** 2).sum(-1))
    h0 = ripser(Dm, distance_matrix=True, maxdim=0)["dgms"][0][:, 1]; h0 = h0[np.isfinite(h0)].sum()
    P(f"selftest H0: Rips total H0 persistence {h0:.6f} vs MST length {minimum_spanning_tree(Dm).sum():.6f}")


def main():
    T.selftest(); selftest_h0()
    C = T.load_prices()
    P(f"prices: {C.index.min().date()}..{C.index.max().date()} (SFP closeadj)")

    P("\n" + "=" * 30 + " N 1246 TDA-RAW (raw log returns, no standardisation) " + "=" * 30)
    s = T.build_l1(C, standardize=False, cache=CDIR / "l1_raw.parquet"); s["z"] = T.zscore(s.l1); warn = s.z > T.ZTH
    std = pd.read_parquet(CDIR / "l1.parquet")
    head = (f"L1raw: {len(s)} days, H1 bars/day median {s.nbars.median():.0f}; z from {s.z.first_valid_index().date()}; "
            f"warnings (z>2) {int(warn.sum())} days; corr with N 1245 standardised L1 {s.l1.corr(std.l1):+.3f}")
    ok, why = T.run_gates(C, s.l1, s.z, warn, head, 1246, "TDA-RAW", "L1raw")
    P(f"\n{'PASS' if ok else 'KILL'}: N 1246 TDA-RAW - {why}")

    P("\n" + "=" * 30 + " N 1247 TDA-XS (top-100 ADV stocks, sqrt(2(1-rho)) on 60d, Rips H0) " + "=" * 30)
    x = build_xs()
    x["z0"] = T.zscore(x.h0); x["z1"] = T.zscore(x.h1l1); x["zc"] = T.zscore(x.mcorr)
    c0 = x.h0.corr(x.mcorr); cs0 = x.h0.corr(x.mcorr, method="spearman")
    P(f"XS series {x.index.min().date()}..{x.index.max().date()} ({len(x)} days; NX SEP cache ends 2021-01-15, so no stock data "
      f"on disk after that: XS report window is 2016-01-04..2021-01-15, gate ON afterwards; 2026 section below is empty for XS)")
    P(f"corr(H0, mean pairwise corr): Pearson {c0:+.3f}, Spearman {cs0:+.3f}; corr(H1-L1, mean corr) {x.h1l1.corr(x.mcorr):+.3f}; "
      f"corr(z H0, z mean corr) {x.z0.corr(x.zc):+.3f}")
    rep0 = T.REPORT; T.REPORT = ("2016-01-04", "2021-01-15")
    try:
        w0 = x.z0 < -T.ZTH
        head = (f"H0: median {x.h0.median():.2f}; z from {x.z0.first_valid_index().date()}; warnings (z<-2) {int(w0.sum())} days "
                f"[REPORT rows below cover 2016-01-04..2021-01-15 despite the label]")
        ok, why = T.run_gates(C, x.h0, x.z0, w0, head, 1247, "TDA-XS", "H0")
        P(f"\n{'PASS' if ok else 'KILL'}: N 1247 TDA-XS (primary, H0 z<-2) - {why}")

        P("\n" + "-" * 20 + " N 1247 report arm: H1-L1 z > 2 (not judged) " + "-" * 20)
        w1 = x.z1 > T.ZTH
        ok1, why1 = T.run_gates(C, x.h1l1, x.z1, w1, f"H1-L1: warnings (z>2) {int(w1.sum())} days", 1247, "XS-H1", "H1L1")
        P(f"\nREPORT (H1 arm, not a verdict): {'would pass' if ok1 else 'would fail'} - {why1}")

        if abs(c0) > 0.9:
            P("\n" + "-" * 20 + " |corr(H0, mean corr)| > 0.9: plain mean-correlation gate, z(mean corr) > 2 (report) " + "-" * 20)
            wc = x.zc > T.ZTH
            okc, whyc = T.run_gates(C, x.mcorr, x.zc, wc, f"mean corr: warnings (z>2) {int(wc.sum())} days", 1247, "MCORR", "mcorr")
            P(f"\nREPORT (mean-corr gate): {'would pass' if okc else 'would fail'} - {whyc}")
        else:
            P(f"\n|corr(H0, mean corr)| = {abs(c0):.3f} <= 0.9: mean-correlation gate not required by the pre-reg (not run)")
    finally:
        T.REPORT = rep0
    OUT.write_text("\n".join(T.L) + "\n")


if __name__ == "__main__":
    main()
