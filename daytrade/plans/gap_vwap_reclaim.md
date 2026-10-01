# Plan: gap_vwap_reclaim (Study AS)

Written 2026-10-01, before any replay, paper trade or computation. Code: `daytrade/strategies/gap_vwap_reclaim.py`.
Pre-registration: `research/drafts/round1_prose.md`, Round 18, Study AS (1 variant, N 669 -> 670).
Any change to a number below is a new variant: log it in `daytrade/PLAN_CHANGES.md` and add it to N.

## The idea
A popular day-trader pattern written as fixed rules. A stock that gaps up hard on heavy premarket volume
(a catalyst: earnings, news) often sells off in the first minutes, pulls back to the session VWAP, and then
resumes the move. The trader buys when price reclaims VWAP, with a stop under the pullback low and a fixed
2R target.

## Why it could work
- Gap-and-go names have news, attention and order-flow imbalance that can persist through the morning.
- VWAP is a widely watched level; a reclaim after a test can mark the end of profit-taking.
- Small size is an advantage here: these names are thin at $1M, not at $2-25k.

Why it probably will not (the prior): Studies AE, AB and AK found no direction at the open in QQQ, and
add. 41 found that intraday momentum outside the most traded names has no edge after costs. Retail
gap-and-go is crowded. Expected result: dead. It is run because it is the pattern the user asked to test,
and the lab needs a first plug-in to exercise the engine.

## How it differs from the dead list
- AE: direction of QQQ at the open from the gap/range/volume. AS trades single stocks selected by a gap,
  and only after a pullback and reclaim, not at the open.
- AB: fading QQQ inside the noise band. AS is a continuation entry, on stocks, with a stop.
- AK: second breakouts of TQQQ out of the noise band. AS has no noise band and no index.
- Add. 41: the noise-band rule on the top-by-dollar-volume stocks at 30-minute decisions. AS selects by
  gap and premarket volume (catalyst names, mostly not top-40 names), decides on 1-minute bars and has an
  intraday stop and target.

## Exact rules (all regular-hours unless stated)
Selection, once per day at 09:30 (the official open, from `signals.regular_clock`):
- US-listed common stock (Alpaca `us_equity`, NYSE / NASDAQ / AMEX / ARCA / BATS, tradable). ETFs, ETNs,
  funds, trusts, warrants, units and rights are excluded by name and symbol filter (listed in the code).
- Previous regular close >= $5 and <= $1,000 (raw, unadjusted).
- 20-session average dollar volume before today >= $5M (SIP daily bars, raw).
- Gap X: official open / previous close - 1 >= +4.0%. The official open is the open of the first regular
  minute bar (09:30), SIP.
- Premarket volume Y: SIP volume 04:00-09:29 ET >= 250,000 shares. This is the only pre-session input; it
  is a selection count, not a price, and is read from extended-hours bars on purpose.
- Keep the top 5 by premarket volume (cap 5 per day).

Entry, on 1-minute regular-session bars:
- Session VWAP from 09:30: cumulative sum(typical price x volume) / sum(volume), typical = (h+l+c)/3.
- Pullback: a bar ending at or after 09:36 whose low <= VWAP, while VWAP > previous close (the gap is
  still alive). The pullback low is the lowest low from that bar on.
- Reclaim: a later bar (or the same bar) that closes above VWAP and above the previous bar's high.
  The signal bar must end by 11:30 ET.
- Entry: market buy after the signal bar (latency setting; default 1s).
- Stop: pullback low - $0.01. Risk per share R = entry signal price - stop. Skip if R < 0.2% or R > 5%
  of price.
- Target: signal price + 2R (resting limit sell). Exit at the stop (engine-managed), the target, or
  flat by 15:55 ET (market). Same bar hits both: the stop is assumed first.
- One entry per symbol per day. Long only.

Size: the engine's risk layer sizes it: 0.5% of lab equity at risk from the stop, capped at the
position notional limit and buying power. No adds, no averaging down.

## Costs
- 1x: 10bp per side (spread + slippage on $5+ gappers in the first two hours). 2x: 20bp per side.
- Stop fills at the stop minus cost, or at the bar's open if the bar opens through the stop.
- Recorded-seconds replay (once there are recorded days) uses the recorded bid/ask instead.

## Replay (Study AS)
- Data: SIP minute bars (regular session for every decision, 04:00-09:29 only for the premarket volume),
  2022-01-03 to 2026-09-30.
- Halves: H1 2022-01-03 .. 2024-05-31, H2 2024-06-03 .. 2026-09-30.
- Latency: 1s (fill at the next minute's open, the closest minute bars can get to 1s), plus 0s (signal
  bar close) and 60s (the open one minute later) as a report.
- Report: trades, trades/day, win rate, mean R, net bp per trade at 1x and 2x, both halves, t clustered by
  day, placebo, and $/day at $2.3k (cash and margin), $10k, $25k through the risk layer.
- Placebo: same symbol-days, entry at a random minute between 09:36 and 11:30, same stop distance in %
  and 2R target, 1,000 draws. The rule must beat the 95th percentile of the placebo mean.

## Pass bar (to paper)
Mean net per trade > 0 at 2x costs in BOTH halves, AND day-clustered t >= 2.0 at 1x over the full period,
AND placebo >= 95th percentile, at the 1s latency.

## Drop condition
- Replay: drop (no paper) if the pass bar fails. No re-tuning of X, Y, the cutoff, R or the target: any
  change is a new variant with its own N.
- Paper: drop after 40 paper round trips if the mean net is < +5bp/trade or < half the replay mean at 1x,
  or if the mean paper-minus-replay fill drift is larger than the replay net edge.
