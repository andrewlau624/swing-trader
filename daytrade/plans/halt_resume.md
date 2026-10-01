# Plan: halt_resume (Study Lab-AY)

Written 2026-10-01, before any halt statistic was computed (the minute data exists from Lab-AX; nothing about halts
has been looked at). Code: `daytrade/strategies/halt_resume.py`. Pre-registration: `research/drafts/round1_prose.md`,
Lab Round 23, Study Lab-AY (2 variants, program N 697 -> 699).

## The idea
A stock that moves 5%+ in five minutes hits its Limit Up-Limit Down band and is halted for 5 minutes, then reopens
in an auction. A market order sent during the halt executes in that reopening auction.
- Y1 (continuation): after a halt UP, buy the reopening and hold 30 minutes.
- Y2 (reversal): after a halt DOWN, buy the reopening (panic overshoot) and hold 30 minutes.
Both are long only (halted-down names are usually under the short-sale restriction anyway).

## Why it could work, and why it might not
- Could: a halt concentrates five minutes of orders into one auction. Retail market orders pile in on the side of
  the move (Y1 continuation if attention keeps arriving; Y2 reversal if the auction overshoots on forced selling).
- Small size fits: these are thin, fast names, and a $2-25k order is invisible in a reopening auction.
- Might not: the auction prices the information; spreads after a halt are wide.
- Checked: no halt study in RESULTS.md, NEXT.md or round1_prose.md (only the night leg's missing opens).

## Exact rules (regular session from the calendar; SIP minute bars)
- Universe: Lab-AX's candidate stock-days (US common stock, previous close >= $5, today's daily high >= 1.25x or low
  <= 0.75x the previous close; the daily bar is only a prefilter). Halts happen mostly in these names.
- Halt detected (from minute bars, no halt feed): at any moment between 09:45 and 15:00, the symbol has printed NO
  bar for 5 minutes or more since its last bar, AND that last bar closed >= +5% (halt up) or <= -5% (halt down) vs
  the close 5 bars earlier, AND it printed bars in >= 8 of the 10 minutes before the gap (it was active, not thin).
- Entry: a market order at detection, filled at the first bar after the gap (its open = the reopening auction
  print), worse by the cost. One entry per name per day.
- Exit: market 30 minutes after the entry fill (the next bar's open), or a 10% catastrophe stop, or flat by 15:55.

## Costs
1x: 20bp per side; 2x: 40bp per side.

## Replay
- SIP minutes 2022-01-03 .. 2026-09-30 (the Lab-AX data), halves split at 2024-06-01.
- Placebo: the same stock-days, entry at a random minute 09:45-15:00 (open of that bar), same 30-minute hold,
  costs and stop, 1,000 draws.

## Pass bar, per variant
Mean net per trade > 0 at 2x in BOTH halves, AND day-clustered t >= 2.0 at 1x, AND >= 95th pct of the placebo.

## Drop condition
Fails: dead; nothing re-tuned (5%, 5 minutes, 8/10 activity, 30-minute hold and stop frozen).
