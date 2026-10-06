# Study FND: physically-settled commodity futures at first notice (2026-10-04)

Pre-registered mechanism probe. Object = the nearby/deferred calendar spread and the OI/volume
migration around first notice day (FND), for physically-settled CL/NG, contrasted with the
financially-settled ES roll already tested (Study FUT-ROLL).

## Physical mechanism (established before any return was read)
- **CL:** first notice day ~ the 25th of the month preceding delivery; the nearby becomes a
  *deliverable* contract at Cushing. A short who fails to exit before FND must deliver physical
  barrels (or buy back the spread). A long who stands for delivery must take barrels and store them.
- **NG:** FND ~ the last business day of the month preceding delivery, delivery at Henry Hub.
- Constrained parties: producers/merchants (natural shorts), physical consumers/refiners
  (natural longs), storers (capacity-limited), and financial speculators who cannot take delivery.
- The physical constraint is real and unavoidable for those without storage/delivery capability.

## Data (free, Databento GLBX.MDP3)
- Individual CL/NG contracts, `ohlcv-1d` 2011-2025 (cached `glbx_CL_daily.parquet`, `glbx_NG_daily.parquet`).
- `definition` gives `expiration` (last trade day); FND is the standard calendar rule (hardcoded, not fitted).
- OI (`statistics` stat_type 9) is pullable but expensive to backfill; volume from the daily bars is the
  proxy used here, **explicitly labelled as a proxy** (OI migration ≠ volume migration, though both fall away at FND).

## Results

### Spread event study (nearby − deferred, bp of deferred)
| root | spread −20d→FND | FND→+5d | FND→+10d |
|---|---|---|---|
| CL | −14.6 (t −0.1, med +5.9, ex5 −152.6) | +205.7 (t 1.47, **med +3.9**, ex5 −23.9) | +87.8 (t 0.82, ex5 −75.1) |
| NG | +199.9 (t 1.3, ex5 −73.2) | +59.2 (t 0.34, ex5 −181.2) | −85.6 (t −0.5, ex5 −312.6) |

Every mean is **outlier-carried**: medians are single-digit bp, ex-top-5 is ~0 or negative, and the
sign flips between CL and NG. **No clean, sign-stable spread distortion.**

### Mechanism evidence (volume migration, proxy)
- **CL:** nearby volume share collapses 0.90 → 0.55 into FND, recovers to 0.91 after — a strong
  physical-delivery migration signature.
- **NG:** nearby share stays 0.92-0.98 — almost no migration (delivery is more diffuse / the
  contract stays liquid).
- The CL signature is the **same shape** as the ES financial roll (front share 0.48→0.37) that
  Study FUT-ROLL showed has been arbitraged away since ~2021. A visible migration signature is
  necessary but not sufficient for a tradable distortion.

## Verdict: **KILL** (outcome: artifact/carry-and-seasonality; branch closed by user 2026-10-04)

Final classification: **KILL**. The physical mechanism is real but the spread effect is not harvestable,
and the physical-settlement branch is closed — no FND variants, no further physical-delivery variants.
The physical constraint is real (CL migration proves it), but it does **not** produce a sign-stable,
median-positive calendar-spread distortion that survives ex-outliers. The apparent spreads are (a)
ordinary carry/convenience yield, (b) seasonal (NG winter), and (c) mean-carried by a few squeeze
events (e.g. 2020 negative-WTI, 2021-22 gas squeezes). This is the "B/C" category, not "A".

Answer to the key question: **physical delivery, as expressed in the front calendar spread, is not a
new harvestable inefficiency — it is carry/seasonality plus a few well-known squeezes.** The
observable migration keeps the market honest: when the constraint binds, it binds for the straddling
speculator too (delivery risk), so there is no free side.

## What would falsify / next
- A falsification of this verdict would need a *median* (not mean) spread move, stable in sign across
  both CL and NG and across storage regimes, surviving ex-top-5. It does not appear in daily data.
- The next genuinely different futures mechanism is **not** another FND variant. Candidates:
  futures-based **volatility-target / CTA repositioning** (scheduled deleveraging), **settlement
  auctions (SOQ)**, and **cross-asset basis** (e.g. futures vs the physical/ETF). Recommend one of
  those, not more physical-delivery windows.
