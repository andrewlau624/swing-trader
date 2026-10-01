# Study AR — remaining brief items: 0DTE options at small size (#6) and asset location (#7) (Round 17d)

Report only; no code run (no options data in the repo). Closes the brief's #6 and #7.

## #6 — a 0DTE options version of the conviction trade

**Sizing (the binding constraint).** The conviction trade is 0.5 of equity in TQQQ, i.e. ~1.5x of
equity in QQQ notional (TQQQ is 3x). At $2.3k that is ~$3,450 of QQQ exposure. One QQQ share is
~$600 (2026), so one 0DTE contract controls **$60,000 of notional**. One contract is ~17x the
trade's intended exposure; the minimum position is far above the strategy's size. A ~1% adverse QQQ
move costs ~$600 on one contract — over a quarter of the whole account — and a 4% move exceeds it.
**At $2.3k, QQQ 0DTE is not sizable.** On the premium alone an ATM 0DTE contract is ~$250-400
(0.4 x S x daily-sigma), which fits inside 0.5 x equity, but the *notional* is what matters and it
is 17-26x too big. The trade becomes sizeable at roughly 0.5 x equity >= one contract's notional:
**equity >= ~$30-40k** for a 0.5-weight QQQ 0DTE (or ~$60k to match the 1.5x-QQQ exposure).

**Data.** ThetaData Standard is $80/mo = $960/yr. On a $2.3k account that is **~42% of equity per
year** before any edge; even at $25k it is ~4%/yr of the account. Not economic at $2-25k.

**Verdict: not worth pursuing at $2-25k.** It is a $50k+ idea (and the repo has no options-price
history to test it without buying the data). Parked.

## #7 — asset location at small size

Every leg holds <= 1 session (IBS open->open, night close->open, noise intraday), so all realisations
are **short-term**: no leg is more tax-efficient by holding period. The tax drag is proportional to
each leg's gross, so the only lever is *which account* holds a leg (taxable pays 35% ST, the Roth
pays 0) and the cross-account **wash-sale guard**, which is structural (add. 31/39). Conclusions:
- The Roth should hold the legs with the best %/yr, and it does: Study AQ's cash-IRA book runs the
  shipped **IBS + night** legs, tax-free, at 19-22%/yr (vs ~12-14% after tax in the taxable book at
  the same costs). The $7.5k/yr deposits compound there untaxed.
- The G4s guard (Roth first, different-index look-alikes) is the household optimum; add. 39 finds it
  worth +$363/yr at the user's size and it avoids the 8.8-9.9% permanent disallowance of a Roth QQQ
  F3 leg. Roth F3 stays off (wash). No new rule.
- Splitting legs by *account* to avoid the guard entirely (Roth night / taxable IBS) was considered
  and is not better: it throws away each account's diversification and the taxable book still holds
  QQQ/SMH via the noise leg, which collides with the Roth's IBS. G4s does the job.

**Verdict: no change; structural. The action is the AQ spec (run IBS + night in the cash-IRA Roth)
under the shipped G4s guard.**
