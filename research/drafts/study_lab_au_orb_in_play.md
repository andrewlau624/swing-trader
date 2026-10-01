# Study Lab-AU — 5-minute ORB on Stocks in Play (Zarattini, Barbon & Aziz 2024): DEAD (N 671 -> 673)

Stamp: `round1_prose.md` Lab Round 19 (commit 1d5153b); plan `daytrade/plans/orb_in_play.md`.
Script: `daytrade/research/au_replay.py` (the lab's `OrbInPlay` code through the lab's engine; SIP minutes).
Output: `data/daytrade/research/au/results.json` (not in git).

**Already dead in RESULTS.md** ("Stocks-in-play 5-min ORB: negative gross, −12bp/trade, 10% win"). AU
re-tested it by mistake (MISTAKES.md). It reproduces that result independently and adds the bound below.

## Data
- 1,190 sessions, 2022-01 to 2026-09.
- ~1,100-1,800 eligible names a day, 150-670 of them "in play" (RVOL >= 1); the top 20 are traded.
- 19,016 trades (Lab-AU1), 9,743 (Lab-AU2).
- The first run was broken (one account compounded; MISTAKES.md). These are the corrected numbers.

## Result (registered fills: a stop touched in the entry minute counts as hit)
| variant | 1x (5bp/side): net bp, win %, mean R, t | H1 1x | H2 1x | 2x H1 | 2x H2 | placebo pct |
|---|---|---|---|---|---|---|
| Lab-AU1 long+short | **−23.5**, 8.8%, −0.51, t −16.7 | −20.9 | −26.3 | −30.9 | −36.3 | 91.3 |
| Lab-AU2 long only | **−23.7**, 9.0%, −0.51, t −11.7 | −20.7 | −26.9 | −30.6 | −36.9 | 79.9 |

Gross before costs: −13.5bp/trade (Lab-AU1). Both sides lose equally (long −23.7, short −23.3 at 1x).

## The fill-model question, settled by an optimistic bound (diagnostic, not a variant)
- 53% of trades are stopped inside the minute they enter. A tight 10%-ATR stop cannot be ordered against
  the trigger with 1-minute bars.
- If NONE of those stops happened (the most favourable reading possible):
  - gross **+9.8 / +11.4bp** per trade (H1 / H2);
  - **−0.2 / +1.4bp** at 5bp/side;
  - **−10.2 / −8.6bp** at 10bp/side.
- So even the best case fails the 2x bar in both halves. The paper's edge (~10bp gross a trade) is
  real-ish but smaller than any realistic spread plus slippage. Its 2.81 Sharpe needs a commission-only
  cost model.

## Money (through the lab's risk layer, 1x)
- $2.3k cash: −$1.81/day, $2,300 -> $140 over 4.7 years.
- $25k margin: −$20.98/day.
- $25k at the paper's sizing (1% risk, 4x, 20 names): −$21.00/day, -> $5.

**DEAD**, both variants, under any fill model. No re-tuning.
