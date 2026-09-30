# Draft addendum — Study S: short the night picks after the open (2026-09-29)

    PYTHONPATH=. .venv/bin/python -m research.sim.night_short      # ~15 s
    output: data/research/program/night_short_out.txt

## Pre-registration
research/drafts/round1_prose.md "Round 5" (commit 2b935b3, stamped before any Study S return).
8 variants: entry A (auction, idealised) / B (09:30 bar close, executable) x cover 09:45 /
10:00 / 10:30 / close. SSR (day-d low <= -10% vs close d-1) = untradable. N 593 -> 601.

## Sample
9,546 shipped V7 night picks (raw prices, corr .7). **75% (7,133) are SSR on d+1** — every pick
fell >= 8% on d and closed near its low, so most crossed -10% intraday. 950 lack am1 bars or
fail the basis check. Scored: 1,463 (2021-23 688, 2024-26 736). Placebo pool 4,148 rows.

## Results (mean net per trade, bp; book increment pp/yr; NW t over 2021-26)

tier:
| variant | 2021-23 | 2024-26 | placebo pct | book 21-23 / 24-26 | NW t |
|---|---|---|---|---|---|
| S1 A cover 09:45 | -7.8 | -18.0 | 1 / 99 | -1.39 / -1.12 | -1.93 |
| S2 A cover 10:00 | -14.3 | -15.3 | 8 / 100 | -1.24 / -0.95 | -1.29 |
| S3 A cover 10:30 | -3.5 | -16.5 | 16 / 99 | -0.00 / -1.90 | -0.92 |
| S4 A cover close | -1.2 | -32.1 | 24 / 100 | +0.47 / -1.65 | -0.38 |
| S5 B cover 09:45 | -18.7 | -19.6 | 0 / 90 | -2.12 / -1.33 | -2.96 |
| S6 B cover 10:00 | -25.1 | -16.7 | 9 / 100 | -1.96 / -1.14 | -2.05 |
| S7 B cover 10:30 | -14.5 | -18.3 | 22 / 86 | -0.72 / -2.09 | -1.51 |
| S8 B cover close | -11.0 | -33.9 | 35 / 100 | -0.27 / -1.86 | -0.73 |

tier_hi: every variant worse (-10 to -55bp per trade, NW t -1.0 to -7.4). Full table in the output.

Gross short return, no costs, scored (shortable) picks: +8 to +13bp by 09:45-10:30, ~-1bp
to the close; win rate 50-52%. Round-trip cost at tier is ~20-35bp on these names.

**Verdict: DEAD** (no variant passes bar (1) at either cost; none reaches NW t >= 2).

## Post-hoc diagnostic (descriptive, not a variant, not counted in N)
Gross short return of the SSR picks the rule excluded (n 5,459): +34 / +35 / +45 / +24bp
at 09:45 / 10:00 / 10:30 / close, vs +10 / +8 / +13 / -1bp for the shortable ones. The
post-open drift that exitt.py shows lives in the names Rule 201 blocks from being shorted
at the open (they are shortable only on an uptick, above the bid, which a market short at
the open cannot do). It explains the anomaly; it is not tradable.

## Do NOT redo
- Shorting the night picks after the open, any cover minute. The shortable ones do not
  drift enough to pay the spread; the ones that drift are SSR.

## Caveats
- Borrow/locates not modelled: they could only make it worse.
- The placebo uses daily-panel adjusted close / 20d ADV for the cost tier (picks use raw).
- 2020-11..12 is in no half.
