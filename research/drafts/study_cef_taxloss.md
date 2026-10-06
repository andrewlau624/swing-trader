# Study CEF-TL: closed-end fund year-end tax-loss forced selling -> January reversion (pre-registered)

**Status:** PRE-REGISTERED, one look, research only. NO DEPLOYMENT. Registered 2026-10-05.
Program N 823 -> 824. Priors cited (not re-derived): CEF discount-vs-history and CEF rights are
listed UNTESTED in `alpha_frontier_2026-10-04.md` (#1/#3/#4); dated-term CEF liquidation (DL5) and
CEF activists/insiders are DEAD and are NOT this study.

## Mechanism (named forced counterparty)

Taxable CEF holders who are sitting on year-to-date losses **must realize them before Dec 31** to
use the losses against gains. CEFs are retail-held, hard to short, and unsuited to institutional
arbitrage, so the forced December supply is absorbed by thin books: the biggest YTD losers should
underperform into year-end, then revert in January once the tax deadline passes. Counterparty =
taxable retail loss-harvesters; forced by the tax code; timing known (Dec 31). This is a different
mechanism from IBS (liquidity provision) and TME (month-end duration).

## Frozen rule (no tuning)

- Universe: the 142 CEFs in `data/research/program/ib/cef/all/*.parquet`, **distribution-adjusted**
  close (total return; verified distinct from raw price, e.g. ADX adj 4.69 vs raw 12.69 in 2016).
- Each year Y: rank funds by YTD total return through the last session of November Y
  (`adj(Nov_end_Y)/adj(Dec_end_{Y-1}) - 1`). Quintiles.
- **Dec leg** (Nov_end -> Dec_end): predicted bottom quintile underperforms the universe (forced selling).
- **Jan leg** (Dec_end -> Jan_end): predicted bottom quintile outperforms the universe (reversion).
- Tradable long-only (Roth-friendly): buy equal-weight bottom quintile at Dec_end close, sell Jan_end.
- Benchmark: equal-weight all eligible CEFs (same dates), and SPY.
- Costs: 15bp/side base, 30bp/side stress (CEF spreads are wide).
- Eligibility: fund present on all three dates; else dropped.

## Judge (one look, 2016-2026; 10-11 December events)

PRIMARY = mean January bottom-quintile excess over the equal-weight CEF universe, net of 30bp
round trip, across all eligible fund-years. PASS = excess >= +1.0% net AND positive in both
chronological halves (2016-20, 2021-26) AND ex-best-5 > 0 AND the December leg shows the forced
sign (bottom < universe). NEAR/PROMISING = positive but < +1.0% or one gate. FAIL otherwise.

Report-only: quintile monotonicity (D1..D5), Dec leg, t clustered by year, SPY-relative, the
"loser magnitude" gradient, worst fund-year, turnover, and per-$1k economics.

## Honest limits

Only ~10 calendar Decembers -> low calendar power; cluster the t by year. The CEF universe is
long-only-accessible; the December leg is not traded (no shorting). No NAV data (discount not
measured) — this tests the PRICE/total-return tax-loss pattern, not the discount-vs-history
mechanism. Runner `research/sim/cef_taxloss.py` -> `data/research/program/cef_taxloss_out.txt`.
