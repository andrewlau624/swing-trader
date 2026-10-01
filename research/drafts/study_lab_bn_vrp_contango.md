# Study Lab-BN — SVXY (−0.5x VIX futures) only in VIX/VIX3M contango, else BIL: DEAD (program N 728 -> 729)

Stamp: round1_prose.md Lab Round 38 (commit ab7497e). Script `daytrade/research/bn_replay.py`. The signal is day t's Cboe closes;
the position runs from opening cross to opening cross. 2018-03 .. 2026-09; in SVXY 92% of days; ~12 switches a year.

| | CAGR | max DD | excess vs BIL / month (1x) | 2x 2018-21 / 2022-26 | t | without best 5 | placebo |
|---|---|---|---|---|---|---|---|
| Lab-BN (1x) | 13.7% | −45% | +118bp | +167 / +60 | 1.5 | +51 | 75.6 |
| SVXY buy and hold | 11.9% | −63% | | | | | |
| SPY | 14.6% | −32% | | | | | |

By year (1x): 2018 −11.7%, 2019 +39.7, 2020 +10.4, 2021 +49.7, 2022 −14.5, 2023 +73.2, 2024 −18.0, 2025 +13.5,
2026 YTD +6.9.

**DEAD** (t 1.5 < 2; the timing beats random in/out days only at the 76th pct). The contango gate trims SVXY's drawdown
(−63% -> −45%) but the book still trails SPY with more drawdown. The premium is real; this rule does not make it pay
for the tail.
