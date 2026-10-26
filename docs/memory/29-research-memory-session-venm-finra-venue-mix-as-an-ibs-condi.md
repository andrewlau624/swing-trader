# Research memory — session "VENM: FINRA venue-mix as an IBS conditioning state" (2026-10-06, night)

- **VENM (N 867): KILL — killed by its own placebo.** Built the FINRA weekly off-exchange venue-mix
  panel (EQ18 ETFs, 2021-12..2026-09, LOOKAHEAD-SAFE via per-row initialPublishedDate; 3.0-week
  empirical lag; key-less `otcMarket/weeklySummary`; the user's FINRA API key still 401s on
  regData — it looks truncated, user will reissue). Data doc + fetcher: research/sim/finra_ats.py;
  cache data/research/finra/ats_etf.parquet; conditioning runner research/sim/venm.py
  (venm_out.txt). Result: LEVEL buckets non-monotone (LOW +10.1 / MID +28.9 / HIGH -4.5bp),
  change buckets t < 2 with halves flips, and the PERMUTED-SYMBOL placebo separates more than the
  real state (+15.9 t 2.68): bucketing = sample noise. Ceiling: ±20bp x ~40 trades/yr = +0.6-0.8pp/yr
  MAX — below the +8pp gate an order of magnitude. Per-stock night-leg attachment: feasible-but-
  heavy; priors inherited from the placebo failure; a new mechanism hypothesis would be required.
- Program N = 867.
