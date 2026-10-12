# Wash guard: cost vs tax saved (2026-10-08, read-only, no code changed)

## Verdict
Keep the guard. Premise correction: it is NOT a same-account guard. Code has no taxable-to-taxable repurchase block.
`executor._wash_symbols` (:1674) blocks names the OTHER real-money book held, ordered, or closed in 31 days;
`_roth_night_wash` (:1691, via `signals.book_loss_sales`) makes the Roth skip names the taxable book holds or closed
AT A LOSS in 30 days. Under `wash_guard: roth_first` the Roth runs first, so the taxable's 58 vs 90 signals (19 vs 40 after
vol20, 09-29..10-07, fidelity audit) is the Roth having taken those names, not same-account blocking. Same-account wash sales
are already unguarded (and, per the tax reasoning below, cost ~0).

## Tax facts (confirm with a tax source; I did not fetch IRS text)
- IRC s1091(a): loss disallowed if substantially identical stock is acquired within 30 days before or after the sale (61-day window).
- s1091(d): same-account disallowed loss is added to the replacement's basis, holding period tacks. Pure deferral.
- Rev. Rul. 2008-5: a purchase in an IRA triggers disallowance, and there is NO basis add-back inside the IRA. Loss gone permanently.
- Direction matters: Roth purchase 30d BEFORE a taxable loss sale also disallows it. So a taxable night trade (buy close, sell next open)
  in a name the Roth bought in the prior 29 days is exposed on every losing outcome.
- Uncertain: how much a lost loss is worth. It is t x loss only if the year has net ST gains to absorb it (else only the $3k cap/carryforward).
  Using t = 24-37% ST ordinary.

## (1) Blocked signals and what they are worth
- Not directly counted by the logs (they show candidate counts, not trades). Estimate: taxable ~2.6 night fills/day (50 closed night trades in the
  live book since 09-23), Roth ~2.2/day; roughly 40-50% of taxable candidate signals are Roth-held names, i.e. ~150-300 collided taxable trades/yr
  (uncertain, +/-2x).
- Edge per night trade: NX 2003-15 +3.07bp/night at tier; 2021-26 delisted-complete +14.75bp/trade at tier (SHAR-SURV). Whole night leg is ~$270/yr at $2.3k
  (11.7%), ~$1.9-2.7k at $25k (8-10.6%) pre-tax (night_cap_out.txt truth A). ~10% at $10k (interpolated).
- Exposure is displaced to the Roth (tax-free), not destroyed; the Roth is the smaller account, so the true loss is only the exposure the Roth cannot fill.
  Upper bound if all collided exposure were lost: ~4-5%/yr of taxable equity; realistic ~1-2%/yr pre-tax (~0.7-1.4% after tax). Same at $2.3k/$10k/$25k within noise
  (the night edge %/yr falls slightly with size).

## (2) Tax cost of lifting the cross-account guard (taxable trades what the Roth holds)
Per collided night trade, a losing outcome's loss is permanently disallowed. Live night stats (small n=50, noisy): p_loss 0.46, avg loss -259bp, mean +8bp.
Extra tax = t x p_loss x |loss| = 0.32 x 0.46 x 259 = ~38bp per trade, vs after-tax edge ~15bp x 0.68 = ~10bp. Net about -28bp per collided trade.
Haircut to NX-like stats (p_loss 0.40, avg loss 200bp, t 0.30): 24bp tax vs 10bp edge, still -14bp.
At 10-20% of equity in collided names x 252 nights: roughly -3.5% to -10% of taxable equity per year. Lifting the guard is clearly net negative. Not close.
Same-account (taxable-only) wash sales: deferral within the year; every night leg is flat by the next open, so the deferred loss is realized when the replacement
sells. Only a chain still open at 12/31 defers a loss into the next year (timing, not loss). Immaterial here, and not currently guarded anyway.

## (3) Roth skipping names the taxable sold at a loss (must stay)
Disallowed taxable loss per such Roth trade ~ t x taxable loss (~250bp of the taxable lot x 0.32) vs the Roth trade's edge ~15bp. At equal sizes the guard saves ~5x what the
trade earns. Keep. The existing rule already only blocks taxable LOSS sales (gain sales do not trigger), so it is already the minimal form.

## Recommended rule
No change to the economics: keep roth_first (Roth owns shared names, taxable avoids names the Roth traded, Roth avoids taxable loss/held names).
Only possible refinement (small, not worth a code change by itself): in `_wash_symbols`, key the taxable block on Roth ENTRY in the last ~29d / open orders
instead of EXIT in the last 31d (the s1091 window is 61 days centered on the taxable sale; exit-based adds ~1-2 days of over-blocking on names the Roth
bought 30-31 days ago). Value <= ~0.1-0.3%/yr. Allowing same-account repurchases needs no change.
Real levers if the taxable book is under-deployed: put capital where the Roth cannot (more shares/names for taxable), not unwind the guard.
