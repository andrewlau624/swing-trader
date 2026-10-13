"""Study LUCK-B6: random-rule discovery batch, grammar 6 (ETF cross-section with fund-level features). Pre-reg: round1_prose.md "Study LUCK-B6".
Run: PYTHONPATH=. .venv/bin/python -m research.sim.luck_gen6   (after research/sim/luck_b6_pull.py has cached data/research/wrds_b6/)
Scoring frame identical to luck_gen4 (reuses ranks()/run() UNCHANGED). Discovery signal dates 2004-01..2012-12; CRSP pulled 2003-07-01..2013-01-31 only
(2013-02+ never pulled; Jan-2013 closes serve only as exits of late-2012 entries; 21d exits beyond 2013-01-31 are absent -> those last signals drop out).
Halves (via G.MID) = signal date < 2009-01-01 vs later. Confirmation 2013-2019 NOT pulled.
Open choices (stated): universe = CRSP dsenames shrcd 73 (any exchcd) on d: close>=5, 20d median $vol>=1M (min 15 obs), listed >=60 days (days since min namedt per permno);
fund age = days since min namedt (listing proxy; pre-2003-07 listings count from namedt); shares-out change = CRSP shrout(t)/shrout(t-h)-1 (CRSP ETF shrout updates
IRREGULARLY, so many zero changes / stale values - flow features are coarse); premium = raw CRSP |prc| / CRSP-MF dnav - 1 (same-day), z21 = (prem - 21d mean)/21d std (min 15 obs);
NAV link = fund_hdr (et_flag F or N) cusip8 == dsenames ncusip (8-char), duplicates per (permno,date) -> median dnav; link rate = share of universe ETF-days with a NAV;
returns/vol/drawdown/52w-high use CRSP total return series (ret), strict 252-row windows for ret252/dd252/hi52 (features start ~mid-2004); vol21 = 21d std(ret);
dollar-volume ratio = prc*vol / 63d mean of prc*vol (min 40 obs, shifted none); delisting return folded in as in luck_gen4 (missing perf-delist -> -30%); ON uses CRSP openprc.
Grammar as luck_gen4 (f1 decile 1/10, optional f2 tercile 1/3, LONG only, horizon ON/5d/21d), seed 20261015, 800 distinct rules; nulls: 10 within-date permutations + 252d-lag placebo.
"""
import time
from pathlib import Path
import numpy as np, pandas as pd
from research.sim import luck_gen4 as G

C = Path("data/research/wrds_b6"); OUTD = Path("data/research/program")
SEED = 20261015; NRULES = 800; D0 = pd.Timestamp("2004-01-01"); D1 = pd.Timestamp("2012-12-31"); MIDB = pd.Timestamp("2009-01-01")
G.MID = MIDB; G.D0 = D0; G.D1 = D1
FEATS_ALL = ["shr5", "shr21", "shr63", "prem", "premz", "dvr", "size", "age", "ret1", "ret5", "ret21", "ret63", "ret252", "vol21", "dd252", "hi52"]
PREM = {"prem", "premz"}
FEATS = list(FEATS_ALL)


def build():
    dsf = pd.read_parquet(C / "dsf.parquet")
    for c in ("prc", "openprc", "ret", "vol", "shrout"):
        dsf[c] = pd.to_numeric(dsf[c], errors="coerce").astype("float64")
    assert dsf["date"].max() <= pd.Timestamp("2013-01-31")
    dates = pd.DatetimeIndex(np.sort(dsf["date"].unique()))
    perm = np.sort(dsf["permno"].unique()); pi = {p: i for i, p in enumerate(perm)}
    D, N = len(dates), len(perm)
    ri = np.searchsorted(dates.values, dsf["date"].values); ci = dsf["permno"].map(pi).values
    def mat(v):
        M = np.full((D, N), np.nan, dtype="float64"); M[ri, ci] = v; return M
    prc = mat(dsf["prc"].abs().values); opn = mat(dsf["openprc"].abs().values); ret = mat(dsf["ret"].values)
    vol = mat(dsf["vol"].values); shr = mat(dsf["shrout"].values * 1000.0)
    dl = pd.read_parquet(C / "delist.parquet").dropna(subset=["dlstdt"]); dl = dl[dl["permno"].isin(pi)]
    dlr = pd.to_numeric(dl["dlret"], errors="coerce").astype("float64")
    dlr = dlr.where(dlr.notna(), np.where(dl["dlstcd"].between(400, 599), -0.30, np.nan))
    for p, d, r in zip(dl["permno"].values, dl["dlstdt"].values, dlr.values):
        if not np.isfinite(r): continue
        k = min(int(np.searchsorted(dates.values, d)), D - 1)
        if k > 0 and np.isnan(prc[k, pi[p]]): k -= 1
        j = pi[p]; ret[k, j] = (1 + (0 if np.isnan(ret[k, j]) else ret[k, j])) * (1 + r) - 1
    nm = pd.read_parquet(C / "names.parquet"); nm = nm[nm["permno"].isin(pi) & (nm["shrcd"] == 73)]
    ok_cs = np.zeros((D, N), dtype=bool)
    for p, a, b in zip(nm["permno"].values, nm["namedt"].values, nm["nameendt"].values):
        ok_cs[int(np.searchsorted(dates.values, a)):int(np.searchsorted(dates.values, b, side="right")), pi[p]] = True
    list0 = nm.groupby("permno")["namedt"].min()
    ldate = np.array([list0.get(p, pd.NaT) for p in perm], dtype="datetime64[ns]")
    age = (dates.values[:, None] - ldate[None, :]).astype("timedelta64[D]").astype("float64")
    r0 = np.nan_to_num(ret, nan=0.0); lr = np.log1p(np.maximum(r0, -0.999999)); cum = np.cumsum(lr, axis=0)
    def cumret(h):
        o = np.full((D, N), np.nan); o[:-h] = np.exp(cum[h:] - cum[:-h]) - 1; return o
    def back(h):
        o = np.full((D, N), np.nan); o[h:] = np.exp(cum[h:] - cum[:-h]) - 1; return o
    dv = prc * vol
    adv = pd.DataFrame(dv).rolling(20, min_periods=15).median().values
    ON = np.full((D, N), np.nan); ON[2:] = ((1 + ret[2:]) * (opn[2:] / prc[2:]) - 1); ON = np.where(np.isfinite(prc), ON, np.nan)
    Rf = {"ON": ON, "5d": cumret(5), "21d": cumret(21)}
    R = {"ON": np.full((D, N), np.nan)}; R["ON"][:-2] = ON[2:]
    for k in ("5d", "21d"):
        R[k] = np.full((D, N), np.nan); R[k][:-1] = Rf[k][1:]
    pr1 = np.full((D, N), False); pr1[:-1] = np.isfinite(prc[1:])
    for k in R: R[k] = np.where(pr1, R[k], np.nan)
    base = ok_cs & (prc >= 5) & (adv >= 1e6) & (age >= 60)
    i0 = int(dates.searchsorted(D0)); i1 = int(dates.searchsorted(D1, side="right"))
    # ---- NAV link
    h = pd.read_parquet(C / "fund_hdr.parquet"); h = h[h["et_flag"].isin(["F", "N"])]
    c2p = nm.dropna(subset=["ncusip"]).drop_duplicates(["ncusip", "permno"]).groupby("ncusip")["permno"].agg(list)
    rows = []
    for f, c in zip(h["crsp_fundno"].values, h["cusip8"].values):
        if c in c2p.index:
            for p in c2p[c]: rows.append((int(f), p))
    lkf = pd.DataFrame(rows, columns=["crsp_fundno", "permno"]).drop_duplicates()
    nav = pd.read_parquet(C / "nav.parquet"); nav["dnav"] = pd.to_numeric(nav["dnav"], errors="coerce").astype("float64")
    nav = nav.merge(lkf, on="crsp_fundno"); nav = nav[nav["dnav"] > 0]
    nav = nav.groupby(["permno", "caldt"], as_index=False)["dnav"].median()
    nav = nav[nav["permno"].isin(pi)]
    ni = np.searchsorted(dates.values, nav["caldt"].values); nj = nav["permno"].map(pi).values
    good = (ni < D) & (dates.values[np.minimum(ni, D - 1)] == nav["caldt"].values)
    NAV = np.full((D, N), np.nan); NAV[ni[good], nj[good]] = nav["dnav"].values[good]
    linked = base & np.isfinite(NAV)
    link_rate = float(linked[i0:i1].sum() / base[i0:i1].sum())
    lr_year = pd.Series(linked[i0:i1].sum(1) / np.maximum(base[i0:i1].sum(1), 1), index=dates[i0:i1].year).groupby(level=0).mean().round(2).to_dict()
    use_prem = link_rate >= 0.5
    # ---- features
    prem = prc / NAV - 1
    pdf = pd.DataFrame(prem); pz = (pdf - pdf.rolling(21, min_periods=15).mean()) / pdf.rolling(21, min_periods=15).std()
    sh = pd.DataFrame(shr)
    def sch(hh): return (sh / sh.shift(hh) - 1).values
    ci_ = np.exp(cum)   # total-return index
    ind = pd.DataFrame(ci_).where(np.isfinite(prc))
    mx252 = ind.rolling(252, min_periods=252).max(); mn_dd = (ind / mx252 - 1).rolling(252, min_periods=252).min()
    X = {"shr5": sch(5), "shr21": sch(21), "shr63": sch(63), "prem": prem, "premz": pz.values,
         "dvr": dv / pd.DataFrame(dv).rolling(63, min_periods=40).mean().values, "size": np.log(prc * shr), "age": age,
         "ret1": back(1), "ret5": back(5), "ret21": back(21), "ret63": back(63), "ret252": back(252),
         "vol21": pd.DataFrame(ret).rolling(21, min_periods=15).std().values, "dd252": mn_dd.values, "hi52": (ind / mx252 - 1).values}
    for k in X: X[k] = np.where(np.isfinite(X[k]), X[k], np.nan).astype("float64")
    if not use_prem:
        for k in PREM: X.pop(k)
    elig = base
    S = dict(dates=dates, D=D, N=N, i0=i0, i1=i1, elig=elig, R=R, X=X, link_rate=link_rate, use_prem=use_prem)
    ys = dates[i0:i1].year
    S["hdr"] = [f"universe (shrcd 73, close>=5, 20d med $vol>=1M, listed>=60d) names/day by year: {pd.Series(elig[i0:i1].sum(1), index=ys).groupby(ys).mean().round(0).to_dict()}",
                f"NAV link: {link_rate*100:.1f}% of universe ETF-days (2004-2012) have a linked NAV; by-year mean share {lr_year}; linked permnos {int(np.isfinite(NAV).any(0).sum())}/{N}; premium features {'KEPT' if use_prem else 'DROPPED (<50%)'}",
                "prem quantiles 1/50/99%: " + str(np.nanpercentile(prem[i0:i1][linked[i0:i1]], [1, 50, 99]).round(4)) if use_prem else "",
                "feature validity among universe rows: " + str({k: round(float(np.isfinite(v[i0:i1])[elig[i0:i1]].mean()), 2) for k, v in X.items()}),
                "shares-out change == 0 share (5d / 21d / 63d): " + str([round(float((X[k][i0:i1][elig[i0:i1]] == 0).mean()), 2) for k in ("shr5", "shr21", "shr63")]),
                f"openprc coverage of universe rows: {float(np.isfinite(R['ON'][i0:i1][elig[i0:i1]]).mean()*100):.1f}%"]
    for l in S["hdr"]: print(l, flush=True)
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
    if fs & {"ret1", "ret5", "ret21"}: o.append("short-term-reversal(known)")
    if fs & {"ret63", "ret252", "hi52", "dd252"}: o.append("momentum/52w(known)")
    if "size" in fs: o.append("size(known)")
    if fs & {"vol21"}: o.append("vol/leverage(known)")
    if fs & {"shr5", "shr21", "shr63"}: o.append("flow")
    if fs & PREM: o.append("premium/discount(known-dead)")
    if fs & {"age", "dvr"}: o.append("age/volume")
    return ",".join(o) or "other"


def main():
    t0 = time.time()
    S = build(); i0, i1 = S["i0"], S["i1"]
    global FEATS
    FEATS[:] = [f for f in FEATS_ALL if f in S["X"]]
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
    rdf.to_parquet(OUTD / "luck_b6_rules.parquet")
    top = rdf[rdf["n"] >= G.MINN].sort_values("t", ascending=False).head(15)
    L = ["LUCK-B6 results (grammar 6: ETF/ETN cross-section, CRSP shrcd 73)",
         f"seed {SEED}, {len(rules)} distinct rules (features used: {FEATS}); runtime {time.time()-t0:.0f}s",
         "Data: CRSP dsf/dsenames/dsedelist shrcd 73 pulled 2003-07-01..2013-01-31; discovery signal dates 2004-01..2012-12; halves split 2009-01-01; confirmation 2013+ NOT pulled/computed.",
         "CRSP shrout for ETFs updates irregularly (stale/zero changes common): shares-outstanding flow features are coarse."] + [l for l in S["hdr"] if l] + [
         "Deviations/choices: see module docstring. Cast numeric cols float64; 21d exits beyond 2013-01-31 unavailable (last signals drop); strict 252-row windows so ret252/dd252/hi52 start mid-2004; age = days since min dsenames namedt; premium uses raw CRSP prc vs CRSP MF dnav (fund_hdr et_flag F/N cusip8 -> dsenames ncusip); scoring/ranks/run imported unchanged from luck_gen4 with G.MID set to 2009-01-01.",
         f"REAL pass count: {nreal}",
         "NULL pass counts (perm seeds 1..10): " + ", ".join(map(str, nulls)) + f"  (max {max(nulls)}, mean {np.mean(nulls):.2f})",
         f"DATE-PLACEBO (252d feature lag) pass count: {nplc}",
         f"BATCH VERDICT: {'COUNTS (real > max of all 11 nulls and > 3x their mean)' if ok else 'LUCK (fails null test) - log and stop, no survivors'}",
         "", "Top 15 rules by t (n>=30 dates; bp net of 10bp RT; ann = % at 100% deployment):"]
    for _, r in top.iterrows():
        L.append(f"  #{r['id']:<4} {r['desc']:<34} n={r['n']:<4} mean={r['mean_bp']:+7.1f} med={r['med_bp']:+7.1f} t={r['t']:.2f} h1={r['h1_bp']:+7.1f} h2={r['h2_bp']:+7.1f} ex5={r['ex5_bp']:+7.1f} ann={r['ann']:+6.1f}% {'PASS' if r['passed'] else 'fail'} fam={r['fam']}")
    L.append(f"(passing rules total: {int(rdf['passed'].sum())})")
    if ok:
        L.append("SURVIVORS (passing, by t):")
        for _, r in rdf[rdf["passed"]].sort_values("t", ascending=False).head(10).iterrows():
            L.append(f"  #{r['id']} {r['desc']} n={r['n']} mean={r['mean_bp']:+.1f} t={r['t']:.2f} ann={r['ann']:.1f}% fam={r['fam']}")
    (OUTD / "luck_b6_out.txt").write_text("\n".join(L) + "\n"); print("\n".join(L))


if __name__ == "__main__":
    main()
