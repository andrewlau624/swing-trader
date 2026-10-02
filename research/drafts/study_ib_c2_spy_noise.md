# Index-beat C2: taxable = SPY core + the noise leg only; Roth = the book minus QQQ/SMH IBS (report, no N) — NOT FOUND (haircut-dependent)

Idea pre-written (index_beat_ideas.md C2, ff9eac7). Script `research/sim/ib_c2.py`, output `data/research/program/ib/c2_out.txt`.
Taxable C2: hold SPY (total return; dividends taxed at 20% yearly; gain taxed at 20% at the end) and run only the live
QQQ/SMH noise leg on top (intraday; SPY at 1.0x uses half the Reg-T buying power, the noise leg's <= 0.75x fits without
the 4x rule); noise P&L netted yearly at 35%, April payment, carry-forward and $3k deduction. Check: noise off
reproduces the C1 index ($41,241 = $41,241). Roth: the proposed book with its IBS leg never buying QQQ or SMH (the
taxable noise leg sells them at a loss most days; a Roth buy within 30 days would make that loss permanently disallowed).
Plan P as in study_ib_c1_location.md (G4s, live taxable book). IRR = combined money-weighted %/yr.

| cost | window | $1k/mo EH | $2k/mo EH | $1k/mo as backtested | $2k/mo as backtested |
|---|---|---|---|---|---|
| tier | 2021-23 | **+1.19pp** | +2.11pp | −1.68pp | −0.67pp |
| tier | 2024-26 | +2.01pp | +3.18pp | −1.02pp | +0.31pp |
| tier | full | +3.29pp | +4.88pp | −0.08pp | +1.67pp |
| tier_hi | 2021-23 | **+1.29pp** | +2.21pp | −1.39pp | −0.41pp |
| tier_hi | 2024-26 | +2.21pp | +3.36pp | −0.51pp | +0.75pp |
| tier_hi | full | +3.59pp | +5.15pp | +0.62pp | +2.32pp |

(The noise leg adds +9.2%/yr pre-tax EH in 2021-23 and +4.4% in 2024-26 on top of SPY; SPY-only taxable, C1 with the
same Roth, is −0.8 / +1.6pp at $1k/mo.)

- **Verdict: NOT FOUND.** At the user's $1k/mo the 2021-23 half is +1.2-1.3pp (< 2). It clears +2pp in both halves only at
  $2k/mo, and only under edge-halves: as backtested it loses −0.4..−1.7pp in 2021-23.
- What it says: **the taxable account's night + IBS legs are worth less than SPY after tax unless their edge is closer to
  the backtest than to half of it**. The noise leg is the one leg that clearly earns its tax bill on top of an index.
  It is a bet on the haircut, not an edge: live evidence decides it (the 2026 night pool's raw bounce is +1.8bp/night,
  Jan-Jul, vs +29.5bp in 2021-25: so far closer to EH).
- If the user wants the hedge anyway: taxable = SPY (or VOO) + `noise` leg only; Roth = the full book with QQQ/SMH IBS
  off (or SMH -> SOXX). This changes live code, so it is a user decision, not a switch this hunt makes.
- NEXT line: "C2 (index beat): taxable SPY + noise leg only beats the plan by +1.2/+2.0pp (2021-23/2024-26, $1k/mo, EH),
  +2.1/+3.2pp at $2k/mo; loses as backtested: a haircut bet, not FOUND."
