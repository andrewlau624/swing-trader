# Draft addendum — Study C: night-tilt v2 (addendum 23) restated on the RAW pool (2026-09-29)

    PYTHONPATH=. .venv/bin/python -m research.sim.tilt_v2_raw          # ~105 s
    output: data/research/program/tilt_v2_raw_out.txt

## Pre-registration
research/drafts/round1_prose.md, "Amendment - Study C" (stamped `Tue Sep 29 01:50:46 PDT
2026`, before any Variant number). Hypothesis: addendum 23's tilt v2 (`signals.night_tilt_v2`,
adds yesterday's return as a third sizing input, fitted 2021-23, built OFF, borderline on
the adjusted pool) restated on the RAW pool; the raw pool removes the sub-$5 lookahead
trades the adjusted pool contained (add. 30), so a fit that looked borderline could break
either way. Variants (2): V7 cap .10 and the moderate-as-built cap .15 book, tilt = v2
(k .25), costs tier/tier_hi. The third input (yesterday's return) is computed from the
daily research panel (split-invariant returns, no lookahead: corporate-action adjusted; the same
weight construction as the shipped night_tilt with the winsorised third feature).

## Results (v2 minus the shipped v1 tilt, pp CAGR on the same book | NW t 5 lags)

| book | tier 21-23 / 24-26 / full (t) | tier_hi 21-23 / 24-26 / full (t) |
|---|---|---|
| V7 cap .10 | +0.14 / -1.83 / -0.82 (t -1.33) | +0.27 / -1.85 / -0.76 (t -1.24) |
| T2b as-built cap .15 | +0.30 / -2.40 / -1.00 (t -1.21) | +0.20 / -2.27 / -0.99 (t -1.20) |

Placebo (within-day shuffle of the third input, 200 draws; percentile of the actual mean):

| book, cost | 2021-23 actual / placebo mean / pct | 2024-26 actual / placebo mean / pct |
|---|---|---|
| V7 tier | +0.14 / +0.28 / 40 | -1.83 / -0.60 / 2 |
| V7 tier_hi | +0.27 / +0.29 / 48 | -1.85 / -0.77 / 2 |
| as-built tier | +0.30 / +0.74 / 26 | -2.40 / -0.89 / 2 |
| as-built tier_hi | +0.20 / +0.59 / 27 | -2.27 / -0.72 / 1 |

The 2016-20 holdout is not computable for the tilt's inputs (the panel begins 2020-10; the
tilt uses a today-input model, so its 2020 leg would have to be rebuilt; reported n/a).

## Verdict: DEAD (both variants, both halves)

On the raw pool the v2 tilt now LOSES 2pp/yr in 2024-26 at the tier AND tier_hi on BOTH
books, with the placebo percentiles 1-2 (the fitted third input's weights are systematically
WORSE than a within-day shuffle of the same column). Addendum 23's borderline conclusion
("sign opposite the prior, best of 9") is confirmed and sharpened: on the corrected pool,
the v2 tilt is a systematic negative for the book's second half. Nothing changes live
(`daily.night_tilt_model` stays v1):
| idea | verdict | why |
|---|---|---|
| night-tilt v2 restated on the RAW pool | **dead** | -1.8..-2.4pp/yr in 2024-26 on both books at both cost tiers; the placebo percentile 1-2 (the third input's weights are worse than shuffled); add. 23's OFF stays |

Hostile review: the third input is computed from close-panel prices, which are split-
adjusted as of the fetch; the returns are split-invariant, and the winsorisation (lo/hi from
the fit's 1st/99th percentiles) matches the shipped emissions. The placebo test here is
"swap the third column WITHIN the day while keeping the day's cross-section" — a weak test
on its own (the within-day shuffle destroys the third input's informativeness but also
correlates with the day's ordering); its 1-2 percentile says the shipped estimate is at the
low tail of the null: the direction of the result is not in doubt. Variants: 2. No survivors.
