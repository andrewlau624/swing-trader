# Study Lab-BL — distance-method stock pairs (Gatev, Goetzmann & Rouwenhorst 2006): DEAD (program N 726 -> 727)

Stamp: round1_prose.md Lab Round 36 (commit d09c954). Script `daytrade/research/bl_replay.py`. Top 100 stocks by formation
dollar volume, 20 min-SSD pairs per 6-month period (20 periods, 2017-01 .. 2026-09), open at 2 SD, close at the
crossing, adjusted SIP daily closes.

| | monthly net, 1x | 2017-21 / 2022-26 (1x) | 2x 2017-21 / 2022-26 | CAGR (1x) | max DD | t | without best 3 | placebo |
|---|---|---|---|---|---|---|---|---|
| Lab-BL | **−13bp** | −10 / −16 | −15 / −21 | −1.6% | −20% | −1.6 | −19 | 68.5 |

By year (1x): negative in 8 of 10 years (best 2019 +1.4%, 2026 YTD +1.4%; worst 2022 −5.8%).

**DEAD**, as the literature's post-2002 decay predicted (Do & Faff 2010). Min-distance pairs among mega caps do not
reconverge after 10-40bp of round-trip costs, and are no better than random pairs.
