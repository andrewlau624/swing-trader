# Research memory — session "capacity/scale frontier" (2026-10-04, part 8)

Objective shifted to **total profit-generation capacity / scaling toward 2x**, not a new standalone signal.
Two strongest free tests run first.

### Study TAC: Treasury-auction concession — REJECTED
`research/sim/tac_treasury.py` (pre-reg `study_tac_treasury.md`; FiscalData auctions 1979+, 2633 note/bond
aucions). TLT/IEF vs SPY, 2016-2026, 979 auctions (TLT 297 / IEF 682).
- Concession (A-3 -> A): -29bp (t -4.3). Reversal (A -> A+3): -16bp (t -2.6). **Executable A+1 -> A+3: +2.4bp (t 0.9).**
- The mid-window "reversal" is the auction-day move **bleeding back** (partly a stale-close day-turn artifact); it
  is gone by the next session. Both halves negative; TLT worse than IEF; not larger for high bid-to-cover.
- **Verdict: no executable post-auction reversal. The published concession effect is a pre-auction move, not a
  tradable simplification. KILL** (economically small even before costs; 2bp/gap in the right direction but t<1).
- Note: ETF bars are 2016+; the pre-2008 positive-reversal regime (Lou-Yan-Zhang) cannot be tested free here.

### Study ETC: SPY creation/redemption flow — REJECTED (no tradable flow signal)
`research/sim/etc_etf_flow.py` (pre-reg `study_etc_etf_flow.md`; SSGA navhist xlsx: daily NAV/shares out).
- **Data bug found and fixed:** `etf_daily` SPY closes are split/DIV-adjusted, so `close/NAV-1` shows a fake -15%
  "discount". The true SPY discount (raw closes vs NAV) is +/-2.7%, median +0.4bp. **Any ETF-premium study must use
  raw closes**, not the adjusted panel.
- Flow (shares-out change) -> next-day return: top creation quintile +9.3bp (t 1.5); big creation +16.8bp (t 1.7);
  big redemption +0.1bp. **Weak (t<2), not stable across years (-17bp in 2022), and ~= SPY's drift + the 1-2bp
  round trip.** Discount quintiles: premium +12.7bp, deep-discount -0.4bp (t<1).
- **Verdict: no tradable, scalable flow or discount-reversion signal in SPY. KILL** (the AP arbitrage leaves nothing
  in the most liquid ETF; a smaller/international fund would need its own NAV history, i.e. a scrape).

### Ranking after this cycle
1. **Options-induced underlying flow (signed dealer gamma) — DATA-TARGET**, no purchase (must beat the killed
   OI-pinning; see data-buy rule). Only remaining structurally-motivated, if small.
2. **Threshold-list forced buy — TESTED-REJECTED.** OI-pinning — killed. Generic options — closed. Night — do not size.
3. **DATA-LIMITED:** ETF creation/redemption (needs a per-fund raw-NAV + shares scrape, not just SPY), fallen angels,
   borrow/HTB, margin cascades.
4. **NOT SEARCHED:** futures (roll/basis/calendar), benchmark/index rebalances (no membership/PIT), auction mechanics
   beyond TAC, cross-venue/structural.
5. **Capacity audit of the live book** (execution/capital bottlenecks) — not yet done; the other lever to 2x.
- Honest read: neither free test produced a scalable edge; the local book is not the bottleneck this cycle revealed.
  Bigger capacity likely needs a new market (futures) or a per-fund NAV scrape. No deployment.
