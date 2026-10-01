# Study AN — night-leg pick quality: a point-in-time EDGAR classifier (Round 17)

`research/drafts/round1_prose.md` Round 17, Study AN (pre-registered before any number).
Code: `research/sim/night_quality.py`. Output: `data/research/program/night_quality_out.txt`.
N = 642 -> 659 (5 variants). Classifier: EDGAR forms accepted in the 400 days before the pick;
LETF from `new_listings.etf_kind`.

## Classifier (this fixes Study U's mislabels)

Study U's "UNMAPPED" = leveraged ETFs and its "ETP" = foreign ADRs. This classifier separates them
(9,546 raw-pool picks):

| class | n | share | median ADV | mean net (bp), 21-23 / 24-26 |
|---|---|---|---|---|
| US_OPER (10-K/10-Q, operating) | 6,362 | 66.6% | $41.5M | −0.1 / −0.1 |
| LETF (leveraged/inverse) | 1,287 | 13.5% | $44.9M | −0.4 / +0.6 |
| ETP (non-operating / SIC 6221) | 1,374 | 14.4% | $48.9M | +0.5 / +1.1 |
| FOREIGN (20-F/40-F/6-K) | 161 | 1.7% | $56.5M | +7.3 / +1.8 |
| NOMAP (no CIK) | 202 | 2.1% | $32.6M | +1.1 / +5.0 |
| OTHER | 160 | 1.7% | $40.1M | −0.2 / −3.1 |

The Study U/T pattern reproduces with a proper classifier: **FOREIGN picks earn ~+5bp** and US
operating picks ~0; the LETF bucket is **not** an edge (21-23 −0.4bp), confirming Study W.

## Variants

| variant | tier inc 21-23/24-26 (pp/yr) | tier_hi inc | NW t (th) | placebo |
|---|---|---|---|---|
| AN1 drop US_OPER | +0.22 / +0.16 | +0.89 / +0.78 | 1.86 | 98% |
| AN2 keep FOREIGN only (n 161) | +0.02 / −0.48 | +0.97 / +0.46 | 1.07 | 100%* |
| AN3 FOREIGN 2x | +0.42 / +0.06 | +0.39 / +0.04 | 1.99 | n/a |
| AN4 drop LETF | +0.01 / −0.28 | +0.07 / −0.11 | −0.03 | 37% |
| AN5 drop US_OPER + 2x FOREIGN | +0.64 / +0.22 | +1.28 / +0.82 | 2.25 (th) / 0.85 (tier) | 98% |

\* AN2's placebo is uninformative (the subset is tiny).

## Verdict: DEAD

The class pattern is real and stable, but the tradeable increments are **≤1.3pp/yr at tier_hi and
fail t ≥ 2 at the planning cost**: AN1 t 1.86, AN5 t 0.85 at tier; AN3's 2024-26 is ~0. FOREIGN is
only 1.7% of picks, so any tilt built on it is thin and high-variance. Drop-LETF is dead (Study W
already showed the LETF gross is leverage, not edge). Nothing adopted.

- $/yr: AN1 +$20/$210 (at $2.3k/$25k, tier_hi, pre-tax); AN5 +$25/$280. Too small to act on.
- Capacity is not the limit (median ADV $40-57M; the leg is ~$115/name at $2.3k, ~$1.15k/name at
  $25k); the limit is signal size.

## What would change it

A decade of forward picks, or a larger FOREIGN share of the pool (it is 1.7%). Revisit only as a new
pre-registration if (say) 2027 picks keep FOREIGN ahead of US_OPER by > 5bp with n > 400.
