# Round 32 (event and structural edges): candidates, listed BEFORE any test

Brief: `prompt_event_edges.md`. Written 2026-10-02, before any return was looked at. Program N at the start: **755**
(round1_prose.md, Round 31 amendment). Models: Round 31's ID3 (insider-buy session, family A) and odd-lot tenders
(family B).

Dead-list check = NEXT.md do-not-redo table + RESULTS.md + `outside_box_ideas.md` (Round 30's 47) +
`deep_search_candidates.md` (Round 29's 23) + `outside_box_explore_log.md` L1-L20 + Study T (offering filings on night
picks) + add. 12 (news on picks).

**Data probes run for this list (EDGAR full-text search, counts only, no prices):** "rounded up to the nearest whole
share" + "reverse stock split" in 8-Ks: 93 (2018) / 127 (2022) / 185 (2025); the same with "participant level" (round
up only at the broker level, which defeats a one-share holder): 0 / 0 / 22. SC TO-I "odd lot" + "exchange offer": 33 /
23 / 15 filings. SC TO-T "net to the seller in cash": 197 / 173 / 76 filings. SC 13E3 "reverse stock split" + "cashed
out": 8 / 3 / 11. 8-K "odd-lot" + "repurchase program": 31 / 50 / 46. 424B3 rights offerings with an over-subscription
privilege: 11 / 4 / 2. 424B3 thrift conversions with a community offering: 4 / 5 / 15.

$/yr columns are **priors** (mechanism size × events/yr at whole-share sizes), not results. Family A judged by the
program bar; family B deal by deal with the selection rule committed before outcomes.

| # | idea | fam | event (point in time) | who pays | small-size advantage / cap | dead-list check | data, cost | events/yr | prior $/yr at $2.3k / $10k / $25k | test? |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **Reverse-split round-up**: buy 1 share before a reverse split whose fractional shares are rounded UP at the holder level; receive 1 post-split share worth ~N× | B | 8-K / DEF 14A / press release with the round-up clause; effective date known days ahead | the issuer (a few hundred $ of extra shares; it chose to avoid cash-in-lieu admin) | **per account, 1 share**: only tiny holders gain; worthless to a fund | Round 30 #12 **KILLED from memory** ("unreliable; grey"), never tested. Reopened: EDGAR now available and the user's priority is exactly fixed-$ per account; "grey" was a broker-practice worry the test can price (a cash-in-lieu outcome loses ~1 share's price) | EDGAR FTS (free) + Alpaca raw/adj daily (free) | ~100-180 filings, maybe ~50-100 usable deals | if half pay ~$5-20: ~$250-1,000 / same / same (per account; fixed $) | **yes (B1)** |
| 2 | **Split-off exchange offers with odd-lot priority**: tender <= 99 parent shares for a ~7-10% premium in subsidiary stock | B | SC TO-I exchange offer (terms, upper limit, odd-lot clause) | the parent (pays the premium to shrink its share count tax-free) | odd lots exempt from proration (final factors often 10-40%) | not tested: the odd-lot report kept **cash** offers only; exchange offers were in the corpus (DD) and dropped | existing tender corpus + FTS; Alpaca | ~1-2 | ~$50-100 / same / same | **yes (B2)** |
| 3 | **Small cash tender offers by acquirers (SC TO-T)**: buy after the offer, tender at the cash price | B | SC TO-T with "$X per share net to the seller in cash" | the acquirer's premium; the arb spread is paid by holders who sell early / funds avoiding deal risk in tiny deals | deals under ~$300M are too small for merger-arb funds; spreads wider | not on any list (merger arb never tested; Round 30 had no deal arb) | FTS + submissions + Alpaca (delisted bars needed for the exit) | ~80-150 | spread ~2-5% per 1-2 months, deal breaks −20-40%: unknown sign at small deals | **yes (B3)** |
| 4 | **Going-private odd-lot cash-outs**: reverse split (1:1000+) that cashes out holders below the ratio at a fixed price | B | SC 13E-3 / DEF 14A with cash-out price | the issuer (buys out small holders to deregister) | only holders **below** the ratio are cashed out: a tiny-holder-only payoff | not on any list | FTS 13E-3 + Alpaca (many are OTC: no Alpaca bars) | ~5-10 | ~$50 / same / same if listed deals price below the cash-out | **yes (B4, deal count first)** |
| 5 | Odd-lot buyback programs (issuer buys holdings < 100 shares, often + a small premium / no commission) | B | 8-K / press release "odd-lot repurchase program" | the issuer (cuts shareholder-servicing costs) | odd lots only | not on any list | FTS 8-K (31-50 hits/yr incl. noise) | ~5-15 real | small: most pay market price, no premium | parked: mostly no premium (read 10 first) |
| 6 | Mini-tenders (offers < 5% below market) | B | press release (not SEC-filed) | — (the offeror profits from holders who mis-tender) | — | — | — | — | negative for a buyer | **no: the payoff runs the wrong way** |
| 7 | Dutch tenders with odd-lot priority, floor below market | B | SC TO-I | — | odd lots | **done**: Round 31, "a coin flip" (64% > 0, mean +0.7%) | — | — | ~0 | no (dead) |
| 8 | CEF NAV tenders | B | SC TO-I | — | — | **dead**: Round 31 (no odd-lot priority) | — | — | — | no |
| 9 | Rights offerings with over-subscription privilege (CEFs, small banks) | B | 424B3, record date | the issuer sells at a discount | over-subscription fills small orders | not on any list | FTS 424B3 (2-11/yr) | ~5 | subscription price ~ market; dilution priced in: ~0 | no (few events; CEF rights trade down to the price) |
| 10 | Thrift mutual-to-stock conversions at $10 (community offering) | B | 424B3 prospectus; first trade date | depositors' undersubscribed shares sold cheap (P/TBV ~60-70%) | per-person caps; manual check by mail | not on any list | FTS 424B3 + Alpaca first-day | ~5-15 | +5-15% first day **only when you get shares**; hot deals fill depositors first (winner's curse) | parked: allocations unknowable from data; manual |
| 11 | SPAC commons below trust near a redemption/extension vote; redeem at trust | B | DEF 14A / 8-K extension vote, trust per share | arbitrage funds who sold below trust | none particular; spreads small | Round 31 L16 **closed** as a cash parking idea (+0.1%/yr); as deal arb: trust − price ~1-3% per few months | FTS + Alpaca | dozens (2021-23), few now | ~$10-30 | no (L16; tiny spreads, ~1% per deal) |
| 12 | CEF liquidation / open-ending announcements: buy after, collect NAV at the date | B | 8-K / N-14 / press release | holders who sell at a residual discount | none | not on any list | FTS + Alpaca | ~5-10 | residual discount ~1-3% with NAV risk | parked (NAV risk dominates; Roth can't hedge) |
| 13 | Preferreds / baby bonds near a call date | B | redemption notice | — | — | — | — | — | priced at call: ~0 | no (no spread to take) |
| 14 | DRIP plans buying at a 1-5% discount (optional cash purchases) | B | plan prospectus | the issuer (raises equity cheaply) | per-holder caps on optional purchases | not on any list | plan docs, no history of fills | ~10 issuers ongoing | ~2-5% on capped amounts, market risk while held | parked (needs direct registration; not testable on data) |
| 15 | Holding-company formations / squeeze-outs with appraisal | B | DEFM14A | — | — | — | — | — | — | no (appraisal is a multi-year lawsuit) |
| 16 | **Schedule 13D initial filings (activists), next session open -> close** | A | SC 13D accepted (quarterly full index; filed by day d) | the activist's information; attention buyers on day d+1 (ID3's mechanism) | none (liquid names) | not tested (13D never on a list; Study T was offerings) | EDGAR full index (free) + panel | ~1,000+ | ID3-like +10-20bp if it exists: +2-6pp | **yes (A1)** |
| 17 | **10%-owner (not officer/director) open-market purchases, next session open -> close** | A | Form 4 code P, reporting owner 10% owner only | the same attention mechanism; owners near control | none | ID filtered on officer/director; 10%-owner-only buys never tested | Form 345 sets (cached) | ~1,000 | +0..+3pp | **yes (A2)** |
| 18 | Insider cluster buys (>= 3 insiders within 5 days) | A | Form 4 | — | — | a subset of ID3/L19 (same events, 20d dead); not new information | cached | ~100 | — | no (subset of ID3, would spend N on the same events) |
| 19 | First purchase in years by a CEO/CFO | A | Form 4 | — | — | subset of ID3 | cached | ~50 | — | no (subset; low power) |
| 20 | Buys after a large drop (overlap with night picks) | A | Form 4 | — | — | **dead**: L19 night-tilt | — | — | — | no |
| 21 | Late-filed Form 4 buys (filing lag) | A | Form 4 | — | — | subset of ID3 | — | — | — | no |
| 22 | Form 144 / its absence; 10b5-1 adoptions | A | 144, 10-Q | insiders selling | — | **dead**: L17 (144); 10b5-1 = sales, long-only can't use | — | — | — | no |
| 23 | Buyback authorisation 8-Ks (Ikenberry drift) | A | 8-K item 8.01 text | under-reaction | none | not tested; multi-day drift legs lag the index here (Lab-BH, BR) | FTS 8-K text (noisy) | ~1,000 | literature decayed post-2000 | no (published decay + multi-day drift record) |
| 24 | Buybacks actually executed (10-Q tables) | A | 10-Q Part II Item 2 | — | none | not tested | heavy parsing | quarterly | — | no (cost; quarterly drift = the dead multi-day family) |
| 25 | **Follow-on offerings priced overnight at a discount: buy the next opening cross, sell the close** | A | 424B4/424B5 priced after the close | the issuer/underwriter's discount; flippers sell at the open | none | Study T = offering filings as a **night-pick filter** (shadow); this is a different trade (the session after pricing) | FTS / full index 424B5 + 8-K pricing (ATM noise) | ~500 | +0..+3pp | parked: ATM supplements are most 424B5s; event identification is the whole problem (next round) |
| 26 | IPO lockup expirations | A | S-1 date + 180d | pre-IPO holders | — | **dead**: Round 30 #7 (−122bp); and the drift is down (long-only) | — | — | — | no |
| 27 | Spin-off orphan selling (buy the spinco after index selling) | A | Form 10 effective / when-issued | index funds | none | **killed** Round 30 #23 (renamed common strategy); multi-day | — | — | — | no |
| 28 | Reverse splits (post-split drift) | A | 8-K | — | — | **dead-ish**: post-split names fall (add. 30/36 raw-price lessons); long-only no. The round-up (#1) is the play | — | — | — | no |
| 29 | Delisting notices (Form 25) / uplistings from OTC (8-A12B) | A | 25 / 8-A | — | — | uplisting **killed** Round 30 #30 (new listings dead add. 36) | — | — | — | no |
| 30 | Small-index additions (S&P 600/400) | A | S&P press release | index funds | — | S&P 500 **dead** add. 34 (move is in the announcement gap); small indexes: no free history | paid | — | — | no |
| 31 | SSR (Rule 201) days | A | — | — | — | **not run** (≈ drop depth) | — | — | — | no |
| 32 | NT 10-K / NT 10-Q | A | NT filing | — | — | **dead** L17 | — | — | — | no |
| 33 | Dividend initiations (Michaely-Thaler-Womack drift) | A | 8-K text | under-reaction | none | not tested | FTS text (noisy) | ~100 | multi-day drift family | no (drift family record; event ID noisy) |
| 34 | Tender-offer completion: post-expiry price of oversubscribed issuer tenders | A | SC TO-I/A final results | prorated sellers dumping the returned shares | none | not tested (Round 31 only scored the tendered part) | existing corpus | ~20 | — | no (few events, multi-day, no mechanism for a long) |
| 35 | Night picks with a filed 13D or 10%-owner buy in the last 30 days | A | as #16/#17 | — | — | L19 tilt family dead (insider tilts) | — | — | — | no |
| 36 | Merger cash/stock election with proration: elect the undersubscribed side | B | S-4 / election deadline | holders who don't elect (default to the unpopular side) | none special | not on any list | S-4 text | ~10-20 | the value gap is usually < 1% by the deadline | no (tiny gap; needs both legs; often a short) |

## To test (6): B1 round-up, B2 exchange offers, B3 small cash tender offers, B4 going-private cash-outs, A1 13D, A2 10%-owner buys

Why these: B1-B4 have a contractual payoff and a cap that keeps size away, which is exactly the odd-lot shape; A1/A2
reuse ID3's tested frame (session open -> close) on events nobody in the program has looked at. Everything else is
dead, a subset of ID3, a multi-day drift (the family that lags the index here), or not testable on data.

Order: build the EDGAR event pipeline (FTS + quarterly full index, cached), commit the family B deal-selection rules
and the family A pre-registration (A1/A2: 2 variants, program N 755 -> 757) **before** any outcome, then run.
