# Index-beat R6-5: stack the bot on a 100% SPY core in the taxable account ("portable alpha") — NOT FOUND (near miss), the strongest result of the hunt

Idea from round 6 (brainstorm agent, index_beat_ideas_r6.md); spec in index_beat_log.md before the run. Script
`research/sim/ib_r65.py` (`main`, `risk`); outputs `data/research/program/ib/r65_out.txt`, `r65_risk.txt`.
Taxable: hold SPY at 1.0x and run every live leg on top (noise intraday; night + IBS overnight on margin: mean debit
0.40E, 12%/yr interest = −4.8%/yr charged); legs' P&L taxed ST 35% yearly, SPY LT at the end (as ib_c2). Roth: the book
without QQQ/SMH IBS (wash). Plan P: live taxable book + Roth, G4s. Edge-halves on every leg; SPY as is.

## Combined plan (taxable + Roth), money-weighted %/yr after tax, vs P
| cost | window | $1k/mo | $2k/mo |
|---|---|---|---|
| tier | 2021-23 | **+1.50pp** | +2.62pp |
| tier | 2024-26 | +4.70pp | +6.92pp |
| tier | full | +4.53pp | +6.52pp |
| tier_hi | 2021-23 | **+1.57pp** | +2.67pp |
| tier_hi | 2024-26 | +4.87pp | +7.05pp |
| tier_hi | full | +4.81pp | +6.74pp |

## Taxable account alone, 2021-26, pre-tax, tier
| | CAGR | max DD | worst month | 2022 |
|---|---|---|---|---|
| SPY | 15.3% | −24.5% | −9.2% | −18.2% |
| bot (plan), EH | 12.2% | −13.9% | −7.2% | +12.3% |
| **stacked, EH** | **22.1%** | −27.8% | −16.3% | −12.6% |
| bot (plan), as backtested | 25.7% | −9.1% | −6.4% | +25.7% |
| stacked, as backtested | 36.8% | −23.2% | −15.5% | −2.2% |

5-year MC, $2.3k + $1k/mo, all gains taxed ST 35% (conservative for the SPY part), EH:
SPY median $78.6k (p10 $65.7k, P(DD>30%) 6%, P(DD>50%) 0%); bot $75.5k ($64.9k, 1%, 0%); **stacked $88.8k ($69.6k, 16%, 0.3%)**.

## Verdict and why it matters
- **NOT FOUND by the prompt's bar**: the combined plan at $1k/mo is +1.5pp in 2021-23 (< +2). At $2k/mo it clears +2pp in
  both halves at both cost levels.
- But it is the first change that **beats the index in both halves at the plan's own haircut**, and it is robust to the
  haircut in both directions: the bot no longer has to beat SPY, it only has to beat its margin interest (~4.8%/yr on a 0.4x
  debit). It is beta + the bot's edge, not a new edge: in a 2022-type bear it loses (−12.6% vs SPY −18.2%), and the
  worst month is −16%; 2020 (COVID) is not in the 2021-26 window — check the COVID rebuild before any use.
- Who pays: nobody new; the change is that the taxable money stops sitting in BIL / the bot instead of the index.
- Risks: Schwab house margin can be 100% on volatile names (the night leg) -> less overnight buying power than modelled;
  a margin call in a crash while 1.4x long; 2.0x gross intraday (SPY 1.0 + noise ≤ 0.75 + IBS) needs the 4x intraday rule
  or careful sizing; the wash rule (Roth must not buy QQQ/SMH) costs the Roth ~4% of its end value.
- Live code is untouched (not FOUND). If the user wants it: taxable = SPY/VOO core + the current legs on margin; the
  executor would need a "core" position it never sells and margin-aware sizing. A user decision.
- NEXT line: "R6-5 (index beat): stack the bot on a 100% SPY core in taxable: EH 22.1%/yr vs SPY 15.3% (2021-26 pre-tax,
  maxDD −27.8% vs −24.5%); combined plan +1.5/+4.7pp at $1k/mo (2021-23 misses +2), +2.6/+6.9 at $2k/mo; near miss."
