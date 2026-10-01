# Plan: orb_in_play (Study Lab-AU)

Written 2026-10-01, before any data for it was fetched. Code: `daytrade/strategies/orb_in_play.py`.
Pre-registration: `research/drafts/round1_prose.md`, Lab Round 19, Study Lab-AU (2 variants, N 671 -> 673).
Any change to a number below is a new variant (PLAN_CHANGES.md, new N).

## Source
Zarattini, Barbon & Aziz, "A Profitable Day Trading Strategy For The U.S. Equity Market", Swiss Finance
Institute Research Paper 24-98 (2024), https://ssrn.com/abstract=4729284. They report a 5-minute ORB on the
top-20 "Stocks in Play" (by relative opening volume): 2016-2023, Sharpe 2.81, +1,600%. Their cost model is
$0.0035/share commission only, with no spread or slippage, and the paper has no held-out period. An
independent QuantConnect re-run reports Sharpe 2.4.

## Why it could work, and why it might not
- Could: stocks with news trade at many times normal volume at the open. Their direction in the first
  5 minutes reflects informed flow that persists through the day (attention, slow digestion).
- Might not: the paper charges no spread. The stop is tight (10% of ATR), so a few bp per side are a
  large fraction of each trade's R. Ours charges 5bp/side (1x) and 10bp/side (2x). And 2024-26 is after
  the paper's sample and its publicity.
- Unlike the dead list:
  - Lab-AS: gap-selected, a VWAP pullback entry with a 2R target.
  - AK / add. 24: ETF ORBs (TQQQ, SOXL).
  - Add. 41: noise-band momentum on the top-by-dollar-volume names.
  - Here the selection is RELATIVE opening volume, on single stocks, and the trade is held to the close.

## Exact rules (regular-hours data; daily inputs from completed prior sessions)
Universe each day (prior sessions only): US common stock (the Lab-AS name filter). Today's 09:30 open > $5;
14-session average daily volume >= 1,000,000 shares; ATR(14) > $0.50 (true range on raw SIP daily bars).

Stocks in play:
- OR volume = SIP volume of the 09:30-09:34 minute bars.
- RVOL = OR volume / the average OR volume of the previous 14 sessions (at least 10 of them observed).
- Keep RVOL >= 1.0, top 20 by RVOL.

Direction: the 5-minute opening candle (09:30 open vs 09:34 bar close). Up = long, down = short, equal = skip.

Entry: at 09:35 a stop order at the opening-range high (long) / low (short). It is valid until the entry
cutoff; an unfilled one is cancelled at the flat.

Stop: 10% of ATR(14) from the trigger price. No target.

Exit: the stop, or flat by 15:55 (the lab's flat rule; the paper exits at the close).

Size: the engine's risk layer.
- Per-trade statistics: unconstrained.
- $/day: the lab limits (0.5% risk, 3 positions, slots taken in RVOL order).
- Also reported at the paper's sizing (1% risk, 4x, 20 positions).

Variants: Lab-AU1 = long and short (the paper). Lab-AU2 = long only (what the lab could trade live first).

## Costs
1x: 5bp per side on entry and stop/flat exits (liquid names, $5+, >= 1M shares/day). 2x: 10bp per side.
A stop that gaps fills at the bar's open.

## Replay (Study Lab-AU)
- SIP minute bars, 2022-01-03 .. 2026-09-30; halves split at 2024-06-01. H2 is entirely after the paper's
  2016-2023 sample.
- Latency 1s (the next minute's open, the closest minute bars get). The stop entry triggers inside the bar
  and fills at the stop, or at the open if it gaps through.
- Placebo: the same stock-days, a random direction (coin flip) with the same mechanics, 1,000 draws.

## Pass bar (to paper), per variant
Mean net per trade > 0 at 2x in BOTH halves, AND day-clustered t >= 2.0 at 1x, AND >= 95th pct of the
placebo.

## Drop condition
- Replay fails: dead, no re-tuning (RVOL cut, top-N, the 5-minute range and the 10% ATR stop are frozen).
- Paper: drop after 40 round trips if the mean net is <= 0 or the drift exceeds the replay edge.
