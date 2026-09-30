# Study AE — the biggest intraday swings: their size is predictable at the open, their direction is not (N stays 619)

Stamp: `round1_prose.md` Round 15 (commit 0f4f3ef). Script: `research/sim/big_swings.py` (22 s).
Output: `data/research/program/big_swings_out.txt`. SIP daily panel, names with ADV20 >= $20M and price >= $5,
open auction -> close, z = ln(close/open) / sigma20. 3.0M stock-days, 2021-26.

## Part 1 — what big swings (|z| >= 3) have in common at 09:30
~15/day in 2021-23, ~25/day in 2024-26; big DOWN days outnumber big up days (0.48-0.63% vs 0.33-0.45% of
stock-days); of the day's 10 biggest swings, 45-46% are up.
| precursor at the open | big UP swings | big DOWN swings | what it predicts |
|---|---|---|---|
| a large gap (either way, top or bottom decile of gap_z) | 2.1-2.3x as likely | 2.0-2.4x | **size, both ways** |
| a wide range yesterday (range1_z top decile) | 2.4-2.7x | 2.4-2.6x | **size, both ways** |
| heavy volume yesterday (rvol1 top decile) | 2.0-2.1x | 1.9-2.0x | **size, both ways** |
| low vol20 (sigma-scaled moves are easier to exceed) | top decile 0.3-0.6x | 0.3x | size |
| prior-day / 5-day return, IBS, 20d high, ADV | ~1.0-1.4x, symmetric | same | little |
Mean z by decile (direction) sits within ±0.07σ of the universe for every feature in both halves. The same
three precursors mark the big up days AND the big down days: they say "this name will move a lot today",
not which way.

## Part 2 — direction, selected on 2021-23 only: nothing to test
Best extreme decile vs the day's universe mean, open -> close, before costs: low-rvol names −3.4bp (t −2.5),
big gap-ups −5.0bp (t −2.0); every other |t| <= 1.4. No feature reached the registered |t| >= 3, so AE1-AE5
were not run (N stays 619). For scale: the round-trip cost on these names is ~10-30bp (tier), so even the best
cell is a tenth of its cost.

## Reading
- This matches every earlier intraday result (add. 6, 8, 24: gap-and-go, gap squeezes, stocks-in-play ORB, all
  negative): big-move days are forecastable in SIZE, which the option market already prices (straddles), but
  their SIGN at the open is a coin flip after costs.
- The one intraday edge the program has, the noise leg / conviction trade, does not predict direction at the
  open either: it waits until the move has started (a breakout out of the noise band) and rides it, with an
  exit when it fails. That is the tradable form of "catching a big swing".
- Not tested (no data): minute-level features after the open for the broad universe (first-30-min volume,
  VWAP behaviour) — minute bars exist only for ~11 ETFs and gap names. That test would be the stocks-in-play
  ORB again, which was negative gross (add. 6).
