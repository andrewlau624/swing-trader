"""Heavy-lock extraction for research/sim/roth_opt.py: the live-guard night leg
(corr 0.7, cap 0.10), the conviction series and the 2016-20 holdout legs, pickled
to the scratchpad so roth_opt.py runs without the panel in memory."""
from __future__ import annotations

import pickle

from . import book as B
from .regime_tilt import holdout_legs
from .validate import load_sim

SCR = str(__import__("pathlib").Path(__file__).resolve().parents[2]) + "/data/research/program"
OUT = f"{SCR}/cache_roth_opt.pkl"


def main():
    s = load_sim()
    N = B.night_days(max_corr=0.7, max_name_pct=0.10)
    BO = B.breakout_days()
    legs = holdout_legs(s)
    pickle.dump({"N": N, "BO": BO, "legs": legs}, open(OUT, "wb"))
    print("wrote", OUT, len(N), "night days")


if __name__ == "__main__":
    main()
