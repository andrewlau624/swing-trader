# INTL-PREF adversarial verification (2026-10-17) - no new N

Verdict: statistical PASS survives every audit; data is real. Executable size is the open question and it is withholding- and auction-fraction-dependent.

## 1. Code audit (research/sim/intl_pref.py)
- Lookahead: CO = (open(E)+div)/close(E-1)-1. Ex-date E and amount come from ds2div effectivedate (flag 'A' only, estimated dates excluded). Canadian pref dividends are declared weeks ahead; the only forward-looking use is the event flag itself. ADV is shifted one day. No lookahead found.
- Currency: only CAD prices and CAD dividends (450 USD dividends excluded). Raw (unadjusted) ds2primqtprc. OK.
- Duplicates: (infocode,date) dup dividends summed (39 rows). Different series of one issuer are different securities, but ex-dates cluster (max 34 events on one day, 1933 ex-dates, 140 issuers). Day-clustered t (+31) is therefore overstated; ISSUER-level mean +51bp, t 12.0 (140 issuers). Still decisive.
- Yield filter 0.2-4%: inert. Ex events y min 0.17%, max 3.6%. Without filter: n 12462, net mean +32.1, median +30.4 (identical to filtered, +32.1/+30.4).
- 2023-25 only: n 1347, net mean +33.5, median +32.2 (no decay). Zero-volume ex-days: none among events (vol0 = 0%), so every event had a trade.
- Median ex-day C$ volume 136k (q25 67k, q75 263k). Ex-day open==close 9.5%, low==high 3.7%.

## 2. Independent price check (Yahoo .TO via curl, UA browser)
Sampled 42 events 2023-25 stratified by ADV tercile (14 each); 28 resolved (12 ticker not found/mapping, 2 date missing). On the 28: open, close and prior close match Datastream to <0.001 C$ in 28/28 (0% mismatch, all three terciles); Yahoo dividend on the ex-date matches ds2div in 28/28. CO mean ds +38.8bp vs Yahoo +38.8bp.
Limits: (a) Yahoo's TSX feed is probably not independent of the exchange tape, so this confirms the vendor print, not that a retail MOO fills at it; (b) only 2023-25; (c) 12 of 42 unmapped (ticker syntax), so liquid/thin split is uneven; (d) no intraday TSX source (Alpaca does not cover TSX), so "first-print vs auction" is unverified. Datastream open==prior close 3.4% on ex days vs 14-16% non-ex, consistent with real opens.

## 3. Execution facts (search snippets unless noted; PDF fetch unreadable)
- TSX MOO is a single-price opening call, orders 7:00-9:30, COP = max-volume price; unfilled non-LOO orders roll into the book (tsx.com Order Types guide, search snippet). No snippet excludes preferreds from the open; inference only.
- MOC: 2017/18 guide excluded ETFs, preferreds, rights, warrants...; the current v1.77 (Sept 2026) list reads ETFs, rights, warrants, notes, debentures, exchangeables (preferreds absent) - snippet, unverified. CC / close leg eligibility must be confirmed with TMX.
- IBKR TSX: general page lists MOO/MOC but nothing confirmed per-exchange for TSX or for preferreds. UNVERIFIED; needs a 1-share test.
- IBKR CAD stock commission: tiered CAD 0.008/sh (<=300k/mo), fixed CAD 0.01/sh, min CAD 1.00, max 0.5% (interactivebrokers.ca pricing page snippet). Negligible at ~C$5k tickets (a few bp). FX conversion cost not sourced; assume ~2-5bp round trip (inside the 10bp).
- Withholding: DTC TaxRelief guide (snippet): IRAs (trad and Roth) are exempt, NR301 not required, EDS code IRA001. But practice varies: Forbes 2014 and forum reports say many custodians withhold 15-25% and reclaim is NR7-R per security per payment. IBKR-specific handling NOT found. Treat 0% as best case, 15% as the planning case.
- 15% on a ~1.26% dividend = ~19bp. Net per event: 0% wht +33.5bp (2023-25), 15% wht about +13bp (all-years +32.1 -> ~+13).

## 4. Capacity (2023-25 events, ex-day C$ volume)
~449 events/yr on ~79 ex-dates/yr (nightly choose highest yield first, deploy min(cap, 5% x auction volume)). Open-auction volume is unknown, so scenarios on auction share of day volume. %/yr = gross dollars x 50% capture / account (CAD->USD ignored):
| auction share of day vol | $10k 0% wht | $10k 15% | $25k 0% | $25k 15% |
|---|---|---|---|---|
| 100% (upper bound) | 16.8 | 8.3 | 11.7 | 4.7 |
| 25% | 9.4 | 3.4 | 6.0 | 2.2 |
| 10% (likely) | 6.0 | 2.2 | 3.0 | 1.1 |
Dollars plateau (~C$1.2-3.4k gross at 10% to 100% share), so %/yr falls with size.

## Bottom line
Mechanism and data survive; not a >=+8pp item at $10k except in the optimistic corner (0% wht AND auction >= ~25% of day volume). Likely executable: ~6pp at 0% wht, ~2pp at 15%. Gates before any pilot: IBKR TSX MOO on a preferred (1-share test), actual Roth withholding, measured auction size.
