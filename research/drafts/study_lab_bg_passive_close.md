# Study Lab-BG — closing-imbalance signal with passive entry: DEAD on the H2 holdout (program N 716 -> 717)

Stamp: round1_prose.md Lab Round 31 (commit fda3fb1). Script `daytrade/research/bg_replay.py`.
- Lab-BC's signals (top-quartile |imbalance/paired| at 15:54:30), a limit at the 15:54:31 touch until 15:55:00.
- If filled, exit market-on-close at the official close.
- Fills from Alpaca SIP trades.

**The first run "PASSED" on a wrong fill model**, kept as results_v1_subpenny.json. It counted off-exchange (TRF, "D")
prints at sub-penny prices (e.g. $32.9969 against a $33.02 bid) as trading through a lit limit. They are internalised
retail flow and never fill a resting order. The corrected model ignores TRF prints and needs a full tick through, or
the queue used up by lit prints.

| H2 holdout (judged) | fill rate | fills/day | filled: mid -> close | from the limit | 1x net (t) | 2x | without top 20 | placebo |
|---|---|---|---|---|---|---|---|---|
| v1 (wrong: sub-penny TRF fills) | 89% | 1.7 | +4.3 | +8.8 | +7.8 (6.4) | +6.8 | +5.6 | 100 |
| **v2 (corrected)** | **66%** | 1.3 | **−0.6** | +3.2 | **+2.2 (1.6)** | +1.2 | **−0.7** | 99.6 |
| v2 H1 (reference) | 72% | 1.7 | +3.7 | +6.9 | +5.9 (5.3) | +4.9 | +3.8 | 100 |

## Reading
- **Adverse selection eats the signal.** The orders that fill are those where the price came to the limit, i.e.
  moved against the imbalance's direction. Filled trades earn −0.6bp mid -> close in H2; the unfilled ones would
  have earned +19bp.
- What remains is the captured half-spread: +2.2bp net, t 1.6, negative without the top 20. **DEAD** (t and the
  outlier check fail). It was strong in H1 (t 5.3) and weakened from mid-2024 (closing-imbalance signals decayed in
  Lab-BD too).
- If it is ever revisited: only as a forward paper shadow, where the fill model is the real broker.
