# EDGAR-SESS (N 1096-1097, 2026-11-06): in-session EDGAR filings, KILL

Idea: dodge "the effect is in the after-close gap" by trading filings ACCEPTED 09:35-15:30 ET from acceptance + 1-5 min to the close /
next open cross. Types: 8-K 1.01/2.01/5.02/1.03/3.01, SC TO-I/T, 424B4/5, 25-NSE. 4,550 events 2019-26 ($5+, ADV $5M+, ~580/yr).

- The EDGAR acceptance minute carries no price impulse: median |m-1 -> m+5| 8-14bp; only 5% of events move >= 50bp by m+2; 0-4% of the
  day's move is done by m+2. The news hits earlier via wire/pre-market PR (event-day gap 53-59bp; m-30 -> m-1 drift 40-60bp vs 26bp).
  EDGAR acceptance is paperwork for $5M+-ADV names, not the event.
- Choose 2019-22: 0/36 cells (type x continuation/reversal/fixed sign x close/next open) passed n >= 30 & t >= 2. Fixed shorts on 424B
  offerings / 25-NSE ~0bp net on ~380 events each. Judge half never read.
- Not tested: micro-caps (< $5M ADV, < $5) where the filing may be the first release; items 7.01/8.01/2.02/4.02; newswire timestamps;
  intraday exits; LLM/keyword classifier (conditional on a plain-rule pass, not run).
- Reusable: `data/research/edgar_sess/submissions/` = form/items/acceptanceDateTime 2019-26 for 6,959 CIKs; runner
  `research/sim/edgar_sess.py` (raw-price join: SEP open/close are split-adjusted, use closeunadj against raw minute bars).
