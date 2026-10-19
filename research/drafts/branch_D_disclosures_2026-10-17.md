# Branch D: regulatory disclosures that reveal forced future transactions (2026-10-17)

Verdict: ZERO surviving cards. Every N-PORT-family lead fails at step one (the disclosure is not public).
The one asset-side lead that has a named forced seller (rating-mandate fallen angels in listed $25 paper) has a
ceiling of ~0.1pp/yr at $10k. One useful by-product: the program's "no free PIT ratings" claim is false (FISD).
No performance backtest was run. Descriptive counts below touched FISD ratings 1998-2025 only.

## Evidence on each lead

### 1. N-PORT / Rule 22e-4 15% illiquid limit: DEAD, nothing public
- Position-level liquidity classifications go to the SEC confidentially. The 2018 amendments (IC-33142, 83 FR 31859) also removed
  the planned public aggregate liquidity buckets. "The Commission will continue to receive non-public position level liquidity
  information on Form N-PORT." (https://www.sec.gov/files/rules/final/2018/ic-33142.pdf, via search summary; I did not open the PDF itself.)
- The 15% breach report (Form N-RN, ex N-LIQUID) is due within one business day, but the SEC states it "does not intend to make
  public information reported on Form N-LIQUID that is identifiable to any particular registrant"
  (https://www.sec.gov/files/formn-liquid.pdf, search snippet). Funds only say in N-CSR whether any were filed.
  The form wording after the N-RN rename was not confirmed. Even if public, an open-end fund over 15% sells illiquids slowly, and the
  holdings are mostly not exchange-listed.
- Public N-PORT holdings come with a 60-day lag. Per memory/ledger: "N-PORT 60-day lag, heavy, TEXTBOOK -> killed" (R2-11, Coval-Stafford
  fire sales), and F13C-CAP killed the participant-typed 13F family (no tradable footprint). N-PORT adds nothing the 13F-state panel lacked.

### 2. Fund liquidations / mergers / ETF closures forcing sales of thin holdings: CLOSED
- ETF closures: DL6 9 liquidations, median -0.24% (NEXT ledger, `research/sim/etf_closures.py`). CEF mergers/open-endings: G48, A4, C7, I9
  parked or killed (NAV risk, no NAV history, Roth cannot hedge). N-14 sweeteners: discovery_ideas_c5.
- Mechanism limit: a liquidating equity fund's sale schedule is not public (497 supplement gives a date, not a list); public
  holdings are 60+ days stale at that point, so position size vs ADV cannot be known when it matters.

### 3. 1940-Act 75-5-10 and Subchapter M diversification breached by price moves: NO FORCED SALE (mechanism fails)
- 15 USC 80a-5(c): a diversified company that met 5(b)(1) when it qualified "shall not lose its status... because of any subsequent
  discrepancy", unless the discrepancy right after an acquisition is partly caused by that acquisition (opened and read:
  https://www.law.cornell.edu/uscode/text/15/80a-5).
- 26 USC 851(d)(1): same structure for RIC status. A discrepancy caused by market value alone never costs status, and an
  acquisition-caused one has a 30-day cure after quarter end (opened and read: https://www.law.cornell.edu/uscode/text/26/851).
  A price move that pushes a position over the limit therefore forces nothing. At most it blocks further buying, which is a
  non-event for the price.

### 4. NAIC designations / insurer RBC / fallen angels: real forced seller, wrong instrument
- Mechanism is documented. Ellul-Jotikasthira-Lundblad (JFE 2011): constrained insurers sell downgraded bonds, with price declines
  and subsequent reversals, larger when insurers are distressed (abstract via search: https://kenaninstitute.unc.edu/publication/regulatory-pressure-and-fire-sales-in-the-corporate-bond-market/;
  paper not opened). Insurers hold more than one-third of IG corporate bonds. Preferreds carry an RBC charge by NAIC designation too
  (NAIC instructions, search summary only).
- The forced sellers hold institutional $1,000-par bonds. They do not hold $25 retail baby bonds, which is the only instrument this
  account can trade (bonds: 1-2% dealer markup per ledger). So the price pressure is in an instrument the account cannot reach.
- A second forced seller does exist on the $25 side. ICE Exchange-Listed Fixed & Adjustable Rate Preferred (PSK) requires an
  investment-grade rating by Moody's or S&P (ICE PSK methodology snippet). PFF has no rating rule in the sources seen. PGX takes B3+.
  PSK holds a small fraction of any one issue, so its deletion is a small flow. The index delete date is observable only after the
  rating change, and PREF-INDEX is already CEILING-KILLED (no PIT holdings history).
- Descriptive count, FISD (Mergent) `fisd.fisd_ratings` (S&P, `rating_type='SPR'`), exchange-listed issues with principal 25, first IG to HY transition at issue level:
  379 issue-events 1998-2025 across about 250 issuer-years. Distinct issuers per year: 2015: 1, 2017: 1, 2018: 3, 2019: 5, 2020: 8,
  2022: 1, 2023: 4, 2024: 1, 2025: 1 (the 2008-09 crisis had 30 and 63). Many are same-day batch re-ratings of one issuer's
  series, and I did not clean the 2020-07-22 cluster, so treat counts as an upper bound. Output: scratchpad `fa_listed.csv`.
  About 2 clean distinct issuers per year outside crises.
- Ceiling at $10k: ~2-3 events/yr x ~5% reversal edge (assumed, not measured) x ~10-20% of account x 50% capture = about 0.1pp/yr.
  At $25k it is the same percentage, smaller dollars. Downside: the moves are in the announcement gap, and issuers that lose IG often
  keep falling. KILL on ceiling before any test.
- Capital lock would be 30-60 days. Failure-mode: no reversal exists when the issuer is genuinely distressed (2023 First Republic).

### 5. Bank regulatory-capital disqualification of preferreds; Fed H.4.1: DROP (from memory, no source opened)
- Capital disqualification of TruPS/hybrids is a phase-out that ended long ago. Remaining events are calls and redemptions, which are
  a price-to-par pull already inside PREF-EX/ETDX carry (deep_loop and PREF-INDEX notes).
- Fed facility purchases (H.4.1 weekly) are crisis one-offs (2020 corporate credit facilities). They are not a recurring forced flow
  and cannot be pre-registered as a rare, recurring event.

### 6. TRACE + baby bonds of the same issuer: no forced party
- TRACE has no signed participant flow for the account to follow. BOND-LEAD (N 948) already killed bond to stock lead 2006-15. Same-issuer
  baby bond vs common is PAIR-CLASS/PREF-EX territory (no convergence force).

## By-product (data correction, high value for other branches)
- `fisd.fisd_ratings` (4.70M rows) and `fisd_rating_hist` (2.27M rows) are accessible: point-in-time issue-level S&P/Moody's/Fitch rating
  histories with dates and reasons (UPG/DNG codes seen). The ledger rows "fallen angels DATA-LIMITED: no free PIT ratings" and
  `wrds_recon` listing PIT ratings as still blocked are WRONG for issue-level ratings. Caveats: rating dates are agency dates, not
  bond-trading dates. `fisd_issue.denomination` is a string like "1/1", so use `principal_amt` (25.0 flags $25 paper). FISD
  `fisd_issue_exchange` listed issues are 15,172, mostly institutional notes with exchange flags, so the $25 filter is required.
- This opens fallen-angel work for bonds (TRACE in hand), but bonds are not retail-executable and equity reaction is in the gap, so
  no candidate follows for this account.

## Dropped list
- N-PORT liquidity / 15% breach: non-public (IC-33142; N-LIQUID instructions).
- N-CEN, N-MFP, N-CSR: no forward-looking forced transaction; N-CSR text already killed (CEF-TXT).
- 75-5-10 and RIC diversification: acquisition-tested only, no price-forced sale (80a-5(c); 26 USC 851(d)).
- Fund liquidation/merger/ETF closure: DL6, G48, A4, C7, I9, R2-11, F13C-CAP.
- NAIC fallen-angel bond pressure: instrument not reachable; $25 side ~0.1pp ceiling.
- Bank capital disqualification, H.4.1: no recurring event.
- Form 13F-NT / Form 4 for funds: 13F filer-disappearance REJECTED (54 events), Form 4 variants excluded.
