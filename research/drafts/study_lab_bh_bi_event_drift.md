# Studies Lab-BH / Lab-BI — announcement-gap drift: long DEAD; the 2022-26 reversal fails out of sample (2017-21)

Event: common stock, prev close >= $5, ADV20 >= $20M; day 0 opens >= +5% above the previous close on >= 3x its 20-day
average volume (an earnings/news proxy; no calendar). Entry: day 1's opening cross. Exit: day H's closing cross.
Adjusted prices for returns; raw for the filters. Scripts: `daytrade/research/bh_replay.py`, `bi_replay.py`.

## Lab-BH (Lab Round 32, 2022-01 .. 2026-09): DEAD as a long — the drift is a REVERSAL
| | n | excess vs SPY, 1x (median) | 2x H1 / H2 | month-clustered t | without top 20 | placebo | by year (1x excess) |
|---|---|---|---|---|---|---|---|
| Lab-BH1 hold 20d | 4,213 | **−185bp** (−194) | −162 / −233 | −3.1 | −242 | 0.0 | 2022 −71, 2023 −175, 2024 −157, 2025 −188, 2026 −300 |
| Lab-BH2 hold 5d | 4,213 | −85bp (−90) | −98 / −109 | −2.5 | −142 | 0.1 | 2022 +74, 2023 −136, 2024 −86, 2025 −124, 2026 −95 |

10-slot portfolio, 1x: $2.3k -> $744 (BH1) over 4.7 years.

## Lab-BI (Lab Round 33): short + SPY hedge, judged ONLY on unseen 2017-01 .. 2021-12 — DEAD
| | n | 1x net (median) | 2x 2017-19 / 2020-21 | t | without top 20 | placebo | by year (1x) |
|---|---|---|---|---|---|---|---|
| Lab-BI1 all events | 3,431 | +68 (+90) | **−36** / +116 | **0.6** | +26 | 100 | 2017 +3, **2018 −91**, 2019 +44, **2020 −159**, 2021 +420 |
| Lab-BI2 easy-to-borrow only | 2,679 | +30 (+42) | **−43** / +51 | **0.3** | **−20** | 100 | 2017 −87, 2018 +34, 2019 −8, **2020 −188**, 2021 +345 |

## Reading
- The 2022-26 fade of announcement gappers is a **regime**, the post-2021 speculative/meme era, not a stable anomaly.
  In 2017-21 shorting them loses in 2018 and 2020 and wins only in 2021. t 0.3-0.6.
- The classic drift (long) does not hold in 2022-26 either.
- Family closed. The out-of-sample discipline (judging the mirror on years nobody had looked at) is what prevented
  shipping a 2022-26-only short.
