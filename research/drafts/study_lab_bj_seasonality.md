# Study Lab-BJ — calendar-month return seasonality (Heston & Sadka): DEAD (program N 723 -> 724)

Stamp: round1_prose.md Lab Round 34 (commit 7f5f933). Script `daytrade/research/bj_replay.py`. Monthly SIP bars (adjusted
returns, raw price filter), top 500 by trailing dollar volume, top 20 by the 5-year same-month mean, 2021-01 .. 2026-09
(69 months).

| | excess vs EW universe / month, 1x | 2x H1 / H2 | t | without best 5 | placebo pct | portfolio / universe per yr (gross) |
|---|---|---|---|---|---|---|
| Lab-BJ | **−69bp** | −110 / −67 | −0.8 | −198 | 3.9 | −1.3% / +9.9% |

By year (1x): 2021 −200, 2022 −199, 2023 +129, 2024 +24, 2025 +39, 2026 −255.

**DEAD.** The seasonality anomaly does not show in the large-cap universe in 2021-26: the picks did worse than random
universe names. Nothing re-tuned.
