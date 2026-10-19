"""Study SEL-CEF: CEF-RV slot ranking among concurrent signals (see round1_prose.md).

Live rule: candidates = forward signals not held, ranked by depth = discount(signal week) - own
trailing-52w median, most negative first; slots = floor(0.50*equity / max($500, min($1000, eq/10))).

Test A (paired cohorts): within each entry week (edate) with k >= 2 signals, is the deepest signal's
forward trade return better than the cohort's others?
Test B (slot simulation): weekly replay at $2.3k / $10k / $25k. Candidate pool at week w = signals
with edate <= w < xdate, not yet taken (exactly what the live shadow log exposes run by run).
When a slot is free take the rule's rank-1: depth (current) / random / newest / shallowest.

Data: data/research/cefconnect/cef_rv_trades.csv (all CEF-RV signals 2016-2026, ret gross;
cost 50bp RT applied as -0.005 for the net column).

Run: PYTHONPATH=. .venv/bin/python research/sim/sel_cef.py
Out: data/research/program/sel_cef_out.txt
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
CSV = ROOT / "data" / "research" / "cefconnect" / "cef_rv_trades.csv"
OUT = ROOT / "data" / "research" / "program" / "sel_cef_out.txt"
COST = 0.005


def main() -> int:
    tr = pd.read_csv(CSV)
    tr["edate"] = pd.to_datetime(tr["edate"])
    tr["xdate"] = pd.to_datetime(tr["xdate"])
    tr["depth"] = tr["disc_in"] - tr["med"]
    tr["year"] = tr["edate"].dt.year
    lines = [f"SEL-CEF: CEF-RV concurrent-signal ranking (all signals 2016-2026, n {len(tr)})", ""]

    # ---- Test A: paired cohorts
    lines.append("Test A - cohort pairing (rank-1 by depth vs the other members of the same week):")
    d_rows = []
    for ed, gg in tr.groupby("edate"):
        if len(gg) < 2:
            continue
        rank1 = gg.loc[gg["depth"].idxmin()]
        rest = gg.drop(rank1.name)
        d_rows.append(dict(edate=ed, k=len(gg), d=float(rank1["ret"] - rest["ret"].mean()),
                           year=int(rank1["year"]),
                           sp=float(gg["ret"].corr(gg["depth"], method="spearman"))))
    dd = pd.DataFrame(d_rows)
    by = dd.groupby("edate")["d"].mean()
    t = by.mean() / (by.std(ddof=1) / np.sqrt(len(by)))
    s = np.sort(dd["d"].to_numpy(float))
    h1, h2 = dd[dd.year <= 2020], dd[dd.year >= 2021]
    lines.append(f"  cohorts k>=2: {len(dd)} covering {dd['k'].sum()} signals; mean d {dd['d'].mean()*1e4:+.1f}bp "
                 f"med {dd['d'].median()*1e4:+.1f} t(week) {t:+.2f} hit {(dd['d'] > 0).mean():.3f} "
                 f"ex-top-5 {s[:-5].mean()*1e4:+.1f}")
    lines.append(f"  halves: 2016-20 {h1['d'].mean()*1e4:+.1f}bp (n {len(h1)}) / 2021-26 {h2['d'].mean()*1e4:+.1f}bp "
                 f"(n {len(h2)})")
    sp = dd["sp"].dropna()
    lines.append(f"  within-cohort Spearman(ret, depth): mean {sp.mean():+.3f} (n {len(sp)} cohorts)")
    # nested subset: k >= 5 (real binding) and k>=2 but slots<=2 implied
    for kk in (2, 3, 5, 8):
        sub = dd[dd.k >= kk]
        if len(sub):
            byk = sub.groupby("edate")["d"].mean()
            tk = byk.mean() / (byk.std(ddof=1) / np.sqrt(len(byk)))
            lines.append(f"  k >= {kk}: n {len(sub)} mean d {sub['d'].mean()*1e4:+.1f}bp t(week) {tk:+.2f}")
    lines.append("")

    # ---- Test B: slot simulation
    lines.append("Test B - slot simulation (weekly; pool = signals open at the week, live semantics):")
    keys = list(zip(tr["ticker"], tr["edate"]))
    pos_map = {}
    for i, (tk, ed) in enumerate(keys):
        pos_map[i] = (tk, ed)
    for eq in (2300, 10000, 25000):
        slot = max(500.0, min(1000.0, eq / 10.0))
        room = int(np.floor(0.50 * eq / slot))
        for rule in ("depth", "random", "newest", "shallow"):
            rng = np.random.default_rng(20261018)
            weeks = sorted(tr["edate"].unique())
            pool: list[int] = []
            open_idx: list[int] = []
            taken: list[int] = []
            for w in weeks:
                w = pd.Timestamp(w)
                pool = [i for i in pool if tr["xdate"].iloc[i] > w]
                new = tr.index[tr["edate"] == w].tolist()
                pool += [i for i in new if i not in pool]
                held = {pos_map[i][0] for i in open_idx}
                free = room - len(open_idx)
                cand = [i for i in pool if pos_map[i][0] not in held and i not in taken]
                if free > 0 and cand:
                    if rule == "depth":
                        order = sorted(cand, key=lambda i: tr["depth"].iloc[i])
                    elif rule == "shallow":
                        order = sorted(cand, key=lambda i: -tr["depth"].iloc[i])
                    elif rule == "newest":
                        order = sorted(cand, key=lambda i: tr["edate"].iloc[i], reverse=True)
                    else:
                        order = [cand[j] for j in rng.permutation(len(cand))]
                    for i in order[:free]:
                        taken.append(i)
                        open_idx.append(i)
                        pool.remove(i)
                open_idx = [i for i in open_idx if tr["xdate"].iloc[i] > w]
            tt = tr.loc[taken]
            per_year = tt.assign(v=tt["ret"] * slot).groupby(tt["edate"].dt.year)["v"].sum()
            lines.append(f"  eq ${eq:>6,} room {room:>2} {rule:8s}: trades {len(tt):4d} gross ${tt['ret'].sum()*slot:>10,.0f} "
                         f"net ${(tt['ret'].sum()-COST*len(tt))*slot:>10,.0f} mean/yr ${per_year.mean():>7,.0f} "
                         f"per-trade net {(tt['ret'].mean()-COST)*1e4:+.0f}bp hold-wk {tt['hold_weeks'].mean():.1f}")
        allg = tr["ret"].sum() * slot
        per_year_all = (tr.assign(v=tr["ret"] * slot).groupby(tr["edate"].dt.year)["v"].sum()).mean()
        lines.append(f"  eq ${eq:>6,} take-all: trades {len(tr):4d} gross ${allg:>10,.0f} "
                     f"(unlimited slots; NOT investable, capital ref)")
        lines.append("")
    txt = "\n".join(lines) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(txt)
    print(txt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
