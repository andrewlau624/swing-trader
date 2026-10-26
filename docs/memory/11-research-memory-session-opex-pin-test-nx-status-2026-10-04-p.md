# Research memory — session "OPEX pin test + NX status" (2026-10-04, part 6)

- **NX: still DATA-LIMITED, not run.** Registration frozen (commit `5be14c74`, N 806->809); the $69 Sharadar
  purchase is user-approved but no `SHARADAR_API_KEY` is in `.env` and no vendor data is on disk. Do not fabricate;
  run the day-1 checks and NX once when the key exists. 2016-20 stays exploratory.
- **Options-induced underlying flow — cheapest variant TESTED and FALSIFIED.** `research/sim/opex_pin.py`
  (pre-reg `study_A_opex_pin.md`): SPY monthly OPEX 2023-24, max-OI strike within +/-3% of prior close, open->close.
  K1 (max-OI) hit 43%, net -8.4bp (t -0.51); K2 (2nd-OI placebo) hit 55%, +19.5bp. **OI-concentration/pin is
  rejected**; do not re-run OI pinning. **Signed dealer gamma (OI x gamma) is still untested (DATA-TARGET).**
- **Frontier statuses:** ETF create/redeem DATA-LIMITED (no free bulk shares/NAV); fallen angels DATA-LIMITED (FRED
  aggregate only, no free PIT ratings); borrow/HTB BLOCKED; threshold-list forced buy still PROMISING (free daily
  lists) and is the top free test; signed gamma is the top paid test. OPRA `statistics` observed ~$0.36-0.37/day
  (the reset doc's "~$4 left" is stale).
- **Strongest negative result this cycle:** the OPEX OI-pinning falsification. **No new mechanism discovered; the
  frontier did not materially change** beyond closing the OI-pinning branch.
