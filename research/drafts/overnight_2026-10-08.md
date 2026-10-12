# Overnight research loop, 2026-10-08

## Decisions waiting for the user
1. **Noise-leg lag fix**: branch `noise-lag-fix` (73e33c3, local, not pushed). Live decides one 30-min bar late
   (executor.py `last_done = last_minute-1`). Costs ~1.2bp/trade over 2016-26 and ~0.5bp since May 2024.
   Write-up is on the branch: `research/drafts/noise_lag_fix_2026-10-08.md`.
2. **The noise leg itself**: since 2024-06, QQQ+SMH +3.1..3.7bp/trade, t 1.5, Sharpe 0.1-0.2 at 1bp RT; negative at 2bp RT;
   2026 Jan-May slightly negative (`noise_recent_2026-10-08.md`). Marginal and cost-bound.
3. **POAS round-up (CPC deadline 10-09)**: Schwab rejects the bot's order daily ("must be placed with a broker"). Manual.
4. **VIVK round-up**: both accounts hold no VIVK and no post-split share, which suggests cash in lieu. Check the Schwab cash credit.
5. **CEF-RV panel**: run `make cef-rv-panel` on the Mac after Friday's close (the server IP is blocked).
6. **Tiny live Roth PREF test order** (CO vs CC): the best next lever decision (`levers_2026-10-08.md`).
7. Optional: Roth `moderate` profile (name cap 0.15), about +1.5-2pp at $1k (`roth_cash_2026-10-08.md`). Optional: Roth SMH
   look-alike SOXX -> SOXQ ($104 vs $589), about +2-5pp at $1k (`etf_twins_2026-10-08.md`).

8. **Roth night priority**: branch `roth-night-priority` (e958dd3, local). On 10-08 the Roth skipped 7 of 10 night picks
   ("book cash exhausted") because $441 sat in 3x noise longs until 15:57 and $402 in SGOV. The fix counts noise longs as
   night cash and sells SGOV if still short. About +1-3%/yr. Confirm the Roth cash-account settlement timeline at Schwab first.
   One existing test now runs with the flag off, because it pinned the old sizing. The full test suite was not run locally
   (no `alpaca` module).

## Deployed to him (log-only, pushed to main)
- f022d56: ROTH-STACK arm in the PREF-EX shadow (idle Roth cash -> pref/ETD ex-nights).
- 6ec35bd: daybook shadow replayed "today" before the open and logged 0 trades. Fixed; ledger repaired 10-01..10-07.
- fbb3140: daybook PROD flattens at 15:57 like live.
- 8cfb7d1: digest: AU3 count (now 15/wk, was 166) and the F3 line (no FOMC eve yet; next is 10-28).

## Studies (one look each; see CLAUDE.md memory and round1_prose.md)
| study | verdict |
|---|---|
| ROTH-STACK (N 897) | PASS-SMALL: +8.4pp at $3k, +5.4 at $10k; 3x cost -> +0.9..1.6 |
| QI-HIST (N 898) | DEAD: skipping the sell-heavy tercile gains +12bp/trade (gate needs +30) |
| EXDATE-OOS (N 899) | forward splits replicate on Sharadar (+82bp, median +43); spin-offs are outlier-carried |
| SPLIT-CROSS (N 900) | FAIL narrowly at the official crosses 2016-20 (t 1.73); 2021-26 liquid names median -17bp |
| FUND-STATE (N 901) | DEAD (wrong sign, no replication); night/IBS conditioning is a closed class (<1pp/yr) |
| PREF-INDEX | ceiling-kill + data-limited |
| Structural-event scan (23 ideas) | nothing new clears the gate |
| Thrift conversions (DL-G27) | real per deal, decaying (2023-25 median +2.3%); ~$0-80/yr EV; not actionable |

## Current regime (`recent_regime_2026-10-08.md`)
- Night leg (exact 15:40 rule, replay): 2026-06..10-07 +98bp/trade at 7.5bp/side (n 1581, t 2.3, median +74), front-loaded
  (Jun +169 ... Oct -149). Live trips match the replay (r 0.998); the live window was a bad stretch, not an execution problem.
- IBS leg (`recent_ibs_2026-10-08.md`): 2026 YTD +57bp/trade at 5bp/side (n 97, t 3.1); 2021-25 +5.8. Excess over the
  same-day top-3 basket is only +12..31bp (t 0.5-1.2), so 2026 is mostly basket beta. Live matches the replay (r 0.99).
- Noise leg: 2026 YTD -0.5bp/trade (no lag), -1.1 (lag); 2021-25 was +5.4. Currently not earning.
- Night-signal high/low already uses regular hours (`rth_hilo_2026-10-08.md`); the audit's 6% IBS mismatch was its own bar choice.

## Audits (no change needed)
- Live night: shadow +132bp vs realized +8bp is accounting (dollar weighting, missing sessions, unfilled buys). Roth night
  cost ~0bp/side: the 3bp rule passes. The Roth loss is the price bounce, not execution.
- Night/IBS fidelity: no one-bar-late bug. 15:42 vs 15:50 picks differ 23% but earn the same. About 6% of picks are IBS
  false positives from Schwab high/low (`fidelity_audit_2026-10-08.md`).
- Wash guard: cross-account only. Keep it: lifting it costs more in disallowed losses than it gains.
- Roth 10-05 cash drop: a manual $857 buy in the Roth, not a bug.
- Correction to the first chat report: taxable noise P&L is about +$1 (a 09-28 QQQ short, -$4, was mis-matched), not +$22.
