# Discovery loop (prompt_discovery_loop.md), session llm-trader-mid-01, started 2026-10-02

Current N = 760 (round1_prose.md, EV2). Tests: 327 passed. Other sessions share this tree; only my own files are
added. Dead-list check = NEXT do-not-redo table + RESULTS + `outside_box_ideas.md` (47) + `deep_search_candidates.md`
(23) + `event_edge_candidates.md` (36) + `runbook_menu_extra.md` (X1-X10) + `runbook_claims.md` (claims).

Banned this round: any "8-K phrase / form type -> next-session or N-day drift" idea (Round 33 killed 13 of them),
unless the phrase sets a contract payoff or a forced trade with a known date.

Method letters: A contract-payoff, B rulebook mining, C form-type census, D enrichment scan, E own-money (insiders),
F steal from another field.

---

## Ideas (>= 30, written before any outcome on them)

| # | idea | method | forced-trader / contract sentence | source | est/yr | small-size edge | novelty (1-5) | kill | rank |
|---|---|---|---|---|---|---|---|---|---|
| I1 | **DEF 14C approved reverse split** (majority already voted; effective a known ~20-60d later) | A, B | The majority already approved the reverse split; the issuer must effect it by a date. A small holder buys the pre-split shares and swaps via the round-up clause (a known-date contract payoff, not a forecast). | DEF 14C / PRE 14C, N≈99/yr | ~99 | fixed $ per account (1 share) | 4 | not D (B1 tested only the *already-announced* split; this is the *pre-announced* proxy window) | high |
| I2 | **Cash-in-lieu at a premium** in reverse splits (issuer offers above market for fractions) | A | The issuer's proxy/8-K fixes a cash price for fractional shares above market; a holder below the ratio collects it. | 8-K / proxy text | ~10-30 | fixed per account | 4 | not tested (B1 assumed cash-in-lieu ≈ market) | high |
| I3 | **Odd-lot buyback programs** (issuer buys < 100 shares, sometimes +premium) | A | The issuer must buy odd lots to cut servicing costs; a 99-share holder tenders at the program price. | 8-K "odd-lot repurchase" | ~5-15 | odd lots only | 3 | event_edge_candidates #5 parked "mostly no premium" (reads 10 first) | med |
| I4 | **Thrift second-step / MHC conversion** (depositors get subscription priority at $10) | A | The converting mutual must sell shares to depositors first at a fixed $10; a qualifying account subscribes (winner's curse: hot deals fill depositors first). | 424B3 / S-1 "Plan of Conversion" | ~5-15 | per-person caps | 3 | candidate #10 "allocations unknowable from data; manual" | med |
| I5 | **Mutual insurer demutualization** (policyholders get fixed-price shares) | A | Same mechanism as thrifts, different regulator (S-1 / 424B); policyholder priority at a fixed price. | S-1 / 424B3 | ~1-3 | per-person | 3 | not tested | med |
| I6 | **Rights offering with oversubscription privilege priced below market** | A | The issuer sells at a discount; the oversubscription privilege lets small holders buy more than their pro-rata; a small account subscribes + oversubscribes. | 424B3 / S-3 "oversubscription" | ~5 | per-order caps; small accounts favored | 3 | event_edge_candidates #9 "few events; CEF rights trade down" | med |
| I7 | **DRIP / optional cash purchase at a 1-5% discount** (S-3D / 424B3) | A | The plan prospectus fixes a discount (1-5%) on optional cash purchases; a holder enrolls and buys at the discount. | S-3D / 424B3 "discount" | ~10 issuers | per-holder caps | 3 | #14 "needs direct registration; not testable on data" | low |
| I8 | **Liquidation / dissolution distribution above market** (trading below estimated distribution) | A | The plan of dissolution fixes a distribution; the stock trades below it; a holder buys and collects. | 8-K "plan of dissolution", DEF 14A | ~5-10 | none | 3 | candidate #12 "residual discount 1-3% with NAV risk" | low |
| I9 | **CEF conversion-to-open-end / full NAV tender** (discount closes) | A | The board approves open-ending or a NAV tender for all holders; the discount closes to NAV. | 8-K / N-14 / press | ~5 | none | 3 | #12 "NAV risk dominates; Roth can't hedge" | low |
| I10 | **Short-form squeeze-out after a 90% tender at a fixed price** | A, B | After a tender crosses 90%, the acquirer must squeeze out the rest at the fixed offer price within a statutory window. | SC TO-T + 8-K | ~5-10 | none | 3 | B3 tested the spread *before* completion; this is the post-90% fixed payoff | med |
| I11 | **Merger cash/stock election: elect the undersubscribed side** (proration avoided for small holders) | A | In a cash/stock election the oversubscribed side is prorated; reading the election clause finds whether small holders are exempt. | S-4 / election docs | ~10-20 | small holders may be exempt | 3 | #36 "value gap < 1%; often a short" | low |
| I12 | **CVR deals pricing a known milestone** | A | The S-4 fixes a CVR payoff on a dated milestone; the market prices it at 0; a holder gets the option free. | S-4 / 425 | ~5 | none | 3 | not tested | low |
| I13 | **Rule 10b-18 buyback timing** (issuer may not buy in the last 30 min / at the open) | B, A | The issuer's own buyback is barred in the last 30 minutes and the opening 30 min; a small account buys in those windows where the price-insensitive buyer is absent. | Rulebook | daily | none | 2 | news events dead; but this is a *rule*, not an 8-K phrase | low |
| I14 | **Reg SHO threshold-security list** (forced short covering at settlement) | B | A name on the threshold list for 13+ days triggers a close-out requirement at T+13; a small account buys into the mandated short cover. | FINRA/Nasdaq threshold list | ~50-100 | none | 3 | SSR flag "not run: ~ drop depth"; threshold close-out is different | med |
| I15 | **Nasdaq/NYSE bid-price deficiency cure window** (forced cures, reverse splits, delistings) | B, C | A sub-$1 bid triggers a 180-day cure; the issuer often announces a reverse split; the round-up clause then pays (I1 link). | Listing rules + press | ~100-200 | fixed per account | 3 | overlaps 25-NSE (dead); the cure *before* delisting is different | med |
| I16 | **40-Act diversification test at quarter-end** (funds must trim concentrated positions) | B | At each fiscal quarter-end a registered fund must meet the 25/5 diversification test; it must trim an oversized winner. | Rulebook (40-Act) | ~quarterly | none | 3 | not tested; multi-day and market-level | low |
| I17 | **ETF 6c-11 custom-basket / creation halt** (premium dislocations) | B, A | During a creation halt (a country, a halted holding) the ETF trades at a premium and can only price on the next day's NAV; the AP's arbitrage is blocked. | 8-K / ETF notices | ~10-20 | none | 2 | add. 27 R4 "ETF pairs dead"; creation-halt premium untested | low |
| I18 | **SC 14F1 distribution-of-shareholder-collateral** | C | A broker-dealer distributes cash/securities to shareholders (a forced distribution with a date). | SC 14F1 | ~20/yr | none | 3 | not tested | low |
| I19 | **N-23C3A / N-23C-2** (a fund's announced repurchase of its own shares) | C, A | The fund must repurchase a stated % of shares at NAV on a stated date; a holder can buy below NAV and redeem. | N-23C3A | ~100/yr | none | 3 | CEF NAV tender family (odd-lot dead); *whole-fund* repurchase is different | low |
| I20 | **1-U (Reg A crowdfunding) offering close-outs** | C | A Reg A issuer completes a round; the shares are illiquid. | 1-U | ~400 | none | 1 | not tradable (OTC, no bars) | kill |
| I21 | **425 merger-communication spin-off terms** | C, A | The 425 states the exchange ratio and dates. | 425 | ~1,400 | none | 2 | B2/B3 families | kill |
| I22 | **15-12B/15-12G deregistration** (issuer leaves SEC reporting) | C | The issuer deregisters; holders can't use Rule 144; forced selling into OTC. | 15-12G | ~120 | none | 3 | 25-NSE adjacent; OTC no bars | low |
| I23 | **8-K12B shell/successor registration** | C | A successor issuer registers after a merger. | 8-K12B | ~50-100 | none | 2 | multi-day mechanics | low |
| I24 | **CORRESP comment-letter release** (SEC correspondence made public) | C, D | A comment letter is released weeks later; it reveals an unresolved accounting issue. | CORRESP | ~2,000 | none | 3 | banned (next-session drift, news); the *release lag* is a fixed date but the content is news | med-low |
| I25 | **Short interest spike + a forced buyback** (FINRA bi-monthly, lagged) | D | Crowded shorts into a name with an announced buyback must cover into an inelastic buyer. | FINRA + 8-K | ~100 | none | 3 | DS4 did days-to-cover tilt (dead); the *interaction* with a buyback is untested | med |
| I26 | **Insider option exercise and HOLD** (Form 4 M with no same-day S) | E | An insider exercises and keeps the shares, paying tax out of pocket — a costlier signal than a buy. | Form 4 | ~1,000 | none | 3 | not tested (ID3 = code P only) | med |
| I27 | **Director buying at a SECOND company they serve** | E | A director buys at company B while serving A; the market treats it as unrelated. | Form 4 | ~200 | none | 3 | subset? not ID3's issuer-level signal | med |
| I28 | **CEO buying in the first 90 days of tenure** | E | A new CEO's early purchase is a commitment signal. | Form 4 + bio | ~80 | none | 3 | subset of ID3? CEO-only + tenure is new | med |
| I29 | **Fund managers buying their own CEF** (Form 4 on a closed-end fund) | E | A CEF's own managers buy the fund's shares, often at a discount to NAV. | Form 4 on CEFs | ~100 | none | 4 | not tested | med |
| I30 | **Insider buys in the issuer's OWN rights offering** (code P during a rights offer) | E, A | Combined own-money + fixed-price subscription. | Form 4 + 424B3 | ~50 | odd lots | 3 | not tested | med |
| I31 | **Appraisal / dissenters' rights merger** | F, B | A merger with appraisal rights pays fair value in court; a holder dissents for a potential premium (multi-year, illiquid). | DEFM14A | ~50 | none | 2 | #15 "multi-year lawsuit" | kill |
| I32 | **Index reconstitution forced trades** (S&P 600/400, Russell) | B, C | Index funds must buy adds / sell deletes at the recon close. | Index methodology | ~2x/yr | none | 3 | S&P 500 dead (add. 34), small indexes no free history | kill |
| I33 | **Insider 10b5-1 plan adoption disclosure** (new 2023 rules) | E | A new 10b5-1 plan is disclosed; the direction (buy/sell) is public. | 10-Q/10-K | ~500 | none | 2 | long-only can't use a sell plan; buy plans rare | kill |
| I34 | **Reverse-split ex-date + round-up sweep** (systematic, not one-off) | A | Same as I1 but the live watch: every Alpaca-announced reverse split with a holder-level round-up. | Alpaca + EDGAR | ~75 | fixed per account | 1 | already built (roundup_watch, B1) | done |
| I35 | **Dividend capture in the Roth before ex-date** (qualified-dividend 61-day holding) | B | Holders must hold 61 days around ex to get the qualified rate; a small account times the capture. | dividends.json | ~monthly | none | 2 | AZ ex-div Roth DEAD | kill |
| I36 | **Wash-sale-aware loss harvesting + planned rebuy** (rule-driven, day 31) | B | The 30-day rule forces the rebuy date; a small taxable account schedules it. | Rulebook | ~monthly | none | 2 | Round 30 #4 wash-sale day-31 DEAD | kill |
| I37 | **Odd-lot priority in *debt-for-equity* exchange offers** | A | Same odd-lot clause as split-offs, but the consideration is new debt/equity of the same issuer. | SC TO-I | ~2-5 | odd lots | 4 | B2 covered split-offs (another company); same-issuer debt-for-equity untested | med |
| I38 | **Preferred/debt exchange with a make-whole** (fixed payoff) | A | The indenture fixes a make-whole premium on a mandatory exchange. | 8-K / indentures | ~10 | none | 3 | not tested | low |
| I39 | **Rights offering for *listed* small banks** (fixed price below market) | A | Small banks raise at a discount; oversubscription favors small holders. | 424B3 | ~20 | per-order caps | 3 | #9 "few events"; banks are listed (unlike CEFs) | med |
| I40 | **Post-bankruptcy emergence equity distribution** | A, C | The plan fixes a distribution date and a share count. | 8-K / S-4 | ~30 | none | 3 | not tested; OTC-heavy | low |

Kills (no data / banned / done): I20, I21, I31, I32, I33, I34, I35, I36 (8). Everything else is scored.

## Ranking after kill-fast (rank from the table column)

The scoring: expected %/yr at $2.3k-25k x P(real) x novelty / manual hours. Top singles and small clusters:

1. **Reverse-split round-up family, extended to the *pre-announced* window (I1, I2, I15)**. The one paying
   contractual shape (B1 PASS); this looks *before* the split is effective, at the approved-but-not-yet-effective
   proxy/8-K window. Fixed $ per account. HIGH.
2. **I29 Fund managers buying their own CEF + I37 odd-lot debt-for-equity + I14 threshold-list close-out** (the
   other three contractual/forced candidates with a dated payoff and a small-size clause). MED.
3. **I26 insider exercise-and-hold, I28 CEO-first-90-days, I30 buys in a rights offer** (own-money, new signals). MED.
4. **I4/I39 thrift + bank rights offerings** (fixed-price subscription priority). MED, manual.
5. Everything else LOW or kill.

Work order: I1/I2/I15 first (contractual, highest prior), then I29, then I26/I28/I30, then I37, then I14, then I4/I39.
