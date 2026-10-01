# Plan: open_imbalance (Study AT)

Written 2026-10-01, before any data for it exists. Code: `daytrade/strategies/open_imbalance.py`.
Pre-registration: `research/drafts/round1_prose.md`, Round 18, Study AT (1 variant, N 670 -> 671).
Any change to a number below is a new variant: log it in `daytrade/PLAN_CHANGES.md` and add it to N.

## The idea
In the first five minutes of the regular session, the level-one quote (bid size vs ask size) and the
signed flow of trades show who is pushing. If both lean the same way, ride that side for 30 minutes.

## Why it could work, and why it needs new data
- Order-flow imbalance predicts short-horizon returns in the microstructure literature (Cont, Kukanov &
  Stoikov 2014; Chordia & Subrahmanyam 2004). The open is when the overnight information is traded.
- Minute bars cannot see it: they have no bid/ask sizes and no trade signs. This is the kind of idea that
  died in this repo for lack of data (AC imbalance, AG breadth). It can only be tested on the lab's own
  recording.

The prior: at a 30-minute horizon the effect is likely small next to QQQ's 0.13bp spread but large next
to nothing; on 5 ETFs x 40 days the test has little power. It is pre-registered now so that the first
look cannot be tuned.

## Exact rules (regular-hours only)
- Symbols: QQQ, SPY, TQQQ, IWM, SMH (the core watchlist; gappers are excluded from this test).
- Window: 09:30:00-09:34:59 ET from `signals.regular_clock` (on a 13:00 half day the same window).
- From the recorded level-one stream, sampled each second (last known quote):
  QI = mean over the window seconds of (bid_size - ask_size) / (bid_size + ask_size).
- Signed flow: each new last-trade update (trade time changed, last size > 0) is +1 if the price >= ask,
  -1 if <= bid, otherwise the tick rule against the previous trade price. FLOW = sum(sign x size) /
  sum(size) over the window.
- Signal at 09:35:00: long if QI >= +0.20 and FLOW >= +0.10. Short if QI <= -0.20 and FLOW <= -0.10.
  Shorts only in a margin account; a cash account skips them.
- Entry: market after 09:35:00 (latency setting, default 1s).
- Stop: the window's low - $0.01 for a long (high + $0.01 for a short), engine-managed.
- Exit: market at 10:05:00, or the stop.
- Size: the engine's risk layer (0.5% of equity at risk from the stop).

## Costs
- 1x: the recorded spread (buy at the ask, sell at the bid) + 0.5bp per side.
- 2x: twice (half-spread + 0.5bp) per side.

## First look (Study AT)
- Not before **40 unflagged recorded sessions** (a day with a recorder gap is excluded, not patched).
  At 5 symbols and an expected ~30-50% signal rate that is ~60-100 trades: the least that can tell a
  5bp edge from zero with a ~15bp per-trade SD (SE ~1.5-2bp). Expected around early December 2026.
- The look is pre-registered here; it is run once.
- Halves: the first 20 and last 20 sessions.

## Pass bar (to paper)
Mean net > 0 at 2x in both halves, day-clustered t >= 2.0 at 1x, and the signal beats a sign-flip placebo
(random long/short on the same trades, 1,000 draws) at the 95th percentile.

## Drop condition
- First look fails the pass bar: dead. No re-tuning of the 0.20 / 0.10 thresholds, the window or the hold.
- Paper: drop after 40 paper round trips if the mean net is <= 0 or the fill drift exceeds the replay edge.
