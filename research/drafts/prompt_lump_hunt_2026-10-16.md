# LUMP-HUNT deep-research prompt (for an external research agent, or me) — 2026-10-16

You are a research agent. Your job is to find **contractual, structural, rare-event money opportunities — "lump-shaped" trades** — that a small US retail account can collect. Not price signals: **events where money is paid or transferred by rule, contract, regulation, tax law, or forced action, and where a small account captures most or all of the payout that a big account cannot.**

Depth over breadth: for every idea, read the actual document (prospectus, rule filing, EDGAR exhibit, tax code section, court opinion, plan of reorganization) and quote the clause that creates the money. If you cannot quote the clause, the idea is unserious.

---

## 1. Who this is for (constraints decide what counts)

- **Accounts:** a US taxable margin account (~$2.3k today, funding up toward $25-75k over months) and a Roth IRA (+$7.5k/yr in new money; NO shorting in the Roth, no intraday margin there). Broker: Schwab (stocks, ETFs, ETNs, preferreds, baby bonds, closed-end funds, listed options, spot BTC/ETH) + Alpaca API. US-listed only; no futures yet; no non-US exchanges; no OTC grey market.
- **Orders matter:** the account can buy/sell at the 09:30 opening auction and 16:00 closing auction at ~0bp measured cost; regular-session fills cost 3-10bp (large caps) or 12-80bp ($10-50M ADV names). Count this in every idea's cost.
- **The bar for a candidate (the "lump bar"):** a strategy that a $2-25k account can collect **$1,000+ per event (or $1,500+/quarter once its calendar is understood), recurring 1-4x/year**, with honest capture (assume you keep at most half of the published effect). The event must have a **per-holder cap, eligibility limit, or round-lot/odd-lot structure that a small account can fully fill** — that cap is why the payout survives at all. If the idea only pays at $100k+ of size, it is not a candidate; note it and move on.
- **Account fit:** anything requiring shorting must be flagged as taxable-only; anything requiring the Roth to hold a debt instrument across an ex-date must be flagged as Roth-friendly (dividend untaxed there); anything requiring a tax loss or a wash sale must be flagged.
- **Rules are date-versioned.** FINRA's PDT rule was replaced 2026-06-04 (Schwab stopped counting day trades 2026-06-08; real-time intraday margin BP from 2026-07-13 for margin accounts ≥$2,000). Nasdaq/NYSE Arca 23/5 overnight trading starts 2026-12-06. T+1 settlement since 2024-05-28. Cite the date of every rule you rely on; a pre-2024 settlement-timing claim without a post-2024 datapoint is probably stale.

## 2. What we already have (do NOT re-propose these as the *headline*; enhancements are fine)

**ALIVE (these are deployed or in forward test — cite only to support a related new idea):**
- Preferred/baby-bond ex-dividend capture (+38-44bp/event, 22/22 yrs; ROTH-STACK sized)
- CEF discount reversion (+125bp/trade vs peers, gated forward)
- Treasury month-end duration extension (+32bp/month, validated 2002-2015)
- Overnight loser bounce / IBS reversal / overnight momentum (book legs, sized)
- SSR-LIFT: Rule 201 short on lift-day T+2 open→close (+42.5bp/event post-T+1 era, hedged, taxable only)
- insider Form 4 buys (conditional, crisis-heavy)
- G45: activist 13D on CEFs (+2-3.6%/60d, too small at this stage)
- forced-flow EDGAR discovery (SC 14D-9 / DEFM14C / 425 / 8-K 2.01-5.01 / 25-NSE / S-4 / SC 13E3 scanned nightly, log-only)

**DEAD or retired in this program — re-propose ONLY with genuinely new evidence that contradicts the death, and say what the new evidence is:**
- Odd-lot tenders (14/15 wins, +5.5% median) — RETIRED only because proceeds lock capital for weeks and the election is manual; if you find a way to make the elective *execution* cheap or a class of tenders that pay faster/properly, SAY so and re-propose explicitly.
- Merger arb (spread ≈ T-bill), deal-break events, S&P add/delete and spin-offs (the move is in the untradeable gap), SPAC liquidations/reDEMPTIONs, IPOs, lockups, secondaries, ATM programs, buybacks/ASR, 13D (except small CEF), 10b5-1, Form 144, Reg SHO threshold forced buy-ins (the LONG side loses: -10.1pp), rights offerings (small/manual — re-propose if you find a rights class with >$1k/deal economics), reverse-split round-ups (~$370/yr, needs Schwab round-up behavior verified), warrant exercises (OTC), box-spread financing (needs $125k+), sets of options premium trades, crypto TA/pattern anything, LETF flow/CTA proxies (all dead in backtests), PEAD/earnings calendars, survivorship-biased calendar effects (turn-of-month, January, window dressing), dividend-month premium, 13F crowding states, borrow-fee long-only tilts (the borrow-fee D1 tilt pays on the SHORT side only), Section 871(m)/ESMA regulatory changes that only affect institutions.
- Data we already mined and exhausted at free tier: Wikipedia pageviews, TanFinBERT/NLP on filings and news, Reddit, IBES, OptionMetrics IV/skew, short interest, TRACE bond→stock lead, FINRA ATS venue-mix, FINRA margin debt, ETF creation/redemption (SPY + bond SPDRs, the CP arbitrage leaves nothing), CFTC COT positioning, crypto funding/basis/unlocks/listings/depegs, Wikipedia pageviews (again), futures roll (ES/NQ decayed since 2021), physical-delivery FND stories, VIX term structure states.

## 3. Where to hunt (the point is non-price-signal sources; log what you reached and what you could not)

**Corporate actions / structural papers (read actual documents, not summaries):**
1. **EDGAR full-text and index mining.** Specific queries to run:
   - `SC 13E3` (going-private) — look for the "interested holder" and "business-judgment-as-under-MFW" structures and CASH alternative tracks.
   - `SC TO-T` / `SC TO-I` tender offers — any structure with an odd-lot/retail-priority tranche, a per-holder cap, or a proration formula that favors small holders.
   - Exchange offers + spin-offs (`425`, `S-4`) — check who gets a sweetener and *how it's distributed*; look for "preferred" or "convertible preferred paper" being issued at >market discount into small holders.
   - Form 25 / Rule 12d4 delisting filings + companies going dark on OTC: legal ways money leaves books holders without a market exit available at par. Look for "share buyback from odd lots" or "small shareholder buyout" language.
   - 8-K Item 1.01-5.03, special items (e.g., "material agreements" like side payments to a class of holders, rebates, cash settlement alternatives).
   -  N-14 (fund reorganizations) — especially multi-class fund conversions where the smaller share class gets cashed out at NAV by design.
   - S-1 / 424(B) with "direct listing," "SMA/managed account access," or odd-lot entitlements.
   - N-CEN / N-PORT oddities: "feeder fund merge-with NAV-to-NAV" exchanges.
   - S-8 removal + plan terminations; ESPP leave dividends.
2. **Prospectuses / SAIs / Rule filings** for anything with a mechanical schedule or forced payoff: buffer ETF resets, option-income ETF option writing calendars, single-stock leveraged ETF rebalances, managed-vol funds, target-date funds, hurdle-rate/bonus-share structures (fee recalculations), feeder-fund reconversions (e.g., tax-related reboots of existing products), interval fund repurchases, closed-end share repurchase programs (VEN when 29-34% of NAV), online integration fund (funds-of-fund with a fixed discount window).
3. **Tax law and tax-advantaged money that doesn't want to stay put:**
   - Wash-sale, holding-period, QBI, QOF (Qualified Opportunity Fund 180-day windows − is the window ever an aviary of forced sellers?), 83(b)/RSU/blocking periods, corporate-to-personal donation rounding (charitable vehicles that must reduce basis by a fixed date and the market absorbs that flow), 401(k) rebalancing flows (dead already but confirm under 2026 rules), 170 charitable contributions of appreciated stock at year-end (dead already), SEP/SIMPLE/403b timing lumps, HSAs at year-end rollovers (dead), FBAR/FATCA effects (no retail angle), interstate re-domiciliation toll tax (CA/PA exit taxes — does anyone hold cash flows that dry up at a date?).
   - "Regulation changes effective date" events in 2026-2027 that create one-time legal windows: 23/5 launch, sub-penny (Rule 612 amendments), settled-market Rule 15c3-3 modernizations, SEC "affiliation" adjustments, mutual fund modernization proposals, stability of margin rules. Each change creates a transition where a forced flow exists (look for papers by exchange/market-structure lawyers on whose interests the rule protects).
4. **Broker/market plumbing + retail priority programs that exist in text:**
   - Schwab/IBKR/Fidelity/Robinhood/Webull/RH intervention programs: fractional-share orphan liquidation, grantor-rule of odd lots, DRIP roll-on behavior, "one-time" broker sweep migrations, SPIS/ACATS bonus money (broker WELCOME bonuses — a real, per-holder capped lump of $100-1,500 depending on broker, real money you collect just for moving an account; note this is not a trading strategy but check: is it BIG enough to be a candidate at $500-3k per move?).
   - Retail-only exchange mechanisms from 2025-2026 filings: Cboe RPI, 24X National Exchange retail designations, NYSE retail sweep programs, IEX/upgrade, Nasdaq retail price improvement. For each: is the small account structurally advantaged? Is there money made just by routing differently?
   - Exchange/sponsorship fee-and-fee rebates / REBATE schedules by market maker for retail flow — does a retail order get PAID sub-penny anywhere?
   - DTCC/Nasdaq/FINRA investor-protection mechanisms: negative balances protected, ACATS freebies, DRIP partial share sweep.
5. **Non-US corporate-restructuring literature (many lump classes exist that haven't a US-equivalent nameplate but do):**
   - UK: mandatory takeover offers, "squeeze-out" at 90%, capital reductions payable to shareholders by court order; scheme-of-arrangement cash-out classes.
   - Germany: Abfindung squeeze-outs (§§ 327a ff. AktG) — the cash settlement is statutorily paid to ALL small holders by law with a published "reasonable compensation" floor. For a US account holding a German ADR? Only if the ADR grants the same right — check ADR depositary agreements for squeeze-out participation.
   - Japan: 株式交付 (stock-swap) offers, "squeeze-out via T/O" at a discount — retail participation rules; TOPIX/BOJ ETF flow.
   - Australia: selective capital reductions (shareholder-approval based), demutualisations, share buyback "equal access" requirements.
   - Hong Kong: 股本 reductions and share consolidations.
   - Brazil: going-private offers (OPA) with "tag along" floors at 80% of economic value (different from US 100%!).
   - Canada: plan of arrangement, dissenting shareholder APPRAISAL rights (see also Delaware 262 below).
   - Israel: workout/merger compensation rules requiring a cash floor to minority holders.
6. **Legal enforcement as forced-flow map (read opinions for the MONEY mechanics, not as recipes):**
   - Delaware Chancery / Delaware appraisal (DGCL § 262): appraisal actions historically recover 20-70% premiums in concentrated retail tails (Perion/Moody's etc.). If there is a "retail-objector side-payment" pattern (as in some going-private settlements) — is that tradeable ahead of the record date by a small account?
   - SEC/FINRA litigation releases: FINDING OF WHAT monies were disgorged, class action settlements with claim deadlines. Economics for small holders with 10-80-share positions in settled securities: automated claims-filing services exist that collect fractions of settlement funds for tiny holders — check whether the underlying class evidence price-check steps are (a) predictable, (b) claimable by ordinary people before the deadline, and (c) whether the *claim* per 100 shares ever exceeds a few dollars (enough to matter at 10-position scale). Also look for the events that made claims valuable in the first place — e.g., whether a *predictable* pre-deadline price pressure exists around any claims deadline (mark UNVERIFIED if you cannot measure it).
   - Probate/estate/unclaimed property escheatment audits — generally not tradeable; skip unless an exchange-mediated mechanism appears.
7. **Court-ordered payout / regulatory-seizure events with retail priority:**
   - SEC "Fair Fund" distributions under § 308(a) (when a court orders disgorgement with prejudgment interest and waives civil penalties: a Fair Fund distributes to harmed shareholders on a claims basis — small holders with small positions get SMALL per-claim dollars but the program costs nothing; is there any way to enter pre-order at all? mark UNVERIFIED if not), CFTC restitution programs, state AG distributions.
   - Social Security Administration overpayment clawbacks etc. — not tradeable but list to prove you checked.
8. **Chunked retail-life money that is not a single "event" but is per-holder capped:**
   - Few-strategy families to check exhaustively: 1099-DIV from municipal CEF/note issuance, Form 1099-B "return of capital" (price-support letter vs. cash), tax-preferred "deemed dividends" under as-of-2026 rules, dividend reinvestment promotions, "muni CEF tender at NAV" corporate actions at par, preferred stock conversion right windows (issuer can call at an exact price that is ABOVE market if the holder does not convert: who pays? who gains?), exchange-traded note index-replacement events, NAV-erosion shock absorbers in new fund structures, bank account bonus/CD bonus (real; check current 2026 rates/bonuses as a lump-size baseline).
9. **Forced-flow events other researchers have *documented* in writing that the price-mining literature never touches:**
   - Fund-of-fund NAV freezes/liquidations, ETF early terminations (mass forced redemptions), bond-fund bailouts triggers, S&P/Russell subsquent-cycle spin events where the *child* is force-sold by reconstituted indexes, mutual fund "screening" changes (ESG/defence/divestment campaigns with a FIXED divestiture date tracked by the campaign organizers — often in public calendars), pension/municipal state-mandated divestment (e.g., state law says sovereign wealth funds must divest by Date X: is that calendar public before it moves price? often yes).
   - Index *reconstruction* in the baby-index world (newish index families whose reconstitution date is schedulable in advance from their published methodology docs (e.g., "reconstituted quarterly"), unlike S&P which is sudden).
   - Crypto "unlock" events that move *custodian-held* paper → the unlock is DEAd in the ledger rewards literature BUT has there been any 2025-2026 tokened-equity unlock analog? (tokenized equities: locked-up period expiries from Robinhood-EU and Kraken xStocks? For a US trader this is not tradable directly but DID it move the US open? Mark UNVERIFIED.)
10. **Community sources that actually trade lumps (search each; log whether reachable):**
   - Reddit: search for the terms "tender offer," "odd lot," "exchange offer," "appraisal rights," "going private," "closed-end fund discount," "baby bond," "preferred stock tender" (site- and year-restricted queries; never assume a subreddit name — find where these threads actually live and log it).
   - Financial forum boards that discuss closed-end funds, baby bonds, preferred stock, and spin-offs by name; search for threads containing "tender," "exchange offer," "appraisal," "odd lot," "guaranteed floor," "bonus yield."
   - Any trader blog or newsletter that publishes an EVENT CALENDAR of corporate actions ahead of time (they exist; find them; mark whether their history is downloadable and free).
   - SEC investor-education pages (Investor.gov alerts) — they publish what the SEC thinks retail is being tricked by, which often maps the same forced flows from the other side.
   - Broker "corporate actions" live pages (Schwab/IBKR/Fidelity) — the event taxonomy itself is a checklist of lump shapes; enumerate their categories and hunt for the ones never covered by quant literature.
11. **Academic (English) quickly-passed:** SSRN "tender offer premium," "appraisal rights returns," "going private," "delisting return," "forced conversion," "equity carve-out spin-off differential," "merger surplus to minority," "corporate government squeeze-out," "odd-lot," "board lot," "retail investor protections," "institutional investor fractional shares," "concentrated arbitrage," "claim farming." Non-English: the German/Australian/Japanese/HK/Brazil terms above, in their own language.

## 4. What the output must look like (edit nothing; be exhaustive but selective in what you present)

For every candidate that survives a first read, produce a **card** with:
1. Name + one-sentence mechanism (who pays, who is forced, why a small account wins)
2. The quoted clause/statute/rule-filing line that creates the money (verbatim, with the URL and its date)
3. The per-holder/e worst-case cap and how you fill it at $2k / $10k / $25k / $75k of account
4. Real dollar outcome per event × how many events/yr × worst- and best-case yields (arithmetic shown, any "published premium" halved first)
5. Execution: what you would have to DO (form, eligibility, hold, brokerage, CUSIP, election deadline, market hours)
6. Where the money goes if the event sours/regulates away — the kill scenario
7. Whether the program's data can test it cheap (eg. EDGAR-log correlation, event-study); note if it needs paid data UNVERIFIED to test
8. Sources (URL + verbatim quote + language + date); each UNVERIFIED item must say why
9. The cheapest 1-2 day test to falsify the claim
10. Confidence + the #1 reason it will die

**Deduplicate against section 2 before ranking; if an idea is a dead item in new clothes, list it under "rejected: duplicate."**

## 5. Method

- Search in English first; then search IN the deal language (German "Abfindung squeeze out," Japanese "*" squeeze out+株式交付," French "offre publique d'achat obligatoire," Spanish "OPAminorista," Portuguese "OPA tag along," Hebrew "רכישה מזערית," Korean "기업공개 청약 우선권" etc.) and map the US analog. Log which languages you worked in.
- Never invent a URL, citation or number. If you cannot open a source, mark UNVERIFIED why. Prefer primary sources; never pay to read a paywall unless free access exists.
- Deal-date everything: "document dated YYYY-MM-DD," "effective from YYYY-MM-DD," plus any SEC/rule-filing era the mechanism sits inside.
- Cap on output: 400-600 lines maximum, structured as below.

## 6. Output

1. **Coverage log**: each class from section 3 → reached / partial / blocked (why) + # of items screened.
2. **Ranked shortlist (max 12)** of lump-shaped ideas that clear the section-1 bar, ordered by expected annual $ at a $10-25k account under the section-3 halving rule.
3. **Rejected with reasons** (duplicate / in-gap / too small / manual-only / regulatory-risk-heavy).
4. **Open questions** that only a human or funded-data decision can answer.

Be adversarial with yourself: for every card, ask "if I were the paying institution, how would I make sure nobody small gets the money?" — every mechanism you cannot defeat with that lens is probably priced already.
