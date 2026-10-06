# Study VT-IBS: vol-tilted split of the IBS budget (N 836 -> 838) — VERDICT: KILL

Pre-reg: `round1_prose.md` (Amendment VT-IBS). Runner `research/sim/ibs_voltilt.py`, out `research/sim/ibs_voltilt_out.txt`.
Selection = live `book.ibs_days`; only the weights across simultaneous names differ (398 of 788 signal days have >= 2 names).

## Theory (plain text)
mu_i = k sigma_i (ibs_xasset_scan). Day growth g(w) = sum w_i mu_i - 0.5 sum w_i^2 sigma_i^2. Unconstrained Kelly
w_i = k/sigma_i. Measured leg Kelly f* = mean/var of the day return = 8.6 (2016-20), 7.5 (2021-26), 4.2 (2017-19): the
budget (sum w = 1) binds, so the constrained optimum w_i = (k sigma_i - lam)/sigma_i^2 tilts to the HIGH-vol name.
Prediction P: g=+1 > equal > g=-1 in mean day return.

## Results (paired vs equal weight, multi-name days, 1bp/side; cost is identical across arms so a 2-3x shock cannot change the paired gap)
| arm | 2016-20 judge | 2021-26 | 2017-19 ex-2020 |
|---|---|---|---|
| A g=+1 | -0.55bp, t -0.77, ex-top5 -1.16, hit 53% | +1.74bp, t 1.43 (NW 1.76), ex5 +0.25 | -1.44bp, t -1.45 |
| B g=-1 | +0.67bp, t 0.87, ex-top5 -0.54, hit 47% | -1.71bp, t -1.43 | +1.58bp, t 1.46 |
Placebo (shuffled weights, 2016-20): A at 19th pct, B at 85th. DSR(N=838): A 0.000, B 0.005. Median paired effect ~0 in all cells.
Growth per signal day (all days, 2016-20): equal 18.5bp, A 18.2, B 18.9; 2021-26: equal 19.0, A 19.8, B 18.2.

## Verdict
KILL both arms. Signs flip between 2016-20 and 2021-26 (A and B mirror images), no cell reaches |t| 2, ex-top-5
negative for both on the judge window, placebo inside noise, DSR ~0. Prediction P is not supported on the judge window:
the within-leg weighting is noise. Paper ceiling was already <= ~0.2 pp/yr of account (paired ~1bp x ~40 days x 0.5
leg), far under the +8pp gate; the Sharpe moves by ~0.003/day, i.e. nowhere near +0.05. Not worth shipping.
Do-not-redo: IBS within-leg vol weighting (either sign), and by extension James-Stein shrinkage of per-name IBS edge (collapses to the k*sigma prior).

## Killed on paper (no run)
- Covariance-aware fractional Kelly across legs: dead already (Goal L1/L2 concentration, `Kelly dial`, Round 18 AS softmax/inverse-vol budget, add. 32 vol-targeted gross, add. 40).
- Drawdown-constrained growth: P(DD) budgets already encode it (moderate10, add. 40); ceiling is a risk dial, not return.
- Per-name James-Stein: top-3 rotate monthly, ~50 trades/name; the shrinkage weight -> 1 so it equals the tested sigma prior.
Useful side fact: f* >> 1 for the IBS leg means more exposure (not better weights) is what pays; that is the already-shadowed ACC 3x overlay (cap 1.25x), not new.
