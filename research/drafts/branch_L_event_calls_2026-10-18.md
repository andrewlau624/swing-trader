# Branch L - special-event redemption clauses in $25-par paper (desk research, 2026-10-18; no backtest, no N)

Verdict: ZERO cards clear the +8pp gate; no pre-registration draft written. The clause is real and common, but (a) every documented
exercise I could find was a PAR call on a high-coupon issue that traded at or above par (the wrong side), (b) I found NO exercise of
the $25.50 "Rating Agency Event" call on a below-par issue, and (c) the one recent methodology change (Moody's 2024) went the other way.
Sources opened: SEC EDGAR full-text search (User-Agent "research andrewlau2007@gmail.com"; .env not read) and the sec.gov filings below,
plus web-search summaries (marked). Price evidence for 2010-13 could NOT be obtained: Sharadar preferred/ETD coverage starts ~2014
(437 of 1,700 tickers first-priced in 2014; scratch query on tickers.parquet), CRSP stocknames has no bank REIT prefs or trust-preferreds
(query on crsp.stocknames), FISD fisd_redemption has callable/make_whole/call_in_whole flags but NO special-event (tax/capital/rating) flags
(columns listed via information_schema), so a "price at trigger vs call price" series needs TAQ with hand-found tickers (not done).

## Mechanism and clause map (opened prospectus/8-K text)
- Rating Agency Event, 102% ($25.50/depositary share, within 90 days, whole series, only before first call date): Allstate (to 2024-10-15),
  Brighthouse Series A (to 2024-03-25), AIG A, American National A/B/D, Alabama Power Class A 2017 (to 2022-10-01; narrower: only a
  change that REDUCES equity credit vs issuance), Arch, Argo, Athene A/E, Air Lease B, Enstar, SiriusPoint (EDGAR FTS hit list + 424B search
  results). Regulatory Capital Event call on the same issues pays par $25.00 (Brighthouse, American National; search summaries).
- Special Event (Tax / Investment Company Act / Regulatory Capital) at $25 par: older bank trust preferreds and bank REIT prefs
  (Wachovia Preferred Funding 7.25% A, 2003 prospectus: "not redeemable before 2022-12-31 except upon a Special Event").
- S&P rule (search summary of S&P criteria, March 2022 PDF, unverified by me): redeeming a hybrid early without replacement strips equity
  credit unless the cause is an "External Event". This is why issuers are happy to use an external-event clause when they want out.

## Episodes (all I could source; trigger -> call)
| Episode | Public trigger | Call | Price vs call | Source |
|---|---|---|---|---|
| Bank REIT/TruPS, Basel III | final rules adopted 2013-07-02 (proposal 2012-06) | Huntington Preferred Capital 7.875% C: board approved 2013-11-07, redeemed 12/31 at $25; Wachovia Preferred Funding 7.25% A ($750m, 30m sec): notice 2013-11-05, redeemed 2014-01-02 at $25; Fifth Third Capital Trust IV (TruPS, $1,000 par) 2013-12-30 | UNKNOWN prices; 7.9%/7.25% coupons on $25 par imply trading AT/ABOVE par, i.e. the call hurt holders (HPCI's own 10-K warns redemption may be below market, search summary) | sec.gov 8-K 0001193125-13-427677; HPCI 8-K 0001144204-13-059642 |
| Dodd-Frank Collins amendment | enacted 2010-07 | Wells Fargo "Capital Treatment Event" TruPS calls at par; holders sued, Judge Wilken dismissed (Pillsbury note, search summary) | holders argued call premature, i.e. price above par | not opened |
| Moody's hybrid change | 2013-07 methodology; ArcelorMittal 8.75% perp redeemed 2014-01 at 101 (search summary; one event, not $25 paper) | 6 months | n/a | not opened |
| Moody's Feb 2024 | equity credit RAISED 25%->50% for US hybrids | no trigger; issuers refinanced prefs into tax-deductible hybrids at first-call/economics | n/a | ICE note via search; my reading, unverified |
| S&P 2013, 2017, TCJA 2017, OSFI NVCC, NAIC | not sourced / no exercise found | - | - | UNVERIFIED, no instance located |
Counts: documented special-event exercises on listed $25 paper: ~3-4 in 2013 (one regulatory shock, all par, all bank sponsors), 0 located for
Rating Agency Event. Episodes per year across 2010-2026: ~0.2 clusters/yr, essentially 2010 and 2013 only. Share of eligible BELOW-par issues
called within 6 months: not measurable (no below-par exercise found; 2013 issues likely above par). EDGAR FTS phrase searches for exercise
notices ("Rating Agency Event has occurred", "Capital Treatment Event has occurred", etc.) returned 0-4 hits, none an exercise; the notices
use issuer-specific wording, so absence is weak evidence, not proof.

## Why the pre-call window is not a card
1. Direction: the clause is an issuer put against the holder; it pays the holder only when price < $25 (or $25.50). Special-event calls
   fired when the regulatory shock made the issue costly (high coupon, lost Tier 1), and those issues trade above par.
2. Below-par issues are low-coupon (issued 2017-21) and rate-depressed; a Rating Agency Event on them needs an agency to REDUCE equity credit.
   The last visible move (Moody's 2024) increased it. Trigger probability per year is small and not forecastable from the public rule text.
3. Issuer incentive is weak even when triggered: redeeming at $25.50 when the issue trades $20-23 is cheap capital retirement, but the
   issuer loses that tranche of equity credit; the call is an option, not an obligation, and 2013 shows banks used it only where the capital
   treatment was lost outright.
4. Event is binary and slow to resolve if the issuer waits (90-day window), so a below-par holder can sit months with no call.

## Ceiling (gate)
events/yr x net edge x deployable share x 50% capture: even granting a repeat of one Rating Agency Event cluster every 5 years (0.2/yr), a
+12% repricing on one name, 30% of account in the held name(s), 50% capture = 0.2 x 12% x 30% x 50% = 0.36pp/yr at $10k ($2.3k, $25k same %,
fixed by share). Hold length: up to 90 days after the event, 0 days before it (you hold the pref as ordinary carry; the pref carry itself
is not an event edge). Needs a pre-event holding position in an under-par pref: that is the PREF-EX-style carry, not this mechanism.
Far below +8pp. Ceiling-kill.

## Watch item (log-only, no code, no N)
Trigger watch: S&P/Moody's/Fitch hybrid-criteria publications that REDUCE equity credit for preferreds. If one appears, list issues with a
$25.50 Rating Agency Event clause trading under ~$24 (the clause set above; Allstate H/I/J, Brighthouse, AIG, Alabama Power, Athene, Air Lease,
Arch, Argo, ANG still pre-first-call) and read the issuer 8-Ks over the next 90 days. Cheap to do by hand; not a systematic rule.

## Dropped
- TCJA 2017 Tax Event / NAIC / OSFI NVCC episodes: no exercises located; TCJA lowered rates, did not change TruPS deductibility (UNVERIFIED).
- Systematic EDGAR scan of special-event calls: FTS can't isolate exercises; ceiling < 0.4pp so not worth the effort.
- Pre-registration draft: not written (no repeatable post-trigger, pre-call window with a large median gap was found).
