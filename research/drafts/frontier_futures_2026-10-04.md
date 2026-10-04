# Futures structural-mechanism frontier memo (2026-10-04)
Research only; nothing run, nothing bought, no tracked files touched.

## A. Schwab futures access (web-verified unless flagged)
- Futures run through Charles Schwab Futures and Forex LLC on thinkorswim. Needs margin approval + $1,500 minimum (margin accounts). Source: schwab.com/futures/faqs via search snippet (page itself blocked WebFetch).
- IRA/Roth: only SEP, Roth, Traditional, Rollover IRAs; **min net liquidation $25,000**, margin + option-spread approval, **125% of initial margin**; not automatic. The "3 years derivatives experience" in market_map.md is NOT confirmed by anything I found.
- Old Bogleheads post (TD era): IRA contracts limited to /YM /ZB /NQ /ES /MYM /MNQ /M2K /MES /RTY /ZN, no futures options. May have changed; ask Schwab.
- Margins: Schwab publishes no table; read on thinkorswim Trade > Futures Trader. Schwab can raise any time without notice. MES: BrokerChooser says $530 day / $2,100 initial; MetroTrade says Schwab has no reduced day margin and uses CME ~$2,500. SOURCES CONFLICT. MNQ per BrokerChooser $760 day / $3,040 initial. Reported MES fee $11.25 (BrokerChooser; unit unclear).
- Listed on Schwab pages: /10Y micro 10-yr yield ($10/bp, tick $1, cash-settled), /MCL, /MGC, /MBT, 1 oz gold. /2YY, /5YY, /30Y, MET, M2K, MYM not confirmed on a Schwab page (ask).
- Taxable $2.3k: one MES ~ $5 x index = ~$30k+ notional (my arithmetic, index level not fetched); MNQ $61k per repo. Index micros are 13-26x leveraged on this account. Only micro yield (/10Y: DV01 $10, roughly 100 TLT shares of rate risk) and MCL/MGC/MBT are sized sensibly.
- Repo fact (NEXT.md:504): Schwab Trader API cannot place futures orders. Any futures leg = manual thinkorswim orders, forward-shadow only.
- Without futures: ETF proxies are the realistic path (TLT/IEF/TMF, SPY, LQD/HYG, USO/UNG/DBC/USCI/GLD, SVXY/VIXY). VIX ETPs and USO-type funds carry their own roll cost, so they express level exposure, not roll-flow edges.

## B. Already dead or mapped in the repo (not re-proposed)
Futures roll (ES/NQ/CL/NG; ES +1.3bp t0.14 in 2021-25; NG opposite sign), Treasury auction concession (TAC), ETF creation/redemption, VIX roll, LETF flow, vol-target proxies, window dressing, OPEX pin, THR, closing-imbalance, pre-FOMC equity drift, cross-asset IBS, SVXY contango, turn-of-month, intraday ES/NQ RV (HFT), MNQ below ~$200k.
Partly open: month-end pension rebalancing was tested ONLY as IBS sizing (add. 34 Q4: dose-response right sign every period, >+3% rel => -17bp (49 events), M3 pooled t 1.94, +0.15pp/yr, placebo 63%). Never tested standalone as an SPY-vs-bond spread, never on 2002-15.

## C. What TME teaches
Benchmark/calendar flows in the deepest market, with a named constrained participant and a date fixed years ahead, validated on an untouched window (t 2.76, 13/14 yrs, duration-monotonic) where ~800 single-stock/event variants died. Reasons: (1) flow is knowable and non-informational, price pressure partly reverts (T+1/T+2 -6/-13bp); (2) the counterparty is a dealer/liquidity provider, not an informed trader; (3) one hypothesis, one look, no tuning. The effect is small per trade (+4%/yr on deployed capital) because deep markets pay small but real concessions. Implication: look for more deep-market benchmark rebalances, not more exotic ones. Caveat: n=1 validation; ex-best-5 t 1.91.
New fact: Bloomberg Agg moved its strike time 3pm -> 4pm ET on 2021-01-14 (NY Fed, Liberty Street, Sept 2026, "Treasury trading at the close": month-end trading shifted from ~3pm to ~4pm). That is a free natural experiment on TME's mechanism.

## D. Candidates (ranked by P(new alpha) x $ impact at $2-25k / research cost)

### 1. Month-end cross-asset rebalancing spread (Harvey-Mazzoleni-Melone, NBER 33554, rev Jan 2026) + TME timing test
- Who/why/when: 60/40-type pensions, balanced and target-risk funds; calendar rebalance on last business day, "predictability peaks in last four days"; threshold rebalance intramonth. Signal = simulated 60/40 drift from MTD equity-minus-bond return.
- Why not arbitraged: trades are non-informational but sized in the $16bn/yr range (~8bp/yr cost to investors); capital that could trade against it is sitting in dealer balance sheets; reverts within 2 weeks.
- Magnitude: one signal unit = -16/-17bp S&P next day, +4/+2bp 10y note; S&P-vs-ZN long/short Sharpe >1, 1997-09 to 2023-03 (6,223 days). Repo 2016-26 replication of sign and size (-17bp, 49 events) exists as a sizing test. Practitioner 9.9%/yr is unconfirmed. Published 2025, so McLean-Pontiff style ~half decay is the prior.
- Instrument: SPY/QQQ vs TLT/IEF (taxable can short SPY; Roth: long-only, hold TLT/IEF when equity overweight, hold SPY when equity underweight). Futures (ES/ZN) only for the 1997-2002 pre-ETF window.
- Data: free. Alpaca/Yahoo ETF daily 2002+; Databento ES/ZN individual contracts ~$0.02/root-year if you want 1997+. Untouched window in repo: 2002-15 (add. 34 used 2016-26).
- Cheapest kill: registered rule from add. 34 (signal from MTD SPY-TLT), standalone, 2002-15, 3-day month-end window, spread return vs placebo of random 3-day windows; kill if net < +10bp/window or placebo > 90th pct fails. Add the TME timing split: 3pm vs 4pm strike (pre/post 2021-01-14) on TLT minute bars already in data/research/night/m1 (2016+; the post-2021 half is a clean test that flow moved to 4pm).
- Artifact: continuous-contract splice (ZN/TY first notice ~ end of Feb/May/Aug/Nov falls IN the month-end window; use ETFs or explicit contracts, never Yahoo ZN=F); dividend adjustment on ETFs; overlap with TME (same bond leg, same days) so incremental value must be measured conditional on TME.
- Capacity: $B. Frequency: ~12 windows/yr. Independence: equity leg independent of book; bond leg correlated with TME (treat as one month-end sleeve). EV: P(real, positive after costs) ~35%; $ impact small standalone (~1-3%/yr deployed) but it is the natural size/timing amplifier for TME.

### 2. Month-end index-extension analogs in other benchmark bonds (adjacent, not futures)
- Same mechanism as TME for credit/TIPS/MBS: LQD/HYG/TIP/MBB/AGG excess over duration-matched Treasury ETF on last 3 sessions. Data free (ETFs 2002-2007+). Kill: TME rule verbatim on each, one look 2003-15. Risk: credit beta confounds (use IEF/TLT hedge), thinner ETFs. P ~20%; magnitude <= TME; independent of the book but correlated with TME via rates.

### 3. CFTC hedging-pressure / positioning (Basu-Miffre 2013; Fan et al. extend to equity and FX futures)
- Who: commercial hedgers must transfer risk; speculators earn premium. Signal = 12-month net hedger/speculator open interest from COT. Long-short commodity Sharpe above long-only; ties to roll yield and momentum only weakly.
- Decay: no post-2013 test found; generic post-publication decay ~58% (McLean-Pontiff). RBA 2016: oil risk premia declined with financialization.
- Instrument: no clean ETF expression; DBC/USCI/PDBC single-basket, GLD/SLV/USO/UNG/CORN/WEAT/SOYB individually (ETF roll-yield and USO/UNG tracking error contaminate).
- Data: CFTC COT free (legacy 1986+, disaggregated 2006+; Tuesday data released Friday, so signal lags). Prices: Databento GLBX 2010+ only; Yahoo =F front-month 2000+ with roll gaps.
- Kill: sign + t on 2010-2025 cross-section with Friday-release lag, monthly rebalance. Low frequency, low t power (15 yrs). P ~12%, impact 2-4%/yr on small basket. Independent. Low priority.

### 4. Treasury micro-yield futures as the capital-light vehicle for TME (leverage/tax, not alpha)
- /10Y micro yield: $10/bp; ~one contract of rates risk ~ 100 TLT shares. On $2.3k a 3-day hold needs only margin (amount UNVERIFIED, read on thinkorswim), is Section 1256 (60/40), no wash sale. Rough upside from my arithmetic: TLT AR +32bp x duration scaling to /10Y exposure ~ +$15-25 per window, x12 = ~$200-300/yr, i.e. ~10% on $2.3k if margin is small; versus ~$58-96 unlevered in repo's own math. Needs IRA $25k NLV for Roth. Manual orders only (no API). Risks: single-look validation, 3-day yield sd ~12bp = ~$120 = 5% of the account, margin/CME changes. This is the only futures item that pays at $2.3k, and it is an implementation choice downstream of TME shadow evidence, not a new study.

### 5. Equity-index futures implied financing / convenience yield (D.E. Shaw "Imbalance Sheet"; CME 2025; Fleckenstein-Longstaff)
- Dealers' balance-sheet cost (+81bp to intermediary cost of capital, FL) shows up as futures financing = SOFR + convenience yield; CME: 3m convenience yield 0-110bp (avg 35.5bp, Feb 2024-Mar 2025), spiked Dec 2024. Quarter/year-end spikes recur.
- Cannot be harvested at $2.3k (arbitrage = box spreads/ cash-and-carry). Only usable as a signal: financing-spread spikes as a funding-stress/leverage-demand indicator for SPY or TLT next-month return. Data: ES calendar settlements (Databento ES spreads), SOFR (FRED), dividends. P ~8%. Research cost medium. Skip unless a spare cycle.

### Dismissed with reason
- Treasury futures roll / CTD / pace-of-the-roll (CME, Quantitative Brokers 1980-2018: calendar spread mildly mean-reverting; effects are ticks, HFT-arbitraged, repo's own ES roll result decayed to ~0).
- Commodity index roll (Mou 2011: front-run Goldman roll days 5-9, 3.6%/yr cost to index holders, 2000-10): Irwin-Sanders-Yan 2023: order-flow cost $2.9bn/yr 2004-11 -> $0.47bn/yr 2012-19, spread effect gone. USO roll (Bessembinder et al.: ~25bp spread widening/roll, ~3%/yr, 2009-12 vintage; "sunshine trading" improves liquidity). Dead for new money.
- CTA/trend crowding: arXiv 2607.01550 (2026): short-term trend demise tied to HFT market-makers refusing CTA flow; crowding story contradicted; 3-12m TSMOM persists but is not a forced-flow edge.
- Pre-FOMC drift: stocks faded after 2015 (Kurov-Wolfe-Gilbert) and repo shows dead in day session; Treasury version (Pan-Peng) is ~0.8bp of 10y yield, formed in Asia/London hours: <1%/yr. Ledger it, skip.
- VIX SOQ, crude delivery squeezes, price limits: rare, no small-account counterparty, no systematic calendar.
- Wrong-universe analogs of the WM/R fix (FX) and the gold fix: not reachable (no FX/ London access), benchmark reforms removed them.

## E. Data caveats
- Free daily continuous futures: Yahoo =F is front-month only with roll gaps; Stooq / Nasdaq CHRIS availability NOT verified this session (CHRIS I believe discontinued; unverified). CME site settlements are recent-only; history needs paid DataMine. Repo already uses Databento GLBX.MDP3 2010+ at ~$0.02/root-year for individual contracts. CFTC COT free and verified reachable by earlier session.
- Roll splicing is the dominant artifact for any futures test whose window touches month-end of Feb/May/Aug/Nov (Treasury) or the third Friday of Mar/Jun/Sep/Dec (equity).

## F. Recommendation for the next cycle
Month-end cross-asset rebalancing (candidate 1), one pre-registered look on ETFs 2002-15, with the 3pm-vs-4pm TME timing split as a diagnostic, then a joint month-end sleeve test (HMM signal as TME sizer) only if the standalone passes.

Sources: schwab.com/futures/faqs; schwab.com/node/38556 (micro futures list); brokerchooser Schwab MES/MNQ pages; metrotrade.com Schwab comparison; NBER w33554; CME "Quantifying and Hedging Equity Financing Risk" (2025); NBER w24224; OFR WP 21-01; FEDS 2024-039; Irwin-Sanders-Yan AEPP 2023; Bessembinder et al. CFTC oce_predatorysunshine0314; Mou 2011 (SSRN 1716841); Basu-Miffre JBF 2013; Kurov-Wolfe-Gilbert FRL 2021; Pan-Peng SSRN 4764451; NY Fed Liberty Street 2026-09 "Treasury trading at the close"; arXiv 2607.01550.
