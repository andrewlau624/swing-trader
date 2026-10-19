"""Study IND-SWING: 40 swing indicators, extreme tails + frozen combos + ML composite, 2-30 day holds
(pre-reg round1_prose.md "Study IND-SWING"). Run: PYTHONPATH=. .venv/bin/python -m research.sim.ind_swing

Choices the registration left open (stated, not tuned):
 - Signal rows = every 5th trading day from 2004-01-02; features are computed on daily bars, then sampled.
 - Adjusted H/L/O = raw * closeadj/close; volume adjusted = volume * close/closeadj (split-consistent).
 - Delisting: last print then flat (as LUCK-B1). Forward returns > +300% or < -99% are set NaN (data-bug guard).
 - Permutation null on a tail = a random subset of the same size among names with a valid feature (identical to
   permuting the feature across names within the date).
"""
from __future__ import annotations
import os, time, pathlib
import numpy as np, pandas as pd, pyarrow.parquet as pq
from .program_books import dsr

SH = os.path.expanduser("~/data/sharadar")
OUT = pathlib.Path("data/research/program/ind_swing_out.txt")
LOAD0, LOAD1, SIG0 = "2002-01-01", "2026-10-15", "2004-01-01"
DISC = ("2004-01-01", "2014-12-31"); DHALF = "2010-01-01"
JUDG = ("2015-01-01", "2026-09-30"); JHALF = "2021-01-01"
HZ = [2, 5, 10, 20, 30]; COST = 0.0020; TAIL = 0.02
NTRIALS = 1002


def load():
    tk = pq.read_table(f"{SH}/tickers.parquet", columns=["table", "ticker", "category"]).to_pandas()
    tk = tk[(tk["table"] == "SEP") & tk["category"].astype(str).str.startswith("Domestic Common Stock")]
    flt = [("date", ">=", pd.Timestamp(LOAD0)), ("date", "<=", pd.Timestamp(LOAD1))]
    s = pq.read_table(f"{SH}/stocks.parquet", columns=["ticker", "date", "open", "high", "low", "close", "volume", "closeadj", "closeunadj"], filters=flt).to_pandas()
    s = s[s["ticker"].isin(set(tk["ticker"]))]
    s["date"] = pd.to_datetime(s["date"])
    s = s.drop_duplicates(["ticker", "date"], keep="last")
    dates = pd.DatetimeIndex(sorted(s["date"].unique())); tick = pd.Index(sorted(s["ticker"].unique()))
    M = {c: s.pivot(index="date", columns="ticker", values=c).reindex(index=dates, columns=tick).astype("float32")
         for c in ["open", "high", "low", "close", "volume", "closeadj", "closeunadj"]}
    del s
    adv = (M["close"] * M["volume"]).rolling(20, min_periods=15).median()
    keep = ((M["closeunadj"] >= 5) & (adv >= 5e6)).any()
    M = {c: v.loc[:, keep] for c, v in M.items()}
    tick = tick[keep.values]
    return dates, tick, M


def build(dates, M):
    raw, cl = M["closeunadj"], M["close"]
    f = M["closeadj"] / cl
    C = M["closeadj"]; O = M["open"] * f; H = M["high"] * f; L = M["low"] * f
    V = (M["volume"] / f).astype("float32")
    printed = cl.notna()
    dvol = cl * M["volume"]
    adv = dvol.rolling(20, min_periods=15).median()
    elig = printed & (raw >= 5) & (adv >= 5e6)
    r = C.pct_change(fill_method=None)
    lr = np.log(C).diff()
    Cp = C.shift(1)
    sig = np.where(dates >= pd.Timestamp(SIG0))[0][::5]
    X = {}
    def put(name, df):
        X[name] = df.iloc[sig].astype("float32").values
    roll = lambda d, n: d.rolling(n, min_periods=int(n * 0.75))
    # ---- volatility ----
    rng = lambda n: (H.rolling(n, min_periods=int(n * .75)).max() - L.rolling(n, min_periods=int(n * .75)).min()) / C
    r5, r20, r60 = rng(5), rng(20), rng(60)
    put("vcp", (r5 / r20) * (r20 / r60))
    tr = np.fmax(np.fmax(H - L, (H - Cp).abs()), (L - Cp).abs())
    atr20 = roll(tr, 20).mean()
    ttm = (4 * roll(C, 20).std()) / (3 * atr20)
    put("ttm_ratio", ttm)
    sq = (ttm < 1).astype("float32").where(ttm.notna())
    put("ttm_days", roll(sq, 20).sum())
    vol20 = roll(r, 20).std()
    # HVP: share of own last 252 vol20 values <= today (signal rows only)
    v20 = vol20.values
    hvp = np.full((len(sig), v20.shape[1]), np.nan, dtype="float32")
    for k, i in enumerate(sig):
        if i < 252: continue
        w = v20[i - 251:i + 1]; cur = v20[i]
        hvp[k] = np.where(np.isfinite(cur), (w <= cur).sum(0) / np.maximum(np.isfinite(w).sum(0), 1), np.nan)
    X["hvp"] = hvp
    hl = np.log(H / L); co = np.log(C / O); ho, lo_, hc, lc = np.log(H / O), np.log(L / O), np.log(H / C), np.log(L / C)
    oc = np.log(O / Cp)
    park = np.sqrt(roll(hl ** 2, 20).mean() / (4 * np.log(2)))
    gk = np.sqrt((roll(0.5 * hl ** 2 - (2 * np.log(2) - 1) * co ** 2, 20).mean()).clip(lower=0))
    rsv = roll(hc * ho + lc * lo_, 20).mean().clip(lower=0)
    k = 0.34 / (1.34 + 21 / 19)
    yz = np.sqrt((roll(oc, 20).var() + k * roll(co, 20).var() + (1 - k) * rsv).clip(lower=0))
    for nm, est in (("park_r", park), ("gk_r", gk), ("rs_r", np.sqrt(rsv)), ("yz_r", yz)):
        put(nm, est / roll(est, 252).mean())
    del park, gk, rsv, yz, ho, lo_, hc, lc, oc
    hh14, ll14 = roll(H, 14).max(), roll(L, 14).min()
    put("chop14", 100 * np.log10(roll(tr, 14).sum() / (hh14 - ll14).where(hh14 > ll14)) / np.log10(14))
    put("ulcer14", np.sqrt(roll((100 * (C / roll(C, 14).max() - 1)) ** 2, 14).mean()))
    hh20, ll20 = roll(H, 20).max(), roll(L, 20).min()
    put("donch_w", (hh20 - ll20) / C)
    # FDI (Sevcik, 30) and trend t-stat (60), permutation entropy are window computations at signal rows
    Cv = C.values; lCv = np.log(Cv)
    fdi = np.full((len(sig), Cv.shape[1]), np.nan, dtype="float32"); tt = fdi.copy()
    n1 = 30; x60 = np.arange(60, dtype="float64"); x60c = x60 - x60.mean(); sxx = (x60c ** 2).sum()
    for kk, i in enumerate(sig):
        if i < 60: continue
        w = Cv[i - n1 + 1:i + 1].astype("float64")
        mn, mx = np.nanmin(w, 0), np.nanmax(w, 0)
        y = (w - mn) / np.where(mx > mn, mx - mn, np.nan)
        Ls = np.sqrt(np.diff(y, axis=0) ** 2 + (1 / (n1 - 1)) ** 2).sum(0)
        fdi[kk] = 1 + (np.log(Ls) + np.log(2)) / np.log(2 * (n1 - 1))
        yy = lCv[i - 59:i + 1].astype("float64")
        ybar = yy.mean(0); b = (x60c[:, None] * (yy - ybar)).sum(0) / sxx
        res = yy - ybar - b * x60c[:, None]
        se = np.sqrt((res ** 2).sum(0) / 58 / sxx)
        tt[kk] = b / np.where(se > 0, se, np.nan)
    X["fdi30"] = fdi; X["trend_t"] = tt
    lr8 = lr.rolling(8, min_periods=8).sum()
    put("hurst", np.log(roll(lr8, 120).var() / roll(lr, 120).var()) / (2 * np.log(8)))
    # ---- volume ----
    rngHL = (H - L).where(H > L)
    mfm = ((C - L) - (H - C)) / rngHL
    put("cmf20", roll(mfm * V, 20).sum() / roll(V, 20).sum())
    hlc = (H + L + C) / 3
    vf = V * np.sign(hlc.diff())
    avgv20 = roll(V, 20).mean(); avgv55 = roll(V, 55).mean()
    put("klinger", (vf.ewm(span=34, min_periods=30).mean() - vf.ewm(span=55, min_periods=45).mean()) / avgv55)
    rr = r.fillna(0)
    nvi = np.exp(np.log1p(rr.where(V < V.shift(1), 0)).cumsum())
    pvi = np.exp(np.log1p(rr.where(V > V.shift(1), 0)).cumsum())
    put("nvi_tr", nvi / nvi.ewm(span=255, min_periods=200).mean() - 1)
    put("pvi_tr", pvi / pvi.ewm(span=255, min_periods=200).mean() - 1)
    del nvi, pvi
    mid = (H + L) / 2
    emv = (mid.diff() / C) * rngHL / C / (V / avgv20)
    put("emv14", roll(emv.replace([np.inf, -np.inf], np.nan), 14).mean())
    put("vpt_sl", roll(V * r, 20).sum() / roll(V, 20).sum())
    trh = np.fmax(H, Cp); trl = np.fmin(L, Cp)
    ad = V * ((C - trl) - (trh - C)) / (trh - trl).where(trh > trl)
    put("twiggs21", ad.ewm(alpha=1 / 21, min_periods=15).mean() / V.ewm(alpha=1 / 21, min_periods=15).mean())
    dv_adj = C * V
    put("force13", (r * dv_adj).ewm(span=13, min_periods=10).mean() / roll(dv_adj, 20).mean())
    put("vwap50", C / (roll(hlc * V, 50).sum() / roll(V, 50).sum()) - 1)
    # anchored VWAP at the 252d-high date (signal rows)
    pv = (hlc * V).fillna(0).values.astype("float64"); vv = V.fillna(0).values.astype("float64")
    CPV, CV = np.cumsum(pv, 0), np.cumsum(vv, 0)
    av = np.full((len(sig), Cv.shape[1]), np.nan, dtype="float32")
    cols = np.arange(Cv.shape[1])
    for kk, i in enumerate(sig):
        if i < 252: continue
        w = np.where(np.isfinite(Cv[i - 251:i + 1]), Cv[i - 251:i + 1], -np.inf)
        a = i - 251 + w.argmax(0)
        num = CPV[i] - CPV[a - 1, cols]; den = CV[i] - CV[a - 1, cols]
        av[kk] = Cv[i] / np.where(den > 0, num / den, np.nan) - 1
    X["avwap_hi"] = av
    del CPV, CV, pv, vv
    vdown = V.where(r < 0).rolling(10, min_periods=1).max().shift(1).fillna(0)
    pocket = ((r > 0) & (V > vdown) & (C > roll(C, 10).mean()) & (C > roll(C, 50).mean())).astype("float32").where(C.notna())
    put("pocket", pocket)
    avgv50 = roll(V, 50).mean()
    put("vdu", roll(V, 5).mean() / avgv50)
    put("udvr50", roll(V.where(r > 0, 0), 50).sum() / roll(V.where(r < 0, 0), 50).sum())
    rvol = V / avgv20.shift(1)
    put("rvol", rvol)
    # ---- statistical ----
    x = np.log(C) - np.log(roll(C, 20).mean()); xl = x.shift(1)
    b = (roll(x * xl, 60).mean() - roll(x, 60).mean() * roll(xl, 60).mean()) / roll(xl, 60).var(ddof=0)
    put("ou_hl", (-np.log(2) / np.log(b.where((b > 0) & (b < 1)))).fillna(1e3))
    lr5 = lr.rolling(5, min_periods=5).sum()
    put("vr5", roll(lr5, 120).var() / (5 * roll(lr, 120).var()))
    ret5 = C / C.shift(5) - 1
    put("z5", (ret5 - roll(ret5, 252).mean()) / roll(ret5, 252).std())
    m = r.where(elig).mean(1)
    def beta(n):
        cov = roll(r.mul(m, axis=0), n).mean() - roll(r, n).mean().mul(m.rolling(n, min_periods=int(n * .75)).mean(), axis=0)
        return cov.div(m.rolling(n, min_periods=int(n * .75)).var(ddof=0), axis=0)
    b250, b60 = beta(250), beta(60)
    res = r - b250.shift(1).mul(m, axis=0)
    rs_sum = res.shift(21).rolling(231, min_periods=170).sum()
    put("resmom", rs_sum / (res.shift(21).rolling(231, min_periods=170).std() * np.sqrt(231)))
    put("ivol60", np.sqrt((roll(r, 60).var() - b60 ** 2 * m.rolling(60, min_periods=45).var().values[:, None]).clip(lower=0)))
    put("beta_inst", b60 - b250)
    put("cusum", (roll(r, 20).mean() - roll(r, 120).mean()) / roll(r, 120).std() * np.sqrt(20))
    pu = roll((r > 0).astype("float32").where(r.notna()), 20).mean().clip(1e-6, 1 - 1e-6)
    put("ent20", -(pu * np.log(pu) + (1 - pu) * np.log(1 - pu)))
    # permutation entropy order 3 over 60 days
    c0, c1, c2 = C.shift(2), C.shift(1), C
    pats = [(c0 < c1) & (c1 < c2), (c0 < c2) & (c2 <= c1), (c2 <= c0) & (c0 < c1),
            (c1 <= c0) & (c0 < c2), (c1 < c2) & (c2 <= c0), (c2 <= c1) & (c1 <= c0)]
    cnts = [roll(p_.astype("float32").where(C.notna() & c0.notna()), 58).sum() for p_ in pats]
    tot = sum(cnts)
    pe = -sum((c_ / tot) * np.log((c_ / tot).where(c_ > 0, 1)) for c_ in cnts) / np.log(6)
    put("pent60", pe)
    del cnts, pats, c0, c1, c2
    put("ac60", r.rolling(60, min_periods=45).corr(r.shift(1)))
    put("amihud20", np.log(roll(r.abs() / dvol, 20).mean() * 1e9))
    dC = C.diff()
    put("roll60", 2 * np.sqrt((-(roll(dC * dC.shift(1), 60).mean() - roll(dC, 60).mean() * roll(dC.shift(1), 60).mean())).clip(lower=0)) / C)
    # ---- combo helpers ----
    Hp = {}
    Hp["ret120"] = (C / C.shift(120) - 1).iloc[sig].values
    Hp["vdu_prev10"] = (roll(V, 10).mean().shift(1) / avgv50).iloc[sig].values
    Hp["rvol"] = X["rvol"]
    Hp["up"] = (r > 0).iloc[sig].values
    Hp["sq_prev6"] = (roll(sq, 6).sum().shift(1)).iloc[sig].values
    Hp["sq_now"] = sq.iloc[sig].values
    Hp["hi20_prev"] = (C > C.rolling(20, min_periods=15).max().shift(1)).iloc[sig].values
    # ---- forward returns from signal rows ----
    oadj = O.where(O.notna(), C.ffill()).ffill().values
    R = {}
    nD = len(dates)
    for h in HZ:
        a = np.full((len(sig), Cv.shape[1]), np.nan, dtype="float32")
        okr = sig + 1 + h < nD
        i_in, i_out = sig[okr] + 1, sig[okr] + 1 + h
        v = oadj[i_out] / oadj[i_in] - 1
        v[(v > 3) | (v < -0.99)] = np.nan
        a[okr] = v
        R[h] = a
    E = elig.iloc[sig].values
    # entry must have printed at t+1 (else no fill): require an open print at t+1
    ent_ok = np.zeros_like(E)
    okk = sig + 1 < nD
    ent_ok[okk] = O.notna().values[sig[okk] + 1]
    E = E & ent_ok
    return dates[sig], E, X, Hp, R


def pct(x, E):
    v = pd.DataFrame(np.where(E, x, np.nan)).replace([np.inf, -np.inf], np.nan)
    return v.rank(axis=1, pct=True).values.astype("float32")


def series(mask, R, E, h, sd):
    """net excess per (non-overlapping) signal date; returns pd.Series indexed by date."""
    step = int(np.ceil(h / 5))
    Rh = R[h]
    okU = E & np.isfinite(Rh)
    U = np.where(okU, Rh, 0).sum(1) / np.maximum(okU.sum(1), 1)
    ok = mask & okU
    cnt = ok.sum(1)
    sm = np.where(ok, Rh, 0).sum(1)
    idx = np.where(cnt >= 3)[0]
    idx = idx[::step]
    net = sm[idx] / cnt[idx] - U[idx] - COST
    raw_ = sm[idx] / cnt[idx]
    return pd.Series(net, index=sd[idx]), pd.Series(raw_, index=sd[idx]), pd.Series(cnt[idx], index=sd[idx])


def stats(s, half):
    n = len(s)
    if n < 30:
        return dict(n=n, mean=np.nan, t=np.nan, med=np.nan, h1=np.nan, h2=np.nan, ex5=np.nan)
    mu, sd = s.mean(), s.std(ddof=1)
    return dict(n=n, mean=mu * 1e4, t=mu / sd * np.sqrt(n) if sd > 0 else 0, med=s.median() * 1e4,
                h1=s[s.index < half].mean() * 1e4, h2=s[s.index >= half].mean() * 1e4,
                ex5=s.sort_values().iloc[:-5].mean() * 1e4)


def era(s, a, b):
    return s[(s.index >= a) & (s.index <= b)]


def main():
    t0 = time.time()
    dates, tick, M = load()
    print("loaded", len(dates), len(tick), f"{time.time()-t0:.0f}s", flush=True)
    sd, E, X, Hp, R = build(dates, M)
    del M
    print("built", len(sd), "signal rows", len(X), "features", f"{time.time()-t0:.0f}s", flush=True)
    FE = list(X)
    P = {f: pct(X[f], E) for f in FE}
    L = [f"IND-SWING (pre-reg round1_prose.md). {len(FE)} features, {len(sd)} weekly signal rows {sd[0].date()}..{sd[-1].date()}",
         f"universe mean names/signal date: " + ", ".join(f"{y}:{int(v)}" for y, v in pd.Series(E.sum(1), index=sd).groupby(sd.year).mean().items())]
    # sanity: known reversal sign (ret5 bottom 2% vs universe, 5d gross)
    rows = []
    def cell(kind, name, mask, h):
        net, raw_, cnt = series(mask, R, E, h, sd)
        d = era(net, *DISC); j = era(net, *JUDG)
        sd_ = stats(d, pd.Timestamp(DHALF)); sj = stats(j, pd.Timestamp(JHALF))
        jr = era(raw_, *JUDG)
        dpass = bool(sd_["n"] >= 30 and sd_["mean"] > 0 and sd_["t"] >= 3 and sd_["h1"] > 0 and sd_["h2"] > 0 and sd_["med"] > 0)
        j3 = (j - 2 * COST)
        jpass = bool(sj["n"] >= 30 and sj["mean"] > 0 and sj["t"] >= 2 and sj["med"] > 0 and sj["ex5"] > 0 and sj["h1"] > 0 and sj["h2"] > 0)
        rows.append(dict(kind=kind, name=name, h=h, **{f"d_{k}": v for k, v in sd_.items()}, **{f"j_{k}": v for k, v in sj.items()},
                         j_raw=jr.mean() * 1e4 if len(jr) else np.nan, j3=j3.mean() * 1e4 if len(j3) else np.nan,
                         names=float(era(cnt, *JUDG).mean()) if len(j) else np.nan, dpass=dpass, jpass=jpass,
                         dsr=dsr(j, n_trials=NTRIALS + 600)["dsr"] if len(j) > 30 else np.nan))
    for f in FE:
        tails = [("top", P[f] > 1 - TAIL)] if f == "pocket" else [("top", P[f] > 1 - TAIL), ("bot", P[f] <= TAIL)]
        if f == "pocket":
            tails = [("flag", np.nan_to_num(X[f]) == 1)]
        for side, msk in tails:
            for h in HZ:
                cell("tail", f"{f} {side}", msk & E, h)
    print("tails done", f"{time.time()-t0:.0f}s", flush=True)
    pr = lambda a: pct(a, E)
    ret120p = pr(Hp["ret120"]); vdup = pr(Hp["vdu_prev10"])
    rv = np.nan_to_num(Hp["rvol"]); up = Hp["up"]
    combos = {
        "C1 RS + dry-up + volume expansion": (ret120p >= .8) & (vdup <= .2) & (rv >= 2) & up,
        "C2 VCP + pocket pivot": (P["vcp"] <= .1) & (np.nan_to_num(X["pocket"]) == 1),
        "C3 TTM squeeze fires up": (np.nan_to_num(Hp["sq_prev6"]) >= 5) & (Hp["sq_now"] == 0) & Hp["hi20_prev"],
        "C4 Donchian squeeze breakout": (P["donch_w"] <= .1) & Hp["hi20_prev"] & (rv >= 1.5),
        "C5 accumulation + RS": (P["cmf20"] >= .9) & (P["udvr50"] >= .9) & (ret120p >= .8),
    }
    for nm, msk in combos.items():
        for h in HZ:
            cell("combo", nm, msk & E, h)
    print("combos done", f"{time.time()-t0:.0f}s", flush=True)
    # ---- ML composite ----
    from sklearn.ensemble import HistGradientBoostingRegressor
    F3 = np.stack([P[f] for f in FE], axis=-1)  # rows x names x feats
    tgt = pct(R[10] - np.nanmean(np.where(E, R[10], np.nan), axis=1, keepdims=True), E & np.isfinite(R[10]))
    pred = np.full(E.shape, np.nan, dtype="float32")
    years = range(2009, 2027)
    imp = None
    for y in years:
        te = (sd.year == y)
        tr_end = np.where(sd < pd.Timestamp(f"{y}-01-01"))[0]
        if not len(tr_end): continue
        last = tr_end[-1] - 6  # 6 weekly rows = 30 sessions embargo
        tr = (sd >= pd.Timestamp(f"{y-5}-01-01")) & (np.arange(len(sd)) <= last)
        ri, ci = np.where(E[tr] & np.isfinite(tgt[tr]))
        rows_tr = np.where(tr)[0][ri]
        Xtr = F3[rows_tr, ci]; ytr = tgt[rows_tr, ci]
        if len(ytr) > 400_000:
            sel = np.random.default_rng(y).choice(len(ytr), 400_000, replace=False); Xtr, ytr = Xtr[sel], ytr[sel]
        mdl = HistGradientBoostingRegressor(max_iter=200, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=200, random_state=0)
        mdl.fit(Xtr, ytr)
        tri = np.where(te)[0]
        for i in tri:
            c = np.where(E[i])[0]
            if len(c): pred[i, c] = mdl.predict(F3[i, c])
        print("ml", y, len(ytr), f"{time.time()-t0:.0f}s", flush=True)
    mlp = pct(pred, E & np.isfinite(pred))
    for h in HZ:
        cell("ml", "ML top 1%", (mlp > 0.99) & E, h)
    D = pd.DataFrame(rows)
    D.to_parquet("data/research/program/ind_swing_cells.parquet")
    # ---- permutation null (tails) ----
    rng = np.random.default_rng(20261015)
    nulls = []
    tail_rows = D[D.kind == "tail"]
    for rep in range(5):
        npass = 0
        for f in FE:
            valid = np.isfinite(P[f]) if f != "pocket" else E
            base = [(np.nan_to_num(X[f]) == 1) & E] if f == "pocket" else [(P[f] > 1 - TAIL) & E, (P[f] <= TAIL) & E]
            for msk in base:
                keys = np.where(valid, rng.random(valid.shape, dtype="float32"), 2.0)
                k_ = msk.sum(1)
                thr = np.take_along_axis(np.sort(keys, 1), np.clip(k_ - 1, 0, None)[:, None], 1)
                rnd = (keys <= thr) & valid & (k_[:, None] > 0)
                for h in HZ:
                    net, _, _ = series(rnd, R, E, h, sd)
                    s_ = stats(era(net, *DISC), pd.Timestamp(DHALF))
                    npass += bool(s_["n"] >= 30 and s_["mean"] > 0 and s_["t"] >= 3 and s_["h1"] > 0 and s_["h2"] > 0 and s_["med"] > 0)
        nulls.append(npass)
        print("null", rep, npass, f"{time.time()-t0:.0f}s", flush=True)
    real = int(tail_rows.dpass.sum())
    batch_ok = real > max(nulls) and real > 3 * np.mean(nulls)
    L.append(f"TAILS: {len(tail_rows)} cells; discovery passes REAL {real}; NULL (random same-size picks) {nulls}; "
             f"batch {'COUNTS' if batch_ok else 'LUCK'}")
    fmt = lambda r: (f"{r['kind']:5s} {r['name']:36s} h={r['h']:<2} | DISC n={r.d_n:<3} net={r.d_mean:+7.1f} t={r.d_t:+5.2f} med={r.d_med:+6.1f} "
                     f"h1={r.d_h1:+6.1f} h2={r.d_h2:+6.1f} | JUDGE n={r.j_n:<3} net={r.j_mean:+7.1f} t={r.j_t:+5.2f} med={r.j_med:+6.1f} "
                     f"ex5={r.j_ex5:+6.1f} h1={r.j_h1:+6.1f} h2={r.j_h2:+6.1f} raw={r.j_raw:+6.1f} 3x={r.j3:+6.1f} names={r.names:5.1f} dsr={r.dsr:.2f}"
                     f"{'  DPASS' if r.dpass else ''}{'  JPASS' if r.jpass else ''}")
    L.append("\nDiscovery passes (tails), judged once:")
    for _, r in tail_rows[tail_rows.dpass].sort_values("d_t", ascending=False).iterrows():
        L.append("  " + fmt(r))
    L.append("\nCombos and ML (judged regardless):")
    for _, r in D[D.kind != "tail"].iterrows():
        L.append("  " + fmt(r))
    L.append("\nTop 15 tail cells by JUDGE t (descriptive; only DPASS rows are eligible):")
    for _, r in tail_rows.sort_values("j_t", ascending=False).head(15).iterrows():
        L.append("  " + fmt(r))
    jp = D[D.jpass & ((D.kind != "tail") | D.dpass)]
    L.append(f"\nJUDGED PASSES (eligible): {len(jp)}; robust at 3x cost: {int((jp.j3 > 0).sum())}")
    for _, r in jp.iterrows():
        L.append("  " + fmt(r))
    L.append(f"runtime {time.time()-t0:.0f}s")
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
