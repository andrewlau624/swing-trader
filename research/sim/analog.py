"""Study ANALOG (N 1180-1188): raw z-normalized PRICE-PATH analogs (nearest-neighbour shape matching).
Registration: research/drafts/round1_prose.md "Study ANALOG" (2026-11-09).

Phases:
  build : Sharadar SEP common + SFP ETFs -> universe rows (closeunadj >= 3, ADV20 >= $5M, >= 41 bars, 1999+), PCA-8 of the
          z-normalized 20/40-session log-closeadj path (+ time-shuffled placebo paths), forward open->open labels
          -> data/research/analog/rows.parquet (+ pca.npz)
  knn   : walk-forward kNN (faiss HNSW, library grows by year, every 5th session per ticker, K=50 after same-ticker/60-session
          exclusion) -> data/research/analog/fc_L{20,40}.parquet (real + shuffled-placebo forecasts for H 1/5/10)
  v1    : N 1180-1185 judge -> data/research/program/analog_out.txt
  v2    : N 1186-1188 templates (swingers chosen 2008-12) -> appended to analog_out.txt
  rgti  : illustrative RGTI nearest analogs (non-judging) -> appended

Run:  uv run --with numpy --with pandas --with pyarrow --with scipy --with faiss-cpu python research/sim/analog.py --phase all
Approximations (stated): PCA-8 distance instead of full 40-dim Euclidean; library sampled every 5th session per ticker;
library cut at the calendar-year boundary (paths whose H=10 exit is before Jan 1 of the query year); HNSW approximate search.
"""
from __future__ import annotations

import argparse
import math
import pathlib
import time

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import scipy.stats as SS

ROOT = pathlib.Path(__file__).resolve().parents[2]
PROG = ROOT / "data" / "research" / "program"
DIR = ROOT / "data" / "research" / "analog"
OUT = PROG / "analog_out.txt"
S = pathlib.Path.home() / "data" / "sharadar"
SEED = 20261109
HS = (1, 5, 10)
LS = (20, 40)
NPC = 8
K, KFETCH = 50, 120
JUDGE0 = pd.Timestamp("2013-01-01")
N_PROGRAM = 1189


# ----------------------------------------------------------------------------- load
def load_panel() -> pd.DataFrame:
    t = pd.read_parquet(S / "tickers.parquet", columns=["table", "ticker", "category"])
    cat = t.category.fillna("")
    stk = t[(t.table == "SEP") & cat.str.contains("Common Stock") & ~cat.str.contains("Secondary")].ticker.unique()
    etf = t[(t.table == "SFP") & (cat == "ETF")].ticker.unique()
    cols = ["ticker", "date", "open", "close", "volume", "closeadj", "closeunadj"]
    d0 = pd.Timestamp("1998-06-01").date()
    parts = []
    for f, tks, kind in (("stocks", stk, 0), ("funds", etf, 1)):
        x = pq.read_table(S / f"{f}.parquet", columns=cols,
                          filters=[("ticker", "in", sorted(tks)), ("date", ">=", d0)]).to_pandas()
        x["etf"] = np.int8(kind)
        parts.append(x)
    df = pd.concat(parts, ignore_index=True)
    df["date"] = pd.to_datetime(df["date"])
    for c in ["open", "close", "volume", "closeadj", "closeunadj"]:
        df[c] = df[c].astype("float64")
    df = df.dropna(subset=["open", "close", "closeadj", "closeunadj"])
    df = df[(df.close > 0) & (df.open > 0) & (df.closeadj > 0)]
    # duplicate ticker keys (stock + fund with the same symbol): keep the stock row
    df = df.sort_values(["ticker", "date", "etf"]).drop_duplicates(["ticker", "date"], keep="first")
    return df.reset_index(drop=True)


def zpaths(logc: np.ndarray, idx: np.ndarray, L: int, rng=None) -> np.ndarray:
    P = logc[idx[:, None] + np.arange(-L + 1, 1)[None, :]]
    if rng is not None:  # time-permute the daily log returns (keeps total-L return and vol, destroys shape)
        r = np.diff(P, axis=1)
        perm = np.argsort(rng.random(r.shape), axis=1)
        r = np.take_along_axis(r, perm, axis=1)
        P = np.concatenate([np.zeros((len(P), 1)), np.cumsum(r, axis=1)], axis=1)
    P = P - P.mean(axis=1, keepdims=True)
    sd = P.std(axis=1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        return (P / sd).astype(np.float32)


def build() -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    df = load_panel()
    print(f"panel {len(df):,} rows {df.ticker.nunique()} tickers {time.time()-t0:.0f}s", flush=True)
    dv = (df.close * df.volume).to_numpy()
    elig = df.loc[(df.closeunadj >= 3) & (dv >= 5e6), "ticker"].unique()
    df = df[df.ticker.isin(elig)].reset_index(drop=True)
    tk = pd.Categorical(df.ticker)
    tcode = tk.codes.astype(np.int32)
    n = len(df)
    start = np.r_[0, np.flatnonzero(np.diff(tcode)) + 1]
    end = np.r_[start[1:], n] - 1
    tstart = np.repeat(start, np.diff(np.r_[start, n]))
    tend = np.repeat(end, np.diff(np.r_[start, n]))
    pos = np.arange(n) - tstart
    c = df.close.to_numpy(); o = df.open.to_numpy(); ca = df.closeadj.to_numpy(); cu = df.closeunadj.to_numpy()
    v = df.volume.fillna(0).to_numpy()
    oa = o * ca / c
    logc = np.log(ca)
    dvv = c * v
    cs = np.r_[0, np.cumsum(dvv)]
    adv20 = np.where(pos >= 19, (cs[np.arange(n) + 1] - cs[np.maximum(np.arange(n) - 19, 0)]) / 20, np.nan)
    r1 = np.r_[np.nan, np.diff(logc)]
    r1[pos == 0] = np.nan
    r1c = np.nan_to_num(r1)
    c1 = np.r_[0, np.cumsum(r1c)]; c2 = np.r_[0, np.cumsum(r1c ** 2)]
    ii = np.arange(n)
    m1 = (c1[ii + 1] - c1[np.maximum(ii - 19, 0)]) / 20
    m2 = (c2[ii + 1] - c2[np.maximum(ii - 19, 0)]) / 20
    vol20 = np.where(pos >= 20, np.sqrt(np.maximum(m2 - m1 ** 2, 0)) * math.sqrt(252), np.nan)
    dates = df.date.to_numpy()
    cal = np.unique(dates)
    sess = np.searchsorted(cal, dates).astype(np.int32)
    uni = (cu >= 3) & (adv20 >= 5e6) & (pos >= 40) & (dates >= np.datetime64("1999-01-01")) & (ii < tend)
    q = np.flatnonzero(uni)
    print(f"universe rows {len(q):,}  {time.time()-t0:.0f}s", flush=True)
    out = {"date": dates[q], "sess": sess[q], "tk": tcode[q], "etf": df.etf.to_numpy()[q],
           "adv20": adv20[q].astype(np.float32), "vol20": vol20[q].astype(np.float32), "px": cu[q].astype(np.float32),
           "samp": (pos[q] % 5 == 0)}
    e = q + 1
    out["gap"] = (oa[e] / ca[q] - 1).astype(np.float32)
    out["ret1_oc"] = (ca[e] / oa[e] - 1).astype(np.float32)  # entry-day intraday leg (open d+1 -> close d+1)
    for H in HS:
        j = q + 1 + H
        ok = j <= tend[q]
        jj = np.where(ok, j, tend[q])
        exitpx = np.where(ok, oa[np.minimum(j, n - 1)], ca[jj])  # delisted early: exit at the last bar's close
        out[f"r{H}"] = (exitpx / oa[e] - 1).astype(np.float32)
        out[f"xs{H}"] = sess[jj]  # exit session (for the library cut)
    # PCA on a 1999-2012 sample of z-paths
    rng = np.random.default_rng(SEED)
    insamp = q[dates[q] < np.datetime64("2013-01-01")]
    smp = rng.choice(insamp, size=min(400_000, len(insamp)), replace=False)
    pcs = {}
    for L in LS:
        Z = zpaths(logc, smp, L)
        Z = Z[np.isfinite(Z).all(1)]
        mu = Z.mean(0)
        U, Sv, Vt = np.linalg.svd(Z - mu, full_matrices=False)
        ev = Sv ** 2 / (Sv ** 2).sum()
        pcs[L] = (mu, Vt[:NPC])
        print(f"PCA L{L}: first {NPC} comps explain {ev[:NPC].sum():.3f}", flush=True)
        np.savez(DIR / f"pca_L{L}.npz", mu=mu, comps=Vt[:NPC], ev=ev)
    CH = 1_000_000
    for L in LS:
        mu, W = pcs[L]
        real = np.empty((len(q), NPC), np.float32); shuf = np.empty((len(q), NPC), np.float32)
        rng2 = np.random.default_rng(SEED + L)
        for a in range(0, len(q), CH):
            qq = q[a:a + CH]
            real[a:a + CH] = (zpaths(logc, qq, L) - mu) @ W.T
            shuf[a:a + CH] = (zpaths(logc, qq, L, rng2) - mu) @ W.T
        for k in range(NPC):
            out[f"p{L}_{k}"] = real[:, k]
            out[f"s{L}_{k}"] = shuf[:, k]
        print(f"paths L{L} done {time.time()-t0:.0f}s", flush=True)
    res = pd.DataFrame(out)
    res["ticker"] = np.asarray(tk.categories)[res.tk.to_numpy()]
    res.to_parquet(DIR / "rows.parquet", index=False)
    # raw logc store for V2 template shuffles / RGTI table
    np.savez(DIR / "logc.npz", logc=logc.astype(np.float64), q=q)
    print(f"saved rows {len(res):,} {time.time()-t0:.0f}s", flush=True)


# ----------------------------------------------------------------------------- knn
def labels(R: pd.DataFrame) -> dict[int, np.ndarray]:
    """cross-sectional excess forward return, winsorized at the 1999-2012 1/99 pct."""
    lab = {}
    ins = (R.date < JUDGE0).to_numpy()
    for H in HS:
        x = R[f"r{H}"].astype(np.float64)
        x = (x - x.groupby(R.date).transform("mean")).to_numpy()
        lo, hi = np.nanpercentile(x[ins], [1, 99])
        lab[H] = np.clip(x, lo, hi).astype(np.float32)
    return lab


def knn() -> None:
    import faiss
    faiss.omp_set_num_threads(10)
    t0 = time.time()
    base = ["date", "sess", "tk", "samp", "r1", "r5", "r10", "xs10"]
    for L in LS:
        pc = [f"p{L}_{k}" for k in range(NPC)]; sc = [f"s{L}_{k}" for k in range(NPC)]
        R = pd.read_parquet(DIR / "rows.parquet", columns=base + pc + sc)
        lab = labels(R)
        P = R[pc].to_numpy(np.float32); Q = R[sc].to_numpy(np.float32)
        ok = np.isfinite(P).all(1) & np.isfinite(Q).all(1)
        LAB = np.stack([lab[H] for H in HS], 1)
        libmask = ok & R.samp.to_numpy() & np.isfinite(LAB).all(1)
        lib_rows = np.flatnonzero(libmask)
        lib_rows = lib_rows[np.argsort(R.xs10.to_numpy()[lib_rows], kind="stable")]
        lib_xs = R.xs10.to_numpy()[lib_rows]
        lib_tk = R.tk.to_numpy()[lib_rows]; lib_sess = R.sess.to_numpy()[lib_rows]; lib_lab = LAB[lib_rows]
        cal_dates = R.groupby("sess").date.first().sort_index()
        index = faiss.IndexHNSWFlat(NPC, 32)
        index.hnsw.efConstruction = 40
        index.hnsw.efSearch = 128
        added = 0
        F = np.full((len(R), 3), np.nan, np.float32); PF = np.full((len(R), 3), np.nan, np.float32)
        ND = np.full(len(R), np.nan, np.float32)
        years = R.date.dt.year.to_numpy()
        tk_all = R.tk.to_numpy(); sess_all = R.sess.to_numpy()
        for Y in range(2005, 2027):
            ycut = int(cal_dates.index[np.searchsorted(cal_dates.to_numpy(), np.datetime64(f"{Y}-01-01"))])
            upto = int(np.searchsorted(lib_xs, ycut, side="left"))
            if upto > added:
                index.add(P[lib_rows[added:upto]])
                added = upto
            qi = np.flatnonzero(ok & (years == Y))
            for arr, tgt, dist in ((P, F, True), (Q, PF, False)):
                for a in range(0, len(qi), 500_000):
                    qq = qi[a:a + 500_000]
                    D, I = index.search(arr[qq], KFETCH)
                    Ic = np.maximum(I, 0)
                    bad = (I < 0) | ((lib_tk[Ic] == tk_all[qq, None]) & (np.abs(lib_sess[Ic] - sess_all[qq, None]) < 60))
                    good = ~bad
                    sel = good & (np.cumsum(good, axis=1) <= K)
                    cnt = sel.sum(1)
                    for h in range(3):
                        tgt[qq, h] = (lib_lab[Ic, h] * sel).sum(1) / np.maximum(cnt, 1)
                    tgt[qq[cnt < K // 2]] = np.nan
                    if dist:
                        ND[qq] = (D * sel).sum(1) / np.maximum(cnt, 1)
            print(f"L{L} {Y}: lib {added:,} queries {len(qi):,} {time.time()-t0:.0f}s", flush=True)
        fc = pd.DataFrame({"row": np.arange(len(R), dtype=np.int64)})
        for h, H in enumerate(HS):
            fc[f"f{H}"] = F[:, h]; fc[f"pf{H}"] = PF[:, h]
        fc["nd"] = ND
        fc.to_parquet(DIR / f"fc_L{L}.parquet", index=False)
        del R, P, Q, index


# ----------------------------------------------------------------------------- judge helpers
def nw_t(x, lags: int = 0) -> float:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 3:
        return float("nan")
    e = x - x.mean()
    s = (e * e).sum()
    for L in range(1, lags + 1):
        s += 2 * (1 - L / (lags + 1)) * (e[L:] * e[:-L]).sum()
    se = math.sqrt(s) / n
    return x.mean() / se if se > 0 else float("nan")


def dsr(x, n_trials: int):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    T = len(x)
    if T < 10 or x.std(ddof=1) == 0:
        return float("nan")
    sr = x.mean() / x.std(ddof=1)
    sk = SS.skew(x); ku = SS.kurtosis(x, fisher=False)
    g = 0.5772156649
    sr0 = math.sqrt(1.0 / T) * ((1 - g) * SS.norm.ppf(1 - 1 / n_trials) + g * SS.norm.ppf(1 - 1 / (n_trials * math.e)))
    z = (sr - sr0) * math.sqrt(T - 1) / math.sqrt(max(1e-12, 1 - sk * sr + (ku - 1) / 4 * sr ** 2))
    return float(SS.norm.cdf(z))


def base_frame() -> pd.DataFrame:
    cols = ["date", "sess", "tk", "ticker", "etf", "adv20", "vol20", "px", "gap", "ret1_oc", "r1", "r5", "r10", "xs10"]
    R = pd.read_parquet(DIR / "rows.parquet", columns=cols)
    for H in HS:
        R[f"r{H}"] = R[f"r{H}"].astype(np.float64).clip(-0.95, 3.0)
    R["cost"] = np.where(R.adv20 >= 1e7, 0.0005, 0.0010)
    R["vdec"] = R.groupby("date").vol20.transform(lambda s: np.ceil(s.rank(pct=True) * 10).clip(1, 10)).fillna(0).astype(np.int8)
    R["band"] = np.select([R.px < 10, R.px < 30], [0, 1], 2).astype(np.int8)
    key = [R.date, R.vdec, R.band]
    for H in HS:
        R[f"cm{H}"] = R.groupby(key)[f"r{H}"].transform("mean")
    R["cmgap"] = R.groupby(key).gap.transform("mean")
    # QQQ open->open over the same window, by session
    qq = pq.read_table(S / "funds.parquet", columns=["date", "open", "close", "closeadj"], filters=[("ticker", "=", "QQQ")]).to_pandas()
    qq["date"] = pd.to_datetime(qq.date)
    cal = R.groupby("sess").date.first().sort_index()
    cal = cal.reindex(range(int(cal.index.max()) + 1))  # position == sess (rows start 1999; sess counts from 1998-06)
    qq = qq.set_index("date").reindex(cal.to_numpy())
    oa = (qq.open * qq.closeadj / qq.close).to_numpy()
    for H in HS:
        s = R.sess.to_numpy()
        a = np.clip(s + 1, 0, len(oa) - 1); b = np.clip(s + 1 + H, 0, len(oa) - 1)
        R[f"q{H}"] = oa[b] / oa[a] - 1
    return R


def judge(R: pd.DataFrame, pick: np.ndarray, H: int, lab: str, placebo: np.ndarray | None = None,
          short: np.ndarray | None = None) -> tuple[list[str], dict]:
    """pick: boolean mask over R rows (judge rows only). Cohort = per signal date."""
    X = R.loc[pick, ["date", "ticker", "adv20", "gap", "cmgap", "cost", f"r{H}", f"cm{H}", f"q{H}", "ret1_oc"]].copy()
    r, cm, c = X[f"r{H}"], X[f"cm{H}"], X["cost"]
    X["gross"] = r; X["exc0"] = r - cm
    for k in (1, 2, 3):
        X[f"net{k}"] = r - 2 * k * c
        X[f"exc{k}"] = X[f"net{k}"] - cm
    g = X.groupby("date")
    C = g[["gross", "exc0", "net1", "net2", "net3", "exc1", "exc2", "exc3", f"q{H}", "gap", "cmgap", "ret1_oc"]].mean()
    C["n"] = g.size()
    e = C.exc1.to_numpy()
    yrs = C.index.year
    half1 = C.exc1[yrs <= 2019]; half2 = C.exc1[yrs >= 2020]
    ex5 = C.exc1.drop(C.exc1.nlargest(5).index)
    ndates_yr = len(C) / max(1e-9, (C.index.max() - C.index.min()).days / 365.25)
    ceil = ndates_yr * C.net1.mean() / H * 0.5
    ceil_alpha = None
    # beta / alpha vs QQQ (cohort gross on the same-window QQQ)
    y = C.gross.to_numpy(); xq = C[f"q{H}"].to_numpy()
    okb = np.isfinite(y) & np.isfinite(xq)
    beta, alpha = np.polyfit(xq[okb], y[okb], 1) if okb.sum() > 10 else (np.nan, np.nan)
    resid = y[okb] - beta * xq[okb]
    alpha_t = nw_t(resid, H)
    nonov = C.exc1.iloc[::H]
    d = dsr(nonov.to_numpy(), N_PROGRAM)
    st = {"mean": e.mean() * 1e4, "t": nw_t(e, H), "med": np.median(e) * 1e4, "h1": half1.mean() * 1e4, "h2": half2.mean() * 1e4,
          "x2": C.exc2.mean() * 1e4, "x3": C.exc3.mean() * 1e4, "ex5": ex5.mean() * 1e4, "dsr": d, "ceil": ceil * 100,
          "net1": C.net1.mean() * 1e4, "beta": beta, "alpha": alpha * 1e4, "alpha_t": alpha_t, "ndates": len(C)}
    L_ = [f"  [{lab}] H{H}: trades {len(X):,} dates {len(C):,} ({ndates_yr:.0f}/yr) names/date med {C.n.median():.0f}; "
          f"median pick ADV ${X.adv20.median()/1e6:.1f}M",
          f"    gross {C.gross.mean()*1e4:+.1f}bp  net(1x) {st['net1']:+.1f}bp  hit(net>0) {(X.net1 > 0).mean():.3f}  "
          f"excess-vs-volmatched gross {C.exc0.mean()*1e4:+.1f}  NET {st['mean']:+.1f}bp t {st['t']:.2f} median {st['med']:+.1f} "
          f"hit(exc>0) {(X.exc1 > 0).mean():.3f}",
          f"    halves 2013-19 {st['h1']:+.1f} / 2020-26 {st['h2']:+.1f}; 2x {st['x2']:+.1f} 3x {st['x3']:+.1f}; ex-top-5 dates "
          f"{st['ex5']:+.1f}; 2020 {C.exc1[yrs == 2020].mean()*1e4:+.1f} 2022 {C.exc1[yrs == 2022].mean()*1e4:+.1f}",
          f"    beta vs QQQ {beta:.2f} alpha {st['alpha']:+.1f}bp/trade NW t {alpha_t:.2f}; DSR(N {N_PROGRAM}, non-overlap) {d:.3f}; "
          f"ceiling abs net @50% {st['ceil']:+.1f}pp/yr",
          f"    gap check: untradable close->open gap picks {C.gap.mean()*1e4:+.1f}bp vs cell {C.cmgap.mean()*1e4:+.1f}bp; "
          f"entry-day intraday leg {C.ret1_oc.mean()*1e4:+.1f}bp"]
    if placebo is not None:
        Pm = R.loc[placebo, ["date", f"r{H}", f"cm{H}", "cost"]]
        pc = (Pm[f"r{H}"] - 2 * Pm.cost - Pm[f"cm{H}"]).groupby(Pm.date).mean()
        dd = (C.exc1 - pc.reindex(C.index)).dropna()
        st["plac"] = pc.mean() * 1e4; st["diff_t"] = nw_t(dd.to_numpy(), H); st["diff"] = dd.mean() * 1e4
        L_.append(f"    shape-shuffled placebo net excess {st['plac']:+.1f}bp; real - placebo {st['diff']:+.1f}bp t {st['diff_t']:.2f}")
    if short is not None:
        Sm = R.loc[short, ["date", f"r{H}", "cost"]]
        sc = (-Sm[f"r{H}"] - 2 * Sm.cost).groupby(Sm.date).mean()
        ls = (C.net1 + sc.reindex(C.index)).dropna() / 2
        L_.append(f"    long-short (taxable, half each leg, both pay cost) {ls.mean()*1e4:+.1f}bp/trade t {nw_t(ls.to_numpy(), H):.2f}")
    return L_, st


def gate(st: dict) -> tuple[bool, str]:
    checks = {"t>=2": st["mean"] > 0 and st["t"] >= 2, "halves": st["h1"] > 0 and st["h2"] > 0, "2x": st["x2"] > 0,
              "ex5": st["ex5"] > 0, "median": st["med"] > 0, "placebo": st.get("diff_t", -9) >= 2,
              "dsr": (st["dsr"] or 0) >= 0.95, "ceiling": st["ceil"] >= 8}
    fails = [k for k, v in checks.items() if not v]
    return (not fails), ("PASS" if not fails else "KILL (fails: " + ", ".join(fails) + ")")


def topdec(R: pd.DataFrame, f: np.ndarray, mask: np.ndarray, top: bool = True, k: int | None = None) -> np.ndarray:
    s = pd.Series(np.where(mask, f, np.nan), index=R.index)
    cnt = s.groupby(R.date).transform("count")
    if k is not None:
        rk = s.groupby(R.date).rank(ascending=not top, method="first")
        return (rk <= k).to_numpy() & (cnt >= 100).to_numpy()
    pr = s.groupby(R.date).rank(pct=True)
    sel = (pr > 0.9) if top else (pr <= 0.1)
    return sel.to_numpy() & (cnt >= 100).to_numpy()


def v1() -> None:
    R = base_frame()
    lines = ["Study ANALOG (N 1180-1188) — raw z-normalized price-path analogs. Registration round1_prose.md 2026-11-09.",
             f"rows {len(R):,} (universe stock/ETF-days 1999-2026); judge 2013-01..{R.date.max().date()}; costs 5/10bp per side by ADV.",
             f"data-bug guard: trade returns clipped to [-95%, +300%]; |gap| > 50% rows: {(R.gap.abs() > 0.5).sum():,}", ""]
    for L in LS:
        ev = np.load(DIR / f"pca_L{L}.npz")["ev"]
        fc = pd.read_parquet(DIR / f"fc_L{L}.parquet")
        lines.append(f"== V1 L{L}: PCA-{NPC} explains {ev[:NPC].sum():.3f} of z-path variance; forecasts finite {np.isfinite(fc.f1).mean():.3f}")
        J = (R.date >= JUDGE0).to_numpy(); I = ((R.date >= "2005-01-01") & (R.date < JUDGE0)).to_numpy()
        for h, H in enumerate(HS):
            f = fc[f"f{H}"].to_numpy(); pf = fc[f"pf{H}"].to_numpy()
            ok = np.isfinite(f) & np.isfinite(pf)
            n = 1180 + LS.index(L) * 3 + h
            top = topdec(R, f, ok & J); bot = topdec(R, f, ok & J, top=False); ptop = topdec(R, pf, ok & J)
            L_, st = judge(R, top, H, f"N {n} V1 L{L} top-decile long-only", placebo=ptop, short=bot)
            lines += L_
            # in-sample descriptive + implementable top-10 + monotonicity
            Li, sti = judge(R, topdec(R, f, ok & I), H, "in-sample 2005-12 top decile")
            lines.append(f"    in-sample 2005-12 net excess {sti['mean']:+.1f}bp t {sti['t']:.2f} (descriptive)")
            L10, st10 = judge(R, topdec(R, f, ok & J, k=10), H, "top-10 names")
            lines.append(f"    implementable top-10/day: net abs {st10['net1']:+.1f}bp, net excess {st10['mean']:+.1f}bp t {st10['t']:.2f}, "
                         f"ceiling {st10['ceil']:+.1f}pp/yr")
            s = pd.Series(np.where(ok & J, f, np.nan))
            dec = s.groupby(R.date.to_numpy()).rank(pct=True).mul(10).apply(np.ceil)
            exc = (R[f"r{H}"] - R[f"cm{H}"]).to_numpy()
            mono = pd.Series(exc).groupby(dec.to_numpy()).mean().mul(1e4)
            lines.append("    gross excess by forecast decile (judge): " + " ".join(f"{v:+.1f}" for v in mono.to_numpy()))
            ok_, verdict = gate(st)
            lines.append(f"    GATE N {n}: {verdict}")
            print("\n".join(lines[-12:]), flush=True)
        lines.append("")
    OUT.write_text("\n".join(lines) + "\n")


def v2() -> None:
    import faiss
    R = base_frame()
    pc = [f"p40_{k}" for k in range(NPC)]
    P = pd.read_parquet(DIR / "rows.parquet", columns=pc).to_numpy(np.float32)
    okp = np.isfinite(P).all(1)
    d = R.date
    win = ((d >= "2008-01-01") & (d < "2013-01-01")).to_numpy()
    # swingers: channel strategy 2008-12 on the panel
    df = load_panel()
    dv = (df.close * df.volume).to_numpy()
    elig = df.loc[(df.closeunadj >= 3) & (dv >= 5e6), "ticker"].unique()
    df = df[df.ticker.isin(elig)].reset_index(drop=True)
    sessions = R.loc[win, "date"].nunique()
    cover = R.loc[win].groupby("ticker").size()
    cand = cover[cover >= 0.8 * sessions].index
    W = df[df.ticker.isin(cand) & (df.date >= "2007-11-01") & (df.date < "2013-01-01")]
    prof = {}
    for t, g in W.groupby("ticker", sort=False):
        ca = g.closeadj.to_numpy(); oa = (g.open * g.closeadj / g.close).to_numpy(); dt = g.date.to_numpy()
        lo = pd.Series(ca).rolling(20).min().to_numpy(); hi = pd.Series(ca).rolling(20).max().to_numpy()
        pos, ent, tot = False, 0.0, 0.0
        for i in range(20, len(ca) - 1):
            if dt[i] < np.datetime64("2008-01-01"):
                continue
            rg = hi[i] - lo[i]
            if not pos and ca[i] <= lo[i] + 0.2 * rg:
                pos, ent = True, oa[i + 1]
            elif pos and ca[i] >= lo[i] + 0.8 * rg:
                tot += math.log(oa[i + 1] / ent); pos = False
        if pos:
            tot += math.log(ca[-1] / ent)
        prof[t] = tot
    prof = pd.Series(prof).sort_values(ascending=False)
    sw = list(prof.index[:50])
    lines = ["", f"== V2 TEMPLATES (L40): candidates {len(cand)} (>= 80% of 2008-12 sessions); top-50 swingers by channel profit "
                 f"(range {prof.iloc[49]:.2f}..{prof.iloc[0]:.2f} log): " + " ".join(sw)]
    cut13 = int(R.loc[R.date >= JUDGE0, "sess"].min())
    tm = win & R.ticker.isin(sw).to_numpy() & (R.r10 >= 0.20).to_numpy() & okp & (R.xs10 < cut13).to_numpy()
    cand_rows = np.flatnonzero(tm)
    keep, last = [], {}
    for i in cand_rows[np.lexsort((R.sess.to_numpy()[cand_rows], R.tk.to_numpy()[cand_rows]))]:
        t, s = R.tk.iat[i], R.sess.iat[i]
        if t not in last or s - last[t] >= 20:
            keep.append(i); last[t] = s
    T = P[keep]
    # shuffled templates from the raw panel path
    z = np.load(DIR / "logc.npz"); logc, q = z["logc"], z["q"]
    pz = np.load(DIR / "pca_L40.npz")
    Ts = ((zpaths(logc, q[np.array(keep)], 40, np.random.default_rng(SEED + 7)) - pz["mu"]) @ pz["comps"].T).astype(np.float32)
    lines.append(f"templates: {len(keep)} (swinger 40d paths before a >= +20% 10-session move, 1 per ticker per 20 sessions)")
    rows = np.flatnonzero(okp & (d >= "2008-01-01").to_numpy())
    nonsw = ~R.ticker.isin(sw).to_numpy()
    J = (d >= JUDGE0).to_numpy()
    sigs = {}
    for name, TT in (("real", T), ("shuffled", Ts)):
        ix = faiss.IndexFlatL2(NPC); ix.add(np.ascontiguousarray(TT))
        D, _ = ix.search(P[rows], 1)
        dist = np.full(len(R), np.nan); dist[rows] = D[:, 0]
        thr = np.nanquantile(dist[win & nonsw], 0.01)
        sigs[name] = np.isfinite(dist) & (dist <= thr) & J
        lines.append(f"  {name}: 1% threshold {thr:.4f}; judge signals {sigs[name].sum():,} on {R.loc[sigs[name], 'date'].nunique():,} dates")
    for h, H in enumerate(HS):
        n = 1186 + h
        L_, st = judge(R, sigs["real"], H, f"N {n} V2 template L40", placebo=sigs["shuffled"])
        lines += L_
        lines.append(f"    GATE N {n}: {gate(st)[1]}")
    print("\n".join(lines), flush=True)
    with OUT.open("a") as fh:
        fh.write("\n".join(lines) + "\n")
    pd.Series(sw).to_csv(DIR / "swingers.csv", index=False)
    np.save(DIR / "templates_L40.npy", T)


def rgti() -> None:
    cols = ["date", "sess", "tk", "ticker", "r1", "r5", "r10", "xs10"] + [f"p40_{k}" for k in range(NPC)]
    R = pd.read_parquet(DIR / "rows.parquet", columns=cols)
    P = R[[f"p40_{k}" for k in range(NPC)]].to_numpy(np.float32)
    me = R[R.ticker == "RGTI"]
    if me.empty:
        return
    i = me.index[-1]
    qv = P[i]
    lib = np.isfinite(P).all(1) & (R.xs10 < R.sess.iat[i]).to_numpy() & (R.ticker != "RGTI").to_numpy()
    dd = np.full(len(R), np.inf)
    dd[lib] = ((P[lib] - qv) ** 2).sum(1)
    order = np.argsort(dd)[:5000]
    nb = R.iloc[order].assign(dist=np.sqrt(dd[order]))
    nb = nb.drop_duplicates("ticker").head(20)
    x50 = R.iloc[order[:50]]
    lines = ["", f"== RGTI illustrative (NON-JUDGING): RGTI 40-session z-path ending {R.date.iat[i].date()} (last Sharadar bar); "
                 f"nearest analogs, one per ticker (PCA-8 distance; approx corr = 1 - d^2/80)",
             "  ticker  date        dist   ~corr   next1d   next5d   next10d"]
    for _, r_ in nb.iterrows():
        lines.append(f"  {r_.ticker:<7} {r_.date.date()}  {r_.dist:.3f}  {1 - r_.dist**2/80:.3f}  {r_.r1*100:+6.1f}%  {r_.r5*100:+6.1f}%  {r_.r10*100:+6.1f}%")
    allr = R.loc[lib]
    lines.append(f"  nearest 50 (any ticker): mean next5d {x50.r5.mean()*100:+.2f}% / median {x50.r5.median()*100:+.2f}%, "
                 f"next10d {x50.r10.mean()*100:+.2f}% / median {x50.r10.median()*100:+.2f}% "
                 f"vs all library paths next10d mean {allr.r10.mean()*100:+.2f}% median {allr.r10.median()*100:+.2f}%")
    print("\n".join(lines), flush=True)
    with OUT.open("a") as fh:
        fh.write("\n".join(lines) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", default="build")
    a = ap.parse_args()
    phases = ["build", "knn", "v1", "v2", "rgti"] if a.phase == "all" else a.phase.split(",")
    for p in phases:
        globals()[p]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
