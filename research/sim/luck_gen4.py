"""Study LUCK-B4: random-rule discovery batch, grammar 4 (options-implied + short-interest features). Pre-reg: round1_prose.md "Study LUCK-B4".
Run: PYTHONPATH=. .venv/bin/python -m research.sim.luck_gen4   (after research/sim/luck_b4_pull.py has cached data/research/wrds_b4/)
Discovery only: signal dates d in 2001-01..2010-12; enter close d+1; ON = close d+1 -> open d+2; 5d/21d = close d+1 -> close d+1+h (Jan-2011 closes used for exits
of late-2010 entries, stated deviation as in B3). 2011-2019 returns are never pulled or scored.
Open choices (stated): link = opcrsphist score==1; feature deciles/terciles are cross-sectional percentiles among eligible names with that feature valid;
non-overlap = greedy (take signal day d if d >= previous taken d + h; ON every day); benchmark = EW of all eligible names with a valid return (uncharged);
cost 5bp/side = 10bp RT on the selected leg; need >=5 selected names on a date; t = date-level mean/se; annualised = mean * 252/h(trading days; ON h=1);
halves = signal date < 2006-01-01 vs later, EXCEPT rules using a short-interest feature (data start 2006-07), whose halves are split at the median of their own
valid dates (otherwise they cannot pass by construction; disclosed); option $-volume ratio = option contracts*100 / stock shares volume (notional-equivalent);
placebo = all raw features lagged 252 rows per stock before ranking; permutation = returns permuted across eligible names within date.
"""
import time
from pathlib import Path
import numpy as np, pandas as pd

C = Path("data/research/wrds_b4"); OUTD = Path("data/research/program")
SEED = 20261013; NRULES = 1000; D0 = pd.Timestamp("2001-01-01"); D1 = pd.Timestamp("2010-12-31"); MID = pd.Timestamp("2006-01-01")
COST = 0.0010; MINN = 30; MINNAMES = 5; ANN_MIN = 0.16
FEATS = ["atm", "pcspr", "skew", "ivrv", "div5", "div21", "term", "ovol", "pcvol", "ovnot", "si", "dsi", "dtc", "ret5", "ret21", "size"]
SIF = {"si", "dsi", "dtc"}
HZ = {"ON": 1, "5d": 5, "21d": 21}


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
    # ---- options features
    lk = pd.read_parquet(C / "link.parquet"); lk = lk[(lk["score"] == 1) & lk["permno"].notna()].copy()
    lk["edate"] = lk["edate"].fillna(pd.Timestamp("2099-01-01")); lk["sdate"] = lk["sdate"].fillna(pd.Timestamp("1990-01-01"))
    vs = pd.concat([pd.read_parquet(f) for f in sorted(C.glob("vs20*.parquet"))], ignore_index=True)
    print("vsurfd rows", len(vs), flush=True)
    vs = vs.merge(lk[["secid", "sdate", "edate", "permno"]], on="secid")
    vs = vs[(vs["date"] >= vs["sdate"]) & (vs["date"] <= vs["edate"])]
    cov = vs.groupby(vs["date"].dt.year)["secid"].nunique()
    vs = vs[vs["permno"].isin(pi)].drop_duplicates(["permno", "date", "days", "delta"])
    vs["j"] = vs["permno"].map(pi); vs["i"] = np.searchsorted(dates.values, vs["date"].values)
    vs = vs[(vs["i"] < D) & (dates.values[np.minimum(vs["i"], D - 1)] == vs["date"].values)]
    def vmat(days, delta):
        s = vs[(vs["days"] == days) & (vs["delta"] == delta)]
        M = np.full((D, N), np.nan); M[s["i"].values, s["j"].values] = s["iv"].values; return M
    a30, p30, p25_30, a91 = vmat(30, 50), vmat(30, -50), vmat(30, -25), vmat(91, 50)
    haveiv = np.isfinite(a30)
    ov = pd.read_parquet(C / "opvold.parquet").merge(lk[["secid", "sdate", "edate", "permno"]], on="secid")
    ov = ov[(ov["date"] >= ov["sdate"]) & (ov["date"] <= ov["edate"]) & ov["permno"].isin(pi)]
    ov["j"] = ov["permno"].map(pi); ov["i"] = np.searchsorted(dates.values, ov["date"].values)
    ov = ov[(ov["i"] < D) & (dates.values[np.minimum(ov["i"], D - 1)] == ov["date"].values)]
    cv = ov[ov["cp_flag"] == "C"].groupby(["i", "j"])["volume"].sum(); pv = ov[ov["cp_flag"] == "P"].groupby(["i", "j"])["volume"].sum()
    CV = np.zeros((D, N)); PV = np.zeros((D, N))
    CV[cv.index.get_level_values(0), cv.index.get_level_values(1)] = cv.values; PV[pv.index.get_level_values(0), pv.index.get_level_values(1)] = pv.values
    OV = CV + PV; OV[~haveiv] = np.nan
    ovavg = pd.DataFrame(OV).shift(1).rolling(20, min_periods=10).mean().values
    rv20 = pd.DataFrame(ret).rolling(20, min_periods=15).std().values * np.sqrt(252)
    # ---- short interest (usable from settlement + 8 business days)
    si = pd.read_parquet(C / "si.parquet"); si = si[si["iid"] == "01"].dropna(subset=["shortint"])
    cc = pd.read_parquet(C / "ccm.parquet"); cc = cc[cc["linkprim"].isin(["P", "C"])].copy()
    cc["linkenddt"] = cc["linkenddt"].fillna(pd.Timestamp("2099-01-01"))
    si = si.merge(cc[["gvkey", "permno", "linkdt", "linkenddt"]], on="gvkey")
    si = si[(si["datadate"] >= si["linkdt"]) & (si["datadate"] <= si["linkenddt"]) & si["permno"].isin(pi)]
    si = si.sort_values(["permno", "datadate"]).drop_duplicates(["permno", "datadate"])
    si["prev"] = si.groupby("permno")["shortint"].shift()
    si["avail"] = pd.to_datetime(np.busday_offset(si["datadate"].values.astype("datetime64[D]"), 8, roll="forward"))
    si["i"] = np.searchsorted(dates.values, si["avail"].values); si["j"] = si["permno"].map(pi)
    si = si[si["i"] < D]
    SI = np.full((D, N), np.nan); PS = np.full((D, N), np.nan)
    SI[si["i"].values, si["j"].values] = si["shortint"].values; PS[si["i"].values, si["j"].values] = si["prev"].values
    SI = pd.DataFrame(SI).ffill(limit=30).values; PS = pd.DataFrame(PS).ffill(limit=30).values
    adv_sh = pd.DataFrame(vol).rolling(20, min_periods=15).mean().values
    X = {"atm": a30, "pcspr": p30 - a30, "skew": p25_30 - a30, "ivrv": a30 - rv20,
         "div5": a30 / pd.DataFrame(a30).shift(5).values - 1, "div21": a30 / pd.DataFrame(a30).shift(21).values - 1,
         "term": a91 - a30, "ovol": np.log((OV + 1) / (ovavg + 1)), "pcvol": np.log((PV + 1) / (CV + 1)),
         "ovnot": OV * 100 / vol, "si": SI / shr, "dsi": SI / PS - 1, "dtc": SI / adv_sh, "ret5": back(5), "ret21": back(21), "size": np.log(prc * shr)}
    for k in X: X[k] = np.where(np.isfinite(X[k]), X[k], np.nan)
    elig = ok_cs & (prc >= 5) & (adv >= 1e7) & haveiv
    i0 = int(dates.searchsorted(D0)); i1 = int(dates.searchsorted(D1, side="right"))
    S = dict(dates=dates, D=D, N=N, i0=i0, i1=i1, elig=elig, R=R, X=X)
    diag = dict(cov=cov, nlink=lk["permno"].nunique(), vs_perm=vs["permno"].nunique())
    # day-1 sanity
    ys = dates[i0:i1].year
    print("elig names/day by year:", pd.Series(elig[i0:i1].sum(1), index=ys).groupby(ys).mean().round(0).to_dict())
    print("OptionMetrics secids (post-link) by year:", cov.to_dict())
    print("link coverage: of eligible (CRSP-side, no IV req) permno-days with IV =", round(float((haveiv & ok_cs & (prc >= 5) & (adv >= 1e7))[i0:i1].sum() / (ok_cs & (prc >= 5) & (adv >= 1e7))[i0:i1].sum() * 100), 1), "%")
    print("ATM IV(30d) quantiles 1/50/99%:", np.nanpercentile(a30[i0:i1], [1, 50, 99]).round(3), " put-call spread med:", np.nanmedian((p30 - a30)[i0:i1]).round(4))
    print("openprc coverage (share of eligible rows):", round(float(np.isfinite(R['ON'][i0:i1][elig[i0:i1]]).mean() * 100), 1), "%")
    print("short-interest feature coverage by year (share of eligible rows with si):", pd.Series(np.isfinite(X['si'][i0:i1])[elig[i0:i1]].mean() if False else 0).iloc[0], flush=True)
    sicov = pd.Series(np.isfinite(X["si"][i0:i1]).sum(1) / np.maximum(elig[i0:i1].sum(1), 1), index=ys).groupby(ys).mean().round(2).to_dict()
    print("SI coverage / eligible by year:", sicov, flush=True)
    S["diag"] = diag
    return S


def ranks(X, elig, lag=0):
    """cross-sectional percentile among eligible names with feature valid (restricted to rows i0:i1). lag: shift raw feature by `lag` rows per stock."""
    P = {}
    for f, M in X.items():
        if lag:
            M = np.full_like(M, np.nan); M[lag:] = X[f][:-lag]
        df = pd.DataFrame(np.where(elig, M, np.nan))
        P[f] = df.rank(axis=1, pct=True).values.astype("float32")
    return P


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


def desc(r):
    return f"{r['f1']} d{r['k1']}" + (f" & {r['f2']} t{r['k2']}" if r["f2"] else "") + f" {r['hz']}"


def fam(r):
    fs = {r["f1"], r["f2"]} - {None}; o = []
    if fs & {"ret5", "ret21"}: o.append("short-term-reversal/mom(known)")
    if "size" in fs: o.append("size(known)")
    if fs & SIF: o.append("short-interest")
    if fs & {"atm", "pcspr", "skew", "ivrv", "div5", "div21", "term"}: o.append("iv-state")
    if fs & {"ovol", "pcvol", "ovnot"}: o.append("opt-volume")
    return ",".join(o) or "other"


def run(S, rules, P, Rm=None):
    i0, i1 = S["i0"], S["i1"]; elig = S["elig"][i0:i1]; dates = S["dates"][i0:i1]
    Rm = Rm or {k: S["R"][k][i0:i1] for k in S["R"]}
    Pr = {f: P[f][i0:i1] for f in P}
    ok = {k: elig & np.isfinite(Rm[k]) for k in Rm}
    bench = {k: np.where(ok[k], Rm[k], 0).sum(1) / np.maximum(ok[k].sum(1), 1) for k in Rm}
    h1mask = dates < MID
    out = []
    for r in rules:
        h = HZ[r["hz"]]; k = r["hz"]
        m = np.zeros(elig.shape, dtype=bool)
        m = (Pr[r["f1"]] <= 0.1) if r["k1"] == 1 else (Pr[r["f1"]] > 0.9)
        if r["f2"]:
            p2 = Pr[r["f2"]]; m &= (p2 <= 1/3) if r["k2"] == 1 else (p2 > 2/3)
        m &= ok[k]
        cnt = m.sum(1)
        mean = np.where(cnt > 0, np.where(m, Rm[k], 0).sum(1) / np.maximum(cnt, 1), np.nan)
        x = mean - bench[k] - COST
        valid = (cnt >= MINNAMES) & np.isfinite(x)
        # greedy non-overlap
        take = np.zeros(len(x), dtype=bool); last = -10**9
        for d in np.where(valid)[0]:
            if d >= last + h: take[d] = True; last = d
        xs = x[take]; n = len(xs)
        d_ = dict(n=n, mean_bp=np.nan, med_bp=np.nan, t=np.nan, h1_bp=np.nan, h2_bp=np.nan, ex5_bp=np.nan, ann=np.nan, passed=False)
        if n >= 2:
            mu = xs.mean(); sd = xs.std(ddof=1); t = mu / (sd / np.sqrt(n)) if sd > 0 else 0.0
            usesi = bool({r["f1"], r["f2"]} & SIF)
            td = np.where(take)[0]
            if usesi:
                cut = np.median(td); hm = td < cut
            else:
                hm = h1mask[td]
            h1 = xs[hm].mean() if hm.any() else np.nan; h2 = xs[~hm].mean() if (~hm).any() else np.nan
            ex5 = np.sort(xs)[:-5].mean() if n > 5 else np.nan; med = np.median(xs); ann = mu * 252 / h
            d_.update(mean_bp=mu * 1e4, med_bp=med * 1e4, t=t, h1_bp=h1 * 1e4, h2_bp=h2 * 1e4, ex5_bp=ex5 * 1e4, ann=ann * 100)
            d_["passed"] = bool(n >= MINN and mu > 0 and t >= 3 and h1 > 0 and h2 > 0 and med > 0 and ex5 > 0 and ann >= ANN_MIN * 100)
        out.append(d_)
    return out


def main():
    t0 = time.time()
    S = build(); i0, i1 = S["i0"], S["i1"]
    rules = gen_rules(); print("rules", len(rules), flush=True)
    P = ranks(S["X"], S["elig"])
    real = run(S, rules, P); nreal = sum(d["passed"] for d in real); print("real", nreal, f"{time.time()-t0:.0f}s", flush=True)
    nulls = []
    elig = S["elig"][i0:i1]
    for s in range(1, 11):
        rng = np.random.default_rng(1000 + s)
        Pm = np.tile(np.arange(elig.shape[1]), (elig.shape[0], 1))
        for d in range(elig.shape[0]):
            c = np.where(elig[d])[0]; Pm[d, c] = rng.permutation(c)
        Rp = {k: np.take_along_axis(S["R"][k][i0:i1], Pm, axis=1) for k in S["R"]}
        nulls.append(sum(d["passed"] for d in run(S, rules, P, Rp))); print("null", s, nulls[-1], flush=True)
    plc = run(S, rules, ranks(S["X"], S["elig"], lag=252)); nplc = sum(d["passed"] for d in plc)
    ok = nreal > max(nulls + [nplc]) and nreal > 3 * np.mean(nulls + [nplc])
    rdf = pd.concat([pd.DataFrame(rules), pd.DataFrame(real)], axis=1)
    rdf["desc"] = [desc(r) for r in rules]; rdf["fam"] = [fam(r) for r in rules]; rdf["plc_passed"] = [d["passed"] for d in plc]
    rdf.to_parquet(OUTD / "luck_b4_rules.parquet")
    top = rdf[rdf["n"] >= MINN].sort_values("t", ascending=False).head(20)
    # sanity known-sign: ret21 decile 10 vs 1 (reversal sign), 5d horizon, overlapping daily gross vs EW universe
    ok5 = elig & np.isfinite(S["R"]["5d"][i0:i1]); R5 = S["R"]["5d"][i0:i1]
    b5 = np.where(ok5, R5, 0).sum(1) / np.maximum(ok5.sum(1), 1)
    sn = []
    for nm, m in (("d10", P["ret21"][i0:i1] > 0.9), ("d1", P["ret21"][i0:i1] <= 0.1)):
        m = m & ok5; sn.append((nm, float(np.nanmean(np.where(m.sum(1) > 0, np.where(m, R5, 0).sum(1) / np.maximum(m.sum(1), 1) - b5, np.nan)) * 1e4)))
    L = [f"LUCK-B4 results (discovery signal dates 2001-01..2010-12; confirmation 2011+ NOT pulled/computed)",
         f"seed {SEED}, {len(rules)} distinct rules; runtime {time.time()-t0:.0f}s",
         "Deviations/choices: see module docstring (link score==1; 10bp RT; non-overlap greedy; SI-rule halves split at own median date; late-2010 exits use Jan-2011 closes; missing perf-delisting dlret -> -30%; ON uses CRSP openprc).",
         f"REAL pass count: {nreal}",
         "NULL pass counts (perm seeds 1..10): " + ", ".join(map(str, nulls)) + f"  (max {max(nulls)}, mean {np.mean(nulls):.2f})",
         f"DATE-PLACEBO (252d feature lag) pass count: {nplc}",
         f"BATCH VERDICT: {'COUNTS (real > max of all 11 nulls and > 3x their mean)' if ok else 'LUCK (fails null test) - log and stop, no survivors'}",
         f"SANITY known-sign (ret21 decile, 5d fwd, gross vs EW universe, overlapping daily): " + "; ".join(f"{a}: {b:+.1f}bp" for a, b in sn),
         "", "Top 20 rules by t (n>=30 dates; bp net of 10bp RT; ann = % at 100% deployment):"]
    for _, r in top.iterrows():
        L.append(f"  #{r['id']:<4} {r['desc']:<34} n={r['n']:<4} mean={r['mean_bp']:+7.1f} med={r['med_bp']:+7.1f} t={r['t']:.2f} h1={r['h1_bp']:+7.1f} h2={r['h2_bp']:+7.1f} ex5={r['ex5_bp']:+7.1f} ann={r['ann']:+6.1f}% {'PASS' if r['passed'] else 'fail'} fam={r['fam']}")
    L.append(f"(passing rules total: {int(rdf['passed'].sum())})")
    if ok:
        L.append("SURVIVORS (passing, by t):")
        for _, r in rdf[rdf["passed"]].sort_values("t", ascending=False).head(10).iterrows():
            L.append(f"  #{r['id']} {r['desc']} n={r['n']} mean={r['mean_bp']:+.1f} t={r['t']:.2f} ann={r['ann']:.1f}% fam={r['fam']}")
    (OUTD / "luck_b4_out.txt").write_text("\n".join(L) + "\n"); print("\n".join(L))


if __name__ == "__main__":
    main()
