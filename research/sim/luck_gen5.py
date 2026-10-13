"""Study LUCK-B5: random-rule discovery batch, grammar 5 (IBES analyst-forecast features). Pre-reg: round1_prose.md "Study LUCK-B5".
Run: PYTHONPATH=. .venv/bin/python -m research.sim.luck_gen5   (after research/sim/luck_b5_pull.py)
Scoring frame identical to luck_gen4 (reuses its ranks()/run()). Discovery only (signal dates 2001-01..2010-12); 2011-2019 never pulled.
Open choices (stated): link = ibcrsphist score<=2, lowest score kept per (permno,statpers); IBES row usable from first trading day AFTER statpers, carried
forward <=45 calendar days; FY1 revision = change vs the previous statpers record of the same fpedats (1m: gap 20-45 cal days; 3m: record 3 back, gap 70-120d);
LTG change = vs record 3 back (70-120d); price scaling = CRSP |prc| on d; universe = luck_gen4 universe (common, >=$5, 20d med $vol>=$10M) AND valid FY1 mean within 45d;
halves = signal date < 2006-01-01; all other choices as luck_gen4 (greedy non-overlap, 10bp RT, >=5 names, t on date means, ann = mean*252/h).
"""
import time
from pathlib import Path
import numpy as np, pandas as pd
from research.sim import luck_gen4 as G

C = Path("data/research/wrds_b4"); C5 = Path("data/research/wrds_b5"); OUTD = Path("data/research/program")
SEED = 20261014; NRULES = 1000; D0 = G.D0; D1 = G.D1
FEATS = ["ey", "disp", "dispm", "rev1", "rev3", "breadth", "numest", "dnum3", "ltg", "dltg", "gap", "ret5", "ret21", "size"]
HZ = G.HZ


def prev_ok(df, grp, n, lo, hi):
    g = df.groupby(grp)
    gap = (df["statpers"] - g["statpers"].shift(n)).dt.days
    return g, gap.between(lo, hi)


def build():
    dsf = pd.read_parquet(C / "dsf.parquet")
    dsf = dsf[dsf["date"] <= "2011-02-04"]
    for c in ("prc", "openprc", "ret", "vol", "shrout"):   # fix (disclosed): nullable NA dtypes -> float64
        dsf[c] = pd.to_numeric(dsf[c], errors="coerce").astype("float64")
    dates = pd.DatetimeIndex(np.sort(dsf["date"].unique()))
    perm = np.sort(dsf["permno"].unique()); pi = {p: i for i, p in enumerate(perm)}
    D, N = len(dates), len(perm)
    ri = np.searchsorted(dates.values, dsf["date"].values); ci = dsf["permno"].map(pi).values
    def mat(v):
        M = np.full((D, N), np.nan, dtype="float64"); M[ri, ci] = v; return M
    prc = mat(dsf["prc"].abs().values); opn = mat(dsf["openprc"].abs().values); ret = mat(dsf["ret"].values)
    vol = mat(dsf["vol"].values); shr = mat(dsf["shrout"].values * 1000.0)
    # delisting return folded into the delisting date (or next dsf row if the date is absent)
    dl = pd.read_parquet(C / "delist.parquet").dropna(subset=["dlstdt"])
    dl = dl[dl["permno"].isin(pi)]
    dlr = pd.to_numeric(dl["dlret"], errors="coerce").astype("float64")
    perf = dl["dlstcd"].between(400, 599)
    dlr = dlr.where(dlr.notna(), np.where(perf, -0.30, np.nan))   # missing performance-related delisting -> -30% (CRSP convention)
    for p, d, r in zip(dl["permno"].values, dl["dlstdt"].values, dlr.values):
        if not np.isfinite(r): continue
        k = int(np.searchsorted(dates.values, d)); k = min(k, D - 1)
        if k > 0 and np.isnan(prc[k, pi[p]]): k -= 1
        j = pi[p]
        ret[k, j] = (1 + (0 if np.isnan(ret[k, j]) else ret[k, j])) * (1 + r) - 1
    # share class / exchange eligibility from dsenames
    nm = pd.read_parquet(C / "names.parquet")
    nm = nm[nm["permno"].isin(pi) & nm["shrcd"].isin([10, 11]) & nm["exchcd"].isin([1, 2, 3])]
    ok_cs = np.zeros((D, N), dtype=bool)
    for p, a, b in zip(nm["permno"].values, nm["namedt"].values, nm["nameendt"].values):
        ok_cs[int(np.searchsorted(dates.values, a)):int(np.searchsorted(dates.values, b, side="right")), pi[p]] = True
    r0 = np.nan_to_num(ret, nan=0.0); lr = np.log1p(np.maximum(r0, -0.999999)); cum = np.cumsum(lr, axis=0)
    def cumret(h):   # return from close t to close t+h
        o = np.full((D, N), np.nan); o[:-h] = np.exp(cum[h:] - cum[:-h]) - 1; return o
    def back(h):     # return from close t-h to close t
        o = np.full((D, N), np.nan); o[h:] = np.exp(cum[h:] - cum[:-h]) - 1; return o
    adv = pd.DataFrame(prc * vol).rolling(20, min_periods=15).median().values
    # forward returns indexed at ENTRY row e = d+1 (entry close); later shifted to signal row d
    ON = np.full((D, N), np.nan); ON[2:] = ((1 + ret[2:]) * (opn[2:] / prc[2:]) - 1)  # open(t)/close(t-1) = (1+ret_t)*open_t/close_t - 1
    ON = np.where(np.isfinite(prc), ON, np.nan)
    Rf = {"ON": ON, "5d": cumret(5), "21d": cumret(21)}
    # signal row d: entry close d+1, ON return = close(d+1)->open(d+2) = ON[d+2]; 5d/21d = cumret(h) at row d+1
    R = {}
    R["ON"] = np.full((D, N), np.nan); R["ON"][:-2] = ON[2:]
    for k in ("5d", "21d"):
        R[k] = np.full((D, N), np.nan); R[k][:-1] = Rf[k][1:]
    # require the stock still priced at entry close (d+1)
    pr1 = np.full((D, N), False); pr1[:-1] = np.isfinite(prc[1:])
    for k in R: R[k] = np.where(pr1, R[k], np.nan)
    # ---- IBES features
    ib = pd.read_parquet(C5 / "ibes.parquet")
    for c in ("numest", "numup", "numdown", "meanest", "medest", "stdev"):
        ib[c] = pd.to_numeric(ib[c], errors="coerce").astype("float64")
    lk = pd.read_parquet(C5 / "ibcrs.parquet"); lk["permno"] = lk["permno"].astype("float64")
    lk = lk[lk["permno"].notna() & lk["permno"].isin(list(pi))]
    ib = ib.merge(lk[["ticker", "permno", "sdate", "edate", "score"]], on="ticker")
    ib = ib[(ib["statpers"] >= ib["sdate"]) & (ib["statpers"] <= ib["edate"])]
    ib = ib.sort_values(["permno", "statpers", "fpi", "score"]).drop_duplicates(["permno", "statpers", "fpi"])
    ib["i"] = np.searchsorted(dates.values, ib["statpers"].values, side="right")   # first trading day AFTER statpers
    ib["j"] = ib["permno"].map(pi)
    fy = ib[ib["fpi"] == "1"].sort_values(["permno", "fpedats", "statpers"]).copy()
    g = fy.groupby(["permno", "fpedats"])
    g1 = (fy["statpers"] - g["statpers"].shift(1)).dt.days.between(20, 45)
    g3 = (fy["statpers"] - g["statpers"].shift(3)).dt.days.between(70, 120)
    fy["m1"] = np.where(g1, g["meanest"].shift(1), np.nan); fy["m3"] = np.where(g3, g["meanest"].shift(3), np.nan)
    fy["n3"] = np.where(g3, g["numest"].shift(3), np.nan)
    lt = ib[ib["fpi"] == "0"].sort_values(["permno", "statpers"]).copy()
    gl = lt.groupby("permno"); l3 = (lt["statpers"] - gl["statpers"].shift(3)).dt.days.between(70, 120)
    lt["l3"] = np.where(l3, gl["meanest"].shift(3), np.nan)
    SPD = dates.values.astype("datetime64[D]").astype("int64")
    def place(df, cols):
        df = df[df["i"] < D]; out = {}
        for nme, v in cols.items():
            M = np.full((D, N), np.nan); M[df["i"].values, df["j"].values] = np.asarray(v(df), dtype="float64"); out[nme] = M
        S_ = np.full((D, N), np.nan); S_[df["i"].values, df["j"].values] = df["statpers"].values.astype("datetime64[D]").astype("int64")
        return out, S_
    def ff(M): return pd.DataFrame(M).ffill(limit=40).values
    fm, fS = place(fy, dict(mean=lambda d: d.meanest, med=lambda d: d.medest, sd=lambda d: d.stdev, m1=lambda d: d.m1, m3=lambda d: d.m3,
                            br=lambda d: (d.numup - d.numdown) / d.numest.where(d.numest > 0), ne=lambda d: d.numest, n3=lambda d: d.n3))
    lm, lS = place(lt, dict(ltg=lambda d: d.meanest, l3=lambda d: d.l3))
    fm = {k: ff(v) for k, v in fm.items()}; fS = ff(fS); lm = {k: ff(v) for k, v in lm.items()}; lS = ff(lS)
    # carry-forward <= 45 calendar days from statpers
    fresh = (SPD[:, None] - fS) <= 45; fm = {k: np.where(fresh, v, np.nan) for k, v in fm.items()}
    freshl = (SPD[:, None] - lS) <= 45; lm = {k: np.where(freshl, v, np.nan) for k, v in lm.items()}
    pa = np.where(prc > 0, prc, np.nan)
    X = {"ey": fm["mean"] / pa, "disp": fm["sd"] / pa, "dispm": fm["sd"] / np.where(fm["mean"] != 0, np.abs(fm["mean"]), np.nan),
         "rev1": (fm["mean"] - fm["m1"]) / pa, "rev3": (fm["mean"] - fm["m3"]) / pa, "breadth": fm["br"], "numest": fm["ne"],
         "dnum3": fm["ne"] - fm["n3"], "ltg": lm["ltg"], "dltg": lm["ltg"] - lm["l3"], "gap": (fm["mean"] - fm["med"]) / pa,
         "ret5": back(5), "ret21": back(21), "size": np.log(prc * shr)}
    for k in X: X[k] = np.where(np.isfinite(X[k]), X[k], np.nan)
    havefy = np.isfinite(fm["mean"])
    elig = ok_cs & (prc >= 5) & (adv >= 1e7) & havefy
    i0 = int(dates.searchsorted(D0)); i1 = int(dates.searchsorted(G.D1, side="right"))
    S = dict(dates=dates, D=D, N=N, i0=i0, i1=i1, elig=elig, R=R, X=X)
    ys = dates[i0:i1].year
    print("elig names/day by year:", pd.Series(elig[i0:i1].sum(1), index=ys).groupby(ys).mean().round(0).to_dict())
    base = ok_cs & (prc >= 5) & (adv >= 1e7)
    print("FY1 coverage of CRSP-eligible (share):", round(float(elig[i0:i1].sum() / base[i0:i1].sum() * 100), 1), "%")
    print("feature validity among eligible rows:", {k: round(float(np.isfinite(v[i0:i1])[elig[i0:i1]].mean()), 2) for k, v in X.items()}, flush=True)
    print("ey quantiles 1/50/99:", np.nanpercentile(X["ey"][i0:i1][elig[i0:i1]], [1, 50, 99]).round(3), " numest med:", np.nanmedian(X["numest"][i0:i1][elig[i0:i1]]))
    print("openprc coverage:", round(float(np.isfinite(R['ON'][i0:i1][elig[i0:i1]]).mean() * 100), 1), "%", flush=True)
    return S


def gen_rules():
    rng = np.random.default_rng(SEED); seen = set(); rules = []
    while len(rules) < NRULES:
        f1 = FEATS[rng.integers(len(FEATS))]; k1 = int(rng.choice([1, 10]))
        if rng.random() < 0.5:
            f2 = FEATS[rng.integers(len(FEATS))]
            if f2 == f1: continue
            k2 = int(rng.choice([1, 3]))
        else:
            f2, k2 = None, None
        hz = ["ON", "5d", "21d"][rng.integers(3)]
        key = (f1, k1, f2, k2, hz)
        if key in seen: continue
        seen.add(key); rules.append(dict(id=len(rules), f1=f1, k1=k1, f2=f2, k2=k2, hz=hz))
    return rules


desc = G.desc


def fam(r):
    fs = {r["f1"], r["f2"]} - {None}; o = []
    if fs & {"ret5", "ret21"}: o.append("short-term-reversal(known)")
    if "size" in fs: o.append("size(known)")
    if fs & {"rev1", "rev3", "breadth", "dltg"}: o.append("revision/PEAD-like(known,gap)")
    if fs & {"disp", "dispm"}: o.append("dispersion")
    if fs & {"ey", "ltg", "gap"}: o.append("level/value-growth")
    if fs & {"numest", "dnum3"}: o.append("coverage")
    return ",".join(o) or "other"


def main():
    t0 = time.time()
    S = build(); i0, i1 = S["i0"], S["i1"]
    rules = gen_rules(); print("rules", len(rules), flush=True)
    P = G.ranks(S["X"], S["elig"])
    real = G.run(S, rules, P); nreal = sum(d["passed"] for d in real); print("real", nreal, f"{time.time()-t0:.0f}s", flush=True)
    nulls = []; elig = S["elig"][i0:i1]
    for s in range(1, 11):
        rng = np.random.default_rng(1000 + s)
        Pm = np.tile(np.arange(elig.shape[1]), (elig.shape[0], 1))
        for d in range(elig.shape[0]):
            c = np.where(elig[d])[0]; Pm[d, c] = rng.permutation(c)
        Rp = {k: np.take_along_axis(S["R"][k][i0:i1], Pm, axis=1) for k in S["R"]}
        nulls.append(sum(d["passed"] for d in G.run(S, rules, P, Rp))); print("null", s, nulls[-1], flush=True)
    plc = G.run(S, rules, G.ranks(S["X"], S["elig"], lag=252)); nplc = sum(d["passed"] for d in plc)
    ok = nreal > max(nulls + [nplc]) and nreal > 3 * np.mean(nulls + [nplc])
    rdf = pd.concat([pd.DataFrame(rules), pd.DataFrame(real)], axis=1)
    rdf["desc"] = [desc(r) for r in rules]; rdf["fam"] = [fam(r) for r in rules]; rdf["plc_passed"] = [d["passed"] for d in plc]
    rdf.to_parquet(OUTD / "luck_b5_rules.parquet")
    top = rdf[rdf["n"] >= G.MINN].sort_values("t", ascending=False).head(15)
    L = ["LUCK-B5 results (discovery signal dates 2001-01..2010-12; IBES statpers 2000-01..2010-12; CRSP dsf 2000-06..2011-02; confirmation 2011+ NOT pulled/computed)",
         f"seed {SEED}, {len(rules)} distinct rules; runtime {time.time()-t0:.0f}s",
         "Deviations/choices: see module docstring. Disclosed: ibes filter measure='EPS'; link ibcrsphist score<=2 (lowest score kept); numeric cols cast float64; late-2010 exits use Jan-2011 closes (as B3/B4);",
         "missing perf-delisting dlret -> -30%; ON uses CRSP openprc; scoring/run/ranks code imported unchanged from luck_gen4; no IBES adjusted-vs-unadjusted split issues handled (statsumu = unadjusted).",
         f"REAL pass count: {nreal}",
         "NULL pass counts (perm seeds 1..10): " + ", ".join(map(str, nulls)) + f"  (max {max(nulls)}, mean {np.mean(nulls):.2f})",
         f"DATE-PLACEBO (252d feature lag) pass count: {nplc}",
         f"BATCH VERDICT: {'SIGNAL (real > max of all 11 nulls and > 3x their mean)' if ok else 'LUCK (fails null test) - log and stop, no survivors'}",
         "", "Top 15 rules by t (n>=30 dates; bp net of 10bp RT; ann = % at 100% deployment):"]
    for _, r in top.iterrows():
        L.append(f"  #{r['id']:<4} {r['desc']:<34} n={r['n']:<4} mean={r['mean_bp']:+7.1f} med={r['med_bp']:+7.1f} t={r['t']:.2f} h1={r['h1_bp']:+7.1f} h2={r['h2_bp']:+7.1f} ex5={r['ex5_bp']:+7.1f} ann={r['ann']:+6.1f}% {'PASS' if r['passed'] else 'fail'} fam={r['fam']}")
    L.append(f"(passing rules total: {int(rdf['passed'].sum())})")
    if ok:
        L.append("SURVIVORS (passing, by t):")
        for _, r in rdf[rdf["passed"]].sort_values("t", ascending=False).head(10).iterrows():
            L.append(f"  #{r['id']} {r['desc']} n={r['n']} mean={r['mean_bp']:+.1f} t={r['t']:.2f} ann={r['ann']:.1f}% fam={r['fam']}")
    (OUTD / "luck_b5_out.txt").write_text("\n".join(L) + "\n"); print("\n".join(L))


if __name__ == "__main__":
    main()
