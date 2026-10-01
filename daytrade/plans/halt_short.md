# Plan: halt_short (Study Lab-BA)

Written 2026-10-01 after Lab-AY showed that LONGS lose ~130bp in the 30 minutes after a halt. That finding motivates
this study; no short-side number has been computed. Code: `daytrade/strategies/halt_resume.py` with `side="sell"`.
Pre-registration: `research/drafts/round1_prose.md`, Lab Round 25 (3 variants, program N 705 -> 708).

## The idea
After a volatility halt, these names drift down for the next 30 minutes, whichever way the halt was. Short the
reopening auction and cover 30 minutes later.

## Why it could work, and why it might not
- Could: retail market orders pile into the reopening (attention). The auction overshoots, then liquidity
  providers lean against it.
- Might not:
  - The Lab-AY numbers are long-side returns with a long-side stop. A short has its stop ABOVE, on exactly the names
    that spike, so it is not the mirror image.
  - Shorting needs a locate. These are often hard-to-borrow small caps.
  - Rule 201 (SSR) blocks shorting at the bid once a stock is down 10% from the prior close.
- Intraday shorts covered the same day usually pay no borrow fee, but a broker may simply have no shares.

## Exact rules (as Lab-AY, except the side)
- Halt detection, universe, timing, the 30-minute hold and flat-by-15:55 are Lab-AY's.
- Entry: SELL SHORT at the reopening (a market order sent during the halt).
- Catastrophe stop: 10% ABOVE the fill.
- Variants:
  - Lab-BA1: short after a halt UP, all names.
  - Lab-BA2: Lab-BA1 restricted to names Alpaca flags `easy_to_borrow` and `shortable` today. This is a disclosed
    look-ahead proxy for a locate; there is no historical borrow data.
  - Lab-BA3: short after a halt DOWN, only when the reopening print is above 0.9 x the previous close (no SSR
    triggered today; a carried-over SSR from yesterday is not modelled).

## Costs
1x: 20bp per side; 2x: 40bp per side. No borrow fee (intraday); availability is the risk, handled by BA2.

## Pass bar, per variant
Mean net per trade > 0 at 2x in BOTH halves, AND day-clustered t >= 2.0 at 1x, AND >= 95th pct of a placebo (random
30-minute SHORT on the same stock-days, same stop and costs), AND the mean without the 20 best trades > 0 at 1x (the
outlier check from MISTAKES.md).

## Drop condition
Fails: dead. Paper: drop after 40 paper shorts if any locate is refused more than 30% of the time, or the mean net
is <= 0, or the drift exceeds the replay edge.
