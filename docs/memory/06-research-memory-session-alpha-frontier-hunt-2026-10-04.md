# Research memory — session "alpha frontier hunt" (2026-10-04)

Trader state: Round 33+ of swing-trader (N≈803 with the options contest). Discovery statuses
below are the point of this section; do not re-open a REJECTED row without new data.

**Project boundary (2026-10-04 correction).** Prediction-market / Kalshi research was
introduced into this repo during a cross-project contamination event. It is preserved, clearly
marked as foreign, in `research/drafts/FOREIGN_prediction_market_context.md`. It is **not** part
of the Trader's validated research universe and must not be treated as Trader evidence, ranked
as a Trader edge, or used to set Trader priorities. Relevant work belongs to the separate
Polymarket project. Never import a conclusion from another project unless the user explicitly
asks to investigate it here.

### New evidence from this session
- **Cross-asset scan (`research/sim/ibs_xasset_scan.py`, out `data/research/program/ibs_xasset_out.txt`), 40 ETFs 2016-26.**
  The IBS<0.2 reversal premium is +9.8bp pooled US equity, +44.6bp leveraged equity, +3.8bp intl
  equity, +1.8bp commodities, +1.7bp bonds, -1.4bp inverse/vol. Leveraged prem ≈ 3x base
  (leverage, not alpha). Crypto majors (12 symbols 2021+, `crypto_daily.parquet`) show no
  consistent premium (t<1.3, mixed signs) but the sample is in-sample/survivorship-flattered.
  **Conclusion:** the mechanism is an equity-vol liquidity premium; it does not extend to a new
  asset class, and leveraged ETFs add only leverage. Do not chase cross-asset IBS as new alpha.
- **Forced-flow / odd-lot, attacked.** `study_oddlot_tenders.md`: the strict subset (odd-lot
  priority + guaranteed floor >= +1% over entry) is 14 deals/10yr, mean +12.1% / median +5.5%,
  100% >0, **but only ~$149/deal, ~$150-200/yr, and the tender is a MANUAL Schwab election —
  the bot cannot do it.** Split-offs ~1.4/yr, long parent beta; reverse-split round-ups ~$370/yr
  IF Schwab rounds up (unverified). `study_goal_g1.md`: the whole complex is +20.5pp after tax at
  $2.3k, +8.8pp at $10k, ~0 above (99-share cap counts across ALL accounts). **Verdict:** real,
  small-account-meaningful, NOT scalable, and partly operational — not a new edge engine.

### Direction ledger
| direction | status | evidence / why |
|---|---|---|
| IBS close-in-range reversal (equity) | **explored, durable** | OOS 2016-20 +29.8bp (prior session); vol/beta-proportional this session |
| Cross-asset / crypto IBS | **rejected** | `ibs_xasset_scan.py`: non-equity weak, no new class |
| Leveraged-ETF IBS as extra edge | **rejected** | prem ≈ 3x base = leverage only |
| Odd-lot tenders | **partial / operational** | pays, but manual election, ~$150-200/yr |
| Split-offs, reverse-split round-ups | **partial / operational** | G1 ceiling; B1 depends on Schwab rounding |
| Event/forced-flow via EDGAR (buybacks/ASR, 13D/13G, S-8, 25-NSE, dividends/spin-offs) | **rejected** | goal_log + runbook_notes: effect in the gap or ~0; ASR t 0.27 |
| Insider Form 4 (ID3/EV2, G2-F) | **promising, forward-only** | only live event edge; gate = 60 forward EV2-big trades |
| G45 activist 13D on CEFs | **promising but too small** | +2-3.6%/60d vs PCEF, but +3.4%/yr at book level; G45-F forward watcher |
| Options (0DTE, straddles, overlays) | **rejected at retail** | T1-T7 dead; spread ~20% of mid eats the mid-to-mid effect |
| Pre-2021 stock data / night-leg OOS | **tested, supportive** | Alpaca serves 2016+; night rule positive every pre-2021 year (+36bp ex-2020); see PHASE 1 below |
| Delisted tokens / pre-2021 crypto | **blocked by data** | `crypto_daily.parquet` is majors-only 2021+ |
| Borrow / stock-loan / HTB fees | **blocked by data; untested** | named counterparty = short sellers; needs borrow-rate history |
| Fallen-angel / bond-downgrade forced selling | **blocked by data; UNEXPLORED** | needs ratings history; no Trader test exists |
| Fails-to-deliver (FTD) spikes / collapses | **rejected** | jump R3-2/R3-16 explored-dead (P 0.13/0.15) |
| 10b5-1 plan adoptions | **rejected** | I33 killed: sell plans unusable long-only, buy plans rare |

### Highest-priority next Trader experiments (in order)
1. **Delisted-complete night-leg OOS** (pre-2021, fully-removed tickers). PHASE 1 gave
   supportive pre-2021 evidence; completing the delisted universe makes it decisive.
2. **Isolate the book's beta vs alpha** (hedge/benchmark decomposition) before any sizing call.
3. **Borrow / fully-paid lending revenue** (Schwab/IBKR stock-yield programs): collect the
   hard-to-borrow fee as the counterparty to short sellers. Data-blocked (no borrow-rate
   history); the untested sub-idea is short-interest x an announced buyback (discovery I25).
4. **Fallen-angel / bond-downgrade forced selling**: IG index funds must sell on downgrade;
   equities/ETFs of affected issuers may overshoot. Data-blocked (needs point-in-time ratings).

### Genuinely unexplored Trader mechanisms (search map)
Statuses reflect the existing memory (NEXT.md do-not-redo table + goal_log + RESULTS). Only
rows marked UNEXPLORED are open ground; do not re-open a REJECTED row without new data.

| mechanism | Trader status | note |
|---|---|---|
| Forced institutional flows | partial | index add/delete (gap), pension/window-dressing, tax-loss/Dec, LETF/vol-target all dead; **margin-call cascade UNEXPLORED** |
| Fund rebalancing | rejected | LETF, target-date/vol-target, month-end (dead/borderline) |
| Index mechanics | mostly dead | S&P add/delete in the gap; Russell untestable (no membership); RSP/SCHD/small-index killed |
| ETF creation / redemption, fund flows | **blocked by data** | needs daily shares-outstanding/NAV; LETF flow dead |
| Options dealer positioning (gamma/GEX) | **blocked / partial** | OPEX timing + 0DTE VRP dead, barrier hedge (G7) killed; no historical chains |
| Volatility surface (skew, term structure) | **UNEXPLORED** | only put-write / iron condor tested (dead); needs options data |
| Borrow / short constraints | **blocked / partial** | FINRA short-volume and days-to-cover tilts dead; borrow fees/recalls no data |
| Corporate actions | extensively explored | splits/round-ups/split-offs/tenders/warrants/buybacks/spin-offs tiny or in gap; rights offerings small/manual |
| Settlement mechanics (buy-ins, T+1, cycle) | **UNEXPLORED** | FTD spikes/collapses rejected (jump R3-2/R3-16) |
| Tax-driven flows | largely explored | turn-of-year/Dec tilt dead holdout; wash-sale bounce dead; January effect not isolated |
| Passive / index flows | = index mechanics | dead / blocked |
| Issuance / redemption mechanics | rejected | ATM programs, follow-ons, IPO access, convert pricing-day, SPAC redemptions dead/parked |
| Insider information timing | heavily explored | Form 4 ID3/EV2 promising (forward-only); 10b5-1 adoptions, Form 144, 13D dead/gap |
| Alternative data | partial | LLM news shadow; reddit tested; no other alt data in repo |
| Cross-asset lead/lag | rejected / weak | ETF pairs dead; cross-asset IBS weak (this session); single-country ETFs untested |
| Cross-venue relationships | not accessible | single broker |
| Execution / microstructure | dead / blocked | closing-auction imbalance dead (paid); open imbalance underpowered; no historical L1 |
| Liquidity provision | = IBS | durable but small; retail options MM not accessible |
| Participant-specific constraints | partial | odd-lot tenders, thrift conversions, BDC/CEF tenders — small/manual |
| Information before price data | partial | EDGAR acceptance-time dead (G12) |
| Structural institutional rules | partial | reverse-split round-ups, DRIP discounts, odd-lot priority |

### What this session did NOT establish
No new materially larger Trader edge. The three genuinely-new Trader tests — cross-asset IBS,
leveraged-ETF IBS, crypto IBS — either failed to generalize or reduce to leverage; the
odd-lot/forced-flow complex is real but small/manual/non-scalable. The Trader is **not**
exhausted: the search map above still has open, data-obtainable ground (margin-call cascades,
borrow/lending, fallen angels, settlement mechanics, the volatility surface). Acquiring the
data for those is the priority, not another IBS variant.
