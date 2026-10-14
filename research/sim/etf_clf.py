"""Study ETF-CLF (round1_prose.md "## Study ETF-CLF"): HGB classifier for P(+15bp before -15bp, 30m) on 26 non-QQQ ETFs, F3 cross-asset features.
usage: PYTHONPATH=. .venv/bin/python research/sim/etf_clf.py fetch | corrupt | panel | run     (no WRDS)
Derived from research/sim/scalp_clf.py. No parameter below was changed after seeing outcomes. Disclosed choices are printed at the end of the output."""
import sys, os, time, warnings
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import numpy as np, pandas as pd, requests
warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]; D = ROOT / "data/research/etf_clf"; BD = D / "bars"; BD.mkdir(parents=True, exist_ok=True)
OUT = ROOT / "data/research/program/etf_clf_out.txt"
ETFS = "SPY IWM DIA XLF XLE XLK XLV XLI XLY XLP XLU XLB EEM EFA EWJ FXI TLT IEF HYG LQD GLD SLV USO GDX XBI KRE".split()
ID = {s: i for i, s in enumerate(ETFS)}
XS = ["SPY", "TLT", "GLD", "USO", "EEM", "HYG"]
G = S = 0.0015; HZN = 30; STEP = 10; K0 = 30; K1 = 350     # decision at minute index k: 10:00 (k=30) .. 15:20 (k=350); last label bar 379 < 390
def hsp(sym): return (0.25 if sym in ("SPY", "IWM", "DIA") else 1.5) * 1e-4
H = None
def env():
    global H
    for line in open(ROOT / ".env"):
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.strip().split("=", 1); os.environ.setdefault(k, v.strip().strip('"').strip("'"))
    H = {"APCA-API-KEY-ID": os.environ["ALPACA_API_KEY"], "APCA-API-SECRET-KEY": os.environ["ALPACA_SECRET_KEY"]}

def fetch_one(sym, y, m):
    fn = BD / f"{sym}_{y}{m:02d}.parquet"
    if fn.exists(): return
    s0 = pd.Timestamp(y, m, 1); e0 = s0 + pd.offsets.MonthBegin(1)
    out, tok = [], None
    for pg in range(60):
        q = {"timeframe": "1Min", "start": s0.strftime("%Y-%m-%dT00:00:00Z"), "end": e0.strftime("%Y-%m-%dT00:00:00Z"), "adjustment": "split", "feed": "sip", "limit": 10000}
        if tok: q["page_token"] = tok
        for k in range(8):
            try: r = requests.get(f"https://data.alpaca.markets/v2/stocks/{sym}/bars", params=q, headers=H, timeout=60)
            except requests.RequestException as e: print("net retry", sym, y, m, e, flush=True); time.sleep(3); continue
            if r.status_code == 429: time.sleep(4 * (k + 1)); continue
            break
        else: raise RuntimeError("retry")
        if r.status_code >= 400: raise RuntimeError(f"{sym} {r.status_code} {r.text[:100]}")
        j = r.json(); out += j.get("bars") or []; tok = j.get("next_page_token")
        if not tok: break
    df = pd.DataFrame(out)
    if len(df):
        t = pd.to_datetime(df.t, utc=True).dt.tz_convert("America/New_York")
        df = pd.DataFrame({"t": t.dt.tz_localize(None), "o": df.o, "h": df.h, "l": df.l, "c": df.c, "v": df.v})
        mod = df.t.dt.hour * 60 + df.t.dt.minute; df = df[(mod >= 570) & (mod < 960)]
    else: df = pd.DataFrame(columns=["t", "o", "h", "l", "c", "v"])
    df.to_parquet(fn)

def fetch():
    env(); jobs = sorted((s, p.year, p.month) for s in ETFS for p in pd.period_range("2015-12", "2019-12", freq="M"))
    print(len(jobs), "jobs", flush=True); t0 = time.time(); n = [0]
    def w(j):
        try: fetch_one(*j)
        except (RuntimeError, OSError) as e: print("ERR", j, e, flush=True)
        n[0] += 1
        if n[0] % 100 == 0: print(n[0], round(time.time() - t0), flush=True)
    with ThreadPoolExecutor(6) as ex: list(ex.map(w, jobs))

def load_bars(sym):
    fs = sorted(BD.glob(f"{sym}_*.parquet"))
    if not fs: return None
    df = pd.concat([pd.read_parquet(f) for f in fs]); df["d"] = df.t.dt.normalize(); df["mn"] = df.t.dt.hour * 60 + df.t.dt.minute - 570
    return df

def day_arrays(df):
    out = {}
    for d, g in df.groupby("d"):
        if len(g) < 200: continue
        idx = g.mn.values; a = {k: np.full(390, np.nan) for k in "ohlcv"}
        for k in "ohlcv": a[k][idx] = g[k].values
        a["v"] = np.nan_to_num(a["v"])
        c = pd.Series(a["c"]).ffill().values
        if np.isnan(c[0]): c = pd.Series(c).bfill().values
        for k in "ohl": a[k] = np.where(np.isnan(a[k]), c, a[k])
        a["h"] = np.maximum(a["h"], c); a["l"] = np.minimum(a["l"], c); a["c"] = c
        out[d] = (a["o"], a["h"], a["l"], a["c"], a["v"])
    return out

FEATS = ["r1", "r5", "r15", "r30", "r60", "ropen", "gap", "rel30", "rv30", "relvol", "dvwap", "mod",
         "spy5", "spy30", "tlt5", "tlt30", "gld5", "gld30", "uso5", "uso30", "eem5", "eem30", "hyg5", "hyg30", "etf"]
CAT = FEATS.index("etf")

def feat_at(k, arr, xs, pc, pcum):
    """features at decision k using ONLY bar indices <= k-1. arr=(O,H,L,C,V) own; xs=dict XS-> arrays; pc prev close; pcum prior-days mean cum-volume profile."""
    O, Hh, L, C, V = arr; j = k - 1; c = C[j]
    def R(n, A=C, O0=None):
        o0 = A[0] if O0 is None else O0
        return A[j] / (A[j - n] if j - n >= 0 else o0) - 1
    cumV = np.cumsum(V[:k]); v30 = cumV[j] - (cumV[j - 30] if j >= 30 else 0.0); b30 = pcum[j] - (pcum[j - 30] if j >= 30 else 0.0)   # j-30<0 (k=30) must not wrap to day end
    pv = np.sum(C[:k] * V[:k]); vw = pv / cumV[j] if cumV[j] > 0 else c
    lr = np.diff(np.log(C[:k]), prepend=np.log(C[0]))
    f = dict(r1=R(1), r5=R(5), r15=R(15), r30=R(30), r60=R(60, O0=O[0]), ropen=c / O[0] - 1, gap=O[0] / pc - 1,
             rv30=np.std(lr[j - 29:j + 1]) * np.sqrt(30), relvol=(v30 / b30) if b30 > 0 else np.nan, dvwap=c / vw - 1, mod=k)
    def Rx(s, n): return xs[s][3][j] / (xs[s][3][j - n] if j - n >= 0 else xs[s][0][0]) - 1   # before n bars exist: session open
    f["rel30"] = f["r30"] - Rx("SPY", 30)
    for s in XS: f[s.lower() + "5"] = Rx(s, 5); f[s.lower() + "30"] = Rx(s, 30)
    return f

def label_at(k, arr, sym):
    O, Hh, L, C, V = arr; c = C[k - 1]; h = hsp(sym); out = {}
    hw = Hh[k:k + HZN]; lw = L[k:k + HZN]; xc = C[k + HZN - 1]
    for tag, m in (("", 1), ("2", 2)):
        e = c * (1 + m * h); tgt = e * (1 + G) + m * c * h; stp = e * (1 - S)
        iw = np.argmax(hw >= tgt) if (hw >= tgt).any() else 999; il = np.argmax(lw <= stp) if (lw <= stp).any() else 999
        if iw < il: y, p = 1, G                       # same-bar (iw==il) -> stop
        elif il < 999: y, p = 0, -S - m * h
        else: y, p = 0, xc / e - 1 - m * h
        out["y" + tag] = y; out["pnl" + tag] = p
    out["d5"] = C[k - 1 + 5] / c - 1; out["d15"] = C[k - 1 + 15] / c - 1; out["d30"] = C[k - 1 + 30] / c - 1
    out["hc"] = h * 2e4
    return out

def prep(sym_days, ds, i):
    prev = ds[max(0, i - 20):i]
    pcum = np.mean([np.cumsum(sym_days[p][4]) for p in prev], axis=0)
    return pcum

def build_panel(ALL, only_days=None):
    rows = []
    for sym in ETFS:
        days = ALL[sym]; ds = sorted(days)
        for i, d in enumerate(ds):
            if only_days is not None and d not in only_days: continue
            if i < 10 or any(d not in ALL[s] for s in XS): continue
            if (d - ds[i - 1]).days > 5: continue
            prev = ds[max(0, i - 20):i]; pcum = np.mean([np.cumsum(days[p][4]) for p in prev], axis=0)
            pc = days[ds[i - 1]][3][-1]; xs = {s: ALL[s][d] for s in XS}
            for k in range(K0, K1 + 1, STEP):
                f = feat_at(k, days[d], xs, pc, pcum); f.update(label_at(k, days[d], sym)); f.update(sym=sym, date=d, k=k, etf=ID[sym]); rows.append(f)
    return rows

def load_all():
    ALL = {}
    for s in ETFS:
        df = load_bars(s)
        if df is None: raise SystemExit(f"no bars {s}")
        ALL[s] = day_arrays(df)
    return ALL

def corrupt():
    """Lookahead test: for sample days and decision times, replace every bar at index >= k (own + cross-asset ETFs) with random garbage; features must be bit-identical."""
    ALL = load_all(); rng = np.random.RandomState(1); bad = 0; n = 0
    for sym in ["SPY", "XLE", "GDX"]:
        days = ALL[sym]; ds = sorted(days)
        for i in [40, 300, 700]:
            d = ds[i]
            if any(d not in ALL[s] for s in XS): continue
            prev = ds[i - 20:i]; pcum = np.mean([np.cumsum(days[p][4]) for p in prev], axis=0); pc = days[ds[i - 1]][3][-1]
            xs = {s: ALL[s][d] for s in XS}
            for k in range(K0, K1 + 1, 40):
                f0 = feat_at(k, days[d], xs, pc, pcum)
                def cor(arr):
                    a = [x.copy() for x in arr]
                    for x in a: x[k:] = rng.uniform(0.5, 2, 390 - k) * (x[k - 1] if x[k - 1] != 0 else 1) * rng.choice([0.2, 1, 5], 390 - k)
                    return tuple(a)
                f1 = feat_at(k, cor(days[d]), {s: cor(xs[s]) for s in XS}, pc, pcum)
                n += 1
                for key in f0:
                    a, b = f0[key], f1[key]
                    if not (a == b or (np.isnan(a) and np.isnan(b))): bad += 1; print("LOOKAHEAD", sym, d, k, key, a, b)
    msg = f"corruption test: {n} (etf,day,k) cases, data at index >= k randomized, {bad} feature mismatches"
    print(msg); (D / "corrupt.log").write_text(msg + "\n"); assert bad == 0

def panel():
    t0 = time.time(); ALL = load_all(); rows = build_panel(ALL); P = pd.DataFrame(rows); P.to_parquet(D / "panel.parquet")
    print(P.shape, round(time.time() - t0)); print(P.groupby(P.date.dt.year).agg(n=("y", "size"), p=("y", "mean"), p2=("y2", "mean"), pnl=("pnl", "mean")))

# ================= model / evaluation =================
from sklearn.ensemble import HistGradientBoostingClassifier as HGB
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import roc_auc_score
def mk(): return HGB(max_iter=200, learning_rate=0.05, random_state=0, categorical_features=[CAT])

def wilson_lo(k, n, z=1.96):
    if n == 0: return np.nan
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n)
    return (c - z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d

def deoverlap(df):
    keep = []; last = {}
    for s, d, k in zip(df.sym.values, df.date.values, df.k.values):
        key = (s, d)
        if key in last and k < last[key] + HZN: keep.append(False); continue
        last[key] = k; keep.append(True)
    return df[np.array(keep)]

def clustered_t(df, col):
    x = df[col].values; m = x.mean(); n = len(x)
    if n < 3: return np.nan
    cs = (df.assign(_e=x - m).groupby("date")._e.sum()).values
    se = np.sqrt((cs ** 2).sum()) / n
    return m / se if se > 0 else np.nan

def label_variants(P, seed=0):
    rng = np.random.RandomState(seed); perm = P.y.values.copy()
    for _, ix in P.groupby("date").indices.items(): perm[ix] = rng.permutation(perm[ix])
    key = P.set_index(["sym", "date", "k"]).y
    sh = pd.Series(list(zip(P.sym, P.date, P.k + 60))).map(key.to_dict()).values
    return {"real": P.y.values.astype(float), "perm": perm.astype(float), "shift": sh.astype(float)}

def fit_score(Xtr, ytr, Xva, yva, Xte):
    ok = ~np.isnan(ytr); m = mk().fit(Xtr[ok], ytr[ok].astype(int))
    pv = m.predict_proba(Xva)[:, 1]; pt = m.predict_proba(Xte)[:, 1]; okv = ~np.isnan(yva)
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(pv[okv], yva[okv])
    return m, iso.predict(pv), iso.predict(pt)

def summarize(df, tag, thr_info="", L=None):
    n = len(df)
    if n == 0: L.append(f"{tag}: no trades"); return {}
    p = df.y.mean(); p2 = df.y2.mean(); c = df.hc.mean(); ps1 = (15 + c) / 30; ps2 = (15 + 2 * c) / 30; lo = wilson_lo(df.y.sum(), n)
    r = dict(n=n, p=p, p2=p2, lo=lo, ps1=ps1, ps2=ps2, net1=df.pnl.mean() * 1e4, net2=df.pnl2.mean() * 1e4, t1=clustered_t(df, "pnl"), t2=clustered_t(df, "pnl2"),
             ex5=df.pnl2.sort_values().iloc[:-5].mean() * 1e4 if n > 5 else np.nan, days=df.date.nunique()); r["tpd"] = n / max(1, r["days"])
    L.append(f"{tag}: n={n} trades/day(active)={r['tpd']:.1f}  p(1x label)={p:.4f} [Wilson lo {lo:.4f}]  p(2x label)={p2:.4f}  p*(1x)={ps1:.4f} p*(2x)={ps2:.4f}  "
             f"net/trade 1x={r['net1']:+.2f}bp (t {r['t1']:.2f})  2x={r['net2']:+.2f}bp (t {r['t2']:.2f})  ex-top5(2x)={r['ex5']:+.2f}bp {thr_info}")
    return r

def reliability(sc, y, L, tag):
    q = pd.qcut(pd.Series(sc).rank(method="first"), 10, labels=False)
    t = pd.DataFrame({"q": q.values, "s": sc, "y": y}).groupby("q").agg(n=("y", "size"), score=("s", "mean"), hit=("y", "mean"))
    L.append(f"reliability by decile ({tag}):"); L += ["  D%d  n=%d  mean score %.4f  hit %.4f" % (i + 1, r.n, r.score, r.hit) for i, r in t.iterrows()]
    return t.hit.values

def byetf(df, L, tag):
    g = df.groupby("sym").agg(n=("y", "size"), p=("y", "mean"), net1=("pnl", lambda x: x.mean() * 1e4), net2=("pnl2", lambda x: x.mean() * 1e4)).sort_values("n", ascending=False)
    L.append(f"by-ETF top-bucket (de-overlapped) {tag}:"); L += [f"  {s:4s} n={int(r.n):4d} p={r.p:.3f} net1={r.net1:+.2f}bp net2={r.net2:+.2f}bp" for s, r in g.iterrows()]

def drift(sel, P, L, tag):
    L.append(f"mean mid drift (bp, close of decision bar -> +5/+15/+30 min), {tag}: top-bucket (n={len(sel)}) vs all decisions (n={len(P)})")
    for c in ("d5", "d15", "d30"):
        L.append(f"  {c}: top {sel[c].mean()*1e4:+.2f}bp  all {P[c].mean()*1e4:+.2f}bp  diff {(sel[c].mean()-P[c].mean())*1e4:+.2f}bp  (top t-ish via day-clustered {clustered_t(sel.assign(z=sel[c]-P[c].mean()), 'z'):.2f})")

def run():
    P = pd.read_parquet(D / "panel.parquet").sort_values(["date", "sym", "k"]).reset_index(drop=True)
    P["date"] = pd.to_datetime(P.date); X = P[FEATS].values.astype(float)
    LV = label_variants(P); sess = np.array(sorted(P.date.unique())); L = []; t0 = time.time()
    months = pd.period_range("2017-01", "2018-12", freq="M")
    oof = {k: np.full(len(P), np.nan) for k in LV}; thrm = {k: {} for k in LV}
    for m in months:
        ms = m.to_timestamp(); me = (m + 1).to_timestamp()
        i0 = np.searchsorted(sess, np.datetime64(ms)); cut = sess[max(0, i0 - 5)]
        trm = (P.date < cut).values; te = ((P.date >= ms) & (P.date < me)).values
        vstart = pd.Timestamp(cut) - pd.DateOffset(months=2)
        fit = trm & (P.date < vstart - pd.Timedelta(days=7)).values; va = trm & (P.date >= vstart).values
        for nm, y in LV.items():
            mdl, sv, st_ = fit_score(X[fit], y[fit], X[va], y[va], X[te]); oof[nm][te] = st_; thrm[nm][m] = np.nanpercentile(sv, 95)
        print(m, round(time.time() - t0), flush=True)
    mask = ~np.isnan(oof["real"]); Pm = P[mask].copy()
    L.append("ETF-CLF  (pre-reg round1_prose.md '## Study ETF-CLF', N 985->986; no WRDS; Alpaca SIP 1-min, split-adjusted only)")
    L.append(f"panel rows {len(P)} (2016-19), ETFs {P.sym.nunique()}, base rate y={P.y.mean():.4f} y2={P.y2.mean():.4f}, mean c={P.hc.mean():.2f}bp")
    L.append("\n== OUT-OF-FOLD 2017-01..2018-12 (walk-forward, 5-session embargo) ==")
    for nm in LV:
        sc = oof[nm]; Pm[nm] = sc[mask]
        for rule in ("pooled95", "permonth95"):
            if rule == "pooled95": thr = np.nanpercentile(sc, 95); sel = Pm[Pm[nm] >= thr]
            else: thrs = Pm.date.dt.to_period("M").map(thrm[nm]).astype(float); sel = Pm[Pm[nm].values >= thrs.values]
            if nm == "shift":
                sel_s = sel.copy(); sel_s["y"] = LV["shift"][sel.index]; sel_s = sel_s.dropna(subset=["y"])
                L.append(f"[{nm}/{rule}] top-bucket hit vs SHIFTED labels: n={len(sel_s)} p={sel_s.y.mean():.4f}")
            summarize(deoverlap(sel), f"[{nm}/{rule}] top bucket vs real labels", f"(thr pooled {np.nanpercentile(sc,95):.4f})" if rule == "pooled95" else "", L=L)
    L.append(f"OOF AUC real model {roc_auc_score(Pm.y, Pm.real):.4f}; perm null {roc_auc_score(Pm.y, Pm.perm):.4f}; shift null {roc_auc_score(Pm.y, Pm['shift']):.4f}")
    reliability(Pm.real.values, Pm.y.values, L, "OOF real")
    thr_frozen = np.nanpercentile(oof["real"], 95); thr_null = {k: np.nanpercentile(oof[k], 95) for k in ("perm", "shift")}
    L.append(f"FROZEN threshold (pooled 95th pct of 2017-18 OOF calibrated scores) = {thr_frozen:.5f}; null thresholds {thr_null}")
    selo = deoverlap(Pm[Pm.real >= thr_frozen]); byetf(selo, L, "OOF 2017-18"); drift(Pm[Pm.real >= thr_frozen], Pm, L, "OOF 2017-18")
    L.append("\n== JUDGE 2019 (single look; model retrained once on 2016-2018, inner val = last 2 months of 2018, threshold frozen) ==")
    te = (P.date >= "2019-01-01").values; trm = (P.date < "2018-12-31").values
    vs = pd.Timestamp("2018-11-01"); fit = trm & (P.date < vs - pd.Timedelta(days=7)).values; va = trm & (P.date >= vs).values
    J = P[te].copy(); models = {}; jr = {}
    for nm, y in LV.items():
        mdl, sv, st_ = fit_score(X[fit], y[fit], X[va], y[va], X[te]); J[nm] = st_; models[nm] = (mdl, sv)
    J["ylab_shift"] = LV["shift"][te]
    for nm in LV:
        thr = thr_frozen if nm == "real" else thr_null[nm]; sel = J[J[nm] >= thr]
        if nm == "shift":
            s2 = sel.dropna(subset=["ylab_shift"]); L.append(f"[judge shift null] top-bucket hit vs SHIFTED labels n={len(s2)} p={s2.ylab_shift.mean():.4f}")
        jr[nm] = summarize(deoverlap(sel), f"[judge {nm}] top bucket (score>={thr:.4f}) vs real labels", L=L)
    L.append(f"judge share of 2019 decisions >= frozen thr: {(J.real >= thr_frozen).mean():.4f} (nominal 0.05); AUC real {roc_auc_score(J.y, J.real):.4f} perm {roc_auc_score(J.y, J.perm):.4f} shift {roc_auc_score(J.y, J['shift']):.4f}")
    hits = reliability(J.real.values, J.y.values, L, "judge 2019 real model")
    selj = deoverlap(J[J.real >= thr_frozen]); byetf(selj, L, "JUDGE 2019"); drift(J[J.real >= thr_frozen], J, L, "JUDGE 2019")
    r = jr["real"]; nd = J.date.nunique(); tpd_all = r.get("n", 0) / max(1, nd)
    # ceiling: each trade occupies 30 of 390 min; 13 sequential slots x 4 concurrent (4x intraday BP) = 52 slots/day; all-capital-per-slot; 50% capture
    ceil = r.get("net2", 0) * 1e-4 * min(tpd_all, 52) * 252 * 0.5 * 100; ceil_act = r.get("net2", 0) * 1e-4 * min(r.get("tpd", 0), 52) * 252 * 0.5 * 100
    L.append("\n== GATE (2019, pessimistic labels) ==")
    def gl(name, ok, d): L.append(f"  {'PASS' if ok else 'FAIL'}  {name}: {d}")
    g = []
    g.append(r["p"] > r["ps2"]); gl("hit rate p > p*(2x)", g[-1], f"p={r['p']:.4f} p*(2x)={r['ps2']:.4f}")
    g.append(r["lo"] > r["ps1"]); gl("Wilson lower 95% bound > p*(1x)", g[-1], f"lo={r['lo']:.4f} p*(1x)={r['ps1']:.4f}")
    g.append(r["net2"] > 0 and r["t2"] >= 2); gl("net/trade at 2x > 0, day-clustered t >= 2", g[-1], f"{r['net2']:+.2f}bp t {r['t2']:.2f}")
    g.append(r["p"] > max(jr["perm"].get("p", 1), jr["shift"].get("p", 1))); gl("beats BOTH nulls' top-bucket hit rate", g[-1], f"real {r['p']:.4f} perm {jr['perm'].get('p',np.nan):.4f} shift {jr['shift'].get('p',np.nan):.4f}")
    g.append(bool(hits[9] >= hits[8] >= hits[7])); gl("reliability monotone in top 3 deciles (D8<=D9<=D10)", g[-1], f"D8 {hits[7]:.4f} D9 {hits[8]:.4f} D10 {hits[9]:.4f}")
    g.append(r["ex5"] > 0); gl("ex-top-5 > 0 (2x net)", g[-1], f"{r['ex5']:+.2f}bp")
    g.append(r["n"] >= 300); gl(">= 300 trades (one open per ETF)", g[-1], f"n={r['n']}")
    g.append(ceil >= 8); gl("ceiling at $10k >= +8pp/yr", g[-1], f"{ceil:+.2f}pp (net2 x min(trades per trading day {tpd_all:.2f},52) x 252 x 50%); using trades per ACTIVE day {r.get('tpd',0):.1f}: {ceil_act:+.2f}pp")
    L.append(f"  trades per active day {r['tpd']:.1f}; trades per calendar trading day {tpd_all:.2f}")
    L.append("  VERDICT: " + ("PASS" if all(g) else "KILL") + f"  ({sum(g)}/8)")
    mdl, _ = models["real"]; vi = np.where(va)[0]; rs = np.random.RandomState(0); vi = rs.choice(vi, min(60000, len(vi)), replace=False)
    base = roc_auc_score(P.y.values[vi], mdl.predict_proba(X[vi])[:, 1]); imp = {}
    for j, f in enumerate(FEATS):
        d = []
        for _ in range(3):
            Xp = X[vi].copy(); Xp[:, j] = rs.permutation(Xp[:, j]); d.append(base - roc_auc_score(P.y.values[vi], mdl.predict_proba(Xp)[:, 1]))
        imp[f] = np.mean(d)
    L.append(f"\npermutation importance (AUC drop, judge model, inner-val 2018-11..12 n={len(vi)}, base AUC {base:.4f}) top 10:")
    L += [f"  {f:8s} {v:+.5f}" for f, v in sorted(imp.items(), key=lambda x: -x[1])[:10]]
    L.append(DISCLOSED); OUT.write_text("\n".join(L) + "\n"); print("\n".join(L))

DISCLOSED = """
== DISCLOSED CHOICES (ambiguities read conservatively) ==
1. Decision at minute-index k (10:00,10:10,...,15:20): features use bars with index <= k-1 (the minute that closed at t); entry price = close of bar k-1; outcome scan uses bars k..k+29 (strictly after). Corruption test (data at index >= k randomized, own + 6 cross-asset ETFs) passed: data/research/etf_clf/corrupt.log.
2. Half-spread 0.25bp (SPY/IWM/DIA), 1.5bp others, per registration; 2x doubles. Entry e=C(1+mh); WIN if high >= e(1.0015)+m*C*h; LOSS if low <= e(1-0.0015); same bar -> LOSS; else time-out at close of bar k+29 minus m*h. P&L: win +15bp of e; loss -15bp - m*h; time-out close/e-1-m*h. Spreads sit inside the thresholds so 1x P&L already nets cost.
3. p*(1x)=(15+c)/30, p*(2x)=(15+2c)/30 with c = round-trip bp (2*half-spread, mean over selected trades): same formula as SCALP-CLF scaled to G=15bp. Gate compares y (1x label) to p*(2x); net2 uses the 2x relabel on the same selected trades.
4. Threshold: pooled 95th pct of all 2017-18 OOF calibrated scores (frozen for judge); per-month fold-validation 95th pct also printed. Nulls trained identically; null thresholds = their own pooled OOF 95th pct; gate compares real p to larger null p.
5. Isotonic/inner val = last 2 months before the 5-session embargo (7-day gap fit|val). HGB max_iter 200, lr 0.05, random_state 0, categorical ETF id (categorical_features), sklearn default early stopping 'auto'.
6. Non-overlap: per ETF, a top-bucket decision accepted only >=30 bars after the last accepted one on the same ETF-day (outcome-independent); different ETFs may overlap concurrently (registration only requires one open trade per ETF). Trades never span days.
7. Ceiling: 'deployed share with 4x intraday BP' read as up to 4 concurrent full-capital positions, i.e. 13 sequential 30-min slots x 4 = 52 slots/day; ceiling = net2 x min(trades per CALENDAR trading day, 52) x 252 x 50% capture (the conservative of calendar vs active-day counts; active-day version also printed). The 4x BP is applied to trade count (capacity), not to per-trade size, so no leverage multiplication of net.
8. Days with <200 bars dropped; rows need >=10 prior days, previous day within 5 calendar days, and all six cross-asset ETFs present that day. Prior close for the gap = last RTH bar of previous available day. relvol baseline = mean cumulative-volume profile of prior up-to-20 days, same clock window (last 30 min vs same clock). 'own returns since open' = c/O[0]-1; r60 at k<60 falls back to the session open. 'own minus SPY 30min' = rel30. SPY/TLT/GLD/USO/EEM/HYG 5- and 30-min returns taken from each ETF's own bars (SPY features are constant-in-ETF same-day-same-time).
9. No separate vol/range feature beyond the registered rv30 (own realized 30-min vol, std of 1-min log returns x sqrt(30)); dhod/dlod/rng features from SCALP-CLF dropped as unregistered.
10. Wilson 95% lower bound; day-clustered t = mean/(sqrt(sum_d(sum of demeaned pnl)^2)/n); ex-top-5 drops the 5 highest 2x P&L. Drift = mean mid return from the decision bar's close to +5/+15/+30 min, top bucket (de-overlap not applied for the drift comparison) vs all decisions.
11. Bug caught by the corruption test BEFORE any model run: at k=30 the 30-bar lookbacks wrapped to the day's last bar (negative index); fixed to fall back to the session open (cross-asset and own) and to zero/day-open for the volume window. The panel was rebuilt after the fix; no model outcome had been read.
12. Permutation importance computed on the judge model's inner validation set (2018-11..12), not 2019. Minute bars split-adjusted only; no cached bars reused (none for these ETFs outside dividend-adjusted night/m1).
"""
if __name__ == "__main__":
    {"fetch": fetch, "corrupt": corrupt, "panel": panel, "run": run}[sys.argv[1]]()
