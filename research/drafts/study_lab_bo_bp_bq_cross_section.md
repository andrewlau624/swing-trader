# Studies Lab-BO / BP / BQ — monthly cross-sectional anomalies on the 500 most-traded stocks: all DEAD (program N 729 -> 732)

Stamp: round1_prose.md Lab Round 39 (commit f385248). Script `daytrade/research/bo_replay.py` (Lab-BJ's frame). Long the top
20, equal weight, monthly, 2017-01 .. 2026-09; excess vs the equal-weight universe (CAGR 12.4%).

| study | 1x excess / month | 2x 2017-21 / 2022-26 | t | without best 5 | placebo | CAGR (1x) | Sharpe H1 / H2 (book vs universe) |
|---|---|---|---|---|---|---|---|
| Lab-BO 52-week-high (George & Hwang) | −8.5bp | −21 / −36 | −0.3 | −39 | 70.8 | 11.8% | 1.17 vs 0.92 / 0.45 vs 0.54 |
| Lab-BP low volatility | −50bp | −51 / −91 | −1.4 | −88 | 7.8 | 6.6% | 0.90 vs 0.92 / 0.11 vs 0.54 |
| Lab-BQ 1-month reversal | +13bp | +17 / **−33** | 0.2 | −101 | 94.4 | 6.9% | 0.50 vs 0.92 / 0.22 vs 0.54 |

**All DEAD.** In 2017-26 large caps, nearness to the 52-week high adds nothing. Low vol lags badly in a rising market
(and its Sharpe is worse in 2022-26). Short-term reversal worked in 2017-21 but not after.
