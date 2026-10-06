"""Study SPLIT-T0 (2016-2020 official crosses): forward-split ex-date night, judged T+0 only.

Pre-registration: "Amendment — Study SPLIT-T0" in research/drafts/round1_prose.md (N 849 -> 850).

    PYTHONPATH=. .venv/bin/python -m research.sim.split_t0_1620
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

from .lh_panel import cluster_t
from .split_night import D, main as basket

OUT = pathlib.Path(__file__).resolve().parent / "split_t0_1620_out.txt"


def main() -> None:
    basket("splitnight1620", "spy1620.json", OUT, split_year=2018)
    X = pd.read_csv(D / "splitnight1620.csv", parse_dates=["d", "E"])
    T = X[X.off == 0]
    m, t = cluster_t(T.x, T.d.dt.strftime("%Y-%m-%d"))
    srt = np.sort(T.x.to_numpy())
    h1, h2 = T[T.d.dt.year <= 2018].x.mean(), T[T.d.dt.year >= 2019].x.mean()
    checks = [m > 0 and t >= 2, h1 > 0 and h2 > 0, T.x.median() > 0, srt[:-5].mean() > 0, m - 0.001 > 0]
    verdict = "PASS" if all(checks) else ("FAIL" if (m <= 0 or t < 1) else "WEAK")
    lines = ["", f"SPLIT-T0 judged (T+0 only, official 2016-2020): n={len(T)} raw-SPY mean {m*1e4:+.1f}bp t {t:.2f} "
             f"median {T.x.median()*1e4:+.1f}bp hit {(T.x > 0).mean()*100:.0f}% ex-top5 {srt[:-5].mean()*1e4:+.1f}bp "
             f"halves 16-18 {h1*1e4:+.1f} 19-20 {h2*1e4:+.1f} 5bp/side {(m-0.001)*1e4:+.1f}",
             f"   checks [t, halves, median, ex-top5, 5bp] = {checks} -> {verdict}"]
    print("\n".join(lines))
    with open(OUT, "a") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
