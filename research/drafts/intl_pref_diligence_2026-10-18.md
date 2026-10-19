# INTL-PREF execution and tax diligence (2026-10-18; no N, no orders, nothing bought)

Fetch date for every source below: 2026-10-18. Quotes are from WebSearch/WebFetch summaries (the fetch tool paraphrases through a small model; treat "quote" marks as the tool's output, not a PDF read by me). Nothing marked UNVERIFIED was confirmed.

## Verdict
UNCERTAIN: survives on cost, execution and withholding unproven. The 10bp RT cost assumption holds only at tickets >= ~C$2k (IBKR C$1 per-order minimum). Net edge stays ~+30bp at 0% withholding and ~+10bp at 15%. Likely executable ~5-6pp/yr at $10k with 0% withholding, ~2pp at 15%. Three items only a live 1-share test resolves (below). Not a >=+8pp item except in the optimistic corner already named in intl_pref_verify.

## 1. TSX open
- Verified (https://www.tsx.com/ebooks/en/order-types-guide/): "Market on Open (MOO) – All matching orders are executed at a single opening trade price"; "a visible single price opening call market at 9:30 a.m."; entry 7:00-9:30, not executed in pre-open. Unfilled non-LOO orders carry into the continuous book; unexecuted LOO cancelled.
- Verified (same guide): "If there are no trades at the Opening, the close price from the previous trading day sets the open price." So a pref with no opening-call trade has a reported "open" = prior close, which on an ex-date is the cum-dividend price and would show a fake ~0 drop. Datastream/Yahoo open==prior close on ex days was 3.4% of events (verify note), so this is the minority case, but in those cases the real order is NOT filled at that price; it rolls into the book.
- Dedicated MOO order type (must be completely filled at the open, cancelled if unfilled, accepts odd lots): TSX/TSXV MOO enhancements primer https://www.tsx.com/en/resource/3381/tsx-tsxv-market-on-open-enhancements-2025-08-01-en.pdf (proposed Jul 2025, Q4 2025 go-live subject to approval) and described in guide v1.77 (Sept 14 2026) per search result. Odd-lot acceptance: per search summary.
- Rule book (effective Sept 14 2026, https://www.tsx.com/en/resource/1464): Rule 4-701 "Opening Eligible Securities shall open for trading at the opening time, and any opening trades shall be at the calculated opening price"; market orders must be completely filled at the open. The definition of Opening Eligible Securities was NOT retrieved. UNVERIFIED: that preferreds are opening-eligible (no exclusion found anywhere; inference only).
- Retail guarantee: a market/MOO order is filled in full at the single opening price if there is an opening trade, so it prints at the official open, not a quote. Cost is then spread-free (like US crosses) but exposed to a thin call's price impact (the 5%-of-auction cap in the plan addresses this; auction size is unmeasured).

## 2. TSX close
- Verified (guide): "All TSX listed equities are eligible for the TSX MOC Facility", exclusions ETFs, rights, warrants, notes, debentures, sustainable bonds, exchangeables. Preferreds are not excluded. The guide's MOC volatility table has a row "Preferreds 1% 5%" (PME 1%, CPA 5%), which shows preferreds are treated as MOC participants. This upgrades the earlier "unverified" to: eligible (high confidence). Older 2017/18 guides excluded preferreds (earlier verify note, snippet); the current text controls.
- MOC cutoff is now 3:50 pm (imbalance period 3:50-4:00, no cancels/amends); older 2013 guide said 3:40. "MOC orders are priced at 'market' and only execute at the MOC calculated closing price." Use 3:50.
- The buy leg (E-1 close) therefore can be MOC. The plan's 15:50 spread check falls on the cutoff: decide before 15:50.

## 3. Withholding
- Treaty: Article XXI(2) exempts dividends to a US-resident tax-exempt retirement arrangement (IRA incl. Roth). Sources via search: https://www.dtcc.com/-/media/Files/Downloads/Settlement-Asset-Services/Global-Tax-Services/Canada.pdf (DTC TaxRelief: IRAs exempt, NR301 not required, EDS identifier "IRA001"; CRA does not require a CRA id to elect 100% for an IRA) and https://www.canada.ca/en/revenue-agency/services/forms-publications/information-on-forms-nr301-nr302-nr303.html (NR301 cannot be used for Article XXI; letter of exemption route, T4016). Article text itself not fetched (UNVERIFIED verbatim).
- So the mechanism is a broker-side DTC election, not a form I sign. Whether IBKR makes it for TSX positions in a US IRA: NOT FOUND. Forum/press reports (earlier verify note) say many custodians withhold 15-25% and the holder reclaims via NR7-R. UNVERIFIED for IBKR. Planning case remains 15%; 25% if the account is treated as having no NR301/W-8 treaty claim (W-8BEN on file normally gives 15%).
- Taxable account: 15% treaty rate with W-8BEN; creditable on Form 1116 (https://bluecloudcpa.com/guides/cross-border-dividend-tax-canada-us, secondary). Qualified-dividend status of Canadian prefs for US tax is not checked (UNVERIFIED).
- Eligible-dividend gross-up / dividend tax credit: Canadian resident mechanics only. Non-residents pay Part XIII tax on the gross dividend; gross-up irrelevant. (Standard, not separately sourced here.)
- In an IRA a withheld 15% is not creditable: pure loss.

## 4. IBKR costs (https://www.interactivebrokers.com/en/pricing/commissions-stocks.php and .ca equivalent, via search summary)
- CAD-priced Canadian stocks, Tiered: CAD 0.008/sh (<=300k sh/month), min CAD 1.00 per order, max 0.5% of trade value; clearing CAD 0.00017/sh capped CAD 2.00; exchange and regulatory fees additional (amounts NOT retrieved, UNVERIFIED). Fixed: CAD 0.01/sh, min 1.00, all fees included (third-party statement). Orders that persist overnight count as new orders for minimums (irrelevant to MOO/MOC).
- FX (third-party, not IBKR page): manual IDEALPRO conversion 0.2bp of value, USD 2 minimum, near interbank; auto-conversion ~0.03% (3bp). Holding a CAD balance means FX is paid on funding and on withdrawing the dividend profit, not per trade.
- Round-trip commission in bp (2 sides, tiered, price ~C$25, + clearing 0.017c/sh; exchange fee unknown, allow ~1bp):
  | ticket | shares | commission per side | RT bp |
  |---|---|---|---|
  | C$1,000 | 40 | C$1.00 (min) | ~20 |
  | C$2,000 | 80 | C$1.00 (min) | ~10 |
  | C$3,000 | 120 | C$1.00 (0.96 -> min) | ~7 |
  | C$5,000 | 200 | C$1.60 | ~6.5 |
  Add ~1bp exchange/regulatory (guess) and ~0.1bp FX at manual rates.
- Implication: the verify note's executable tickets (5% of a thin pref's auction, C$1.2-3.4k per night split across names) are often C$500-2,000 per name, where the C$1 minimum pushes RT cost to 10-40bp, above the 10bp modeled. Concentrating each night on the 1-2 highest-yield names improves it.

## 5. Access
- TSX FAQ for US retail (https://www.tsx.com/en/resource/2674/): US citizens can buy TSX/TSXV listings through a US broker; names IBKR, Fidelity International, Schwab; IBKR gives full TSX quotes, priced in CAD. So TSX listings directly, not OTC "F" lines. Fractional TSX shares at IBKR since Aug 2023 (press release, search result).
- IRA: IBKR offers Traditional/Roth IRA (stockbrokers.com review, Sept 2026: stocks, ETFs, options). Whether a US IRA can trade TSX with the 'Canada' stock permission: NOT FOUND in any source. UNVERIFIED; IRAs commonly allow multi-currency but this needs IBKR's confirmation.
- IBKR order types on TSX: IBKR MOO page (https://www.interactivebrokers.ca/en/trading/orders/moo.php) lists MOO (OPG time-in-force) for stocks, US and non-US, directed routing; MOC "executes on the Primary Listing Exchange". Per-exchange TSX availability is not shown. UNVERIFIED. Also UNVERIFIED: IBKR's internal MOC cutoff for TSX (likely before 15:50).

## Net edge and %/yr at $10k
Research: CO +32bp net at 10bp RT, so gross ~+42bp at 0% withholding. Backfill (60 sessions, not evidence): +40 / +20bp at 0/15%; the 12bp implied difference in the headline and the 20bp in the backfill both come from dividend x 15% (avg dividend ~1.3% of price; drop/div 0.65 in backfill).
| ticket | RT cost | net 0% wh | net 15% wh (-~20bp) |
|---|---|---|---|
| C$1,000 | ~21bp | ~+21 | ~+1 |
| C$2,000 | ~11bp | ~+31 | ~+11 |
| C$3,000-5,000 | ~7-8bp | ~+34-35 | ~+14-15 |
%/yr at $10k, rescaling the verify table (which used 10bp) for a ~12bp average cost (tickets ~C$1.5-2k): 100% auction share 15.8 / 7.8; 25% share 8.8 / 3.0; 10% share (likely) 5.6 / 1.9 (0% / 15% withholding). These are 50%-capture, CAD->USD ignored, scale roughly linearly with the net per event. Below the +8pp gate except the optimistic corner. Add ~0.03% FX to fund the CAD balance if auto-converted (negligible per year).

## What only a live 1-share test can resolve
1. IBKR (US IRA or taxable) accepts a TSX MOO/OPG order on a pref and fills at the official open print (vs rolling into the book, filling a bar later, or being rejected); same for MOC and IBKR's TSX MOC cutoff.
2. Whether the IRA can trade TSX at all, and actual dividend withholding on a Roth/IRA (0% vs 15% vs 25%) with timing of any NR7-R reclaim; read it off the first dividend statement.
3. All-in fees on a small ticket (exchange/regulatory add-ons, true minimum), FX fill vs mid, and the opening-call size/price impact on thin prefs, including how often the pref has no opening trade.
Plus (not testable with 1 share): whether the +3.4% no-open-trade rate hurts net by unfilled-at-open exits.
