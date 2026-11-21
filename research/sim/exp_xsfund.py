"""EXP round 5 N 1237 XS-FUND: cross-sectional monthly stock selection on 19 price ranks + 16 point-in-time SF1 fundamentals.

Pre-registration: research/drafts/round1_prose.md, "## Amendment - EXP round 5" (N 1236 -> 1239). Same frame, universe, portfolio,
costs, placebo and gates as N 1235 XS-RFF (research/sim/exp_xsrff.py, imported, not copied; its loader is wrapped, not edited),
with the three registered changes: gates judged vs SPY (EW reported), the SF1 features below, and the learner
(HistGradientBoostingRegressor max_depth 3, lr 0.05, 300 iterations, min_samples_leaf 200 = PRIMARY; RFF ridge at N 1235 settings =
second model). Annual expanding refit at each December month-end from 2010-12 with the 21-session purge (N 1235 rule).
Code frozen (sha256 printed in the header) before any judge number was printed.

SF1 (~/data/sharadar/fundamentals.parquet, dimensions ARQ and ART). The file has no `datekey` column: `date` is the filing date
(SF1 `price`/`marketcap` are struck at `date`, median date - reportperiod lag 40-45 days in every year 2001-21 = 10-Q deadlines).
Point in time: a row is usable at decision close t only if date < t (strict; = on or after date + 1 session). Amendments: per
ticker and dimension, rows ordered by filing date; a row whose calendardate is older than a period already filed is dropped (an
old-period amendment never replaces a newer period); a same-period amendment replaces the original from its own filing date.
Stale cap 450 days (modern_xs precedent; registration silent). Year-ago values (growth) = the latest ARQ row of calendardate - 1y
filed on or before the current row's filing date.
Features (raw, then rank-normalised to [-1, 1] per month among names with a finite value; missing = 0):
  value   ep = netinccmnusd(ART)/mcap_t, bp = equityusd(ARQ)/mcap_t, sp = revenueusd(ART)/mcap_t, fcfp = fcf*fxusd(ART)/mcap_t,
          ebitdaev = ebitdausd(ART)/EV_t (EV_t > 0)
  quality roa = netinc/assets (ART), roe = netinc/equity (ART, equity > 0), gpa = gp/assets (ART), accr = (netinc - ncfo)/assets (ART)
  growth  revg = revenue/revenue_ya - 1 (ARQ q vs q-4, ya > 0), epsg = (eps - eps_ya)/|eps_ya| (ARQ, ya != 0), assetg (ARQ)
  finance iss = sharesbas/sharesbas_ya - 1 (ARQ), de = debt/equity (ARQ, equity > 0)
  size    lmcap = log mcap_t;  recency = calendar days from the latest ARQ filing date (< t) to t (no stale cap)
  mcap_t = SF1 marketcap at the filing x close_t / close_f (close = split-adjusted SEP close of the last bar <= filing date, same
  source file as the label, so splits between filing and t cancel; SF1 `price` is itself split-adjusted to the SF1 vintage, 99.5%
  within 1% of SEP close, so it is not mixed with SEP); EV_t = mcap_t + debtusd - cashnequsd (SF1's own EV identity).

    PYTHONPATH=. python3 research/sim/exp_xsfund.py            # -> research/sim/exp_xsfund_out.txt
    XSFUND_DRY=1 ...                                           # small P / ticker subset, prints no judge numbers
"""
from __future__ import annotations

import os

DRY = os.environ.get("XSFUND_DRY") == "1"
if DRY:
    os.environ["XSRFF_DRY"] = "1"
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "3")

import gc  # noqa: E402
import hashlib  # noqa: E402
import pathlib  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402
from sklearn.ensemble import HistGradientBoostingRegressor  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from research.sim import exp_xsrff as X  # noqa: E402
from research.sim.exp_rl_universe import load_etfs  # noqa: E402
from research.sim.weekwin_short import tstat  # noqa: E402
from research.sim.exp_rl import dsr  # noqa: E402

OUT = ROOT / ("research/sim/exp_xsfund_dry.txt" if DRY else "research/sim/exp_xsfund_out.txt")
N_TRIALS = 1239
H, COST, SHOCK, NW = X.H, X.COST, X.SHOCK, X.NW
FUND_STALE = pd.Timedelta(days=450)
PFEATS = list(X.FEATS)
FFEATS = ["ep", "bp", "sp", "fcfp", "ebitdaev", "roa", "roe", "gpa", "accr", "revg", "epsg", "assetg", "iss", "de", "lmcap",
          "recency"]
FEATS = PFEATS + FFEATS
GBM_KW = dict(max_depth=3, learning_rate=0.05, max_iter=300, min_samples_leaf=200, early_stopping=False, random_state=0)
say, lines = X.say, X.lines

SF1_COLS = ["ticker", "dimension", "calendardate", "date", "fxusd", "price", "marketcap", "debtusd", "cashnequsd", "netinccmnusd",
            "equityusd", "revenueusd", "fcf", "ebitdausd", "assets", "equity", "netinc", "gp", "ncfo", "revenue", "eps", "sharesbas",
            "debt"]


# ---------------------------------------------------------------- SF1 point-in-time tables
def _drop_old_amendments(d: pd.DataFrame) -> pd.DataFrame:
    d = d.sort_values(["ticker", "date", "calendardate"], kind="mergesort").reset_index(drop=True)
    cm = d.groupby("ticker").calendardate.cummax()
    prev = cm.groupby(d.ticker).shift(1)
    return d[prev.isna() | (d.calendardate >= prev)].reset_index(drop=True)


def load_sf1():
    f = pq.read_table(X.FULL / "fundamentals.parquet", columns=SF1_COLS,
                      filters=[("dimension", "in", ["ARQ", "ART"])]).to_pandas()
    f["ticker"] = f.ticker.astype(str)
    for c in ("calendardate", "date"):
        f[c] = pd.to_datetime(f[c])
    f = f.dropna(subset=["date", "calendardate"])
    for c in SF1_COLS[4:]:
        f[c] = f[c].astype(np.float64)
    arq_all = f[f.dimension == "ARQ"].drop(columns="dimension")
    art = _drop_old_amendments(f[f.dimension == "ART"].drop(columns="dimension"))
    n_raw = len(arq_all)
    arq = _drop_old_amendments(arq_all)
    # year-ago values known on or before this row's filing date
    ya = arq_all[["ticker", "calendardate", "date", "revenue", "eps", "assets", "sharesbas"]].rename(
        columns={"date": "date_ya", "revenue": "revenue_ya", "eps": "eps_ya", "assets": "assets_ya", "sharesbas": "sharesbas_ya"})
    q = arq.copy()
    q["cd_ya"] = q.calendardate - pd.DateOffset(years=1)
    q["cd_ya"] = q.cd_ya + pd.offsets.MonthEnd(0)
    ya = ya.rename(columns={"calendardate": "cd_ya"}).sort_values("date_ya", kind="mergesort")
    q = pd.merge_asof(q.sort_values("date", kind="mergesort"), ya, left_on="date", right_on="date_ya", by=["ticker", "cd_ya"],
                      allow_exact_matches=True)
    assert (q.date_ya.isna() | (q.date_ya <= q.date)).all()
    with np.errstate(divide="ignore", invalid="ignore"):
        q["revg"] = np.where(q.revenue_ya > 0, q.revenue / q.revenue_ya - 1, np.nan)
        q["epsg"] = np.where(q.eps_ya.abs() > 0, (q.eps - q.eps_ya) / q.eps_ya.abs(), np.nan)
        q["assetg"] = np.where(q.assets_ya > 0, q.assets / q.assets_ya - 1, np.nan)
        q["iss"] = np.where(q.sharesbas_ya > 0, q.sharesbas / q.sharesbas_ya - 1, np.nan)
        q["de"] = np.where(q.equity > 0, q.debt / q.equity, np.nan)
        a = art
        art = a[["ticker", "date"]].copy()
        art["e_usd"] = a.netinccmnusd; art["s_usd"] = a.revenueusd; art["fcf_usd"] = a.fcf * a.fxusd; art["ebitda_usd"] = a.ebitdausd
        art["roa"] = np.where(a.assets > 0, a.netinc / a.assets, np.nan)
        art["roe"] = np.where(a.equity > 0, a.netinc / a.equity, np.nan)
        art["gpa"] = np.where(a.assets > 0, a.gp / a.assets, np.nan)
        art["accr"] = np.where(a.assets > 0, (a.netinc - a.ncfo) / a.assets, np.nan)
    arq = q[["ticker", "date", "price", "marketcap", "debtusd", "cashnequsd", "equityusd", "revg", "epsg", "assetg", "iss", "de"]]
    say(f"SF1: ARQ rows {n_raw} -> {len(arq)} after dropping old-period amendments filed after a newer period; ART {len(art)}; "
        f"ARQ with a year-ago row {q.date_ya.notna().mean()*100:.1f}%; field used as filing date: `date` (no `datekey` column)")
    return arq.reset_index(drop=True), art.reset_index(drop=True)


# ---------------------------------------------------------------- wrap the N 1235 loader to collect split-adjusted closes
STASH: dict = {}
_ORIG_FEATURES = X._features


def _features_hook(b: pd.DataFrame) -> pd.DataFrame:
    o = _ORIG_FEATURES(b)
    if "filings" not in STASH:
        return o
    tk = o.ticker.to_numpy()
    per = o.date.dt.to_period("M").to_numpy()
    last = np.r_[(tk[1:] != tk[:-1]) | (per[1:] != per[:-1]), True]
    STASH["me"].append(o.loc[last, ["ticker", "date", "close"]].rename(columns={"close": "close_t"}))
    fl = STASH["filings"]
    fl = fl[fl.ticker.isin(set(tk))].sort_values("date", kind="mergesort")
    if len(fl):
        bb = o[["ticker", "date", "close", "closeunadj"]].rename(columns={"date": "bd"}).sort_values("bd", kind="mergesort")
        m = pd.merge_asof(fl, bb, left_on="date", right_on="bd", by="ticker", allow_exact_matches=True)
        STASH["ff"].append(m[["ticker", "date", "close", "closeunadj"]].rename(columns={"close": "close_f", "closeunadj": "unadj_f"}))
    return o


X._features = _features_hook


def build_source(source, me_from, me_to, arq, art):
    STASH.clear()
    STASH.update(filings=arq[["ticker", "date"]].drop_duplicates(), me=[], ff=[])
    rows, spy_me = X.build_rows(source, me_from, me_to)
    me = pd.concat(STASH["me"], ignore_index=True)
    ff = pd.concat(STASH["ff"], ignore_index=True).drop_duplicates(["ticker", "date"])
    STASH.clear()
    rows = rows.merge(me, on=["ticker", "date"], how="left")
    assert rows.close_t.notna().all(), "every month-end row has its own split-adjusted close"
    q = arq.merge(ff, on=["ticker", "date"], how="left")
    with np.errstate(divide="ignore", invalid="ignore"):
        q["px_adj_f"] = q.close_f          # SF1 `price` is split-adjusted (to the SF1 vintage); use the label file's own close at the filing
    rows["t"] = pd.to_datetime(rows.date)
    rows = rows.sort_values("t", kind="mergesort").reset_index(drop=True)
    qs = q.sort_values("date", kind="mergesort")
    m = pd.merge_asof(rows[["ticker", "t"]], qs, left_on="t", right_on="date", by="ticker", allow_exact_matches=False,
                      tolerance=FUND_STALE)
    assert (m.date.isna() | (m.date < m.t)).all(), "SF1 ARQ value used on/after its filing date"
    mr = pd.merge_asof(rows[["ticker", "t"]], qs[["ticker", "date"]].rename(columns={"date": "lastf"}), left_on="t",
                       right_on="lastf", by="ticker", allow_exact_matches=False)
    s = pd.merge_asof(rows[["ticker", "t"]], art.sort_values("date", kind="mergesort"), left_on="t", right_on="date", by="ticker",
                      allow_exact_matches=False, tolerance=FUND_STALE)
    assert (s.date.isna() | (s.date < s.t)).all(), "SF1 ART value used on/after its filing date"
    with np.errstate(divide="ignore", invalid="ignore"):
        mcap = m.marketcap.to_numpy() * rows.close_t.to_numpy() / m.px_adj_f.to_numpy()
        mcap = np.where(mcap > 0, mcap, np.nan)
        ev = mcap + m.debtusd.fillna(0).to_numpy() - m.cashnequsd.fillna(0).to_numpy()
        rows["ep"] = s.e_usd.to_numpy() / mcap
        rows["bp"] = m.equityusd.to_numpy() / mcap
        rows["sp"] = s.s_usd.to_numpy() / mcap
        rows["fcfp"] = s.fcf_usd.to_numpy() / mcap
        rows["ebitdaev"] = np.where(ev > 0, s.ebitda_usd.to_numpy() / ev, np.nan)
        for c in ("roa", "roe", "gpa", "accr"):
            rows[c] = s[c].to_numpy()
        for c in ("revg", "epsg", "assetg", "iss", "de"):
            rows[c] = m[c].to_numpy()
        rows["lmcap"] = np.log(mcap)
        rows["recency"] = (rows.t - mr.lastf).dt.days.to_numpy(float)
        rows["_mcap_drift"] = np.log(mcap / m.marketcap.to_numpy())
        rows["_fdate"] = m.date.to_numpy()
    for c in FFEATS:
        rows[c] = np.where(np.isfinite(rows[c].to_numpy(float)), rows[c].to_numpy(float), np.nan).astype(np.float32)
    return rows.drop(columns=["t"]), spy_me


def rank_fund(rows: pd.DataFrame) -> pd.DataFrame:
    g = rows.groupby("date")
    for col in FFEATS:
        rk = g[col].rank(method="average").to_numpy(float)
        cnt = g[col].transform("count").to_numpy(float)
        v = 2 * (rk - 1) / np.maximum(cnt - 1, 1) - 1
        rows[col] = np.where(np.isfinite(v), v, 0.0).astype(np.float32)
    return rows


# ---------------------------------------------------------------- GBM pipeline (same train sets / placebo labels as run_model)
def run_gbm(name, months, Zs, Ylab, codes, me_dates, seg_S, shifts, Lmat, with_placebo=True):
    t0 = time.time()
    me_sidx = np.array([mo[1] for mo in months])
    ref_idx = [k for k, d in enumerate(me_dates) if d.month == 12 and d >= X.FIRST_REFIT]
    nmon = len(months)
    F = {}
    for r_i, ri in enumerate(ref_idx):
        tr = np.where(me_sidx + H < me_sidx[ri])[0]
        assert tr.max() < ri and (me_sidx[tr] + H < me_sidx[ri]).all()
        Xtr = np.vstack([Zs[k] for k in tr])
        last_pred = ref_idx[r_i + 1] if r_i + 1 < len(ref_idx) else nmon
        need_pl = with_placebo and ri < seg_S and me_dates[ri] <= X.JUDGE_LAST
        Ycols = [np.concatenate([Ylab[k] for k in tr])]
        if need_pl:
            assert tr.max() < seg_S
            for sh in shifts:
                yc = []
                for k in tr:
                    yp = Lmat[codes[k], (k - sh) % seg_S]
                    yc.append(np.where(np.isfinite(yp), yp, 0.0))
                Ycols.append(np.concatenate(yc).astype(np.float32))
        preds = {mi: np.empty((len(Zs[mi]), len(Ycols)), np.float32) for mi in range(ri, last_pred)}
        for c, y in enumerate(Ycols):
            mdl = HistGradientBoostingRegressor(**GBM_KW).fit(Xtr, y)
            assert mdl.n_iter_ == GBM_KW["max_iter"]
            for mi in range(ri, last_pred):
                preds[mi][:, c] = mdl.predict(Zs[mi])
        F.update(preds)
        say(f"    refit {me_dates[ri].date()} train rows {len(Xtr)} fits {len(Ycols)} -> months {me_dates[ri].date()}.."
            f"{me_dates[last_pred-1].date()} ({time.time()-t0:.0f}s)")
        del Xtr, Ycols; gc.collect()
    return F


# ---------------------------------------------------------------- permutation importance, fit/validation only (pre-2010-12)
def _ic(f_by_m, y_by_m):
    out = []
    for f, y in zip(f_by_m, y_by_m):
        rf = np.argsort(np.argsort(f)).astype(float)
        out.append(np.corrcoef(rf, y)[0, 1])
    return float(np.mean(out))


def importances(months, Zs, Ylab, me_dates):
    me_sidx = np.array([mo[1] for mo in months])
    sess_2007 = me_sidx[np.searchsorted(me_dates, X.LAM_TRAIN_END, side="right") - 1]
    ref0 = [k for k, d in enumerate(me_dates) if d.month == 12 and d >= X.FIRST_REFIT][0]
    tr = np.where(me_sidx + H <= sess_2007)[0]
    va = np.where((me_dates >= X.VAL_START) & (me_sidx + H < me_sidx[ref0]))[0]
    assert me_dates[va].max() < X.FIRST_REFIT
    mdl = HistGradientBoostingRegressor(**GBM_KW).fit(np.vstack([Zs[k] for k in tr]), np.concatenate([Ylab[k] for k in tr]))
    Zv = [Zs[k] for k in va]; Yv = [Ylab[k] for k in va]
    base = [mdl.predict(z) for z in Zv]
    ic0 = _ic(base, Yv)
    mse0 = float(np.mean(np.concatenate([(p - y) ** 2 for p, y in zip(base, Yv)])))
    rng = np.random.default_rng(7)
    rep = 3

    def perm(cols):
        d_ic, d_mse = [], []
        for _ in range(rep):
            P = []
            for z in Zv:
                zz = z.copy()
                for c in cols:
                    zz[:, c] = zz[rng.permutation(len(zz)), c]          # within-month shuffle
                P.append(mdl.predict(zz))
            d_ic.append(ic0 - _ic(P, Yv))
            d_mse.append(float(np.mean(np.concatenate([(p - y) ** 2 for p, y in zip(P, Yv)]))) - mse0)
        return np.mean(d_ic), np.mean(d_mse)

    say(f"  GBM permutation importance (judge-free): fit on {len(tr)} months with labels realised <= {X.LAM_TRAIN_END.date()}, "
        f"scored on validation {me_dates[va[0]].date()}..{me_dates[va[-1]].date()} ({len(va)} months, labels realised before "
        f"{me_dates[ref0].date()}); within-month shuffles x{rep}, seed 7; validation mean monthly rank IC {ic0:+.4f}, MSE {mse0:.5f}")
    res = [(FEATS[c],) + perm([c]) for c in range(len(FEATS))]
    res.sort(key=lambda r: -r[1])
    say("  per feature (drop in mean IC x1e4 | rise in MSE x1e5): " +
        " ".join(f"{n} {a*1e4:+.0f}|{b*1e5:+.1f}" for n, a, b in res))
    bp = perm(list(range(len(PFEATS)))); bf = perm(list(range(len(PFEATS), len(FEATS))))
    say(f"  blocks: all 19 price ranks permuted: IC drop {bp[0]*1e4:+.0f}e-4 (MSE {bp[1]*1e5:+.1f}e-5); "
        f"all 16 SF1 features permuted: IC drop {bf[0]*1e4:+.0f}e-4 (MSE {bf[1]*1e5:+.1f}e-5)")


# ---------------------------------------------------------------- evaluation: gates vs SPY, EW reported
def evaluate(tag, gross, turn, ew, spy, dates, pl_spy=None, pl_ew=None, gate=True):
    net = gross - COST * turn; net_s = gross - SHOCK * turn
    h1 = dates <= X.H1_LAST
    res = {}
    for bn, B in (("SPY", spy), ("EW", ew)):
        a, t, beta = X.stats(net, B)
        a1 = X.stats(net[h1], B[h1])[0] if h1.sum() > 12 else float("nan")
        a2 = X.stats(net[~h1], B[~h1])[0] if (~h1).sum() > 12 else float("nan")
        as_, ts_, _ = X.stats(net_s, B)
        hedged = net - beta * B
        keep = np.ones(len(net), bool); keep[np.argsort(hedged)[-5:]] = False
        ax5 = X.stats(net[keep], B[keep])[0]
        sh, shb = X.sharpe_m(net), X.sharpe_m(B)
        exc = net - B
        res[bn] = dict(a=a, t=t, a1=a1, a2=a2, as_=as_, ax5=ax5, dsh=sh - shb)
        say(f"  {tag} vs {bn:<3}{' (GATED)' if bn == 'SPY' else ' (report)'}: alpha {a*1e4:+7.1f}bp/mo NW t {t:+5.2f} beta {beta:.2f} | "
            f"halves 11-15 {a1*1e4:+7.1f} 16-20 {a2*1e4:+7.1f} | Sharpe {sh:.2f} vs {shb:.2f} (d {sh-shb:+.2f}) | 10bp/side alpha "
            f"{as_*1e4:+7.1f} t {ts_:+5.2f} | ex-top5 {ax5*1e4:+7.1f} | excess mean {exc.mean()*1e4:+6.1f}bp t {tstat(exc, NW):+5.2f} "
            f"med {np.median(exc)*1e4:+6.1f} hit {(exc>0).mean()*100:4.1f}% | DSR(N {N_TRIALS}) {dsr(hedged, N_TRIALS):.3f}")
    say(f"  {tag} net: mean {net.mean()*1e4:+.1f}bp/mo, CAGR {(np.prod(1+net)**(12/len(net))-1)*100:+.1f}%, Sharpe {X.sharpe_m(net):.2f}, "
        f"maxDD {X.maxdd(net)*100:.1f}% (EW {X.maxdd(ew)*100:.1f}%, SPY {X.maxdd(spy)*100:.1f}%), median {np.median(net)*1e4:+.1f}bp, "
        f"hit {(net>0).mean()*100:.1f}%, months {len(net)}, turnover {turn.mean():.2f}/mo ({turn.mean()*12:.1f}x/yr), "
        f"cost drag {COST*turn.mean()*12*1e4:.0f}bp/yr")
    if not gate:
        return res
    pct = (pl_spy < res["SPY"]["a"]).mean() * 100
    pct_ew = (pl_ew < res["EW"]["a"]).mean() * 100
    say(f"  {tag} placebo: real alpha vs SPY {res['SPY']['a']*1e4:+.1f}bp/mo at pct {pct:.1f} of {len(pl_spy)} (placebo p50 "
        f"{np.percentile(pl_spy,50)*1e4:+.1f}, p95 {np.percentile(pl_spy,95)*1e4:+.1f}); [report] vs EW {res['EW']['a']*1e4:+.1f} at pct "
        f"{pct_ew:.1f} (p50 {np.percentile(pl_ew,50)*1e4:+.1f}, p95 {np.percentile(pl_ew,95)*1e4:+.1f})")
    S = res["SPY"]
    g = [S["a"] > 0 and S["t"] >= 2, S["a1"] > 0 and S["a2"] > 0, S["dsh"] >= 0.20, S["as_"] > 0, pct >= 95, S["ax5"] > 0]
    names = ["G1 alpha>0 & t>=2", "G2 both halves>0", "G3 dSharpe>=+0.20", "G4 10bp/side>0", "G5 placebo>=95th", "G6 ex-top-5>0"]
    say("  " + tag + " gates (vs SPY): " + "; ".join(f"{n} {'PASS' if v else 'FAIL'}" for n, v in zip(names, g)) +
        f" => {'PASS' if all(g) else 'DEAD'}")
    res["gates"] = g
    return res


# ---------------------------------------------------------------- main
def main():
    t0 = time.time()
    sha = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]
    sha_x = hashlib.sha256(pathlib.Path(X.__file__).read_bytes()).hexdigest()[:16]
    say(f"EXP round 5 N 1237 XS-FUND (program N {N_TRIALS}; code sha256 {sha}; imports exp_xsrff.py sha256 {sha_x}; DRY {DRY}; "
        f"threads 3; float32)")
    say(f"universe/portfolio/costs/placebo as N 1235: SEP common, px>=$5, ADV20>=$10M, >=253 bars; month-end decisions; label t->t+{H}; "
        f"top min({X.MAXN}, N/10) EW; {COST*1e4:g}bp/side (shock {SHOCK*1e4:g}); placebo {X.N_PLACEBO} per-name circular label shifts "
        f"seed 12345; GBM {GBM_KW}; RFF P {2*X.P_HALF} gamma {X.GAMMA} on {len(FEATS)} features")
    arq, art = load_sf1()
    rows_c, spy_c = build_source("cache", X.FEAT_START, X.JUDGE_LAST, arq, art)
    assert rows_c.y21.notna().all(), "judge labels must be complete inside the cache"
    say(f"cache rows {len(rows_c)} months {rows_c.date.nunique()} names {rows_c.ticker.nunique()}; {time.time()-t0:.0f}s")
    try:
        rows_f, spy_f = build_source("full", pd.Timestamp("2020-12-01"), pd.Timestamp("2030-01-01"), arq, art)
        rows_f = rows_f[rows_f.y21.notna()]
        report_ok = True
        say(f"full-store rows {len(rows_f)} months {rows_f.date.nunique()}; {time.time()-t0:.0f}s")
    except Exception as e:  # noqa: BLE001
        say(f"full store unavailable ({e!r}); REPORT skipped")
        rows_f, spy_f, report_ok = rows_c.iloc[:0], spy_c.iloc[:0], False
    del arq, art; gc.collect()
    rows = pd.concat([rows_c, rows_f], ignore_index=True)
    del rows_c, rows_f; gc.collect()
    # audit: coverage and point-in-time
    yr = pd.to_datetime(rows.date).dt.year
    cov = rows.assign(yr=yr, has=rows.ep.notna() | rows.bp.notna()).groupby("yr").has.mean()
    lagd = (pd.to_datetime(rows.date) - pd.to_datetime(rows._fdate)).dt.days
    say("audit SF1 coverage of universe rows by year (any value): " + " ".join(f"{y}:{v*100:.0f}%" for y, v in cov.items()))
    say(f"audit days from filing date to decision t: min {lagd.min():.0f} median {lagd.median():.0f} max {lagd.max():.0f} "
        f"(must be >= 1); log(mcap_t / SF1 mcap at filing) quantiles 5/50/95 "
        f"{np.nanpercentile(rows._mcap_drift, [5, 50, 95]).round(3).tolist()}; delisted names in rows "
        f"{rows.loc[rows.delist, 'ticker'].nunique()}, of which with SF1 {rows.loc[rows.delist & rows.ep.notna(), 'ticker'].nunique()}")
    assert lagd.min() >= 1
    say("audit raw missing share: " + " ".join(f"{c} {rows[c].isna().mean()*100:.0f}%" for c in FFEATS))
    rows = X.rank_norm(rows)
    rows = rank_fund(rows)
    cal_c = load_etfs(["SPY"]).date.to_numpy("datetime64[ns]")
    if report_ok:
        tt = pq.read_table(X.FULL / "funds.parquet", columns=["date"], filters=[("ticker", "=", "SPY")]).to_pandas()
        cal_f = pd.to_datetime(tt.date).to_numpy("datetime64[ns]")
        cal = np.unique(np.r_[cal_c, cal_f[cal_f > cal_c[-1]]])
    else:
        cal = cal_c
    rows["gs"] = np.searchsorted(cal, rows.date.to_numpy("datetime64[ns]"))
    rows = rows.sort_values(["date", "ticker"], kind="mergesort").reset_index(drop=True)
    tick_codes = pd.factorize(rows.ticker)[0]
    rows["code"] = tick_codes
    spym = pd.concat([spy_c, spy_f]).drop_duplicates("date", keep="first").set_index("date").spy21
    groups = rows.groupby("date", sort=True).indices
    me_dates = pd.DatetimeIndex(sorted(groups))
    months = [(d, int(rows.gs.iloc[groups[d][0]])) for d in me_dates]
    Zall = rows[FEATS].to_numpy(np.float32)
    assert np.isfinite(Zall).all()
    Z = [Zall[groups[d]] for d in me_dates]
    del Zall
    Ylab = [rows.ylab.to_numpy(np.float32)[groups[d]] for d in me_dates]
    Yret = [rows.y21.to_numpy(np.float32)[groups[d]] for d in me_dates]
    codes = [rows.code.to_numpy()[groups[d]] for d in me_dates]
    PX = [rows.px.to_numpy(np.float32)[groups[d]] for d in me_dates]
    ew = np.array([y.astype(float).mean() for y in Yret])
    spy21 = spym.reindex(me_dates).to_numpy(float)
    assert np.isfinite(spy21).all()
    assert all(np.corrcoef(Ylab[k], Yret[k])[0, 1] > 0.5 for k in range(0, len(me_dates), 7))
    seg_S = int((me_dates <= X.JUDGE_LAST).sum())
    Lmat = np.full((tick_codes.max() + 1, seg_S), np.nan, np.float32)
    for k in range(seg_S):
        Lmat[codes[k], k] = Ylab[k]
    prng = np.random.default_rng(12345)
    shifts = prng.integers(X.MIN_SHIFT, seg_S - X.MIN_SHIFT + 1, X.N_PLACEBO)
    nm = np.array([len(z) for z in Z])
    say(f"months {len(me_dates)} ({me_dates[0].date()}..{me_dates[-1].date()}), label segment S {seg_S}, names/month median "
        f"{int(np.median(nm))} min {nm.min()} max {nm.max()}; delisted-truncated labels {int(rows.delist.sum())}; {time.time()-t0:.0f}s")
    del rows; gc.collect()

    say("\n## judge-free diagnostics (fit/validation period only, before the first refit)")
    importances(months, Z, Ylab, me_dates)

    rng = np.random.default_rng(0)
    W = (X.GAMMA * rng.standard_normal((len(FEATS), X.P_HALF))).astype(np.float32)

    def f_rff(z):
        S = z @ W
        return np.hstack([np.sin(S), np.cos(S)]).astype(np.float32)

    judge_idx = [k for k, d in enumerate(me_dates) if X.FIRST_REFIT <= d <= X.JUDGE_LAST]
    rep_idx = [k for k, d in enumerate(me_dates) if d > X.JUDGE_LAST]
    jd = me_dates[judge_idx]
    results = {}
    say("\n# FROZEN: everything below is the first and only judge read of this code (sha above)")
    for name in ("N1237 XS-FUND GBM (primary)", "N1237 XS-FUND RFF (second)"):
        say(f"\n## {name}")
        if "GBM" in name:
            F = run_gbm(name, months, Z, Ylab, codes, me_dates, seg_S, shifts, Lmat)
        else:
            F, _ = X.run_model(name, f_rff, 2 * X.P_HALF, months, Z, Ylab, codes, me_dates, seg_S, shifts, Lmat)
        g, tu, pk = X.portfolio(lambda mi: F[mi][:, 0], judge_idx, Yret, codes, PX)
        pl_s, pl_e = [], []
        for c in range(1, 1 + X.N_PLACEBO):
            gp, tp, _ = X.portfolio(lambda mi, c=c: F[mi][:, c], judge_idx, Yret, codes, PX)
            pl_s.append(X.stats(gp - COST * tp, spy21[judge_idx])[0]); pl_e.append(X.stats(gp - COST * tp, ew[judge_idx])[0])
        pl_s, pl_e = np.array(pl_s), np.array(pl_e)
        if DRY:
            say(f"  DRY: judge months {len(judge_idx)}, placebo cols {len(pl_s)}, picks/month {np.mean([len(o) for o in pk]):.0f}; "
                f"judge numbers suppressed ({time.time()-t0:.0f}s)")
            continue
        say(f"JUDGE decisions {jd[0].date()}..{jd[-1].date()} ({len(judge_idx)} months), picks/month {np.mean([len(o) for o in pk]):.0f}")
        r = evaluate(name, g, tu, ew[judge_idx], spy21[judge_idx], jd, pl_s, pl_e)
        X.deciles(name, lambda mi: F[mi][:, 0], judge_idx, Yret)
        X.dollars(name + " judge", g - COST * tu, ew[judge_idx], spy21[judge_idx], pk, judge_idx, PX)
        results[name] = r
        if rep_idx:
            gr, tr_, pkr = X.portfolio(lambda mi: F[mi][:, 0], rep_idx, Yret, codes, PX)
            rd = me_dates[rep_idx]
            say(f"REPORT (descriptive, full store) decisions {rd[0].date()}..{rd[-1].date()} ({len(rep_idx)} months)")
            evaluate(name + " REPORT", gr, tr_, ew[rep_idx], spy21[rep_idx], rd, gate=False)
            X.deciles(name + " REPORT", lambda mi: F[mi][:, 0], rep_idx, Yret)
            X.dollars(name + " REPORT", gr - COST * tr_, ew[rep_idx], spy21[rep_idx], pkr, rep_idx, PX)
        del F; gc.collect()
    if not DRY:
        a = results.get("N1237 XS-FUND GBM (primary)", {}).get("gates")
        b = results.get("N1237 XS-FUND RFF (second)", {}).get("gates")
        say(f"\nVERDICT: N1237 XS-FUND {'PASS' if a and all(a) else 'DEAD'} (needs the GBM); GBM {'PASS' if a and all(a) else 'DEAD'}, "
            f"RFF {'PASS' if b and all(b) else 'DEAD'}")
    say(f"total {time.time()-t0:.0f}s")
    OUT.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
