# BDC-RV + CEF-sibling branches (2026-11-07): BDC-RV KILL, three ceiling-kills

- Branch list (siblings of CEF-RV, Roth long-only): DMP trigger tenders (user ruling: tenders dead; anticipation ~1.5pp), rights
  (CEF-RIGHTS KILL), merger/open-ending drift (cef_ends; ~2pp ceiling), activist 13D (G45, forward G45-F), tax-loss (CEF-TL/TL2 dead),
  distribution cuts (R16 continuation; R17 avoid-screen = `cef_rv_shadow.cut42`), CEF index-ETF reconstitution (~3pp ceiling),
  BDC-RV (the only unrun branch).
- **BDC-RV (N 1130-1131) KILL.** Frozen CEF-RV bands on 64 BDCs (XBRL frames NAVPS x InvestmentOwnedAtCost -> Sharadar CIK, +16
  hand-added delisted), PIT NAV = SF1 ARQ bvps by filing date (split units fixed at reportperiod). 880 trades 2004-26: excess vs EW BDC
  +84bp t 1.92, median +209, 3x cost -16, ex-top-5 funds ~0; price-only control +35. Mechanism faintly there (NAV anchor +70bp), ~1/3
  CEF size; quarterly manager-marked NAV carries credit info. ~1.4pp/yr.
- Data: `data/research/bdc_rv/` (frames, universe_raw.csv, trades.csv); frames API starts 2012Q4. Runner `research/sim/bdc_rv.py`.
- Not tested: NAV nowcasts, BDC peer excess, open fills, other bands; no backtests of the ceiling-killed branches.
