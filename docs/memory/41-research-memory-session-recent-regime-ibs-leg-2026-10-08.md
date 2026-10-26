# Research memory — session "recent regime: IBS leg" (2026-10-08)

- IBS replay through 10-07 (`research/drafts/recent_ibs_2026-10-08.md`, `research/sim/recent_ibs.py`): adjusted 2021-25 +15.8bp t 1.9, 2026 YTD +67bp t 3.1 (+57 at 5bp/side), Jun-Oct +77; live fills match replay (corr 0.99, 5/5 scorable). But paired excess vs the same-day unconditional top-3 basket is +1.7 (2021-25) / +12 (YTD) / +31 (Jun-Oct), t 0.5-1.2: 2026 strength is mostly basket beta, 2024 negative. No sizing change.
- Data gotcha: raw (price-only) open-to-open is ~10bp/trade lower than the adjusted panel in 2021-25 because IBS trades span ex-dates and the holder receives the dividend; use adjustment=all for ETF replays.
