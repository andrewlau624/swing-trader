"""Study SEL-PREF: PREF-EX/ETDX same-ex-date bundle ranking (see round1_prose.md).

The live module ranks candidates for tomorrow's ex-date by yield = div / last price, buys the top
MAX_NAMES=3 (budget-capped). Test: on ex-dates with k > 3 candidates, does the yield-top-3 bundle
beat the rest of the same date, and do alternatives (div-$ absolute, cross liquidity, random) beat
the current yield order?

Capture = the live CC form (buy T-1 closing cross, sell T closing cross, keep the dividend):
  cross rows: (cc_T + div)/c_{T-1} - 1 as recorded by pref_cross.py (official auctions);
  raw fallback: (closeunadj_T + div)/closeunadj_{T-1} - 1 from Sharadar (2005-26 rows without crosses).

Run: PYTHONPATH=. .venv/bin/python research/sim/sel_pref.py
Out: data/research/program/sel_pref_out.txt
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
STORE = pathlib.Path.home() / "data" / "sharadar"
D = ROOT / "data" / "research"
OUT = ROOT / "data" / "research" / "program" / "sel_pref_out.txt"
COST = 0.0010  # 10bp RT shock (auction-to-auction measured ~0-5bp/side)


def load_class(name: str) -> pd.DataFrame:
    ev = pd.read_parquet(D / name / "events.parquet")
    ev["date"] = pd.to_datetime(ev["date"])
    ev = ev.rename(columns={"date": "d", "ticker": "t"})[["t", "d", "div", "pc", "dv"]]
    cr = pd.read_parquet(D / name / "cross_rows.parquet")
    cr["d"] = pd.to_datetime(cr["d"])
    m = ev.merge(cr[["t", "d", "yld", "co", "cc", "open_usd", "close_usd"]], on=["t", "d"], how="left")
    m["cls"] = name
    return m


def raw_closes(tickers: list[str]) -> pd.DataFrame:
    parts = []
    for f in (STORE / "stocks.parquet", STORE / "funds.parquet"):
        parts.append(pd.read_parquet(f, columns=["ticker", "date", "closeunadj"],
                                     filters=[("ticker", "in", tickers)]))
    b = pd.concat(parts, ignore_index=True)
    b["date"] = pd.to_datetime(b["date"])
    return b.drop_duplicates(["ticker", "date"]).rename(columns={"ticker": "t"})


def bundle_stats(m: pd.DataFrame, rank: list[str], label: str, lines: list[str], kmin: int = 4) -> None:
    """For each ex-date with k >= kmin: delta = mean(capture | top-3 by rank) - mean(capture | rest)."""
    rows = []
    for d, gg in m.groupby("d"):
        gg = gg.dropna(subset=["cap"])
        if len(gg) < kmin:
            continue
        gg = gg.sort_values(rank, ascending=[False] * len(rank))
        top, rest = gg.head(3), gg.iloc[3:]
        rows.append(dict(d=d, k=len(gg), delta=float(top["cap"].mean() - rest["cap"].mean()),
                         year=int(pd.Timestamp(d).year)))
    r = pd.DataFrame(rows)
    if r.empty:
        lines.append(f"  {label}: no dates")
        return
    by = r.groupby("d")["delta"].mean()
    t = by.mean() / (by.std(ddof=1) / np.sqrt(len(by)))
    s = np.sort(r["delta"].to_numpy(float))
    h1, h2 = r[r.year <= 2015], r[r.year >= 2016]
    lines.append(f"  {label:14s} dates {len(r):4d} (k>= {kmin}) mean {r['delta'].mean()*1e4:+7.1f}bp "
                 f"med {r['delta'].median()*1e4:+7.1f} t(date) {t:+6.2f} hit {(r['delta'] > 0).mean():.3f} "
                 f"ex5 {s[:-5].mean()*1e4:+7.1f} | h1 {h1['delta'].mean()*1e4:+6.1f} (n {len(h1)}) "
                 f"h2 {h2['delta'].mean()*1e4:+6.1f} (n {len(h2)})")


def main() -> int:
    m = pd.concat([load_class("pref"), load_class("etdx")], ignore_index=True)
    m = m[m["dv"].fillna(0) >= 1e5].copy()
    # raw-close CC fallback
    need = m["t"].dropna().unique().tolist()
    px = raw_closes(need).pivot_table(index="t", columns="date", values="closeunadj")
    caps = []
    for r in m.itertuples():
        cap = None
        if np.isfinite(r.cc) if r.cc is not None else False:
            cap = float(r.cc)
        else:
            try:
                row = px.loc[r.t]
                d0 = pd.Timestamp(r.d) - pd.offsets.BDay(1)
                # T-1 close = pc (raw prev close from events); T close from the panel
                cT = row.get(pd.Timestamp(r.d), np.nan)
                if np.isfinite(cT) and np.isfinite(r.pc) and r.pc > 0:
                    cap = (cT + float(r.div)) / float(r.pc) - 1.0
            except KeyError:
                cap = None
        caps.append(cap)
    m["cap"] = caps
    n_cross = m["cc"].notna().sum()
    lines = [f"SEL-PREF: same-ex-date ranking, pref+etd, n {len(m)} events, "
             f"{m['d'].nunique()} ex-dates; official-cross CC available {n_cross}", ""]
    # monotonicity: capture vs yield within date
    sp = []
    for d, gg in m.dropna(subset=["cap"]).groupby("d"):
        if len(gg) >= 4 and gg["yld"].notna().all():
            sp.append(gg["cap"].corr(gg["yld"], method="spearman"))
    sp = pd.Series(sp)
    lines.append(f"within-date Spearman(cap, yield): mean {sp.mean():+.3f} (n {len(sp)} dates); "
                 f"detail: positive share {(sp > 0).mean():.1%}")
    lines.append("")
    lines.append("Bundle tests (top-3 by rank vs the rest, same ex-date; k>=4):")
    for name, rank in [("yield (current)", ["yld"]), ("div-$ absolute", ["div"]),
                       ("cross $ (open)", ["open_usd"]), ("random", [])]:
        if rank:
            bundle_stats(m, rank, name, lines)
        else:
            rng = np.random.default_rng(20261018)
            mm = m.copy()
            mm["rnd"] = rng.random(len(mm))
            bundle_stats(mm, ["rnd"], "random", lines)
    lines.append("")
    lines.append("Cross-only subset (official auctions, 2021-26):")
    mc = m[m["cc"].notna()].copy()
    mc["cap"] = mc["cc"]
    for name, rank in [("yield (current)", ["yld"]), ("div-$ absolute", ["div"]),
                       ("cross $ (open)", ["open_usd"]), ("random", [])]:
        if rank:
            bundle_stats(mc, rank, name, lines, kmin=4)
        else:
            rng = np.random.default_rng(20261018)
            mcc = mc.copy()
            mcc["rnd"] = rng.random(len(mcc))
            bundle_stats(mcc, ["rnd"], "random", lines, kmin=4)
    lines.append("")
    # cost shock on the current rule (cancels in a same-date difference; level handled in the report)
    m2 = m.copy()
    m2["cap"] = m2["cap"] - COST
    bundle_stats(m2, ["yld"], "yield @10bp", lines)
    lines.append("")
    # halves within the available window (all events 2021+, so split 2021-23 / 2024-26)
    rows = []
    for d, gg in m.groupby("d"):
        gg = gg.dropna(subset=["cap"])
        if len(gg) < 4:
            continue
        gg = gg.sort_values("yld", ascending=False)
        rows.append(dict(d=d, delta=float(gg.head(3)["cap"].mean() - gg.iloc[3:]["cap"].mean()),
                         year=int(pd.Timestamp(d).year)))
    rr = pd.DataFrame(rows)
    a, b = rr[rr.year <= 2023], rr[rr.year >= 2024]
    lines.append(f"yield halves: 2021-23 {a['delta'].mean()*1e4:+.1f}bp (n {len(a)}) / "
                 f"2024-26 {b['delta'].mean()*1e4:+.1f}bp (n {len(b)})")
    # size of the binding set
    g = m.groupby("d").size()
    lines.append(f"ex-dates: {len(g)}, mean k {g.mean():.1f}; dates with k>3: {(g > 3).sum()} "
                 f"({(g > 3).mean():.1%}) carrying {g[g > 3].sum()/g.sum():.1%} of events")
    txt = "\n".join(lines) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(txt)
    print(txt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
