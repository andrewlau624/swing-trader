# Plan: late_mover (Study Lab-AX)

Written 2026-10-01, before any data for it was fetched. Code: `daytrade/strategies/late_mover.py`.
Pre-registration: `research/drafts/round1_prose.md`, Lab Round 22, Study Lab-AX (1 variant, N 676 -> 677).

## The idea
A stock up 25% or more on the day by 15:00 keeps rising into the close. RESULTS.md (the intraday-setups table) found the
mirror: stocks DOWN >= 25% by 15:00 keep falling, ~-1.5% gross, real in both halves. That was untradable
because shorting them hits the SEC's Rule 201 short-sale restriction and needs hard-to-borrow stock. The long side has
neither problem. It was never tested (grep of RESULTS.md / NEXT.md, 2026-10-01).

## Why it could work, and why it might not
- Could: late-day flows chase the day's biggest movers (attention, short covering, momentum funds and
  closing-auction demand), and the losers' version is a measured, two-half effect.
- Small size is an advantage: these are thin, volatile names where a $2-25k order is invisible.
- Might not: the effect may be asymmetric (losers fall on forced selling; winners may already have
  had their squeeze). Spreads on +25% names are wide (20-40bp+).

## Exact rules (regular session from the calendar; SIP minute bars; daily inputs from prior sessions)
- Universe: US common stock (the Lab-AS name filter); previous regular close >= $5.
- At the 14:59 minute bar's close (15:00): day change = close / previous close - 1 >= +25%, and the
  09:30-15:00 dollar volume >= $10M.
- Entry: market at the next minute (latency 1s = the 15:00 bar's open). Exit: market at 15:55 (the lab's
  flat rule). Catastrophe stop 10% below the entry, engine-managed. Long only, one entry per name per day.
- Size: the risk layer (unconstrained for per-trade statistics; lab limits for $/day).

## Costs
1x: 20bp per side. 2x: 40bp per side (wide spreads on +25% movers). Latency 1s; 60s reported.

## Replay (Study Lab-AX)
- SIP minutes 2022-01-03 .. 2026-09-30, halves split at 2024-06-01.
- Placebo: the same stock-days, entry at a random minute between 11:00 and 14:30, held 55 minutes (with the
  same costs and stop), 1,000 draws. This tests whether late day is special for these names.
- Diagnostic (not a variant): the losers' mirror (<= -25%) gross mean, to check RESULTS.md's finding.

## Pass bar
Mean net per trade > 0 at 2x in BOTH halves, AND day-clustered t >= 2.0 at 1x, AND >= 95th pct of the placebo.

## Drop condition
Fails: dead; nothing re-tuned (the 25%, 15:00, $10M and stop are frozen).
Paper: drop after 40 round trips if the mean net is <= 0 or the drift exceeds the replay edge.
