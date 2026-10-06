# Study SHAR-IBS — the live IBS leg judged on untouched 2003-15 ETF data

Pre-registration: `research/drafts/round1_prose.md:3945-3953` (Mon Oct 5 2026, written
before any 2003-15 IBS outcome was computed). 1 judged rule; program N 838 -> 839.
Runner: `research/sim/shar_ibs.py`. Output: `research/sim/shar_ibs_out.txt`.

## VERDICT: WEAK (corrected; was FAIL before a return-calculation bug fix)

At `tier`, mean net is **+4.99 bp/leg-day (t 1.03)**. The registered kill rule
(`mean <= 0` or `t < 1` -> FAIL) is cleared, but only 2 of the 5 pass-bar checks pass,
so the rule is WEAK, not PASS. Gross (zero-cost) is **+16.15 bp (t 3.34)**: a real,
median-positive reversal whose net edge sits inside the assumed `tier` round trip and
does not survive SPY beta adjustment.

### Data-bug fix (correction, not a new look)

The first run computed the trade return as a ratio of **raw** opens
(`raw_open(d+2)/raw_open(d+1)-1`, raw = stored x `closeunadj/close`). On a split ex-date at
d+2 the factor changes between d+1 and d+2, so raw_open(d+1) ~ k x raw_open(d+2) and the
return is spuriously ~-67%. This hit exactly two judged leg-days: **EEM 2005-06-07**
(raw -66.93%) and **XBI 2015-09-09** (raw -65.69%). The return is now computed on the
**split-adjusted `open`** column, `open(d+2)/open(d+1)-1`, which is split-invariant; the raw
open still feeds the `tier`/price/ADV inputs as registered. The two rows are kept and
recomputed, not dropped. This is a correction of the same frozen rule/window/costs/pass bar,
not a new specification.

## Rule (frozen, not tuned)

Live `signals.ibs_targets` + `signals.momentum_top`, run as `book.ibs_days`
(`research/sim/book.py:124-143`; `swingtrader/daily/signals.py:28-45,57-73`). On session d
(>= 260 sessions into the panel): rank the 18 live `ibs_symbols` by 12-1 momentum
(`close.shift(21)/close.shift(252)-1`) at the last month-end strictly before d+1, keep top-3;
hold each with IBS(d) < 0.2; buy open(d+1), sell open(d+2); per-name return
`open(d+2)/open(d+1)-1`, equal weight. Judge 2003-01-02..2015-12-31, one look.

## Data / calendar

Sharadar SFP `funds` bars, 1997-01-01..2016-01-31, via the local loader
(`prices(EQ18, ..., adjust="split", source="funds")`). OHLC is split-adjusted; raw OHLC =
stored x `closeunadj/close`. Signals (momentum, IBS) and the trade return use the
split-adjusted close/open (both split-invariant); raw open feeds only the cost tier / price /
ADV. ADV$ = prior-20-session mean of split-invariant `close*volume` (ETF splits are rare; this
is the dollar value either way). Sessions = the union of the 18 funds bars' dates (all 18 are
US-listed; panel 1997-12-31..2016-01-29, 4549 sessions). This is not a broker "day". Leg days
1568 total, 1146 in the judged window.

Implementation was cross-checked against the touched window: my `build_legs` on the repo's
`D.etf()` panel reproduces `research/sim/ibs_oos.py:_trades` exactly for 2016-20 — per-name
n=557, mean +29.75 bp/name (vs the published +29.8 bp), confirming the frozen rule is
implemented correctly.

## Pass bar (all at `tier`; t is day-clustered over 1146 leg days)

| # | check | value | result |
|---|---|---|---|
| 1 | mean net > 0 and t >= 2.0 | +4.99 bp, t 1.03 | FAIL |
| 2 | mean net > 0 in both halves | 2003-09 +11.84 bp (t 1.85) / 2010-15 -4.69 bp (t -0.64) | FAIL |
| 3 | median per-trade net > 0 | +10.69 bp | PASS |
| 4 | mean net > 0 ex-best-5 leg days | +1.84 bp | PASS |
| 5 | mean net > 0 beta-adjusted to SPY open->open | beta +1.010, resid -8.58 bp, t -2.89 | FAIL |

Gross (0 cost): +16.15 bp, t 3.34, median +19.94 bp, hit 55%, ex-best-5 +12.99 bp.
(2/5 checks pass; kill rule not triggered -> WEAK.)

## Cost shock (judged window, per side via `book.cost_bps`, book.py:36-64)

| model | mean | t | median | hit | ex-best-5 |
|---|---|---|---|---|---|
| `tier` (judged) | +4.99 bp | 1.03 | +9.56 bp | 52% | +1.84 bp |
| `tier_hi` | -0.18 bp | -0.04 | +3.81 bp | 51% | -3.34 bp |
| `2*tier_hi` | -16.52 bp | -3.42 | -12.71 bp | 46% | -19.66 bp |

## Reported subperiods (not judged)

- 2000-02: -13.23 bp (t -1.09), n=329; 2008-09: +8.05 bp (t 0.49), n=190.
- Effective universe (mean # of 18 with a bar): 2000 14.2, 2003 16.7, 2007-15 18.0.
- Per-year (tier): positive 2000, 2003-2008, 2010, 2011; negative 2001, 2002, 2009, 2012-2015.
  No stable sign; 2012-2015 all negative. (2005 +12.52 and 2015 -16.76 after the fix; the
  spurious -67% rows are gone.)

## Placebo (judged window, `tier`)

- IBS lagged one session (stale signal, still tradable): +14.84 bp (t 1.71, n=380) — no worse
  than the actual timing, i.e. the specific d-alignment adds nothing.
- IBS led one session (lookahead, buys the close-low day): -129.44 bp (t -18.10) — buying at
  the open of a day that closes at its low loses badly; a mechanical check, not a candidate.
- Random-name top-3 (100 draws): mean +2.51 bp, sd 2.5 bp; actual +4.99 bp sits at the 82nd
  percentile. The live momentum selection beats a random top-3, but only modestly.

## DSR (program N = 839)

Repo convention (`research/sim/ibs_voltilt.py:43`, V[SR]=1/T): SR/day 0.0305, SR0 0.0947,
**DSR = 0.015**.

## Caveats

- Daily-close signal reconstruction, not the live 15:40 decision; no auction minute data for
  2003-15, so open(d+1)/open(d+2) are daily opens.
- Short ETF history: XBI starts 2006-02, EEM 2003-04, EFA 2001-08; effective universe is
  16.7-18 names, reported per year.
- `tier` is an assumed cost model, not measured pre-2016 (live auction cost is ~0 bp on a small
  2021+ sample). The gross leg is +16.2 bp (t 3.3) but still fails both-halves and
  beta-adjustment.
- BTC/after-tax, capacity and Kelly sizing are out of scope; this is a rule verdict.
- Surplus to the two windows already touched (2016-20, 2021-26); 2003-15 is now touched too.

## Conclusion

On the first genuinely untouched pre-2016 window for this leg, IBS<0.2 as the live rule is
**weak**: net-positive at the registered `tier` cost (+4.99 bp, t 1.03) with a positive median
and a positive ex-best-5 mean, but not statistically distinguishable from zero, not positive
in the 2010-15 half, and negative after SPY beta adjustment. The gross reversal (+16.2 bp,
t 3.3) is real but small and mostly consumed by the tier round trip. Combined with Study NX
(night leg VALIDATED-SMALL on the same purchase), the program's ETF liquidity-provision leg
remains a modest, cost-bound edge bounded to roughly 2016+; the user's deployed book is
unaffected (this study changes no live rule and opens no position).
