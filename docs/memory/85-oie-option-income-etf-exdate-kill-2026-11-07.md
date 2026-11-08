# OIE (N 1140-1142, 2026-11-07): option-income ETF ex-date flow — KILL; Roth forced-flow branches (b)-(e) already in ledgers

- Task: forced-flow trades for the long-only Roth that are not PREF-EX variants. Branch grep: (b) pref called-for-redemption =
  idea_scan_events row 11 COVERED / PREF-INDEX deletion side; (c) ETF closures DL6 dead, ETN acceleration ceiling-kill; (d) PFF/PGX
  recon PREF-INDEX CEILING-KILL + DATA-LIMITED; (e) single-stock LETF rebalance LETF-REV N 1065 KILL (+ NIGHT-LETF-TILT shadow).
  Only (a) was new.
- (a) 41 option-income ETFs (YieldMax, XDTE/QDTE/RDTE, SPYI/QQQI, QYLD/XYLD/RYLD, JEPI/JEPQ), Yahoo daily, 2023-26 n 3,122:
  close T-1 -> open T +div excess -0.6bp t -0.09; post-ex T -> T+3 -7.8bp; pre-ex T-4 -> T-1 +2.3bp. All FAIL. Ceiling < 1pp/yr.
- Why: distributions are mostly return of capital (no tax seller) and AP arbitrage keeps price ~ NAV, which drops by the payout.
- Not tested: post-hoc yield >= 2% subset (+14-26bp, unregistered), official auction prints, iNAV premium, pay-date DRIP flow,
  hedged form. Do not re-cut 2023-26 by yield/issuer. Files: research/sim/oie.py, data/research/program/oie_out.txt.
