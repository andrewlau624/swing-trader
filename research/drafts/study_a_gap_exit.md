# Draft addendum — Study A: gap-conditioned night-leg exit (2026-09-29)

    PYTHONPATH=. .venv/bin/python -m research.sim.night_exit_gap      # ~75 s
    output: data/research/program/night_exit_gap_out.txt

## Pre-registration

research/drafts/round1_prose.md (stamped `Tue Sep 29 01:33:38 PDT 2026`, before any
variant number). Base = load_sim(raw_price=True) (add. 30); V7 1.0x cap .10 conv .5.
Baseline before any variant number: 3bp 50.2/44.1/47.2/2.06 and tier_hi 34.4/24.3/29.4/1.41
(add. 30/39 exactly).

Hypothesis: for night picks whose next session opens <= -5% (or -8%), the opening auction
is mechanically dominated; selling the pick at a later minute (5/15/30) earns more after
costs. Variants E1-E5 = the exit minute and the threshold grid of the pre-registration.

## Sample
gm1 minute data (SIP minute, 09:30-16:01, top-40 |gap| >= 3% per session, C1 >= $3,
ADV >= $5M), 1,474 sessions 2020-11-05..2026-09-21. Night picks whose NEXT session has
minute bars: 233 of 9,546 pick legs (the rest keep the auction exit by construction).
Qualifying (gap <= -5%) trades: 73 over 70 sessions; (gap <= -8%): 37.

## Results (per-trade diff = alt exit vs the opening auction, bp of notional)

| variant | 2021-23 mean (t) | 2024-26 mean (t) | full t | placebo pct 21-23 / 24-26 |
|---|---|---|---|---|
| E1 gap<=-5% exit 09:35 | n 47: -12.1 (t -0.36) | n 21: +0.2 (t 0.00) | t -0.21 | 50 / 50 |
| E2 gap<=-5% exit 09:45 | n 47: -101.1 (t -1.46) | n 21: +29.4 (t +0.35) | t -1.12 | 12 / 13 |
| E3 gap<=-5% exit 10:00 | n 47: -44.3 (t -0.62) | n 21: -83.3 (t -0.79) | t -0.98 | 6 / 7 |
| E4 gap<=-8% exit 10:00 | n 17: -189.7 (t -1.22) | n 17: -49.7 (t -0.40) | t -1.17 | 18 / 14 |
| E5 gap<=-5% half@auction+half@10:00 | n 47: -22.2 (t -0.62) | n 21: -41.6 (t -0.79) | t -0.98 | 6 / 7 |

Book increments (same cost tier), tier and tier_hi columns:
E1: +0.06 / -0.17pp (t -0.33); tier_hi +0.08 / -0.16 (t -0.22)
E2: -0.33 / +0.03 (t -0.71); tier -0.24 / +0.03 (t -0.49)
E3: -0.15 / -0.14 (t -0.57); tier -0.09 / -0.19 (t -0.54)
E4: -0.24 / -0.05 (t -0.77); tier -0.18 / -0.10 (t -0.74)
E5: -0.07 / -0.06 (t -0.53); tier -0.05 / -0.08 (t -0.50)

Crash diagnostics: the 2020-11 start means 2020 COVID is not in the sample (no minute data
before 2020-11; the holdout gate is NOT MEET — the study cannot clear the holdout condition,
which is itself a failed adopt condition).

## Verdict: DEAD (all 5 pre-registered variants)

Every variant's full-sample mean per-trade diff is negative regardless of exit minute; the
09:35 exit's -6bp is within the noise of the 2021-26 sample (n 73) but 2021-23 is -12bp and
nothing passes the both-halves bar at any exit minute or threshold; the placebo percentiles
(6-50) show a random extreme-gap name of the same session captures comparable (often better)
exit-slippage value; the book increments are negative in 2024-26 for every threshold.
Addendum 10's unconditional auction finding extends to the extreme-gap subset: the opening
auction remains the correct exit even when the open gaps down hard. Cost realism is moot:
the diff direction is the same at tier and tier_hi.

Hostile review (c): the "same-signed greater>3% placebo name" control could bias either way;
the surviving placebo percentiles put the actual near the median (not clamped). The 73-trade
sample cannot hide a +30bp effect (the 95% CI is ~+/-35bp) but the sign is negative at both
ends; downgrade nothing. The 1.5% of trades at < $5 raw shouldn't change the auction-exit
conclusion (their cost tier is priced by the shipped convention).

## Count
Variants: 5 (pre-registered). No survivors.
