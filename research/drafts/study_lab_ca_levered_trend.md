# Study Lab-CA — 3x daily-levered market with a 200-day trend exit (Gayed & Bilello 2016): DEAD on its risk bars (program N 741 -> 742)

Stamp: round1_prose.md Lab Round 49 (commit 65591ae). Script `daytrade/research/ca_replay.py`. French daily market (CRSP 202608),
simulated 3x daily fund (financing RF + 0.5%, 0.95% expense); in the fund while the market > its 200-day average, else
T-bills; switch cost 10bp. About 5-7 switches a year; in the market ~73% of days.

| period (1x) | sleeve CAGR / Sharpe / max DD / worst 12m | market | 3x buy and hold (no filter) |
|---|---|---|---|
| **judged 1963-2015** | **17.4% / 0.67 / −75% / −55%** | 10.0% / 0.69 / −55% / −43% | 10.1%, max DD −98% |
| 1963-89 | 22.5% / 0.87 / −47% / −38% | 10.7% / 0.83 / −48% | |
| 1990-2015 | 12.4% / **0.51** / −75% / −55% | 9.4% / **0.59** / −55% | |
| ref 1927-63 | 26.4% / 0.83 / −78% | 8.2% / 0.52 / −84% | |
| ref 2016-26 (simulated) | 25.2% / 0.80 / −49% | 15.2% / 0.86 / −34% | 29.0%, −77% |
| **real UPRO / SPY / BIL, 2016-26** | **24.5% / 0.81 / −51% / −40%** | SPY 15.0% / 0.89 / −34% | UPRO 29.2%, −77% |

**DEAD**: (b) fails (the 1990-2015 Sharpe is below the market's) and (c) fails (the worst 12 months −55% vs the −50%
bound). (a) and (d) pass.

## Reading
- It earns far more than the index in most periods (17-26%/yr), but it is LEVERAGE, not an edge: its Sharpe is about
  the market's.
- The 200-day exit turns 3x buy-and-hold's ruin (−98%) into a survivable −75%. That is still a 75% loss, and the
  bound registered for a small account was −50%.
- For the user's %/yr priority this is the honest trade-off: ~+9 points a year over 2016-26 (real UPRO) for drawdowns
  of −50% (and −75% in history). The live book already has the levered profiles (add. 22/32) and their P(DD) budgets.
  This adds no new edge. Nothing built.
