"""Study PB-S — do the pre-boom conditions aggregate into a market stress-timing signal?
Pre-registered (N 830 -> 831) before any number was read. One look. No deployment."""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.sim import preboom as PB

LOG = []
PRIMARY = ["volcomp", "rngcomp", "voldry", "accumbias", "amihudrise", "ivolrise", "corrbreak", "gapfreq"]


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


def main():
    D = PB.load()
    C, E, R = D["C"], D["E"], D["R"]
    idx = C.index
    conds, _ = PB.build_conditions(D)
    score = sum(conds[n].astype("int8") for n in PRIMARY).where(E)
    stress = score.mean(axis=1)
    den = E.sum(axis=1).replace(0, np.nan)
    hi = (score >= 3).where(E).sum(axis=1) / den
    spy = R["SPY"]
    # forward quantities
    fwd_spy20 = (C["SPY"].shift(-20) / C["SPY"] - 1)
    fwd_vol20 = spy.rolling(20).std().shift(-20)
    # EQ18-ish liquid ETFs present in panel
    etfs = [s for s in ["SPY", "QQQ", "IWM", "SMH", "XLK", "XLF", "XLE", "XLV", "XLI", "XLY",
                        "XLP", "XLU", "XLB", "MDY", "EEM", "EFA", "DIA", "TLT"] if s in C.columns]
    ibs = ((C[etfs] - D["L"][etfs]) / (D["H"][etfs] - D["L"][etfs]))
    # IBS pick open(t+1)->open(t+2) premium proxy: mean over ETFs with IBS<0.2 at t
    prem = pd.Series(np.nan, index=idx)
    fwd_oo = (C[etfs].shift(-2) / C[etfs].shift(-1) - 1)
    for i in range(len(idx) - 2):
        sel = ibs.iloc[i] < 0.2
        if sel.sum() >= 2:
            prem.iloc[i] = fwd_oo.iloc[i][sel].mean()
    for span, tag in ((PB.DISC, "DISCOVERY"), (PB.OOS, "OOS")):
        wm = PB.win_mask(idx, span)
        df = pd.DataFrame(dict(stress=stress, hi=hi, fspy=fwd_spy20, fvol=fwd_vol20, prem=prem))[wm].dropna(subset=["fspy"])
        log("\n" + "=" * 80)
        log(f"{tag}  n={len(df)}")
        for y in ["fspy", "fvol", "prem"]:
            d = df.dropna(subset=[y])
            if len(d) < 30:
                continue
            log(f"  corr(stress,{y}) spearman={d[['stress',y]].corr(method='spearman').iloc[0,1]:+.2f}  "
                f"corr(hi,{y})={d[['hi',y]].corr(method='spearman').iloc[0,1]:+.2f}")
            q = d.stress.rank(pct=True)
            top = d[q >= 0.8][y].mean(); bot = d[q <= 0.2][y].mean()
            log(f"    {y}: stress top-quintile mean={top:+.2%}  bottom={bot:+.2%}  diff={top-bot:+.2%}")
    open(f"{PB.ROOT}/data/research/program/preboom7_out.txt", "w").write("\n".join(LOG) + "\n")
    log(f"\nwrote {PB.ROOT}/data/research/program/preboom7_out.txt")


if __name__ == "__main__":
    main()
