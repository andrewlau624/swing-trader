"""Study VENM runner (pre-reg research/drafts/round1_prose.md N 866->867).

FINRA weekly off-exchange venue-mix state -> conditions the live IBS leg
(book.py ibs_days: EQ18, top-3 momentum, IBS<0.2, open d+1 -> open d+2).

Run: PYTHONPATH=. .venv/bin/python -m research.sim.venm
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

from .book import EQ18, ibs_days
from . import data as D

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/venm_out.txt"
ATS = ROOT / "data/research/finra/ats_etf.parquet"
B = 1e4


def offshare_panel() -> pd.DataFrame:
    d = pd.read_parquet(ATS)
    d["shares"] = pd.to_numeric(d["totalWeeklyShareQuantity"], errors="coerce").fillna(0)
    keep = d[d.summaryTypeCode.isin(["ATS_W_SMBL_FIRM", "OTC_W_SMBL_FIRM"])]  # _FIRM rows only: summed across firms below
    g = keep.groupby(["issueSymbolIdentifier", "weekStartDate"]).agg(
        offshares=("shares", "sum"),
        nfirm=("shares", "size"),
        pub=("initialPublishedDate", "max")).reset_index()
    g["week"] = pd.to_datetime(g["weekStartDate"])
    vol = D.panel()["volume"]
    weeks = sorted(g["week"].unique())
    tape = {}
    for wk in weeks:
        fr = [x for x in pd.date_range(wk, periods=6, freq="B") if x in vol.index]
        tape[wk] = (vol.loc[fr], len(fr))          # per-symbol tape from these rows
    def tape_of(row):
        v, n = tape[row["week"]]
        return (float(v[row["issueSymbolIdentifier"]].sum()) if len(v) else np.nan, n)
    g[["tape", "nsess"]] = g.apply(tape_of, axis=1, result_type="expand")
    g = g.dropna(subset=["tape"])
    g = g[g.tape > 0]
    g["offshare_raw"] = (g["offshares"] / g["tape"]).clip(0, 1)
    g["pub"] = pd.to_datetime(g["pub"])
    return g


def build_trades(g: pd.DataFrame) -> pd.DataFrame:
    ents = ibs_days()
    P = D.etf()
    V = D.panel()["volume"]
    C, O = P["close"], P["open"]
    A = V.rolling(20).mean() * C
    states = {}
    for sym in EQ18:
        a = g[g.issueSymbolIdentifier == sym].sort_values("week")
        pub, wk, sh = a["pub"].values, a["week"].values, a["offshare_raw"].values
        st = {}
        days = C.index
        pos = 0
        for d in days:
            while pos < len(pub) and pub[pos] < np.datetime64(d):
                pos += 1
            k = pos - 1
            if k >= 0:
                st[d] = (sh[k], wk[k])
        states[sym] = st
    rows = []
    for d, legs in ents.items():
        for sym, o, r in legs:
            st = states.get(sym, {})
            if d not in st or not np.isfinite(o) or not np.isfinite(r):
                continue
            i = C.index.get_loc(d)
            p, advv = o, A.iloc[max(i-1, 0)][sym]
            cb = 15.0 if p < 10 else 10.0 if p < 20 else 7.5 if advv < 50e6 else 5.0
            rows.append(dict(day=d, sym=sym, tag="IBS", ret=r, offshare=st[d][0],
                             asof=pd.Timestamp(st[d][1]), cost_bps=cb))
    return pd.DataFrame(rows)


def past_pct(col: pd.Series) -> pd.Series:
    x = col.values
    out = np.full(len(x), np.nan)
    for i in range(len(x)):
        if i >= 20:
            h = x[max(0, i - 26):i]
            if np.isfinite(x[i]):
                out[i] = (np.sum(h < x[i]) + 0.5 * np.sum(h == x[i])) / len(h)
    return pd.Series(out, index=col.index)


def main():
    g = offshare_panel()
    T = build_trades(g)
    T["net"] = T["ret"] * B - 2 * T["cost_bps"]

    # past-only weekly percentile per symbol (frozen: expanding, min 20 weeks) + weekly diff in pp
    # weekly series straight from the panel (not from trades), then per-symbol state
    W = g.pivot_table(index="week", columns="issueSymbolIdentifier", values="offshare_raw").sort_index()
    Wpct = W.apply(past_pct)
    Wd = W.diff() * 100

    state = {}
    for s in EQ18:
        if s not in W.columns:
            print(f"  WARN: no weekly panel for {s}")
            continue
        for wk in W.index:
            p = W.at[wk, s]
            if not np.isfinite(p):
                continue
            dd = Wd.at[wk, s]
            pc = Wpct.at[wk, s]
            state[(s, wk)] = (p,
                              float(dd) if np.isfinite(dd) else 0.0,
                              float(pc) if np.isfinite(pc) else np.nan)
    def get_state(sym, asof):
        for lag in range(5):
            w = asof - pd.Timedelta(weeks=lag)
            if (sym, w) in state:
                p, dd, pc = state[(sym, w)]
                return p, dd, pc
        return np.nan, np.nan, np.nan
    F = [get_state(s, w) for s, w in zip(T["sym"], T["asof"])]
    T["lv"], T["dpp"], T["pct"] = ([f[i] for f in F] for i in range(3))
    T = T.dropna(subset=["pct"]).copy()

    parts = [f"Study VENM: IBS conditioned by weekly off-exchange share (EQ18)",
             f"trades n={len(T)} on {T['day'].nunique()} days; offshare mean={T['offshare'].mean():.3f} "
             f"median={T['offshare'].median():.3f} min={T['offshare'].min():.3f} max={T['offshare'].max():.3f}",
             f"weeks {W.index.min().date()}..{W.index.max().date()} n_weeks={len(W)}",
             "net = ret - 2x tier cost (bps per side: 5 / 7.5 / 10 / 15 by ADV/price, the live cost model)", ""]

    def block(mask, lab):
        x = T[mask].copy()
        if len(x) < 15:
            parts.append(f"  {lab:24s} n={len(x)} (too few)"); return
        x = x.sort_values("day")
        k = len(x) // 2
        by = x.groupby("day")["ret"].mean()
        t = by.mean() / by.std() * np.sqrt(len(by)) if len(by) > 3 else np.nan
        noby = x["net"]
        ex5 = x.nsmallest(max(len(x)-5, 1), "net")["net"].mean()
        parts.append(f"  {lab:24s} n={len(x):5d} net={x['net'].mean():6.2f}bp t_day={t:5.2f} med={x['net'].median():6.2f} "
                     f"ex5={ex5:6.2f} halves={x['net'].iloc[:k].mean():6.2f}/{x['net'].iloc[k:].mean():6.2f} hit={(x['net']>0).mean()*100:3.0f}%")

    parts.append("--- C1: IBS unconditional")
    block(T["pct"].notna(), "ALL IBS")
    parts.append("--- C2: buckets by offshare LEVEL percentile (past-only)")
    for lo, hi, lab in ((-1, 1/3, "LOW third"), (1/3, 2/3, "MID third"), (2/3, 99, "HIGH third"),
                        (0.9, 99, "TOP decile"), (0, 0.1, "BOTTOM decile")):
        block((T.pct > lo) & (T.pct <= hi), lab)
    parts.append("--- C2b: buckets by weekly CHANGE (dpp, pp/week)")
    for lo, hi, lab in ((3, 99, "RISING +3pp"), (-99, -3, "FALLING -3pp"), (-3, 3, "NEUTRAL")):
        block((T.dpp >= lo) & (T.dpp <= hi), lab)
    parts.append("--- C4: PLACEBO (permuted symbol's state)")
    rng = np.random.default_rng(20261006)
    syms = sorted(T["sym"].unique())
    perm = dict(zip(syms, rng.permutation(syms)))
    Fp = [get_state(perm[s], w) for s, w in zip(T["sym"], T["asof"])]
    T["pct_pl"] = [f[2] for f in Fp]
    for lo, hi, lab in ((-1, 1/3, "LOW third"), (2/3, 99, "HIGH third")):
        block((T.pct_pl > lo) & (T.pct_pl <= hi), lab)
    # per-year + economics for the best-defined contrast (HIGH vs unconditional)
    for lab, msk in (("HIGH third", T.pct > 2/3), ("LOW third", T.pct <= 1/3)):
        x = T[msk]
        yrm = x.groupby(x["day"].dt.year)["net"].mean() * 1
        parts.append(f"  {lab} per-year: " + " ".join(f"{y}:{m:5.1f}" for y, m in yrm.items()))
        years = (x["day"].max() - x["day"].min()).days / 365.25
        tpd = len(x) / max(years, 1e-9)
        nmax_day = x.groupby("day").size().max()
        cpm = x["net"].mean() / B
        parts.append(f"  {lab} trades/yr={tpd:5.1f}; max same-day legs={int(nmax_day)}; -> $/yr:")
        for bal in (1000, 3000, 10000, 25000):
            notional = 0.9 * bal / max(int(nmax_day), 1)
            parts.append(f"    ${bal:5d}: ${notional * cpm * tpd:6.0f}/yr (whole shares ignored; <~$${notional:.0f}/trade)")
    text = "\n".join(parts) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
