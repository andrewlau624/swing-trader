# Research memory — session "physical delivery / FND" (2026-10-04, part 11)

Study FND (`research/sim/fnd_physical.py`, pre-reg `study_fnd_physical.md`). Object = the nearby/deferred
calendar spread and OI/volume migration around first notice day, for physically-settled CL/NG vs the
financially-settled ES roll (part 10). Data: cached Databento GLBX individual contracts 2011-2025.

- **Physical constraint is real and observable.** CL nearby volume share collapses 0.90 -> 0.55 into FND
  then recovers to 0.91 (delivery migration). NG shows almost none (0.92-0.98; diffuse delivery).
- **But no harvestable spread distortion.** Spread (nearby - deferred) means around FND are outlier-carried:
  CL FND->+5d +206bp (t 1.5, **median +3.9**, ex-top-5 -24); NG FND->+10d -86bp (ex-top-5 -313); signs
  flip between CL and NG; every median is single-digit bp. The apparent moves are carry/convenience yield,
  seasonality (NG winter), and a few well-known squeezes (2020 negative WTI, 2021-22 gas).
- The CL migration signature is the **same shape** as the ES financial roll (part 10) that has been
  arbitraged since ~2021: visible migration is necessary but NOT sufficient for a tradable distortion.
- **Verdict: KILL (physical-settlement branch closed).** Outcome is ARTIFACT / carry-and-seasonality, not
  a physical edge; the user closed the branch 2026-10-04. **No FND variants, no more physical-settlement
  variants.** Answer to the key question: physical delivery, as expressed in the front calendar spread, is
  NOT a new harvestable inefficiency. The straddling speculator bears the same delivery risk as the
  constrained physical party, so there is no free side.
- **Next genuinely different futures mechanisms (not load-bearing roll):** futures-based
  volatility-target / CTA scheduled repositioning; settlement-auction (SOQ); cross-asset basis
  (futures vs ETF/physical). Pick one; do not re-tune roll/FND windows.
