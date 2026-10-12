"""Study LUCK-B3: random-rule discovery batch, grammar 3 (crypto alts, long-only, 7/30d). Pre-reg: round1_prose.md "Study LUCK-B3".
Run: PYTHONPATH=. python3 -m research.sim.luck_gen3
Panel is TRUNCATED at 2023-02-15 on load: nothing from the confirmation set (entries 2023-01..2026-09) is ever computed;
exits of late-2022 entries (max h=30) use closes up to 2023-01-30 (stated deviation, as in B1/B2).
Open choices (stated): non-overlap = greedy (take signal day d if d >= previous taken d + h); permutation shuffles the
eligible symbols' rows jointly within date (equivalent to permuting returns); BTC-regime / weekday filters are also lagged
365d in the date placebo; BTC terciles cut on discovery days; rule mix: none 20% / cross-sectional f2 50% / BTC regime 15% /
weekday 15%; rank percentiles among eligible names with that feature valid; 'stop at last bar' = ffill of last close.
"""
import time
from pathlib import Path
import numpy as np, pandas as pd

OUTD = Path("data/research/program"); SEED = 20261014; NRULES = 800
TRUNC = pd.Timestamp("2023-02-15"); D0 = pd.Timestamp("2019-01-01"); D1 = pd.Timestamp("2022-12-31"); MID = pd.Timestamp("2021-01-01")
COST = 0.008; MINN = 30
FEATS = ["ret1", "ret3", "ret7", "ret14", "ret30", "ret90", "vol30", "range", "volratio", "logqv30", "tradesratio", "age",
         "rel7", "rel30", "dhigh", "dlow"]


def load():
    p = pd.read_parquet("data/research/crypto_spot/panel.parquet")
    p["date"] = pd.to_datetime(p["date"]); p = p[p["date"] <= TRUNC]
    sy = pd.read_csv("data/research/crypto_spot/symbols.csv")
    bad = set(sy.loc[sy.is_stable_fiat | sy.is_leveraged, "symbol"])
    p = p[~p["symbol"].isin(bad)]
    # forced deviation: split series at token-swap / relaunch price breaks (>=20x daily up-jump, plus hand-listed redenominations
    # SUN 2021-06-18, VEN 2018-10-19, QUICK 2023-07-21 is after truncation). Post-break segment = new symbol, age restarts.
    p = p.sort_values(["symbol", "date"]).reset_index(drop=True)
    rr = p.groupby("symbol")["close"].pct_change() + 1
    brk = (rr >= 20) | ((p["symbol"] == "SUNUSDT") & (p["date"] == "2021-06-18")) | ((p["symbol"] == "VENUSDT") & (p["date"] == "2018-10-19"))
    seg = brk.groupby(p["symbol"]).cumsum()
    new = p["symbol"] + "#" + seg.astype(str)
    newfirst = p.groupby(new)["date"].transform("min")
    ex = sy.set_index("symbol")
    p["symbol"] = np.where(seg > 0, new, p["symbol"])
    add = pd.DataFrame({"symbol": p.loc[seg > 0, "symbol"].unique()}); add["first_date"] = [str(p.loc[p.symbol == s_, "date"].min().date()) for s_ in add.symbol]
    sy = pd.concat([sy, add], ignore_index=True)
    sy["first_date"] = sy["first_date"].astype(str)
    print("price-break splits:", list(add.symbol))
    idx = pd.date_range(p["date"].min(), TRUNC, freq="D")
    W = {k: p.pivot(index="date", columns="symbol", values=k).reindex(idx) for k in ["close", "high", "low", "quote_volume", "trades"]}
    return idx, W, sy


def build(idx, W, sy):
    C = W["close"]; Cf = C.ffill()
    cols = list(C.columns)
    first = pd.to_datetime(sy.set_index("symbol")["first_date"]).reindex(cols)
    have = C.notna()
    qv = W["quote_volume"]; qv30 = qv.rolling(30, min_periods=20).median()
    elig = have & (qv30 >= 1e6) & ((idx.values[:, None] - first.values[None, :]) / np.timedelta64(1, "D") >= 60)
    lr = np.log(Cf).diff()
    btc = Cf["BTCUSDT"]
    F = {}
    for h in (1, 3, 7, 14, 30, 90):
        F[f"ret{h}"] = Cf / Cf.shift(h) - 1
    F["vol30"] = lr.rolling(30, min_periods=20).std()
    F["range"] = (W["high"] - W["low"]) / C
    F["volratio"] = qv / qv.rolling(30, min_periods=20).mean()
    F["logqv30"] = np.log(qv30)
    F["tradesratio"] = W["trades"] / W["trades"].rolling(30, min_periods=20).mean()
    F["age"] = pd.DataFrame(np.repeat(((idx.values[:, None] - first.values[None, :]) / np.timedelta64(1, "D")), 1, axis=1), index=idx, columns=cols)
    F["rel7"] = F["ret7"].sub(btc / btc.shift(7) - 1, axis=0)
    F["rel30"] = F["ret30"].sub(btc / btc.shift(30) - 1, axis=0)
    F["dhigh"] = Cf / W["high"].ffill().rolling(90, min_periods=60).max() - 1
    F["dlow"] = Cf / W["low"].ffill().rolling(90, min_periods=60).min() - 1
    Q = {}
    for k in FEATS:
        x = F[k].where(elig).replace([np.inf, -np.inf], np.nan)
        Q[k] = x.rank(axis=1, pct=True).values.astype("float32")
    bt = {"btc_ret7": (btc / btc.shift(7) - 1).values, "btc_vol30": lr["BTCUSDT"].rolling(30, min_periods=20).std().values}
    # returns: signal day d, enter close d+1, exit close d+1+h. Only entries 2019-01-01..2022-12-31.
    T = len(idx); Cv = Cf.values; hv = have.values
    R = {}
    ent_ok = (idx >= D0) & (idx <= D1)  # entry date
    for h in (7, 30):
        r = np.full(Cv.shape, np.nan, "float64")
        r[:-1 - h] = Cv[1 + h:] / Cv[1:-h] - 1 if False else Cv[1 + h:T] / Cv[1:T - h] - 1
        # r[d] aligns with entry d+1: shift rows so r[d] = ret from d+1 to d+1+h
        rr = np.full(Cv.shape, np.nan)
        rr[:T - 1 - h] = Cv[1 + h:] / Cv[1:T - h] - 1
        okd = np.zeros(T, bool); okd[:-1] = ent_ok[1:]
        ent_have = np.zeros_like(hv); ent_have[:-1] = hv[1:]
        rr[~okd] = np.nan; rr[~ent_have] = np.nan
        R[h] = rr
    dates_d = np.where(np.r_[ent_ok[1:], False])[0]  # signal days with entry in window
    return dict(idx=idx, elig=elig.values, Q=Q, bt=bt, R=R, dd=dates_d, cols=cols)


def gen_rules():
    rng = np.random.default_rng(SEED); seen = set(); rules = []
    nf = len(FEATS)
    while len(rules) < NRULES:
        f1 = FEATS[rng.integers(nf)]; q1 = int(rng.choice([1, 5])); h = int(rng.choice([7, 30])); u = rng.random()
        r = dict(f1=f1, q1=q1, h=h, kind="none", f2="", t2=0, bfeat="", bt=0, dow=-1)
        if u >= 0.2 and u < 0.7:
            f2 = FEATS[rng.integers(nf)]
            if f2 == f1: continue
            r.update(kind="x", f2=f2, t2=int(rng.choice([1, 3])))
        elif u >= 0.7 and u < 0.85:
            r.update(kind="btc", bfeat=str(rng.choice(["btc_ret7", "btc_vol30"])), bt=int(rng.choice([1, 3])))
        elif u >= 0.85:
            r.update(kind="dow", dow=int(rng.integers(7)))
        key = tuple(r.items())
        if key in seen: continue
        seen.add(key); r["id"] = len(rules); rules.append(r)
    return rules


def desc(r):
    s = f"{r['f1']} q{r['q1']}"
    if r["kind"] == "x": s += f" & {r['f2']} t{r['t2']}"
    if r["kind"] == "btc": s += f" & {r['bfeat']} t{r['bt']}"
    if r["kind"] == "dow": s += f" & dow={r['dow']}"
    return s + f" h{r['h']}"


def fam(r):
    f = r["f1"]; c = []
    if f in ("ret1", "ret3", "ret7", "ret14") and r["q1"] == 1: c.append("short-term-reversal(known)")
    if f in ("ret30", "ret90", "rel30", "rel7") and r["q1"] == 5: c.append("momentum")
    if f in ("ret30", "ret90", "rel30") and r["q1"] == 1: c.append("long-reversal")
    if f in ("vol30", "range"): c.append("vol")
    if f in ("logqv30", "age", "tradesratio", "volratio"): c.append("liquidity/size/age")
    if f in ("dhigh", "dlow"): c.append("52wk-style")
    if r["kind"] == "btc": c.append("btc-regime")
    if r["kind"] == "dow": c.append("weekday")
    return ",".join(c) or "other"


def cond(Q, f, q, thirds=False):
    x = Q[f]
    if thirds: return (x < 1 / 3) if q == 1 else (x >= 2 / 3)
    return (x < 0.2) if q == 1 else (x >= 0.8)


def dayfilter(S, r, cuts, lag):
    T = len(S["idx"])
    if r["kind"] == "btc":
        v = S["bt"][r["bfeat"]]
        if lag: v = np.r_[np.full(lag, np.nan), v[:-lag]]
        lo, hi = cuts[r["bfeat"]]
        return (v <= lo) if r["bt"] == 1 else (v >= hi)
    if r["kind"] == "dow":
        w = S["idx"].dayofweek.values
        if lag: w = np.r_[np.full(lag, -9), w[:-lag]]
        return w == r["dow"]
    return np.ones(T, bool)


def score_rule(S, r, cuts, Rp=None, lag=0):
    h = r["h"]; R = S["R"][h] if Rp is None else Rp[h]; dd = S["dd"]
    Q = S["Q"]
    def lg(a):
        if not lag: return a
        o = np.zeros_like(a) if a.dtype == bool else np.full_like(a, np.nan)
        o[lag:] = a[:-lag]; return o
    m = lg(cond(Q, r["f1"], r["q1"]))
    if r["kind"] == "x": m = m & lg(cond(Q, r["f2"], r["t2"], True))
    m = m & S["elig"]
    df = dayfilter(S, r, cuts, lag)
    Rv = S["R"][h]; uni = np.nanmean(np.where(S["elig"], S["R"][h], np.nan), axis=1) if "uni" not in S else S["uni"][h]
    Rd = R[dd]; md = m[dd] & ~np.isnan(Rd) & df[dd][:, None]
    cnt = md.sum(1)
    sm = np.where(md, Rd, 0).sum(1) / np.maximum(cnt, 1)
    net = sm - uni[dd] - COST
    gross = sm - uni[dd]
    sig = np.where((cnt >= 5) & ~np.isnan(net))[0]
    take = []; last = -10**9
    for i in sig:
        if dd[i] >= last + h: take.append(i); last = dd[i]
    take = np.array(take, int)
    return take, net[take] if len(take) else np.array([]), gross[take] if len(take) else np.array([])


def stats(S, take, x):
    d = dict(n=len(x), mean_bp=np.nan, med_bp=np.nan, t=np.nan, h1_bp=np.nan, h2_bp=np.nan, ex5_bp=np.nan, passed=False)
    if len(x) < 2: return d
    ent = S["idx"][S["dd"][take] + 1]
    mu = x.mean(); sd = x.std(ddof=1); t = mu / (sd / np.sqrt(len(x))) if sd > 0 else np.nan
    h1 = x[ent < MID]; h2 = x[ent >= MID]
    h1m = h1.mean() if len(h1) else np.nan; h2m = h2.mean() if len(h2) else np.nan
    ex5 = np.sort(x)[:-5].mean() if len(x) > 5 else np.nan
    med = np.median(x)
    d.update(mean_bp=mu * 1e4, med_bp=med * 1e4, t=t, h1_bp=h1m * 1e4, h2_bp=h2m * 1e4, ex5_bp=ex5 * 1e4)
    d["passed"] = bool(len(x) >= MINN and mu > 0 and t >= 3 and h1m > 0 and h2m > 0 and med > 0 and ex5 > 0)
    return d


def run(S, rules, cuts, Rp=None, lag=0):
    out = []
    for r in rules:
        take, x, _ = score_rule(S, r, cuts, Rp, lag)
        out.append(stats(S, take, x))
    return out


def main():
    t0 = time.time()
    idx, W, sy = load(); S = build(idx, W, sy)
    dd = S["dd"]
    S["uni"] = {h: np.nanmean(np.where(S["elig"], S["R"][h], np.nan), axis=1) for h in (7, 30)}
    cuts = {k: (np.nanpercentile(v[dd], 100 / 3), np.nanpercentile(v[dd], 200 / 3)) for k, v in S["bt"].items()}
    # universe size per year (eligible symbols on mid-year signal days, mean over days)
    el = pd.DataFrame({"y": idx.year, "n": S["elig"].sum(1)}); ny = el[(idx >= "2018-01-01") & (idx <= D1)].groupby("y")["n"].agg(["mean", "max"])
    rules = gen_rules()
    real = run(S, rules, cuts); nreal = sum(d["passed"] for d in real)
    print("real", nreal, f"{time.time()-t0:.0f}s", flush=True)
    nulls = []
    elig = S["elig"]
    for s in range(1, 11):
        rng = np.random.default_rng(s)
        P = np.tile(np.arange(elig.shape[1]), (len(idx), 1))
        for d in dd:
            c = np.where(elig[d])[0]; P[d, c] = rng.permutation(c)
        Rp = {h: np.take_along_axis(S["R"][h], P, axis=1) for h in (7, 30)}
        nulls.append(sum(d["passed"] for d in run(S, rules, cuts, Rp)))
        print("null", s, nulls[-1], flush=True)
    plc = run(S, rules, cuts, lag=365); nplc = sum(d["passed"] for d in plc)
    ok = nreal > max(nulls + [nplc]) and nreal > 3 * np.mean(nulls + [nplc])
    rdf = pd.concat([pd.DataFrame(rules), pd.DataFrame(real)], axis=1)
    rdf["desc"] = [desc(r) for r in rules]; rdf["fam"] = [fam(r) for r in rules]
    rdf["plc_passed"] = [d["passed"] for d in plc]
    rdf.to_parquet(OUTD / "luck_b3_rules.parquet")
    top = rdf[rdf["n"] >= MINN].sort_values("t", ascending=False).head(20)
    # sanity: ret30 quintile 5 vs 1, 30d horizon, gross, all discovery signal days (overlapping, descriptive)
    sn = []
    for q in (5, 1):
        m = cond(S["Q"], "ret30", q) & S["elig"]; Rd = S["R"][30][dd]; md = m[dd] & ~np.isnan(Rd)
        c = md.sum(1); ok_ = c >= 5
        g = (np.where(md, Rd, 0).sum(1) / np.maximum(c, 1) - S["uni"][30][dd])[ok_]
        sn.append((q, g.mean() * 1e4, len(g)))
    L = ["LUCK-B3 results (discovery entries 2019-01..2022-12; confirmation 2023+ entries NOT computed)",
         f"seed {SEED}, {NRULES} distinct rules; runtime {time.time()-t0:.0f}s",
         "Universe (eligible symbols/day, mean [max]) by year: " + ", ".join(f"{y}: {r['mean']:.0f} [{int(r['max'])}]" for y, r in ny.iterrows()),
         "Deviations/choices: panel truncated at 2023-02-15 (exits of late-2022 entries use Jan-2023 closes, no 2023 entry scored); "
         "FORCED: series split at token-swap price breaks (>=20x daily up-jump: COCOS, DREP, LUNA relaunch; hand-listed SUN 2021-06-18, VEN 2018-10-19), post-break segment = new symbol, age resets (unsplit, DREP/LUNA gave +1e5 bp fake returns); non-overlap = greedy every >=h days; rule mix none20/x50/btc15/dow15; BTC terciles on discovery days; perm = joint row shuffle of eligible "
         "symbols within date; placebo lags all features, BTC/weekday filters and eligibility-ranks by 365 rows; delisted exit = ffill last close; "
         "cost 80bp RT on selected, universe benchmark uncharged.",
         f"REAL pass count: {nreal}",
         "NULL pass counts (perm seeds 1..10): " + ", ".join(map(str, nulls)) + f"  (max {max(nulls)}, mean {np.mean(nulls):.2f})",
         f"DATE-PLACEBO (365d lag) pass count: {nplc}",
         f"BATCH VERDICT: {'COUNTS (real > max of all 11 nulls and > 3x their mean)' if ok else 'LUCK (fails null test) - log and stop, no survivors'}",
         f"SANITY known-sign (ret30 quintile, 30d fwd, gross vs EW universe, overlapping daily): " + "; ".join(f"q{q}: {m:+.1f}bp (n={n} days)" for q, m, n in sn) + f"; q5-q1 {sn[0][1]-sn[1][1]:+.1f}bp",
         "", "Top 20 rules by t (n>=30; bp net of 80bp RT):"]
    for _, r in top.iterrows():
        L.append(f"  #{r['id']:<4} {r['desc']:<46} n={r['n']:<4} mean={r['mean_bp']:+7.1f} med={r['med_bp']:+7.1f} t={r['t']:.2f} h1={r['h1_bp']:+7.1f} h2={r['h2_bp']:+7.1f} ex5={r['ex5_bp']:+7.1f} {'PASS' if r['passed'] else 'fail'} fam={r['fam']}")
    L.append(f"(passing rules total: {int(rdf['passed'].sum())})")
    (OUTD / "luck_b3_out.txt").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
