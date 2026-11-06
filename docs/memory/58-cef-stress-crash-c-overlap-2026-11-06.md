# CEF-STRESS (N 1070 -> 1071, 2026-11-06): KILL; CRASH-C blowout buy = CEF-RV in a crash costume

- **Overlap (Q1, descriptive):** at every CRASH-C fire (2008-09-26, 2020-03-13, 2022-06-17) 100% of the blowout decile was
  already a CEF-RV position or entry within +-8 weeks; the decile is only 5-14% of CEF-RV's entries in those weeks. Same signal
  (own-discount extreme), different timing/exit (CRASH-C enters at the fire and exits at the PRE-crash 52w median; CEF-RV usually
  entered weeks earlier and exits at the rolling median). Fund-return corr 0.43-0.91. Not a new leg.
- **Q2 judged (entries 2008-15, rebuilt panel):** stress (SPY <= -10% from 252d high OR EW median disc >= 2pt wider than its 52w
  median) vs normal CEF-RV excess vs EW CEF incl. delisted: +183 vs +56bp, DIFF +126bp, month-clustered t 1.91, median +46, halves
  +199 (t 2.1) / +10, ex-top5 +105; 2x cost on stress entries +26, **3x -74** (gate fails t and cost3). 2015 (untouched) -6bp.
  2016-26 (CEF-RV selection period, report) +114 t 2.81, but 2021-26 only +37 t 1.0. SPY-dd component alone +232 t 2.2 (report).
  Read: stress entries earn more GROSS, but the extra is about one extra round-trip of panic spread. No stress size-up of CEF-RV.
- Ceiling: stress-tilt ~1.3pp/yr on deployed CEF-RV capital; CRASH-C standalone ~0.2 fires/yr x +14% x 50% = ~1.4pp/yr. Both < +8pp.
- **Data:** CEFConnect history is gone from the Mac and blocked/HTML; rebuilt from Nasdaq Fund Network NAV (2007-04+, 205 funds from
  2007, 314 total, matches the server panel 2023-26 at median 0.00pt) by `research/sim/cef_nasdaq_hist.py` ->
  `data/research/cefconnect/nasdaq_daily.parquet`. Runner `research/sim/cef_stress.py`, out `data/research/program/cef_stress_out.txt`.
- **2026-11-05 state:** EW median disc -9.25% vs 52w -6.72% (2.5pt wider: stress flag ON by the widening leg), SPY -5.9% from high,
  155/312 funds at own 52w 10th pct. CRASH-C NOT firing (needs SPY -20% and 3pt).
- Not tested: VIX/credit/flow-defined stress; dead-fund NAV; the CRASH-C exit anchor (pre-crash median) as a CEF-RV exit variant
  (3 episodes, would be fit); intraday panic entries; category-level stress.
