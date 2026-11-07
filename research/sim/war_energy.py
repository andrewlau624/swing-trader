"""Study WAR-ENERGY (N 1113-1114): hold energy for 6 months after a geopolitical oil supply shock begins.
Pre-reg research/drafts/round1_prose.md "Study WAR-ENERGY". Alpha form CEILING-KILLED before data; judged ONLY as a hedge.
One look.

Monthly: Ken French 49-industry VW "Oil" (12-industry "Enrgy" secondary) vs F-F Mkt (Mkt-RF + RF). Entry at the END of the
onset month (ex-ante), hold t+1..t+6. Daily (secondary): XLE/USO/EWC/EWJ vs SPY from Yahoo (regular-hours closes), entry at the
close AFTER the trigger session.

  PYTHONPATH=. python3 -I -m research.sim.war_energy      (run from repo root)
"""
from __future__ import annotations

import io
import pathlib

import numpy as np
import pandas as pd

from research.sim.upro_gate import yahoo

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data/research/war_energy"
OUT = ROOT / "data/research/program/war_energy_out.txt"
L: list[str] = []

CORE = ["1952-04", "1956-10", "1973-10", "1978-11", "1980-09", "1990-08", "2002-12"]
ADD = ["2011-02", "2019-09", "2022-02"]
SLEEVE = 0.10


def P(s=""):
    print(s, flush=True); L.append(s)


def french(name: str) -> pd.DataFrame:
    """First (monthly VW) block of a Ken French CSV, in decimal returns, PeriodIndex M."""
    txt = (D / name).read_text(errors="ignore").splitlines()
    start = next(i for i, l in enumerate(txt) if l.strip().startswith(",") or l.lower().startswith(" ,"))
    rows = [txt[start]]
    for l in txt[start + 1:]:
        if not l.strip() or not l.strip()[:6].isdigit():
            break
        rows.append(l)
    df = pd.read_csv(io.StringIO("\n".join(rows)), index_col=0)
    df.columns = [c.strip() for c in df.columns]
    df.index = pd.PeriodIndex([str(i).strip()[:4] + "-" + str(i).strip()[4:6] for i in df.index], freq="M")
    df = df.apply(pd.to_numeric, errors="coerce")
    return df.where(df > -99) / 100


def monthly():
    ff = french("F-F_Research_Data_Factors.csv")
    i49 = french("49_Industry_Portfolios.csv"); i12 = french("12_Industry_Portfolios.csv")
    m = pd.DataFrame({"mkt": ff["Mkt-RF"] + ff["RF"], "rf": ff["RF"], "oil": i49["Oil"], "enrgy": i12["Enrgy"]}).dropna()
    w = pd.read_csv(D / "WTISPLC.csv", parse_dates=["observation_date"]).set_index("observation_date")["WTISPLC"]
    w.index = w.index.to_period("M")
    m["wti"] = pd.to_numeric(w, errors="coerce").reindex(m.index)
    return m


def window(m, onset: str, h: int, col="oil"):
    t = pd.Period(onset, "M")
    w = m.loc[t + 1:t + h]
    if len(w) < h:
        return None
    acct_e = (1 - SLEEVE) * w.mkt + SLEEVE * w[col]
    acct_b = (1 - SLEEVE) * w.mkt + SLEEVE * w.rf
    def dd(r):
        c = np.r_[1.0, (1 + r).cumprod().values]
        return (c / np.maximum.accumulate(c) - 1).min()
    return dict(onset=onset, ex=(1 + w[col]).prod() - (1 + w.mkt).prod(), en=(1 + w[col]).prod() - 1,
                mk=(1 + w.mkt).prod() - 1, acc_e=(1 + acct_e).prod() - 1, acc_b=(1 + acct_b).prod() - 1,
                dd_e=dd(acct_e), dd_b=dd(acct_b), dd_m=dd(w.mkt),
                corr=np.corrcoef(w[col], w.mkt)[0, 1] if h >= 3 else np.nan,
                wti=(m.wti.get(t + h, np.nan) / m.wti.get(t, np.nan) - 1))


def table(m, evs, h, col="oil", title=""):
    rs = [r for r in (window(m, e, h, col) for e in evs) if r]
    df = pd.DataFrame(rs).set_index("onset")
    P(f"\n== {title} ({col}, {h}m from end of onset month), n={len(df)}")
    P(f"{'onset':8s} {'energy':>8s} {'mkt':>8s} {'excess':>8s} {'WTI':>8s} {'acc+E':>8s} {'acc+B':>8s} {'DD+E':>7s} {'DD+B':>7s} {'DDmkt':>7s} {'corr':>6s}")
    for k, r in df.iterrows():
        P(f"{k:8s} {r.en:+8.1%} {r.mk:+8.1%} {r.ex:+8.1%} {r.wti:+8.1%} {r.acc_e:+8.2%} {r.acc_b:+8.2%} {r.dd_e:+7.2%} {r.dd_b:+7.2%} {r.dd_m:+7.2%} {r["corr"]:+6.2f}")
    ex = df.ex.sort_values()
    P(f"median excess {df.ex.median():+.1%}  mean {df.ex.mean():+.1%}  hit {int((df.ex > 0).sum())}/{len(df)}  "
      f"ex-top-1 median {ex.iloc[:-1].median():+.1%}")
    P(f"hedge: median acct ret +E {df.acc_e.median():+.2%} vs +B {df.acc_b.median():+.2%}; median DD +E {df.dd_e.median():+.2%} "
      f"vs +B {df.dd_b.median():+.2%} (E better DD in {int((df.dd_e > df.dd_b).sum())}/{len(df)})")
    return df


def placebo(m, n, h, obs_med, draws=10000, col="oil", seed=1113):
    rng = np.random.default_rng(seed)
    idx = m.index[(m.index >= pd.Period("1927-01", "M")) & (m.index <= m.index[-1] - h)]
    lr = np.log1p(m[col]) ; lm = np.log1p(m.mkt)
    cs_o = np.r_[0, lr.cumsum().values]; cs_m = np.r_[0, lm.cumsum().values]
    pos = np.array([m.index.get_loc(p) for p in idx])
    ex_all = np.exp(cs_o[pos + 1 + h] - cs_o[pos + 1]) - np.exp(cs_m[pos + 1 + h] - cs_m[pos + 1])
    meds = np.median(rng.choice(ex_all, size=(draws, n)), axis=1)
    P(f"placebo ({draws} draws of {n} random onsets 1927+): random-onset median excess {np.median(ex_all):+.1%}; "
      f"medians p50 {np.percentile(meds,50):+.1%} p90 {np.percentile(meds,90):+.1%}; observed {obs_med:+.1%} "
      f"-> percentile {(meds < obs_med).mean():.0%}")
    return np.percentile(meds, 90)


def price_trigger(m):
    w = m.wti.dropna()
    ch = w / w.shift(3) - 1
    ev, last = [], None
    for p, v in ch.items():
        if v >= 0.25 and (last is None or (p - last).n >= 12):
            ev.append(str(p)); last = p
    return ev


def always_on(m):
    P("\n== Unconditional 10% sleeve, 1927-2026 monthly (account = 90% Mkt + 10% X, monthly rebalanced)")
    mm = m.loc["1927-01":]
    for nm, r in [("100% Mkt", mm.mkt), ("+10% Oil", .9 * mm.mkt + .1 * mm.oil), ("+10% bills", .9 * mm.mkt + .1 * mm.rf)]:
        c = (1 + r).cumprod(); yrs = len(r) / 12
        P(f"{nm:12s} CAGR {c.iloc[-1] ** (1 / yrs) - 1:+.2%}  maxDD {(c / c.cummax() - 1).min():+.1%}")
    P(f"corr(Oil, Mkt) all months {mm.oil.corr(mm.mkt):+.2f}")


def daily_arms():
    P("\n== Daily arms (secondary): trigger = DCOILWTICO +25% over 30 sessions (first day, 252-session refractory), "
      "entry at the next session's close; also CORE/ADD onsets >= 1999 entered at the onset month-end close")
    w = pd.read_csv(D / "DCOILWTICO.csv", parse_dates=["observation_date"]).set_index("observation_date")["DCOILWTICO"]
    w = pd.to_numeric(w, errors="coerce").dropna(); w = w[w > 0]
    ch = w / w.shift(30) - 1
    trig, last = [], None
    for d, v in ch.items():
        if v >= 0.25 and (last is None or (d - last).days >= 365):
            trig.append(d); last = d
    px = {s: yahoo(s, "1993-01-01")["adjclose"] for s in ["SPY", "XLE", "USO", "EWC", "EWJ"]}
    bk = pd.read_parquet(ROOT / "data/research/upro_gate/book.parquet")["r"]
    P(f"daily triggers: {[str(d.date()) for d in trig]}")
    onsets = [(pd.Period(e, 'M').end_time.normalize(), e + "(ev)") for e in CORE + ADD if e >= "1999"]
    rows = []
    for d, lab in [(t, str(t.date())) for t in trig] + onsets:
        r = {"when": lab}
        for h in (63, 126):
            for a, b in [("XLE", "SPY"), ("USO", "SPY"), ("EWC", "EWJ")]:
                pa, pb = px[a], px[b]
                ia = pa.index[pa.index > d]
                if len(ia) < h + 1 or pa.index[0] > d or pb.index[0] > d:
                    r[f"{a}-{b}{h}"] = np.nan; continue
                e0, e1 = ia[0], ia[h]
                r[f"{a}-{b}{h}"] = pa[e1] / pa[e0] - pb[e1] / pb[e0]
        # account proxy = backtest book 1999+; 10% XLE sleeve vs 10% bills (0) over 126 sessions
        i = bk.index[bk.index > d]
        if len(i) > 127 and px["XLE"].index[0] < d:
            s = i[1:127]
            xr = px["XLE"].pct_change().reindex(s).fillna(0)
            def dd(rr):
                c = np.r_[1.0, (1 + rr).cumprod().values]; return (c / np.maximum.accumulate(c) - 1).min()
            be, bb = .9 * bk.reindex(s) + .1 * xr, .9 * bk.reindex(s)
            r.update(bookE=(1 + be).prod() - 1, bookB=(1 + bb).prod() - 1, ddE=dd(be), ddB=dd(bb))
        rows.append(r)
    df = pd.DataFrame(rows).set_index("when")
    pd.set_option("display.width", 250)
    P(df.to_string(float_format=lambda x: f"{x:+.3f}"))
    P("median by column:"); P(df.median(numeric_only=True).to_string(float_format=lambda x: f"{x:+.3f}"))
    return w, px


def now_2026(m, w, px):
    P("\n== 2026 episode (describe only, never judged)")
    s = w.loc["2025-10-01":]
    P(f"WTI daily: 2025-12-31 {w.asof(pd.Timestamp('2025-12-31')):.2f}; 2026 max {s.loc['2026'].max():.2f} on "
      f"{s.loc['2026'].idxmax().date()}; last {s.iloc[-1]:.2f} on {s.index[-1].date()}; max 30-session change in 2026 "
      f"{(w / w.shift(30) - 1).loc['2026'].max():+.1%}")
    for a in ["XLE", "USO", "EWC", "EWJ", "SPY"]:
        p = px[a]; p0 = p.asof(pd.Timestamp("2025-12-31"))
        P(f"{a}: YTD 2026 {p.iloc[-1] / p0 - 1:+.1%} (last {p.index[-1].date()})")
    P(f"French Oil vs Mkt 2026 months available: " + ", ".join(f"{k}:{v.oil - v.mkt:+.1%}" for k, v in m.loc['2026-01':].iterrows()))


def main():
    m = monthly()
    P(f"WAR-ENERGY (N 1113-1114) one look. French data {m.index[0]}..{m.index[-1]}; sleeve {SLEEVE:.0%} funded from Mkt.")
    P("Alpha form: CEILING-KILL pre-data (0.25/yr x 15% x 100% x 50% = +1.9pp/yr at every account size).")
    core = table(m, CORE, 6, title="PRIMARY N1113 CORE")
    ex = core.ex.sort_values()
    p90 = placebo(m, len(core), 6, core.ex.median())
    g1 = core.ex.median() > 0 and (core.ex > 0).sum() >= 5 and ex.iloc[:-1].median() > 0
    g2 = core.ex.median() > p90
    g3 = core.dd_e.median() > core.dd_b.median() and core.acc_e.median() >= core.acc_b.median()
    P(f"GATES: G1 {'PASS' if g1 else 'FAIL'}  G2 {'PASS' if g2 else 'FAIL'}  G3 {'PASS' if g3 else 'FAIL'}  -> "
      f"{'PASS-HEDGE (n=7, unproven)' if g1 and g2 and g3 else 'KILL as hedge'}")
    P("\n---- secondary N1114 (descriptive) ----")
    c3 = table(m, CORE, 3, title="CORE 3m")
    placebo(m, len(c3), 3, c3.ex.median(), seed=1115)
    table(m, CORE, 6, col="enrgy", title="CORE 12-ind Enrgy")
    P("halves: pre-1975 " + ", ".join(f"{k}:{v:+.1%}" for k, v in core.ex.items() if k < "1975") +
      " | post-1975 " + ", ".join(f"{k}:{v:+.1%}" for k, v in core.ex.items() if k >= "1975"))
    table(m, ADD, 6, title="ADDITIONS (hindsight-chosen, not judged)")
    tr = price_trigger(m)
    P(f"\nprice trigger T months (WTISPLC 3m >= +25%, 12m refractory): {tr}")
    tdf = table(m, [t for t in tr if t >= "1974"], 6, title="PRICE TRIGGER T 1974+")
    placebo(m, len(tdf), 6, tdf.ex.median(), seed=1114)
    always_on(m)
    w, px = daily_arms()
    now_2026(m, w, px)
    OUT.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
