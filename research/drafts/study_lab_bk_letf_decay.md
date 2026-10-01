# Study Lab-BK — short both legs of a 3x LETF pair (volatility drag), weekly: DEAD (program N 724 -> 726)

Stamp: round1_prose.md Lab Round 35 (commit de97e28). Script `daytrade/research/bk_replay.py`. Adjusted SIP daily closes
2016-01 .. 2026-09; short 0.5E per leg, rebalanced at each week's last close.

| | gross / week | 1x net / week (CAGR, max DD) | 2x 2016-20 / 2021-26 | t | without best 5 | corr vs index |
|---|---|---|---|---|---|---|
| Lab-BK1 TQQQ+SQQQ | +7.3bp | +1.3bp (+0.5%/yr, −16%) | −3.6 / −11.3 | 0.4 | −3.3 | −0.20 |
| Lab-BK2 UPRO+SPXU | +1.6bp | −4.4bp (−2.3%/yr, −23%) | −10.3 / −15.9 | −1.8 | −7.8 | −0.11 |
| reference QQQ+PSQ | −2.4bp | −8.3bp | | | | |

Lab-BK1 by year (1x): 2020 +19.1%, 2022 +8.1%, 2023 −5.9%, 2024 −6.7%, others about −2 to +1%.

## Reading
- The theoretical drag (3σ² and 6σ² a year) is earned by a holder against DAILY rebalancing. A short pair rebalanced
  weekly keeps only the difference between daily and weekly variance: about 3.8%/yr gross on QQQ. It pays off only
  in violent choppy years (2020, 2022).
- Shorts also pay the inverse ETFs' distributions (their T-bill interest, ~4-5%/yr since 2023; in the adjusted
  prices). The reference pair shows that cost alone.
- After 2-4%/yr borrow it is ~0; after 5-10% (the HTB reality of SQQQ/SPXU) it is negative. **DEAD.**
