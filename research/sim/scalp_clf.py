"""Study SCALP-CLF (round1_prose.md "## Study SCALP-CLF"): HGB classifier for P(+30bp before -30bp, 30m) in >$1B names, 2016-18 walk-forward, 2019 judge.
usage: PYTHONPATH=. .venv/bin/python research/sim/scalp_clf.py fetch | panel | run     (no WRDS)
No parameter below was changed after seeing outcomes. Disclosed choices are printed at the end of the output file."""
import sys, os, time, random, warnings
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import numpy as np, pandas as pd, requests
warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]; D = ROOT / "data/research/scalp_clf"; BD = D / "bars"; BD.mkdir(parents=True, exist_ok=True)
OUT = ROOT / "data/research/program/scalp_clf_out.txt"
SH = Path("/Users/andrewlau/data/sharadar")
G = S = 0.003; HZN = 30; STEP = 15; K0 = 60; K1 = 330   # decision bar index k: 10:30 (k=60) .. 15:00 (k=330)
# 2018 A>1B round-trip c (median, bp) by bucket -> half-spread = c/2 (2016-19 all use 2018 values)
CB = [(60, 150, 3.8), (150, 270, 3.2), (270, 390, 3.4)]   # k ranges: 10:30-12:00, 12:00-14:00, 14:00-15:30
def hs(k):
    for a, b, c in CB:
        if a <= k < b: return c / 2 * 1e-4
    return CB[-1][2] / 2 * 1e-4
H = None
def env():
    global H
    for line in open(ROOT / ".env"):
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.strip().split("=", 1); os.environ.setdefault(k, v.strip().strip('"').strip("'"))
    H = {"APCA-API-KEY-ID": os.environ["ALPACA_API_KEY"], "APCA-API-SECRET-KEY": os.environ["ALPACA_SECRET_KEY"]}

def universe():
    f = D / "universe.parquet"
    if f.exists(): return pd.read_parquet(f)
    st = pd.read_parquet(SH / "stocks.parquet", columns=["ticker", "date", "volume", "closeunadj"]); st["date"] = pd.to_datetime(st.date)
    tk = pd.read_parquet(SH / "tickers.parquet", columns=["table", "ticker", "category"])
    ok = set(tk[(tk.table == "SEP") & tk.category.fillna("").str.startswith("Domestic Common Stock")].ticker)
    s = st[(st.date >= "2015-10-01") & (st.date <= "2019-12-31") & st.ticker.isin(ok)].sort_values(["ticker", "date"])
    s["dv"] = s.closeunadj * s.volume
    s["adv"] = s.groupby("ticker").dv.transform(lambda x: x.shift(1).rolling(20, min_periods=15).median())   # as of d-1
    u = s[(s.date >= "2016-01-01") & (s.adv >= 1e9)][["ticker", "date", "adv", "closeunadj"]].reset_index(drop=True)
    u.to_parquet(f); return u

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
            except Exception: time.sleep(3); continue
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
    env(); u = universe(); jobs = set()
    for sym, g in u.groupby("ticker"):
        for p in g.date.dt.to_period("M").unique():
            jobs.add((sym, p.year, p.month)); q = p - 1; jobs.add((sym, q.year, q.month))
    for p in pd.period_range("2015-12", "2019-12", freq="M"): jobs.add(("SPY", p.year, p.month))
    jobs = sorted(jobs); print(len(jobs), "jobs", flush=True); t0 = time.time(); n = [0]
    def w(j):
        try: fetch_one(*j)
        except Exception as e: print("ERR", j, e, flush=True)
        n[0] += 1
        if n[0] % 200 == 0: print(n[0], round(time.time() - t0), flush=True)
    with ThreadPoolExecutor(6) as ex: list(ex.map(w, jobs))

def load_bars(sym):
    fs = sorted(BD.glob(f"{sym}_*.parquet"))
    if not fs: return None
    df = pd.concat([pd.read_parquet(f) for f in fs]); df["d"] = df.t.dt.normalize(); df["mn"] = df.t.dt.hour * 60 + df.t.dt.minute - 570
    return df

def day_arrays(df):
    """-> dict date -> (O,H,L,C,V) arrays len 390 (missing bars: price ffill from previous close, vol 0); days with <200 bars dropped."""
    out = {}
    for d, g in df.groupby("d"):
        if len(g) < 200: continue
        idx = g.mn.values; a = {k: np.full(390, np.nan) for k in "ohlcv"}
        for k in "ohlcv": a[k][idx] = g[k].values
        a["v"] = np.nan_to_num(a["v"])
        c = pd.Series(a["c"]).ffill().values
        if np.isnan(c[0]):                       # first bar missing: back-fill from first available
            c = pd.Series(c).bfill().values
        for k in "ohl": a[k] = np.where(np.isnan(a[k]), c, a[k])
        a["h"] = np.maximum(a["h"], c); a["l"] = np.minimum(a["l"], c); a["c"] = c
        out[d] = (a["o"], a["h"], a["l"], a["c"], a["v"])
    return out

def feats_label(sym, days, spyd, univ_days):
    """build rows for one name. days: date-> arrays; univ_days: set of dates qualified (as of d-1). Features use bars [0..k-1] only; label bars k..k+29."""
    ds = sorted(days); rows = []
    # prior-day volume profile at 15-min windows for relvol: cum-vol array per day
    for i, d in enumerate(ds):
        if d not in univ_days or d not in spyd: continue
        prev = [x for x in ds[max(0, i - 20):i]]
        if len(prev) < 10: continue
        # data issue guard: previous day must be previous trading day (gap in data -> prev close unreliable)
        pc = days[ds[i - 1]][3][-1] if i > 0 else np.nan
        O, Hh, L, C, V = days[d]; sO, sH, sL, sC, sV = spyd[d]
        cumV = np.cumsum(V); pcum = np.mean([np.cumsum(days[p][4]) for p in prev], axis=0)
        lr = np.diff(np.log(C), prepend=np.log(C[0])); rng = (Hh - L) / C
        rng20 = pd.Series(rng).rolling(20, min_periods=5).mean().values
        pv = np.cumsum(C * V); hod = np.maximum.accumulate(Hh); lod = np.minimum.accumulate(L)
        for k in range(K0, K1 + 1, STEP):
            j = k - 1; c = C[j]
            def R(n): return c / (C[j - n] if j - n >= 0 else O[0]) - 1   # j-n<0 (r60 at 10:30) -> session open, never wraps to day end
            v15 = cumV[j] - cumV[j - 15]; b15 = pcum[j] - pcum[j - 15]
            vw = pv[j] / cumV[j] if cumV[j] > 0 else c
            sj = sC[j]
            rv = np.std(lr[j - 29:j + 1]) * np.sqrt(30)
            f = dict(sym=sym, date=d, k=k, r1=R(1), r5=R(5), r15=R(15), r30=R(30), r60=R(60), ropen=c / O[0] - 1, gap=O[0] / pc - 1,
                     rng1=rng[j], rng20=rng20[j], relvol=(v15 / b15) if b15 > 0 else np.nan, dvwap=c / vw - 1, dhod=c / hod[j] - 1, dlod=c / lod[j] - 1,
                     s5=sj / sC[j - 5] - 1, s30=sj / sC[j - 30] - 1, sopen=sj / sO[0] - 1, rel30=R(30) - (sj / sC[j - 30] - 1), mod=k, rv30=rv)
            # label (bars k..k+29)
            h = hs(k); e = c * (1 + h); tgt = e * (1 + G) + c * h; stp = e * (1 - S)
            hw = Hh[k:k + HZN]; lw = L[k:k + HZN]
            iw = np.argmax(hw >= tgt) if (hw >= tgt).any() else 999; il = np.argmax(lw <= stp) if (lw <= stp).any() else 999
            hout = hs(min(k + HZN, 389))
            if iw < il: y, pnl, pnl2 = 1, G, G
            elif il < 999: y, pnl, pnl2 = 0, -S - hout, -S - 2 * hout
            else:
                y = 0; xc = C[k + HZN - 1]; pnl = xc / e - 1 - hout
                pnl2 = xc / (c * (1 + 2 * h)) - 1 - 2 * hout
            # 2x-cost label: doubled half-spreads
            e2 = c * (1 + 2 * h); tgt2 = e2 * (1 + G) + 2 * c * h; stp2 = e2 * (1 - S)
            iw2 = np.argmax(hw >= tgt2) if (hw >= tgt2).any() else 999; il2 = np.argmax(lw <= stp2) if (lw <= stp2).any() else 999
            if iw2 < il2: y2, p2 = 1, G
            elif il2 < 999: y2, p2 = 0, -S - 2 * hout
            else: y2, p2 = 0, C[k + HZN - 1] / e2 - 1 - 2 * hout
            f.update(y=y, pnl=pnl, y2=y2, pnl2=p2, hc=h * 2e4)
            rows.append(f)
    return rows

def panel():
    u = universe(); spy = day_arrays(load_bars("SPY")); allr = []; t0 = time.time()
    for sym, g in u.groupby("ticker"):
        df = load_bars(sym)
        if df is None: print("NOBARS", sym); continue
        days = day_arrays(df); ds = set(pd.to_datetime(g.date))
        # ticker-reuse / data sanity: drop name-days whose alpaca close-to-close return disagrees with Sharadar's by >5% (split days allowed since both raw/split-adj differ)
        sh = g.set_index("date").closeunadj; bad = set()
        ad = sorted(days)
        for a, b in zip(ad[:-1], ad[1:]):
            if b in sh.index and a in sh.index:
                ra = days[b][3][-1] / days[a][3][-1]; rs = sh[b] / sh[a]
                if abs(np.log(ra / rs)) > 0.15 and abs(np.log(ra)) < 0.4: bad.add(b)   # mismatch not explained by split adjustment (ratio ~ split factor is >0.4)
        r = feats_label(sym, days, spy, ds - bad); allr += r
        print(sym, len(r), len(bad), flush=True)
    P = pd.DataFrame(allr); P.to_parquet(D / "panel.parquet"); print(P.shape, round(time.time() - t0)); print(P.groupby(P.date.dt.year).agg(n=("y", "size"), p=("y", "mean"), p2=("y2", "mean"), pnl=("pnl", "mean")))

FEATS = ["r1", "r5", "r15", "r30", "r60", "ropen", "gap", "rng1", "rng20", "relvol", "dvwap", "dhod", "dlod", "s5", "s30", "sopen", "rel30", "mod", "rv30"]
if __name__ == "__main__":
    {"fetch": fetch, "panel": panel}.get(sys.argv[1], lambda: None)()

# ================= model / evaluation =================
from sklearn.ensemble import HistGradientBoostingClassifier as HGB
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import roc_auc_score
def mk(): return HGB(max_iter=200, learning_rate=0.05, random_state=0)

def wilson_lo(k, n, z=1.96):
    if n == 0: return np.nan
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n)
    return (c - z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d

def deoverlap(df):
    """one open trade per name: accept a top-bucket decision only if >= 30 bars (full horizon) after the last accepted one, same name-day."""
    keep = []; last = {}
    for i, (s, d, k) in enumerate(zip(df.sym.values, df.date.values, df.k.values)):
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
    """returns dict name -> training label series aligned with P (real, perm within day, shift +60min within name-day)."""
    rng = np.random.RandomState(seed)
    perm = P.y.values.copy()
    for _, ix in P.groupby("date").indices.items():
        perm[ix] = rng.permutation(perm[ix])
    key = P.set_index(["sym", "date", "k"]).y
    sh = pd.Series(list(zip(P.sym, P.date, P.k + 60))).map(key.to_dict()).values  # NaN where t+60 beyond 15:00 decision grid
    return {"real": P.y.values.astype(float), "perm": perm.astype(float), "shift": sh.astype(float)}

def fit_score(Xtr, ytr, Xva, yva, Xte):
    """fit on Xtr; isotonic on Xva (inner validation); return calibrated scores for val and test."""
    ok = ~np.isnan(ytr); m = mk().fit(Xtr[ok], ytr[ok].astype(int))
    pv = m.predict_proba(Xva)[:, 1]; pt = m.predict_proba(Xte)[:, 1]
    okv = ~np.isnan(yva)
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(pv[okv], yva[okv])
    return m, iso.predict(pv), iso.predict(pt)

def summarize(df, tag, thr_info="", nul=None, L=None):
    """df: top-bucket decisions, already de-overlapped."""
    n = len(df); L = L if L is not None else []
    if n == 0: L.append(f"{tag}: no trades"); return {}
    p = df.y.mean(); p2 = df.y2.mean(); c = df.hc.mean(); ps1 = (30 + c) / 60; ps2 = (30 + 2 * c) / 60
    lo = wilson_lo(df.y.sum(), n)
    r = dict(n=n, p=p, p2=p2, lo=lo, ps1=ps1, ps2=ps2, net1=df.pnl.mean() * 1e4, net2=df.pnl2.mean() * 1e4, t1=clustered_t(df, "pnl"), t2=clustered_t(df, "pnl2"),
             ex5=df.pnl2.sort_values().iloc[:-5].mean() * 1e4 if n > 5 else np.nan, days=df.date.nunique())
    r["tpd"] = n / max(1, df.date.nunique())
    L.append(f"{tag}: n={n} trades/day(active)={r['tpd']:.1f}  p(1x label)={p:.4f} [Wilson lo {lo:.4f}]  p(2x label)={p2:.4f}  p*(1x)={ps1:.4f} p*(2x)={ps2:.4f}  "
             f"net/trade 1x={r['net1']:+.2f}bp (t {r['t1']:.2f})  2x={r['net2']:+.2f}bp (t {r['t2']:.2f})  ex-top5(2x)={r['ex5']:+.2f}bp {thr_info}")
    return r

def reliability(sc, y, L, tag):
    q = pd.qcut(pd.Series(sc).rank(method="first"), 10, labels=False)
    t = pd.DataFrame({"q": q.values, "s": sc, "y": y}).groupby("q").agg(n=("y", "size"), score=("s", "mean"), hit=("y", "mean"))
    L.append(f"reliability by decile ({tag}):"); L += ["  D%d  n=%d  mean score %.4f  hit %.4f" % (i + 1, r.n, r.score, r.hit) for i, r in t.iterrows()]
    return t.hit.values

def run():
    P = pd.read_parquet(D / "panel.parquet").sort_values(["date", "sym", "k"]).reset_index(drop=True)
    P["date"] = pd.to_datetime(P.date); X = P[FEATS].values.astype(float)
    LV = label_variants(P); sess = np.array(sorted(P.date.unique()))
    L = []; t0 = time.time()
    months = pd.period_range("2017-01", "2018-12", freq="M")
    oof = {k: np.full(len(P), np.nan) for k in LV}; thrm = {k: {} for k in LV}
    for m in months:
        ms = m.to_timestamp(); me = (m + 1).to_timestamp()
        i0 = np.searchsorted(sess, np.datetime64(ms)); cut = sess[max(0, i0 - 5)]              # train: dates < cut (5-session embargo)
        trm = (P.date < cut).values; te = ((P.date >= ms) & (P.date < me)).values
        vstart = sess[np.searchsorted(sess, np.datetime64(cut)) - 1] if False else pd.Timestamp(cut) - pd.DateOffset(months=2)
        fit = trm & (P.date < vstart - pd.Timedelta(days=7)).values; va = trm & (P.date >= vstart).values   # 7-day gap fit|val
        for nm, y in LV.items():
            mdl, sv, st_ = fit_score(X[fit], y[fit], X[va], y[va], X[te])
            oof[nm][te] = st_; thrm[nm][m] = np.nanpercentile(sv, 95)
        print(m, round(time.time() - t0), flush=True)
    # ---- OOF diagnostics 2017-2018
    mask = ~np.isnan(oof["real"]); Pm = P[mask].copy(); L.append("SCALP-CLF  (pre-reg round1_prose.md '## Study SCALP-CLF', N 979->980; no WRDS; Alpaca SIP 1-min, split-adjusted)")
    L.append(f"panel rows {len(P)} (2016-19), names {P.sym.nunique()}, base rate y={P.y.mean():.4f} y2={P.y2.mean():.4f}, mean c={P.hc.mean():.2f}bp")
    L.append("\n== OUT-OF-FOLD 2017-01..2018-12 (walk-forward, 5-session embargo) ==")
    res = {}
    for nm in LV:
        sc = oof[nm]; Pm[nm] = sc[mask]
        for rule in ("pooled95", "permonth95"):
            if rule == "pooled95":
                thr = np.nanpercentile(sc, 95); sel = Pm[Pm[nm] >= thr]
            else:
                thrs = Pm.date.dt.to_period("M").map(thrm[nm]).astype(float); sel = Pm[Pm[nm].values >= thrs.values]
            if nm == "shift":   # null evaluated on its own shifted labels as well as real labels
                sel_s = sel.copy(); sel_s["y"] = LV["shift"][sel.index]; sel_s = sel_s.dropna(subset=["y"])
                L.append(f"[{nm}/{rule}] top-bucket hit vs SHIFTED labels: n={len(sel_s)} p={sel_s.y.mean():.4f}")
            r = summarize(deoverlap(sel), f"[{nm}/{rule}] top bucket vs real labels", f"(thr pooled {np.nanpercentile(sc,95):.4f})" if rule == "pooled95" else "", L=L)
            res[(nm, rule)] = r
    ar = roc_auc_score(Pm.y, Pm.real); L.append(f"OOF AUC real model {ar:.4f}; perm null {roc_auc_score(Pm.y, Pm.perm):.4f}; shift null {roc_auc_score(Pm.y, Pm['shift']):.4f}")
    reliability(Pm.real.values, Pm.y.values, L, "OOF real")
    thr_frozen = np.nanpercentile(oof["real"], 95); thr_null = {k: np.nanpercentile(oof[k], 95) for k in ("perm", "shift")}
    L.append(f"FROZEN threshold (pooled 95th pct of 2017-18 OOF calibrated scores) = {thr_frozen:.5f}; null thresholds {thr_null}")
    # ---- JUDGE 2019 (single look)
    L.append("\n== JUDGE 2019 (single look; model retrained once on 2016-2018, inner val = last 2 months of 2018, threshold frozen) ==")
    te = (P.date >= "2019-01-01").values; trm = (P.date < "2018-12-31").values
    vs = pd.Timestamp("2018-11-01"); fit = trm & (P.date < vs - pd.Timedelta(days=7)).values; va = trm & (P.date >= vs).values
    J = P[te].copy(); models = {}; jr = {}
    for nm, y in LV.items():
        mdl, sv, st_ = fit_score(X[fit], y[fit], X[va], y[va], X[te]); J[nm] = st_; models[nm] = (mdl, sv)
    J["ylab_shift"] = LV["shift"][te]
    for nm in LV:
        thr = thr_frozen if nm == "real" else thr_null[nm]
        sel = J[J[nm] >= thr]
        if nm == "shift":
            s2 = sel.dropna(subset=["ylab_shift"]); L.append(f"[judge shift null] top-bucket hit vs SHIFTED labels n={len(s2)} p={s2.ylab_shift.mean():.4f}")
        jr[nm] = summarize(deoverlap(sel), f"[judge {nm}] top bucket (score>={thr:.4f}) vs real labels", L=L)
    L.append(f"judge share of 2019 decisions >= frozen thr: {(J.real >= thr_frozen).mean():.4f} (nominal 0.05); AUC real {roc_auc_score(J.y, J.real):.4f} perm {roc_auc_score(J.y, J.perm):.4f} shift {roc_auc_score(J.y, J['shift']):.4f}")
    hits = reliability(J.real.values, J.y.values, L, "judge 2019 real model")
    # ---- gate
    r = jr["real"]; nd = J.date.nunique(); tpd_all = r.get("n", 0) / max(1, nd)
    ceil = r.get("net2", 0) * 1e-4 * min(r.get("tpd", 0), 13) * 252 * 0.5 * 100
    L.append("\n== GATE (2019, pessimistic labels) ==")
    def gl(name, ok, d): L.append(f"  {'PASS' if ok else 'FAIL'}  {name}: {d}")
    g = []
    g.append(r["p"] > r["ps2"]); gl("hit rate p > p*(2x)", g[-1], f"p={r['p']:.4f} p*(2x)={r['ps2']:.4f}")
    g.append(r["lo"] > r["ps1"]); gl("binomial lower 95% bound > p*(1x)", g[-1], f"lo={r['lo']:.4f} p*(1x)={r['ps1']:.4f}")
    g.append(r["net2"] > 0 and r["t2"] >= 2); gl("net/trade at 2x > 0, day-clustered t >= 2", g[-1], f"{r['net2']:+.2f}bp t {r['t2']:.2f}")
    g.append(r["p"] > max(jr["perm"].get("p", 1), jr["shift"].get("p", 1))); gl("beats BOTH nulls' top-bucket hit rate", g[-1], f"real {r['p']:.4f} perm {jr['perm'].get('p',np.nan):.4f} shift {jr['shift'].get('p',np.nan):.4f}")
    g.append(bool(hits[9] >= hits[8] >= hits[7])); gl("reliability monotone in top 3 deciles (D8<=D9<=D10)", g[-1], f"D8 {hits[7]:.4f} D9 {hits[8]:.4f} D10 {hits[9]:.4f}")
    g.append(r["ex5"] > 0); gl("ex-top-5 > 0 (2x net)", g[-1], f"{r['ex5']:+.2f}bp")
    g.append(r["n"] >= 300); gl(">= 300 trades (non-overlapping per name)", g[-1], f"n={r['n']}")
    g.append(ceil >= 8); gl("ceiling at $10k >= +8pp/yr", g[-1], f"{ceil:+.2f}pp = net2 x min(trades/active-day,13 sequential slots) x 252 x 50% capture")
    L.append(f"  trades per active day {r['tpd']:.1f}; trades per calendar trading day {tpd_all:.2f}")
    L.append("  VERDICT: " + ("PASS" if all(g) else "KILL") + f"  ({sum(g)}/8)")
    # ---- permutation importance (inner val 2018-11..12 of judge model, label-free of 2019)
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
1. Decision at minute t: features use 1-min bars that closed by t (bar index <= k-1); entry price = close of bar k-1; the outcome scan uses bars k..k+29 (strictly after). Decisions at 10:30,10:45,...,15:00.
2. Half-spread = 2018 A>1B round-trip c/2 (median): 10:30-12:00 1.9bp, 12:00-14:00 1.6bp, 14:00-15:30 1.7bp; used for all of 2016-19. 2x = doubled.
3. Label: entry e = C(1+h_in); WIN if high >= e(1+0.003)+C*h; LOSS if low <= e(1-0.003); same bar -> LOSS; else time-out at close of bar k+29. P&L: win +30bp of e; loss -30bp - h_out (stop exit pays the half-spread, conservative);
   time-out = close/e-1-h_out. Because the spreads are inside the label thresholds, P&L at 1x already nets costs; p*(1x/2x)=(30+c)/60 and (30+2c)/60 are the registered formula (stricter than the realized breakeven) and the gate compares y (registered 1x label) to p*(2x); y2 (2x relabel) is also printed.
4. 2x net/trade uses the 2x relabel (doubled half-spreads in thresholds and exits) on the SAME selected trades (selection by the 1x-trained model).
5. Threshold: registration says 95th pct of OOF scores of the training window, unavailable for the first fold; used (a) per-month: 95th pct of calibrated scores on that fold's inner validation set, and (b) pooled: 95th pct of all 2017-18 OOF scores (this is the frozen judge threshold, as the judge section specifies). Both printed; pooled is primary.
6. Isotonic/inner validation = last 2 months before the 5-session embargo (7-day gap between fit and val); fit uses everything earlier. HGB defaults + max_iter 200, lr 0.05, random_state 0 (sklearn default early stopping 'auto' active at n>10000).
7. Nulls are trained with the same code on (a) labels permuted within day (train+val), (b) label of the same name-day at t+60min (NaN dropped); both scored on REAL test rows with real labels, threshold = own pooled OOF 95th pct. The shift null is also reported against shifted test labels. Gate compares real p to the larger null p.
8. Non-overlap: within a name-day a top-bucket decision is accepted only >=30 bars after the previous accepted one (full horizon blocked, outcome-independent); trades never span days.
9. Universe: Sharadar SEP 'Domestic Common Stock' rows with 20d median(closeunadj*volume) as of d-1 >= $1B (min 15 obs); no price filter. Names with Sharadar tickers lacking an Alpaca symbol (suffix-digit delisted tickers, e.g. APC1) are missing: survivorship-limited in the delisted direction, count in the log. Name-days where Alpaca vs Sharadar daily returns disagree (>15% log diff and not split-sized) are dropped (ticker-reuse guard). Days with <200 bars dropped. 2016-19 universe is 25-33 names/day (no subsampling needed).
10. Prior close for the gap = last RTH bar of the previous available day; relvol baseline = mean cumulative-volume profile of the prior up-to-20 days (>=10 required), same clock window. Regular hours only (09:30-16:00 ET bars).
11. Binomial lower bound = Wilson 95% two-sided lower (z=1.96). Day-clustered t = mean / (sqrt(sum_d (sum of demeaned pnl in day d)^2)/n). Ex-top-5 = drop the 5 highest-P&L trades (2x). Ceiling = net2 x min(trades per active day, 13 sequential 30-min slots) x 252 x 50% capture, all capital per trade (pp of account), ignoring whole-share and margin limits; this is generous on trade count.
12. Permutation importance computed on the judge model's inner validation set (2018-11..12), not on 2019, so the judge look is untouched. Minute bars are split-adjusted only, not dividend-adjusted.
"""
if __name__ == "__main__" and sys.argv[1] == "run": run()
