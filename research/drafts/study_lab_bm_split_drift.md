# Study Lab-BM — drift after forward-split ex-dates: DEAD (program N 727 -> 728)

Stamp: round1_prose.md Lab Round 37 (commit 71c560e). Script `daytrade/research/bm_replay.py`. Forward splits inferred from
raw SIP daily bars (open/prev close within ±6% of 1/k), 2017-2026; buy at the ex-date close, hold 60 sessions, excess vs SPY.

- 192 events. 2x excess: **−399bp** (2017-21) / **−135bp** (2022-26); −250bp overall.
- Placebo 0.3rd pct: the SAME stocks on random dates beat SPY by about +12% per 60 days. Splitters are past mega-winners,
  and the 60 days after the split ex-date are their worst stretch.
- By year it swings from −1,009bp (2021) to +1,435bp (2023, n 13): a few names dominate.

**DEAD.** The 1990s post-split drift does not hold 2017-26.
