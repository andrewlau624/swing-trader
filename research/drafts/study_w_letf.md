# Study W — leveraged ETFs inside the night leg: DEAD (the extra bp is leverage, not edge)

Pre-registration: `round1_prose.md` Round 8 (commit c81bda5). Script: `research/sim/night_letf.py`.
Output: `data/research/program/night_letf_out.txt`. N = 611.

LETF picks 2021-26: 1,268 (13.6%), 232 in 2021-23 vs 1,036 in 2024-26 (single-stock LETF
launches); 783 single-stock. Median vol20 1.43 vs 1.00 for other picks.

| test | 2021-23 | 2024-26 | 2021-26 |
|---|---|---|---|
| z excess vs same-vol-decile non-LETF (sd units) | −0.009 (t −0.2) | +0.023 (t +0.7) | +0.017 (t +0.6) |
| W1 drop, pp/yr tier / tier_hi | +0.14 / +0.46 | −1.86 / −0.58 | NW t −0.5 / −0.0 |
| W2 2x, pp/yr tier / tier_hi | −0.06 / −0.37 | +1.40 / +0.87 | NW t +0.7 / +0.2 |

- Study U's +45bp gross was the leverage: per unit of risk an LETF pick equals a non-LETF pick
  of the same volatility.
- Mechanism absent: z excess by L(L−1): 2 → +0.045, 6 → −0.032, 12 → +0.024 (no rise).
- Correction to the Study U write-up: LETF picks are NOT the scalable part of the leg. They
  are mostly single-stock LETFs (CONL, RKLX, QBTX, ASTX, HIMZ); median ADV $45M, the same
  as the rest of the leg.
- Report: W2 raises the night leg's max drawdown (tier_hi −37.9 → −40.8pp); W1 lowers it
  (→ −31.4pp) while giving up 2024-26 return: a risk dial, not an edge.
