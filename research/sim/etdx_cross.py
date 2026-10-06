"""ETDX judged on official SIP crosses 2021-26 (pref_cross with the ETDX data dir), plus a per-class split.

    PYTHONPATH=. .venv/bin/python -m research.sim.etdx_cross
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

from . import pref_cross as P

ROOT = pathlib.Path(__file__).resolve().parents[2]
P.D = ROOT / "data/research/etdx"
P.OUT = ROOT / "data/research/program/etdx_cross_out.txt"

if __name__ == "__main__":
    P.main()
    df = pd.read_parquet(P.D / "cross_rows.parquet")
    cat = pd.read_parquet(P.D / "events.parquet").drop_duplicates("ticker").set_index("ticker").cat
    df["cat"] = df.t.map(cat)
    L = [""]
    for k, x in df.groupby("cat"):
        for c in ["co", "cc"]:
            day = x.groupby("d")[c].mean()
            t = day.mean() / day.std() * np.sqrt(len(day))
            L.append(f"{k:14s} {c}: n {len(x):5d} mean {x[c].mean()*1e4:+6.1f} med {x[c].median()*1e4:+6.1f} "
                     f"hit {(x[c] > 0).mean():.2f} t(day) {t:+5.2f} ex-top5 {np.sort(x[c].values)[:-5].mean()*1e4:+6.1f} "
                     f"| open$ med {x.open_usd.median():,.0f} close$ med {x.close_usd.median():,.0f}")
    print("\n".join(L))
    with open(P.OUT, "a") as f:
        f.write("\n".join(L) + "\n")
