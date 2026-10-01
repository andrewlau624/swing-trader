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

## Lab-BR — 12-1 momentum (Lab Round 40): DEAD by t, the closest call of the lab
| | 1x excess / month | 2x 2017-21 / 2022-26 | t | without best 5 | placebo | CAGR (1x) vs universe | Sharpe H1 / H2 (book vs universe) |
|---|---|---|---|---|---|---|---|
| Lab-BR | +131bp | +0.9 / **+225** | **1.5** | +16 | 100 | **22.6%** vs 12.2% | 0.52 vs 0.89 / higher in H2 |

- It fails only t >= 2. Nearly all the excess is 2022-26 (the AI-led rally), and 2017-21's Sharpe was worse than the
  universe's. That is the known momentum-factor profile (a priced risk with crash risk), not an anomaly that survives
  the bar.
- **Watch, not adopt.** A future look needs a NEW registration with longer history (pre-2016 data) and a crash-risk
  bound. Nothing re-tuned.
- (The first run printed t = NaN: an early month without a full 13-month signal gave an empty portfolio. Fixed by
  skipping months without a full signal. BO/BP/BQ unchanged.)

## Lab-BS — sector-SPDR 12-1 momentum, top 3 monthly (Lab Round 41): DEAD
| | 1x excess / month vs EW sectors | 2x 2017-21 / 2022-26 | t | without best 5 | placebo | CAGR (1x) vs EW sectors / SPY |
|---|---|---|---|---|---|---|
| Lab-BS | +11bp | **−31** / +35 | 0.6 | −9 | 89.4 | 13.6% vs 12.1% / 15.1% |

By year (1x): 2022 +159bp/month (energy) carries it; 2019 −54, 2021 −76. Trails SPY. **DEAD.** (The SIP history starts
2016-01, so the first full 12-1 signal is 2017-02; 116 test months.)
