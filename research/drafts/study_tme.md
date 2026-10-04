# Study TME: Treasury month-end duration extension, one look on 2002-15 (VALIDATED by the registered rule)

Pre-registered `round1_prose.md` "Study TME" (commit 003e176, 2026-10-04 15:22 PDT; N 813 -> 814) before any 2002-15
price was loaded. Runner `research/sim/tme_treasury.py` (`fetch`, `validate`, `run`); output
`data/research/program/tme_out.txt`; run sentinel `data/research/tme/run_done.json` (15:24, git 003e176).

**Rule TME1.** Buy TLT at the close of session T-3, sell at the close of T (T = last session of the month), 161 months
2002-08..2015-12. AR = window return - 3 x the month's other-session mean daily return; 2bp/side.

| statistic | value |
|---|---|
| gross window return | +40.2bp/month (median +51, t 3.67) |
| excess over cash | +38.7bp (t 3.54) |
| **AR net** | **+32.3bp/month, median +35.9, t 2.76 (NW3 2.82), hit 61%** |
| ex-best-5 months | +20.8bp (t 1.91) |
| 2x cost | +28.3bp (t 2.42) |
| 2002-08..2008-12 / 2009-15 | +23.5 (t 1.58) / +40.4 (t 2.26) |
| years positive | 13 of 14 (2004 -13bp) |
| ex Sep-Dec 2008 | +35.0bp (t 3.05) |
| best 5 months share of total | 38% |

All six gates pass; mean >= +25bp -> **VALIDATED** (registered label).

**Identification (registered diagnostics).**
- Duration monotonic: AR TLT +36.3 > IEF +18.0 > SHY +5.4bp, about proportional to duration (~2-3bp per duration-year
  each): a common month-end fall in yields, the duration-demand signature.
- Timing: the abnormal return is on T-1 (+16.5bp, t 2.5) and T (+23.9bp, t 3.4); T-3/T-2 ~0; partial reversal on
  T+1/T+2 (-6, -13bp). Consistent with temporary price pressure at the index reset. (The registered window also holds
  T-2, which adds noise but was not changed.)
- Against the mechanism: refunding months (larger extension) are NOT stronger (+27 vs +35bp, both positive).
- Independent window: the 2016-26 market-map probe (different benchmark: mid-month) was the same sign, +42.6bp, t 3.5.
  Literature: Hartley-Schwarz report the same end-of-month Treasury return pattern.

**Economics (excess over cash, net).** +34.7bp per 3-session window, 12 windows/yr = +4.2%/yr on deployed capital,
using capital only ~14% of sessions. Account: $2.3k +$58 (taxable 60% idle) / +$96 (Roth 100%) per year; $10k +$250 /
+$417; $25k +$625 / +$1,042; $100k +$2.5k / +$4.2k. Capacity: TLT/IEF trade $1B+/day; the account never binds, and
the mechanism (benchmark rebalancing of the whole Treasury market) is far larger. Turnover 12 round trips/yr.

**Caveats.** Effect is modest per trade; first subperiod alone is t 1.58; ex-best-5 t 1.91; 2002-03 TLT liquidity was
thin (cost assumption 2bp/side is optimistic for 2002-04). Process notes: validation was first written comparing raw
Yahoo closes with a dividend-adjusted Alpaca file (failed by the dividend drift); it was re-done as daily-return
agreement (median 0.31bp) before any outcome. The first `run` crashed on a column-name bug before printing or writing
its sentinel; the only completed look is the one above.

**What it is.** A real, small-per-trade, highly scalable, capital-light calendar flow effect with a named
constrained participant. It is not a large edge at today's balances. Scaling routes (NOT tested, each a new study):
leverage over the 3 sessions (taxable margin costs ~1.5bp per window at 12.5%/yr; Roth via 2x/3x Treasury ETFs) and
stacking with the book's idle month-end cash. Next step if pursued: log-only forward shadow with a testing.py entry.
