"""Study LUCK-B1: seeded random-rule discovery batch, grammar 1 (pre-reg round1_prose.md ~:6210).

Discovery 2006-01..2015-12 ONLY (signal dates). Feature warm-up loads from 2003-01; windows of
late-2015 signals reach into early 2016 prices (needed for exit opens); no 1998-2005 outcome and no
2016+ signal outcome is scored. Run: PYTHONPATH=. python3 -m research.sim.luck_gen

Choices the registration left open (stated, not tuned):
 - f1 is always a cross-sectional feature (19: ret1/5/20/60/250, ibs, gap, range, vol20, volratio,
   logadv20, logprice, dist_hi252, dist_lo252, logmcap, pe, pb, ps, evebitda). f2 (50% of rules) is a
   cross-sectional tercile (80%) or a calendar day filter (20%: day-of-week or month).
 - Cross-sectional rank percentiles are over eligible names with a non-NaN feature that day.
 - "every h-th signal date" = every h-th date on which that rule has >= 10 names.
 - Pass also requires n >= 30 signal dates (guard; t on tiny n is meaningless).
 - Net = side*(EW selected - EW eligible universe, same window) - 20bp, for every horizon.
 - Permutation null shuffles each cross-sectional feature's values independently across the
   valid names within each date (calendar filters unpermuted). Placebo lags all features 252 rows.
"""
from __future__ import annotations
import os, sys, time, pathlib
import numpy as np, pandas as pd, pyarrow.parquet as pq
from multiprocessing import Pool

SH = os.path.expanduser("~/data/sharadar")
OUTD = pathlib.Path("data/research/program")
LOAD0, LOAD1 = "2003-01-01", "2016-03-31"
D0, D1 = "2006-01-01", "2015-12-31"
SEED, NRULES, COST = 20261012, 1000, 0.0020
FEATS = ["ret1", "ret5", "ret20", "ret60", "ret250", "ibs", "gap", "range", "vol20", "volratio",
         "logadv20", "logprice", "dist_hi", "dist_lo", "logmcap", "pe", "pb", "ps", "evebitda"]
HORIZ = ["ovn", 1, 5, 20]
G = {}


def load():
    tk = pq.read_table(f"{SH}/tickers.parquet", columns=["table", "ticker", "category"]).to_pandas()
    tk = tk[(tk["table"] == "SEP") & tk["category"].astype(str).str.startswith("Domestic Common Stock")]
    keep = set(tk["ticker"])
    flt = [("date", ">=", pd.Timestamp(LOAD0)), ("date", "<=", pd.Timestamp(LOAD1))]
    s = pq.read_table(f"{SH}/stocks.parquet", columns=["ticker", "date", "open", "high", "low", "close", "volume", "closeadj", "closeunadj"], filters=flt).to_pandas()
    s = s[s["ticker"].isin(keep)]
    s["date"] = pd.to_datetime(s["date"])
    d = pq.read_table(f"{SH}/daily.parquet", columns=["ticker", "date", "marketcap", "pe", "pb", "ps", "evebitda"], filters=flt).to_pandas()
    d = d[d["ticker"].isin(keep)]
    d["date"] = pd.to_datetime(d["date"])
    dates = pd.DatetimeIndex(sorted(s["date"].unique()))
    tick = pd.Index(sorted(s["ticker"].unique()))
    s = s.drop_duplicates(["ticker", "date"], keep="last")
    d = d.drop_duplicates(["ticker", "date"], keep="last")
    def piv(df, c):
        return df.pivot(index="date", columns="ticker", values=c).reindex(index=dates, columns=tick).astype("float32")
    M = {c: piv(s, c) for c in ["open", "high", "low", "close", "volume", "closeadj", "closeunadj"]}
    F = {c: piv(d, c) for c in ["marketcap", "pe", "pb", "ps", "evebitda"]}
    return dates, tick, M, F


def build(dates, tick, M, F):
    close, opn, hi, lo, vol, cadj, raw = (M[k] for k in ["close", "open", "high", "low", "volume", "closeadj", "closeunadj"])
    printed = close.notna()
    oadj = opn * cadj / close                      # guard against raw-open split bug
    cadj_f = cadj.ffill()
    oadj_f = oadj.where(oadj.notna(), cadj_f).ffill()
    dv = close * vol
    adv = dv.rolling(20, min_periods=15).median()
    elig = printed & (raw >= 5) & (adv >= 5e6)
    ret = lambda n: cadj / cadj.shift(n) - 1
    X = {}
    X["ret1"], X["ret5"], X["ret20"], X["ret60"], X["ret250"] = ret(1), ret(5), ret(20), ret(60), ret(250)
    X["ibs"] = (close - lo) / (hi - lo).where(hi > lo)
    X["gap"] = opn / close.shift(1) - 1
    X["range"] = (hi - lo) / close
    X["vol20"] = cadj.pct_change(fill_method=None).rolling(20, min_periods=15).std()
    X["volratio"] = vol / vol.rolling(20, min_periods=15).mean()
    X["logadv20"] = np.log(dv.rolling(20, min_periods=15).mean())
    X["logprice"] = np.log(raw)
    X["dist_hi"] = cadj / cadj.rolling(252, min_periods=200).max() - 1
    X["dist_lo"] = cadj / cadj.rolling(252, min_periods=200).min() - 1
    X["logmcap"] = np.log(F["marketcap"])
    for c in ["pe", "pb", "ps", "evebitda"]:
        X[c] = F[c]
    # forward returns (rows = signal date t)
    n = len(cadj)
    R = {}
    nxt = oadj_f.shift(-1)
    R["ovn"] = nxt / cadj_f - 1
    for h in (1, 5, 20):
        R[h] = oadj_f.shift(-1 - h) / nxt - 1
    return elig, X, R


def pct_rank(x, elig):
    """cross-sectional percentile in (0,1] among eligible & non-NaN; NaN elsewhere."""
    v = x.where(elig).replace([np.inf, -np.inf], np.nan)
    return v.rank(axis=1, pct=True).astype("float32")


def make_rules():
    rng = np.random.default_rng(SEED)
    rules = []
    for i in range(NRULES):
        f1 = FEATS[rng.integers(len(FEATS))]; d1 = int(rng.choice([1, 10]))
        r = dict(id=i, f1=f1, d1=d1, f2=None, k2=None, hz=HORIZ[rng.integers(4)], side=int(rng.choice([1, -1])))
        if rng.random() < 0.5:
            if rng.random() < 0.8:
                r["f2"] = FEATS[rng.integers(len(FEATS))]; r["k2"] = int(rng.choice([1, 3]))
            else:
                if rng.random() < 5 / 17:
                    r["f2"] = "dow"; r["k2"] = int(rng.integers(5))
                else:
                    r["f2"] = "month"; r["k2"] = int(rng.integers(1, 13))
        rules.append(r)
    return rules


def describe(r):
    s = f"{r['f1']} decile{r['d1']}"
    if r["f2"]:
        s += f" & {r['f2']}={r['k2']}" if r["f2"] in ("dow", "month") else f" & {r['f2']} tercile{r['k2']}"
    return f"{'long' if r['side'] > 0 else 'short'} {s} h={r['hz']}"


def masks_for(rule, P, cal, elig):
    a = P[rule["f1"]]
    m = (a <= 0.1) if rule["d1"] == 1 else (a > 0.9)
    if rule["f2"] in ("dow", "month"):
        m = m & (cal[rule["f2"]] == rule["k2"])[:, None]
    elif rule["f2"]:
        b = P[rule["f2"]]
        m = m & ((b <= 1 / 3) if rule["k2"] == 1 else (b > 2 / 3))
    return m & elig


def score_all(rules, P, cal, elig, Rm, half_mask, valid_univ):
    """returns list of dict stats per rule"""
    # universe mean per horizon
    U = {}
    for h, Rh in Rm.items():
        ok = elig & np.isfinite(Rh)
        Z = np.where(ok, Rh, 0).astype("float32")
        U[h] = (Z.sum(1) / np.maximum(ok.sum(1), 1)).astype("float64")
    out = []
    for r in rules:
        m = masks_for(r, P, cal, elig)
        Rh = Rm[r["hz"]]
        ok = m & np.isfinite(Rh)
        cnt = ok.sum(1)
        sm = np.einsum("ij,ij->i", np.where(ok, Rh, 0).astype("float32"), np.ones_like(ok, dtype="float32")) if False else np.where(ok, Rh, 0).sum(1, dtype="float64")
        dates_ok = np.where(cnt >= 10)[0]
        h = r["hz"]; step = 1 if h == "ovn" else h
        idx = dates_ok[::step]
        net = r["side"] * (sm[idx] / cnt[idx] - U[r["hz"]][idx]) - COST
        n = len(idx)
        st = dict(n=n, mean_bp=np.nan, t=np.nan, h1_bp=np.nan, h2_bp=np.nan, med_bp=np.nan, passed=False)
        if n >= 2:
            mu, sd = net.mean(), net.std(ddof=1)
            t = mu / (sd / np.sqrt(n)) if sd > 0 else 0.0
            hm = half_mask[idx]
            h1 = net[~hm].mean() if (~hm).any() else np.nan
            h2 = net[hm].mean() if hm.any() else np.nan
            med = np.median(net)
            st.update(mean_bp=mu * 1e4, t=t, h1_bp=h1 * 1e4, h2_bp=h2 * 1e4, med_bp=med * 1e4)
            st["passed"] = bool(n >= 30 and mu > 0 and t >= 3.0 and h1 > 0 and h2 > 0 and med > 0)
        out.append(st)
    return out


def run_job(job):
    kind, seed = job
    if kind == "shift":
        return kind, seed, score_all(G["rules"], G["P_sh"], G["cal_sh"], G["elig"], G["R"], G["hm"], None)
    return run_variant(job)


def run_variant(args):
    kind, seed = args
    rules, P0, cal0, elig, Rm, hm = G["rules"], G["P"], G["cal"], G["elig"], G["R"], G["hm"]
    if kind == "perm":
        rng = np.random.default_rng(seed)
        P = {}
        for f in FEATS:
            a = P0[f]
            valid = np.isfinite(a)
            keys = rng.random(a.shape, dtype="float32"); keys[~valid] = 2.0
            order = np.argsort(keys, axis=1)
            sv = np.sort(np.where(valid, a, np.inf), axis=1); sv[~np.isfinite(sv)] = np.nan
            new = np.full_like(a, np.nan)
            np.put_along_axis(new, order, sv, axis=1)
            P[f] = new
        cal = cal0
    elif kind == "shift":
        L = 252
        P = {}
        for f in FEATS:
            a = np.full_like(P0[f], np.nan); a[L:] = P0[f][:-L]; P[f] = a
        cal = {}
        for k, v in cal0.items():
            a = np.full_like(v, -1); a[L:] = v[:-L]; cal[k] = a
    else:
        P, cal = P0, cal0
    st = score_all(rules, P, cal, elig, Rm, hm, None)
    return kind, seed, st


def main():
    t0 = time.time()
    dates, tick, M, F = load()
    print("loaded", len(dates), len(tick), f"{time.time()-t0:.0f}s", flush=True)
    elig, X, R = build(dates, tick, M, F)
    del M, F
    pr = {f: pct_rank(X[f], elig) for f in FEATS}
    del X
    sel = (dates >= D0) & (dates <= D1)
    ncol = elig.values[sel].any(0)
    # sanity: universe size per year
    ee = elig.loc[sel]
    sz = ee.sum(1).groupby(ee.index.year).mean().round(0)
    # slice to discovery rows (keep the 252-row history for the shift placebo: slice after shifting is
    # equivalent to shifting on the full axis, so keep rows from index start of sel minus 252)
    i0 = int(np.argmax(sel)); i1 = int(len(sel) - np.argmax(sel[::-1]))
    lo = i0 - 252
    assert lo >= 0
    cs = np.where(ncol)[0]
    P_full = {f: pr[f].values[lo:i1][:, cs] for f in FEATS}
    dt = dates[lo:i1]
    elig_full = elig.values[lo:i1][:, cs]
    R_full = {h: R[h].values[lo:i1][:, cs].astype("float32") for h in HORIZ}
    cal_full = {"dow": dt.dayofweek.values.astype("int8"), "month": dt.month.values.astype("int8")}
    # variants run on the full (history+discovery) block, but scoring restricted to discovery rows:
    # do shift/perm on the block and then slice rows
    G.update(rules=make_rules(), dt=dt)
    def slice_d(d):
        return {k: v[252:] for k, v in d.items()}
    # shifted placebo needs history: build shifted version here, then slice
    def shifted(L=252):
        P = {}
        for f in FEATS:
            a = np.full_like(P_full[f], np.nan); a[L:] = P_full[f][:-L]; P[f] = a[252:]
        cal = {}
        for k, v in cal_full.items():
            a = np.full_like(v, -1); a[L:] = v[:-L]; cal[k] = a[252:]
        return P, cal
    P_sh, cal_sh = shifted()
    G.update(P=slice_d(P_full), cal={k: v[252:] for k, v in cal_full.items()}, elig=elig_full[252:],
             R={h: v[252:] for h, v in R_full.items()}, hm=(dt[252:] >= pd.Timestamp("2011-01-01")))
    G["P_sh"], G["cal_sh"] = P_sh, cal_sh
    del pr, R
    # sanity checks (known sign): ret1 decile1 vs decile10 unconditional returns
    Pn, E, Rn = G["P"], G["elig"], G["R"]
    sanity = []
    for h in HORIZ:
        for d, lab in ((1, "D1(losers)"), (10, "D10(winners)")):
            m = ((Pn["ret1"] <= 0.1) if d == 1 else (Pn["ret1"] > 0.9)) & E & np.isfinite(Rn[h])
            ok = E & np.isfinite(Rn[h])
            xs = (np.where(m, Rn[h], 0).sum(1) / np.maximum(m.sum(1), 1) - np.where(ok, Rn[h], 0).sum(1) / np.maximum(ok.sum(1), 1))
            sanity.append(f"ret1 {lab} h={h}: mean excess per signal date {xs.mean()*1e4:+.1f}bp (gross, all dates, overlapping for h>1)")
    # lookahead guard: ret1 feature at t must not correlate w/ ovn return perfectly; report corr of ret1 pct and R_ovn
    # run variants
    rules = G["rules"]
    jobs = [("real", 0)] + [("perm", s) for s in range(1, 11)] + [("shift", 0)]
    def init():
        pass
    # shift variant uses P_sh: temporarily handle by passing through G
    res = {}
    nproc = min(6, os.cpu_count() or 2)
    G_real = ("real", 0)
    # patch run_variant for shift to use prebuilt arrays
    import multiprocessing as mp
    with mp.get_context("fork").Pool(nproc) as pool:
        outs = pool.map(run_job, jobs, chunksize=1)
    for kind, seed, st in outs:
        res[(kind, seed)] = st
    cnt = {k: sum(s["passed"] for s in v) for k, v in res.items()}
    real = cnt[("real", 0)]
    nulls = [cnt[("perm", s)] for s in range(1, 11)]
    plc = cnt[("shift", 0)]
    verdict_ok = real > max(nulls) and real > 3 * np.mean(nulls)
    rdf = pd.DataFrame(rules)
    rdf["desc"] = [describe(r) for r in rules]
    rs = pd.DataFrame(res[("real", 0)])
    rdf = pd.concat([rdf, rs], axis=1)
    rdf["hz"] = rdf["hz"].astype(str); rdf["k2"] = rdf["k2"].astype("float")
    rdf.to_parquet(OUTD / "luck_b1_rules.parquet")
    top = rdf[rdf["passed"]].sort_values("t", ascending=False).head(20)
    def fam(r):
        f = []
        if r["f1"] == "ibs" or r["f2"] == "ibs": f.append("IBS")
        if r["hz"] == "ovn" and (r["f1"] in ("ret1", "ibs", "dist_lo") or r["f2"] in ("ret1", "ibs")) and r["side"] > 0: f.append("night-leg/loser-bounce")
        if r["f1"] in ("ret1", "ret5", "ret20") and r["side"] * (1 if r["d1"] == 1 else -1) > 0: f.append("ST-reversal")
        if r["f1"] in ("ret60", "ret250", "dist_hi") and r["side"] * (1 if r["d1"] == 10 else -1) > 0: f.append("momentum")
        if r["f1"] in ("pe", "pb", "ps", "evebitda") : f.append("value")
        if r["f1"] in ("logmcap", "logadv20", "logprice"): f.append("size/liq")
        if r["f1"] in ("vol20", "range"): f.append("vol-tilt")
        return ",".join(f) if f else "-"
    L = []
    L.append("LUCK-B1 results (discovery 2006-01..2015-12; confirmation set NOT touched)")
    L.append(f"seed {SEED}, {NRULES} rules; runtime {time.time()-t0:.0f}s")
    L.append("Universe (mean eligible names/day by year): " + ", ".join(f"{y}:{int(v)}" for y, v in sz.items()))
    L.append("Sanity (known sign): " + " | ".join(sanity))
    L.append(f"REAL pass count: {real}")
    L.append(f"NULL permutation pass counts (seeds 1..10): {nulls}  max {max(nulls)}  mean {np.mean(nulls):.2f}")
    L.append(f"PLACEBO (252d lag) pass count: {plc}")
    L.append(f"BATCH VERDICT: {'COUNTS (real > max null and > 3x mean null)' if verdict_ok else 'LUCK (fails null test) - log and stop, no survivors'}")
    L.append("")
    L.append("Top 20 passing rules by t (n dates, net mean bp, t, half1 2006-10 bp, half2 2011-15 bp, median bp, family flag):")
    for _, r in top.iterrows():
        L.append(f"  #{r['id']:<4} {r['desc']:<60} n={r['n']:<4} mean={r['mean_bp']:+7.1f} t={r['t']:.2f} h1={r['h1_bp']:+7.1f} h2={r['h2_bp']:+7.1f} med={r['med_bp']:+7.1f} fam={fam(r)}")
    L.append(f"(passing rules total: {int(rdf['passed'].sum())}; listed {len(top)})")
    (OUTD / "luck_b1_out.txt").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
