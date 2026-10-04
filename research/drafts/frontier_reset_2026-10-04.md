# Frontier reset (2026-10-04, after the options hunt): mechanisms, not variants

Program N = 809 (806 after T5L + Study NX's three, registered in parallel by another session). No tests run in this
cycle: mechanism + data-feasibility only (three read-only research agents; every data source below was QUERIED, not
assumed). Classes: VALIDATED / PROMISING / DATA-LIMITED / TESTED-AND-REJECTED. Missing data is never a negative.

## Permanent verdicts carried in
- **Options strategy search: CLOSED.** 12 judged variants dead at executable NBBO (T1-T7, T5L). T5 earnings fly: the
  +20% of risk mid-to-mid was a midpoint/liquidity illusion; on liquid names (>= $1B/day) judged on untouched 2016-22 at
  far-side fills it is **-3.4% of risk/trade**, 5 of 6 gates failed; mid +3.3% < ~3.7% round-trip spread; the residue is
  ordinary short volatility. Reopen options only for an options-INDUCED flow in the underlying (dealer gamma etc.).
- **Execution: true live cost ~0bp** (130 fills = auction prints). Cleanup item (separate, not this cycle):
  `slippage_bps` measures ref->auction drift; `digest.py:256/264` shows that drift as "open-sell cost" in the 1.3x
  re-arm text. Fix list `research/drafts/audit_execution_1002.md`.

## Mechanism ledger
| # | mechanism | forced party / why | arbitrage constraint | observable before the move? | data (verified) | magnitude (post-haircut) | capacity / execution | class |
|---|---|---|---|---|---|---|---|---|
| 1a | Fallen angels: bond price pressure | insurers (NAIC RBC), IG mandates, IG index exit at month-end | thin dealer balance sheets, slow HY capital, no bond lending | downgrade day, ~30d lead to index exit | no free PIT ratings; FINRA TRACE API 401 (free signup likely, unverified); VanEck ANGL 302; iShares FALN CSV not scriptable | 3-6% pressure in literature, partly reverts | bonds at $1k lots, 1-2% markups: not executable retail | DATA-LIMITED + execution-blocked |
| 1b | Fallen angels: issuer equity | weak link (sellers hold bonds) | - | yes | same rating gap | literature: drift, not reversal | stock tradable | DATA-LIMITED, low prior |
| 2a | ETF premium/discount in bond/intl ETFs (stress) | APs create/redeem only at NAV; stale matrix NAVs | AP balance sheets, illiquid underlying | close vs same-day NAV (published evening) | **SSGA navhist xlsx WORKS** (daily NAV + shares out: SPY 5,902 rows, JNK 2007-2026); iShares/VanEck/Invesco not scriptable; Yahoo iNAV no history | few %/yr, episodic | ETF tradable both accounts; long discounts only in Roth | DATA-LIMITED, acquirable ($0, SPDR) |
| 2b | ETF month-end index-rebalance flow | index ETFs must trade the rebalance | schedule public | yes (calendar) | SSGA shares-outstanding history | unknown | ETF | DATA-LIMITED, acquirable |
| 2c | LETF creation/rebalance flow | LETF daily rebalance | - | - | - | - | - | TESTED-AND-REJECTED (Q3, Lab-BK) |
| 2d | Crypto-ETF creations / heartbeats | APs, tax heartbeats | - | not before the move | - | - | - | DATA-LIMITED |
| 3a | Borrow fee / HTB / lending spikes | shorts facing fee spikes / no borrow | no borrow | only on paid feeds | no free fee history (Ortex/S3/IBKR); IBKR shortstock = forward-only, needs account | - | long side small, micro names | DATA-LIMITED |
| 3b | Recall / record-date / proxy-vote forced cover | shorts recalled for votes, specials | must re-borrow | record dates weeks ahead (DEF14A) | no recall data | < 1% | small | DATA-LIMITED, low prior |
| 4 | Margin / deleveraging cascades | margin calls, vol-target/CTA/risk-parity, PB hikes | forced timing | vol-target need forecastable; exchange margin notices are the real lead (CME 403); FINRA margin stats monthly, 1-month lag; COT weekly | - | - | price-proxy versions overlap IBS/night | price proxies TESTED-AND-REJECTED (LETF/vol-target flows, crowded-day night); true triggers DATA-LIMITED |
| 5a | **Reg SHO threshold close-out (T+13 forced buy)** | clearing members with persistent fails must buy | no borrow in threshold names | **YES now: daily lists verified free** (Nasdaq `nasdaqthYYYYMMDD.txt` 2007+; NYSE family JSON 2012+; Cboe unresolved). Overturns part 2's "FTD ~20 days late" for timing | as left | small, micro-float | < $100k/name, long only | **PROMISING (timing); payoff side unresolved** |
| 5b | T+1 / ex-div fails / CNS buy-ins | same | same | rides on 5a + cached FTD | - | - | - | DATA-LIMITED |
| 6a | **Signed dealer gamma -> underlying (last 30 min / pin)** | short-gamma dealers hedge with the move | dealer mandates, inventory limits | prior-close OI by strike | Databento OPRA `statistics` (OI) + `definition`, 2013+, ~$180/yr SPY+QQQ; no free OI-by-strike (OCC totals only). Add. 35 tested only the CALENDAR (OPEX), never signed GEX | +0-2pp/yr as a noise-leg gate (literature) | underlying, any size | DATA-LIMITED (paid, cheap); the one untouched source |
| 6b | Treasury auction concession (Lou-Yan-Zhang RFS 2013) | primary dealers warehouse supply | dealer balance sheets | auction calendar, weeks ahead | **FiscalData API works, 1979+**; TLT/IEF bars | 1-2%/yr sleeve; decayed post-2013 | TLT/IEF, any account | PROMISING (small) |
| 6c | Government contract awards to micro-caps | not forced: unpriced revenue shock | thin names, attention | award announcement (often after hours) | **USAspending API works** | uncertain, possibly several %/event, rare | micro-caps; gap risk | DATA-LIMITED, long shot |
| 6d | 0DTE hedging flow, VIX roll/settlement, window dressing, FINRA retail flow, IPO/SPAC/rights, intl ETF overnight | | | | | | | TESTED-AND-REJECTED (add. 35 V3, Lab-BN, DS5, AY, DL7, X4) |
| 6e | Futures carry, FX carry, attention data (Trends/Wikipedia), intl single stocks | | | | partial (Cboe VX CSVs, ECB FX, Yahoo ^N225 1965+) | small or leverage | | DATA-LIMITED, low rank |
Nothing is VALIDATED. Nothing found promises an order-of-magnitude larger opportunity at $2-25k.

## Separate track: closed-end fund discounts (secondary; must not displace the search)
Literature ~2-5%/yr excess after haircut (Pontiff 1995; Patro-Piccotti-Wu 2017). Prerequisites, status:
- NAV history: **CEFConnect API works** (`/api/v3/pricinghistory/{TICKER}/All`: NAV, price, discount, WEEKLY points,
  e.g. ADX from 1996). Weekly is enough for a monthly rule.
- Survivorship: **not handled**. CEFConnect lists live funds only; merged/liquidated funds (which often close their
  discount at the exit) are missing. Needs a dead-fund list (EDGAR N-2/N-CSR filers, or the repo's DL4-DL6 CEF lists).
- Costs: 10-40bp spreads, whole shares $8-30: fine at $2-25k. Capacity: thin funds, small. OOS: not run.
Status: DATA-LIMITED (survivorship). Do not start until the main frontier has a test in flight.

## "What entire source of alpha have we not searched?"
Honest answer from this sweep: for a $2-25k US-listed account, the forced-flow catalog is close to exhausted. The two
sources that are genuinely unsearched AND acquirable are (1) **options-induced underlying flows** (signed dealer gamma,
~$180 of OPRA OI) and (2) **real-time settlement constraints** (daily threshold lists, free). Neither is expected to be
large. A substantially larger mechanism probably needs either a different asset/market access (futures, international,
bonds at institutional size) or paid data (borrow fees, PIT ratings): both are user decisions, not research ones.

## First tests, in order (each one look, pre-registered before data)
1. **Threshold-list forced buy (5a)**: build daily Nasdaq+NYSE threshold panels (free); common stock, price > $2, still
   listed on day 10; long next open -> day 13 or delisting; matched placebo; design 2008-15, judge untouched 2016-22;
   kill: median abnormal <= 0, t < 2, or < 150 events. A forward daily snapshot needs a testing.py REGISTRY entry.
2. **Signed dealer gamma (6a)**: pull sample weeks first (~$2) to check format; then SPY+QQQ OI 2013-2020 (untouched);
   claim: negative GEX -> last-30-min continuation; kill: NW t < 2, wrong sign in either window, or < +1pp after 3bp.
   Needs the user's OK for ~$180 of data (credit left ~$4).
3. **ETF discount reversion (2a)** on SPDR bond/intl funds (SSGA, $0): discount <= -0.75% vs same-day NAV, next-open
   entry, 5-day hold; judge untouched 2023-26; kill: net <= 0 or t < 2 or < 30 events.
