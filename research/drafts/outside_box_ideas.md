# Round 30 (outside the box): raw ideas, before any test

Brief: `prompt_outside_box.md`. Written 2026-10-02, **before any number was looked at**. Every idea starts from a
forced or constrained trader. Methods: (1) invert a constraint, (2) steal from another field, (3) small-size
advantage, (4) the bot's own logs, (5) second-order effects of the bot's legs, (6) weird data. Plus (7), the
brief's forced-trader source list read directly ("mine": rebalancers / rule-bound / plumbing / attention / broken arb).

Data: **C** = cached in `data/research/night/` (SIP daily panel 2020-10..2026-09, 13,933 symbols with open/close/
volume/vwap/trade_count; raw prices for the 4,230 night-pool names; `dividends.json` with payable dates; EDGAR
submissions for 1,992 issuers incl. SIC; ETF daily; auction prints), **F** = free to fetch, **P** = paid,
**E** = EDGAR (blocked: no `NOTIFY_EMAIL`/`SEC_USER_AGENT` in this Mac's `.env`).

Novelty 1-5 (5 = nothing found after a real search). "searched:" names the search actually run today (WebSearch);
"memory" means scored from what I know of the literature, without a search today.

Kill checks: **D** = on the dead list (NEXT do-not-redo / RESULTS), **R** = a renamed common strategy (banned list),
**W** = does not fit whole shares at $2-25k, or pays only at size, **X** = untestable on free data inside this round.

| # | idea | forced-trader sentence | method | data | novelty | kill check | verdict |
|---|---|---|---|---|---|---|---|
| 1 | **Share-class twins at the close** (FOX/FOXA, NWS/NWSA, BF.A/B, UA/UAA, Z/ZG, FWONA/K, BATRA/K, HEI/HEI.A, LEN/LEN.B, PBR/PBR.A, GEF/GEF.B, RUSHA/B, MOG.A/B, LILA/K, MKC/MKC.V, BRK, GOOG/L) | Index funds and retail market-on-close orders must trade the *indexed / familiar* class at the close whatever its price vs. the twin, and a small account can buy the twin that closed cheap vs. its own 60-day ratio in the auction and sell it at the next auction. | 7 (broken arb), 3 | C | 2 (searched: "dual-class ratio mean reversion": Schultz-Shive 2010; Vortex 2026 says gross ≈ NBBO round trip, but via auctions there is no NBBO crossing) | not D; not R (no price pattern, a fixed anchor); fits whole shares except BRK.A | **KEEP** |
| 2 | **Same-index ETF clones at the close** (GLD/IAU/GLDM/SGOL/BAR/AAAU/OUNZ; SPY/IVV/VOO/SPLG; QQQ/QQQM; TLT/SPTL/VGLT; BIL/SGOV/SHV/TBIL/XBIL; IWM/VTWO; SLV/SIVR) | Retail sellers in a thin clone must take whatever its close prints, and the AP only arbitrages outside a band, so a small account buys the clone that closed below its liquid twin and sells at the next cross. | 7, 3 | C | 3 (searched: "ETF premium discount same index thin"; Hilliard 2014 OU premiums, warnings that thin closes are stale) | not D (add. 27 R4 "ETF pairs" were sector pairs, not the same holdings); not R | **KEEP** |
| 3 | **Leveraged ETF vs. L × underlying at the close** (thin 2x/3x sector LETFs vs. their underlying ETF) | LETF holders send market orders into a thin LETF's close while the underlying closes efficiently; the LETF's residual vs. L × the underlying is not NAV, so a small account buys the LETF that closed below L × underlying. | 7, 3 | C | 3 (memory: LETF tracking papers study NAV vs. index, not close-print residuals) | Study W tested LETF *picks*, not this; not R | **KEEP** (merge with 1-2 as one family) |
| 4 | **Wash-sale day-31 rebuy** after crash days | Taxable holders who sold a crashed name for the loss **cannot** buy it back for 30 calendar days; robo-harvesters schedule the rebuy for day 31; a small account buys the crashed names the session before day 31 and sells into the rebuy. | 7 (plumbing), 1 | C | 4 (searched: "wash sale day 31 price pressure": rule guides and harvesting patents only, no return study) | not D (DS5 = Dec seasonality, different); not R | **KEEP** |
| 5 | **Retail-trade-size tilt on night picks** (volume / trade_count) | Zero-commission app users queue market buys overnight on the day's big losers, executed at the 09:30 cross; names with small average trades (retail-heavy) get a richer open, which the night leg sells into. | 4, 7 (attention) | C (trade_count) | 4 (memory: Boehmer et al. retail-flow uses sub-penny prints, not the open cross) | not D (rel-volume tilt is volume, not trade size); not R | **KEEP** |
| 6 | **The $5 cliff** | Many mandates and brokers' margin rules (100% initial margin below $5; Schwab $3) force sales when a stock closes under $5; a small cash account has no such rule and buys names that just crossed below $5. | 1, 7 (rule-bound) | C (raw prices, night-pool names) | 3 (searched: "$5 threshold margin": folklore and broker rules, no study found) | night-pool $5 floor is the bot's own filter, not this; not R | **KEEP** |
| 7 | **Lockup-expiry losers** in the night pool | Pre-IPO holders sell the day their lockup ends (~180 days) for liquidity, not information; a −8% drop on that day should bounce more than a news drop, so tilt toward night picks within ±3 sessions of IPO+180. | 7, 5 | C (first trade date in panel) | 3 (memory: Field-Hanka on the lockup drop; the night-bounce conditioning is not in it) | add. 36 tested "new listings" (age), not lockup days; not R | **KEEP** (explore n first) |
| 8 | **Supply-shock vs. news-shock losers** (general: lockup, S-3 resale effective, Form 144) | Holders with a registered resale or a lockup end dump into the close regardless of news; a supply-driven drop reverts, a news drop does not. | 2 (inventory), 7 | E | 4 | overlaps Study T (offering filings, shadow) | **park** (E; T covers the offering part) |
| 9 | **Sympathy losers** (peers of a crashed name, not the crashed name) | Sector funds and risk systems sell the whole SIC cluster when one member crashes on news; the peers' drop carries no news and should revert overnight; a small account buys the peers. | 2 (epidemiology: contagion, not the index case) | C (SIC for 1,992 issuers; or return clusters) | 4 (memory: "sympathy plays" are trader lore; Cohen-Frazzini links are slow, not overnight) | not D (idio-move tilt was the pick's own move); not R | **KEEP** |
| 10 | **Listing exchange of the night pick** (NYSE / Nasdaq / Arca / Cboe close auctions) | MOC sellers are forced into whichever auction the listing exchange runs; NYSE's D-orders/floor and Nasdaq's cross set different closing dislocations in thin names. | 7 (plumbing), 4 | C (asset_meta exchange) | 4 (memory: auction-design papers compare venues, not overnight reversal) | not D; not R | **KEEP** (cheap tilt) |
| 11 | **Odd-lot tender offers** (holders of < 100 shares are exempt from proration) | In an issuer tender at a premium, large holders are prorated and must keep part at the post-tender price; an odd-lot holder is filled in full. A $2-25k account buys 99 shares below the tender price and tenders. | 3, 1 | E (SC TO-I / TO-T) | 2 (memory: known to odd-lot arb blogs; a pure small-size edge) | W: only works small, which suits us; X: needs E | **park: ask user** (EDGAR UA; operational, not a statistical test) |
| 12 | **Reverse-split round-up** | When an issuer rounds fractional post-split shares UP, a 1-share holder gets one post-split share worth N× the price; only tiny accounts can collect it, per account. | 3 | E (proxy/8-K terms) | 2 (memory: well known on retail forums; issuers and brokers now often cash out instead) | W: dollars fixed per event; ethical/broker grey zone (DTC-level cash-in-lieu) | **KILL** (unreliable; grey) |
| 13 | **SPAC commons below trust as the BIL replacement** | SPAC IPO arbitrage funds dump commons after the unit split and hold warrants; the commons trade below the trust, which earns T-bill rates and is redeemable. A small account holds them instead of BIL. | 3, 7 | C prices + E (trust/deal dates) | 2 (memory: well-known SPAC arb) | W ok; X: trust values and vote dates need E; few SPACs 2023-24 | **park** (E) |
| 14 | **Treasury auction cycle in IEF/TLT** for idle cash | Primary dealers must absorb new supply at each auction and lay it off over days; prices dip before and recover after. A small account holds IEF over the post-auction days instead of BIL. | 7, 6 | C (IEF/TLT) + F (fiscaldata auction dates) | 2 (memory: Lou-Yan-Zhang 2013) | not D; not seasonality (a supply calendar), but published | **KEEP (low prior)** |
| 15 | **Dividend payment-day pressure** as an idle-cash index tilt | Funds and DRIPs must reinvest dividend cash after payment; on heavy payment days the index is bid. | 7, 6 | C (payable dates) but no shares outstanding | 2 (searched: Hartzmark-Solomon 2022, +3-6bp on top days, not in Q4) | add. 16: idle cash in SPY dead; this is conditional, but direction-of-market, which the legs don't earn | **KILL** (published; aggregate payouts need shares outstanding; a market-direction bet) |
| 16 | **Long-term-gain anniversary** (IPO+1y for appreciated IPOs) | Taxable IPO buyers sitting on gains wait for day 366 to sell; supply arrives after the anniversary. | 7 (tax) | C | 3 (searched: Reese 1998 volume yes, price weak) | not D; small n 2021-23 (few IPOs were up a year later) | **KILL** (power: little n in the select window) |
| 17 | Single-stock LETF underlyings in the night pool | Issuers must sell L(L−1)× of the move into the close. | 7 | P (AUM history) | 2 | max_edge #7 dropped (Ivanov-Lenkey: insignificant) | **KILL** (D) |
| 18 | Covered-call / YieldMax roll dates | Option-income ETFs must roll on fixed dates. | 7 | P (roll calendars, OI) | 3 | options calendar sizing dead (add. 35) | **KILL** (D-adjacent, X) |
| 19 | Buffer-ETF monthly resets | Innovator funds reset SPY option collars on fixed days. | 7 | P | 3 | effect is SPY-option level; the legs don't trade options | **KILL** (X) |
| 20 | Small-index reconstitution (sector / equal-weight / dividend) | Index funds must buy adds at the recon close. | 7 | P (membership) | 2 | S&P adds dead (add. 34), Russell untestable | **KILL** (D, X) |
| 21 | ETF closure / liquidation discounts | Holders panic-sell a closing ETF below NAV; the liquidation pays NAV. | 3 | F (closure lists) + NAV (P) | 4 | ~20 thin events/yr; no NAV history | **KILL** (X) |
| 22 | Dividend-cut forced selling by income funds | Dividend ETFs drop cutters at recon. | 7 | C (dividends.json) | 2 | published drift is negative (Michaely 1995): long side loses | **KILL** |
| 23 | Spin-off orphan selling | Index funds must sell spun-off shares that are not index members. | 7 | E (Form 10) | 1 (Greenblatt) | R: well-known event strategy | **KILL** (R) |
| 24 | Margin-call morning after a market crash | Brokers liquidate margin accounts at the next open after a broad down day; the open is depressed and recovers by 10:30. | 7, 5 | C (minutes) | 3 | "night exit later than the open" is dead overall (add. 7); an IBS-at-open variant is BE (dead) | **KILL** (D-adjacent) |
| 25 | Buyback blackout windows | Issuers can't buy in the weeks before earnings. | 7 | E | 3 | earnings-calendar ideas dead (DS1); market-level | **KILL** |
| 26 | SSR day-2 tilt | Shorts can't hit bids on day 2. | 7 | C | 2 | NEXT: "SSR flag not run: ≈ drop depth" | **KILL** (D) |
| 27 | LULD reopen trades | — | 7 | C | — | Lab-AY/BA dead | **KILL** (D) |
| 28 | Option pinning on night picks | — | 7 | — | — | add. 35 dead | **KILL** (D) |
| 29 | Ticker-change inattention | Quant funds with stale symbol maps drop the name; retail search fails. | 7 (attention) | F (exchange notices, not cached) | 4 | rare; no symbol-change history cached | **KILL** (X) |
| 30 | OTC → exchange uplisting | Newly marginable/indexable names get first-day buyers. | 7 | F | 3 | new listings dead (add. 36); usually comes with an offering | **KILL** (D-adjacent) |
| 31 | Name-confusion trades (ZOOM vs ZM) | Inattentive retail buys the wrong ticker on famous news. | 7 | C | 4 | too rare to test or trade | **KILL** (power) |
| 32 | Odd-lot price improvement on high-priced picks | Odd-lot quotes inside the NBBO aren't shown to round-lot users; a small order can take them. | 3, 4 | live fills only | 4 | engineering, forward-only (the 2025 round-lot reform narrows it) | **KILL as research; note for execution** |
| 33 | Thin-ETF bid-ask bounce (new ETFs) | — | — | C | — | add. 36 dead | **KILL** (D) |
| 34 | Closed-end fund discount shocks vs. a matched ETF | CEF holders (retail, income funds) sell into the close without NAV arbitrage (no creations); the discount move reverts. | 7, 3 | C prices; NAV P | 3 | no NAV; an ETF proxy is a reversal on a basis, close to #2-3 | **park** (fold into the twin family if the family lives) |
| 35 | ADR vs. home share | — | 7 | P | 1 | — | **KILL** (X) |
| 36 | Treasury/BIL ETF ex-dividend mechanics | T-bill ETFs drop at monthly ex-dates. | 7 | C | 2 | ~0 after the drop ratio (AZ logic) | **KILL** |
| 37 | Robinhood-style "top losers" list membership | — | 7 | — | — | it *is* the night pool | **KILL** (dup) |
| 38 | Sports-betting closing-line value: 15:50 → close move of the pick | — | 2 | C | — | late-selling tilt dead (add. 23) | **KILL** (D) |
| 39 | Predator-prey crowding (trailing night-pool returns) | — | 2 | C | — | AU1/AU2 dead | **KILL** (D) |
| 40 | Market-maker inventory premium ∝ abnormal volume | — | 2 | C | — | rel-volume tilt dead | **KILL** (D) |
| 41 | Whole-share rejects at $2.3k: substitute the next pick | The bot itself is forced to drop high-priced picks at small size. | 4 | live logs | 2 | engineering; the sim already rounds whole shares | **KILL as research; check in code** |
| 42 | Second-day night after a strong open bounce | — | 5 | C | — | 2/3/5-day losers dead (add. 27 R2) | **KILL** (D) |
| 43 | IBS breadth (many sector ETFs firing) as a next-week signal | — | 5 | C | — | a regime gate (banned) | **KILL** (R) |
| 44 | NT 10-K / NT 10-Q late filers among night picks | Late filers lose S-3 eligibility and index/fund eligibility; holders must sell; the night-pick drop on an NT day is then followed by more. Drop them. | 6 | E | 4 | drop-filter like Study T | **park** (E) |
| 45 | Form 144 intent-to-sell (2023+ electronic) on night picks | An insider's notice means registered selling over the next 90 days. | 6 | E | 4 | only 2023+ (no select window for night 2021-23 except 2023) | **KILL** (power + E) |
| 46 | 23/5 overnight-session prices (from 2026-12) as the night leg's early read | Overnight-venue retail trades news before the open cross. | 1 | forward only | 4 | forward-only | **forward note** |
| 47 | PDT-rule removal changing retail intraday flow | Former sub-$25k accounts can now round-trip; less forced overnight holding. | 1 | forward only | 4 | forward-only | **forward note** |

## Survivors (kill-fast done): 10 to explore on 2021-23 only (2020-10..2023-12 for panel ideas)

1. #1-3 **anchored twins at the close** (share classes, clones, LETF vs. L×underlying): one family.
2. #4 wash-sale day-31 rebuy.
3. #5 retail trade size on night picks.
4. #6 the $5 cliff.
5. #7 lockup-expiry night picks.
6. #9 sympathy losers.
7. #10 listing exchange of night picks.
8. #14 Treasury auction cycle (low prior, published).
Parked for EDGAR (needs the user's UA): #8, #11, #13, #44.

Exploration rule: select data only (panel ≤ 2023-12-31; night pool 2021-23). Every look is logged in
`outside_box_explore_log.md`. 2024-26 is not read until the pre-registration is committed.
