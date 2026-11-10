# IDX-LETF-REV (N 1208-1209, 2026-11-10): index/sector LETF close rebalance -> underlying ETF next-open reversal, KILL

Branch list (conditional-edge hunt; round1_prose "BRANCH LIST + PRE-REGISTRATION - IDX-LETF-REV"): six branches, five dedupe- or
ceiling-killed before any test: OPEX pin (1.8-4pp), month-end 60/40 rebalancing (HMM-REBAL dead), dividend-month premium (2.4pp)
and aggregate dividend pay-day reinvestment (1.3pp) (both new leaves, not run), IPO lockup-expiry short (re-ceilinged 3.75pp),
stock-and-bond down day deleveraging (VT-FLOW class, 3pp). Survivor: LETF-REV's `not tested: index LETFs` leaf.
- Rule: I = sum over the underlying's 2x/3x/-1..-3x LETFs of AUM(t-1) x L(L-1) x r_t / underlying $ADV20; PIT top-decile |I|
  over prior 252 sessions; long close->open after I<0 (A), short after I>0 (B); 15 underlyings; CRSP dsf (WRDS); judge 2009-19.
- A long: net -9.3bp/event-day t -2.30 (gross -3.3), halves -14.4/-4.5, 2020-24 -13.5, 3x cost -21.3, dose high-minus-low
  -3.0bp, DSR 0. B short: net -1.9 (gross +4.1 t 1.1), halves +2.3/-5.8, dose -4.4. No underlying shows a dose pattern
  (SOXX has the largest LETF/ADV ratio and earns only +2.5bp net on the long arm).
- Not tested: constituent-level demand on single stocks, 15:45 -> close on indices, holds past the open, leverage changes
  (NUGT/JNUG 2020) modelled, bond/commodity LETFs, other thresholds.
Files: research/sim/idx_letf_rev.py, data/research/program/idx_letf_rev_out.txt, cache data/research/idx_letf/.
