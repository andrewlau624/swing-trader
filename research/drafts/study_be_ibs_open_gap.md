# Study BE (Round 27) — skip IBS entries indicated to open well above the prior close: DEAD (N 705)

Pre-registration: `round1_prose.md` Round 27 (commit 24463d9, before any data). Data: Databento opening-auction
`imbalance` messages 09:27-09:29 ET on IBS entry days 2018-05..2026-09 (ARCX.PILLAR for 16 ETFs, XNAS.ITCH for
QQQ/SMH; ~$1; cached in `data/research/night/ibs_open_imbalance.parquet`), indicative price vs the prior official
closing cross (Alpaca auctions, raw). Script `research/sim/ibs_gap_study.py`; output
`data/research/program/ibs_gap_study_out.txt`.

## Coverage (caveat)
1,214 IBS entries since 2018-05; **only 31.1% have an opening message in the window** (the Arca feed is sparse
before 09:29). Entries without a gap are kept, as registered. Median indicated gap +30bp; 13% are ≥ +0.5%, 8% ≥ +1%.

## Per-entry open→open net (−2bp)
| | gap T1 / T2 / T3 | gap ≥ 0.5% | gap ≥ 1% |
|---|---|---|---|
| 2018-05..20 | +108.6 / +51.6 / +53.9bp | +29.6 (n 60) | +40.4 (n 32) |
| 2021-23 | +61.8 / −6.6 / +14.2bp | +4.9 (n 46) | +20.1 (n 26) |
| 2024-26 | +25.0 / −17.8 / +68.9bp | **+51.1 (n 55)** | **+83.7 (n 37)** |

## Book (2.5bp/side judged)
| | V7 $10k inc (halves) | NW t | placebo / shuffle | unit IBS 2018-05..20 |
|---|---|---|---|---|
| BE1 skip gap ≥ 0.5% | −1.89pp (−0.03 / −3.12) | −1.46 | 7% / 90% | −5.2pp |
| BE2 skip gap ≥ 1.0% | −1.99pp (+0.05 / −3.34) | −1.62 | 4% / 38% | −3.4pp |

## Verdict: DEAD, both
A gap-up indication does not mean the bounce is used up. Gap-up entries earn as much or more over the next
session, most clearly in 2024-26: oversold ETFs that open strong keep going. Keep the shipped "buy at the open
regardless of the gap".
