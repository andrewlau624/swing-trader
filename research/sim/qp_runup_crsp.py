"""QP-RUNUP-CRSP (N 1202): IPO pre-quiet-period-expiry run-up on CRSP 1989-1995 (unseen period).

Pre-registration: research/drafts/round1_prose.md "Study QP-RUNUP-CRSP". Rule identical to QP-RUNUP (N 1201, qp_init.py --runup).
Pull is cached to data/research/qp_crsp/. Usage: python research/sim/qp_runup_crsp.py [--pull]
"""
import math
import pathlib
import sys

import numpy as np
import pandas as pd
import scipy.stats as SS

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data" / "research" / "qp_crsp"
OUT = ROOT / "data" / "research" / "program" / "qp_runup_crsp_out.txt"
N_PROGRAM = 1207
LINES = []


def P(s=""):
    print(s)
    LINES.append(str(s))


def pull():
    import wrds
    D.mkdir(parents=True, exist_ok=True)
    db = wrds.Connection(wrds_username="andrewlau624", wrds_connect_attempts=2)
    first = db.raw_sql("""
        select permno, min(date) as f from crsp.dsf where prc is not null group by permno
        having min(date) between '1985-01-01' and '1995-12-31'""", date_cols=["f"])
    first.to_parquet(D / "first.parquet")
    pl = ",".join(str(int(p)) for p in first.permno)
    dsf = db.raw_sql(f"""
        select d.permno, d.date, d.prc, d.vol, d.ret from crsp.dsf d
        join (select permno, min(date) as f from crsp.dsf where prc is not null and permno in ({pl}) group by permno) f
          on d.permno = f.permno
        where d.date >= f.f and d.date <= f.f + 420""", date_cols=["date"])
    dsf.to_parquet(D / "dsf.parquet")
    nm = db.raw_sql(f"select permno, namedt, nameendt, shrcd, exchcd from crsp.dsenames where permno in ({pl})",
                    date_cols=["namedt", "nameendt"])
    nm.to_parquet(D / "names.parquet")
    de = db.raw_sql(f"select permno, distcd, exdt, acperm from crsp.dsedist where acperm in ({pl})", date_cols=["exdt"])
    de.to_parquet(D / "dist.parquet")
    dsi = db.raw_sql("select date, vwretd, ewretd from crsp.dsi where date between '1985-01-01' and '1997-12-31'",
                     date_cols=["date"])
    dsi.to_parquet(D / "dsi.parquet")
    print("pulled", len(first), len(dsf))


def day_t(x, dates):
    df = pd.DataFrame({"x": np.asarray(x), "d": np.asarray(dates)}).dropna()
    m = df.x.mean()
    gs = df.groupby("d").x.apply(lambda s: (s - m).sum())
    se = math.sqrt((gs ** 2).sum()) / len(df)
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
    s = x.sort_values()
    P(f"  {name:34s} n {len(x):4d} mean {x.mean()*1e4:+7.1f}bp med {x.median()*1e4:+7.1f} hit {100*(x>0).mean():4.1f}% "
      f"t_day {day_t(x.values, dates.loc[x.index].values):+5.2f} ex-top5 {s.iloc[:-5].mean()*1e4:+7.1f}")


def main():
    if "--pull" in sys.argv or not (D / "dsf.parquet").exists():
        pull()
    first = pd.read_parquet(D / "first.parquet")
    dsf = pd.read_parquet(D / "dsf.parquet").sort_values(["permno", "date"])
    nm = pd.read_parquet(D / "names.parquet")
    dist = pd.read_parquet(D / "dist.parquet")
    dsi = pd.read_parquet(D / "dsi.parquet").set_index("date")
    dsf["px"] = pd.to_numeric(dsf.prc, errors="coerce").astype(float).abs()
    dsf["dv"] = dsf.px * pd.to_numeric(dsf.vol, errors="coerce").astype(float)
    dsf["ret"] = pd.to_numeric(dsf.ret, errors="coerce")
    g = {p: d.reset_index(drop=True) for p, d in dsf.groupby("permno")}
    P("QP-RUNUP-CRSP (N 1202): IPO run-up x-3 -> x-1, K=25, CRSP; run " + pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"))
    ev = []
    drop = {"no_names": 0, "shr_exch": 0, "spin": 0, "day1": 0}
    for r in first.itertuples():
        d = g.get(r.permno)
        if d is None or len(d) < 10:
            continue
        F = d.date.iloc[0]
        n = nm[(nm.permno == r.permno) & (nm.namedt <= F) & (nm.nameendt >= F)]
        if n.empty:
            drop["no_names"] += 1
            continue
        n = n.iloc[0]
        if int(n.shrcd) not in (10, 11, 12, 18, 31) or int(n.exchcd) not in (1, 2, 3):
            drop["shr_exch"] += 1
            continue
        sp = dist[(dist.acperm == r.permno) & ((dist.exdt - F).abs() <= pd.Timedelta(days=30))]
        if len(sp):
            drop["spin"] += 1
            continue
        if not (d.px.iloc[0] >= 5 and d.dv.iloc[0] >= 5e6):
            drop["day1"] += 1
            continue
        ev.append((r.permno, F))
    ev = pd.DataFrame(ev, columns=["permno", "F"])
    P(f"events (F 1985-1995) after filters: {len(ev)}; dropped {drop}")
    P("  by year: " + " ".join(f"{y}:{k}" for y, k in ev.groupby(ev.F.dt.year).size().items()))
    # calendar + cohort matrix of cumulative returns
    cal = pd.DatetimeIndex(sorted(dsi.index))
    pos = pd.Series(np.arange(len(cal)), index=cal)
    W = np.full((len(cal), len(ev)), np.nan)
    f0 = np.zeros(len(ev), dtype=int)
    for j, r in enumerate(ev.itertuples()):
        d = g[r.permno]
        cr = np.cumprod(1 + d.ret.fillna(0).values)
        ii = pos.reindex(d.date).values
        ok = ~np.isnan(ii)
        W[ii[ok].astype(int), j] = cr[ok]
        f0[j] = pos[d.date.iloc[0]]
    rows = []
    for j, r in enumerate(ev.itertuples()):
        d = g[r.permno]
        for K, tag in ((25, "true"), (40, "placebo40")):
            ix = d.index[d.date >= r.F + pd.Timedelta(days=K)]
            if not len(ix):
                continue
            x = ix[0]
            e, xx = x - 3, x - 1
            if e < 1:
                continue
            adv = d.dv.iloc[1:e + 1].median()
            if not (d.px.iloc[e] >= 3) or not (adv >= 2e6):
                continue
            ret = np.prod(1 + d.ret.iloc[e + 1:xx + 1].fillna(0).values) - 1
            ie, ix2 = pos[d.date.iloc[e]], pos[d.date.iloc[xx]]
            age = ie - f0
            m = (age >= 60) & (age <= 250)
            m[j] = False
            v = W[ix2, m] / W[ie, m] - 1
            v = v[np.isfinite(v)]
            ctl = v.mean() if len(v) >= 5 else np.nan
            mk = np.prod(1 + dsi.vwretd.iloc[ie + 1:ix2 + 1].values) - 1
            side = 0.0005 if (d.px.iloc[e] >= 10 and adv >= 1e7) else 0.0010
            rows.append((r.permno, r.F, tag, d.date.iloc[e], ret, ctl, len(v), mk, 2 * side))
    R = pd.DataFrame(rows, columns=["permno", "F", "tag", "de", "ret", "ctl", "nctl", "mkt", "c1"])
    R["xc"] = R.ret - R.ctl - R.c1
    J = R[(R.tag == "true") & (R.F >= "1989-01-01")].copy()
    pre = R[(R.tag == "true") & (R.F < "1989-01-01")]
    P(f"\nJUDGE (F 1989-01..1995-12, K=25): {len(J)} events ({len(J)/7:.0f}/yr), cohort ctl median n {J.nctl.median():.0f}")
    summ("net excess vs cohort", J.xc, J.de)
    summ("net raw", J.ret - J.c1, J.de)
    summ("net excess vs vwretd", J.ret - J.mkt - J.c1, J.de)
    for k in (2, 3):
        summ(f"net excess, {k}x cost", J.ret - J.ctl - k * J.c1, J.de)
    summ("half F 1989-1992", J[J.F < "1993-01-01"].xc, J.de)
    summ("half F 1993-1995", J[J.F >= "1993-01-01"].xc, J.de)
    X = J.dropna(subset=["ret", "mkt"])
    res = SS.linregress(X.mkt, X.ret - X.c1)
    P(f"  vs vwretd: beta {res.slope:+.2f} alpha {res.intercept*1e4:+.1f}bp/event t {res.intercept/res.intercept_stderr:+.2f}")
    P(f"  DSR (N {N_PROGRAM}, reported): {dsr(J.xc.dropna().values, N_PROGRAM):.3f}")
    Q = R[(R.tag == "placebo40") & (R.F >= "1989-01-01")]
    P("\nREPORTED: K=40 placebo window on the same IPOs; and F 1985-88 (pre-1988-amendment era, K=25 window)")
    summ("placebo K=40", Q.xc, Q.de)
    summ("F 1985-1988 at K=25", pre.xc, pre.de)
    xs = J.xc.dropna()
    gates = {
        "mean>0 & t>=2": xs.mean() > 0 and day_t(xs.values, J.loc[xs.index, "de"].values) >= 2,
        "median>0": xs.median() > 0,
        "ex-top5>0": xs.sort_values().iloc[:-5].mean() > 0,
        "2x cost>0": (J.ret - J.ctl - 2 * J.c1).mean() > 0,
        "halves>0": J[J.F < "1993-01-01"].xc.mean() > 0 and J[J.F >= "1993-01-01"].xc.mean() > 0,
        "alpha t>=2": res.intercept / res.intercept_stderr >= 2,
    }
    P("\nGATES: " + "; ".join(f"{k} {'PASS' if v else 'FAIL'}" for k, v in gates.items()))
    P("VERDICT: " + ("PASS (run-up OOS-confirmed)" if all(gates.values()) else "FAIL"))
    J.to_parquet(OUT.with_suffix(".parquet"))
    OUT.write_text("\n".join(LINES) + "\n")


if __name__ == "__main__":
    main()
