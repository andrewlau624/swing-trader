# Plan: seasonality (Study Lab-BJ)

Written 2026-10-01 before any computation. Pre-registration: `research/drafts/round1_prose.md`, Lab Round 34 (1 variant,
program N 723 -> 724). Monthly, long only: a small-account strategy (about 20 positions, works in a cash IRA too).

## Source
Heston & Sadka (2008, JFE), "Seasonality in the cross-section of stock returns": a stock's return in calendar month M
predicts its return in month M of later years, for up to 20 years. Keloharju, Linnainmaa & Nyberg (2016, JF) find the
same in countries, industries and anomalies. Checked: no seasonality study in RESULTS.md / NEXT.md / round1_prose.md.

## Exact rules (fixed a priori)
- Data: Alpaca SIP MONTHLY bars, adjusted for splits and dividends (returns), 2016-01 .. 2026-09. Common stock
  (Lab-AS name filter), active and inactive.
- Universe at the end of month m-1: price >= $5, and the top 500 by average monthly dollar volume over months
  m-12..m-1 (at least 10 observed).
- Signal for month m (calendar month M of year Y): the mean of the stock's returns in month M of years Y-1..Y-5
  (at least 3 observed).
- Portfolio: equal-weight the 20 highest-signal names, bought at month m-1's close and sold at month m's close
  (market-on-close both ways).
- Benchmark: the equal-weight return of the whole 500-name universe in month m. Excess = portfolio - benchmark.
- Test months: 2021-01 .. 2026-09 (the first month with 5 lags available). Halves: 2021-01 .. 2023-12 / 2024-01 .. 2026-09.

## Costs
Full turnover every month (conservative). 1x: 10bp per side; 2x: 20bp per side.

## Pass bar
Mean monthly excess net > 0 at 2x in BOTH halves; t >= 2.0 (monthly); >= 95th pct of a placebo (20 random universe
names each month, 1,000 draws); the mean without the 5 best months > 0.
Also reported: $ at $2.3k / $10k / $25k with whole shares, and the Roth (cash) version.
