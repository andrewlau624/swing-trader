# BORROW-UNIT (N 1122-1123, 2026-11-07): `optionm.borrate.borrowrate` is DECIMAL/yr — verified data bug, corrected re-runs, nothing revived

- **Unit (WRDS direct, 2026-11-07):** 30d-tenor June cross-section medians 0.016 (2005) / 0.022 (2015) / 0.024 (2021) / 0.026 (2024),
  p99 0.23-1.52, rows >= 10: 0. GME 2021-01-22 0.94 (28d); AMC 2022-08-17 1.37; BYND 2022-08 0.92; MSFT 0.0005-0.005; SPY 0.0002-0.003.
  => 0.05 = 5%/yr. Sentinel -99.99. Treat any `/100` or `>= 10` on this field as a bug. (Rate is put-call-parity implied: dividend /
  early-exercise contaminated, not a broker locate fee.)
- **Bugs fixed in place:** `research/sim/borrow_xs.py` + `borrow_xs2.py` charged D10 borrow as mean/100/12 (100x too small);
  `research/sim/pcp_htb.py` prefilter `>= 10` (= 1000%/yr; now `>= 0.10`); `wrds_borrate_profile.py` text said percent.
  `rec_recall.py` and `rh_fade.py` were already right (x100 for display).
- **BORROW-XS-U (N 1122):** unit-invariant lines reproduce exactly (gross LS +106.5bp/mo t 6.43; long-only D1-EW +22.3). Corrected LS net
  FULL **-160bp/mo t -9.4** (sub-periods -68 / -120 / -320); was reported +84 t 5.1 (memory 46 and the N 1006 result: WITHDRAWN). D10 fee
  mean 29.8%/yr, median 21.6, monthly floor 13.6 — even the floor (113bp/mo) exceeds the gross spread. Every XS2 size/vol tercile LS net
  negative. The high-fee underperformance is roughly fee-priced. Verdict unchanged (NOT DEPLOYABLE), now stronger.
- **PCP-HTB-U (N 1123):** true 10%/yr prefilter = 589,474 name-dates (not 359; borrow data is NOT empty pre-2016). 13 confirmed
  entries, all one artifact name 2010-12 (OTM call bid above value), 0 in 2016-24 -> KILL, gate 1/6. Conversion excess vs fee spearman
  -0.15: parity sign confirmed (conversion earns r - b), weak in EOD HTB mids.
- Not tested: real broker locate fees; fee-capped (<10%) D10 short leg; securities-lending income on a long book; synthetic long + lending.
- Files: round1_prose "Study BORROW-UNIT"; data/research/program/borrow_xs_out.txt, borrow_xs2_out.txt, pcp_htb_out.txt (overwritten).
