"""Study LUCK-B2: random-rule discovery batch, grammar 2 (events x price state, 20/60-session horizons).
Pre-reg: research/drafts/round1_prose.md "Study LUCK-B2". Run: PYTHONPATH=. python3 -m research.sim.luck_gen2

Discovery = ENTRY dates 2005-01-01..2015-12-31. Prices are loaded to 2016-04-15 ONLY so that exit opens of late-2015
entries exist (same as LUCK-B1); no entry on/after 2016-01-01 is scored. Features warm up from 2003-06.

Choices the registration left open (stated, not tuned):
 - Event types: every 8-K code, every ACTIONS action type, plus derived div_up / div_cut (regular 'dividend' value vs the
   ticker's previous 'dividend' value, ratio >= 1.10 / <= 0.90, only if the previous is <= 400 days earlier and no 'split'
   action lies between the two dates). A type is eligible for rules if it has >= 150 eligible discovery events (real data).
 - Rule: 50% have a price-state filter (feature uniform over ret20, ret60, vol20, dist_hi, logmcap; tercile 1 or 3 of the
   cross-sectional percentile among eligible names on the session BEFORE entry); horizon {20,60}; side +-1.
 - Entry: 8-K events at the open of the 5th session after the event date; actions (incl. derived) the 2nd session after.
 - Benchmark: EW mean of all names eligible the session before entry with prices at entry and exit (open-to-open, adjusted).
 - Name must have printed on the entry session. Delisted names: last print then flat.
 - Cluster t: SE of the mean with clusters = entry calendar months. Ex-top-5 = mean after dropping the 5 largest events.
 - Null perm: event-type labels permuted within (calendar year of event date, source class 8-K vs action), seeds 1..10.
 - Date placebo: each event's entry moved back by U{250..750} sessions (seed 99); events landing before 2005-01 drop out.
 - 'initiated' in Sharadar ACTIONS is a database-coverage marker, NOT a dividend initiation (stated).
"""
from __future__ import annotations
import os, time, pathlib
import numpy as np, pandas as pd, pyarrow.parquet as pq
from numba import njit

SH = os.path.expanduser("~/data/sharadar")
OUTD = pathlib.Path("data/research/program")
LOAD0, LOAD1 = "2003-06-01", "2016-04-15"
D0, D1 = pd.Timestamp("2005-01-01"), pd.Timestamp("2015-12-31")
SEED, NRULES, COST, MINN = 20261013, 600, 0.0020, 100
PF = ["ret20", "ret60", "vol20", "dist_hi", "logmcap"]
# EVENTS code -> 8-K item (Sharadar docs not on disk; code = item number x 10, verified by frequency pattern:
# 22 results, 52 officers, 91 exhibits, 81 other, 71 RegFD, 57 votes). 34/35/37 have no standard item (label only).
ITEM = {c: f"Item {c//10}.{c%10:02d}" for c in [11,12,13,14,21,22,23,24,25,26,31,32,33,41,42,51,52,53,54,55,56,57,58,71,81,91,62,63,64,65]}
G = {}


def load():
    tk = pq.read_table(f"{SH}/tickers.parquet", columns=["table", "ticker", "category"]).to_pandas()
    tk = tk[(tk["table"] == "SEP") & tk["category"].astype(str).str.startswith("Domestic Common Stock")]
    keep = set(tk["ticker"])
    flt = [("date", ">=", pd.Timestamp(LOAD0)), ("date", "<=", pd.Timestamp(LOAD1))]
    s = pq.read_table(f"{SH}/stocks.parquet", columns=["ticker", "date", "open", "close", "volume", "closeadj", "closeunadj"], filters=flt).to_pandas()
    s = s[s["ticker"].isin(keep)]
    s["date"] = pd.to_datetime(s["date"])
    d = pq.read_table(f"{SH}/daily.parquet", columns=["ticker", "date", "marketcap"], filters=flt).to_pandas()
    d = d[d["ticker"].isin(keep)]
    d["date"] = pd.to_datetime(d["date"])
    dates = pd.DatetimeIndex(sorted(s["date"].unique()))
    tick = pd.Index(sorted(s["ticker"].unique()))
    s = s.drop_duplicates(["ticker", "date"], keep="last"); d = d.drop_duplicates(["ticker", "date"], keep="last")
    piv = lambda df, c: df.pivot(index="date", columns="ticker", values=c).reindex(index=dates, columns=tick).astype("float32")
    M = {c: piv(s, c) for c in ["open", "close", "volume", "closeadj", "closeunadj"]}
    return dates, tick, M, piv(d, "marketcap")


def build(dates, M, mc):
    close, opn, vol, cadj, raw = (M[k] for k in ["close", "open", "volume", "closeadj", "closeunadj"])
    printed = close.notna()
    oadj = opn * cadj / close
    oadj_f = oadj.where(oadj.notna(), cadj.ffill()).ffill()
    adv = (close * vol).rolling(20, min_periods=15).median()
    elig = printed & (raw >= 5) & (adv >= 2e6)
    X = {"ret20": cadj / cadj.shift(20) - 1, "ret60": cadj / cadj.shift(60) - 1,
         "vol20": cadj.pct_change(fill_method=None).rolling(20, min_periods=15).std(),
         "dist_hi": cadj / cadj.rolling(252, min_periods=200).max() - 1, "logmcap": np.log(mc)}
    P = {f: X[f].where(elig).replace([np.inf, -np.inf], np.nan).rank(axis=1, pct=True).values.astype("float32") for f in PF}
    O = oadj_f.values
    R, U = {}, {}
    ev = elig.values & printed.values
    for h in (20, 60):
        r = np.full(O.shape, np.nan, dtype="float32")
        r[:-h] = O[h:] / O[:-h] - 1
        r[~np.isfinite(r)] = np.nan
        ok = ev & np.isfinite(r)
        # universe: eligible the session before entry, priced at entry & exit
        okp = np.zeros_like(ok); okp[1:] = elig.values[:-1]; ok = okp & printed.values & np.isfinite(r)
        U[h] = (np.where(ok, r, 0).sum(1, dtype="float64") / np.maximum(ok.sum(1), 1)).astype("float32")
        R[h] = r
    return elig.values, printed.values, P, R, U


def make_events(dates, tick):
    ti = {t: i for i, t in enumerate(tick)}
    e = pq.read_table(f"{SH}/events.parquet").to_pandas()
    e["date"] = pd.to_datetime(e["date"])
    e = e[(e["date"] >= "2004-10-01") & (e["date"] <= D1) & e["ticker"].isin(ti)]
    e["code"] = e["eventcodes"].str.split("|")
    e = e.explode("code")[["ticker", "date", "code"]]
    e["type"] = "8K_" + e["code"].astype(str); e["cls"] = 0; e["off"] = 5
    a = pq.read_table(f"{SH}/actions.parquet").to_pandas()
    a["date"] = pd.to_datetime(a["date"])
    a = a[a["ticker"].isin(ti) & (a["date"] >= "2000-01-01")]
    # derived dividend change
    dv = a[a["action"] == "dividend"].dropna(subset=["value"]).sort_values(["ticker", "date"])
    sp = a[a["action"] == "split"].groupby("ticker")["date"].apply(lambda s: s.values)
    dv["pv"] = dv.groupby("ticker")["value"].shift(); dv["pd_"] = dv.groupby("ticker")["date"].shift()
    ok = dv["pv"].notna() & (dv["pv"] > 0) & ((dv["date"] - dv["pd_"]).dt.days <= 400)
    dv = dv[ok]
    nosplit = []
    for tkr, d0, d1 in zip(dv["ticker"].values, dv["pd_"].values, dv["date"].values):
        s_ = sp.get(tkr)
        nosplit.append(True if s_ is None else not ((s_ > d0) & (s_ <= d1)).any())
    dv = dv[np.array(nosplit, dtype=bool)]
    ratio = dv["value"] / dv["pv"]
    der = pd.concat([dv[ratio >= 1.10].assign(type="div_up"), dv[ratio <= 0.90].assign(type="div_cut")])[["ticker", "date", "type"]]
    ac = a[(a["date"] >= "2004-10-01") & (a["date"] <= D1) & (a["action"] != "relation")][["ticker", "date", "action"]].rename(columns={"action": "type"})
    ac = pd.concat([ac, der]); ac["cls"] = 1; ac["off"] = 2
    ev = pd.concat([e[["ticker", "date", "type", "cls", "off"]], ac], ignore_index=True)
    ev["t"] = ev["ticker"].map(ti).astype("int32")
    ev["e"] = (np.searchsorted(dates.values, ev["date"].values, side="right") + ev["off"].values - 1).astype("int32")
    ev["yr"] = ev["date"].dt.year.astype("int16")
    return ev[["t", "e", "type", "cls", "yr"]]


def rows(ev, dates, elig, printed, P, R, U):
    """attach features/returns to events (entry row e, features at e-1). Restrict to discovery entry window."""
    i0 = int(dates.searchsorted(D0)); i1 = int(dates.searchsorted(D1, side="right"))
    ev = ev[(ev["e"] >= i0) & (ev["e"] < i1)].sort_values(["t", "e"], kind="stable").reset_index(drop=True)
    t, e = ev["t"].values, ev["e"].values
    out = dict(valid=elig[e - 1, t] & printed[e, t])
    for f in PF:
        out[f] = P[f][e - 1, t]
    for h in (20, 60):
        out[f"r{h}"] = R[h][e, t]; out[f"u{h}"] = U[h][e]
    out["mon"] = (dates[e].year.values - 2005) * 12 + dates[e].month.values - 1
    out["h2"] = dates[e] >= pd.Timestamp("2011-01-01")
    return ev, out


@njit(cache=True)
def rearm(tk, en, gap):
    keep = np.zeros(len(tk), dtype=np.bool_)
    lt, le = -1, -10**9
    for i in range(len(tk)):
        if tk[i] != lt or en[i] - le >= gap:
            keep[i] = True; lt = tk[i]; le = en[i]
    return keep


def score(rules, tp, tk, en, F):
    """tp: type labels (object array) of valid rows; F: dict arrays of valid rows."""
    order = np.argsort(tp, kind="stable"); ts = tp[order]
    uniq, st = np.unique(ts, return_index=True); en_ = np.append(st[1:], len(ts))
    pos = {u: (s, e_) for u, s, e_ in zip(uniq, st, en_)}
    res = []
    for r in rules:
        d = dict(n=0, mean_bp=np.nan, med_bp=np.nan, t=np.nan, h1_bp=np.nan, h2_bp=np.nan, ex5_bp=np.nan, passed=False)
        if r["etype"] in pos:
            s, e_ = pos[r["etype"]]
            idx = np.sort(order[s:e_])               # back to (ticker, entry) order
            m = np.isfinite(F[f"r{r['hz']}"][idx])
            if r["pf"]:
                p = F[r["pf"]][idx]
                m &= (p <= 1/3) if r["k"] == 1 else (p > 2/3)
            idx = idx[m]
            if len(idx):
                idx = idx[rearm(tk[idx], en[idx], 20)]
            n = len(idx); d["n"] = n
            if n >= 2:
                x = r["side"] * (F[f"r{r['hz']}"][idx].astype("float64") - F[f"u{r['hz']}"][idx]) - COST
                mu = x.mean()
                cl = F["mon"][idx]; u_, inv = np.unique(cl, return_inverse=True)
                cs = np.bincount(inv, weights=x - mu)
                se = np.sqrt((cs ** 2).sum()) / n
                t = mu / se if se > 0 else 0.0
                h2 = F["h2"][idx]
                h1m = x[~h2].mean() if (~h2).any() else np.nan; h2m = x[h2].mean() if h2.any() else np.nan
                ex5 = np.sort(x)[:-5].mean() if n > 5 else np.nan
                med = np.median(x)
                d.update(mean_bp=mu*1e4, med_bp=med*1e4, t=t, h1_bp=h1m*1e4, h2_bp=h2m*1e4, ex5_bp=ex5*1e4)
                d["passed"] = bool(n >= MINN and mu > 0 and t >= 3 and h1m > 0 and h2m > 0 and med > 0 and ex5 > 0)
        res.append(d)
    return res


def make_rules(types):
    rng = np.random.default_rng(SEED)
    rules = []
    for i in range(NRULES):
        r = dict(id=i, etype=types[rng.integers(len(types))], pf=None, k=None, hz=int(rng.choice([20, 60])), side=int(rng.choice([1, -1])))
        if rng.random() < 0.5:
            r["pf"] = PF[rng.integers(len(PF))]; r["k"] = int(rng.choice([1, 3]))
        rules.append(r)
    return rules


def desc(r):
    return f"{'long' if r['side']>0 else 'short'} {r['etype']}" + (f" & {r['pf']} T{r['k']}" if r["pf"] else "") + f" h={r['hz']}"


def fam(r):
    f, t = [], r["etype"]
    if t == "8K_22": f.append("earnings-8K/PEAD")
    if t.startswith("spin") or t == "spunofffrom": f.append("spin-off")
    if t in ("dividend", "div_up", "div_cut", "initiated"): f.append("dividend/initiation")
    if t.startswith("acquisition") or t.startswith("merger"): f.append("M&A")
    if t == "split": f.append("split")
    if t == "8K_52": f.append("officer-change(insider-adj)")
    if r["pf"] in ("ret20", "ret60"): f.append("ST-rev/mom tilt")
    if r["pf"] == "dist_hi": f.append("52wk-high tilt")
    if r["pf"] == "logmcap": f.append("size tilt")
    if r["pf"] == "vol20": f.append("vol tilt")
    return ",".join(f) if f else "-"


def main():
    t0 = time.time()
    dates, tick, M, mc = load()
    print("loaded", len(dates), len(tick), f"{time.time()-t0:.0f}s", flush=True)
    elig, printed, P, R, U = build(dates, M, mc)
    del M, mc
    ev0 = make_events(dates, tick)
    print("events", len(ev0), f"{time.time()-t0:.0f}s", flush=True)
    ev, F = rows(ev0, dates, elig, printed, P, R, U)
    valid = F["valid"]; vi = np.where(valid)[0]
    tk, en = ev["t"].values, ev["e"].values
    ty = ev["type"].values.astype(object)
    cnt = pd.Series(ty[vi]).value_counts()
    types = sorted(cnt[cnt >= 150].index)
    rules = make_rules(types)
    Fv = {k: v[vi] for k, v in F.items() if k != "valid"}
    tkv, env = tk[vi], en[vi]
    real = score(rules, ty[vi], tkv, env, Fv)
    nreal = sum(d["passed"] for d in real)
    print("real", nreal, f"{time.time()-t0:.0f}s", flush=True)
    # permutation nulls
    g = ev["yr"].values.astype(int) * 2 + ev["cls"].values
    o0 = np.argsort(g, kind="stable")
    nulls = []
    for s in range(1, 11):
        rng = np.random.default_rng(s)
        o1 = np.lexsort((rng.random(len(g)), g))
        tp = np.empty_like(ty); tp[o0] = ty[o1]
        nulls.append(sum(d["passed"] for d in score(rules, tp[vi], tkv, env, Fv)))
        print("null", s, nulls[-1], flush=True)
    # date placebo
    rng = np.random.default_rng(99)
    evp = ev0.copy(); evp["e"] = (evp["e"].values - rng.integers(250, 751, len(evp))).astype("int32")
    evp = evp[evp["e"] >= 0]
    evp, Fp = rows(evp, dates, elig, printed, P, R, U)
    vp = np.where(Fp["valid"])[0]
    plc = score(rules, evp["type"].values.astype(object)[vp], evp["t"].values[vp], evp["e"].values[vp], {k: v[vp] for k, v in Fp.items() if k != "valid"})
    nplc = sum(d["passed"] for d in plc)
    ok = nreal > max(nulls) and nreal > 3 * np.mean(nulls)
    rdf = pd.concat([pd.DataFrame(rules), pd.DataFrame(real)], axis=1)
    rdf["desc"] = [desc(r) for r in rules]; rdf["fam"] = [fam(r) for r in rules]
    rdf["plc_passed"] = [d["passed"] for d in plc]
    rdf.to_parquet(OUTD / "luck_b2_rules.parquet")
    top = rdf[rdf["n"] >= MINN].sort_values("t", ascending=False).head(20)
    L = ["LUCK-B2 results (discovery entries 2005-01..2015-12; confirmation 2016+ entries NOT scored)",
         f"seed {SEED}, {NRULES} rules, {len(types)} eligible event types; runtime {time.time()-t0:.0f}s",
         f"Events in discovery window: {len(ev)}; valid (eligible, priced): {len(vi)}; placebo valid: {len(vp)}",
         "8-K code -> item map used (code = item x 10; 34/35/37 no standard item): " + ", ".join(f"{c}={v}" for c, v in sorted(ITEM.items())),
         "Forced deviations: exit opens of Q4-2015 entries use 2016-01..04 prices (as in B1); 'initiated' = coverage marker; "
         "perm null shuffles labels within (year, class); price-filter prob 0.5 and min 150 events/type were unspecified choices.",
         f"REAL pass count: {nreal}",
         "NULL pass counts (perm seeds 1..10): " + ", ".join(map(str, nulls)) + f"  (max {max(nulls)}, mean {np.mean(nulls):.2f})",
         f"DATE-PLACEBO pass count: {nplc}",
         f"BATCH VERDICT: {'COUNTS (real > max null and > 3x mean null)' if ok else 'LUCK (fails null test) - log and stop, no survivors'}",
         "", "Top 20 rules by t (n>=100; PASS marks full gate; all bp net of 20bp):"]
    for _, r in top.iterrows():
        L.append(f"  #{r['id']:<4} {r['desc']:<42} n={r['n']:<5} mean={r['mean_bp']:+7.1f} med={r['med_bp']:+7.1f} t={r['t']:.2f} h1={r['h1_bp']:+7.1f} h2={r['h2_bp']:+7.1f} ex5={r['ex5_bp']:+7.1f} {'PASS' if r['passed'] else 'fail'} fam={r['fam']}")
    L.append(f"(passing rules total: {int(rdf['passed'].sum())})")
    (OUTD / "luck_b2_out.txt").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
