# Branch S: new-issue concession in $1,000-par corporate bonds via Schwab (2026-10-18)

Verdict: CEILING-KILL (descriptive probe only; no N, no judged backtest, nothing appended to round1_prose.md). Net edge per round trip ~5-15bp median with an IQR straddling zero, ceiling ~0.5-1pp/yr at $10k vs the +8pp gate.

## 1. Evidence (search-result snippets only; the pages/papers were NOT opened, treat as UNVERIFIED in detail)
- Schwab pricing (schwab.com/fixed-income/pricing, April 2026 Pricing Guide per search snippet): new-issue bonds $0 commission, footnote "a selling concession is included in the offering price" (so the retail price is the public offering price, the underwriter's concession is inside it; no extra markup). Secondary corporates: $1/bond ($10 min, $250 max) online, plus principal markup/bid-ask. Schwab glossary snippet: "retail notes" (issuer-direct, par, $1,000 increments) are a different product from institutional-style underwritten deals. UNVERIFIED: minimum size, allocation rules, which underwritten (non-144A) IG deals Schwab actually offers, Roth eligibility (bonds are IRA-eligible in general; not confirmed for new issues).
- Underpricing: Nikolova et al. (JFE 2020, IG 2002-14) avg 32bp; Manconi et al. (ECGI WP 548/2018) mean 0.13%, median 0.08% of price over 5,396 bonds; Bocconi WP "Structural Changes in Corporate Bond Underpricing" 10-day underpricing ~23bp pre-crisis, ~64-72bp crisis/post-crisis. JFE 2022 "Overallocation and secondary market outcomes": syndicate short covered (>=70% within 2 days), i.e. price support is short-lived; underwriter stabilisation is the early price path. Underpricing is concentrated in institutional allocations (insurers).
- Literature magnitudes (price, 13-70bp) are before any retail exit cost.

## 2. Probe (descriptive; touched period 2015-2019 only; nothing judged)
Code: research/sim/branch_s_probe/{pull,trace,ana}.py; outputs out/summary.csv. FISD fisd_mergedissue: fixed coupon, non-convertible, non-MTN, non-144A, USD, principal 1000, offering_amt>=$300M, offering price 98-101.5 -> 4,604 issues; random 500 (seed 7); IG 461 / HY 35 / 4 unrated (IG = any S&P/Moody rating in the IG set; HY n is small). TRACE enhanced_clean, days 0..+10 business days after offering, wis_fl != Y, customer trades (cntra_mp_id='C'). Clean prices vs offering price, bp of par (clean, no accrued; ignores ~1.4bp/day coupon carry and market moves; not market-adjusted). Per-issue median then cross-issue median.
IG, bp vs offering price (median [p25,p75]):
- institutional (>=$1MM par): d0 +10, d1 +20 [3,42], d3 +26, d5 +23 [-16,83], d10 +40 [-23,126].
- retail-size (<=$100k) dealer-sell prices (what a post-issue buyer pays): d0 exactly 0 (these are the offering-price allocations), d1 +43, d3 +52, d5 +63.
- retail-size customer prices on the other side (what a seller realizes; side-code mapping B/S unconfirmed, medians of the two codes differ only 22.8 vs 21.1, so treat as indicative, n 26-85 issues): d1 +16 [-1,53], d3 +29, d5 +16 [-45,70], d10 +20.
- paired per issue, institutional minus retail-bid gap: ~9-10bp (IG, d1-d10), 8-19bp (HY, tiny n).
HY (n 6-22 issues/cell): institutional +38..+88bp, retail bid +31..+152, huge dispersion; far too small a sample to use, and few HY deals are retail-offered.
Reading: the concession is real (+20-25bp median institutional by day 1-5, matching the literature) but a retail seller captures roughly half, with dispersion bigger than the median (IQR -45..+70 at d5); the day-1 jump to +43 on retail-size buys shows the dealer markup that a secondary buyer pays, which is why the only way in is the offering price.

## 3. Ceiling (gate)
Per round trip at $10k: sell at dealer bid ~+16..29bp (day 1-3, IG median) minus Schwab $1/bond secondary fee ($10 per 10 bonds = 10bp) = ~+5..+20bp, IQR -50..+60, mark-to-market and rate risk over 1-5 days dwarf it (10y IG: 1bp yield = ~8 price bp). Frequency Schwab could allocate: UNVERIFIED; say 20-40 usable underwritten IG deals/yr, one position at a time (5-day lock): 30 x ~12bp = ~3.6pp gross on a fully deployed account, x 50% capture = ~1.8pp, but the median-after-fee is the lower end so ~0.5-1pp. $2.3k: smaller than 1 bond lots in some deals ($1,000 steps work, but fee floor $10 = 43bp, edge ~gone). $25k: same pp, bounded by allocation. Below +8pp at every size.
Hold variant: the concession is a one-time ~5-25bp price (about 3-6bp of yield on a 5y); the carry vs BIL is the IG credit spread (credit risk, not the concession). Not an edge over T-bills after risk.

## 4. Pre-registration DRAFT (do not run unless Schwab access is verified AND a user wants to test)
Untouched period 2020-2025 (the probe touched 2015-19 descriptively). Rule: every registered, non-144A, fixed USD IG deal >=$500M with offering price 99-101, buy 10 bonds at offering, sell at TRACE-implied dealer bid on day 3 (retail-size customer buys-from-dealer side confirmed first). Gate: median net of $1/bond fee >= +15bp, day-clustered t >= 2, ex-top-5 positive, rate-hedged (vs duration-matched Treasury ETF) excess > 0. Kill: median < +10bp or hedged excess <= 0. Expected: dies (probe hedged excess not computed, unadjusted median is only +5..20 net).

## Dropped
- HY new issues: n too small, wide dispersion, rarely retail-available. - Hold-to-maturity concession carry: ~one-time 5-25bp. - Retail issuer-direct notes at par: concession is inside the price, no edge. - $25-par new issues: already rejected (round1_prose.md ~4979).
