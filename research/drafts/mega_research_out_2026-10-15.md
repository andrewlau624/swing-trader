# MEGA deep-research output — 2026-10-15

Run of `prompt_mega_research_2026-10-15.md` by four parallel web-research agents (academic-EN /
non-US / regulators+plumbing / practitioner+community+patents+courts), synthesized and deduped
against the dead list, with the +8pp/yr-at-$10k pre-test gate applied. Top citations spot-verified
by direct fetch (marked VERIFIED below). **No test was run, no N consumed (program N = 1002 per
last session note; this memo adds none).** No deployment.

**Honest headline: no candidate with established evidence clears the +8pp/yr bar.** The screen
found (a) two *kill-test* candidates whose SHAPE can clear the bar but whose effect is unestablished
(both $0, both one-evening/2-day tests), (b) one rule-created execution-cost lever worth +2-7pp/yr
on regular-session legs, (c) a new-session watch (23/5, starts 2026-12-06). Everything else
deduped into dead classes, access-kills, or ceiling-kills. This matches the standing result: the
free-data frontier inside the old design space is exhausted; what is left is *new venues / new
data channels / rule-created retail priority*.

---

## 1. Coverage log

| Source class | Status | Items screened / notes |
|---|---|---|
| SSRN (newest 2023-26) | **partial** | papers.ssrn.com 403s bots; titles/DOIs/dates verified via Crossref+OpenAlex, **abstracts UNVERIFIED** for all SSRN items. ~45 surfaced, ~25 screened |
| NBER 2024-26 | **blocked (JS site)** | ~5 titles only, off-topic |
| arXiv q-fin | **reached** | ~25 items, full abstracts (export.arxiv.org) |
| RePEc/IDEAS | partial | site search broken; Crossref/OpenAlex proxy, ~10 |
| Scholar / cited-by chains | partial | Scholar unreachable; OpenAlex citation graph used (McLean-Pontiff 1,519 cites -> top 451 works since 2024 screened at 15; JKP 2023 490 cites). **Chen-Zimmermann openassetpricing.com fetched directly** (2025-10-22 update): 331 signals -> 165 clear / 100 indirect / 47 likely / 14 not / 5 drop |
| Journal TOCs | partial | JPM + FAJ 2025-26 swept via Crossref (~45 titles); JF/JFE/RFS/JFQA/ROF hit only via citations |
| AFA/WFA/EFA programs | **blocked** | AFA 2026 URL 404; WFA already promoting 2027. One AFA submission full text reached |
| China (CNKI/Wanfang/brokers/Xueqiu) | partial | paywalled; DDG/Baidu-Xueshu snippets; PLOS One price-limit full text reached. ~14 items |
| Japan (J-STAGE/TCER/JPX/JSME) | **reached** | TOPIX phased-exclusion WP, BoJ-ETF papers, ~5 |
| Korea / Taiwan / HK / India | partial/light | KCMI short-ban quote; Taiwan IREF abstracts; no India academic hit. ~8 |
| Brazil / Russia / Europe | partial | FGV RBF closing-auction abstract; CyberLeninka thin (calendar only); Bundesbank DP 33/2024 full PDF |
| Central banks (BIS/ECB/Fed/BoE/IMF) | partial | ECB FSR forced-sales box; Fed T+1 via SSRN pair (abstracts UNVERIFIED) |
| SEC / rule filings | **reached via federalregister.gov** (~20 filings incl. FR 2026-20799 VERIFIED) | direct EDGAR not exercised (no SEC_USER_AGENT) |
| FINRA | **reached** | Reg Notice 26-10 full text fetched |
| CFTC / OCC / DTCC / NSCC | partial | NSCC 24x5-support filing only |
| Exchange updates (Cboe/Nasdaq/NYSE/IEX) | **reached** | RPI pages (VERIFIED), 23/5 filings, halt/LULD overnight amendments |
| Fund prospectuses/SAIs | **reached** | buffer-ETF N-CSR, JEPI prospectus, YieldMax TSLY issuer page — mechanical schedules extracted |
| Tokenized-equity programs | **reached** | Robinhood EU PR; Kraken xStocks support ("Not available in the U.S. or to U.S. persons", updated 2026-06-18) |
| Quantpedia 2025-26 | reached | ~40 new strategy entries scanned; premium paywalled |
| Practitioner blogs / forums | partial | Alpha Architect, Return Stacked reached; Elite Trader/usethinkscript = dead-class content; NuclearPhynance dead; Quantopian archives gone |
| Reddit / TradingView / GitHub / Substacks / X | partial | search-only; no verified live track records found; X not reached |
| Podcasts / conferences | partial | Odd Lots 2026-10-01 transcript; Cboe RMC notices; others not reached |
| Patents | **reached** | nothing mechanical/scheduled and harvestable |
| Court / enforcement | reached | the one front-running case found is MNPI — excluded by rule; nothing else |

~105 search/fetch calls; ~190-210 items screened. Known gaps: SSRN abstracts, NBER, AFA/WFA
programs, Scholar, CNKI/Xueqiu depth, r/thetagang (options class excluded by prior), X/Twitter.

## 2. Ranked shortlist

### 1. TOK-GAP — tokenized-stock certificates as an overnight sensor into the 09:30 open (kill-test candidate, $0)
- **Mechanism:** tokenized wrappers of US stocks (MSTRX, NVDAX, AAPLX, TSLAX on Gate; xStocks family)
  trade ~24/7; their pre-09:00 marks carry overnight/weekend repricing that the US opening cross then
  absorbs. Forced party: overnight token traders pricing without US liquidity; payer: whoever rests
  opening-auction orders against stale information. **Note the access distinction:** the tokens
  themselves are NOT tradeable by US persons (Kraken: "Not available in the U.S. or to U.S. persons";
  Robinhood EU-only) — this candidate only *reads* their free public OHLCV as a signal and trades the
  US-listed underlying at the ~0bp open auction.
- **Evidence (VERIFIED, fetched):** NEST, arXiv 2610.21491 (submitted 2026-10-15, MARBLE 2026/Springer):
  token-only R^2 0.916 on MSTRx shrinks under controls; "the token explains 15.7% of the remaining
  gap variation (1% frontier 0.031), and 14.0% to 17.0% under stricter clock variants"; trade-level
  reconstruction on Gate 25.2%; "NVDAX and AAPLX clear their frontiers, whereas TSLAX does not."
  Paper's own warning (verbatim): "A token return and the next opening gap, however, share the price
  move from the previous close to the token mark, so part of their apparent fit is mechanical."
  **NEST predicts the GAP only — it stops exactly where our trade would start.** Second source:
  SSRN 7470121 "One Instrument, Two Technologies" (title/date verified, abstract UNVERIFIED).
- **Ceiling at $10k:** ~200 admissible days x net edge x ~100% deployable x 50% capture -> clears
  +8pp iff **conditional open->close drift >= 8bp/day** on token-sign days. Shape is right; the drift
  is untested anywhere.
- **Account fit:** taxable or Roth, long-only tilt at the open; no shorting needed.
- **Data:** Gate/CCXT public OHLCV (free; depth unverified), Alpaca minutes (owned), BTC 1m (owned). $0.
- **Cheapest kill test:** 2025-06 -> 2026-10: token mark 09:00 -> official 09:30 gap (replicate NEST
  controls) -> then the real question: **open->close drift conditional on token sign**, day-clustered
  t, ex-top-5, 3x cost shock. ~2 days.
- **Falsifiable prediction:** conditional on BTC, mark age, and a pre-09:00 premarket proxy, token
  sign at 09:00 predicts open->close drift on NVDAX/AAPLX (the certificates that clear NEST's
  frontier) and not on TSLAX.
- **Dedupe:** not the dead cross-asset lead/lag class (new data channel, predicts into a tradable
  auction, not venue-to-venue returns); distinct from ALIVE OVN-MOM (that is trailing overnight
  *momentum* of the stock itself, no token channel).
- **Confidence: LOW.** Biggest fail reason: gap-prediction != drift — the 04:00-09:30 premarket may
  already arbitrage the token's information away before the open; ~16-month sample; thin token prints.

### 2. BTC-ETF-FLOW — bitcoin/ether spot-ETF flow momentum into next-day IBIT (kill-test candidate, $0)
- **Mechanism:** AP creations/redemptions force same-day BTC buying/selling in US hours (in-kind);
  next-day continuation of the ETF-flow state. Forced party: AP/issuer basket at 16:00 NY; payer:
  the flow-chasing ETF holder.
- **Evidence: NONE net-of-cost and OOS found anywhere** — all hits are narrative flow reporting
  (investing.com 2026-02-27: "$257-258 million of net inflows on February 24, followed by roughly
  $506-507 million on February 25"; Yahoo/Glassnode 2026-07-03: 34 negative of 39 sessions, -$8.95B).
  Effect itself UNVERIFIED. SSRN flow-impact papers exist (6592830, 6564338, 7545019) — abstracts
  UNVERIFIED.
- **Ceiling at $10k:** ~120 big-flow days x 30bp net x ~100% deployable (IBIT spread 5-10bp) x 50%
  = **+18pp/yr IF the effect is >= 30bp/day net.** Shape clears; effect unestablished.
- **Account fit:** IBIT is an ETF — **Roth-eligible, long-only**. Good.
- **Data:** Farside daily-flow CSV / Glassnode series — free.
- **Cheapest kill test:** t-1 net-flow decile -> t IBIT open->open, 2024-2026, 10bp RT, halves +
  ex-top-5. One evening.
- **Falsifiable prediction:** top-decile next-day IBIT return > bottom decile by >= 25bp net in BOTH
  halves (2024-25 vs 2026).
- **Dedupe:** dead list has "ETF premium/discount and creation/redemption (SPY, bond SPDRs)" and
  "crypto funding/basis/unlocks/listings/depegs" — a *flow-momentum* signal into the ETF's own next
  day is neither; CBAS (cash-futures basis) was futures-side. New costume risk acknowledged; the
  kill test is the cheap way to settle it.
- **Confidence: LOW.** Biggest fail reason: the effect is just BTC momentum already inside the 09:30
  price (contemporaneous flow impact = 0 under half-capture); 2026 multi-month outflow streaks cut
  against naive continuation.

### 3. RPI — Cboe EDGX/BYX Retail Price Improvement, live 2026-04-10 (execution-cost lever, user test)
- **Mechanism:** rule-created sub-penny ($0.001) liquidity that ONLY retail-marked orders may
  execute against — a retail-priority market that did not exist before April 2026. **VERIFIED
  verbatim (cboe.com):** "Retail Price Improving (RPI) orders are available on EDGX and BYX. RPI
  orders offer price improvement in $0.001 increments to Retail Member Organizations (RMOs) that
  enter a Retail Order (RO)... RPI orders only interact with Retail Orders." SEC order (FR
  2026-05660, 2026-03-24): "an RPI Order must be priced at least $0.001 better than the Protected
  NBB or Protected NBO" (Rule 612(d) exemption).
- **Why it persists:** priority is rule-created; non-retail flow is barred from RPI interest.
- **Ceiling at $10k:** pure cost lever, not alpha: ~1-2 regular-session fills/day x 3-10bp
  improvement x 50% capital = **+2-7pp/yr** — below the +8pp bar alone, but it raises the net of
  every existing regular-session edge (and thin $10-50M-ADV names are exactly where 12-80bp hurts).
- **Account fit:** taxable/Roth, either side, regular session only. Auction legs (already ~0bp)
  unaffected.
- **Data:** none. **Cheapest test:** one Schwab test order in a wide-spread name; check whether
  Schwab certifies as an RMO and routes RO-flagged orders to EDGX/BYX (**UNVERIFIED** — broker
  participation is the whole question; user-run like the CEF open test).
- **Falsifiable prediction:** >= 30% of small marketable retail orders in $10-50M-ADV names fill
  better than NBBO.
- **Confidence: MEDIUM** on the mechanism (rule text verified), LOW on access.
- Fail reason: Schwab not routing there, or RPI depth concentrated in high-flow mega-caps only.

### 4. OVN-23/5 — official 23/5 overnight session watch, starts 2026-12-06 (log-only, not a strategy)
- **Mechanic (VERIFIED, FR 2026-20799, 2026-10-13, Release 34-106624):** Joint Industry Plan
  Twenty-Ninth Amendment — overnight trading with a 7:30 p.m. ET consolidated-price snapshot
  (temporary, <= 120 days) and Overnight LULD ±20% bands (x leverage ratio for leveraged ETPs).
  Nasdaq/NYSE Arca filings dated 2026-09-18; Nasdaq 4120 ETP-halt filing FR 2026-21137.
- **Use for this book:** not new alpha. (a) The ALIVE night leg gains a mid-flight exit venue —
  re-time the 04:00 exit only if overnight execution beats the 09:30 open by >= 5bp median over 60
  sessions; (b) launch-friction monitor (single-dealer books, the 20:00-21:00 pause, stale quotes)
  for dislocations — same class as NIGHT-23/5 in the practitioner screen ("a new trading session
  from 9 p.m. to 4 a.m." with "a mandatory one-hour trading pause Monday through Thursday evening
  between 8 p.m. and 9 p.m. ET" — Skadden memo 2026-10-13).
- **Evidence:** none — regime does not exist until 2026-12-06. Blue-Ocean-era adverse-selection
  papers exist (SSRN 6610883, 7301379 — abstracts UNVERIFIED); no readable numbers.
- **Kill test:** log-only shadow (REGISTRY entry per standing rule): overnight-session best bid/ask
  and last print at 04:00 vs the 09:30 official open on night-leg names, 60 sessions.
- **Confidence: MEDIUM-LOW.** Fail reason: broker access unknown (does Schwab or Alpaca offer the
  session on our names, and are prints SIP-official?) and overnight spreads likely wide.

### 5-10. Documented near-misses (below bar — recorded so nobody re-derives them)
5. **LULD-PAUSE** — China price-limit continuation ("price continuation is much more likely to occur
   than price reversal on the next trading day after a limit-hitting day, especially for down-limit
   hits", PLOS One 2015, limit-down next-day continuation 75.9% vs 63.7%) mapped to US LULD pause
   resumption->close. Ceiling ~+1.1pp/yr; halt names pay 12-80bp; liquid subset tiny. Below bar.
6. **CONV-CALL** — US convertible forced-conversion overhang (China 强赎 documentation: concentrated
   conversion selling after call notices). ~100-150 events/yr x ~1.5% x 25% deployable x 50% =
   +0.19pp. Effect likely in the announcement gap. Below bar.
7. **LETF-1STK** — single-stock LETF close rebalancing (NVDL $4.4B AUM into ONE stock). Old Fed
   number is index-context ("LETF flows equivalent to 1% of stock volume... 3.09% of daily
   volatility", FEDS 2013-48); NVDL flow ~$88M vs $30-50B NVDA volume — only thinner underlyings
   could reach 1-3% of volume. ~+0.5pp. **Near-duplicate of the dead LETF class** (the class label
   was tested on index products, not these 2022+ products); 2026 SSRN cluster exists (7554363,
   7030278, 7603998, 5400451 — abstracts UNVERIFIED). Revive only if an abstract directly
   contradicts the decay finding.
8. **BUF-RESET** — buffer-ETF FLEX-option resets ("On the first day of each new Target Outcome
   Period, the Fund resets by investing in a new set of FLEX Options...", N-CSR fetched). Flow lands
   in SPY FLEX options, not the underlying; user cannot take the dealer side. KILL; keep sticker
   filings as free monitoring. AQR/JPM: "the majority of buffer funds have produced inferior
   risk-adjusted returns"; Hill (JBIS 2023): tracking vs target "averaged very close to 0%".
9. **OI-ETF** — option-income ETFs (JEPI ELN resets, TSLY weekly call spreads, "100.00% estimated
   return of capital and 0.00% income" — NAV erosion). The one mechanism paper (AFA submission,
   "Flow-Induced Demand Pressure from Option-Trading ETFs") finds rollover trades move option IV
   ("coefficient of 0.008... 1% level"), not the underlying. Options-tier. KILL.
10. **FINRA-4210-TRANSITION** — broker-forced intraday deleveraging during the 26-10 phase-in
    ("until October 20, 2027"). No data exists; watch only. (Margin-2610 itself is an enabling fact,
    not a strategy: PDT abolished, real-time intraday BP — makes intraday flips feasible at $2.3k.)

## 3. Rejected with reasons (aggregated, deduped)

**Duplicate of dead list (selection):** buffer-ETF roll timing (options overlay); option-income
underlying flow (no study; funds underperform own underlying: "70.8%... 42.6 points behind MSTR");
0DTE dealer hedging in single stocks (arXiv 2512.17923: LLM *detection* 71.5%, "detection accuracy...
remains stable even as economic profitability varies quarterly" — detection is not profit); crypto
ETF flow -> BTC price (75bp spot cost, contemporaneous); cross-index overnight -> morning gap
(Borsa Istanbul Review 2026-09); TOPIX/index reconstitution (gap; "The Disappearing Index Effect",
JF 2024, confirms shrinkage); HF anticipatory rebalancing (Yelekenova 2025 PhD: front-running a
known calendar, +0.6%/month accrues to HFs); B3 closing-auction imbalance (FGV RBF 2026-06); BLS/
Bundesbank retail order flow (PFOF class); Korea short-ban (US analog SSR done: SSR-LIFT); Taiwan
alerts/day-trading; MOEX calendar anomalies; margin-debt timing (MFLW kill); JoinQuant ETF 折价;
Quantpedia 1115 margin-debt / 1130 auction+macro / 1114 IPO-options / 1116 intraday option
reversals / 1117-1118 bond betas (ceiling/access); wheel/thetagang; r/algotrading "VRT Levels"
(no-cost backtest culture); Quant League contest winners (unverifiable); Composer TQQQ rotation
(LETF trend costume); patents (nothing scheduled/harvestable); TIAA front-running (MNPI — excluded
by rule); Cboe new options products (CBTX/MBTX, binary KPI options, 3x single-commodity ETFs —
options tier / swap-rebalanced); retirement-plan payroll flows (window-dressing class); NSCC 24x5
settlement support (plumbing); LULD rule plumbing itself; 24X exchange retail designation (watch
only); Robinhood Chain token rails (US access unclear, volumes "fall more than 40%", CoinDesk
2026-10-10).

**Ceiling too small (pre-test gate):** Heston-Sadka cross-seasonal seasonality — the one
price-only "clear" family in Chen-Zimmermann not already dead here; long-only leg ~1-2%/yr on a
monthly-turnover basket = ~+1pp at $10k. Loan-fee anomaly (short side; borrow data-blocked). T+1
frictions (FTD family, long side loses). Indian overnight anomaly (venue-inaccessible). China
block-trade discount ("an average of about 4% block discount", PBFJ 2012 — no US public block
tape). 龙虎榜 / 北向资金 (no US per-stock daily disclosure analog). Pledge/margin-call forced
selling (US pledge 8-Ks ~tens/yr, <0.2pp). Snowball autocall knock-in hedging (documented in
futures basis — CBAS closed; US barriers unobservable). BoJ ETF lending channel (no US analog).

**Access:** tokenized-equity trading itself (Kraken "Not available in the U.S. or to U.S. persons",
2026-06-18; Robinhood EU-only) — but note reading their public data is NOT blocked (feeds TOK-GAP);
non-US exchanges; futures/micro-futures (no account); OTC grey market.

**UNVERIFIED items deliberately not promoted:** all SSRN-abstract claims (403), NBER, AFA 2026
program, several CNKI/Xueqiu snippets, the "11,991 halt events" practitioner count.

**Contradicting-evidence check (per prompt §2):** nothing found directly contradicts a dead
verdict. Positive confirmations of dead-list reasoning: Disappearing Index Effect (index reconstitution
keeps shrinking); buffer funds inferior risk-adjusted returns; JKP replication + SignalDoc counts
(165/331 "clear" — and the only clear non-dead family left, cross-seasonal seasonality, fails the
ceiling gate).

## 4. Open questions (human decisions)

1. **TOK-GAP kill test** — $0, ~2 days (Gate OHLCV + owned Alpaca minutes; log-only). Run? It is
   the only genuinely new *data channel* this screen found.
2. **BTC-ETF-FLOW kill test** — $0, one evening (Farside CSV). Run?
3. **Log-only 23/5 overnight-cost recorder** before 2026-12-06 (60 sessions, night-leg names,
   overnight print/quote at 04:00 vs 09:30 open; REGISTRY entry + weekly digest per standing rule).
   Also check: Alpaca 24/5 coverage of night-leg names and whether its prints are SIP-official. OK?
4. **RPI routing test** — user must place one test order (auto-mode classifier blocks real orders,
   like the CEF open test): does Schwab route retail-marked orders to EDGX/BYX RPI? Any fill
   better than NBBO?
5. **No data purchase is justified by this screen** (data-buy rule). Signed dealer gamma stays a
   spec; nothing here raised its prior.
6. **Optional:** N-PORT CEF assets/leverage for CEF-RV inputs (free; needs the standing
   SEC_USER_AGENT one-liner).
7. **Session tooling for next research sweep:** free OpenAlex API key (one POST with an email)
   and/or an Exa search key would roughly double query throughput (Exa rate-limited mid-task this
   time). No purchase required.
8. **Tokenized-venue data in the research pipeline** (Kraken/Gate public APIs, $0) — confirm OK as
   a standing data source before any TOK-GAP work.
