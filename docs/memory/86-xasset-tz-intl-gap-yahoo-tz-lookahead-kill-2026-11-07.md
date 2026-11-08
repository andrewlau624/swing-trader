# XASSET-TZ (N 1150, 2026-11-07): non-US / non-equity daily branch — INTL-GAP KILL, rest ceiling-killed

- Branches: B1 INTL-GAP (fade Asian ETF open-cross gap minus home index close-to-close; open -> close cross) RUN;
  B2 Treasury auction concession pre-2016 (3.6pp TLT; TAC measured ~1pp), B4 GSCI/BCOM roll ex-USO (spread effect; ETF only
  gets direction; 1.8-2.9pp), B5 daily London FX fix (2.5pp), B6 crypto weekend/funding (in the gap / access): CEILING-KILL.
  B3 month/quarter-end = TME/HMM-REBAL, not redone.
- B1 corrected judge 2000-15: +2.5bp/day net t 1.83; 2000-07 +11.7, 2008-15 -6.7, 2016-26 -7.6; SPY-hedged +0.3; ceiling 3.1pp. KILL.
- **Pitfall (data bug, cost one false PASS at t 9.9):** `vt_flow.yahoo_ohlc` and `tme_treasury.fetch_px` date bars in New York.
  Yahoo stamps Asian (and FX `=X`) bars at the local session open = the previous evening ET, so they land ONE DATE EARLY ->
  a "same-day" foreign close is actually the next one (lookahead). Use `intl_gap.home_index()` (exchange-local dates) for any
  foreign index. Tell-tale: a hedged arm that predicts SPY's intraday move.
- Not tested: USD-converted home return, futures fair-value gap, European ETFs, first-minute fills, futures spreads for B4.
  Files: research/sim/intl_gap.py, data/research/program/intl_gap_out.txt, data/research/intl_gap/.
