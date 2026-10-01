# Report (Round 26): the "everything on" book simulated as one book, not a sum of estimates (no N)

Script `research/sim/everything_on.py`; output `data/research/program/everything_on_out.txt`. Night returns on the
official crosses (Study AW); the program's live sizing map (`growth.cfg`: overnight gross, conviction weight,
intraday multiplier -> weights, noise cap, margin interest 12%/yr on the debit); fixed capital; levers added
cumulatively.

| step (fixed $10k) | 2.5bp/side: CAGR / Sharpe / maxDD | after 32% tax | step | tier_hi CAGR | step |
|---|---|---|---|---|---|
| S0 live today (g 1.0, mult 2.48) | 39.4% / 2.01 / −14% | 26.8% | | 22.3% | |
| S1 + tug-of-war tilt (AU3) | 42.7% / 2.14 / −12% | 29.0% | +3.3pp | 25.3% | +3.0 |
| S2 + 15% name cap | 51.4% / 2.23 / −16% | 35.0% | +8.7pp | 28.2% | +2.9 |
| S3 + conviction 0.5 | 60.3% / 2.22 / −17% | 41.0% | +8.9pp | 35.7% | +7.5 |
| S4 + 4x intraday | 64.9% / 2.20 / −17% | 44.2% | +4.6pp | 39.6% | +3.9 |
| S5 + 1.3x overnight | **76.6% / 2.21 / −21%** | **52.1%** | +11.7pp | 42.0% | +2.4 |

- Same shape at $2.3k (37.6% → 75.5%) and $25k (39.9% → 77.0%).
- Every step is positive in both halves (2021-23 / 2024-26) at 2.5bp.
- 5-year P(DD > 50%) is 0% at every step ($10k).
- **Cost decides the size of the prize.** At tier_hi, everything on is 42%, not 77%. The 15% name cap and
  1.3x overnight lose most of their value (+2-3pp each): both scale the night leg, which is the cost-sensitive
  leg. Conviction and 4x intraday hold up (+7.5 / +3.9pp).
- **Correction to the weekly digest:** its backtest lines used 31% + 15pp (a sum of separately measured gains,
  on the Round 18 book's tighter intraday cap). The simulation under the live sizing map is 39% and +37pp. The
  digest's BACKTEST constants are updated; the plan lines are unchanged.
- These are backtests on 2021-26, and the order of the gates in NEXT.md stands: each lever switches on only
  when its live evidence clears. The night-leg levers (name cap, 1.3x) should wait for live night costs to
  confirm ≤ ~3bp/side, because their value collapses at higher costs.
