# EDGAR-MICRO (N 1100-1102, 2026-11-06): in-session EDGAR filings by listed micro-caps, KILL

Sibling leaf of EDGAR-SESS (71): does the filing minute move price where there is no newswire? Listed NASDAQ/NYSE/NYSEMKT names with
prior close < $5 or ADV < $5M (>= $0.50, ADV >= $100k), delisted included, accepted 09:35-15:30 ET; ~1,970 events/yr.

- Ceiling not binding by count (~8 events/day, capacity ~5% of rest-of-day $vol ~$40k median); the gate is per-event net edge.
- Acceptance is still not a price event: |m-1 -> m+2| median 26bp vs 22bp at random minutes in the same name-day; share >= 100bp
  16% vs 8%; 0-4% of big-day moves done by m+2; no pre-acceptance leak (60 vs 54bp). Nasdaq 5250(b)(1) press-release rule is the
  likely reason: listed micro-caps wire too.
- Choose 2019-22: 0/54 cells (item x CONT/REV/FIX x close/next open) selected. Pooled gross ~0, net ~-240bp on >= 100bp movers.
  Best T301 delisting-notice short NXO +147 net t 0.88 n 30 median -11. Judge never read.
- NBBO check: micro-cap half-spread median 37bp (70bp at ADV < $500k); ~half of events have no trade near m+2.
- Not tested: OTC / sub-$0.50 / ADV < $100k (no SIP bars), passive entries, intraday exits, 3.02/5.07/2.03 items, 2.02 by surprise,
  text classifier, newswire timestamps.
- Reuse: `research/sim/edgar_micro.py` (events/bars/run/quotes); `edgar_sess.bars(ev_path)` now maps digit-suffixed delisted tickers.
