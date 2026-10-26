# Research memory — session "threshold forced-buy test" (2026-10-04, part 7)

### Data-buy rule (user, permanent)
Buy research data only if **expected information value > data cost**: (1) structurally compelling
mechanism, (2) free evidence does not already weaken it, (3) experiment specified enough to
falsify it, (4) payoff materially larger than existing edges, (5) no cheaper dataset answers it.
- **Sharadar $69: DEFERRED, not rejected.** Do not purchase or request the key now; NX is
deprioritized. Apply the rule retroactively.

### Study NX: BLOCKED / LOW PRIORITY (unchanged, frozen)
Registration frozen (commit `5be14c74`, N 806->809): 2003-2015 judge, one execution, no tuning,
2016-20 exploratory. Not proven false; just not worth paid data while the night hypothesis is
already weakened. Do not edit the preregistration to make it easier to pass.

### Study THR: Reg SHO threshold forced-buy window — TESTED and REJECTED (long side)
`research/sim/threshold_flow.py` (pre-reg `study_threshold_flow.md`). FTD-derived threshold
episodes (fails >= 0.5% of shares AND >= 10k shares, 5 consecutive settlement days; same
definition as the SRO list, 2016+, all exchanges); entry at the open after the 5th day (list is
public then); deadline = +13 settlement days. Panel 2021-2026, n=1516 episodes / 647 symbols.
- **CAR to deadline: -959bp (median -1242, hit 27%, day-clustered t -6.4, ex-top-5 -1217).**
  The 3 sessions into the deadline are the WORST (-274bp) — the opposite of a forced-buy lift.
  Sub-periods both negative: 2021-23 -58bp, 2024-26 -1094bp.
- **No volume footprint** (window $vol / 20d ADV at entry = 0.54x median): no forced-buying
  signature. Split: overnight +267bp, intraday -878bp (the fall is intraday).
- **Long-only net of 50bp is -1009bp. KILL.** The forced flow is real (Rule 203(b)(3) buy-in) but
  the profitable short side is inaccessible — these names are on the list *because they are
  hard to borrow* — and the long side is a strong loser. Do not re-run threshold/FTD-buy tests.
- Data note: the useful daily list URL is `nasdaqtrader.com/dynamic/symdir/regsho/nasdaqthYYYYMMDD.txt`
  (2008+); the older `/symdir/threshold/` path 404s. FTD-derived status is equivalent and cached.

### OI-pinning / signed gamma / ranking
- **OPEX OI-pinning: permanently killed** for the tested mechanism/window (part 6).
- **Signed dealer gamma: DATA-TARGET, no purchase yet** — must compete against free tests and
  pass the data-buy rule first (state exact mechanism, direction, inputs, design, why larger
  than the killed OI-pinning effect).
- **Frontier ranking (user):** 1) threshold-list forced buy -> now TESTED-REJECTED; next free
  candidates are Treasury-auction concession and SPDR ETF discount reversion (SSGA, $0);
  2) NX BLOCKED; 3) signed gamma DATA-TARGET; 4) ETF creation/redemption DATA-LIMITED;
  5) fallen angels DATA-LIMITED; 6) borrow/HTB BLOCKED; 7) futures roll / benchmark changes /
  auction mechanics NOT SEARCHED; 8) night variants / generic options / intraday noise CLOSED.
- "Data-limited" is NOT negative evidence. No deployment.
