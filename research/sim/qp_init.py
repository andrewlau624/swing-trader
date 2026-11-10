"""QP-INIT (N 1200): IPO research quiet-period expiry, a 2-session hold over the initiation date.

Pre-registration: research/drafts/round1_prose.md "Study QP-INIT". Data: Sharadar SEP/actions/tickers, ~/data/sharadar.
Usage: python research/sim/qp_init.py --events   (event counts only, no returns read)
       python research/sim/qp_init.py            (the one judged run)
"""
import math
import pathlib
import sys

import numpy as np
import pandas as pd
import scipy.stats as SS

S = pathlib.Path.home() / "data" / "sharadar"
OUT = pathlib.Path(__file__).resolve().parents[2] / "data" / "research" / "program" / "qp_init_out.txt"
N_PROGRAM = 1207   # program N at registration (other agent used 1205-1207); this study is N 1200
REG40 = (pd.Timestamp("2002-08-01"), pd.Timestamp("2012-04-04"))   # NASD 2711 40-day quiet period
JOBS = pd.Timestamp("2012-04-05")                                   # JOBS Act; 25-day convention after
JUDGE_START, JUDGE_END = pd.Timestamp("2002-08-01"), pd.Timestamp("2026-10-05")
LINES = []


def P(s=""):
    print(s)
    LINES.append(str(s))


def K_of(f):
    if REG40[0] <= f <= REG40[1]:
        return 40
    return 25


def load():
    tk = pd.read_parquet(S / "tickers.parquet")
    tk = tk[tk.table == "SEP"]
    cats = tk.category.fillna("")
    tk = tk[cats.str.startswith("Domestic Common") | cats.str.startswith("ADR Common")]
    a = pd.read_parquet(S / "actions.parquet")
    a["date"] = pd.to_datetime(a.date)
    lst = a[a.action == "listed"][["ticker", "date"]].rename(columns={"date": "L"})
    lst = lst.merge(tk[["ticker", "category", "siccode", "name", "firstpricedate"]], on="ticker")
    lst["fpd"] = pd.to_datetime(lst.firstpricedate)
    lst = lst[(lst.fpd - lst.L).abs() <= pd.Timedelta(days=3)]
    spac_t = set(a[a.action.isin(["spacmerger", "spacunitseparation"])].ticker) | set(
        a[a.action.isin(["spacmerger", "spacunitseparation"])].contraticker.dropna())
    lst = lst[~lst.ticker.isin(spac_t) & (lst.siccode != 6770)]
    lst = lst[~lst.name.fillna("").str.upper().str.contains("ACQUISITION")]
    sp = a[a.action.isin(["spunofffrom", "spinoff", "spinoffdividend"])]
    sp_rows = pd.concat([sp[["ticker", "date"]], sp[["contraticker", "date"]].rename(columns={"contraticker": "ticker"})])
    m = lst.merge(sp_rows, on="ticker", how="left", suffixes=("", "_sp"))
    bad = m[(m.date - m.L).abs() <= pd.Timedelta(days=30)].ticker
    lst = lst[~lst.ticker.isin(set(bad))].drop_duplicates("ticker")
    return lst


def panel(tickers):
    st = pd.read_parquet(S / "stocks.parquet", columns=["ticker", "date", "close", "closeadj", "closeunadj", "volume"],
                         filters=[("ticker", "in", list(tickers) + ["SPY", "QQQ"])])
    fu = pd.read_parquet(S / "funds.parquet", columns=["ticker", "date", "closeadj"],
                         filters=[("ticker", "in", ["SPY", "QQQ"])])
    st["date"] = pd.to_datetime(st.date)
    fu["date"] = pd.to_datetime(fu.date)
    return st, fu


def build_events(lst, st):
    rows = []
    g = {k: v.sort_values("date").reset_index(drop=True) for k, v in st.groupby("ticker")}
    for r in lst.itertuples():
        d = g.get(r.ticker)
        if d is None or len(d) < 5:
            continue
        F = d.date.iloc[0]
        if abs((F - r.L).days) > 3:
            continue
        d1 = d.iloc[0]
        if d1.closeunadj < 5 or d1.closeunadj * d1.volume < 5e6:
            continue
        # pinned-at-$10 SPAC-like listings: first 20 closes almost constant
        c20 = d.closeunadj.iloc[:20]
        if c20.std() / c20.mean() < 0.01:
            continue
        rows.append((r.ticker, F, r.category))
    ev = pd.DataFrame(rows, columns=["ticker", "F", "category"])
    ev["K"] = ev.F.map(K_of)
    return ev, g


def window(d, F, K, lo_off, hi_off):
    """entry = last session <= F+K+lo_off days; exit = first session >= F+K+hi_off days."""
    e_lim, x_lim = F + pd.Timedelta(days=K + lo_off), F + pd.Timedelta(days=K + hi_off)
    ie = d.index[d.date <= e_lim]
    ix = d.index[d.date >= x_lim]
    if len(ie) == 0 or ie[-1] < 1:
        return None
    e = ie[-1]
    x = ix[0] if len(ix) else d.index[-1]          # delisted before exit: last close
    if x <= e:
        return None
    return e, x


def event_returns(ev, g, K_col="K", lo_off=-2, hi_off=0):
    out = []
    for r in ev.itertuples():
        d = g[r.ticker]
        K = getattr(r, K_col)
        w = window(d, r.F, K, lo_off, hi_off)
        if w is None:
            continue
        e, x = w
        de = d.loc[e]
        dv = (d.closeunadj * d.volume).iloc[1:e + 1].median()
        if de.closeunadj < 3 or not (dv >= 2e6):
            continue
        out.append((r.ticker, r.F, K, de.date, d.loc[x, "date"], d.loc[x, "closeadj"] / de.closeadj - 1,
                    de.closeunadj, dv, e))
    return pd.DataFrame(out, columns=["ticker", "F", "K", "de", "dx", "ret", "px", "adv", "age"])


_M = {}


def cohort_control(R, g, ev):
    """EW same-window return of other listings (event universe) aged 60-250 sessions on the entry date."""
    if not _M:
        ts = [t for t in ev.ticker.unique() if t in g]
        W = pd.concat({t: g[t].set_index("date").closeadj for t in ts}, axis=1).sort_index()
        first = pd.Series({t: g[t].date.iloc[0] for t in ts})
        pos = pd.Series(np.arange(len(W)), index=W.index)
        _M.update(W=W.values.astype(np.float64), idx=pos, cols=list(W.columns),
                  f0=pos.reindex(first.values, method="bfill").values)
    W, pos, cols, f0 = _M["W"], _M["idx"], _M["cols"], _M["f0"]
    cix = {t: i for i, t in enumerate(cols)}
    cache, ctl, nct = {}, [], []
    for r in R.itertuples():
        key = (r.de, r.dx, r.ticker)
        ie, ix = pos.get(r.de), pos.get(r.dx)
        if ie is None or ix is None:
            ctl.append(np.nan); nct.append(0); continue
        age = ie - f0
        m = (age >= 60) & (age <= 250)
        if r.ticker in cix:
            m[cix[r.ticker]] = False
        v = W[ix, m] / W[ie, m] - 1
        v = v[np.isfinite(v)]
        ctl.append(v.mean() if len(v) >= 5 else np.nan); nct.append(len(v))
    R["ctl"] = ctl
    R["nctl"] = nct
    return R


def bench(R, fu):
    for b in ("SPY", "QQQ"):
        c = fu[fu.ticker == b].set_index("date").closeadj
        R[b] = [c.get(x, np.nan) / c.get(e, np.nan) - 1 for e, x in zip(R.de, R.dx)]
    return R


def cost(R, mult=1.0):
    side = np.where((R.px >= 10) & (R.adv >= 1e7), 0.0005, 0.0010)
    return 2 * side * mult


def day_t(x, dates):
    df = pd.DataFrame({"x": x, "d": dates}).dropna()
    m = df.x.mean()
    gsum = df.groupby("d").x.apply(lambda s: (s - m).sum())
    n = len(df)
    se = math.sqrt((gsum ** 2).sum()) / n
    return m / se if se > 0 else float("nan")


def dsr(x, n_trials):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    T = len(x)
    sr = x.mean() / x.std(ddof=1)
    sk = SS.skew(x); ku = SS.kurtosis(x, fisher=False)
    g = 0.5772156649
    sr0 = math.sqrt(1.0 / T) * ((1 - g) * SS.norm.ppf(1 - 1 / n_trials) + g * SS.norm.ppf(1 - 1 / (n_trials * math.e)))
    z = (sr - sr0) * math.sqrt(T - 1) / math.sqrt(max(1e-12, 1 - sk * sr + (ku - 1) / 4 * sr ** 2))
    return float(SS.norm.cdf(z))


def summ(name, x, dates):
    x = pd.Series(x).dropna()
    if len(x) < 5:
        P(f"  {name:34s} n {len(x)}")
        return
    srt = x.sort_values()
    P(f"  {name:34s} n {len(x):4d} mean {x.mean()*1e4:+7.1f}bp med {x.median()*1e4:+7.1f} hit {100*(x>0).mean():4.1f}% "
      f"t_day {day_t(x.values, dates.loc[x.index].values):+5.2f} ex-top5 {srt.iloc[:-5].mean()*1e4:+7.1f}")


def main():
    lst = load()
    st, fu = panel(lst.ticker.unique())
    ev, g = build_events(lst, st)
    ev = ev[ev.F >= pd.Timestamp("1998-01-15")]
    P("QP-INIT (N 1200) IPO quiet-period expiry; Sharadar SEP; run " + pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"))
    P(f"events after universe filters: {len(ev)}; by first-trade year:")
    P("  " + " ".join(f"{y}:{n}" for y, n in ev.groupby(ev.F.dt.year).size().items()))
    if "--events" in sys.argv:
        print("\n".join(LINES))
        return
    R = event_returns(ev, g)
    R = bench(cohort_control(R, g, ev), fu)
    R["c1"] = cost(R)
    R["xs"] = R.ret - R.ctl - R.c1
    R["raw_net"] = R.ret - R.c1
    R["xs_spy"] = R.ret - R.SPY - R.c1
    J = R[(R.de >= JUDGE_START) & (R.de <= JUDGE_END)].copy()
    pre = R[R.F < REG40[0]]
    P(f"\nwindow: close(last session <= F+K-2d) -> close(first session >= F+K); judged events {len(J)} "
      f"({len(J)/((JUDGE_END-JUDGE_START).days/365.25):.0f}/yr); median sessions held "
      f"{(J.dx - J.de).dt.days.median():.0f} cal days")
    P("\nPRIMARY (judge 2002-08..2026-10): net excess vs IPO cohort (age 60-250 sessions), base cost")
    summ("net excess vs cohort", J.xs, J.de)
    summ("net raw", J.raw_net, J.de)
    summ("net excess vs SPY", J.xs_spy, J.de)
    for m in (2, 3):
        summ(f"net excess, {m}x cost", J.ret - J.ctl - cost(J, m), J.de)
    P("regimes (halves):")
    summ("K=40 regime 2002-08..2012-04", J[J.K == 40].xs, J.de)
    summ("K=25 regime 2012-04..2026", J[J.K == 25].xs, J.de)
    summ("K=25 2012-2018", J[(J.K == 25) & (J.de < "2019-01-01")].xs, J.de)
    summ("K=25 2019-2026", J[(J.K == 25) & (J.de >= "2019-01-01")].xs, J.de)
    P("reported, not judged: 1998-2002-07 (BJR-era convention K=25):")
    summ("pre-2002-08 K=25", pre.xs, pre.de)
    # placebo 1: regime swap
    ev2 = ev.copy()
    ev2["K"] = np.where(ev2.K == 40, 25, 40)
    Q = event_returns(ev2, g)
    Q = cohort_control(Q, g, ev2)
    Q["xs"] = Q.ret - Q.ctl - cost(Q)
    Qj = Q[(Q.de >= JUDGE_START) & (Q.de <= JUDGE_END)]
    P("\nPLACEBO A (regime swap: K=25 in the 40-day era, K=40 in the 25-day era):")
    summ("swap K", Qj.xs, Qj.de)
    summ("swap K, 40-era (K=25)", Qj[Qj.K == 25].xs, Qj.de)
    summ("swap K, 25-era (K=40)", Qj[Qj.K == 40].xs, Qj.de)
    # placebo 2: random fixed offsets
    rng_means = []
    for K2 in range(15, 61):
        ev3 = ev.copy()
        if any(abs(K2 - k) <= 3 for k in (25, 40)):
            continue
        ev3["K"] = K2
        Z = event_returns(ev3, g)
        Z = Z[(Z.de >= JUDGE_START) & (Z.de <= JUDGE_END)]
        Z = cohort_control(Z, g, ev3)
        rng_means.append((K2, (Z.ret - Z.ctl - cost(Z)).mean()))
    pm = np.array([m for _, m in rng_means])
    P(f"PLACEBO B (fixed K' in 15..60 excluding 22-28, 37-43; {len(pm)} offsets): mean excess "
      f"5th/50th/95th pct {np.nanpercentile(pm,5)*1e4:+.1f}/{np.nanpercentile(pm,50)*1e4:+.1f}/{np.nanpercentile(pm,95)*1e4:+.1f}bp; "
      f"primary rank {(pm < J.xs.mean()).mean()*100:.0f}th pct")
    P("  " + " ".join(f"{k}:{m*1e4:+.0f}" for k, m in rng_means))
    # beta / alpha
    P("\nBETA: event raw return on same-window SPY / QQQ (OLS, per event)")
    for b in ("SPY", "QQQ"):
        X = J[["ret", b]].dropna()
        res = SS.linregress(X[b], X.ret - J.loc[X.index, "c1"])
        tt = res.intercept / (res.intercept_stderr or np.nan)
        P(f"  vs {b}: beta {res.slope:+.2f} alpha {res.intercept*1e4:+.1f}bp/event t {tt:+.2f}")
    d = dsr(J.xs.values, N_PROGRAM)
    P(f"\nDSR (per-event net excess, N {N_PROGRAM}): {d:.3f}")
    # event-time profile (descriptive)
    P("\nDESCRIPTIVE event-time profile (judge sample, 1-session close->close excess vs cohort, sessions rel. to first >= F+K):")
    prof = []
    for off in range(-6, 5):
        vals = []
        for r in J.itertuples():
            d0 = g[r.ticker]
            ix = d0.index[d0.date >= r.F + pd.Timedelta(days=int(r.K))]
            if not len(ix):
                continue
            i = ix[0] + off
            if i < 1 or i >= len(d0):
                continue
            vals.append(d0.closeadj.iloc[i] / d0.closeadj.iloc[i - 1] - 1)
        prof.append((off, np.mean(vals), np.median(vals), len(vals)))
    P("  " + " | ".join(f"{o:+d}: {m*1e4:+.0f}/{md*1e4:+.0f}" for o, m, md, n in prof) + "  (mean/median bp, raw)")
    yrs = (JUDGE_END - JUDGE_START).days / 365.25
    n_yr = len(J) / yrs
    for share in (1.0, 0.5):
        P(f"ceiling at share {share:.0%}: {n_yr:.0f}/yr x {J.xs.mean()*1e4:+.1f}bp x {share} x 50% = "
          f"{n_yr * J.xs.mean() * share * 0.5 * 100:+.1f}pp/yr")
    J.to_parquet(OUT.with_suffix(".parquet"))
    OUT.write_text("\n".join(LINES) + "\n")


if __name__ == "__main__":
    main()
