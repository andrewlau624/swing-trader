# MEGA deep-research prompt (for an external research agent)

You are a research agent. Your job is to **scour every legitimate source you can reach, in every language you can read**, for
trading mechanisms that a small US retail account can exploit. Breadth is the point: search far past the first page of
English results. Depth is the second point: follow citations, read the paper, find the out-of-sample evidence.

Today is 2026-10-15. Treat anything you know from training as possibly stale; prefer sources you can open and date.

---

## 1. Who this is for (the constraints decide what counts)

- **Accounts:** a US taxable margin account (~$2.3k now, growing to ~$25k) and a Roth IRA (+$7,500 of new money every year,
  no shorting, no intraday margin). Rank everything by **% per year at $2k, $10k and $25k after costs**. Capacity above $100k
  does not matter; a small account's ability to trade thin names, odd lots and auctions is an advantage.
- **Access:** Schwab (US stocks, ETFs, ETNs, preferreds, baby bonds, closed-end funds; listed options; spot BTC/ETH since
  2026-05), Alpaca API. Orders at the 09:30 opening auction, 16:00 closing auction or in the regular session. No futures
  account yet (micro futures are a possible later addition), no non-US exchanges, no OTC grey market.
- **Costs measured live:** official auction fills ~0bp; regular-session single stocks pay the spread (3-10bp in large caps,
  12-80bp in $10-50M ADV names).
- **Rules are date-versioned.** The FINRA pattern-day-trader rule was replaced 2026-06-04 (Schwab stopped counting day trades
  2026-06-08). Nasdaq/NYSE Arca 23/5 trading starts 2026-12-06. Cite the date of every rule you rely on.
- **Bar for a "candidate":** a plausible path to **+8 percentage points per year on the whole account at $10k**, independent
  of the existing book, under honest capture (assume you keep at most half of the published effect). Show the arithmetic:
  `events/yr x net edge per event x share of account deployable per event x capture rate`.
  Shapes that can clear it: daily x >= 15bp net x >= 50% of capital; ~monthly x >= 2% x ~100%; rare events x >= 10-20% with a
  per-holder cap that small accounts fill. Shapes that cannot: deep-market calendar effects, signals that deploy a sliver of
  capital, anything whose edge is < 5x its round-trip cost.

## 2. Already tested and DEAD (do not bring these back without genuinely new evidence)

About 1,000 pre-registered tests have been run. Report a dead item only if you find evidence that directly contradicts the
reason it died (and say so explicitly).

- **Technical indicators / chart patterns:** 40 daily indicators (VCP, TTM squeeze, Bollinger/Keltner, HVP, Parkinson/GK/YZ,
  choppiness, ulcer, Hurst, FDI, Donchian, CMF, Klinger, NVI/PVI, OBV/VPT, anchored VWAP, pocket pivot, volume dry-up, RVOL,
  OU half-life, variance ratio, entropy, residual momentum, Amihud, Roll) as 2% tails, 15,210 pairwise combinations and an
  ML composite, 2-30 day holds: nothing. MACD/RSI on stocks and crypto at 4h-1d: nothing. ICT/SMC/fair-value-gap setups: random.
- **Day trading / scalping:** ORB, VWAP reclaim, HOD breaks, gap fades, in-play scanners, order-flow imbalance, quote
  imbalance, ISO sweeps, retail-flow (BJZZ), stop runs, prior-day levels, sector-ETF lead-lag: all dead after costs.
- **Exits:** trailing stops, take-profits, mid-day exits, intraday-peak exits: worse than fixed auction exits.
- **Classic anomalies post-publication:** PEAD (in the announcement gap), earnings-announcement premium, analyst revisions,
  industry/sector momentum, customer-supplier momentum (Cohen-Frazzini replicated 1981-2004, zero after 2015), 52-week high,
  low-vol, value/quality/size/issuance sorts in 2021-26, January/December tax-loss bounce (gross only), turn-of-month,
  window dressing, dividend-month premium, momentum/52w/theme.
- **Events:** S&P/Nasdaq-100 add/delete (in the gap), spin-offs, split-offs (small), merger arb (spread ~T-bill), SPACs,
  IPOs, lockups, secondary offerings, ATM programs, buybacks/ASR, 13D (except small CEF effect), 10b5-1, Form 144, FTD/Reg SHO
  threshold forced buy-ins (long side loses), deal breaks, 8-K text, rights offerings (small/manual), odd-lot tenders
  (real but manual, capital locked; retired).
- **Options:** buying or selling premium at retail (0DTE, straddles, condors, flies, put-write, earnings): the bid-ask
  spread eats the effect. OI pinning at OPEX: falsified. Only options-INDUCED flows in the underlying remain open.
- **Flows / structure:** leveraged-ETF rebalancing, vol-target/CTA proxies, VIX roll, VIX term structure, ETF
  premium/discount and creation/redemption (SPY, bond SPDRs), CFTC COT positioning, futures cash-basis, futures roll (ES/NQ
  decayed since 2021), physical delivery/FND, Treasury auction concession, month-end 60/40 rebalancing, repo stress,
  FINRA margin debt, FINRA ATS venue mix, 13F crowding, closing-auction imbalance.
- **Data sources already mined:** Wikipedia pageviews, FinBERT/NLP on filings and news, Reddit, IBES, OptionMetrics IV/skew,
  short interest, TRACE bond->stock lead, crypto funding/basis/unlocks/listings/depegs.

**Alive (context, do not re-propose):** overnight loser bounce, IBS reversal on ETFs (small), overnight momentum (forward test),
preferred-stock and baby-bond ex-dividend auction trade (Roth), closed-end fund discount reversion, Treasury month-end
duration extension (small), insider purchases (small, conditional).

## 3. Where to search (go far beyond the English web)

Search each of these deliberately; log which you reached and which you could not.

**Academic, English:** SSRN (sort by newest, 2023-2026), NBER, arXiv q-fin, RePEc/IDEAS, Google Scholar "cited by" chains,
journals (JF, JFE, RFS, JFQA, Review of Finance, JFM, Journal of Portfolio Management, Financial Analysts Journal), AFA/WFA/EFA
conference programs, PhD theses (ProQuest, university repositories, job-market papers).

**Academic and practitioner, non-US** (search in the native language, translate the key findings):
- China: CNKI, Wanfang, 经济研究/金融研究/管理世界; broker research (中金, 华泰, 国泰君安 金融工程 reports); JoinQuant, BigQuant,
  RiceQuant, Xueqiu, Zhihu quant columns. A-share limit-up/limit-down, T+1, retail-dominated microstructure research often
  documents effects that also exist in US small caps.
- Japan: J-STAGE, CiNii, Japan Exchange Group working papers, Nikkei, Japanese retail boards; TOPIX rebalancing, BoJ ETF flows.
- Korea: KCI, RISS, KRX research; retail-heavy market studies.
- Taiwan, Hong Kong, Singapore, India (IIM working papers, NSE research), Brazil (SciELO, B3), Russia (eLibrary.ru,
  CyberLeninka, smart-lab.ru), Germany (Bundesbank, wallstreet-online), France (HAL), Nordics, Israel, Australia (ASX, SIRCA).
- Central banks and supranationals: BIS, ECB, Fed (FEDS notes, Liberty Street), Bank of England staff papers, IMF.

**Regulators and market plumbing (primary sources for forced, scheduled flows):** SEC (SR- rule filings for new products and
auction changes, staff reports, risk alerts, litigation releases), FINRA (regulatory notices, research), CFTC, OCC, DTCC,
NSCC, Cboe/Nasdaq/NYSE/IEX trader updates and rule changes, ESMA, FCA, IOSCO. Fund prospectuses and SAIs for products with
mechanical trading schedules (buffer/defined-outcome ETFs, option-income ETFs, single-stock leveraged ETFs, target-date and
managed-volatility funds, tokenized-equity programs), N-PORT and N-CEN filings.

**Practitioner and community:** Quantpedia (newest entries), Alpha Architect, Robot Wealth, Flirting with Models, Return
Stacked, QuantConnect and Quantopian archives, Wilmott, Elite Trader, Nuclear Phynance, r/algotrading, r/quant,
r/thetagang, usethinkscript.com, TradingView scripts with published track records, GitHub repos with backtests, Substack
quant newsletters, X/Twitter quant accounts.

**Non-text media:** conference talks (QuantMinds, Battle of the Quants, CFA Institute, Cboe RMC, Imperial/Oxford quant
events), YouTube lectures, podcasts (Top Traders Unplugged, Flirting with Models, Chat With Traders, Odd Lots, Excess
Returns): use transcripts. Patents (Google Patents, CNIPA, JPO) for trading methods that describe mechanical flows. Court
filings and enforcement actions, as evidence of which flows are predictable and who is forced to trade (never as a recipe).

**Excluded:** dark web/Tor, leaked or stolen data, paid-signal groups, anything that would mean trading on material
nonpublic information, front-running a client, or manipulating a price. Report nothing from such sources.

## 4. What to look for (priority order)

1. **Forced or scheduled flows created by products and rules that are new since ~2020**, where the forced party is named:
   buffer-ETF resets and hedge rolls, option-income ETF option writing and NAV-erosion distributions, single-stock leveraged
   ETF close rebalancing, 0DTE dealer hedging in single stocks, tokenized-stock weekend price discovery vs Monday open,
   23/5 overnight-session liquidity, crypto ETF creation flows, new index families and their reconstitution dates,
   retirement-plan payroll flows, the June 2026 margin-rule change.
2. **Effects with out-of-sample survival after publication** (post-publication papers, replications such as Jensen-Kelly-
   Pedersen, Chen-Zimmermann open-source asset pricing, McLean-Pontiff decay), restricted to ones a long-only or Roth account
   can hold, preferably in small/illiquid names where capacity protects them.
3. **Mechanisms documented in non-US markets** that have a US analogue nobody has tested (e.g., retail-heavy microstructure
   effects in China/Korea/India; Japanese and Taiwanese ETF flow studies; European auction design).
4. **Small-account-only opportunities:** per-holder caps, odd lots, thin auctions, retail-priority allocations, DRIP
   discounts, broker programs, tax-advantaged Roth-only trades.
5. Market-structure changes in 2025-2026 (auction rules, tick-size regime, 23/5, settlement) that create new, temporary
   inefficiencies.

## 5. Method

- For each source class, run many queries: synonyms, the mechanism's name in the native language, author names, product
  tickers. Snowball: references, then papers citing them. Aim for hundreds of sources screened, not dozens.
- For every claim record: URL, title, author, date, language, market, sample period, whether the sample is before or after
  publication, net-of-cost evidence, and a short verbatim quote of the key number.
- **Never invent a citation, number or URL.** If you can't open a source, mark it UNVERIFIED and say why. Prefer primary
  sources over summaries.
- Dedupe against section 2 before ranking. If an idea is a dead item in a new costume, list it under "rejected: duplicate".

## 6. Output

1. **Coverage log:** each source class -> reached / partially / blocked, with the number of items screened.
2. **Ranked shortlist (max 15)**, one card each:
   name; mechanism; who is forced to trade or who pays and why it persists; markets/period where documented; post-
   publication or out-of-sample evidence; ceiling arithmetic at $2k/$10k/$25k; capacity and why small size helps; account
   fit (taxable/Roth, long/short); data needed to test it and whether it is free; the cheapest test that would kill it;
   a falsifiable prediction; sources (with quotes); confidence and the biggest reason it may fail.
3. **Rejected with reasons** (duplicates of section 2, ceiling too small, effect in the untradable gap, not accessible).
4. **Open questions** a human must decide (data purchases, new account types).

Be skeptical: most published effects are smaller out of sample and vanish after costs. A short list of well-sourced,
gate-clearing candidates is worth more than a long list of interesting ideas.
