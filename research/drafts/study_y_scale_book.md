# Study Y — the whole book at size: ~16-18%/yr pre-tax to $1M; taxable loses to a held index from ~$250k (report, N 614)

Stamp: `round1_prose.md` Round 12 (commit 29ef565). Script: `research/sim/scale_book.py` (7 s).
Output: `data/research/program/scale_book_out.txt`. Constant equity per size, 2021-02..2026-09,
raw pool, V7 live-today legs, Study V/X impact on the night leg (Y_rule 4 cap), square-root
impact on the ETF legs from scale_legs_diag.txt. Rates are simple %/yr at constant equity.

## Book rate by size (CENTRAL: night A/Y 1, ETF Y 1)
| equity | B2 taxable, pre-tax | after tax MOD / TOP | B3 Roth | legs: night / IBS / noise |
|---|---|---|---|---|
| $25k | 22.6% | 15.9 / 11.5 | 22.6% | 2.3 / 7.8 / 11.3 |
| $100k | 20.5% | 14.5 / 10.5 | 20.5% | 1.3 / 7.6 / 10.6 |
| $250k | 19.2% | 13.5 / 9.8 | 19.2% | 1.1 / 7.3 / 9.8 |
| $500k | 17.8% | 12.5 / 9.1 | 17.8% | 1.0 / 7.0 / 8.8 |
| $1M | 15.9% | 11.2 / 8.1 | 15.9% | 0.9 / 6.5 / 7.4 |
| $2.5M | 12.2% | 8.6 / 6.2 | 12.2% | 0.8 / 5.6 / 4.7 |
| $5M | 8.1% | 5.7 / 4.1 | 8.1% | 0.7 / 4.6 / 1.7 |
OPT and PESS move these by about ±1-3pp up to $1M; the night-cost stress (tier) changes <0.5pp
past $100k. B1 (SMH kept) falls behind B2 from $1M (SMH impact) and is ~3% at $5M.
SPY held over the same window: 15.0%/yr (2021-23 10.0, 2024-26 20.7); after-tax equivalent over
20 years with tax at sale: 13.5% (MOD), 12.5% (TOP).

## Registered readings
1. **Planning rate above $250k** (replaces the 10% placeholder): taxable B2 12.5% after tax at
   $500k, 11.2% at $1M (pre-tax 17.8 / 15.9); Roth B3 17.8% / 15.9%.
2. **Taxable crossover E\* = $250k** (CENTRAL and PESS; $1M under OPT): from there the taxable book
   after yearly short-term tax earns about what a held index does after deferred tax, and less
   beyond. TOP bracket: below the index at every size on the grid past $2.3k.
3. **Roth crossover $2.5M** (CENTRAL, PESS; none on the grid under OPT): no tax drag, so the Roth
   beats the held index until the ETF legs saturate.
Both halves (pre-tax): the book is above SPY in 2021-23 at every size to $5M and below it in 2024-26 from
$100k (SPY +20.7%); no reading depends on 2024-26 alone. Upper bounds: all of this replays the
fitting period.

## What drives it
- **The night leg is worth ~1%/yr from $25k** under the Y_rule 4 cap (binds on 70% of orders at
  $25k, 95% at $250k). The book at size is IBS + noise.
- Observation (not registered): Study V's uncapped A/Y 1 leg earns ~$1.9k at $25k (≈7.8%/yr) vs
  ~2.3% capped here: if Y turns out near 1, Y_rule 4 gives up ~5pp at $25k-$100k. Section 8's fit
  of Y from live participation decides; do not loosen the cap before it identifies.
- Noise dominates past $1M decay (QQQ impact x many trades a day); IBS decays slowest.

## Consequences for the plan (scale_plan.md stands, with numbers)
- **Roth first, always**: same legs, no tax, beats a held index to ~$2.5M.
- **Taxable: run the book to ~$250k**, then route new taxable money to a held index (or MNQ-only
  pieces) unless a later study finds a liquid edge. Not tested here, next: the book's intraday
  noise leg as an overlay on an account whose overnight money is held index (the legs use
  daytime buying power, so "bot or index" may be "bot on top of index").
