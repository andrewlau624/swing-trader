# Study U — where the night leg's edge lives: U1/U2 DEAD as registered; the classes were mislabeled

Pre-registration: `round1_prose.md` Round 7 (commit 874c815). Script: `research/sim/night_classes.py`.
Output: `data/research/program/night_classes_out.txt`, diagnostic `night_classes_diag.txt`.

## Registered result
U1 (drop "ETP") and U2 ("ETP" only) fail at tier and tier_hi: NW t −0.8..+1.0, placebo 38-66.
N = 609.

## The classification was wrong (found in the diagnostic, stated here so nobody reuses it)
- EDGAR's entity/ticker index does not cover ETF series. "UNMAPPED" (15% of picks) is mostly
  **leveraged / inverse ETFs**: LABD 46, NAIL 35, CONL 25, LABU 24, SOXL 23, GDXU, RKLX, YANG...
  It is NOT "names that later delisted"; the lookahead worry in the pre-registration was wrong.
- "ETP" (entityType != operating) is mostly **foreign private issuers** (Chinese ADRs: BTDR, EH,
  DQ, FUTU, GDS, VNET, YMM, NNOX) plus commodity pools (KOLD 58, BOIL 25, UVIX 27).
- OPER-GONE caught 1 pick: Study T's cache has no delisted CIKs to begin with (today's index).
So U1/U2 tested an arbitrary mix. Their DEAD verdict stands for what was run; it says nothing
about LETFs or ADRs as such.

## Diagnostic (NOT pre-registered): w-weighted GROSS bp per trade, 2021-26
| real class | n | 2021-23 | 2024-26 | all | median ADV |
|---|---|---|---|---|---|
| leveraged/inverse ETFs (+ unmapped rest) | 1,401 | +19.5 | **+44.9** | +37.3 | $41M |
| foreign ADRs + commodity ETPs | 1,406 | +32.9 | +40.6 | +36.7 | $51M |
| US operating companies | 6,538 | +21.8 | +16.7 | +19.1 | $42M |
| all | 9,346 | +23.4 | +25.6 | +24.6 | $43M |

Units note for anyone re-reading Study T/U tables: equal-weighted per-trade NET at `tier`
(~9.6bp/side) is −2.6bp for the whole leg; the book's weights (crowding scale) make gross
+24.6bp; live costs are ~0-1bp/side (NEXT.md). Read the leg at weighted gross minus live cost.

## Hypotheses this opens (each needs its own pre-registration with a PROPER classifier)
1. **LETF close-rebalance reversal.** Leveraged ETFs must buy/sell at the close in the
   direction of the day's move; on a big down day they sell into the close, depressing it, and
   the price relaxes overnight. Mechanism-backed, and LETF ADV is large: the most scalable
   part of the leg at $500k+. Test: weight LETF picks up vs down, by leverage factor.
2. **ADR overnight = home-market session.** A Chinese ADR's close->open spans the Asia session;
   the "bounce" may be information (home market), not overreaction. Test by region (Asia vs
   Europe listing) and against the home index's overnight return.
Classifier: an issuer/ETF list with a point-in-time flag (e.g. the panel's asset metadata
exchange + a fund-name rule applied at d, guarded against ticker reuse as in add. 36).
