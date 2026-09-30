# Study AK — more rare setups (second breakouts, SMH/SPY/IWM fill-in days) + latency report: DEAD (N 637 -> 642)

Stamp: `round1_prose.md` Round 16 AK (commit f51c726). Script: `research/sim/conviction_ak.py` (~20 s).
Output: `data/research/program/conviction_ak_out.txt`. Brief ideas #5 and #4 (report part).

## Setup
- There is at most one conviction trade per day, at weight 0.5. The allowance is reserved at the open, so the noise
  leg is unchanged.
- The base reproduces `book.breakout_days` exactly.

## Variants (stressed costs; increment to the book, per year)
| variant | trades/yr | EV/added trade 2016-23 → 2024-26 | 2016-23 | 2024-26 | NW t | placebo | B3 maxDD (−21.3) | P(DD>50%) (1.7%) | $/yr at $25k / $100k / $500k |
|---|---|---|---|---|---|---|---|---|---|
| AK1 second TQQQ breakout after a failed strong first (94% same direction) | 11.7 | +15.1 → +6.9bp | +0.9pp | +0.4 | +0.9 | 75 | −21.3 | 1.8% | +$189 / +$757 / +$3.8k |
| AK2 SMH on no-TQQQ days | 31.7 | +5.0 → −17.9 | +0.8 | −2.4 | 0.0 | 50 | −24.4 | 5.2% | ~$0 (2024-26: −$2.4k at $100k) |
| AK3 SPY on no-TQQQ days | 33.3 | −6.1 → −10.8 | −1.0 | −1.7 | −1.0 | 16 | −20.2 | 1.4% | −$303 / −$1.2k / −$6.1k |
| AK4 IWM on no-TQQQ days | 46.5 | −19.2 → −30.3 | −4.5 | −7.0 | **−2.7** | 0.4 | −23.6 | 4.2% | −$1.3k / −$5.1k / −$25.7k |
| AK5 all three, earliest first | 80.8 | −9.3 → −17.8 | −3.8 | −7.0 | −1.9 | 4 | −24.1 | 6.2% | −$1.2k / −$4.6k / −$23.1k |

- **All five fail.** DSR ≤ 0.01 at N 642.
- AK1 is the only one positive in every half (+0.9 / +0.8 / +0.4pp for 2016-20 / 2021-23 / 2024-26), but t 0.9 is
  far from 2.0.
- **Same-bet check:** on days both fire, correlation with the TQQQ trade is SPY +0.75 (≥ 0.7: the same bet),
  SMH +0.58 and IWM +0.45. They agree on direction 85-97% of the time.
- **As the priors said:** the breakout edge lives in QQQ/TQQQ. SPY adds nothing new, IWM loses (as the noise leg does
  there, add. 6), and SMH is regime-dependent (2021-23 only, like SOXL in conv2).
- More setups dilute the one that works.

## Latency report (idea #4, no variant)
The shipped trade with every fill at the close of minute m+k (3bp/side):

| fill delay | 2016-20 | 2021-23 | 2024-26 | 2016-26 EV/trade | $/yr at $100k (w 0.5) |
|---|---|---|---|---|---|
| 0 (decision close) | +6.7bp | +29.0 | +14.3 | **+15.3** | +$5.6k |
| 1 minute | +5.4 | +24.1 | +13.0 | +12.9 | +$4.7k |
| 2 minutes | +5.3 | +22.7 | +12.7 | +12.4 | +$4.5k |

- One minute of delay costs ~2.4bp of ~15bp per trade (−16%). The second minute costs another 0.5bp.
- Unlike the SOXL ORB (add. 24: one minute ruined it), the conviction trade survives slow execution.
- The live bot decides at :00/:30 on the latest quote, so it sits between rows 0 and 1.
- **So faster decisions (5-min / 1-min / tick triggers) have little to gain:**
  - Most of the edge is already captured at 30-minute decisions.
  - A faster cadence was dead for the noise leg (add. 22).
- Sub-minute delays (5/15/60 s) need tick data the repo does not have.
- **Not built:** the Schwab L1 / NASDAQ-book recorder for QQQ/TQQQ/SMH/SPY. It would run on the live trading server,
  so it is the user's call. Given the ~2bp/minute sensitivity above, it is worth building only if a tick-level idea
  is on the table.
