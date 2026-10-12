# Noise leg (QQQ+SMH, daybook PROD) in recent years, no-lag vs one-bar lag (2026-10-08)
Runner: `research/sim/noise_recent.py` (signal code copied from `swingtrader/daybook/shadow.py::replay_instrument`, no tuning;
data = `data/research/night/m1` SIP minute cache 2016..2026-05, PROD weights 0.5/0.5, target_vol .02, max_lev 3.5, flat 15:57).
Lag = decision at 30-min bar m, fill at the m+30 print (clipped to the 15:57 flatten). `noise_lag_fix_2026-10-08.md` was not on disk,
so the lag was rebuilt from the live coids (`noise-sell-m60` filled 15:01 UTC = m90). Check: all-sample combined at 1bp RT gives
no-lag +3.63 (t 4.1, n 5238) and lag +2.48 (t 3.1), vs tonight's +3.62 / +2.44 (n 5211).
Units: bp per trade, unlevered, net of cost; cost c per fill (RT = 2c). Sharpe = annualised, daily P&L (levered, trade-weighted, zero on no-trade days).

## Headline (combined QQQ+SMH; mean bp / t / hit% / Sharpe)
| period | n | no-lag 0.5bp/fill (1bp RT) | lag 0.5bp/fill | no-lag 1bp/fill | lag 1bp/fill | no-lag 2bp/fill | lag 2bp/fill |
|---|---|---|---|---|---|---|---|
| 2016-24.05 | 4148 | +3.62 / 3.9 / 39 / +0.58 | +2.31 / 2.7 / 45 / +0.05 | +2.62 / 2.8 / +0.17 | +1.31 / 1.6 / -0.38 | +0.62 / 0.7 / -0.62 | -0.69 / -0.8 / -1.22 |
| **post 2024-06** | 1090 | **+3.65 / 1.5 / 39 / +0.14** | **+3.14 / 1.5 / 46 / +0.22** | +2.65 / 1.1 / -0.18 | +2.14 / 1.0 / -0.15 | +0.65 / 0.3 / -0.81 | +0.14 / 0.1 / -0.86 |
| all | 5238 | +3.63 / 4.1 / +0.48 | +2.48 / 3.1 / +0.08 | +2.63 / 2.9 / +0.09 | +1.48 / 1.9 / -0.33 | +0.63 / 0.7 / -0.66 | -0.52 / -0.7 / -1.15 |

Post-2024-06 by symbol at 0.5bp/fill, mean/t/Sharpe: QQQ no-lag +2.54/0.9/-0.07, lag +2.32/0.9/+0.06; SMH no-lag +4.75/1.2/+0.33, lag +3.95/1.2/+0.34.
Medians: no-lag about -8bp, lag exactly -1.0 (gross 0). 6.6% of lagged trades are zero-duration (15:30 entries filled at the 15:57 flatten price, which live
could not take); dropping them lifts lag all-sample to +2.73 and post-2024 to +3.44 (t 1.55). It does not change the conclusion.

## Per year, combined, 0.5bp/fill (mean bp / t / Sharpe), no-lag | lag
2016 +2.0/1.0/-0.25 | +2.1/1.1/-0.07;  2017 +1.4/0.9/+0.26 | -0.3/-0.2/-0.86;  2018 +8.2/2.6/+1.53 | +7.7/2.8/+1.47;  2019 -1.7/-0.9/-1.02 | -4.4/-2.4/-2.18;
2020 +2.2/0.6/+0.80 | +3.6/1.3/+0.63;  2021 +8.3/2.9/+1.30 | +5.6/2.2/+0.75;  2022 +7.1/2.0/+1.21 | +3.7/1.1/+0.82;  2023 +3.3/1.2/+1.02 | +2.2/1.0/+0.83;
2024 +2.8/0.9/+0.62 | +2.5/0.9/+0.17;  2025 +5.3/1.3/-0.05 | +4.7/1.4/+0.54;  **2026 YTD (to May, cache end) -0.2/-0.1/-0.65 | -1.1/-0.3/-1.00**.
At 1bp/fill 2026 is -1.2 / -2.1 bp and Sharpe -1.0 / -1.3. Full per-symbol/per-cost grid: rerun the runner (prints every cell).

## Verdict
1. Post-2024-05 the leg is positive in mean (+3.1 to +3.7bp/trade at the live 1bp RT) but not distinguishable from zero (t 1.5, n 1090, Sharpe 0.1-0.2), it halves at 2bp RT, and is ~0 at 4bp RT. 2026 YTD is negative (-0.2 no-lag, -1.1 lag, Sharpe -0.7/-1.0).
2. The lag costs ~0.5bp/trade post-2024 (3.65 vs 3.14, difference well inside noise; lagged Sharpe is even slightly higher). Most of the lag penalty is pre-2024 (3.62 vs 2.31). The lag fix therefore adds little where it matters now: it is NOT the thing deciding whether this leg earns. The leg itself is marginal-to-unproven recently, and entirely cost-bound (consistent with noise_audit and study_noise_decay). Whether to keep it is the user's call.
3. Cache ends 2026-05, so 2026 YTD is Jan-May only; the Sep/Oct live days came from Alpaca SIP via `shadow._sessions_alpaca`.

## Live noise fills vs replay (QQQ/SMH, taxable book `dly.*`, fill-to-fill round trips; 7 trips, 4 days; far too few to judge)
| day | sym | live bp (gross, unlevered) | lag replay | no-lag replay |
|---|---|---|---|---|
| 09-28 | QQQ short | -56.4 | -54.6 | -37.8 |
| 09-28 | SMH short | -99.7 | -91.4 | -74.8 |
| 09-28 | SMH short | +10.0 | +5.0 | -31.0 |
| 09-30 | QQQ long x2 | +3.0, +2.6 | +11.8 (one trip) | -3.1 |
| 10-01 | SMH long | +25.4 | +25.8 | -7.9 |
| 10-05 | QQQ long | +15.9 | +18.8 | +30.7 |
Live mean -14.2bp, median +3.0, 5/7 up (09-28 shorts into a rally dominate). The lagged replay reproduces live fills within a few bp on 09-28, 10-01, 10-05 (confirms the one-bar lag is what live does); the no-lag replay does not. 09-23/24 fills are partial (no complete trips in the logs) and 10-05 SMH short in the replay was not traded live (whole-share sizing). Roth (`dlv`/`dlr`, incl. TQQQ/SOXL) fills mirror these.
