# Branch H: access-unlock map (2026-10-17)

Map only. Nothing approved, nothing bought, no backtest run, no live code touched. Return numbers below are copied from the repo ledgers (CLAUDE.md, mech_loop, morning_memo, branch_B/F/G) and are not re-derived.

Source caveat: the broker pages (interactivebrokers.com SYEP, schwab.com stock-loan, securities-lending/faqs, futures/faqs) returned HTTP 403 or an access-denied page to WebFetch, so I could not open them. Every broker fact below comes from WebSearch result snippets and is labelled "search snippet". Confirm in the account or by phone before relying on any of them.

## 1. Verified facts (2026-10-17), with sources
| item | fact | source |
|---|---|---|
| IBKR SYEP | 50% of a market-based rate. Needs a margin account, or a cash account with liquid net worth > $25k (US site; older IBKR Campus text says $50k). Lends fully-paid and excess-margin shares. IRA eligibility not stated anywhere I found. | search snippet: interactivebrokers.com/campus/trading-lessons/syep/ and interactivebrokers.com/en/pricing/stock-yield-enhancement-program.php (pages not opened) |
| Schwab fully-paid lending (SLFP) | $100k household assets, invitation or approval, 50/50 split. IRA eligibility conflicts between sources (Bogleheads says yes, LegalClarity says no). Already recorded as "not actionable" in morning_memo_2026-10-17.md. | search snippet: schwab.com/learn/story/earning-extra-income-with-securities-lending, schwab.com/securities-lending/faqs (not opened); bogleheads.org/forum/viewtopic.php?t=251763 |
| IBKR shortstock file | ftp2.interactivebrokers.com, user `shortstock`, blank password, one file per country (usa.txt). Pipe-delimited: `#SYM\|CUR\|NAME\|CON\|ISIN\|REBATERATE\|FEERATE\|AVAILABLE\|`. FEERATE is the borrow cost, % annualised. AVAILABLE can be a ">" value. Current snapshot only, no history on the server. Some symbols (warrants) are missing. A forward archive therefore has to be built by us. | search snippets: community.portfolio123.com/t/historical-data-on-ib-short-lending-fee-and-share-availability/58254; apify.com/stdevi/ibkr-shortable-stocks-scraper; elitetrader thread 347024 (not opened) |
| Futures in IRA | Schwab: IRA needs $25k NLV, with margin and spread approval, and the IRA margin requirement is 125% of initial. Taxable: margin approval plus a $1,500 minimum (search snippet). This conflicts with the common brief's "no futures". IBKR allows futures in an IRA but with much higher margin (page about 12 years old). | search snippet: schwab.com/futures/faqs (403 on direct fetch); bogleheads.org/forum/viewtopic.php?t=289144 |
| Portfolio margin | IBKR: $110k to open, $100k to keep. FINRA floor is $100k. | search snippet of IBKR and matchmybroker pages (not opened) |
| IBKR open auction | MKT + tif=OPG sends a market-on-open. Nasdaq cutoff is 09:28 ET. Whether OPG is accepted on NYSE-listed preferreds is not confirmed. | search snippet: interactivebrokers.com/en/trading/orders/moo.php, interactivebrokers.com/docs/general/order-types/market-orders/market-on-open (not opened) |
| Canada-US treaty | Art. XXI(2) exempts dividends earned by a US IRA from Canadian tax. An IRS info letter confirms this for IRAs. Whether IBKR applies it automatically is unknown. | search snippet: irs.gov/pub/irs-wd/1330025.pdf (not opened) |
| Reg SHO threshold | 5 consecutive settlement days of fails >= 10k shares and >= 0.5% of shares outstanding. Close-out at 13 consecutive days. | search snippet: sec.gov/investor/pubs/regsho.htm; nasdaqtrader.com/trader.aspx?id=RegSHOThreshold |

## 2. What the previously dead results actually need
| killed result | why it died | does an account capability fix it? |
|---|---|---|
| SSR-LIFT (short T+2 open to close, +16.7bp/day gross, cost-bound) | Short only, squeeze tail, ~4-5pp at honest capture | The Schwab taxable margin account can already short. IBKR adds borrow transparency and (per search snippets) more locates. That is information, not new access. Roth can never short. The ceiling is unchanged. |
| Threshold-flow (long CAR -959bp, median -1242, ex-top-5 -1217, 1516 episodes) | The profitable side is the short of hard-to-borrow names | Only if shares are available to short. Availability and fee at the event entry have never been measured. This is the one short-only result where a free dataset decides everything (card H-1). |
| BORROW-XS (short leg +106bp/mo gross, +84bp net of option-implied borrow) | The payoff is the short leg of names that are often unborrowable | Same as above. A real locate and fee replaces the option-implied rate. Long-only D1 tilt stays a size/vol beta. |
| TVIX-style ETN creation-suspension premium (branch_B) | Pays the short side only, ~0.3 events/yr | A borrowable ETN is rarer still. Ceiling ~0. Dropped. |
| Margin-hike deleveraging (branch_F) | No point-in-time archive of margin changes | IBKR client emails are the only source. If the user holds an IBKR account, saving them builds a forward log. It is not a trade. |
| PREF-EX CO form dies if the open leg misses the auction (no Schwab MOO) | Schwab has no MOO, so CC (~60-70% of CO) is the safe form | IBKR MKT+OPG could restore CO (card H-3). |
| Box-spread financing, TME 3x scaling | PM or margin cost | PM at $125k+ only, or a ceiling-kill (TME 3x +5.8pp, below gate). Nothing at $10-25k. |

## 3. Capability ranking
Score = expected pp/yr at $10k divided by (cost + effort). The expected value is the ceiling times a subjective probability that the mechanism exists and transfers.

| rank | capability | cost / effort | ceiling at $10k | expected pp | verdict |
|---|---|---|---|---|---|
| 1 | Free IBKR shortstock FTP daily archive (no account needed) | $0, a cron job, minutes | n/a, it is a dataset | n/a, it unlocks ranks 2 and 6 | Do first. History is not archived by IBKR, so every day not saved is lost. |
| 2 | Canadian / Australian / European $25-par-like preferreds, PREF-EX replication (H-2) | Data test $0 if WRDS Datastream is entitled (CLAUDE.md lists it; raw prices and ex-dates not checked). Trading needs IBKR plus FX. | If it transfers: US CO is ~$789/yr at $10k, i.e. ~+8pp, so a second market is plausibly +4-8pp | ~+1.5pp (P of transfer ~25%, see H-2) | Best expected value per cost. Untouched data. |
| 3 | IBKR Roth or taxable with MOO/OPG (H-3) | Second broker account, API, FX-free | CO over CC ~ +30-40% of PREF-EX dollars, i.e. ~$250-300/yr at $10k | ~+1-3pp, and only if PREF-EX passes its own 30-trip live gate (0/30 today) | Conditional on an existing pilot. Do not move money before the gate. |
| 4 | IBKR short account for the threshold-flow short (H-1) | Margin account >= $2k, same or new | Wide; see card | ~+1.5pp (P(borrowable and affordable) ~15%) | Cheap if rank 1 is running. The test is free; the account is not needed until it passes. |
| 5 | IBKR SYEP | Account, $25k liquid or margin | $20-80/yr per morning memo; PREF-EX names are thin and rarely borrowed | ~0.2pp | Not worth it at this size. IRA eligibility unknown. |
| 6 | Futures, Schwab taxable (snippet: $1.5k) or IRA ($25k) | Approval, tiny edge unlock | No alive mechanism is futures-based (roll, FND, basis, COT all killed for edge, not access). Section 1256 60/40 tax is the one real benefit. | ~0 | Nothing to unlock. |
| 7 | Schwab SLFP | $100k, invite | 0 (ineligible) | 0 | n/a until $100k. |
| 8 | Portfolio margin | $110-125k | 0 | 0 | n/a. |

## 4. Candidate cards

### H-1. Threshold-flow short, gated on IBKR availability and fee (not a trade yet)
- Mechanism: the Rule 203(b)(3) close-out is a real forced buy at day 13, and the pre-registered long test measured the opposite sign over the window. Reference: CLAUDE.md "Study THR": CAR to deadline -959bp, median -1242, hit 27%, day-clustered t -6.4, ex-top-5 -1217; 2021-23 -58bp, 2024-26 -1094bp; overnight +267, intraday -878.
- Why it is only a card: the mirror (short) was never registered. The sign was chosen after seeing the long result. The 2021-23 leg is ~0, so this may be a 2024-26 regime (many 2x single-stock ETFs sit on the list, per the Nasdaq page snippet).
- Who pays: holders of names that are on the list because they are hard to borrow. The short side needs locates, and the fee may be 50-200%+ annualised or unavailable.
- Descriptive ceiling (not a backtest): if N borrowable events/yr, net ~6% after fee over 13 sessions, 20% of the account per event, 50% capture, then ceiling = N x 0.6pp. N = 15 gives +9pp. N is unknown, and I expect it to be low because list names are by construction the ones with no shares available. Squeeze tail: unbounded on a short.
- Capital lock: 13 settlement days.
- Cheapest falsifier (zero cost, forward only): archive IBKR usa.txt daily from now; join to the Nasdaq/NYSE daily threshold lists (free, 2008+/2012+, per CLAUDE.md); at each event entry (open after the 5th flagged day) record AVAILABLE and FEERATE. Pre-register: count events with AVAILABLE >= 1,000 shares and FEERATE <= 40%/yr; kill if < 6 per year or if their median net short return (fee-adjusted, vs SPY hedge) is <= 0 after 60 forward events. Historical period (2021-26) is touched by THR; only forward data is untouched.
- Roth: impossible (no shorting).

### H-2. International $25-par income-paper ex-date replication
- Mechanism under test: price drop on the ex-date is smaller than the dividend (under-adjustment) in thin, retail-held income paper. US evidence: official crosses 2021-26 +38bp/event, drop ~0.8 x dividend, 22/22 Sharadar years (CLAUDE.md "PREF-EX"). The repo's own THN note says tax clientele is contributing, not proven. That is the main reason the transfer probability is only ~25%: Canadian preferreds are largely held in registered plans (TFSA/RRSP), which would remove the tax-clientele driver if it is the cause. This is my inference, not a sourced fact.
- Alternatives worth listing: ASX hybrids (franking credits make the ex-date drop systematically different, which makes it a different mechanism, not a replication); European hybrids and UK prefs.
- Why it persists in the US (auction-size cap): the edge lives in thin $25-par paper. A second market adds capacity, because the US dollars plateau above ~$5k (ROTH-STACK).
- Data path: WRDS Datastream (licensed per CLAUDE.md; coverage of raw TSX prices and ex-dates unverified), Compustat Global if entitled (unverified), or Yahoo for a manual sample. Need unadjusted close and ex-dividend date. Prices must be raw, not adjusted (see the ETC/SPDR data bug note).
- Tradability caveats not verified: TSX closing and opening auction access through IBKR; CAD conversion cost; Canadian withholding (15% taxable, treaty exempt for IRA per Art. XXI snippet, whether IBKR applies it automatically unknown).
- Ceiling: if it transfers at US size, ~+4-8pp at $10k; expected ~+1.5pp.
- Falsifier to pre-register: TSX preferreds $25 par, close(E-1) to open(E) plus dividend, 2005-2020 raw data. Pass: net >= +15bp/event at 10bp round trip, median > 0, day-clustered t >= 2, >= 80% of years positive, dividend drop ratio <= 0.9. Kill otherwise. Untouched period: all of it (the program has no Canadian data). Cost: $0 if Datastream works.

### H-3. IBKR MOO/OPG to restore the CO form of PREF-EX
- Fact: IBKR documents MKT+OPG as a market-on-open, with a 09:28 ET cutoff on Nasdaq (search snippet). Not confirmed for NYSE-listed preferreds.
- Gain: CO over CC is ~+30-40% of PREF-EX dollars (shadow notes: CC ~60-70% of CO).
- Test: one 1-share Roth order, as with the JRI Schwab test, but only after the Schwab pilot passes. Falsifier: open-leg cost vs the official open cross on 10+ preferred opens, kill if mean miss > 5bp.
- Roth mechanics (a second Roth at another broker) are a user decision. Do not move money for this alone.

## 5. Dropped
- IBKR SYEP and Schwab SLFP as income: $20-80/yr or ineligible (morning_memo_2026-10-17.md).
- Futures for the night leg or IBS: edges are tied to the equity auction, MNQ/MES notional is too large for $2.3k, and no futures mechanism survived on edge (fut_roll, FND, CBAS, COTX).
- Portfolio margin and box spreads: need $110-125k.
- TVIX-type ETN premium short: ~0.3 events/yr (branch_B).
- Margin-change archive: IBKR emails only, 3 press episodes, ceiling ~1.9pp (branch_F).

## 6. What this map says
- No account upgrade by itself produces a new strategy. The two things worth doing are both free: archive the IBKR shortstock file daily, and test the PREF-EX ex-date rule on a market the program has never seen.
- The short-only killed results (SSR-LIFT, threshold flow, BORROW-XS) were killed partly on an unmeasured quantity: real availability and fee. That quantity can be measured forward at $0 without opening an account.
