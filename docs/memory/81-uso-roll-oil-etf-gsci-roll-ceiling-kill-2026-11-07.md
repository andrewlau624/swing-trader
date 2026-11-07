# USO-ROLL (N 1117, 2026-11-07): oil-ETF / GSCI WTI roll front-run is ceiling-killed

- Schedule history (USO 8-Ks): 4-day roll ~2 weeks before CL expiry from Feb 2009; Apr 2020 position-limit crisis -> multi-month
  holdings, roll over the first 10 trading days, discretionary (Brent/RBOB allowed). GSCI rolls bdays 5-9.
- Free data: EIA NYMEX WTI contract 1/2 daily settles 1985-2024-04 (`data/research/uso_roll/RCLC{1,2}.csv`; xls needs xlrd).
- Perfect-sign bound on the F2/F1 spread (the only thing the forced flow moves): 4.3pp/yr at 1x 1985-2008, 1.2-2.9pp 2009-24.
  Roll-window |spread move| ~= random windows of the same length: no roll footprint in CL variance (ES/NQ had 3-4.6x).
- ETF pair long USL / short USO 3.6-6.4pp bound (ladder-slope noise, taxable only); Roth can only time USO outright = oil beta,
  not the mechanism. MCL micro spreads are the only leverage path: ~1-2pp honest. All < +8pp at $10k.
- Consistent with memory 15 (FUT-ROLL: CL sign-unstable, roll edges arbitraged) and 27/69 ceiling kills. Do not revisit roll
  front-running in any commodity without a size-up mechanism. Not tested: signed outcome, Brent/BNO, RBOB/NG/ag legs, intraday
  TAS window, AP creation flows, deferred-ETF NAV premium, options. Runner `research/sim/uso_roll.py`, out `uso_roll_out.txt`.
