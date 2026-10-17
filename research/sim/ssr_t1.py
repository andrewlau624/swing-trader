"""SSR-T1 (pre-registered 2026-10-16, N 1013): did T+1 settlement (2024-05-28) shift the Rule 201
lift-day executable window? Judge = post-T+1 events only (trigger date >= 2024-06-01); official SIP
crosses; one look.
  arm A (deployed):  short T+2 open cross, cover T+2 close cross.
  arm T1:            short T+1 open cross, cover T+1 close cross.
Control = L in (-10%,-7%]. Pre-signed: T+1 accelerates the close-out obligation ~1 day earlier, so
the T+1-arm excess should recover vs A in the post-T+1 era. PASS = T1 >= A + 10bp, day-clustered
t >= 2 in the era, hedged intact (1.5x SPY). Else the deployed window stays T+2.

PYTHONPATH=. .venv/bin/python -m research.sim.ssr_t1
"""
from __future__ import annotations
import glob
import json
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from exdiv_open import crosses  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data/research/ssr"
OUT = pathlib.Path(__file__).resolve().parent / "ssr_t1_out.txt"
POST_T1 = "2024-06-01"


def day_t(a, b):
    o = pd.concat([a, b])
    m = o.mean()
    s = o.std()
    return m / s * np.sqrt(len(o) + len(b)), m


def main():
    e = pd.read_parquet(D / "events.parquet")
    rows = []
    stems = {pathlib.Path(f).stem: f for f in sorted(glob.glob(str(D / "x" / "*.json")))}
    for r in e.itertuples():
        if r.ticker == "SPY":
            continue
        st = pd.Timestamp(r.d1).strftime("%Y-%m-%d")
        if st not in stems:
            continue
        j = json.load(open(stems[st]))
        if r.ticker not in j or "SPY" not in j:
            continue
        spy = crosses(j["SPY"])
        x = crosses(j[r.ticker])
        d1, d2 = pd.Timestamp(r.d1), pd.Timestamp(r.d2)
        if d1 not in x.index or d2 not in x.index or d1 not in spy.index or d2 not in spy.index:
            continue
        A = -(x.loc[d2, "cp"] / x.loc[d2, "op"] - 1)
        T1 = -(x.loc[d1, "cp"] / x.loc[d1, "op"] - 1)
        sA = spy.loc[d2, "cp"] / spy.loc[d2, "op"] - 1
        sT1 = spy.loc[d1, "cp"] / spy.loc[d1, "op"] - 1
        rows.append(dict(t=r.ticker, d=r.date, L=r.L, adv=r.adv,
                         A=A * 1e4, T1=T1 * 1e4,
                         Ah=(A + 1.5 * sA) * 1e4, T1h=(T1 + 1.5 * sT1) * 1e4,
                         open_usd=x.loc[d1, "os"] * x.loc[d1, "op"]))
    df = pd.DataFrame(rows)
    if df.empty:
        print("no rows: no post-T+1 events matched in the cache; fetch emits nothing")
        return
    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=["A", "T1"])
    df = df[df.d >= POST_T1]
    lines = [f"SSR-T1 judged POST-T+1 era: {len(df)} events, {df.d.nunique()} sessions "
             f"({df.d.min()} .. {df.d.max()})"]
    for lab, x in [("TREATED L<=-10%", df[df.L <= -0.10]),
                   ("TREATED ADV>=$20M", df[(df.L <= -0.10) & (df.adv >= 2e7)]),
                   ("CONTROL L -10..-7 ", df[df.L > -0.10])]:
        for c in ("A", "Ah", "T1", "T1h"):
            day = x.groupby("d")[c].mean()
            t = day.mean() / day.std() * np.sqrt(len(day))
            lines.append(f"{lab:18s} {c:3s} n {len(x):5d} mean {x[c].mean():+6.1f} med {x[c].median():+6.1f} "
                         f"hit {(x[c] > 0).mean():.2f} | day-t {t:+5.2f}")
        lines.append("")
    tr = df[df.L <= -0.10]
    lines.append(f"open-cross $ size on T+1 (treated): median ${tr.open_usd.median():,.0f}, "
                 f"p10 ${tr.open_usd.quantile(.1):,.0f}")
    t1, m1 = day_t(tr[tr.L <= -0.10]["T1"], tr[tr.L <= -0.10]["A"])
    lines.append(f"T1 minus A (treated): {m1:+.1f}bp")
    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
