"""CEF-ML (N 1205-1207): does a learned model (Ridge, shallow GBM) rank CEF-RV candidates better than depth?

Pre-registration: round1_prose.md "PRE-REGISTRATION - CEF-ML". Trades = the frozen CEF-RV rule on the Nasdaq NAV panel
(CEF-STRESS output cef_stress_trades.csv; live funds only). Label exc = net (50bp) - EW CEF incl. delisted, same hold.
Walk-forward annual refits 2016..2026, purged (training exits < Jan 1 of the ranked year). Needs scikit-learn.

    PYTHONPATH=. python research/sim/cef_ml.py     # -> data/research/program/cef_ml_out.txt
"""
from __future__ import annotations

import math
import pathlib
import warnings

import numpy as np
import pandas as pd
import scipy.stats as SS
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import LogisticRegression

from research.sim.cef_peer import category
from research.sim.cef_rv import STORE

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[2]
CEF = ROOT / "data/research/cefconnect"
OUT = ROOT / "data/research/program/cef_ml_out.txt"
COST = 0.005
N_TRIALS = 1207
SURV_GAP = 0.0186          # CEF-SURV99 live-minus-dead alpha gap per trade
FIT_END = pd.Timestamp("2016-01-01")
lines: list[str] = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    lines.append(s)


# ---------------------------------------------------------------- data
def weekly_panel() -> pd.DataFrame:
    """Same construction as cef_stress.weekly_panel (Friday NAV rows, SFP closeunadj price, frozen error screen)."""
    d = pd.read_parquet(CEF / "nasdaq_daily.parquet")
    d = d[d.date.dt.weekday == 4]
    tk = sorted(d.ticker.unique())
    f = pd.read_parquet(STORE / "funds.parquet", columns=["ticker", "date", "closeunadj"], filters=[("ticker", "in", tk)])
    f["date"] = pd.to_datetime(f["date"]); f = f.drop_duplicates(["ticker", "date"])
    d = d.merge(f, on=["ticker", "date"], how="left")
    d["price"] = d.closeunadj.fillna(d.px_nasdaq)
    d["disc"] = d.price / d.nav - 1
    d.loc[(d.disc < -0.6) | (d.disc > 1.0), "disc"] = np.nan
    return d.dropna(subset=["disc"])[["ticker", "date", "disc", "nav", "price"]].sort_values(["ticker", "date"])


def fred(path: str, col: str) -> pd.Series:
    s = pd.read_csv(ROOT / path)
    s["observation_date"] = pd.to_datetime(s["observation_date"])
    return pd.to_numeric(s.set_index("observation_date")[col], errors="coerce").dropna().sort_index()


def asof(s: pd.Series, dates) -> np.ndarray:
    return s.reindex(pd.DatetimeIndex(dates), method="ffill").to_numpy()


def features(tr: pd.DataFrame) -> pd.DataFrame:
    p = weekly_panel()
    rows = []
    for t, g in p.groupby("ticker"):
        g = g.reset_index(drop=True)
        d, nav = g.disc.to_numpy(), g.nav.to_numpy()
        lnav = np.log(np.where(nav > 0, nav, np.nan))
        idx = {pd.Timestamp(x): i for i, x in enumerate(g.date)}
        for ed in tr.loc[tr.ticker == t, "edate"]:
            i = idx.get(pd.Timestamp(ed))
            if i is None or i < 52:
                rows.append(dict(ticker=t, edate=ed)); continue
            w = d[i - 51: i + 1]
            sd = np.nanstd(w, ddof=1)
            rows.append(dict(ticker=t, edate=ed, depth=(d[i] - np.nanmedian(w)) * 100,
                             dz=(d[i] - np.nanmean(w)) / sd if sd > 0 else np.nan,
                             gap10=(d[i] - np.nanpercentile(w, 10)) * 100, dlev=d[i] * 100,
                             navvol=np.nanstd(np.diff(lnav[i - 52: i + 1]), ddof=1) * 100,
                             nav13=(nav[i] / nav[i - 13] - 1) * 100))
    F = tr[["ticker", "edate"]].merge(pd.DataFrame(rows).drop_duplicates(["ticker", "edate"]), on=["ticker", "edate"], how="left")

    # SFP: price 13w total return, 20d median $ADV, 52w weekly price vol
    tk = sorted(tr.ticker.unique())
    f = pd.read_parquet(STORE / "funds.parquet", columns=["ticker", "date", "close", "volume", "closeadj", "closeunadj"],
                        filters=[("ticker", "in", tk)])
    f["date"] = pd.to_datetime(f["date"]); f = f.drop_duplicates(["ticker", "date"]).sort_values(["ticker", "date"])
    a = pd.read_parquet(STORE / "actions.parquet", columns=["date", "action", "ticker", "value"])
    a = a[(a.action == "dividend") & a.ticker.isin(tk)].copy(); a["date"] = pd.to_datetime(a["date"])
    out = {}
    for t, g in f.groupby("ticker"):
        dts = g.date.to_numpy("datetime64[ns]"); ca = g.closeadj.to_numpy(); cu = g.closeunadj.to_numpy()
        dv = (g.close * g.volume).to_numpy()
        dvd = a[a.ticker == t].sort_values("date"); ddt = dvd.date.to_numpy("datetime64[ns]"); dval = dvd.value.to_numpy()
        for ed in F.loc[F.ticker == t, "edate"]:
            j = int(np.searchsorted(dts, np.datetime64(ed, "ns"), side="right")) - 1
            if j < 260:
                continue
            e64 = np.datetime64(ed, "ns")
            m = (ddt > e64 - np.timedelta64(365, "D")) & (ddt <= e64)
            last = ddt[ddt <= e64]
            cut = 0.0
            k = np.where((ddt >= e64 - np.timedelta64(42, "D")) & (ddt <= e64))[0]
            for q in k:
                if q >= 3:
                    pr = dval[q - 3: q]
                    if pr.max() / max(pr.min(), 1e-9) - 1 <= 0.02 and dval[q] <= 0.9 * np.median(pr):
                        cut = 1.0
            wk = ca[j - 255: j + 1: 5]
            out[(t, pd.Timestamp(ed))] = dict(
                px13=(ca[j] / ca[j - 63] - 1) * 100, ladv=np.log(max(np.median(dv[j - 19: j + 1]), 1.0)),
                pxvol=np.std(np.diff(np.log(wk)), ddof=1) * 100,
                yld=dval[m].sum() / cu[j] * 100 if cu[j] > 0 else np.nan, cut42=cut,
                dsx=float((e64 - last[-1]) / np.timedelta64(1, "D")) if len(last) else np.nan)
    G = pd.DataFrame([dict(ticker=k[0], edate=k[1], **v) for k, v in out.items()])
    F = F.merge(G, on=["ticker", "edate"], how="left")

    names = pd.read_parquet(STORE / "tickers.parquet", columns=["ticker", "name", "table", "category"])
    names = names[(names.table == "SFP")].drop_duplicates("ticker", keep="last").set_index("ticker")["name"]
    F["cat"] = [category(names.get(t, "")) for t in F.ticker]
    vix = fred("data/research/oil_shock/VIXCLS.csv", "VIXCLS")
    baa = fred("data/research/regime_x/BAA10Y.csv", "BAA10Y")
    tb = fred("data/research/regime_x/DTB3.csv", "DTB3")
    e = pd.DatetimeIndex(F.edate)
    F["vix"] = asof(vix, e)
    F["baa13"] = asof(baa, e) - asof(baa, e - pd.Timedelta(weeks=13))
    F["tb13"] = asof(tb, e) - asof(tb, e - pd.Timedelta(weeks=13))
    return F


NUM = ["depth", "dz", "gap10", "dlev", "yld", "cut42", "dsx", "navvol", "nav13", "px13", "ladv", "vix", "baa13", "tb13",
       "dd", "widen", "taxs", "nsig"]
CATS = ["muni", "pref_conv", "sector", "taxable_fi", "intl"]   # equity = base


def design(D: pd.DataFrame) -> pd.DataFrame:
    X = D[NUM].astype(float).copy()
    for c in CATS:
        X["c_" + c] = (D["cat"] == c).astype(float)
    return X


# ---------------------------------------------------------------- stats
def nw_t(x: np.ndarray, lags: int = 8) -> float:
    x = np.asarray(x, float); n = len(x); m = x.mean(); e = x - m
    v = (e @ e) / n
    for L in range(1, lags + 1):
        v += 2 * (1 - L / (lags + 1)) * (e[L:] @ e[:-L]) / n
    return m / math.sqrt(v / n) if v > 0 else float("nan")


def dsr(x, n_trials):
    x = np.asarray(x, float); x = x[~np.isnan(x)]; T = len(x)
    sr = x.mean() / x.std(ddof=1); sk = SS.skew(x); ku = SS.kurtosis(x, fisher=False); g = 0.5772156649
    sr0 = math.sqrt(1.0 / T) * ((1 - g) * SS.norm.ppf(1 - 1 / n_trials) + g * SS.norm.ppf(1 - 1 / (n_trials * math.e)))
    z = (sr - sr0) * math.sqrt(T - 1) / math.sqrt(max(1e-12, 1 - sk * sr + (ku - 1) / 4 * sr ** 2))
    return float(SS.norm.cdf(z))


def ridge_fit(X: np.ndarray, y: np.ndarray, lam: float):
    mu, sd = X.mean(0), X.std(0); sd[sd == 0] = 1
    Z = (X - mu) / sd; ym = y.mean()
    b = np.linalg.solve(Z.T @ Z + lam * np.eye(Z.shape[1]), Z.T @ (y - ym))
    return lambda Xn: ((Xn - mu) / sd) @ b + ym, b


def ridge_cv(X, y, order, lams=(1, 10, 100, 1000)):
    """Purged time-ordered 4-fold forward CV inside the training set: fold k trains on blocks < k (exit-purged by caller order)."""
    n = len(y); cuts = np.linspace(0, n, 6).astype(int)
    best, bl = -np.inf, lams[-1]
    for lam in lams:
        ics = []
        for k in range(2, 6):
            tr_i, te_i = order[: cuts[k - 1]], order[cuts[k - 1]: cuts[k]]
            if len(tr_i) < 100 or len(te_i) < 30:
                continue
            fn, _ = ridge_fit(X[tr_i], y[tr_i], lam)
            ics.append(SS.spearmanr(fn(X[te_i]), y[te_i])[0])
        if ics and np.mean(ics) > best:
            best, bl = np.mean(ics), lam
    return bl


# ---------------------------------------------------------------- main
def main() -> int:
    tr = pd.read_csv(CEF / "cef_stress_trades.csv", parse_dates=["edate", "xdate"])
    tr = tr[tr.edate >= "2008-01-01"].reset_index(drop=True)
    tr["taxs"] = tr.edate.dt.month.isin([11, 12]).astype(float)
    tr["nsig"] = tr.groupby("edate").ticker.transform("size").astype(float)
    F = features(tr)
    D = pd.concat([tr, F.drop(columns=["ticker", "edate"])], axis=1)
    D["cat"] = D["cat"].fillna("equity")
    miss = D[NUM].isna().mean()
    say("CEF-ML (N 1205-1207). sign convention: exc = net(50bp RT) - EW CEF incl. delisted over the same hold; + = beat the universe;"
        " depth < 0 = cheaper than own 52w median.")
    say(f"trades {len(D)} funds {D.ticker.nunique()} entries {D.edate.min().date()}..{D.edate.max().date()}; "
        f"missing share max {miss.max():.1%} ({miss.idxmax()})")
    assert (D.depth.dropna() <= 0.5).mean() > 0.95, "depth sign: CEF-RV entries are at/below their own median"

    # -------- conditional-edge map, FIT period only
    fit = D[D.edate < FIT_END].copy()
    say(f"\n== Conditional-edge map, entries 2008-2015 only (n {len(fit)}), exc bp: mean / median / n ==")
    say(f"   all: {fit.exc.mean()*1e4:+.0f} / {fit.exc.median()*1e4:+.0f} / {len(fit)}")
    def binrow(lab, key):
        g = fit.groupby(key, observed=True).exc
        s = "  ".join(f"[{k}] {v.mean()*1e4:+.0f}/{v.median()*1e4:+.0f}/{len(v)}" for k, v in g)
        say(f"   {lab:8s} {s}")
    for c in ["depth", "dz", "gap10", "dlev", "yld", "navvol", "nav13", "px13", "ladv", "dsx", "vix", "baa13", "tb13", "dd",
              "widen", "nsig"]:
        q = pd.qcut(fit[c], 5, labels=False, duplicates="drop")
        edges = fit[c].quantile([0, .2, .4, .6, .8, 1]).round(2).tolist()
        binrow(c, q); say(f"            quintile edges {edges}")
    binrow("cat", fit["cat"]); binrow("cut42", fit["cut42"]); binrow("month", fit.edate.dt.month)

    # -------- walk-forward ladder
    X_all = design(D).to_numpy(float); y_all = D.exc.clip(-1, 1).to_numpy(float)
    D["s_r1"] = -D.depth          # rung 1: deeper = higher score
    D["s_r2"] = np.nan; D["s_r4"] = np.nan
    coefs = {}
    for Y in range(2016, 2027):
        cut = pd.Timestamp(f"{Y}-01-01")
        trn = (D.xdate < cut).to_numpy()
        te = (D.edate.dt.year == Y).to_numpy()
        if te.sum() == 0:
            continue
        Xt = X_all[trn].copy(); med = np.nanmedian(Xt, 0)
        Xt = np.where(np.isnan(Xt), med, Xt); Xe = np.where(np.isnan(X_all[te]), med, X_all[te])
        yt = y_all[trn]; lo, hi = np.percentile(yt, [1, 99]); yt = np.clip(yt, lo, hi)
        order = np.argsort(D.edate.to_numpy()[trn], kind="stable")
        lam = ridge_cv(Xt, yt, order)
        fn, b = ridge_fit(Xt, yt, lam)
        D.loc[te, "s_r2"] = fn(Xe)
        gbm = GradientBoostingRegressor(loss="huber", max_depth=2, n_estimators=150, learning_rate=0.03, subsample=0.7,
                                        min_samples_leaf=50, random_state=1205).fit(Xt, yt)
        D.loc[te, "s_r4"] = gbm.predict(Xe)
        coefs[Y] = (lam, b, gbm.feature_importances_, int(trn.sum()))
    cols = list(design(D).columns)
    for Y in (2016, 2026):
        lam, b, imp, n = coefs[Y]
        top = np.argsort(-np.abs(b))[:8]
        say(f"\nRidge {Y} (train n {n}, lambda {lam}): " + ", ".join(f"{cols[i]} {b[i]*1e4:+.0f}" for i in top) + " (bp per sd)")
        ti = np.argsort(-imp)[:8]
        say(f"GBM   {Y} importance: " + ", ".join(f"{cols[i]} {imp[i]:.2f}" for i in ti))

    J = D[D.edate >= FIT_END].copy()
    J["wk"] = J.edate
    say(f"\n== JUDGE walk-forward 2016..2026: {len(J)} trades, {J.wk.nunique()} signal weeks; "
        f"weeks with >= 3 signals: {(J.groupby('wk').size() >= 3).sum()} ==")
    ics = {r: [] for r in ("s_r1", "s_r2", "s_r4")}
    picks: dict[str, list] = {r: [] for r in ("s_r1", "s_r2", "s_r4")}
    wkrow = []
    for w, g in J.groupby("wk"):
        if len(g) < 3:
            continue
        k = math.ceil(len(g) / 3)
        row = dict(wk=w, n=len(g), all=g.exc.mean())
        for r in ics:
            ics[r].append(SS.spearmanr(g[r], g.exc)[0])
            top = g.nlargest(k, r)
            picks[r].append(top)
            row[r] = top.exc.mean()
        wkrow.append(row)
    W = pd.DataFrame(wkrow).sort_values("wk").reset_index(drop=True)
    for r in ics:
        P = pd.concat(picks[r])
        say(f"  {r}: picked n {len(P)} exc mean {P.exc.mean()*1e4:+.0f}bp med {P.exc.median()*1e4:+.0f} | weekly-mean {W[r].mean()*1e4:+.0f} "
            f"| at 2x cost {(P.exc.mean()-COST)*1e4:+.0f} 3x {(P.exc.mean()-2*COST)*1e4:+.0f} | mean IC {np.nanmean(ics[r]):+.3f} "
            f"(t {np.nanmean(ics[r])/(np.nanstd(ics[r],ddof=1)/math.sqrt(np.sum(~np.isnan(ics[r])))):.2f}) | ladv {P.ladv.mean():.2f} "
            f"yld {P.yld.mean():.1f} cat {P['cat'].value_counts(normalize=True).round(2).to_dict()}")
    say(f"  all-signal weekly mean {W['all'].mean()*1e4:+.0f}bp")

    def gate(lab, a, b, Pa):
        x = (W[a] - W[b]).to_numpy()
        h1 = x[W.wk < "2021-01-01"].mean(); h2 = x[W.wk >= "2021-01-01"].mean()
        o = np.argsort(-x); ex5 = np.delete(x, o[:5]).mean()
        t = nw_t(x); ds = dsr(x, N_TRIALS); c3 = pd.concat(picks[a]).exc.mean() - 2 * COST
        ok = dict(mean=x.mean() > 0, t=t >= 2, halves=h1 > 0 and h2 > 0, ex5=ex5 > 0, cost3=c3 > 0, dsr=ds >= 0.95)
        say(f"  {lab}: delta {x.mean()*1e4:+.1f}bp/trade med {np.median(x)*1e4:+.1f} NW-t {t:.2f} halves {h1*1e4:+.0f}/{h2*1e4:+.0f} "
            f"ex-top5 {ex5*1e4:+.1f} picks@3x {c3*1e4:+.0f} DSR(N {N_TRIALS}) {ds:.3f} hit {np.mean(x>0):.0%} -> "
            f"{'PASS' if all(ok.values()) else 'FAIL'} " + " ".join(f"{k}={'Y' if v else 'n'}" for k, v in ok.items()))
        return x
    say("\nGATES (weekly top-third delta, weeks >= 3 signals):")
    d21 = gate("N 1205 Ridge vs depth", "s_r2", "s_r1", None)
    d42 = gate("N 1206 GBM vs Ridge  ", "s_r4", "s_r2", None)
    gate("     GBM vs depth (report)", "s_r4", "s_r1", None)
    for y, g in W.groupby(W.wk.dt.year):
        say(f"    {y}: weeks {len(g)} depth {g.s_r1.mean()*1e4:+.0f} ridge {g.s_r2.mean()*1e4:+.0f} gbm {g.s_r4.mean()*1e4:+.0f} all {g['all'].mean()*1e4:+.0f}")

    # N 1207 filter
    keep = J.s_r2 > 0
    from research.sim.cef_txt import spread_stats
    s = spread_stats(J.exc.to_numpy(), (~keep).to_numpy(), J.edate.dt.strftime("%Y-%m").to_numpy())
    h = [J[(J.edate < "2021-01-01")], J[J.edate >= "2021-01-01"]]
    hh = [g[g.s_r2 > 0].exc.mean() - g[g.s_r2 <= 0].exc.mean() for g in h]
    say(f"\nN 1207 Ridge filter (skip pred < 0): kept {s['n_keep']} dropped {s['n_drop']} | kept-minus-dropped {s['spread']*1e4:+.0f}bp "
        f"t_month {s['t']:.2f} halves {hh[0]*1e4:+.0f}/{hh[1]*1e4:+.0f} | lift vs take-all {s['lift']*1e4:+.0f}bp | kept hit {s['hit_keep']:.0%}")
    mo = J.assign(k=keep, m=J.edate.dt.strftime("%Y-%m"))
    ms = mo.groupby("m").apply(lambda g: g[g.k].exc.mean() - g[~g.k].exc.mean() if g.k.any() and (~g.k).any() else np.nan).dropna()
    kx = J[keep].exc.to_numpy(); o = np.argsort(-kx)
    ex5 = np.delete(kx, o[:5]).mean() - J[~keep].exc.mean()
    say(f"  filter gate parts: ex-top5 kept-minus-dropped {ex5*1e4:+.0f}bp | kept exc at 3x cost {(kx.mean()-2*COST)*1e4:+.0f}bp | "
        f"monthly spread n {len(ms)} mean {ms.mean()*1e4:+.0f} NW-t {nw_t(ms.to_numpy(), 3):.2f} DSR(N {N_TRIALS}) {dsr(ms.to_numpy(), N_TRIALS):.3f}")

    # -------- survivorship hazard bound
    say("\n== Survivorship: death-hazard of each rung's picks (logit on all SFP CEFs incl. delisted, fund-weeks 2008-15) ==")
    tkr = pd.read_parquet(STORE / "tickers.parquet")
    c = tkr[(tkr.table == "SFP") & (tkr.category == "CEF")].drop_duplicates("ticker", keep="last")
    f = pd.read_parquet(STORE / "funds.parquet", columns=["ticker", "date", "close", "volume", "closeadj", "closeunadj"],
                        filters=[("ticker", "in", sorted(c.ticker))])
    f["date"] = pd.to_datetime(f["date"]); f = f.drop_duplicates(["ticker", "date"]).sort_values(["ticker", "date"])
    f = f[f.date >= "2006-06-01"]
    f["dv"] = f.close * f.volume
    f["wk"] = f.date.dt.to_period("W-FRI")
    wk = f.groupby(["ticker", "wk"]).agg(date=("date", "last"), ca=("closeadj", "last"), dv=("dv", "median")).reset_index()
    wk["lr"] = np.log(wk.ca).groupby(wk.ticker).diff()
    wk["pxvol"] = wk.groupby("ticker").lr.transform(lambda s: s.rolling(52, min_periods=40).std()) * 100
    wk["px13"] = wk.groupby("ticker").ca.pct_change(13) * 100
    wk["ladv"] = np.log(wk.groupby("ticker").dv.transform(lambda s: s.rolling(4, min_periods=2).median()).clip(lower=1))
    lpd = pd.to_datetime(c.set_index("ticker").lastpricedate); dl = c.set_index("ticker").isdelisted == "Y"
    wk["dies"] = (wk.ticker.map(dl).fillna(False) & (wk.ticker.map(lpd) <= wk.date + pd.Timedelta(weeks=52))).astype(int)
    nm = c.set_index("ticker").name
    catmap = {t: category(nm.get(t, "")) for t in wk.ticker.unique()}
    wk["cat"] = wk.ticker.map(catmap)
    HZ = ["ladv", "pxvol", "px13"]
    def hx(Dx):
        X = Dx[HZ].astype(float).copy()
        for cc in CATS:
            X["c_" + cc] = (Dx["cat"] == cc).astype(float)
        return X
    hf = wk[(wk.date >= "2008-01-01") & (wk.date < FIT_END)].dropna(subset=HZ)
    Xh = hx(hf).to_numpy(); mu, sd = Xh.mean(0), Xh.std(0); sd[sd == 0] = 1
    lr = LogisticRegression(C=1.0, max_iter=500).fit((Xh - mu) / sd, hf.dies)
    say(f"  fund-weeks {len(hf)}, tickers {hf.ticker.nunique()}, die-within-52w rate {hf.dies.mean():.2%}; coefs " +
        ", ".join(f"{n} {v:+.2f}" for n, v in zip(hx(hf).columns, lr.coef_[0])))
    dead16 = c[(c.isdelisted == "Y") & (pd.to_datetime(c.lastpricedate) >= FIT_END)].shape[0]
    say(f"  SFP CEFs delisted 2016+: {dead16} (absent from the live NAV panel)")
    Jh = J.copy(); Xj = hx(Jh.assign(pxvol=Jh.pxvol)).to_numpy(float)
    Xj = np.where(np.isnan(Xj), mu, Xj)
    Jh["hz"] = lr.predict_proba((Xj - mu) / sd)[:, 1]
    hz = {}
    for r in ("s_r1", "s_r2", "s_r4"):
        P = pd.concat(picks[r]); hz[r] = Jh.loc[P.index, "hz"].mean()
    say("  mean 52w death hazard of picks: " + ", ".join(f"{r} {v:.2%}" for r, v in hz.items()) + f"; all judge trades {Jh.hz.mean():.2%}")
    for lab, a, b, x in (("Ridge vs depth", "s_r2", "s_r1", d21), ("GBM vs Ridge", "s_r4", "s_r2", d42),
                         ("GBM vs depth", "s_r4", "s_r1", (W.s_r4 - W.s_r1).to_numpy())):
        dh = hz[a] - hz[b]
        say(f"  {lab}: delta {x.mean()*1e4:+.1f}bp, hazard diff {dh*100:+.2f}pt -> adj (gap {SURV_GAP*1e4:.0f}bp) "
            f"{(x.mean() - dh * SURV_GAP)*1e4:+.1f}bp; worst case 3x gap {(x.mean() - 3 * dh * SURV_GAP)*1e4:+.1f}bp")

    # -------- slot replay
    say("\n== Slot replay 2016..2026 (live formula; pool = open signals; net of 50bp; %/yr of equity) ==")
    J = J.reset_index(drop=True)
    for eq in (2300, 10000, 25000):
        slot = max(250.0, min(1000.0, eq / 10.0)); room = int(math.floor(0.5 * eq / slot))
        res = {}
        for r in ("s_r1", "s_r2", "s_r4"):
            pool, open_i, taken = [], [], []
            for w in sorted(J.edate.unique()):
                w = pd.Timestamp(w)
                open_i = [i for i in open_i if J.xdate[i] > w]
                pool = [i for i in pool if J.xdate[i] > w] + J.index[J.edate == w].tolist()
                held = {J.ticker[i] for i in open_i}
                cand = [i for i in pool if J.ticker[i] not in held]
                free = room - len(open_i)
                if free > 0 and cand:
                    for i in sorted(cand, key=lambda i: -J.loc[i, r])[:free]:
                        taken.append(i); open_i.append(i); pool.remove(i); held.add(J.ticker[i])
            T = J.loc[taken]
            yr = T.assign(v=T.net * slot).groupby(T.edate.dt.year).v.sum().reindex(range(2016, 2027), fill_value=0)
            yx = T.assign(v=T.exc * slot).groupby(T.edate.dt.year).v.sum().reindex(range(2016, 2027), fill_value=0)
            res[r] = (yr / eq * 100, yx / eq * 100, len(T))
        b = res["s_r1"][0]
        say(f"  ${eq:,} slot ${slot:.0f} room {room}: " + " | ".join(
            f"{r} trades {n} net {v.mean():+.1f}%/yr exc {x.mean():+.1f}%/yr d-vs-depth {(v-b).mean():+.1f}pp (yrs + {(v-b>0).sum()}/11)"
            for r, (v, x, n) in res.items()))
        say(f"      net 3x cost (Ridge): {(res['s_r2'][0] - 2*COST*slot*res['s_r2'][2]/11/eq*100).mean():+.1f}%/yr")
    OUT.write_text("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
