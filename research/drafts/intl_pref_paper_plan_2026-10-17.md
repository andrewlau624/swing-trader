# INTL-PREF paper-trading plan (TSX $25-par preferreds, log-only)

Rule: buy close(E-1), sell open(E) (CO, primary) or close(E) (CC), keep the dividend; research CO +32bp net (10bp RT), CC +16bp.
Prototype: `research/sim/intl_pref_shadow.py` (`make intl-pref`). Log: `data/research/intl_pref/shadow.jsonl`. No orders, nothing deployed.

## Data sources (probed 2026-10-18)
- Forward ex-dates: TMX Money GraphQL (`app-money.tmx.com/graphql`, no key) `getQuoteBySymbol{exDividendDate dividendAmount dividendCurrency}`. Works, but shows only the NEXT declared ex-date (about 2-6 weeks ahead), so each name enters the scan window once. Yahoo `quoteSummary` needs a crumb (401); Yahoo chart `events=div` is past-only.
- Prices/scoring: Yahoo chart `.TO` (raw open/close/volume/div), TMX `getCompanyPriceHistory` fallback for names Yahoo covers sparsely. Universe: 492 TMX symbols from the brute force, of which 261 are stale placeholders (redeemed/dead, empty TMX history); 231 live CAD-or-USD prefs priced (213 Yahoo + 18 TMX); USD series listed but excluded from the CAD rule.
- Open caveat: Yahoo opens must be checked against the true TSX opening-auction print on a few events.

## Daily schedule (ET)
1. Weekdays 15:00-15:50: `scan` (E in next 5 TSX sessions). Review the sized list; paper "buy" is the 16:00 close of E-1.
2. After 09:35 on E (TSX open 09:30): `score` (needs Yahoo to print the day; rerun later if a row stays pending). `report` weekly.
3. Refresh `universe` monthly (new series, redemptions).
Note ex-date E is TMX's date; confirm E-1 is a TSX session (holiday list is in the script through 2027).

## To go live (user actions)
- IBKR account (Roth/IRA-type), TSX market data, CAD funding; decide CAD conversion cost (Norbert's gambit or IBKR FX; roughly 2-4bp at size) and USD/CAD exposure over a 1-night hold (small).
- Withholding: confirm IRA treatment. Treaty exempts IRAs, but custodians often withhold 15% on Canadian dividends; paper shows 15% cuts CO from about +33 to about +13bp. Get IBKR's written position (NR301/exemption handling) before real money.
- 1-share tests on a liquid pref (e.g. BMO.PR.E, RY.PS): MOC buy at the TSX close, then a market-on-open sell next day. Check the fill vs the official auction price (target 0-2bp), MOO/MOC acceptance for preferreds, and that the dividend credits.
- Proceed only after at least 5 clean round trips.

## Risk controls
- Per name: whole shares, at most 5% of the auction (default auction = 25% of 20d median C$ day volume); at $10k and $25k the liquidity cap binds, so size is similar.
- Per night: at most 100% of capital, equal split across the night's eligible names.
- Skip any name whose spread at 15:50 exceeds 1%, or that fails the frozen filters (C$10-30, 20d median value traded >= C$50k, CAD dividend).
- Kill rule: stop if the mean net of 30 live round trips is below 0, or any single night loses more than 3% of the account.
- Forward gate (paper): 60 scored forward events, CO net mean >= +15bp at 0% withholding, day-clustered t >= 2; also report the 15% view.

## Stacking with US PREF-EX
Different exchange, calendar and auctions, so the cash is free for each (TSX trades 09:30-16:00 ET, same clock as US). A night with both TSX and US ex-events splits the Roth cash; priority by edge per dollar, US PREF-EX first (already in forward shadow). TSX adds ex-nights US lacks, since Canadian banks and utilities pay on different dates. Roth-only constraints (no margin, settlement) apply to both; CAD leg adds FX conversion and withholding the US leg lacks.

## Backfill proof (last 60 sessions, BACKFILL only, not evidence)
77 events, 21 nights: CO +40bp (0% wh) / +20bp (15% wh), CC +28 / +8; hit 75%; drop/div 0.65.
