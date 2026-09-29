# Draft addendum — Study E: local ML models (GBM/ridge) on the honest 15:50 night pool (2026-09-29)

    PYTHONPATH=. .venv/bin/python -m research.sim.ml_picker         # ~7 min (200 placebo replays
                                                                   # x 3 model variants x 2 books x 2 costs)
    output: data/research/program/ml_picker_out.txt
    preds cache: data/research/program/ml_picker_preds.pkl

## Pre-registration
research/drafts/round1_prose.md, "Amendment - Study E" (stamped `Tue Sep 29 02:14:15 PDT 2026`,
before any Study E number). The study uses addendum-23's own honest night-candidate panel
(`data/research/night/features.pkl`, the SAME 20,501 rows the RAW pool uses), so the features
are exactly what the 15:50 decision process can see. Purged walk-forward: fit 2021-02..2023-
12-31, judge 2024-02-01..2026-09 (a 30-day purge; the label holds 1 day and the night leg's
picks are 1-night, so no intra-window leakage is possible). No 2016-20 holdout: the honest
reconstruction begins 2020-10, so the verdict caps at SHADOW by construction (addendum 23's
rule). The 2024-26/2021-23 numbers were not computed before the stamp.

Three model variants:
- E1 HistGradientBoostingRegressor (depth 3, lr 0.05, 300 trees, leaf 200, sklearn 1.9)
  on 15 honest features (add. 23's nine: late, rvol, gap, spy50, idio, dist20, dist252,
  prev, lprice; plus the pool's own 15:50 fields: ibs50, day50, width (the 15:30-50 range
  / p50), vol20, ret20, log10 adv).
- E2 the same model class on ONLY the add. 23 nine ("the same features, more model").
- E3 Ridge (alpha 10) on E1's feature set, standardised, nan-imputed (the linear reference).
Label = the pool's close -> next-open return net of 2 x book.cost_bps("tier on the RAW price").
The book test: the V7-raw (cap 0.10) and the as-built cap-0.15 books on the RAW pool with
the night leg's tilt weights driven by the model: clip(1 + k*z_pred, 0.25, 2)/mean, k=0.25
(the shipped weight form); everything else unchanged.
Placebo: the same weights with their VALUES shuffled within the day, 200 draws; pass = the
actual mean book increment > 0 in both halves AND the actual per-half increment above the
placebo's 95th percentile in both halves.

## Results (every number computed after the stamp)

Per-trade cross-sectional ranking, judged half (the model's top-5% minus bottom-5% P&L,
net of the tier costs, per name, n ~1,026 rows per arm):

| variant | 2021-23 (fwd training, the number printed for the pre-registered pass flow) | 2024-26 top-btm |
|---|---|---|
| E1 | n 0 rows (the forward fit trains on 2021-23; the fwd model scores only 2024-26) | **+100bp** (top +66, bot -34), corr +0.048 |
| E2 | same | +71bp (top +88, bot +17), corr +0.041 |
| E3 | same | +67bp (top +32, bot -35), corr +0.050 |
| rev E1 (fit 24-26 -> judge 21-23) | **-167bp** (top -19, bot +149), corr -0.061 | n 0 |
| rev E2 | -130bp (corr -0.041) | n 0 |
| rev E3 | +52bp (corr +0.011) | n 0 |

The 2024-26 top-5% bucket earns ~+66..88bp net per night vs the pool mean ~+50bp — the model
has honest cross-sectional predictiveness on the JUDGE half (corr 0.04-0.05, spread ~+70-100bp).

Book increments (the model's tilt vs the shipped v1 tilt), pp CAGR (t on 2021-26 NW):

| book, cost | forward E1 | forward E2 | forward E3 | reverse E1 / E2 / E3 |
|---|---|---|---|---|
| cap .10 tier | -0.09 / -1.41 / -0.73 (NW t -0.66) | -0.06 / -0.41 / -0.23 (NW t -0.18) | -0.20 / +0.06 / -0.08 (NW t -0.03) | -1.22 (t -1.38) / -1.49 (t -1.75) / -1.69 (t -1.92) |
| cap .10 tier_hi | +0.10 / -1.46 / -0.66 | +0.17 / -0.42 / -0.12 | -0.02 / -0.02 / -0.02 | -1.11 (t -1.25) / -1.43 (t -1.68) / -1.63 (t -1.85) |
| cap .15 tier | -0.28 / -1.24 / -0.74 (t -0.48) | -0.17 / -0.19 / -0.18 | -0.40 / +0.56 / +0.06 | -1.65 (t -1.39) / -2.05 (t -1.72) / -2.43 (t -1.99) |
| cap .15 tier_hi | -0.24 / -1.30 / -0.75 | -0.11 / -0.20 / -0.16 | -0.40 / +0.48 / +0.02 | -1.57 (t -1.31) / -2.00 (t -1.69) / -2.34 (t -1.91) |

Placebo percentiles: the forward rows are at 94-100 (the actual > the SHUFFLED weights in
both halves most of the time) — but the actual increment's SIGN is negative in 2024-26 for
E1/E2 and ~0 for E3. The reverse rows run at 0-2 pct for the tree models on 2024-26: a
retrained model on 2024-26's data applied BACK to 2021-23 is worse than a within-day shuffle
of its own weights (the corr -0.041/-0.061 problem). The pass-bar reading is bar 1 (the book
increment > 0 in BOTH halves vs the shipped v1 tilt), which FAILS in every row.

Model-tilt vs the shipped-tilt weight correlation (2024-26): mean +0.065, median +0.077, |corr|
> 0.5 on 50% of days (the small pools align trivially), so the tilt's information partially
overlaps the ship on busy nights and is not dimensionally new.

## Verdict: DEAD (all 3 model variants, at the book level)

The ML models rank the night pool's individual candidates slightly better than the shipped
tilt does in 2024-26 (the top/bottom cross-sectional spread 67-100bp/night); but the same
information does NOT reach the BOOK: the leg's own wt form (k 0.25, clip to [0.25, 2]) only
moves a single night's per-name shares a little, the shipped tilt already uses vol20 and
day_ret stakes, and 2024-26's retrain does not generalize back to 2021-23 (the reverse rows
are negative at 0-2 percentile). The result is the same direction add. 23 found with the
linear model ("accuracy does not move, late-share/rvol/gap/low-distance all flip between
halves") plus a slightly positive-forward cross-correlation.

Hostile reviewer's checklist:
- Lookahead: all features are computed from the 15:30-15:50 minute bars / the prior closes;
  the fit is 2021-23 and the judge 2024-02.. (30-day purge ≥ the winsorised features'
  1-day label hold).
- Cost realism: the label's cost tier is applied at each row's RAW price; the book replay
  uses the shipped `night_cost` tier/tier_hi.
- Whole-share rounding at $3k: unchanged from the shipped sim (sizing via nd.frac, the same
  weights per name).
- Survivorship: the pool = night_candidates(raw=True) on the raw close (add. 30); no
  universe modification.
- Does it duplicate an existing leg? The model's weight vector's corr with the shipped
  tilt's: |corr| > 0.5 on 50% of days; the shipped tilt also carries the pool's vol/day
  context (the case for both).
- Does it duplicate IBS? The model's "idio / spy50 / gap" features are the same dimensions
  the IBS leg uses (4.5-5.0% of the total variance explained by SPY's own day).

## Count
N = 572 + 3 (E1, E2, E3) = **575**. No survivor.

Note: the study's F (per-name live cost refit from the logs) is data-blocked locally — the
repo's own RESEARCH plan in add. 38's items expects the LIVE fills on the server (~
logs/daily-decisions-live.jsonl); the local clone's logs carry none of the 15:40 quoted
spread lines. Nothing in this study's local environment can complete item "F" (the replay
needs real fill prints). Marked data-blocked rather than dead.
