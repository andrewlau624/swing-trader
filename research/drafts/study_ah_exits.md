# Study AH — stops, targets, half-off and a pullback entry for the conviction trade: DEAD (N 624 -> 630)

Stamp: `round1_prose.md` Round 16 AH (commit 424db02). Script: `research/sim/conviction_ah.py` (~2 s).
Output: `data/research/program/conviction_ah_out.txt`. Brief: `prompt_conviction_research.md` idea #3.

## Setup
- The base exit reproduces `book.breakout_days` exactly (785 trades, max |diff| 0).
- Unit u = the band σ at entry × the entry price (TQQQ).
- Stops and targets are resting orders. They are checked on every regular-hours minute, on top of the band/VWAP
  exit and the 15:57 exit.
- A minute that touches both counts as a stop. A stop that gaps through fills at the minute's open.
- Costs are 3bp/side (2x measured).
- Prior, as registered: targets lose (they cut the winners), and stops are ~neutral because the band exit is already a stop.

## Per trade (3bp/side, 2016-26)
| exit | win | mean win | mean loss | EV/trade | worst trade | 2016-20 | 2021-23 | 2024-26 |
|---|---|---|---|---|---|---|---|---|
| shipped band/VWAP | 39% | +197bp | −101 | **+15.3** | −7.9% | +6.7 | +29.0 | +14.3 |
| AH1 stop 1u | 36% | +195 | −84 | +16.9 | **−4.1%** | +9.7 | +34.5 | **+8.1** |
| AH2 stop 2u | 39% | +195 | −100 | +15.0 | −8.2% | +8.5 | +29.5 | +9.0 |
| AH3 target 2u | 44% | +158 | −105 | +10.9 | −7.9% | +1.9 | +26.4 | +8.5 |
| AH4 target 4u | 39% | +197 | −101 | +16.3 | −7.9% | +6.1 | +34.5 | +12.6 |
| AH5 half off at 2u | 44% | +164 | −104 | +13.1 | −7.9% | +4.3 | +27.7 | +11.4 |
| AH6 pullback limit at the band (fills 30%) | 35% | +95 | −66 | **−8.7** | −3.0% | −9.3 | −13.7 | −2.0 |

## Increment to the book (0.5 of equity, 3bp/side)
| variant | 2016-23 | 2024-26 | NW t | placebo | B3 maxDD (base −21.3) | P(DD>50%) (base 1.7%) | $/yr $2.3k / $25k / $100k / $500k (2016-26) |
|---|---|---|---|---|---|---|---|
| AH1 | +1.5pp | **−2.1** | +0.6 | 69 | −21.0 | 0.9% | +$14 / +$148 / +$590 / +$2.9k (2024-26: −$10.6k at $500k) |
| AH2 | +0.5 | −1.8 | −0.2 | 46 | −21.1 | 1.6% | −$3 / −$27 / −$109 / −$0.5k |
| AH3 | −1.5 | −2.0 | −1.2 | 12 | −20.8 | 0.6% | −$37 / −$404 / −$1.6k / −$8.1k |
| AH4 | +0.7 | −0.6 | +0.4 | 66 | −21.3 | 1.3% | +$8 / +$92 / +$368 / +$1.8k |
| AH5 | −0.7 | −1.0 | −1.2 | 12 | −21.0 | 0.9% | −$19 / −$202 / −$808 / −$4.0k |
| AH6 | −7.1 | −5.2 | **−2.8** | 0.1 | −21.7 | 1.5% | −$152 / −$1.7k / −$6.6k / −$33k |

**All six fail** (2024-26 < 0 and t < 2). DSR 0.00-0.01 at N 630.

## Reading
- **Targets lose, as predicted (AH3, AH5).**
  - They raise the win rate (39 → 44%) and cut the average win by 20%.
  - The trade lives on its few big winners, so this is the same result as add. 3 and add. 13.
  - A far target (4u) almost never fills (10%) and is ≈ the base.
- **The pullback entry is adverse selection (AH6).**
  - Price comes back to the band on 30% of breakouts, and those are mostly the ones that fail.
  - It is the only significantly negative result (t −2.8).
  - "Wait for a better price" is the wrong instinct for a breakout.
- **A tight stop (AH1, 1u) is the one interesting near-miss:**
  - It halves the worst trade (−7.9% → −4.1% of the position).
  - It lowers the 5y P(DD>50%) (1.7 → 0.9%).
  - It is +1.5pp/yr in 2016-23, but −2.1pp/yr in 2024-26, where it stops out winners that come back (38% of
    trades end on the stop).
  - Not adopted. It only matters as a tail control if the conviction weight is raised; that is Study AI's question,
    not a reason to rerun AH.
- Keep the shipped exit.
