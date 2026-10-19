"""Study REV-TONE (N 1008): Amazon review tone vs sales acceleration, EA reaction, and a tradable hold to EA+1.

Pre-registered in research/drafts/round1_prose.md. Input data/research/reviews/scored.parquet (rev_tone_build/).
Output data/research/program/rev_tone_out.txt and data/research/reviews/{firm_month,firm_quarter}.parquet.
"""
from pathlib import Path
import numpy as np, pandas as pd
from sharadar import prices, table

ROOT = Path(__file__).resolve().parents[2]
REV = ROOT / "data/research/reviews"
OUT = ROOT / "data/research/program/rev_tone_out.txt"
COST = 0.0010  # per side
JUDGE = ("2019-01-01", "2023-06-30")
PAPER = ("2014-01-01", "2018-12-31")
lines = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    lines.append(s)


def firm_month(sc):
    sc["neg"] = sc.tone < -0.5
    g = sc.groupby(["tk", "ym"])
    fm = g.agg(tone=("tone", "mean"), neg=("neg", "mean"), rating=("rating", "mean"), n_sc=("tone", "size"),
               n_all=("n_all", "first"), **{c: (c, "mean") for c in sc.columns if c.startswith("tag_")}).reset_index()
    fm["mend"] = pd.PeriodIndex(fm.ym, freq="M").to_timestamp(how="end").normalize()
    return fm


def firm_quarter(fm):
    f = table("fundamentals", columns=["ticker", "dimension", "calendardate", "reportperiod", "revenue"],
              filters=[("ticker", "in", sorted(fm.tk.unique())), ("dimension", "=", "ARQ")])
    f = f.rename(columns={"ticker": "tk"}).sort_values(["tk", "reportperiod"]).drop_duplicates(["tk", "reportperiod"])
    f["reportperiod"], f["calendardate"] = pd.to_datetime(f.reportperiod), pd.to_datetime(f.calendardate)
    f["prev_rp"] = f.groupby("tk").reportperiod.shift(1)
    out = []
    for r in f.itertuples():
        d = dict(tk=r.tk, rp=r.reportperiod, cq=r.calendardate, revenue=r.revenue, n_sc=0, n_all=np.nan,
                 tone=np.nan, neg=np.nan, rating=np.nan)
        m = fm[(fm.tk == r.tk) & (fm.mend > r.prev_rp) & (fm.mend <= r.reportperiod + pd.Timedelta(days=3))] \
            if pd.notna(r.prev_rp) else fm.iloc[:0]
        if len(m):
            w = m.n_sc
            d.update(n_sc=w.sum(), n_all=m.n_all.sum(), tone=np.average(m.tone, weights=w),
                     neg=np.average(m.neg, weights=w), rating=np.average(m.rating, weights=w))
        out.append(d)
    q = pd.DataFrame(out).sort_values(["tk", "rp"]).reset_index(drop=True)
    g = q.groupby("tk")
    lr = np.log(q.revenue.where(q.revenue > 0))
    q["yoy"] = lr - g.revenue.shift(4).pipe(lambda s: np.log(s.where(s > 0)))
    q["acc"] = q.yoy - q.groupby("tk").yoy.shift(1)
    for c in ["tone", "neg", "rating"]:
        q["d_" + c] = q[c] - g[c].shift(4)
    q["d_logn"] = np.log(q.n_all) - np.log(g.n_all.shift(4))
    q["ok"] = (q.n_sc >= 100) & (g.n_sc.shift(4) >= 100)
    return q


def add_market(q):
    ev = table("events", filters=[("ticker", "in", sorted(q.tk.unique()))])
    ev = ev[ev.eventcodes.astype(str).str.split("|").apply(lambda c: "22" in c)].copy()
    ev["date"] = pd.to_datetime(ev.date)
    px = prices(sorted(q.tk.unique()) + ["SPY"], start="2012-01-01", end="2024-03-31", adjust="split")
    px["date"] = pd.to_datetime(px.date)
    r = px.pivot(index="date", columns="ticker", values="closeadj").pct_change()
    dates = r.index
    ea, car, hold, beta_l, entry_l = [], [], [], [], []
    for row in q.itertuples():
        e = ev[(ev.ticker == row.tk) & (ev.date > row.rp) & (ev.date <= row.rp + pd.Timedelta(days=100))].date.min()
        ea.append(e)
        if pd.isna(e) or row.tk not in r:
            car.append(np.nan); hold.append(np.nan); beta_l.append(np.nan); entry_l.append(pd.NaT); continue
        ie = dates.searchsorted(e)
        ri, rm = r[row.tk], r["SPY"]
        car.append((ri.iloc[ie - 1:ie + 2] - rm.iloc[ie - 1:ie + 2]).sum() if ie + 2 <= len(dates) else np.nan)
        i0 = dates.searchsorted(row.rp, side="right")  # first session after the quarter end: entry at its close
        win = slice(max(0, i0 - 252), i0)
        x, y = rm.iloc[win], ri.iloc[win]
        okm = x.notna() & y.notna()
        b = np.cov(y[okm], x[okm])[0, 1] / x[okm].var() if okm.sum() > 100 else np.nan
        hs = slice(i0 + 1, ie + 2)  # returns from entry close to EA+1 close
        hold.append(((1 + ri.iloc[hs]).prod() - 1) - b * ((1 + rm.iloc[hs]).prod() - 1) if ie + 2 <= len(dates) and ie > i0 else np.nan)
        beta_l.append(b); entry_l.append(dates[i0] if i0 < len(dates) else pd.NaT)
    q["ea"], q["car"], q["hold"], q["beta"], q["entry"] = ea, car, hold, beta_l, entry_l
    return q


def ols(d, y, xs):
    """OLS on standardized regressors, quarter-clustered SEs. Returns (coef, t, n) dicts; coef in units of y per 1 sd."""
    d = d.dropna(subset=[y] + xs)
    if len(d) < 30:
        return None
    X = np.column_stack([np.ones(len(d))] + [((d[x] - d[x].mean()) / d[x].std()).values for x in xs])
    Y = d[y].values
    XtXi = np.linalg.inv(X.T @ X)
    b = XtXi @ X.T @ Y
    e = Y - X @ b
    meat = sum(np.outer(X[g].T @ e[g], X[g].T @ e[g]) for g in d.groupby("cq").indices.values())
    G = d.cq.nunique()
    V = XtXi @ meat @ XtXi * G / (G - 1)
    t = b / np.sqrt(np.diag(V))
    return dict(zip(xs, b[1:])), dict(zip(xs, t[1:])), len(d)


def tstat(x):
    x = pd.Series(x).dropna()
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 else np.nan


def window(q, lo, hi, label):
    d = q[q.ok & (q.cq >= lo) & (q.cq <= hi)].copy()
    say(f"\n=== {label} {lo[:7]}..{hi[:7]}: firm-quarters {len(d)}, firms {d.tk.nunique()}")
    for y in ["acc", "car"]:
        for xs in (["d_tone"], ["d_tone", "d_rating", "d_logn"], ["d_neg", "d_rating", "d_logn"]):
            res = ols(d, y, xs)
            if res:
                b, t, n = res
                say(f"  {y:4s} ~ {' + '.join(xs):28s} n {n:4d}  " +
                    "  ".join(f"{x} {b[x]*1e4:+7.1f}bp t {t[x]:+.2f}" for x in xs))
    # H3 terciles within calendar quarter
    d = d.dropna(subset=["hold"])
    d["terc"] = d.groupby("cq").d_tone.transform(lambda s: pd.qcut(s.rank(method="first"), 3, labels=False) if len(s) >= 6 else np.nan)
    d = d.dropna(subset=["terc"])
    by = d.groupby(["cq", "terc"]).hold.mean().unstack().reindex(columns=[0.0, 1.0, 2.0])
    if by.notna().all(axis=1).sum() < 4:
        say("  H3: too few quarters with >= 6 firms"); return None
    spread = (by[2] - by[0]).dropna()
    net = spread - 4 * COST
    say(f"  H3 hold rp+1 -> EA+1 (beta-adj), {len(spread)} quarters: bottom {d[d.terc==0].hold.mean()*1e4:+.0f}bp "
        f"(median {d[d.terc==0].hold.median()*1e4:+.0f}, n {int((d.terc==0).sum())})  mid {d[d.terc==1].hold.mean()*1e4:+.0f}  "
        f"top {d[d.terc==2].hold.mean()*1e4:+.0f}bp")
    say(f"  top-bottom gross {spread.mean()*1e4:+.0f}bp t {tstat(spread):+.2f}; net {net.mean()*1e4:+.0f}bp t {tstat(net):+.2f}; "
        f"ex-top-5 quarters {net.sort_values().iloc[:-5].mean()*1e4:+.0f}bp; median {net.median()*1e4:+.0f}; "
        f"hit {(net > 0).mean():.0%}")
    short = -(by[0]) - 2 * COST
    say(f"  short-bottom-only net {short.mean()*1e4:+.0f}bp t {tstat(short):+.2f}")
    mid = spread.index[len(spread) // 2]
    say(f"  halves: {net[net.index < mid].mean()*1e4:+.0f}bp / {net[net.index >= mid].mean()*1e4:+.0f}bp")
    b = d[d.terc == 0]
    say(f"  'always' check (bottom-tercile dTONE vs all): P(acc<0) {(b.acc<0).mean():.0%} vs {(d.acc<0).mean():.0%}; "
        f"P(car<0) {(b.car<0).mean():.0%} vs {(d.car<0).mean():.0%}; P(hold<0) {(b.hold<0).mean():.0%} vs {(d.hold<0).mean():.0%}")
    return net


def main():
    sc = pd.read_parquet(REV / "scored.parquet")
    say(f"REV-TONE (N 1008). scored reviews {len(sc):,}, firms {sc.tk.nunique()}, {sc.ym.min()}..{sc.ym.max()}")
    say("reviews scored per firm:", sc.tk.value_counts().to_dict())
    fm = firm_month(sc)
    fm.to_parquet(REV / "firm_month.parquet")
    q = add_market(firm_quarter(fm))
    q.to_parquet(REV / "firm_quarter.parquet")
    window(q, *PAPER, "PAPER ERA")
    net = window(q, *JUDGE, "JUDGE")
    say("\nper-firm corr(d_tone, acc) / corr(d_tone, car), judge+paper, ok quarters:")
    for tk, d in q[q.ok].groupby("tk"):
        say(f"  {tk:5s} n {len(d):3d}  acc {d.d_tone.corr(d.acc):+.2f}  car {d.d_tone.corr(d.car):+.2f}  hold {d.d_tone.corr(d.hold):+.2f}")
    say("\nNKE quarterly (fiscal), tone / d_tone / yoy rev / EA CAR / hold:")
    for r in q[(q.tk == "NKE") & (q.rp >= "2019-01-01")].itertuples():
        say(f"  {r.rp.date()} n {r.n_all:6.0f} tone {r.tone:+.3f} d {r.d_tone:+.3f} neg {r.neg:.2f} yoy {r.yoy:+.3f} "
            f"car {r.car:+.3f} hold {r.hold:+.3f}")
    OUT.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
