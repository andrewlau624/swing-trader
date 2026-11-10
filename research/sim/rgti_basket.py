"""Study RGTI-BASKET (N 1190-1195): swing rules R1-R3 on RGTI-like baskets M1 (high-vol, VR5<=1) and M2
(range-bound vs own 120d history), Sharadar delisted-complete common stocks 1999-2026.
Pre-registration: research/drafts/round1_prose.md "Study RGTI-BASKET".

Stage 1 (build): per-ticker features + hypothetical trade outcome of every rule for every eligible row
  -> data/research/rgti_basket/panel.parquet
Stage 2 (judge): signals, controls (C1 vol-matched members, C2 vol-matched non-members, C3 shuffled date),
  stats, account sim -> data/research/program/rgti_basket_out.txt
Run: PYTHONPATH=.:../sharadar-data python3 -m research.sim.rgti_basket [build|judge|today]
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.ndimage import maximum_filter1d, minimum_filter1d

from research.sim.nx import is_common

ROOT = pathlib.Path(__file__).resolve().parents[2]
DD = ROOT / "data/research/rgti_basket"
PANEL = DD / "panel.parquet"
OUT = ROOT / "data/research/program/rgti_basket_out.txt"
STORE = pathlib.Path.home() / "data/sharadar"
START = "1998-06-01"
RULES = ("R1", "R2", "R3")
MEMB = ("M1", "M2")
NCELL = {("M1", "R1"): 1190, ("M1", "R2"): 1191, ("M1", "R3"): 1192,
         ("M2", "R1"): 1193, ("M2", "R2"): 1194, ("M2", "R3"): 1195}
PROGRAM_N = 1195


# ------------------------------------------------------------------ stage 1
def load_raw() -> pd.DataFrame:
    t = pd.read_parquet(STORE / "tickers.parquet", columns=["table", "ticker", "category"])
    t = t[(t.table == "SEP") & is_common(t.category.fillna(""))]
    keep = set(t.ticker)
    f = pq.ParquetFile(STORE / "stocks.parquet")
    parts = []
    cols = ["ticker", "date", "open", "high", "low", "close", "volume", "closeunadj"]
    for g in range(f.metadata.num_row_groups):
        x = f.read_row_group(g, columns=cols).to_pandas()
        x = x[x.ticker.isin(keep) & (x.date >= pd.Timestamp(START).date())]
        for c in cols[2:]:
            x[c] = x[c].astype("float32")
        parts.append(x)
    df = pd.concat(parts, ignore_index=True)
    df["date"] = pd.to_datetime(df["date"])
    df = df.drop_duplicates(["ticker", "date"]).sort_values(["ticker", "date"], kind="mergesort")
    return df.reset_index(drop=True)


def _sh(a, k, tid):
    """a shifted by k rows within ticker (k>0: past, k<0: future); NaN across ticker boundaries."""
    out = np.full(len(a), np.nan, dtype="float64")
    if k > 0:
        out[k:] = a[:-k]
        bad = np.ones(len(a), bool)
        bad[k:] = tid[k:] != tid[:-k]
    else:
        k = -k
        out[:-k] = a[k:]
        bad = np.ones(len(a), bool)
        bad[:-k] = tid[:-k] != tid[k:]
    out[bad] = np.nan
    return out


def _rsum(x, w, tid, pos):
    """trailing w-row sum within ticker (NaN until w rows of history); x NaN treated as 0."""
    cs = np.concatenate([[0.0], np.cumsum(np.nan_to_num(x))])
    n = len(x)
    i = np.arange(n)
    s = cs[i + 1] - cs[np.maximum(i + 1 - w, 0)]
    s[pos < w - 1] = np.nan
    return s


def _rmax(x, w, pos, fn):
    fill = -np.inf if fn is maximum_filter1d else np.inf
    y = fn(np.where(np.isfinite(x), x, fill), size=w, origin=(w - 1) // 2)
    y = y.astype("float64")
    y[pos < w - 1] = np.nan
    return y


def build() -> pd.DataFrame:
    df = load_raw()
    print("rows", len(df), "tickers", df.ticker.nunique(), "last", df.date.max(), flush=True)
    tk = df.ticker.unique()
    outs = []
    for i in range(0, len(tk), 2500):
        sub = df[df.ticker.isin(set(tk[i:i + 2500]))].reset_index(drop=True)
        outs.append(build_chunk(sub))
        print("chunk", i, len(outs[-1]), flush=True)
    out = pd.concat(outs, ignore_index=True)
    DD.mkdir(parents=True, exist_ok=True)
    out.to_parquet(PANEL)
    print("panel rows", len(out), flush=True)
    return out


def build_chunk(df: pd.DataFrame) -> pd.DataFrame:
    tid = pd.factorize(df.ticker)[0]
    first = np.r_[True, tid[1:] != tid[:-1]]
    pos = np.arange(len(df)) - np.maximum.accumulate(np.where(first, np.arange(len(df)), 0))
    o, h, l, c = (df[k].to_numpy("float64") for k in ("open", "high", "low", "close"))
    cu, v = df.closeunadj.to_numpy("float64"), df.volume.to_numpy("float64")
    dv = cu * v
    lr = np.log(c / _sh(c, 1, tid))
    lr[~np.isfinite(lr)] = np.nan
    F = {}
    nvalid120 = _rsum(np.isfinite(lr).astype(float), 120, tid, pos)
    s1, s2 = _rsum(lr, 120, tid, pos), _rsum(lr ** 2, 120, tid, pos)
    var120 = (s2 - s1 ** 2 / nvalid120) / (nvalid120 - 1)
    F["vol120"] = np.sqrt(var120)
    n20 = _rsum(np.isfinite(lr).astype(float), 20, tid, pos)
    a1, a2 = _rsum(lr, 20, tid, pos), _rsum(lr ** 2, 20, tid, pos)
    F["vol20"] = np.sqrt((a2 - a1 ** 2 / n20) / (n20 - 1))
    r5 = _rsum(lr, 5, tid, pos)                       # overlapping 5d log returns
    b1, b2 = _rsum(r5, 116, tid, pos), _rsum(r5 ** 2, 116, tid, pos)
    var5 = (b2 - b1 ** 2 / 116) / 115
    F["vr5"] = var5 / (5 * var120)
    F["nvalid120"] = nvalid120
    F["adv20"] = _rsum(dv, 20, tid, pos) / 20
    F["adv120"] = _rsum(dv, 120, tid, pos) / 120
    H20, L20 = _rmax(h, 20, pos, maximum_filter1d), _rmax(l, 20, pos, minimum_filter1d)
    H120, L120 = _rmax(h, 120, pos, maximum_filter1d), _rmax(l, 120, pos, minimum_filter1d)
    # M2 touches: runs of days in the last 20 with low <= 1.1*L20(d) / high >= H20(d)/1.1
    lt = np.zeros(len(df))
    ht = np.zeros(len(df))
    prev_l = np.zeros(len(df), bool)
    prev_h = np.zeros(len(df), bool)
    for k in range(19, -1, -1):                     # oldest -> newest; count run starts
        lk = (_sh(l, k, tid) if k else l) <= 1.10 * L20
        hk = (_sh(h, k, tid) if k else h) >= H20 / 1.10
        lt += lk & ~prev_l
        ht += hk & ~prev_h
        prev_l, prev_h = lk, hk
    F["m2"] = ((H20 - L20) <= 0.6 * (H120 - L120)) & (lt >= 2) & (ht >= 2) & (cu >= 2) & (cu <= 50) & (F["adv20"] >= 5e6)
    sma50 = _rsum(c, 50, tid, pos) / 50
    cm1 = _sh(c, 1, tid)
    min20prev = _rmax(cm1, 20, pos, minimum_filter1d)            # min close over d-20..d-1
    min20prev[pos < 20] = np.nan
    max5prev = _rmax(cm1, 5, pos, maximum_filter1d)
    max5prev[pos < 5] = np.nan
    ret1 = c / cm1 - 1
    F["s1"] = (cm1 <= min20prev + 1e-9) & (ret1 >= 0.08)
    F["s2"] = c <= L20 + 0.10 * (H20 - L20)
    F["s3"] = (c > sma50) & (c / max5prev - 1 <= -0.12)
    # outcomes from open d+1: one forward loop j=1..15 updates all three rules
    e = _sh(o, -1, tid)
    F["gap"] = e / c - 1
    mid = (H20 + L20) / 2
    n = len(df)
    R = {k: np.full(n, np.nan) for k in ("r1", "x1", "r2", "x2", "r3", "x3")}
    done = {k: ~np.isfinite(e) for k in ("1", "2", "3")}
    last_seen = e.copy()
    for j in range(1, 16):
        cj = _sh(c, -j, tid)
        fin = np.isfinite(cj)
        if j <= 10:
            oj, hj, lj = _sh(o, -j, tid), _sh(h, -j, tid), _sh(l, -j, tid)
            d1 = done["1"]
            have = fin & ~d1
            stop = have & (lj <= 0.90 * e)
            R["r1"][stop] = np.minimum(oj[stop], 0.90 * e[stop]) / e[stop] - 1
            R["x1"][stop] = j
            tgt = have & ~stop & (hj >= 1.15 * e)
            R["r1"][tgt] = np.maximum(oj[tgt], 1.15 * e[tgt]) / e[tgt] - 1
            R["x1"][tgt] = j
            d1 |= stop | tgt
            gone = ~d1 & ~fin
            R["r1"][gone] = last_seen[gone] / e[gone] - 1
            R["x1"][gone] = j - 1
            d1 |= gone
            if j == 10:
                rest = ~d1
                R["r1"][rest] = cj[rest] / e[rest] - 1
                R["x1"][rest] = 10
                d1 |= rest
            del oj, hj, lj
            d3 = done["3"]
            hit = ~d3 & fin & (j == 10)
            R["r3"][hit] = cj[hit] / e[hit] - 1
            R["x3"][hit] = 10
            gone = ~d3 & ~fin
            R["r3"][gone] = last_seen[gone] / e[gone] - 1
            R["x3"][gone] = j - 1
            d3 |= hit | gone
        d2 = done["2"]
        hit = ~d2 & fin & ((cj >= mid) | (j == 15))
        R["r2"][hit] = cj[hit] / e[hit] - 1
        R["x2"][hit] = j
        gone = ~d2 & ~hit & ~fin
        R["r2"][gone] = last_seen[gone] / e[gone] - 1
        R["x2"][gone] = j - 1
        d2 |= hit | gone
        last_seen = np.where(fin, cj, last_seen)
    F.update(R)
    for k in ("r1", "r2", "r3"):                    # zero-session exits (entry bar was last): drop
        F[k][F["x" + k[1]] < 1] = np.nan
    F["e_unadj"] = e * cu / c
    out = pd.DataFrame({"ticker": df.ticker.values, "date": df.date.values, "cu": cu.astype("float32")})
    for k, a in F.items():
        out[k] = a.astype("float32") if a.dtype != bool else a
    # keep rows that can matter: month-ends (for M1 formation) or price/ADV-eligible rows with an entry
    me = out.date.dt.to_period("M") != out.date.shift(-1).dt.to_period("M")
    me = me | (out.ticker != out.ticker.shift(-1))
    elig = (out.cu >= 2) & (out.cu <= 50) & (out.adv20 >= 5e6) & np.isfinite(out.gap)
    out["month_end"] = me.values
    return out[elig | me].reset_index(drop=True)


# ------------------------------------------------------------------ stage 2
def m1_membership(P: pd.DataFrame) -> pd.DataFrame:
    """Month-end formation -> (ticker, month m) member / nonmember-pool flags."""
    f = P[P.month_end & (P.nvalid120 >= 100)].copy()
    f = f[(f.cu >= 2) & (f.cu <= 50) & (f.adv120 >= 5e6) & np.isfinite(f.vol120)]
    f["m"] = (f.date.dt.to_period("M") + 1)
    f = f.sort_values("date").drop_duplicates(["ticker", "m"], keep="last")
    f["vrank"] = f.groupby("m").vol120.rank(pct=True)
    top = f[f.vrank > 0.9]
    top = top.assign(m1=top.vr5 <= 1.0, m1pool=top.vr5 > 1.0)
    return top[["ticker", "m", "m1", "m1pool"]]


def load_judge_frame():
    P = pd.read_parquet(PANEL)
    P = P[(P.cu >= 2) & (P.cu <= 50) & (P.adv20 >= 5e6) & np.isfinite(P.gap)].copy()
    P["m"] = P.date.dt.to_period("M")
    mem = m1_membership(pd.read_parquet(PANEL, columns=["ticker", "date", "cu", "adv120", "vol120", "vr5",
                                                        "nvalid120", "month_end"]))
    P = P.merge(mem, on=["ticker", "m"], how="left")
    P["m1"] = P.m1.fillna(False).astype(bool)
    P["m1pool"] = P.m1pool.fillna(False).astype(bool)
    P["m2"] = P.m2.astype(bool)
    P["m2pool"] = ~P.m2
    P["cost"] = np.where(P.adv20 >= 1e7, 5.0, 10.0) / 1e4
    return P.reset_index(drop=True)


def bench():
    from sharadar import prices
    q = prices(["QQQ", "SPY"], "1998-01-01", None, adjust="total", source="funds")
    q["date"] = pd.to_datetime(q["date"])
    return {t: g.set_index("date").sort_index() for t, g in q.groupby("ticker")}


def mtstat(x, months):
    s = pd.Series(np.asarray(x, float)).groupby(np.asarray(months)).mean()
    return s.mean() / (s.std(ddof=1) / np.sqrt(len(s))) if len(s) > 2 else np.nan


def matched_draw(P, sig_idx, pool_mask, rng, rcol, exclude_mask=None):
    """For each signal row: random row on the same date from pool_mask with nearest vol20 (one of the 3
    nearest, random). Returns the matched outcome (NaN when no candidate)."""
    out = np.full(len(sig_idx), np.nan)
    pools = P[pool_mask & np.isfinite(P[rcol])]
    if exclude_mask is not None:
        pools = pools[~exclude_mask[pools.index]]
    g = {d: (x.vol20.to_numpy(), x[rcol].to_numpy()) for d, x in pools.groupby("date")}
    dates = P.date.to_numpy()[sig_idx]
    vols = P.vol20.to_numpy()[sig_idx]
    for i, (d, vv) in enumerate(zip(dates, vols)):
        z = g.get(d)
        if z is None or len(z[0]) == 0:
            continue
        k = min(3, len(z[0]))
        nn = np.argpartition(np.abs(z[0] - vv), k - 1)[:k]
        out[i] = z[1][rng.choice(nn)]
    return out


def account_sim(S, rcol, xcol, equity0, K=5, seed=0):
    """K equal slots, whole shares, first-come by entry date (random tie-break), realized-PnL equity."""
    rng = np.random.default_rng(seed)
    S = S.assign(tb=rng.random(len(S))).sort_values(["date", "tb"])
    eq = equity0
    openp = []        # (exit_date, pnl)
    dates_idx = None
    taken = 0
    maxc = 0
    for d, g in S.groupby("date", sort=True):
        still = []
        for ex, pnl in openp:
            if ex <= d:
                eq += pnl
            else:
                still.append((ex, pnl))
        openp = still
        for eu, rr, cc, ex in zip(g.e_unadj.values, g[rcol].values, g.cost.values, g.exit_date.values):
            if len(openp) >= K:
                break
            slot = eq / K
            sh = np.floor(slot / eu) if eu > 0 else 0
            if sh < 1:
                continue
            openp.append((ex, sh * eu * (rr - 2 * cc)))
            taken += 1
        maxc = max(maxc, len(openp))
    for ex, pnl in openp:
        eq += pnl
    yrs = (S.date.max() - S.date.min()).days / 365.25
    return dict(cagr=(eq / equity0) ** (1 / yrs) - 1 if eq > 0 else -1, taken=taken, per_yr=taken / yrs)


def judge():
    P = load_judge_frame()
    B = bench()
    sessions = B["QQQ"].index
    qo, qc = B["QQQ"]["open"], B["QQQ"]["close"]
    lines = []
    p = lines.append
    p("Study RGTI-BASKET (N 1190-1195) - swing rules on RGTI-like baskets; pre-reg round1_prose.md")
    p(f"panel eligible rows {len(P):,}, dates {P.date.min().date()}..{P.date.max().date()}")
    mem_ct = P.groupby("date")[["m1", "m2"]].sum()
    p(f"avg members/day M1 {mem_ct.m1.mean():.0f}, M2 {mem_ct.m2.mean():.0f}")
    rng = np.random.default_rng(1190)
    sidx = pd.Index(sessions)
    summary = []
    from research.sim.hpool_sharadar import dsr
    for M in MEMB:
        for R in RULES:
            k = R[1]
            rcol, xcol, scol = "r" + k, "x" + k, "s" + k
            sig = P[P[M.lower()] & P[scol] & np.isfinite(P[rcol])].copy()
            # one open position per name per rule: drop signals while a prior trade on that name is open
            sig = sig.sort_values(["ticker", "date"])
            keep = []
            busy_until = {}
            pos_in = {d: i for i, d in enumerate(sessions)}
            for t, d, x in zip(sig.ticker.values, sig.date.values, sig[xcol].values):
                i = pos_in.get(pd.Timestamp(d), None)
                if i is None:
                    keep.append(False)
                    continue
                if busy_until.get(t, -1) >= i:
                    keep.append(False)
                    continue
                busy_until[t] = i + 1 + int(x)
                keep.append(True)
            sig = sig[np.array(keep)]
            ii = np.array([pos_in[pd.Timestamp(d)] for d in sig.date.values])
            ent = sessions[np.minimum(ii + 1, len(sessions) - 1)]
            exd = sessions[np.minimum(ii + 1 + sig[xcol].astype(int).values - 1, len(sessions) - 1)]
            sig["exit_date"] = exd
            sig["qqq"] = qc.reindex(exd).values / qo.reindex(ent).values - 1
            sig_ix = sig.index.to_numpy()
            # controls (same date, nearest vol20) on the full eligible frame
            excl = np.zeros(len(P), bool)
            excl[sig_ix] = True
            c1 = np.vstack([matched_draw(P, sig_ix, P[M.lower()].values, rng, rcol, excl) for _ in range(20)])
            c2 = np.vstack([matched_draw(P, sig_ix, P[M.lower() + "pool"].values, rng, rcol) for _ in range(5)])
            sig["c1"] = np.nanmean(c1, axis=0)
            sig["c2"] = np.nanmean(c2, axis=0)
            # C3 shuffled date: same name random session within +-250 rows of the frame
            c3 = []
            Pv = P[np.isfinite(P[rcol])]
            byt = {t: (g.date.values.astype("datetime64[D]").astype(np.int64), g[rcol].to_numpy())
                   for t, g in Pv.groupby("ticker")}
            sd = sig.date.values.astype("datetime64[D]").astype(np.int64)
            for _ in range(5):
                v = np.full(len(sig), np.nan)
                for n, (t, d) in enumerate(zip(sig.ticker.values, sd)):
                    dd, rr = byt.get(t, (None, None))
                    if dd is None:
                        continue
                    i0, i1 = np.searchsorted(dd, d - 365), np.searchsorted(dd, d + 365)
                    if i1 > i0:
                        v[n] = rr[rng.integers(i0, i1)]
                c3.append(v)
            sig["c3"] = np.nanmean(np.vstack(c3), axis=0)
            for period, lo, hi in (("FIT 1999-2012", "1999-01-01", "2012-12-31"), ("JUDGE 2013-26", "2013-01-01", "2027-01-01"),
                                   ("  2013-19", "2013-01-01", "2019-12-31"), ("  2020-26", "2020-01-01", "2027-01-01"),
                                   ("  2020", "2020-01-01", "2020-12-31"), ("  2022", "2022-01-01", "2022-12-31"),
                                   ("  2024-25", "2024-01-01", "2025-12-31")):
                S = sig[(sig.date >= lo) & (sig.date <= hi)]
                if len(S) < 5:
                    p(f"{M} {R} {period}: n={len(S)}")
                    continue
                net = S[rcol] - 2 * S.cost
                net2 = S[rcol] - 4 * S.cost
                net3 = S[rcol] - 6 * S.cost
                ex1 = S[rcol] - S.c1                 # gross excess over control (same costs both sides)
                ok = np.isfinite(ex1)
                srt = np.sort(ex1[ok].values)
                exx5 = srt[:-5].mean() if len(srt) > 10 else np.nan
                plc = np.nanmean(c1[:, np.isin(sig_ix, S.index.to_numpy())], axis=1)  # each draw's mean
                ex2 = S[rcol] - S.c2
                ex3 = S[rcol] - S.c3
                X = S.qqq.values
                Y = net.values
                okq = np.isfinite(X)
                beta = np.cov(X[okq], Y[okq])[0, 1] / np.var(X[okq], ddof=1) if okq.sum() > 5 else np.nan
                alpha = np.mean(Y[okq] - beta * X[okq]) if okq.sum() > 5 else np.nan
                mo = S.date.dt.to_period("M").values
                p(f"{M} {R} {period}: n {len(S)} net {net.mean()*1e4:+.0f}bp (2x {net2.mean()*1e4:+.0f}, 3x {net3.mean()*1e4:+.0f}) "
                  f"t {mtstat(net, mo):.2f} med {net.median()*1e4:+.0f} hit {(net>0).mean():.2f} | C1 {S.c1.mean()*1e4:+.0f} "
                  f"ex1 {ex1.mean()*1e4:+.0f} t {mtstat(ex1[ok], mo[ok.values]):.2f} exTop5 {exx5*1e4:+.0f} "
                  f"plc95 {(np.nanpercentile(plc,95)-np.nanmean(plc))*1e4:+.0f} | ex2 {np.nanmean(ex2)*1e4:+.0f} "
                  f"ex3 {np.nanmean(ex3)*1e4:+.0f} | beta {beta:.2f} alpha {alpha*1e4:+.0f} | gap {S.gap.mean()*1e4:+.0f} "
                  f"hold {S[xcol].mean():.1f}")
                if period.startswith("JUDGE"):
                    summary.append(dict(cell=f"{M}{R}", N=NCELL[(M, R)], n=len(S), net=net.mean(), net2=net2.mean(),
                                        ex1=ex1.mean(), t1=mtstat(ex1[ok], mo[ok.values]), exx5=exx5,
                                        plc95=np.nanpercentile(plc, 95) - np.nanmean(plc), ex2=np.nanmean(ex2),
                                        alpha=alpha, S=S, ex1s=ex1, rcol=rcol, xcol=xcol))
            p("")
    # gates + account sims on judge
    p("=== JUDGE gate (pre-registered) ===")
    for s in summary:
        S = s["S"]
        h1 = s["ex1s"][S.date < "2020-01-01"].mean()
        h2 = s["ex1s"][S.date >= "2020-01-01"].mean()
        sims = {E: account_sim(S, s["rcol"], s["xcol"], E) for E in (2300, 10000, 25000)}
        turns = sims[10000]["per_yr"]
        ceil = s["ex1"] * turns * 0.20 * 0.5
        dpr, sr, sr0 = dsr(s["ex1s"].dropna().values, PROGRAM_N)
        gates = dict(a=s["net2"] > 0, b=(s["ex1"] > s["plc95"]) and s["t1"] >= 2, c=s["ex2"] > 0,
                     d=(s["exx5"] > 0) and h1 > 0 and h2 > 0, e=s["alpha"] > 0, f=ceil >= 0.08)
        verdict = "PASS" if all(gates.values()) else "KILL"
        p(f"{s['cell']} (N {s['N']}): {verdict} gates {''.join(k if v else '.' for k, v in gates.items())} | "
          f"ex1 {s['ex1']*1e4:+.0f}bp t {s['t1']:.2f} halves {h1*1e4:+.0f}/{h2*1e4:+.0f} | ceiling@$10k {ceil*100:+.1f}pp/yr | "
          f"DSR {dpr:.2f} | sim CAGR $2.3k {sims[2300]['cagr']*100:+.1f}% $10k {sims[10000]['cagr']*100:+.1f}% "
          f"$25k {sims[25000]['cagr']*100:+.1f}% ({turns:.0f} trades/yr)")
    qq = qc[qc.index >= "2013-01-01"]
    p(f"QQQ total-return CAGR 2013-26: {((qq.iloc[-1]/qq.iloc[0])**(365.25/(qq.index[-1]-qq.index[0]).days)-1)*100:.1f}%")
    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "build":
        build()
    elif cmd == "judge":
        judge()
