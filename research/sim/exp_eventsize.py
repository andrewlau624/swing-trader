"""EXP round 3, R3-PREF (N 1230) / R3-CEF (N 1231): linear per-event sizing of PREF-EX and CEF-RV vs equal size.

Pre-registration: research/drafts/round1_prose.md, "## Amendment - EXP round 3: RL / linear models pointed at the book's
EXISTING edges", bullet R3-PREF / R3-CEF. Ridge on event features known at entry -> size = clip(1 + 0.5 z, 0.5, 1.5),
renormalised per entry date, vs equal size. PREF fit 2021-01..2023-12, judge 2024-01..2026-10; CEF fit to 2015, judge 2016-26.
Gate: judge sized-minus-equal mean > 0, day-clustered t >= 2, both judge halves > 0, placebo (labels shuffled within entry
date, 200) >= 95th pct, ex-top-5 events > 0.

Readings fixed before any judge number (most conservative where ambiguous):
- PREF events = pref_fetch.events() -> pref_noauc.build() on the cached official prints (data/research/pref_noauc/x); the
  pref_cross cache (data/research/pref) is not on disk, so no per-event measured cross cost exists. Live window = CC
  (pref_ex_live: "Roth, CC form"). Cost = registered 10bp RT on events with a real '6' close print on T-1 and T, 20bp RT
  on no-auction events (live measured no-auction cost ~+20bp, pref_noauc memo).
- CEF events = cef_rv.build_trades output on the Nasdaq NAV panel as saved by cef_stress (cef_stress_trades.csv, the
  file CEF-ML used); data/research/cefconnect/cef_panel.parquet (cef_rv.load_nav's input) is not on disk. Label = ret - 50bp.
- z = (prediction - mean) / sd of the fit-period in-sample predictions (fixed ex ante, not per judge date).
- Lambda: inner time split of the fit period (first 70% of entry dates train, last 30% validate; CEF training rows purged
  to exits before the first validation entry), criterion = validation sized-minus-equal mean per event.
- Training labels winsorised at the fit 1st/99th pct (CEF-ML practice); judge labels raw. Missing features -> fit median.
- Fit rows must also EXIT inside the fit period (purge at the fit/judge boundary).
- Placebo = fit labels shuffled within entry date, whole pipeline (lambda + fit + z) re-run, 200 draws; a second placebo
  (judge labels shuffled within date, sizes fixed, 200) is also required >= 95th.
- Ex-top-5 = drop the 5 judge events with the largest (s - 1) * r contribution.

    PYTHONPATH=. python3 research/sim/exp_eventsize.py      # -> research/sim/exp_eventsize_out.txt
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from research.sim.cef_ml import features as cef_features, ridge_fit  # noqa: E402
from research.sim.pref_fetch import S as SHARADAR, events  # noqa: E402
from research.sim.pref_noauc import ACCT, D as PREF_D, PART, build, day_table  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent / "exp_eventsize_out.txt"
CEF = ROOT / "data/research/cefconnect"
LAMS = (0.1, 1, 10, 100, 1e3, 1e4, 1e5)
N_PLAC = 200
RNG = np.random.default_rng(1230)
lines: list[str] = []


def say(s: str = "") -> None:
    print(s, flush=True)
    lines.append(s)


# ---------------------------------------------------------------- sizing machinery
def sizes(pred: np.ndarray, dates: np.ndarray, mu: float, sd: float) -> np.ndarray:
    z = (pred - mu) / sd if sd > 0 else np.zeros_like(pred)
    s = np.clip(1 + 0.5 * z, 0.5, 1.5)
    m = pd.Series(s).groupby(dates).transform("mean").to_numpy()
    return s / m


def tilt(r, s):
    return (s - 1.0) * r


def fit_model(X, y, dates, exits=None):
    """Lambda by inner time split, then refit on the whole fit set. Returns (fn, b, lam, mu, sd)."""
    ud = np.sort(np.unique(dates))
    cut = ud[int(len(ud) * 0.7)]
    va = dates >= cut
    tr = (dates < cut) if exits is None else (exits < cut)
    best, bl = -np.inf, LAMS[-1]
    for lam in LAMS:
        fn, _ = ridge_fit(X[tr], y[tr], lam)
        p_tr = fn(X[tr])
        s = sizes(fn(X[va]), dates[va], p_tr.mean(), p_tr.std())
        v = tilt(y[va], s).mean()
        if v > best:
            best, bl = v, lam
    fn, b = ridge_fit(X, y, bl)
    p = fn(X)
    return fn, b, bl, p.mean(), p.std()


def prep(Xf: np.ndarray, Xj: np.ndarray, yf: np.ndarray):
    med = np.nanmedian(Xf, 0)
    Xf = np.where(np.isnan(Xf), med, Xf); Xj = np.where(np.isnan(Xj), med, Xj)
    lo, hi = np.percentile(yf, [1, 99])
    return Xf, Xj, np.clip(yf, lo, hi)


def cl_t(x: np.ndarray, g: np.ndarray) -> float:
    m = x.mean(); s = pd.Series(x - m).groupby(g).sum().to_numpy(); G = len(s)
    se = np.sqrt((s ** 2).sum() * G / max(G - 1, 1)) / len(x)
    return m / se if se > 0 else np.nan


def run(name: str, df: pd.DataFrame, cols: list[str], fitm: np.ndarray, judm: np.ndarray, mid: pd.Timestamp,
        dollar_fn=None) -> None:
    f, j = df[fitm].reset_index(drop=True), df[judm].reset_index(drop=True)
    Xf, Xj, yf = prep(f[cols].to_numpy(float), j[cols].to_numpy(float), f.r.to_numpy(float))
    df_, dj = f.ed.to_numpy("datetime64[ns]"), j.ed.to_numpy("datetime64[ns]")
    exf = f.xd.to_numpy("datetime64[ns]") if "xd" in f else None
    rj = j.r.to_numpy(float)
    say(f"fit:   {len(f)} events / {f.ed.nunique()} entry dates ({f.ed.min().date()}..{f.ed.max().date()})")
    say(f"judge: {len(j)} events / {j.ed.nunique()} entry dates ({j.ed.min().date()}..{j.ed.max().date()}); "
        f"dates with >= 2 events {(j.groupby('ed').size() >= 2).sum()}")
    miss = df[cols].isna().mean()
    say("feature missing share (all rows): " + ", ".join(f"{c} {v:.0%}" for c, v in miss.items() if v > 0) or "none")

    fn, b, lam, mu, sd = fit_model(Xf, yf, df_, exf)
    s = sizes(fn(Xj), dj, mu, sd)
    x = tilt(rj, s)
    day = pd.Series(x).groupby(dj).mean()
    t = cl_t(x, dj)
    h1m, h2m = dj < np.datetime64(mid), dj >= np.datetime64(mid)
    h1, h2 = x[h1m].mean(), x[h2m].mean()
    ex5 = np.sort(x)[:-5].mean()
    say(f"lambda {lam:g}; ridge coefs (bp per fit sd of the feature): "
        + ", ".join(f"{c} {v * 1e4:+.1f}" for c, v in zip(cols, b)))
    say(f"size spread in judge: p5 {np.percentile(s, 5):.2f} p50 {np.median(s):.2f} p95 {np.percentile(s, 95):.2f}; "
        f"corr(pred, r) judge {np.corrcoef(fn(Xj), rj)[0, 1]:+.3f}")
    say(f"equal-size judge mean net {rj.mean() * 1e4:+.1f}bp/event (date-EW {pd.Series(rj).groupby(dj).mean().mean() * 1e4:+.1f}bp), "
        f"hit {(rj > 0).mean():.2f}")
    say(f"sized - equal: {x.mean() * 1e4:+.2f}bp/event, date-mean {day.mean() * 1e4:+.2f}bp/date, day-clustered t {t:+.2f}")
    if dollar_fn is not None:
        say(dollar_fn(j, s))
    say(f"halves (split {mid.date()}): {h1 * 1e4:+.2f} (n {h1m.sum()}) / {h2 * 1e4:+.2f} (n {h2m.sum()}) bp/event")
    say(f"ex-top-5 events: {ex5 * 1e4:+.2f}bp/event")

    # placebo A: fit labels shuffled within entry date, whole pipeline re-run
    yraw = f.r.to_numpy(float); grp = pd.Series(np.arange(len(f))).groupby(df_)
    idx_groups = [g.to_numpy() for _, g in grp]
    pa = []
    for _ in range(N_PLAC):
        ys = yraw.copy()
        for g in idx_groups:
            if len(g) > 1:
                ys[g] = yraw[RNG.permutation(g)]
        lo, hi = np.percentile(ys, [1, 99])
        fn_p, _, _, mu_p, sd_p = fit_model(Xf, np.clip(ys, lo, hi), df_, exf)
        pa.append(tilt(rj, sizes(fn_p(Xj), dj, mu_p, sd_p)).mean())
    pa = np.array(pa); pctA = (pa < x.mean()).mean() * 100
    # placebo B: judge labels shuffled within date, sizes fixed
    gj = [g.to_numpy() for _, g in pd.Series(np.arange(len(j))).groupby(dj)]
    pb = []
    for _ in range(N_PLAC):
        rs = rj.copy()
        for g in gj:
            if len(g) > 1:
                rs[g] = rj[RNG.permutation(g)]
        pb.append(tilt(rs, s).mean())
    pb = np.array(pb); pctB = (pb < x.mean()).mean() * 100
    say(f"placebo A (fit labels shuffled within date, refit, {N_PLAC}): real at {pctA:.1f} pct (null p50 {np.median(pa) * 1e4:+.2f}, "
        f"p95 {np.percentile(pa, 95) * 1e4:+.2f}bp)")
    say(f"placebo B (judge labels shuffled within date, {N_PLAC}): real at {pctB:.1f} pct (null p95 {np.percentile(pb, 95) * 1e4:+.2f}bp)")
    checks = dict(mean_pos=x.mean() > 0, t_ge_2=bool(np.isfinite(t) and t >= 2), halves=h1 > 0 and h2 > 0,
                  placebo=pctA >= 95 and pctB >= 95, ex_top5=ex5 > 0)
    ok = all(checks.values())
    say("gate: " + ", ".join(f"{k} {'ok' if v else 'FAIL'}" for k, v in checks.items()) + f" -> {'PASS' if ok else 'FAIL'}")
    verdict[name] = ok


verdict: dict[str, bool] = {}


# ---------------------------------------------------------------- PREF
def pref_frame() -> pd.DataFrame:
    e = events()
    b = build(e)
    m = b.merge(e.rename(columns={"ticker": "t", "date": "d"}), on=["t", "d"], how="left")
    # ex-ante spread proxy: median M-print band over the 5 sessions before T-1 (T-1's own band is not known at 15:25)
    pb = {}
    for d, x in e.groupby("date"):
        fpath = PREF_D / "x" / f"{pd.Timestamp(d).date()}.json"
        if not fpath.exists():
            continue
        jj = json.load(open(fpath))
        for r in x.itertuples():
            if r.sym in jj:
                tt = day_table(jj[r.sym])
                pr = tt[tt.index < pd.Timestamp(r.d0)].tail(5)
                pb[(r.ticker, pd.Timestamp(d))] = float(pr.band.median()) if len(pr) else np.nan
    m["pband"] = [pb.get((a, pd.Timestamp(c)), np.nan) for a, c in zip(m.t, m.d)]
    # days since the previous ex-date (any Sharadar dividend action; ex-dates are announced in advance)
    a = pd.read_parquet(SHARADAR / "actions.parquet", columns=["date", "action", "ticker"])
    a = a[(a.action == "dividend") & a.ticker.isin(set(m.t))].copy(); a["date"] = pd.to_datetime(a.date)
    a = a.drop_duplicates(["ticker", "date"]).sort_values(["ticker", "date"])
    a["prev"] = a.groupby("ticker").date.shift(1)
    m = m.merge(a[["ticker", "date", "prev"]].rename(columns={"ticker": "t", "date": "d"}), on=["t", "d"], how="left")
    m["dsl"] = (m.d - m.prev).dt.days.astype(float)
    tk = pd.read_parquet(SHARADAR / "tickers.parquet", columns=["table", "ticker", "sector"])
    sec = tk[tk.table == "SEP"].drop_duplicates("ticker", keep="last").set_index("ticker").sector
    sc = m.t.map(sec).fillna("")
    m["s_fin"] = (sc == "Financial Services").astype(float)
    m["s_re"] = (sc == "Real Estate").astype(float)
    m["s_util"] = (sc == "Utilities").astype(float)
    m["yld"] = m["div"] / m.pc * 1e4                 # bp of prior close
    m["ldv"] = np.log(m.dv)
    m["ldiv"] = np.log(m["div"])
    m["cost"] = np.where(m.auc, 10e-4, 20e-4)
    m["r"] = m.cc - m.cost
    m["ed"] = pd.to_datetime(m.d0)
    m["xd"] = pd.to_datetime(m.d)
    return m


def pref_dollars(j: pd.DataFrame, s: np.ndarray) -> str:
    """$ per entry date at $10k, pref_noauc.dollars convention: min(5% of ex-ante cross $, share of $10k), whole shares."""
    j = j.assign(s=s)
    eq, sz = [], []
    for _, g in j.groupby("ed"):
        cap = ACCT / len(g)
        e_, z_ = 0.0, 0.0
        for r in g.itertuples():
            if not np.isfinite(r.xa):
                continue
            e_ += np.floor(min(PART * r.xa, cap) / r.c0) * r.c0 * r.r
            z_ += np.floor(min(PART * r.xa, r.s * cap) / r.c0) * r.c0 * r.r
        eq.append(e_); sz.append(z_)
    eq, sz = np.array(eq), np.array(sz)
    return (f"$ per entry date at $10k (5% of cross cap, whole shares): equal ${eq.mean():.2f}, sized ${sz.mean():.2f}, "
            f"diff ${sz.mean() - eq.mean():+.2f} (x {len(eq) / ((j.ed.max() - j.ed.min()).days / 365.25):.0f} dates/yr "
            f"= ${(sz.mean() - eq.mean()) * len(eq) / ((j.ed.max() - j.ed.min()).days / 365.25):+.0f}/yr)")


# ---------------------------------------------------------------- CEF
def cef_frame() -> pd.DataFrame:
    tr = pd.read_csv(CEF / "cef_stress_trades.csv", parse_dates=["edate", "xdate"])
    F = cef_features(tr)
    D = pd.concat([tr, F.drop(columns=["ticker", "edate"])], axis=1)
    D["cat"] = D["cat"].fillna("equity")
    # spread proxy: 20-session median (high - low) / close up to the signal Friday (entry is the NEXT close)
    f = pd.read_parquet(SHARADAR / "funds.parquet", columns=["ticker", "date", "high", "low", "close"],
                        filters=[("ticker", "in", sorted(tr.ticker.unique()))])
    f["date"] = pd.to_datetime(f.date); f = f.drop_duplicates(["ticker", "date"]).sort_values(["ticker", "date"])
    f["hl"] = ((f.high - f.low) / f.close).where(f.close > 0)
    f["hl20"] = f.groupby("ticker").hl.transform(lambda v: v.rolling(20, min_periods=10).median())
    D = D.sort_values("edate").reset_index(drop=True)
    D = pd.merge_asof(D, f[["date", "ticker", "hl20"]].rename(columns={"date": "edate"}).sort_values("edate"),
                      on="edate", by="ticker", direction="backward")
    D["hl20"] *= 1e4
    D = D.sort_values(["ticker", "edate"]).reset_index(drop=True)
    D["dsl"] = (D.edate - D.groupby("ticker").edate.shift(1)).dt.days.astype(float)
    for c in ("muni", "pref_conv", "sector", "taxable_fi", "intl"):
        D["c_" + c] = (D.cat == c).astype(float)
    D["r"] = D.ret - 0.005
    D["ed"], D["xd"] = D.edate, D.xdate
    return D


def main() -> int:
    t0 = time.time()
    say("EXP round 3 R3-PREF (N 1230) / R3-CEF (N 1231): ridge per-event size tilt vs equal size. Pre-reg round1_prose.md "
        "'EXP round 3'. sign: + = sizing beat equal size.")
    say("")
    say("== R3-PREF (N 1230): PREF-EX CC window (live form), cost 10bp RT auction / 20bp no-auction ==")
    P = pref_frame()
    pc = ["yld", "ldv", "pband", "ldiv", "dsl", "s_fin", "s_re", "s_util"]
    say("features: yld (div/prior close, bp), ldv (log Sharadar 20d median $vol, shifted), pband (median M-print band, 5 "
        "sessions before T-1, bp), ldiv (log $ dividend), dsl (days since previous ex-date), sector dummies fin/re/util")
    fitm = ((P.ed >= "2021-01-01") & (P.xd <= "2023-12-31")).to_numpy()
    judm = ((P.ed >= "2024-01-01") & (P.ed <= "2026-10-31")).to_numpy()
    run("R3-PREF", P, pc, fitm, judm, pd.Timestamp("2025-06-01"), pref_dollars)
    say(f"[pref done {time.time() - t0:.0f}s]")
    say("")
    say("== R3-CEF (N 1231): CEF-RV trades (frozen rule, Nasdaq NAV panel, cef_stress_trades.csv), net of 50bp RT ==")
    C = cef_frame()
    cc = ["yld", "ladv", "hl20", "dz", "dsl", "c_muni", "c_pref_conv", "c_sector", "c_taxable_fi", "c_intl"]
    say("features: yld, ladv, dz (CEF-ML builder, identical definitions), hl20 (20d median high-low range, bp; new), dsl (days "
        "since the fund's previous CEF-RV entry; new), category dummies (cef_peer.category, as CEF-ML; equity base)")
    fitm = ((C.ed < "2016-01-01") & (C.xd < "2016-01-01")).to_numpy()
    judm = (C.ed >= "2016-01-01").to_numpy()

    def cef_dollars(j, s):
        x = pd.Series(tilt(j.r.to_numpy(), s)).groupby(j.ed.to_numpy()).mean()
        return (f"$ per entry date at $10k (NOTIONAL: full $10k per entry date, overlapping holds and capacity ignored): "
                f"diff ${x.mean() * 1e4:+.2f}")
    run("R3-CEF", C, cc, fitm, judm, pd.Timestamp("2021-01-01"), cef_dollars)
    say("")
    for k, v in verdict.items():
        say(f"VERDICT {k}: {'PASS' if v else 'FAIL -> KILL'}")
    say(f"runtime {time.time() - t0:.0f}s")
    OUT.write_text("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
