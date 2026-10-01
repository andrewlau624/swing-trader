# Plan: close_cross (Study Lab-AZ)

Written 2026-10-01 before any imbalance history was downloaded. A 70-second QQQ sample from one day was used only to
learn the record's fields. Pre-registration: `research/drafts/round1_prose.md`, Lab Round 24 (2 variants, program N
701 -> 703; main Round 26 BD took 699 -> 701). Data: Databento XNAS.ITCH `imbalance` (Nasdaq NOII), paid from the user's free credit (~$52 for this
universe and window). The research is done in `daytrade/research/az_replay.py`; a strategy plug-in is built only if it passes.

## The idea
From 15:50 Nasdaq publishes, every second, the closing cross's indicative clearing price: the "near" price
(`cont_book_clr_price`), the far price, and the imbalance size and side. When the near price sits well away from the
current reference price on the imbalance side, the official close tends to land near the indicative price. Buy (or
short) the continuous book before 15:55, and exit with a market-on-close order: the fill IS the closing cross.

## Why it could work, and why it might not
- Could: the closing auction is 7-10% of daily volume and index and ETF flows are price-insensitive. The NOII reveals
  where the cross will print before it happens.
- Small size fits: a $2-25k order is noise in the cross. Exiting with a market-on-close order pays no spread.
- Might not: HFTs and market makers trade exactly this. The near price already moves the continuous book toward it, so
  the gap may be gone at a 15:54:30 decision plus our latency.
- Checked: the main program's AC (parked) used imbalance only as a night-entry filter. This intraday convergence
  trade is untested.

## Exact rules
- Universe (fixed before looking; no look-ahead): the 100 Nasdaq-listed US common stocks with the highest average
  dollar volume in Nov-Dec 2021 (the Lab-AS name filter), plus QQQ and TQQQ. The list is `data/daytrade/research/az/universe.json`.
- Decision at close - 5 min 30 s (15:54:30 ET; 12:54:30 on half days, from the calendar). Read each name's latest
  closing-cross NOII record (auction_type C) at or before that time. dev = near price / ref_price - 1.
- Long if dev >= +10bp and the imbalance side is buy (B). Short if dev <= -10bp and the side is sell (A).
- Entry: at the SIP NBBO 1 second later (buy at the ask, sell at the bid). Exit: market-on-close, filled at the
  official closing price (the SIP regular-session daily close = the closing-cross print).
- **Lab rule exception (stated here):** the position is held from ~15:54:31 to the 16:00 closing cross, not flat by
  15:55. The market-on-close order is sent before Nasdaq's 15:55 cutoff and cannot be left open overnight.
- Variants: Lab-AZ1 long and short; Lab-AZ2 long only.

## Costs
- 1x: the NBBO at entry + 0.5bp, and 0.5bp on the close.
- 2x: the NBBO + 1bp + the half-spread again at entry, and 1bp on the close.

## Replay
- 2022-01-03 .. 2026-09-30, halves split at 2024-06-01.
- Placebo: a random side on the same symbol-days, using the gross entry-mid-to-close return minus the same cost,
  1,000 draws.

## Pass bar, per variant
Mean net per trade > 0 at 2x in BOTH halves, AND day-clustered t >= 2.0 at 1x, AND >= 95th pct of the placebo.

## Drop condition
Fails: dead; nothing re-tuned (10bp, 15:54:30, the universe and the side rule are frozen).
