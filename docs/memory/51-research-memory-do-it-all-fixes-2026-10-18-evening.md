# Research memory — "do it all" fixes (2026-10-18 evening)

- **TAX-NOWASH (N 1029): KILL.** Taxable-only wash risk on PREF-EX is small (3.5% of price-loss sales; a 31-day same-issuer
  exclusion gives +4.4pp at $10k cash), but the live Roth buys the same ex-date events, so ~99.9% of taxable price losses are
  permanently disallowed (Rev. Rul. 2008-5): -10pp at $10k. Disjoint issuers +2.0pp, 3x cost -0.3: fails. **Never run PREF-EX/
  ETDX in the taxable book while the Roth runs it.** (Process: loss definition corrected from net-of-dividend to price-only after
  v1 was read; v1 kept.) `research/sim/tax_nowash.py`, `tax_nowash_out.txt`.
- Roth IBS suppression: the Roth bot book is ~$1,000 of a ~$7.6k Roth (DAILY_ROTH_CAPITAL); SMH->SOXX rounded the $500 leg to 0
  shares (fixed: SOXQ); XBI skip is correct wash protection. The memo's +1.4-2.5pp "Roth runs IBS" assumed a full-size Roth book.
- CEF-RV live module in `dry` from 2026-10-19; dry holdings no longer feed cef-rv-held.json (they shrank the Roth night cash).
