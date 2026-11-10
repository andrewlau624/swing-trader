# Sharadar row-order audit (2026-11-10): files are shuffled, but no recorded verdict moved

## What the files look like on disk
The bulk CSVs are written to parquet in whatever order the zip delivers them (`sharadar-data/sharadar/download.py`).
Adjacent-row date inversions within a ticker, measured 2026-11-10:
- funds (SFP), stocks (SEP), daily, fundamentals (SF1): shuffled. SPY 7,187/7,234 and AAPL (stocks) 7,072/7,234.
  The note "stocks.parquet is sorted" was wrong; it came from a filtered read.
- actions, events, sp500: newest first, both globally and per ticker.
- metrics, insiders, holdings: close to sorted. tickers has no date.
- No (ticker, date) duplicates in funds or stocks. fundamentals has duplicate (ticker, calendardate) and
  (ticker, reportperiod) rows: amended filings with different values. There are no duplicates on the full
  (ticker, dimension, calendardate, date) key.

## Audit
All 171 files under research/, swingtrader/, scripts/ and tests/ that mention a Sharadar table were traced through
the code path that actually runs:
- 125 SAFE: sorted, pivoted or `sharadar.load.prices()` (which sorts) before any order-dependent op.
- 44 NOT-ORDER-DEPENDENT; about 25 of these are false grep hits on `etf_daily.parquet`. Note that `ibs_oos.py` and
  `ibs_xasset_scan.py` read Alpaca etf_daily, not Sharadar.
- 1 BROKEN, 1 FRAGILE. **Neither involves funds.**

None of the funds readers was broken: shar_ibs, robust_ibs, the cef_* family, upro_gate, nx, the pref studies, etc.
The shared helpers sort where they are defined: `cef_rv.load_sfp`, `cef_rv_surv.load_sfp`, `lh_panel._build`,
`winsig.load_panel`, `shar_surv.load_bars`, `nx.load_bars`, `sel_night`, `fxd.load` and `BH.sharadar_px`.

The two exceptions are both fundamentals readers whose dedup depended on file order:
- `spx_elig.py:74` BROKEN. It did a non-stable sort on calendardate, then `drop_duplicates(keep="first")`, so which
  filing survived was random. Fixed by sorting on (calendardate, date) with mergesort, so the first filing is kept.
  Re-run with the same parameters:

  | | old | new |
  |---|---|---|
  | primary trades | 472 | 471 |
  | net mean | +0.61% | +0.75% |
  | t | 0.50 | 0.62 |
  | median | -0.91% | -0.90% |
  | ex-top-5 | -0.61% | -0.47% |
  | halves | +1.14 / -0.05% | +1.40 / -0.05% |
  | placebo | +1.81% t 2.44 | +1.80% t 2.42 |
  | $10k | ~0.6%/yr | ~0.8%/yr |

  **Verdict unchanged: FAIL / REJECTED.**
- `rev_tone.py:37` FRAGILE. Same pattern, keyed on reportperiod. Fixed to keep the earliest filing. On the study's
  20 tickers the kept revenue is identical in 1,068/1,068 quarters. The input `scored.parquet` is not on disk, so
  this was not re-run. REV-TONE KILL is unchanged.

## What was fixed
- funds.parquet was re-sorted in place by (ticker, date). The unsorted original is backed up at
  `~/data/sharadar/_unsorted_backup_2026-11-10/funds.parquet`; keep it until the user says otherwise. The checksum
  matches before and after: 15,704,811 rows, plus the sum and the sum of squares of the uint64 row hashes. Inversions
  after the sort: 0.
- stocks, daily and fundamentals were NOT re-sorted: the permission classifier denied it. They need the user's OK.
  Until then every reader must sort them itself.
- The loader (`sharadar-data` 5df328f) now sorts stocks, funds, daily and fundamentals on write.
- Canary: `tests/test_sharadar_sorted.py`. It asserts funds/SPY is sorted. stocks/AAPL is marked strict-xfail, so
  the test fails once stocks is sorted and the marker must be removed.

## Rules
- Sort after every Sharadar read, including fundamentals, before any shift/rolling/first/last/keep= op.
- When dropping duplicates on fundamentals, add `date` to the sort with `kind="mergesort"`.
- actions/events/sp500 are newest first: never use iloc[0] to mean "earliest".

Not tested: the order dependence of the same-date duplicate picks in `spin_t0.py:29`, `spin_child.py:69` and
`pcal.py:139` (spin-off and dividend rows sharing a (ticker, date)). These are not date-order bugs and were left
as they are.
