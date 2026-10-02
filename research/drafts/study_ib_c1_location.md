# Index-beat C1 / C3 / C5: where the bot runs, after tax, on the user's plan (report, no N)

Ideas pre-written in `index_beat_ideas.md` (ff9eac7) before any number. Script `research/sim/ib_c1.py`
(`python -m research.sim.ib_c1`, `--c5`); outputs `data/research/program/ib/c1_out.txt`, `c5_c3_out.txt`.
Plan P = taxable live book (V7 1.0x, cap .10, no conviction) + proposed Roth (M2L + A2), guard G4s, RAW pool,
edge-halves (EH), 35% ST via `taxable_frontier.after_tax` (April payment, carry, $3k), G4s permanent disallowance
(0.1-0.5% of losses) charged. User sizes: taxable $2.3k + $1k or $2k / 21 sessions, Roth $8.5k + $625 / 21 sessions.
Each window restarts at those balances. IRR = money-weighted %/yr of both accounts together.

## C1: bot only in the Roth, taxable = SPY (dividends taxed yearly at 20%, gain liquidated at 20% at the end)
| cost | $/mo | 2021-23 C1−P | 2024-26 C1−P | full C1−P | full IRR P → C1 |
|---|---|---|---|---|---|
| tier | 1k | −0.1pp | +3.6pp | +3.6pp | 11.1% → 14.6% |
| tier | 2k | +0.1pp | +4.2pp | +4.6pp | 9.9% → 14.5% |
| tier_hi | 1k | −0.0pp | +3.7pp | +3.8pp | 9.6% → 13.4% |
| tier_hi | 2k | +0.2pp | +4.3pp | +4.8pp | 8.9% → 13.7% |

- The Roth ends at the same value without a guard as under G4s (±$0.8k): Roth-first already gives it everything.
  The whole difference is the taxable account: **under edge-halves, the live taxable book does not beat SPY after
  tax**. It ties in 2021-23 (the 2022 bear) and loses ~4pp a year in 2024-26.
- **Verdict (track C bar: >= +2pp/yr both halves): NOT FOUND.** 2021-23 is a tie. It is the digest's "the brokerage
  ties an index after tax" in exact numbers, with the honest addition that over 2021-26 the index won.

## C5: the rate does not decide it at edge-halves (taxable $2.3k + $1k/mo, end $)
| window | book | 0% | 12% | 22% | 32% | 35% | SPY liquidated / held |
|---|---|---|---|---|---|---|---|
| 2021-23 | EH | $43.6k | $42.6k | $41.9k | $41.1k | $40.9k | $41.2k / $42.3k |
| 2021-23 | as backtested | $54.2k | $51.8k | $49.9k | $48.0k | $47.4k | |
| 2024-26 | EH | $41.9k | $41.0k | $40.2k | $39.5k | $39.2k | $42.5k / $44.4k |
| 2024-26 | as backtested | $47.9k | $46.2k | $44.8k | $43.4k | $43.0k | |
| full | EH | $95.9k | $92.3k | $89.5k | $86.7k | $85.8k | $104.0k / $111.9k |
| full | as backtested | $139.4k | $128.8k | $120.5k | $112.6k | $110.4k | |

- At EH even a **0% rate** loses to SPY held over 2021-26. Tax is not what makes the taxable book tie: the haircut is.
  As backtested (no haircut) the book beats SPY held by $27k at 0%; at 35% it is $110.4k vs SPY $104.0k liquidated /
  $111.9k held, a tie.
- So the user's real rate matters only if the edge is closer to the backtest than to half of it. A full-time student
  under 24 may owe the kiddie tax (parents' rate on unearned income above ~$2.7k) — a question for the user/CPA,
  not research.

## C3: front-loading the Roth's $7.5k in January (same total deposits; waiting money in SPY)
2021-23 +$296/yr, 2024-26 −$329/yr, full +$60/yr. The sign flips with which of the Roth book and SPY did better that
half. **Dead** (tiny, half-flip).

## What this means for the hunt
- The taxable account is where the margin over the index is missing, and it is missing before tax. Track C cannot
  manufacture +2pp from the same edges: the best placement change (C1) is +4pp in one half and 0 in the other.
- New death for the map: **HAIRCUT** — at edge-halves the taxable book ≈ SPY pre-tax; anything that "saves tax" is
  bounded by ~1/3 of a gain that is near zero. Track A/B ideas for the taxable account must add pre-tax edge
  >= ~4pp to beat the index after tax there.
- NEXT line: "Index-beat C1/C3/C5 (report): bot-only-in-Roth + index in taxable ties 2021-23, +4pp 2024-26 (not both
  halves); at edge-halves the taxable book loses to SPY even untaxed over 2021-26; Jan Roth lump ±$300/yr."
