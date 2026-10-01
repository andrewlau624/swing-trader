# Study Lab-CD — volatility-managed market exposure (Moreira & Muir 2017): DEAD (program N 744 -> 745)

Stamp: round1_prose.md Lab Round 51. Script `daytrade/research/cd_replay.py`. Monthly weight = c / last month's realised
variance (c fixed on 1927-62: 0.00087), capped at 2x; levered part financed at RF + 0.5% + 0.9% fee.

| period (1x) | book CAGR / Sharpe / max DD (mean weight) | market CAGR / Sharpe / max DD |
|---|---|---|
| judged 1963-2015 | 8.8% / 0.74 / **−37%** (0.91) | 10.0% / 0.70 / −50% |
| 1963-89 | 9.3% / **0.67** / −37% (1.06) | 10.6% / **0.73** / −46% |
| 1990-2015 | 8.4% / 0.90 / −13% (0.76) | 9.4% / 0.68 / −50% |
| ref 2016-26 | 9.3% / 0.86 / −23% (0.79) | 15.1% / 0.98 / −25% |

**DEAD**: the 1963-89 Sharpe is below the market's, and CAGR is below the market's in both halves (2x as well). It cuts
drawdowns (−50% -> −37%; −13% in 1990-2015) but earns less than the index everywhere, as Cederburg et al. (2020)
found out of sample. Not a %/yr lever for a small account.
