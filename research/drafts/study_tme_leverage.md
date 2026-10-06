# Study TME-L2 — capital efficiency of TME via leveraged Treasury ETFs (pre-registered)

**Status:** PRE-REGISTERED, one look, research only. NO DEPLOYMENT, NO LIVE SIZING, NO MARGIN CHANGES.
Registered 2026-10-05. Program N 822 -> 823. Priors cited (not re-derived): Study TME (validated
on untouched 2002-15, +32.3bp/mo net) and TME-L instrument history (`tme_l_hist_out.txt`, report only).

Question (user): does modest leveraged Treasury-ETF exposure make TME a materially better
small-account profit generator — i.e. more **$/yr per $1,000 of account capital** without
unacceptable drawdown or path-dependent ETF drag? NOT "does leverage raise CAGR".

## Frozen signal (unchanged)

TME1: buy at close(T-3), sell at close(T), T = the month's last session (>= 8 sessions), 12
windows/yr. Duration/benchmark month-end extension mechanism. No retuning of timing or entry days.

## Frozen implementation arms (per unit of sleeve capital C)

Costs/side — TLT 2bp, TMF 5bp, UBT 15bp (as in `tme_shadow.py`); margin debit 12.5%/yr act/360;
idle cash earns the 13-week T-bill (^IRX) rate.

- **A** TLT 1.0x (unlevered reference)
- **B** TLT 1.25x synthetic (Reg T margin)
- **C** UBT 2x (ProShares Ultra 20+yr)
- **D** TMF 3x (Direxion 20+yr)
- **E** 0.5 TLT + 0.5 TMF (≈2x effective, cheaper/non-callable than margin, no 15bp UBT cost)
- Report-only synthetic TLT m ∈ {1, 1.25, 1.5, 2, 2.5, 3} for the risk-budget cap.

## Account model (whole-share)

Sizes $1k / $2.3k / $3k / $5k / $10k / $25k. Buy floor(alloc/price) shares at close(T-3), sell at
close(T); remainder in T-bills. Daily mark-to-market (close) for drawdown; 30% tax on each year's
net gain, loss carried forward; no deposits. Report realised exposure, idle cash, effective
leverage, annual $, after-tax return, maxDD, worst window, worst rolling 5/20-day loss,
financing/ETF drag, capital utilisation.

## Risk budget

For each arm, the max defensible leverage m such that account maxDD <= 20% / 25% / 33%. The cap is
a risk constraint, not a CAGR optimum.

## Judge

- **PROMISING** if some leverage arm gives materially more $/yr per $1,000 than TME 1x AND beats the
  IBS 1.25x route ($/k) OR does so with lower drawdown, within a 25% DD budget, and the ETF drag is
  not the dominant term.
- **SMALL / NON-SCALABLE** if leverage helps but the $/k stays below IBS.
- **REJECTED** if the apparent gain is ETF path/decay, dominated by drag, or breaches the budget.
- Always report the cross-edge comparison (IBS 1x/1.25x vs TME 1x/levered) and whether the right
  answer is simply "more IBS + modest TME".

Runner `research/sim/tme_leverage.py` -> `data/research/program/tme_leverage_out.txt`; one look.
