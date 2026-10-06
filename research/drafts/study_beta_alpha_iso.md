# Diagnostic: beta/alpha isolation of the book, IBS, night, noise (2026-10-05; no N bump)
Pre-registered (factors, windows, A/B/C rule) in `round1_prose.md` "Diagnostic amendment" before outputs were read.
Code `research/sim/beta_alpha_iso.py`; full output `research/sim/beta_alpha_iso_out.txt`. Factors window-matched
(MKT=SPY, TECH=QQQ-SPY, SIZE=IWM-SPY, MOM=MTUM-SPY, adjusted bars); night/IBS factors scaled by invested fraction;
alpha arithmetic x252, Newey-West(5) t; OOS = expanding window, betas from earlier years only.

## Results (book = V7 via Sim.replay, 2021-02..2026-09, night 2.5bp; night/noise window is FITTED)
| object | raw %/yr | alpha %/yr (t) | systematic share | OOS pooled alpha (t, +yrs) | class |
|---|---|---|---|---|---|
| total book (ex-cash) | 37.6 | 23.5 (4.3) | 37% | 21.8 vs raw 38.2 (2.9, 4/4) | B (57% < 60% bar) |
| night | 20.3 | 15.2 (3.1) | 25% | 15.0 vs 22.8 (2.3, 4/4) | A mechanically, see caveats |
| IBS leg in book | 8.1 | 0.2 (0.1) | 98% | 1.0 vs 9.0 (0.4, 2/4) | C |
| noise (unscaled) | 9.3 | 8.1 (3.1) | 13% | 5.0 vs 5.7 (1.5, 3/4) | B |
| IBS sleeve excess-of-cash 2017-26 | 15.5 | 1.0 (0.4) | 93% | -0.3 (-0.1, 4/8) | C |

IBS sleeve vs buy&hold (open->open): 2017-20 CAGR 16.8% Sharpe 1.13 maxDD -13% vs SPY 15.6/0.82/-32 and QQQ 28.5/1.21/-28;
2021-26 19.6% / 1.05 / -17% vs SPY 15.3/0.75/-26, QQQ 17.0/0.67/-37, TQQQ 25.4/0.63/-82. SPY scaled to the same ~32%
utilisation: 6-7%/yr; IBS beats it by +11%/yr (t 2.7) but the 4-factor residual of that excess is ~0 (beta 0.9-1.05, plus
MOM/SIZE/TECH loadings). IBS exposure-scaled R2 0.60-0.80.

IBS trade level (every-top-3 control, placebo of same day count): 2017-20 OOS IBS +29.8bp vs control +9.4 (premium +20.3;
beta-adjusted +16.8; 4-factor residual IBS-specific +6.7bp/day, placebo pct 99, Welch t 1.5). 2021-26 +21.6 vs +7.8
(beta-adj +8.5; residual -0.5bp/day, placebo pct 45). Split of the premium: 2017-20 market-day timing +0.8bp, ETF
selection +17.4bp; 2021-26 timing +10.3bp (signal days are SPY dip days), selection +4.7bp. The IBS premium is therefore
real OOS pre-2021 as ETF-level selection, but in the fitted window most of it is dip-day equity beta/timing.

Night: market explains 18% of raw, tech 5%, size 2%, mom -1%; residual alpha 15.2% (t 3.1). By sub-period own-fit alpha:
2021-22 9.9 (t 1.7), 2023-24 8.5 (t 1.2), 2025-26 28.0 (t 2.4); OOS per year 2023 +3.7, 2024 +11.5, 2025 +39.9, 2026 +1.2.
Beta-isolation does NOT kill the night leg in 2021-26, but 2025 alone carries the OOS pool, window is the fitted one, and
the exact 15:40 pre-2021 test (CLAUDE.md part 3) is ~0 outside 2019-20. Not rescued, not proven.

## Portfolios (fractional risk stats; $ = S x whole-share CAGR, static account, pre-tax; IBS 1bp/side, TME 2bp/side)
2021-26: A V7 CAGR 45.1% vol 16.6 DD -12.8 Sharpe 2.14, OOS alpha(ex-cash) 21.8%, dollar-beta 0.38, util 40%.
B IBS 19.5/15.1/-16.8/1.05, alpha 2.5 (t 0.6), beta 0.31, util 33%. C IBS+TME 18.1/15.1/-19.5/0.97. D (IBS 1.25x+TME)
20.6/18.5/-23.6/0.93. TME alone 5.0/5.3/-4.7/0.34, alpha 4.5 (t 2.2), beta 0.0, util 14%.
2017-26: B 18.3/14.4/-16.8/1.07, alpha 3.2 (t 1.2), OOS 2.2 (t 0.6, 4/8); C 18.8/14.4/-19.5/1.10, alpha 4.8 (t 1.6);
D 21.4/17.8/-23.6/1.05; TME alone alpha 4.9 (t 3.4), OOS 4.9 (t 2.8, 6/8). 2017-20 holdout C beats B (20.2 vs 16.9%, DD -10.7 vs -13).
Recovery: A 27d, B 67d, C/D ~165d (2021-26). Worst 5d/20d: A -6.8/-12.2, B -9.2/-13.0, C -9.2/-14.6, D -11.5/-17.6.
$/yr at $1k/$3k/$5k/$10k/$25k (2021-26): A 413/1295/2252/4496/11364; B 176/570/958/1927/4855; C 155/525/890/1788/4504;
D 190/606/1014/2048/5134; TME 49/147/246/495/1236. IBS cost shock 3bp/side: B 2017-26 CAGR 18.3 -> 14.5%.

## Classification and meaning
Book = B by the frozen rule (OOS alpha is 57% of raw, bar 60%; t 2.9, 4/4 years). The independent alpha sits in night and
noise, both in their fitted 2021-26 window and unverified by exact pre-2021 evidence; the one OOS-validated leg (IBS) is C
after isolation (a beta/tilt/dip-timing sleeve with a better Sharpe and ~half the drawdown of SPY, not residual alpha).
TME is the only component with beta 0 and positive OOS alpha but tiny capacity (14% util, ~$50/yr per $1k).
Stacking TME adds ~0.5pp CAGR and worsens DD vs IBS alone; 1.25x adds return, Sharpe flat, DD -23.6%.

## Caveats
Single regime 2021-26; OOS here is beta-out-of-sample, not rule-out-of-sample (rules fitted on 2021-23); night/noise
2025 outlier; noise exposure sign unobserved so its beta is ~0 by construction; replay at 2.5bp night cost (live ~0, tier_hi
would cut); factors are total-return adjusted while IBS legs use raw prices (<0.3%/yr bias); portfolio sums legs on
slightly offset date labels; TME on adjusted TLT prices, equal-split on overlap, daily rebalanced shares; whole-share $
for B-E ignore tax; 2026 is YTD; last TME month excluded.
