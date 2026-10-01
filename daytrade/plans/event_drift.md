# Plan: event_drift (Study Lab-BH)

Written 2026-10-01 before any computation (the daily bars on disk were fetched for other studies; no event return
has been looked at). Pre-registration: `research/drafts/round1_prose.md`, Lab Round 32 (2 variants, program N 719 -> 721).
Multi-day: this belongs to the lab only as a small-account strategy, a few positions held for weeks, not intraday.

## The idea and source
Stocks keep drifting in the direction of a large announcement-day move for weeks: the earnings-announcement-return
drift (Brandt, Kishore, Santa-Clara & Venkatachalam 2008; Chan, Jegadeesh & Lakonishok 1996). There is no earnings
calendar here, so the event is proxied by a big gap UP on abnormal volume (earnings, guidance, FDA, contract news).
Spread and costs are paid once against a multi-week move, which is where small accounts can win.

## Exact rules
- Universe: US common stock (Lab-AS name filter); previous close >= $5; 20-session average dollar volume >= $20M
  (before day 0).
- Event (day 0): open / previous close - 1 >= +5% AND day-0 volume >= 3x its 20-session average (raw SIP daily bars;
  regular sessions).
- Entry: day 1's official opening cross (a market order directed to the listing exchange before 09:30, as the live
  book's open sells do), using only completed day-0 data.
- Exit: the official close of day H (BH1: H = 20 sessions; BH2: H = 5 sessions). Long only, no stop.
- Returns on split/dividend-ADJUSTED prices (adjustment = all) for the holding period. Raw prices only for the filters.

## Costs
1x: 10bp per side; 2x: 20bp per side.

## Measures
- Per event: net return, and EXCESS net return over SPY on the same open-to-close window (the market's own drift
  2022-26 must not count as edge).
- Day-0 halves split at 2024-06-01.
- t clustered by entry month (overlapping holds).
- Placebo: the same stocks at random non-event dates (no +5%/3x day within 5 sessions), same H, 1,000 draws of one
  random date per event.
- $: a 10-slot portfolio (10% of equity each, new events ranked by volume ratio when a slot frees, whole shares) at
  $2.3k / $10k / $25k.

## Pass bar, per variant
Mean EXCESS net > 0 at 2x in BOTH halves; month-clustered t >= 2.0 at 1x (excess); >= 95th pct of the placebo
(excess); the mean excess without the 20 best events > 0.
