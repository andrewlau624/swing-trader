"""Study Lab-BT: top-decile momentum vs the market on Ken French's library (round1_prose.md Lab Round 42).

  python -m daytrade.research.bt_replay
"""
from __future__ import annotations

import io
import json
import math

import numpy as np
import pandas as pd

from ..settings import DATA

OUT = DATA / "research" / "bt"


def first_block(path):
    """The first monthly table (value-weighted) of a French CSV."""
    lines = path.read_text().splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith(",") )
    rows = []
    for l in lines[start + 1:]:
        p = l.split(",")
        if not p[0].strip().isdigit() or len(p[0].strip()) != 6:
            break
        rows.append(l)
    df = pd.read_csv(io.StringIO(lines[start] + "\n" + "\n".join(rows)))
    df = df.rename(columns={df.columns[0]: "ym"})
    df["ym"] = df.ym.astype(str).str.strip()
    return df.set_index("ym").astype(float) / 100


def stats(x, months):
    x = x[x.index.isin(months)]
    return x


def run():
    mom = first_block(OUT / "10_Portfolios_Prior_12_2.csv")
    ff = first_block(OUT / "F-F_Research_Data_Factors.csv")
    mkt = ff["Mkt-RF"] + ff["RF"]
    hi = mom["Hi PRIOR"]
    d = pd.DataFrame({"hi": hi, "mkt": mkt}).dropna()
    res = {}
    def block(lo, hi_):
        s = d[(d.index >= lo) & (d.index <= hi_)]
        return s
    for tier, c in (("1x", 0.0020), ("2x", 0.0040)):
        ex = d.hi - d.mkt - c
        res[tier] = {name: float(ex[(ex.index >= a) & (ex.index <= b)].mean() * 1e4)
                     for name, a, b in (("judged 1963-07..2015-12", "196307", "201512"), ("h1 1963-07..1989-12", "196307", "198912"),
                                        ("h2 1990-01..2015-12", "199001", "201512"), ("ref 1927-1963-06", "192701", "196306"),
                                        ("ref 2016-01..2026-08", "201601", "202608"))}
    ex1 = (d.hi - d.mkt - 0.0020)
    j = ex1[(ex1.index >= "196307") & (ex1.index <= "201512")]
    res["t_judged"] = float(j.mean() / (j.std(ddof=1) / math.sqrt(len(j))))
    res["without_best5_judged_bp"] = float(np.sort(j.values)[:-5].mean() * 1e4)
    roll = (1 + ex1).rolling(12).apply(np.prod, raw=True) - 1
    res["worst_12m_excess"] = {"value": float(roll.min()), "ending": str(roll.idxmin())}
    for name, a, b in (("1963-2015", "196307", "201512"), ("2016-2026", "201601", "202608")):
        s = d[(d.index >= a) & (d.index <= b)]
        res[f"cagr_{name}"] = {"top_decile_1x": float((1 + s.hi - 0.002).prod() ** (12 / len(s)) - 1),
                               "market": float((1 + s.mkt).prod() ** (12 / len(s)) - 1)}
    res["by_decade_excess_1x_bp"] = {str(dec): float(g.mean() * 1e4) for dec, g in ex1.groupby(ex1.index.str[:3] + "0s")}
    a2 = res["2x"]
    res["verdict"] = ("PASS" if a2["h1 1963-07..1989-12"] > 0 and a2["h2 1990-01..2015-12"] > 0 and res["t_judged"] >= 2
                      and res["without_best5_judged_bp"] > 0 else "DEAD")
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    run()
