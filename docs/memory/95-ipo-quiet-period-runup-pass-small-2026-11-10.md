# IPO quiet-period clock (N 1200-1202, 2026-11-10): initiation day dead; pre-expiry run-up CONFIRMED OOS but PASS-SMALL

Lens sweep (15 candidates, one per alpha-foundry lens; table in round1_prose.md "LENS SWEEP 2026-11-10"): 13 dedupe- or
ceiling-killed, only the regulator-lens IPO quiet period survived (re-ceilinged: the old 1.5pp kill in deep_loop_ledger #14 assumed
10% share; a 2-session hold deploys ~50-100%).
- Rule clock: K = 40 days 2002-08..2012-04 (NASD 2711), 25 days otherwise (post-JOBS convention; 1988-2002). x = first session >= F+K.
- QP-INIT (N 1200) KILL: hold close(<= F+K-2d) -> close(x), 2002-26 n 2,133: -3.5bp net excess vs IPO cohort, t -0.27; the initiation
  day itself is ~0. BJR's 1998-2002 effect (+72bp mean, median -46) is gone.
- QP-RUNUP (N 1201, window from QP-INIT's profile): buy close x-3, sell close x-1. 1998-2002 +381bp t 7.7; 2002-26 +52.7bp
  (median +34, t 4.47, both K regimes > 0, alpha vs SPY t 3.7); regime-swap placebo +16.6 t 1.3. KILL as registered on DSR 0.887.
- QP-RUNUP-CRSP (N 1202), unseen CRSP 1989-95, 731 IPOs: +69bp net excess, median +19, t 3.69, halves +59/+74, alpha t 4.66: PASS.
  K=40 placebo +1bp. The run-up tracks the regulatory date in every era: real mechanism (anticipation of near-all-Buy initiations).
- Trade: book replay 2002-26 at 50% share +7.5%/yr, maxDD -46%, Sharpe 0.55; 2x cost +4.0%, 3x +0.6%. Megadeals ($ADV > $100M) and
  < $10 / > $40 names negative (seen, not a rule). Below the +8pp gate; not deployed. Same %/yr at $2.3k/$10k/$25k (thin-ish $10-40
  names, $2M+ ADV); capacity breaks well above $100k.
- Not tested: analyst initiation counts/ratings (IBES recs), price/ADV-band rule (post-hoc, needs new N + forward), day-30
  stabilization end (needs 424B4 offer prices; short-only, ceiling 2.7pp), secondary-offering 3-day quiet periods, 2012-15 non-EGC
  40-day deals (misclassified as K=25), combination with the night/IBS book (correlation not measured), forward data.
Files: research/sim/qp_init.py (--runup), qp_runup_crsp.py (WRDS pull cached data/research/qp_crsp/), qp_runup_book.py;
outs data/research/program/qp_{init,runup,runup_crsp,runup_book}_out.txt. wrds pkg was missing in stvenv; installed via uv.
