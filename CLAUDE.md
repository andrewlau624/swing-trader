# Standing context for Claude (read before any sizing, ROI or "is it worth it" call)

## Priority: % return on the money that exists now (user, 2026-09-30)
- The user cares most about **more return on lower money**: today's balances (Schwab taxable
  ~$2.3k as of 2026-09; Roth $1-3k) and the next few years of growth (to ~$25k). Rank ideas
  by **%/yr at $2-25k** after costs, whole shares and margin rules. An edge that only pays
  at $100k+ (MNQ needs ~$29k for one contract; capacity fixes) ranks below anything that
  pays now, however large it gets later.
- Report money at **$2.3k, $10k and $25k** first. Add $100k / $500k as one line for
  capacity: say where the edge breaks (Study V: the night leg peaks by ~$250k), but do not
  let large-size scalability decide a ranking.
- Small size is an advantage to use: thin names, auctions and odd lots have no capacity
  limit at $2-25k. Whole-share rounding and the $2,000 margin / intraday minimums are the
  real small-account constraints; model them.
- Roth IRA: **$7,500/yr of new contributions is guaranteed, every year**. Model the
  Roth as a growing account (+$7.5k/yr, compounding tax-free), not a static
  $1-3k. Roth rules still apply: no shorting, limited margin, no intraday margin
  buying power.
- "Deposits beat alpha at $2k" is true in dollars and is not an argument against
  research: %/yr compounds on every deposit.

## Sessions (23/5 trading from 2026-12-06)
- The book trades only the official 09:30 / 16:00 auctions and the regular session. Take session
  times from the exchange's regular-hours calendar (`signals.regular_clock`), never from a broker
  clock or a vendor "day" (which may start at 21:00 the evening before). Label bars/fills by trade
  date (`marketdata.trade_date`). Anything new that reads a daily bar or quote open/high/low must say
  why it is regular-hours, or use regular-hours minutes (`marketdata.rth_minutes`).

## Everything being tested goes on the weekly digest (user, 2026-10-02)
- Any new shadow, watch, alert, log-only switch or forward-only weight gets an entry in
  `swingtrader/daily/testing.py` REGISTRY **in the same commit** (name, what it tests, start date, gate count,
  a one-line reader). The weekly digest's "Being tested" section and `make testing` list every entry with its
  count, what's new this week and where it stands. `tests/test_testing_registry.py` fails if a module with a
  `LOG_NAME` or a `shadow` key under `daily:` in config.yaml is not covered. When a test ends (passed and
  switched on, or killed), remove its entry in the commit that ends it.

## Research philosophy (living memory — read before proposing any new edge)

This project is ~800 pre-registered variants deep, and almost everything is dead. That is
normal; the danger now is not a lack of effort, it is **searching harder inside a local
optimum**. Read this before you add variant 801.

### The single biggest trap: the "two halves" gate is NOT out of sample
`summary`/`stats` fit 2021-23 and judge 2024-26. Both halves are **the same regime**
(the post-2020 retail/0DTE, tech-led, dip-buying-friendly market). An idea that passes
"both halves" has passed *within-regime stability*, not out-of-sample. Before trusting any
survivor, ask: **on what period was it chosen, and is there any period it has never seen?**
Prefer a period never inspected, or forward shadow, over another re-split of 2021-2026.

### What is actually established (do not re-derive)
- **IBS is durable and now genuinely OOS.** `research/sim/ibs_oos.py` re-runs the exact live
  rule on the 2016-2020 ETF series (never used to choose the rule): +29.8bp/trade OOS vs
  +21.6bp live, median-positive, beats the "every top-3" control (+9bp) and IBS>0.8
  (~0bp), and survives ex-best-5 and ex-2020 (2017-19: +14.3bp, t 2.09). The IBS leg is a
  real, simple liquidity-provision edge, not a 2021+ artifact. Output:
  `data/research/program/ibs_oos_out.txt`.
- **The night leg is the opposite.** It is the biggest raw edge and the most fragile: no
  pre-2021 data exists anywhere in the repo, and its return is concentrated in 2024+. It is
  the *least verified* live leg. Judge it on live fills only, forward; never on 2021-23.
- **The durable finds are structural / forced-flow, not prediction.** Odd-lot tenders
  (14-15/15, +5.5-6.3% median), split-off exchange offers (12/14, +7.4%), reverse-split
  round-ups, insider Form 4 (ID3/EV2), DRIP discounts, mutual-thrift conversions. These
  have a **named, constrained counterparty** and are capacity-limited in the user's favour.
- **Retail options are dead for a reason.** T3 pre-earnings straddle: mid rose +1.5% but the
  straddle's own bid-ask is ~20% of mid — the spread eats a real effect 13x over. Any
  options idea must clear a 2x-spread shock; buying premium does not.
- **Most "effects" live in the untradable gap.** S&P add/delete, 13D, PEAD, halts: the move
  is in the after-close announcement gap; the tradable window flips sign.
- **Costs:** measured live ~0bp, but on a 34-fill sample. Paper night fills are fake
  (Alpaca paper open sells ~+200bp). Never let a paper fill decide a leg.
- **The IBS premium is proportional to volatility/beta — not a free lunch.** A cross-asset
  scan of the same rule (`research/sim/ibs_xasset_scan.py`, 40 ETFs 2016-26) shows the
  premium (conditional minus unconditional open-to-open return) scales with the underlying:
  leveraged ETFs ≈ 1.98-3.3x their base ETF (SOXL/SMH 3.03, TQQQ/QQQ 3.08, UPRO/SPY 3.12),
  i.e. leverage, not new alpha. Non-equity is weak (bonds +1.7bp, commodities +1.8bp) and
  crypto majors show no consistent premium. The effect is an equity-vol liquidity premium,
  not a universal reversal.

### Assumptions to challenge (each has been wrong or unexamined)
1. That the book's Sharpe is not mostly **long-tech beta**. The IBS control shows the ETF
   basket alone earns ~8bp/day; how much of the book is alpha vs levered beta has never been
   cleanly isolated. Ask "what is this long/short of?" before "what is its Sharpe?"
2. That the edges are **price-prediction** at all. The best real results here are
   contractual/forced-flow. Do not force every question into a bars-and-signals shape.
3. That **fixed thresholds are structural** (IBS<0.2, -8%, ADV>$10M). Some are fitted; test
   the mechanism, not the parameter.
4. That a **new dataset is unnecessary**. The repo's stock data is 2021+ only. Acquiring
   pre-2021 (and delisted) stock data is the highest-value infrastructure task available.

### Failure modes to check every time (in this order)
Data bug → lookahead at the close/cross → survivorship (the panel is today's listing file;
delisted losers are missing) → selection (was the rule chosen on this data?) → multiple
testing (deflate; DSR) → costs and 2-3x cost shock → is the effect a **median**, or <5
outliers? (run ex-top-5) → is it in the gap, not the trade? → is the fill passive/adversely
selected? → overlapping windows.

### Where to search outside the current design space (ranked for this user, $2-25k)
1. **Genuine out-of-sample regimes.** Pre-2021 ETF series; acquire pre-2021 stock data
   incl. delisted; 2008 / 2018Q4 / 2020 / 2022 as stress regimes.
2. **Structural / forced-flow events where small size is an advantage, not a limit**:
   odd-lot and retail-priority tenders, rights offerings, warrant exercises, going-private
   cash-outs, SPAC liquidations, Dutch auctions, thrift conversions, spin-offs. Build a
   systematic EDGAR scanner instead of one-off studies. (EDGAR needs a SEC User-Agent.)
3. **Non-US-equity and non-equity assets** with long history: international equity ETFs,
   bonds, commodities, FX, crypto. More bars, different regimes, no overnight gap for
   crypto. Cheapest untapped OOS frontier.
4. **Conditioning / regimes (Level 5):** a vol or trend gate whose *purpose* is to keep the
   legs alive in bad regimes (add. 18 slow bear still breaks the book). Test as a
   pre-registered rule, not tuned thresholds.
5. **Information asymmetry beyond Form 4** — but first check whether the effect is in the
   gap, which kills almost all of it.
6. Only then, and only selling structures with a defensible edge-to-spread.

### Large edge vs small improvement
A large edge here would have: a **named, constrained counterparty who must trade**; survival
in a period/asset the rule never saw; a **median** effect, not a mean carried by outliers;
survival of a 2-3x cost/spread shock; a capacity limit that explains why it persists (at
$2-25k these are advantages); and a stated prediction that could be falsified. If an idea
only raises Sharpe by 0.05 inside 2021-26, it is not this. Say so and stop.

### Validation protocol (non-negotiable)
1. Pre-register in `research/drafts/round1_prose.md` (name, rule, data, gate, kill rule)
   **before** any outcome is read; bump N.
2. Judge on a period/asset never used to choose the rule; forward shadow for anything with
   orders.
3. Report both halves **and** a cost shock, ex-top-5, median and hit rate, day-clustered t,
   bootstrap/placebo, and DSR across the program's N.
4. A PASS with no economic mechanism, or one carried by <5 events, is a NO.

### Prioritized experiments (do these before anything else)
1. OOS-test the **night leg** on pre-2021 stock data (incl. delisted) — the single most
   important missing dataset. Until then treat the leg as unproven.
   **Decision (user, 2026-10-04): this is THE open question; no broad strategy hunt until it is
   answered.** The night leg is the highest-value *unresolved hypothesis*, not proven and not
   "the largest source of upside". Pre-registered as Study NX (`round1_prose.md`, N 806 -> 809):
   exact live rule, judge 2003-15, tier costs. **2016-20 is touched** (survivor-only
   `night_oos_pre2021.py` and the D3 proxy read it): report it, never judge on it.
   - Data must have: unadjusted daily OHLCV + split/dividend factors; delisted names through the
     last day with a delisting price/return; a permanent security id across ticker changes;
     security type (the live universe includes ETFs/ETNs); a real trading calendar. Plain
     historical OHLC is not enough. Vendor evaluation and decision: `LOOP_LOG.md`.
   - Until NX passes: no night-leg size-ups (losing-night x2, "moderate" 1.3x + cap .15), no
     parameter tuning on pre-2016 data. Those size-ups are judged in NX only if the primary passes.
   - If NX FAILS: record it here and in NEXT.md, then decide whether more data buying is
     justified or the book runs on the OOS-verified IBS leg (+ index exposure).
   - The 2006-15 insider study (H-POOL, N 796) stays registered; it runs on the same purchase
     but is secondary.
   - **2026-10-04: NX NOT FUNDED (user declined the $69 purchase).** NX is registered and unrun; the
     night leg stays UNPROVEN (not failed): no size-ups, no tuning. `research/sim/nx.py` is staged for
     qualifying data if it ever appears (settle the two wording issues in LOOP_LOG first).
2. Build the **forced-flow / odd-lot EDGAR scanner** (structural, capacity-limited, where
   small accounts win).
3. Test the IBS/reversal mechanism on **non-US-equity assets** with long history.
4. Isolate the book's **beta vs alpha** (hedge/benchmark decomposition) before any sizing.

### Anti-local-optimum rules
- When a direction yields only tiny gains, that is evidence **the whole direction is
  wrong**, not that it needs more variants. Name the class and stop.
- Never test the same idea in a new costume (the repo's `MISTAKES.md` and NEXT "do-not-redo"
  table exist for this; grep both first).
- Keep a falsification near every finding; prefer experiments that kill a class of
  hypotheses over ones that produce another number.
- Record the dead ends and the audit results where the next agent will look (NEXT.md's
  do-not-redo table, `research/sim/*_out.txt`, this section) — the local optimum is built
  out of forgotten failures.

### Do not assume the current legs are the answer
The live book (IBS + night + intraday) is a local optimum, not the global one. Its Sharpe is
mostly one bet (long liquid equity/tech, timed with oversold closes). The user's real
objective is **%/yr on $2-25k**, where structural, odd-lot and forced-flow trades that no
fund can run are worth more than another 0.1 Sharpe on a $2.3k account. Search there first.

## Research memory — session "alpha frontier hunt" (2026-10-04)

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

## Research memory — session "data frontier" (2026-10-04, part 2)

The binding constraint is data access, not idea generation. This session finished the two
cheapest high-value tests and mapped what each remaining mechanism actually needs.

### Correction to prior memory
- "Pre-2021 stock data blocked: the repo has no pre-2021 stock bars anywhere" was a **cache**
  limit, not a source limit. **Alpaca serves pre-2021 stock bars (2016+), including
  inactive/delisted symbols** (verified with AAPL/TWTR/ATVI/GE; fetched into
  `data/cache/bars_pre2021/`). The night-leg OOS is therefore TESTABLE; stop calling it
  blocked. (The default `data/cache/bars` stays 2021-2026 — always fetch the old range into a
  separate cache or it evicts the current one.)

### PHASE 1 results
1. **Night-leg OOS 2016-2020** (`research/sim/night_oos_pre2021.py`; picks
   `data/research/program/night_pre2021_picks.parquet`). Daily-bar reconstruction of the live
   rule (close/prev_close <= -8%, IBS<0.10, $5-2000, vol20>=60%, ADV>=$10M; buy close, sell
   next open); universe = the swing cache incl. ~14% inactive names. **Positive every year:**
   2016 +16.5 / 2017 +31.5 / 2018 +16.2 / 2019 +84.9 / 2020 +139.3 bp/trade; pooled +108bp
   (t 14.4), **ex-2020 +36bp (t 3.5, ex-top-5 +26.5)**. Liquid names earn MORE (+138bp) than
   illiquid (+91bp) -> not a microcap premium. The same daily-bar rule on 2021-26 = +47bp
   (t 10.2). **Conclusion: the loser-bounce is not a 2024+ artifact; it was positive
   pre-2021, and its strength tracks volatility.** Caveats: daily-bar, not the 15:40 live rule
   (optimistic ~2x); survivorship-limited (inactive included, fully-removed dead tickers not);
   no costs. **SUPERSEDED by the exact 15:40 test (part 3 below): the daily-close selection
   is optimistic; the exact rule is weak and regime-concentrated, not a stable pre-2021 edge.**
2. **Book beta/factor decomposition** (`research/sim/book_decomp.py`; out
   `data/research/program/book_decomp_out.txt`). Factors must be WINDOW-MATCHED (close-to-close
   SPY is off by a day and wipes the correlation). Night leg: alpha 7.1% (t 1.5) after TECH
   +35.7 (t 3.5) and SIZE +17.8 (t 3.1) -> weak alpha, much of it is a levered small-cap/tech
   overnight bet. IBS: alpha t 1.8, MKT beta +15.9 (t 3.3). **Noise (intraday): alpha 13.0%,
   t 3.0 — the one significant residual.** Total book: overnight SPY beta +0.31 (t 3.5).
   **The book is not pure alpha; the overnight legs are partly style/beta and the clearest
   residual alpha sits in the intraday leg.**

### PHASE 5 result (settlement / forced buy-in)
- **Reg SHO threshold close-out** (`research/sim/threshold_probe.py`). Threshold episodes
  (5+ consecutive settlement days with fails >= 0.5% of shares) 2021+: n=2241. The mandated
  close-out deadline is 13 settlement days after the first threshold day, but the SEC FTD file
  is public only ~20 days later — **the forced-buy window had already passed when the data was
  public in 2234 of 2241 episodes**. Post-publication the names keep falling (abn -2.8% at +5d,
  t -7.5), but they are by definition the unborrowable names (short side inaccessible) and the
  drift is a distress premium. **Verdict: the forced flow is real but NOT harvestable from SEC
  FTD; the timely source would be the daily exchange/OTC threshold lists, and the payoff is on
  the untradable side.** Do not re-run FTD-spike tests (jump R3-2/R3-16 dead).

### Data map — what each frontier mechanism needs
`AVAILABLE` = testable now; `TARGET` = acquire; `NO` = do not pretend we tested it.

| mechanism | required fields | depth / PIT | access / cost | status |
|---|---|---|---|---|
| Night-rule OOS incl. delisted | daily OHLCV, PIT listing | 2016+ (could go to 2016 Alpaca limit) | Alpaca SIP, keys in `.env` | **AVAILABLE** (fetched) |
| Borrow / HTB / recalls | daily borrow fee, utilization, recall notices | PIT 2015+ | IBKR API needs funded acct; Ortex/Fintel paid | **NO free history**; proxies below |
| \_ borrow proxies | bi-monthly short interest, FTD, short volume | FINRA SI free 2020+; FTD cached 2015+ | FINRA API (free), SEC FTD (cached) | **AVAILABLE**, but no fee/recall info |
| Fallen-angel forced selling | PIT issuer ratings (and/or bond spreads) | 2000s+ | ratings paid (WRDS/Compustat); TRACE bond prices partial | **TARGET**; free ratings do not exist |
| Settlement / buy-ins | daily threshold lists + FTD + shares outstanding | FTD/shares cached; threshold lists not | Nasdaq/NYSE daily lists need scraping | **TARGET** (lists); FTD+shares AVAILABLE |
| Margin-call cascades | daily + margin/borrow stats | — | none free | **NO**; price proxy only |
| Vol surface / dealer positioning | historical option chains + OI | 2013+ | Databento OPRA cbbo-1m, key in `.env`, ~$0.001/sym-day | **TARGET** (paid, cheap for targeted pulls) |
| ETF creation/redemption flows | daily shares outstanding + NAV | 2016+ | issuer sites / ETF.com, no free bulk API | **TARGET** (scrape) |

- SEC EDGAR / FTD index gives **403 without `SEC_USER_AGENT`** (absent from `.env`). Setting it
  (with the user's contact) is a one-line, user-approved change that unblocks EDGAR pulls.
- Databento was used for the options contest; historical OPRA is obtainable at low cost, so the
  vol-surface and dealer-positioning mechanisms are acquisition-feasible, not impossible.

### Remaining frontier (ranked by information gain x accessibility)
1. **Delisted-complete pre-2021 night test** (`asset_meta.json` + Alpaca 2016 bars for the
   inactive universe) — turns PHASE 1's supportive result into a decisive one.
2. **Historical option chains via Databento** (vol surface, dealer positioning) — paid but
   accessible; unlocks two mechanisms plus better options-cost modelling.
3. **Borrow-fee / HTB history** — the one named counterparty (short sellers) with no data;
   without it borrow stays a proxy game (FINRA SI / FTD / short volume).
4. **Point-in-time ratings** (fallen angels) — no free source; needs a paid vendor or a
   bond-spread/TRACE proxy.
5. **Daily threshold lists** (settlement) — scraping task; the payoff side is unborrowable.
6. **Daily ETF shares-outstanding / NAV** — scraping task; unlocks creation/redemption flows.

## Research memory — session "exact night + noise audit" (2026-10-04, part 3)

### PHASE 1 (exact): the night leg at the live 15:40 rule, pre-2021
- `research/sim/night_exact_pre2021.py` (out parquet `night_exact_pre2021.parquet`): Alpaca
  SIP MINUTE bars 2016-2020 for candidate down-days (low touched -8%), exact signal at 15:40
  (day_ret = p15:40/prev_close-1 <= -8%, IBS(15:40) < 0.10), buy the close, sell the next open.
- Result: 2016-18 **+3.0bp (t 0.25, ex-top-5 -6bp)**; 2016-19 ex-2020 +26.3bp (t 2.57);
  2020 +76.5bp; pooled +63bp. Per year: 2016 -2.1, **2017 -23.1**, 2018 +15.5, 2019 +91.9,
  2020 +76.5. **After 7.5bp/side cost: 2016-18 -12.0bp, ex-2020 +11.3bp (t 1.10).**
- **Verdict: the exact night leg does NOT have a stable pre-2021 edge. The daily-close proxy
  (+108bp) was flattering; the positive exact average is a 2019-2020 high-volatility regime
  effect. Do NOT size up the night leg; it remains unproven as durable alpha and is largely a
  vol-regime bet (consistent with the reversal premium scaling with vol).**
- Caveats: survivorship-limited (inactive names in, fully-removed dead tickers out); minute
  close as the 15:40 proxy. **This 2016-2020 window is the "touched" one: the run is exploratory.
  The formal Study NX judge is 2003-2015 on delisted-complete vendor data (round1_prose.md, N
  806->809; purchase awaiting user OK). Do not treat this run as the NX verdict.**

### PHASE 2: intraday noise residual audit
- `research/sim/noise_audit.py` (out `data/research/program/noise_audit_out.txt`). The ~13%
  residual is **NOT** a vol-targeting artifact (unlevered alpha 10.2%, t 4.29; levered 17.8%,
  t 3.93) and **NOT** an omitted market factor (QQQ beta ~0; alpha unchanged adding QQQ/IWM/UVXY;
  it is long-vol: UVXY beta +0.03-0.05, t 7-8).
- But it is **fragile**: by year the levered mean is 2016 -2.6, 2017 +2.3, 2019 +0.3, 2025 +0.1,
  2026 +2.5 bp vs 2018 +19.8, 2020 +11.1, 2022-24 +9-11bp. And **cost-dominated**: 1.65 fills/day;
  Sharpe 1.07 at 0.5bp/fill, 0.19 at 2bp, -0.94 at 4bp.
- **Verdict: the intraday residual is genuine (not an artifact) but time-unstable and entirely
  inside the execution cost; it is not a durable standalone edge at realistic flip costs.**
- Factor rule: the noise leg is intraday (open->close), night is close->open, IBS is
  open(d+1)->open(d+2). Factors MUST be window-matched; close-to-close SPY is wrong.

### PHASE 3: execution realism
- Night: entry = 16:00 close auction, exit = 09:30 open auction. Research uses 7.5bp/side; the
  OOS above is quoted both at 0 and 7.5bp/side. Live measured ~0bp but on 34 fills (too few).
- Noise: 30-min bar-close execution, ~1.65 fills/day; the edge is gone above ~1.5-2bp/fill.
  Never assume midpoint; the flip pays the spread each leg.

### PHASE 4: OPRA data status (not yet tested)
- Databento OPRA.PILLAR `statistics` (daily OPEN INTEREST, 2013+) + `definition`
  (strike/expiry/type) + `cbbo-1m` (NBBO). Verified: ~$1.75/symbol-week (SPY.OPT), ~$1.88
  (QQQ.OPT) for OI; ~$180/yr for SPY+QQQ. Key in `.env`.
- **Dealer gamma / OI concentration / expiration flows = DATA TARGET (accessible, paid).** The
  mechanism to test is a structural constraint on the UNDERLYING from options positioning, not
  another calls/puts/condor backtest.

### Frontier ledger (updated)
| mechanism | status |
|---|---|
| Night-leg durability | **weakened**: exact pre-2021 rule is ~0 outside 2019-2020 after costs; do not size up |
| Intraday noise residual | **genuine but fragile**: real alpha, cost-bound, unstable across years |
| Dealer positioning / vol surface | **TARGET** (Databento OPRA statistics; ~$180/yr SPY+QQQ) |
| Borrow / HTB / recalls | **BLOCKED** (no fee history); proxies FINRA SI (2020+) + FTD |
| Fallen angels | **TARGET** (no free PIT ratings; TRACE/bond-spread proxy) |
| ETF creation/redemption | **TARGET** (scrape shares-outstanding/NAV) |
| Margin cascades | **NO DATA** (price proxy only) |

## Research memory — session "contest hunt + T5L + execution audit" (2026-10-04, part 4)

### Options hunt: CLOSED for this account (N 791 -> 806)
- 12 judged option variants, every one dead at executable (far-side) NBBO from Databento OPRA cbbo-1m:
  QQQ 0DTE on the noise signal (T1a-c, T2a: -5..-15% of risk/trade, the underlying signal is only +2.6bp/trade in
  2025-26), overnight 1DTE condor/fly (T4: mid-to-mid ~0), intraday 0DTE straddle (T6: -9%), pre-earnings straddle
  (T3: mid +1.5% vs ~20% spread), insider-buy calls (T7: 23% spread at 09:35), short earnings fly (T5, T5L).
  Studies `research/drafts/study_contest_t*.md`, `study_t5l.md`; log `contest_hunt_log.md`.
- **T5 status: DEAD.** Its +20% of risk mid-to-mid (2023-26, >= $2B) was a liquidity mirage. On liquid names
  (20d $ADV >= $1B) judged on untouched 2016-22 with far-side fills (T5L): **-3.4% of risk/trade** (median +3.0%, fat left
  tail; 2016 -15%, 2022 -13%; 4/7 years > 0). In liquid names the earnings premium is ~fairly priced (mid +3.3% of risk)
  and the round trip costs ~3.7% of risk. Do not re-test with filters (news, sector, size): no filter changes the spread.
- Rule for any future options idea: compute mid-to-mid AND far-side on the most liquid names first; a mid-only effect
  in thin chains is a quote artifact, not an edge. Retail cannot capture an option premium smaller than ~2x its spread.
- Data gotchas: the SIP minute matrices (`intra.load`, data/research/night/m1) are DIVIDEND-ADJUSTED (~2% low in 2023):
  option strikes need raw prices. The Nasdaq earnings calendar's marketCap is as-of today (look-ahead): never filter on it.
  Databento credit: ~$4 of $125 left after this session (signal-driven windowed pulls cost cents; month-wide pulls dollars).
- `swingtrader/daily/zero_dte.py` is an uncommitted, untested DRAFT (T1a live mirror); the permission classifier
  blocked editing it further. Not deployed. T1a is a measured loser: do not finish it.

### Execution audit (10-02 and all 130 live fills since 09-23): true cost ~0bp
- Every fill printed exactly at the official SIP auction price. True cost: open auction 0.0bp (n 59), close auction
  -0.2bp (n 57), intraday noise +0.4bp vs mid (n 14). The "~0bp" claim holds.
- `slippage_bps` is NOT cost: it is fill vs a decision-time ref (09:17 broker mark for night sells, prior close for IBS,
  15:40 last trade for MOC buys, the ENTRY price for noise exits), i.e. ref -> auction market drift. `digest.py:256/264`
  feeds that drift (~+43bp) into the "Overnight 1.3x" re-arm text as cost: misleading. Fix list (not done):
  `research/drafts/audit_execution_1002.md`.

### Next unexplored frontier (from `research/drafts/alpha_frontier_2026-10-04.md`)
- No candidate on the forced-flow map promises a LARGE edge at $2-25k; most of the map is already dead or done here.
- Best untested: **closed-end fund discount vs its own history** (Pontiff 1995; Patro-Piccotti-Wu 2017; ~2-5%/yr over
  PCEF after haircut, long-only, Roth-friendly), with arms for CEF December tax-loss selling and CEF rights offerings;
  then the **dividend-month premium** (Hartzmark-Solomon 2013, Roth). Blocker for CEFs: free daily NAV history 2016+.
- Conflicts with the part-3 ledger above, not resolved: that ledger lists fallen angels and ETF creation/redemption as
  TARGETS; the part-4 survey dropped both (dealer markups 1-2% on $1k bonds; no free consolidated ETF NAV history).
  Dealer gamma/OI (part 3, paid OPRA statistics) is a different question from T1-T7 (it predicts the UNDERLYING) and
  remains open.

## Research memory — FRONTIER RESET (2026-10-04, part 5) — read before proposing anything
- **Permanent: T5/T5L DEAD; generic options strategy search CLOSED** (part 4 has the numbers). Do not search for another
  T5 variation or any calls/puts/condor/fly/straddle strategy. Options reopen only for options-INDUCED underlying flows.
- **Execution cost ~0bp is established.** The digest's `slippage_bps` drift-as-cost display is a separate CLEANUP item;
  do not change live code for it inside a research cycle.
- Program N = 809 (T5L 806 + NX 807-809). N measures how hard the local neighbourhood was searched, not the space.
- Ledger with the 11-question standard and verified data: `research/drafts/frontier_reset_2026-10-04.md`.
  Classes: nothing VALIDATED; PROMISING = Reg SHO threshold forced buy (timing now observable: daily Nasdaq lists 2007+,
  NYSE JSON 2012+, free) and Treasury auction concession (small); DATA-LIMITED = fallen angels (no free PIT ratings;
  bonds not retail-executable), ETF premium/discount + rebalance (SSGA navhist works, $0), borrow/HTB/recalls (no free
  fee history), margin-cascade triggers (CME notices 403, FINRA margin monthly), signed dealer gamma (OPRA OI ~$180/yr,
  the one untouched source; add. 35 only tested the OPEX calendar); TESTED-AND-REJECTED = LETF flow, vol-target/LETF
  deleveraging proxies, 0DTE hedging timing, VIX roll, window dressing, FINRA short volume, IPO/SPAC, intl ETF overnight.
- Resolves the part-3/part-4 conflict: fallen angels and ETF creation/redemption are DATA-LIMITED (acquirable for ETFs
  via SSGA), NOT rejected.
- **CEF discounts = separate secondary track** (~2-5%/yr literature). CEFConnect `/api/v3/pricinghistory/{T}/All` gives
  weekly NAV/discount from 1996, live funds only: survivorship unhandled. Must not displace the main search.
- Honest read: no candidate found promises an order-of-magnitude larger opportunity at $2-25k. Bigger mechanisms
  likely need new market access (futures, international, institutional-size bonds) or paid data (borrow fees, PIT
  ratings): user decisions. Test order: threshold forced buy -> dealer gamma (needs ~$180 OK) -> SPDR ETF discounts.
- Keep Trader research separate from the Polymarket project (same server, different repo; never mix data or code).

## Research memory — session "OPEX pin test + NX status" (2026-10-04, part 6)
- **NX: still DATA-LIMITED, not run.** Registration frozen (commit `5be14c74`, N 806->809); the $69 Sharadar
  purchase is user-approved but no `SHARADAR_API_KEY` is in `.env` and no vendor data is on disk. Do not fabricate;
  run the day-1 checks and NX once when the key exists. 2016-20 stays exploratory.
- **Options-induced underlying flow — cheapest variant TESTED and FALSIFIED.** `research/sim/opex_pin.py`
  (pre-reg `study_A_opex_pin.md`): SPY monthly OPEX 2023-24, max-OI strike within +/-3% of prior close, open->close.
  K1 (max-OI) hit 43%, net -8.4bp (t -0.51); K2 (2nd-OI placebo) hit 55%, +19.5bp. **OI-concentration/pin is
  rejected**; do not re-run OI pinning. **Signed dealer gamma (OI x gamma) is still untested (DATA-TARGET).**
- **Frontier statuses:** ETF create/redeem DATA-LIMITED (no free bulk shares/NAV); fallen angels DATA-LIMITED (FRED
  aggregate only, no free PIT ratings); borrow/HTB BLOCKED; threshold-list forced buy still PROMISING (free daily
  lists) and is the top free test; signed gamma is the top paid test. OPRA `statistics` observed ~$0.36-0.37/day
  (the reset doc's "~$4 left" is stale).
- **Strongest negative result this cycle:** the OPEX OI-pinning falsification. **No new mechanism discovered; the
  frontier did not materially change** beyond closing the OI-pinning branch.

## Treasury frontier (2026-10-04, Study TME)
- **Treasury auction concession: KILLED** (Study TAC 2016-26: dip real, no tradable bounce, +2.4bp t 0.9). No variants.
- **Treasury month-end duration extension: VALIDATED on untouched 2002-15** (pre-reg 003e176, one look): TLT
  close(T-3) -> close(T), +32bp/month net, t 2.76, 13/14 years, duration-monotonic (TLT > IEF > SHY), move on T-1/T.
  The program's first non-equity, untouched-window pass. Real and scalable, but ~+4%/yr on deployed capital: small
  dollars at $2-25k. Not deployed. Stop Treasury variants; scaling it (leverage over 3 sessions) is the only open
  Treasury question. Russell Dec-2026 and signed dealer gamma are forward-shadow SPECS only
  (`research/drafts/shadow_*.md`); no paid data.
- **Month-end 60/40 rebalancing (Study RB6040, 2002-15): ARTIFACT.** The registered abnormal-return statistic was
  inflated by its own benchmark (other sessions of the month = the signal's inputs; 69% of the effect). Executable
  spread +27bp net, t 1.2, gone after 2015. Rule for all future studies: gate on executable raw P&L; never benchmark an
  event window against sessions that define the signal. No more month-end variants.

## Research-priority gate (user, 2026-10-04): reject low-ceiling ideas BEFORE any backtest
Target = 2x the book. The live book's realistic forward return is ~8-15%/yr pre-tax (T0L: 23.7% at tier_hi 2021-26,
11% edge-halves, 16.8% 2016-20 holdout, night leg unproven), so a candidate needs a plausible path to **+8-15pp/yr
on the whole account, independent of the book**. Before writing code, write down:
`ceiling %/yr = events per year x net edge per event x share of account deployable per event x capture rate`
at $2.3k / $10k / $25k / $100k, plus who pays, why it persists, independence and the cheapest kill test.
**Kill before testing if the ceiling at $10k is < +8pp/yr under honest capture (<= 50% of the published effect).**
Shapes that can clear it: daily frequency x >= 15bp net x >= 50% of capital (the night-leg shape); ~monthly x >= 2% x
~100%; rare events x >= 10-20% with a per-holder cap that small accounts fill (the contract-payoff shape). Shapes that
cannot: deep-market calendar effects (TME: 12 x 35bp x 100% = 4%/yr), event signals deploying a sliver of capital
(insider-day ~0.5%/yr), anything whose edge is < 5x its round-trip cost.
- **CPC (2026-10-04): FORWARD VALIDATION ACTIVE, personal-scale only.** UMH is HOLD-ONLY and excluded from clean CPC
  accounting (the plan prohibits the hedge/flip that captures the discount). Remaining CPC (split-offs, odd-lot
  tenders, round-ups) sits near the +8pp gate (~+8.4pp at $10k historically): an active hypothesis, not validated.
  Ledger `swingtrader/daily/cpc_ledger.py`; no new CPC families, no issuer-plan search, no positions opened for data.
