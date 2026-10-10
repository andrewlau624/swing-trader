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

## Live data lives on the server (user, 2026-10-05: standing permission)
- `ssh him` (ihearthim@143.244.190.248, repo `~/llm-trader`, python `.venv/bin/python`) is always
  allowed for reading live state: `logs/` (daily-fills-{live,roth}.jsonl, daily-decisions*, run logs)
  and `state/`. Any live-data question (fills, costs, gates, positions) is answered from there, not the
  local checkout. Read-only by default; changing anything on the server still needs the user's OK.

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

## Research memory — session "threshold forced-buy test" (2026-10-04, part 7)

### Data-buy rule (user, permanent)
Buy research data only if **expected information value > data cost**: (1) structurally compelling
mechanism, (2) free evidence does not already weaken it, (3) experiment specified enough to
falsify it, (4) payoff materially larger than existing edges, (5) no cheaper dataset answers it.
- **Sharadar $69: DEFERRED, not rejected.** Do not purchase or request the key now; NX is
deprioritized. Apply the rule retroactively.

### Study NX: BLOCKED / LOW PRIORITY (unchanged, frozen)
Registration frozen (commit `5be14c74`, N 806->809): 2003-2015 judge, one execution, no tuning,
2016-20 exploratory. Not proven false; just not worth paid data while the night hypothesis is
already weakened. Do not edit the preregistration to make it easier to pass.

### Study THR: Reg SHO threshold forced-buy window — TESTED and REJECTED (long side)
`research/sim/threshold_flow.py` (pre-reg `study_threshold_flow.md`). FTD-derived threshold
episodes (fails >= 0.5% of shares AND >= 10k shares, 5 consecutive settlement days; same
definition as the SRO list, 2016+, all exchanges); entry at the open after the 5th day (list is
public then); deadline = +13 settlement days. Panel 2021-2026, n=1516 episodes / 647 symbols.
- **CAR to deadline: -959bp (median -1242, hit 27%, day-clustered t -6.4, ex-top-5 -1217).**
  The 3 sessions into the deadline are the WORST (-274bp) — the opposite of a forced-buy lift.
  Sub-periods both negative: 2021-23 -58bp, 2024-26 -1094bp.
- **No volume footprint** (window $vol / 20d ADV at entry = 0.54x median): no forced-buying
  signature. Split: overnight +267bp, intraday -878bp (the fall is intraday).
- **Long-only net of 50bp is -1009bp. KILL.** The forced flow is real (Rule 203(b)(3) buy-in) but
  the profitable short side is inaccessible — these names are on the list *because they are
  hard to borrow* — and the long side is a strong loser. Do not re-run threshold/FTD-buy tests.
- Data note: the useful daily list URL is `nasdaqtrader.com/dynamic/symdir/regsho/nasdaqthYYYYMMDD.txt`
  (2008+); the older `/symdir/threshold/` path 404s. FTD-derived status is equivalent and cached.

### OI-pinning / signed gamma / ranking
- **OPEX OI-pinning: permanently killed** for the tested mechanism/window (part 6).
- **Signed dealer gamma: DATA-TARGET, no purchase yet** — must compete against free tests and
  pass the data-buy rule first (state exact mechanism, direction, inputs, design, why larger
  than the killed OI-pinning effect).
- **Frontier ranking (user):** 1) threshold-list forced buy -> now TESTED-REJECTED; next free
  candidates are Treasury-auction concession and SPDR ETF discount reversion (SSGA, $0);
  2) NX BLOCKED; 3) signed gamma DATA-TARGET; 4) ETF creation/redemption DATA-LIMITED;
  5) fallen angels DATA-LIMITED; 6) borrow/HTB BLOCKED; 7) futures roll / benchmark changes /
  auction mechanics NOT SEARCHED; 8) night variants / generic options / intraday noise CLOSED.
- "Data-limited" is NOT negative evidence. No deployment.

## Research memory — session "capacity/scale frontier" (2026-10-04, part 8)

Objective shifted to **total profit-generation capacity / scaling toward 2x**, not a new standalone signal.
Two strongest free tests run first.

### Study TAC: Treasury-auction concession — REJECTED
`research/sim/tac_treasury.py` (pre-reg `study_tac_treasury.md`; FiscalData auctions 1979+, 2633 note/bond
aucions). TLT/IEF vs SPY, 2016-2026, 979 auctions (TLT 297 / IEF 682).
- Concession (A-3 -> A): -29bp (t -4.3). Reversal (A -> A+3): -16bp (t -2.6). **Executable A+1 -> A+3: +2.4bp (t 0.9).**
- The mid-window "reversal" is the auction-day move **bleeding back** (partly a stale-close day-turn artifact); it
  is gone by the next session. Both halves negative; TLT worse than IEF; not larger for high bid-to-cover.
- **Verdict: no executable post-auction reversal. The published concession effect is a pre-auction move, not a
  tradable simplification. KILL** (economically small even before costs; 2bp/gap in the right direction but t<1).
- Note: ETF bars are 2016+; the pre-2008 positive-reversal regime (Lou-Yan-Zhang) cannot be tested free here.

### Study ETC: SPY creation/redemption flow — REJECTED (no tradable flow signal)
`research/sim/etc_etf_flow.py` (pre-reg `study_etc_etf_flow.md`; SSGA navhist xlsx: daily NAV/shares out).
- **Data bug found and fixed:** `etf_daily` SPY closes are split/DIV-adjusted, so `close/NAV-1` shows a fake -15%
  "discount". The true SPY discount (raw closes vs NAV) is +/-2.7%, median +0.4bp. **Any ETF-premium study must use
  raw closes**, not the adjusted panel.
- Flow (shares-out change) -> next-day return: top creation quintile +9.3bp (t 1.5); big creation +16.8bp (t 1.7);
  big redemption +0.1bp. **Weak (t<2), not stable across years (-17bp in 2022), and ~= SPY's drift + the 1-2bp
  round trip.** Discount quintiles: premium +12.7bp, deep-discount -0.4bp (t<1).
- **Verdict: no tradable, scalable flow or discount-reversion signal in SPY. KILL** (the AP arbitrage leaves nothing
  in the most liquid ETF; a smaller/international fund would need its own NAV history, i.e. a scrape).

### Ranking after this cycle
1. **Options-induced underlying flow (signed dealer gamma) — DATA-TARGET**, no purchase (must beat the killed
   OI-pinning; see data-buy rule). Only remaining structurally-motivated, if small.
2. **Threshold-list forced buy — TESTED-REJECTED.** OI-pinning — killed. Generic options — closed. Night — do not size.
3. **DATA-LIMITED:** ETF creation/redemption (needs a per-fund raw-NAV + shares scrape, not just SPY), fallen angels,
   borrow/HTB, margin cascades.
4. **NOT SEARCHED:** futures (roll/basis/calendar), benchmark/index rebalances (no membership/PIT), auction mechanics
   beyond TAC, cross-venue/structural.
5. **Capacity audit of the live book** (execution/capital bottlenecks) — not yet done; the other lever to 2x.
- Honest read: neither free test produced a scalable edge; the local book is not the bottleneck this cycle revealed.
  Bigger capacity likely needs a new market (futures) or a per-fund NAV scrape. No deployment.

## Research memory — session "frontier ranking" (2026-10-04, part 9)

Memo: `research/drafts/memo_next_frontier_2026-10-04.md`. Ranked 9 directions; chose ONE.

- **Capacity finding (important):** the live book is NOT capital-constrained until ~$1M
  (`study_y_scale_book.md`: ~20.5%/yr at $100k, ~17.8% at $500k, ~15.9% at $1M). So the "execution
  audit → 2x" path CANNOT move total P&L at $2-25k. The real ceiling is the after-tax crossover at
  ~$250k (lever: Roth-first), not execution. Stop treating the capacity audit as a route to 2x.
- **Chosen next experiment: FUTURES roll / calendar / basis** — the "have we been in the wrong
  universe?" test. Scheduled, mechanical flow from beta/passive roll; maximal capacity; free CME
  settlement/volume + CFTC COT (verified reachable) allow a pre-purchase falsification; independent
  of the equity book.
- **Ranked frontier:** 1) futures roll/calendar — SEARCH; 2) signed dealer gamma — DATA-TARGET
  (small; must beat OI-pinning); 3) borrow/HTB/recall — DATA-LIMITED; 4) fallen angels — DATA-LIMITED;
  5) margin cascades, 6) benchmark/index rebalances, 7) auction/beyond-TAC, 8) per-fund ETF flow —
  DEPRIORITIZE; 9) retail vol-premium — KILL.
- **Lesson:** the frontier's binding constraint is universe/data, not signal generation. The two
  genuinely new spaces are futures (capacity, scheduled flows) and options-induced underlying flow
  (small). Bigger capacity = new universe, not more equity variants. No deployment; no purchase.

## Research memory — session "futures roll" (2026-10-04, part 10)

Study FUT-ROLL (`research/sim/fut_roll.py`, pre-reg `study_fut_roll.md`). Data: Databento `GLBX.MDP3`
`ohlcv-1d`, individual contracts 2011-2025 for ES/NQ/CL/NG (~$0.02/root-year; the parent also publishes
the actual calendar-spread instruments, e.g. `ESH0-ESM0`). Spread S = F1-F2, LTD = last day a contract
is front.

- **Mechanism is real in equity-index futures.** Rolling institutions vacate the front: the front
  contract's volume share falls monotonically 0.48 -> 0.37 into LTD (ES/NQ), then jumps back to ~0.59.
  Spread daily volatility in the roll window is **3-4.6x** the baseline for ES/NQ. So scheduled roll
  pressure exists and is measurable.
- **The tradable distortion is small and decaying.** Short-spread (short front/long back) into LTD:
  ES +16.6bp t 2.0 (but 2011-15 +21.9 t 1.66, 2016-20 +19.0 t 1.34, **2021-25 +1.3 t 0.14**);
  NQ +8.2bp t 0.97 (**2021-25 +3.0 t 0.16**). CL sign-unstable. NG has the **opposite** sign (-94bp).
  One-tick round trip is only ~1-6bp, so cost is not the killer — the effect itself has decayed to ~0.
- **Verdict: ARTIFACT-ADJACENT / INTERESTING, not RESEARCH.** A genuine mechanism (roll migration) with
  a real but small spread effect that has been **arbitraged away in ES/NQ since ~2021** and is
  contract-specific (NG reverses). Equity-index rolls were the right mechanism example but are now
  too crowded; commodity "roll" is carry/seasonality, not the same forced flow.
- **Spread liquidity (capacity):** the published ES calendar spread instruments trade heavily in the
  roll weeks (multi-million contracts/day on the active spreads) — capacity is NOT the constraint.
  The constraint is that the edge is gone.
- **Did futures fail, or just roll pressure?** Not settled. Roll *pressure* is arbitraged, but the
  futures universe is still largely unsearched for other structural mechanisms (settlement/SOQ,
  first-notice/warehouse flows in commodities, futures-based volatility-target/CTA repositioning,
  cross-asset basis). Recommend pivoting to those, not to more roll variants.

## Research memory — session "physical delivery / FND" (2026-10-04, part 11)

Study FND (`research/sim/fnd_physical.py`, pre-reg `study_fnd_physical.md`). Object = the nearby/deferred
calendar spread and OI/volume migration around first notice day, for physically-settled CL/NG vs the
financially-settled ES roll (part 10). Data: cached Databento GLBX individual contracts 2011-2025.

- **Physical constraint is real and observable.** CL nearby volume share collapses 0.90 -> 0.55 into FND
  then recovers to 0.91 (delivery migration). NG shows almost none (0.92-0.98; diffuse delivery).
- **But no harvestable spread distortion.** Spread (nearby - deferred) means around FND are outlier-carried:
  CL FND->+5d +206bp (t 1.5, **median +3.9**, ex-top-5 -24); NG FND->+10d -86bp (ex-top-5 -313); signs
  flip between CL and NG; every median is single-digit bp. The apparent moves are carry/convenience yield,
  seasonality (NG winter), and a few well-known squeezes (2020 negative WTI, 2021-22 gas).
- The CL migration signature is the **same shape** as the ES financial roll (part 10) that has been
  arbitraged since ~2021: visible migration is necessary but NOT sufficient for a tradable distortion.
- **Verdict: KILL (physical-settlement branch closed).** Outcome is ARTIFACT / carry-and-seasonality, not
  a physical edge; the user closed the branch 2026-10-04. **No FND variants, no more physical-settlement
  variants.** Answer to the key question: physical delivery, as expressed in the front calendar spread, is
  NOT a new harvestable inefficiency. The straddling speculator bears the same delivery risk as the
  constrained physical party, so there is no free side.
- **Next genuinely different futures mechanisms (not load-bearing roll):** futures-based
  volatility-target / CTA scheduled repositioning; settlement-auction (SOQ); cross-asset basis
  (futures vs ETF/physical). Pick one; do not re-tune roll/FND windows.

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

## Research memory — session "frontier tests + discovery" (2026-10-05)
- **Study BSPD (bond-SPDR premium/discount + creation flow, N 834 -> 835): KILL.** JNK/SJNK/SPSB/SPIB/SPLB,
  2007-12..2026-10, navhist + raw closes. Gross market-adjusted spreads ~0 (+0.32/-1.54/-1.25bp); every arm negative
  net (net_1x -6.6..-9.5bp, median ~-8, clus_t -3..-12), wrong sign, same in all sub-periods. No reversion to harvest.
  With SPY (ETC) and broad SPDRs (EF) rejected, the **ETF premium/discount + creation-flow family is CLOSED**.
- **Study DM (dividend-month clientele premium, N 835 -> 836): KILL.** Monthly payer-vs-non-payer +66.8bp (t 2.51,
  ex-top5 +31.2) passes the registered gates but is a size/value tilt (164 payers vs 3,081 smaller benchmark names);
  the ex-date mechanism test (T-5..T+5 vs SPY) is -6.9bp, median -19.7, t -0.04, and the monthly spread dies at 3x
  cost (-23.2bp). Panel 2021+ only. Hartzmark-Solomon does not survive at retail size/cost.
- **P01 EDGAR discovery layer built** (`swingtrader/daily/forced_flow_discovery.py`, REGISTRY "Forced-flow discovery
  (EDGAR forms)", `make forced-flow-discovery`): scans SC 14D-9 / DEFM14C / 425 / 8-K 2.01-5.01 / 25-NSE / S-4 /
  SC 13E3, flags per-holder-capped guaranteed-floor events to `state/forced-flow-discovery.jsonl`; discovery-only, no
  orders. Dry run 3 sessions: 85 docs, 1 candidate. The only new forward mechanism this cycle.
- **No new runnable edge. The free frontier is exhausted.** Remaining open ground is DATA-LIMITED/BLOCKED (borrow
  fees, PIT ratings, per-fund NAV) or the paid signed-gamma source, whose free proxy already failed the untouched
  2016-20 window. Do not re-open BSPD/DM/CEF-TL or the ETF-discount family without new data.

## Study NX RESULT (2026-10-06) — supersedes "night leg UNPROVEN / NX NOT FUNDED" above
- Sharadar bought direct (full bundle, 3.2GB at ~/data/sharadar; loader repo github.com/andrewlau624/sharadar-data).
  Day-1 checks all PASS. Single look: **night leg PASSES on untouched 2003-15**: +3.07bp/night at tier (t 3.13), all 3
  subperiods positive, median trade +23bp, beta-adjusted +2.1bp t 2.3. S1 (losing-night x2) and S2 (1.3x cap .15)
  pass their bars. **Small and cost-bound**: tier_hi t 1.95, 2x tier_hi negative; ~3.9%/yr of book at w .5 in 2003-15.
  Status: VALIDATED-SMALL, not "unproven". Size-ups are a user decision, only while live auction cost stays ~0bp.
  Details NEXT.md; output data/research/program/nx_out.txt. 2003-15 is now TOUCHED for the night leg: no second look.

## Research memory — session "Sharadar full bundle" (2026-10-05)
Data: full Sharadar bundle at `~/data/sharadar` (SEP stocks + SFP funds both 1997-12-31..2026-10-05, delisted included;
insiders=SF2 **2008-01-02+**; actions, sp500, fundamentals, daily, holdings), permaticker ids; loader
`github.com/andrewlau624/sharadar-data` (`from sharadar import prices, tickers, actions, table`). Daily bars only — no minute
data, so every 15:40/intraday rule is a labelled daily-close proxy. Backup at `~/Downloads/sharadar-backup/`. Program N 838 -> 839.

**Verdicts (all one-look, pre-registered in `round1_prose.md`; each adversarially checked before acceptance):**
- **SHAR-IBS (N 839): WEAK, not PASS.** The live IBS leg on the untouched 2003-15 ETF window: tier net +4.99bp, day-clustered
t 1.03 (gross +16.15bp t 3.34); halves +11.84 / -4.69; median +10.69bp; ex-best-5 +1.84bp; beta-adj SPY residual -8.58bp
t -2.89; 2/5 registered checks. **The positive gross is entirely eaten by `tier` costs (5bp/side), and the beta-adjusted
residual is negative pre-2016** (vs the +6.7bp/day 2017-20 residual in `beta_alpha_iso`). Read: the IBS liquidity premium is
real but **weak and cost-bound in the 2003-15 regime** and its pre-2016 alpha (net of beta) is not there; 2003-15 is now
TOUCHED — no IBS variants or tuning on it. (A verifier found a raw-open split bug on 2 leg-days; fixing it moved FAIL->WEAK.)
Runner `research/sim/shar_ibs.py`.
- **H-POOL on Sharadar (N 796): PASS at `tier`, NOT ROBUST.** The registered pooled insider-buy open->close rule, run
survivorship-free; SF2 starts 2008 so the judge is 2008-01..2015-12: tier +21.1bp, t 2.71, n 29,285; halves +37.2 / +10.6bp;
gross +40.2bp; **tier_hi +11.4bp t 1.46 (fails), ex-top-1% +5.4bp, DSR 0.842, decays to ~0 by 2013-15** (crisis/high-vol
tilt). Placebo 100th pct. The insider-buy family therefore transfers to a pre-2021 decade the program never saw, but only as a
conditional/crisis leg; keep it forward (ID3 shadow) and do not size up on this alone. Runner `research/sim/hpool_sharadar.py`.
- **SHAR-SURV (diagnostic): the 2021-26 night-leg results were survivorship-flattered by ~+4.1bp/trade at `tier`**
(survivor-only +18.86bp t 1.99 vs delisted-complete +14.75bp t 1.81; flat 2.5bp/side +33.95 vs +30.14). Delisted names are
24.1% of eligible but 16.0% of picks; the gap is one mis-valued -100% merger plus a 2021-23 concentration. Small but real:
quote night-leg panels as delisted-complete. Runner `research/sim/shar_surv.py`.
- **SHAR-CRASH (diagnostic, no N):** daily-bar 0.5 IBS + 0.5 night, no noise leg. 2000-02 cum +278%, maxDD **-24.07%**
(trips the -10% lever gate, not the -25% halt); 2008-09 maxDD -9.86%; 2011 -8.35%; 2015-16 -8.25%. The `-25%` halt would
never have fired in these windows; the `-10%` lever gate would have in 2000-02. Daily-close proxy is optimistic (~1.7x vs
the exact 15:40 rule per NX). Runner `research/sim/shar_crash.py`.
- **Dropped before testing (research-priority gate):** structural events (S&P 500 add/delete, spin-offs, reverse-split
round-ups) — S&P flow is in the announcement gap, spin-off effect in the distribution gap, round-ups ~$370/yr; all <
+8pp/yr at $10k. No generic fundamentals factor mining. Bounded errors found+fixed by adversarial checks: a raw-open
split bug (SHAR-IBS) and a dropped -100% delisting-outcome bug (SHAR-CRASH).
- **Net:** the bundle's new evidence does not add a new edge; it **qualifies two live legs** — IBS is weaker and
cost-bound in the oldest regime, the night leg is ~4bp/trade less good once delisting is included, and the insider-buy
family is validated-small/conditional on 2008-15. Nothing here changes live sizes; all sizing is a user decision and the
data-buy gate is vindicated (the open pre-2016 questions are now answered).

## Research memory — session "resurrection track" (2026-10-06)
- Two-track session (new frontier ~75% / resurrection ~25%). Inventory:
  `research/drafts/resurrection_inventory_2026-10-06.md`. Only ONE candidate cleared the reopen bar
  (low power, not proxies/costs/timing): the never-run seasonal-memo design (Dec tax-loss losers ->
  January reversal), upgraded from 10 Alpaca years to 28 delisted-complete Sharadar years (N 853->854).
- **TL-JAN: REJECTED AGAIN.** +2.94%/event-year t 1.91 at 25bp/side, but not monotone in YTD loss
  (terciles 2.66/1.94/3.18), 2016-25 dead (+0.53% t 0.30), pre-2016 era ex-2010/12 +1.41% t 0.88;
  June placebo clean (-0.31%). December losers: PERMANENTLY DEAD; do not re-open without a real
  sell-footprint measure (off-exchange imbalance), not another prices-only panel.
- **CLOSE-DISLOC (LOC at >=1% closing-cross dislocations, pending from the golden-egg session): REJECTED.**
  Data restored through 2026-10-01; k=1% t 1.76 ex-top-5 -11 halves flip; k=0.5% +9bp t 1.06 < bar;
  mirror loses 18bp; control -0.8bp. No re-tuning of k.
- Session meta-findings: (1) the power-objection class is now fixable for every price-only question and
  the answer keeps coming back "dead"; remaining deaths are structural. (2) The resurrection test as a
  gate worked: everything else failed "what changed?" at the first question. (3) No new edge, no
  deployment; next user decisions unchanged (signed gamma $180 OK, LETF-NIGHT forward shadow OK,
  SPLIT-T0 gate watch).
\n
## Research memory — session "domain jump: regulatory positioning" (2026-10-06, cont.)
- Answer to "what category has the program never modeled": (1) cross-instrument same-issuer relationships
  (preferred/dual-class/holdco vs common: NO convergence force / costs); (2) regulatory-mandated positioning.
  Built the first 13F-state panel ever (`f13f_agg.py` -> `data/research/f13f/agg.parquet`, 432k name-quarters,
  common-only, mxp/opp/fxp vs marketcap-implied shares, fund-name regex flag).
- **F13C-CAP (N 854->856): KILL both judged arms.** Trim (short, press = mxp>=9.5% & dsh<=-5%): +1.31%/window
  t 0.80, ex-top-5-names ~0; FREED (long after unwind prints done): -12.2%/window t -3.2 both halves.
  Reverse-split contamination only ~3%; the null is real. Participant-typed v2 (N->857): TRIM2 +0.15% t 0.08, FREED2 n 36 noise — family FINAL: no tradable footprint in daily 13F-state data.
- **Kept diagnostic:** implied shares down >=5%/q => -4.7..-5.7%/q vs SPY both halves (t -2.3..-2.8):
  dilution/death-spiral drag as a defensive avoid-screen (forward-watch), not alpha.
- 13F economics: quarterly lag + heavy overlap; a present-13F family can work only as a STATE gate on an
  existing edge, which no session has specified cleanly yet. No deployment.

## Research-process error (user correction, 2026-10-06): date-version regulatory/account constraints
- The SSR-RD economics first applied the old PDT rule ("< $25k = 3 day trades / 5 days"). That rule is GONE:
  FINRA Rule 4210 amendments (SEC approved 2026-04-14, Reg Notice 26-10) took effect **2026-06-04** (firm phase-in to
  2027-10-20). Schwab (per secondary sources; its own page blocked automated fetch — confirm in the account): stopped
  counting day trades 2026-06-08; real-time intraday margin buying power from 2026-07-13 for margin accounts >= $2,000.
  Restrictions now come from unresolved intraday margin deficits, not a trade count.
- **Rule: regulatory/account constraints must be date-versioned. Do not apply pre-June-2026 PDT assumptions to 2026+
  trading economics.** Keep separate: regulatory rule / broker house rule / account type (Roth: no shorting, no
  intraday margin) / borrow availability / capital and margin. Account eligibility never changes a statistical verdict.
- **SSR-LIFT (Rule 201 lift day, N 859->860): first regulatory-threshold RD in the program. Mechanism CONFIRMED**
  (diff-in-disc -43bp t -6.5 post-2011 vs ~0 pre-rule; adjacent-cutoff and ETF placebos clean; permanent). Executable
  short (T+2 open cross -> close cross, SPY-hedged) on official crosses 2021-26: +16.7bp/day t 2.72; frozen liquid rule
  +15.5bp t 1.78; squeeze tail (maxDD -41% at 0.5x); cost-bound (dead at 5bp/side + 2bp borrow). Forward-only, short-only
  (taxable margin >= $2k). ~+9%/yr gross at 0.25x, ~4-5% at honest 50% capture: below the +8pp gate. Not deployed.
## Research memory — session "category attack: same-issuer + filing-lag" (2026-10-06, party 2)
- PAIR-CLASS (dual-class differential, N 857->858): killed by SCALE not falsity (GOOGL/GOOG median +13bp
  but 6 fills/yr). WBD/DISCK/ZG/Z thin. No re-tuning of z/horizons.
- FN-LAG (SF1 filing-lag map, no N): OBSERVATION DEAD — the +12.7%/63d "late-filer premium" is a sub-$2
  artifact pool; $2-5 and $5+ universes NEGATIVE all eras. SF1 publish-date proxy needs restatement dedup.
- Same-issuer / regulatory family (the new-vocabulary category) is now fully measured at the daily tier:
  no member produces a $2-25k candidate. Remaining: STATE-gate usage of 13F only; paid sources untouched.

## Research memory — session "derivatives frontier: futures/options as infrastructure" (2026-10-06)
User directive: futures/options as a NEW frontier, mechanism-first, no brute force, NO data buys
($180 signed-gamma NOT funded). Three pre-registered studies (round1_prose.md; runners
research/sim/{cotx,cbas,vts}.py; outputs data/research/program/*_out.txt), ALL KILL; program
N renumbered to 866 (multiple parallel-session collisions: PAIR-CLASS/SSR-LIFT/PREF-EX consumed
857-861; canonical numbering now COTX 862, CBAS 863, VTS 864).
- **COTX (N 862) KILL:** CFTC COT weekly positioning state (free Socrata API: TFF + disaggregated;
  leveraged funds/dealers/asset managers, 9 products, 2006-2026, cached data/research/cot/) — no
  tradable 1-2wk footprint in any frozen arm (t 0.25..1.40, wrong signs, halves flip). The
  participant-state information that exists ONLY in CFTC data is invisible to P&L at weekly tier.
  CL/NG series end 2022-02 (CFTC dataset split; not the cause of the null).
- **CBAS (N 863) KILL + mechanism finding:** daily ES/NQ cash-futures basis (front close vs
  SPY/QQQ raw close, z vs 21d med/MAD, roll5 excluded): retail spot legs net-negative BOTH
  directions next-day (SPY follows the futures-led move ~1 day, against convergence, cost-bound);
  3d arm t 1.47. **The persistent daily basis-dislocation regime does not exist 2011-2025** (after
  a |z|>=2 flag, median z_(t+1) ~ 0, only 14-26% still flagged) — the arb is never balance-sheet
  constrained for days at this frequency; the "hedged convergence t=18-24" is 2xMAD
  regression-to-median baked into the flag definition. Basis family closed at the daily tier.
  **DATA BUG FIXED: Databento GLBX daily bars are stamped by SESSION START (evening), not trade
  date — trade_date = next business day (research/sim/cbas.py::trade_dates). Any new consumer of
  data/research/program/glbx_*_daily.parquet must remap; old fut_roll/FND event-window verdicts
  are label-shift invariant and stand.**
- **VTS (N 864) KILL:** VIX term structure via Yahoo ^VIX9D/^VIX3M (the ONLY free options-family
  data; note Yahoo range=max silently returns MONTHLY bars — use period1/period2 interval=1d).
  Contango 5d +17bp t 5.5 = unconditional SPY drift (per-year +-5bp noise, not excess) — rejected
  as a sensor; inversion arm wrong sign (market relief-bounces; short loses both halves). The
  unregistered MIRROR (LONG after inversion, ~+59bp/5d excess, 11% of days, overlapping windows)
  is an observation/forward-shadow candidate only, NOT a PASS.
- **META ANSWER (user question 12): NO.** Free derivative data (positioning, cash-futures basis,
  vol curve) reveals no harvestable forced behavior invisible in equity daily prices at this
  tier; each visible state is arbitraged flat, drift-only, or the wrong sign. What remains
  invisible-in-equity (OI by strike/signed gamma, margin-rate history, skew) is exactly the PAID
  tier, and its prior is now LOWER (OI-pin killed + these 3 kills). Do not fund automatically.
- **Data-limited (not tested, not rejected):** CME margin-hike forced deleveraging (no free
  historical margin-rate series; CME notices scrape is the spec; silver-2011 canonical), SOQ/
  expiration at minute tier (no power at daily), cross-contract spreads (generic-carry exclusion
  stands until a named constrained participant is written down).
- Derivatives share of the loop this session was ~100% by directive; the standing 60-70% rule
  resumes with the next session (open non-derivative ground per part 9-11 ledgers).
- **PREF-EX (preferred ex-dividend under-adjustment, N 860->861): STRONGEST small-account candidate of the clean-slate loop.**
  Buy the T-1 closing cross, sell the ex-date opening cross, collect the dividend: official crosses 2021-26 +38bp/event
  (median +35, t 20, every year), Sharadar 2005-26 22/22 years; drop ~0.8 x dividend (tax clientele, partial). Crosses
  print at the NBBO mid; quoted spreads (38/88bp) make it auction-only. Roth-only (dividend untaxed). Gross at a 10%
  participation cap: ~$840/yr at $3k, ~$1.6k at $10k, ~$2.4k at $25k; capital used ~128 nights/yr (stacks). Unverified:
  impact in thin crosses, broker MOC/MOO on preferreds, Roth T+1 settlement on back-to-back nights. Forward log-only, then
  a tiny live pilot (user decision). Common-stock ex-div capture stays dead (EXDIV-OPEN); this is a different class.
  Independent support: CEF ex-nights +13bp (drop 0.78), high-yield ETFs +17.5bp (drop 0.86), 2005-26, ~20/22 yrs each.

## Research memory — session "mechanism jump: financing/collateral/margin" (2026-10-06, cont.)
- **Pre-test ceiling table** (round1_prose.md): CL/NG monthly GSCI roll (~1-4%/yr), buyback 10b-18
  blackout flow (~1-2%/yr), SG-CTA crowding (~1-2%/yr), DXJ/EWJ forward-point wedge (2-4%/yr minus
  borrow), dividend-fail pre-ex-div front-run — ALL CEILING-KILLED before any backtest. No reruns.
- **PLUM (N 865): KILL.** Daily repo-stress states (SOFR-DTB3 >= 25bp n 171, SOFR-IORB n 3, FRED
  free): 1d ~0 both directions; 3d mean crash-carried (median -18bp). Post-2021 flags benign —
  SRF absorbed the mechanism. The daily financing state is NOT a usable risk gate. Runners
  research/sim/{plum,mflw}.py; outputs data/research/program/{plum,mflw}_out.txt.
- **MFLW (N 866): KILL.** FINRA margin-debt monthly 1997-2026 (one free XLSX,
  data/research/finra/margin.xlsx): cascade-bounce +16bp/mo t 0.11 with 52% hit (2008/09.next-months
  -8..-11%) — no reliable bounce; euphoria-short wrong sign. Margin debt coincident. Family closed.
- **Region status:** the financing/collateral/margin/clearing members of the mechanism map are now
  MEASURED at free data and empty at retail tier. The one remaining free-data region = FINRA ATS
  venue-mix (off-exchange share per symbol, weekly): needs a FREE FINRA API token (user action at
  api.finra.org; otcMarket weeklySummary already key-less) — then a conditioning study on the
  IBS/night legs becomes testable. Everything else standing is paid-tier (OPRA gamma, margin-rate
  archive, borrow fees, PIT ratings, TBA, per-fund NAV, Milliman LDI) — user decisions, not automatic.
- Program N = 866.
## Research memory — session "frontier reset: margin data + CEF-TL2" (2026-10-06, evening 3)
- CME margin-rate history probed four ways (web+ftp+wayback): NOT free-reachable; margin-hike
  forced-deleveraging stays DATA-LIMITED. Do not re-probe without new credentials/clean IP.
- **CEF-TL2 (N 863->864): REJECTED (net)** — 1,156 delisted-complete CEFs 1999-2025: Jan Q1-u gross
  +2.72% t 3.28 (22/27 yrs+, ex-best +2.31), net +0.13 t 0.27 at 30bp; Dec leg wrong sign.
- **CLASS-verdict: December-loser January bounce = real GROSS seasonal, cost-bound at retail
  (panels: stocks t 1.91, CEFs t 3.28). Closed at prices-only data forever.**
- **PREF-EX execution attack (2026-10-06): size claim halved, edge intact.** At 5% of auction $ and 10bp round trip: CO
  $232/yr at $1k, $456 at $3k, $585 at $5k, $789 at $10k, $919 at $25k (dollars plateau: capacity binds above ~$5k).
  CO dies if the open leg misses the auction (half-spread 44bp); Schwab has no MOO (directed routes refused; AUTO pre-open
  sells hit the official open for liquid names only so far); CC (MOC both legs) is the Schwab-safe form (~60-70% of CO).
  Shadow live on him (`pref_ex_shadow.py`, REGISTRY, 60 ex-nights). Next: one tiny live Roth test order (user decision).
- **ETDX (2026-10-06, N 869): PASS** — PREF-EX rule on baby bonds (SFP ETD) + CEF preferreds: official 2021-26 ETD CO
  +44bp / CC +39bp, 28/29 yrs. Mechanism = dividend-proportional under-adjustment surviving only in $25-par income paper (THN: thin commons had it pre-2021 regardless of tax status, ~0 since; tax is contributing, not proven). Lifts the Roth plateau ~1.5x ($1.1k/yr at $10k, $1.4k at $25k
  CO). Logged in the same shadow (cls "etd"). **FXD KILL** (CEF/ETF ex-nights decayed to <10bp since 2020). SFP dividends
  can be split-adjusted vs raw prices: guard against y(closeadj).


## Research memory — session "VENM: FINRA venue-mix as an IBS conditioning state" (2026-10-06, night)
- **VENM (N 867): KILL — killed by its own placebo.** Built the FINRA weekly off-exchange venue-mix
  panel (EQ18 ETFs, 2021-12..2026-09, LOOKAHEAD-SAFE via per-row initialPublishedDate; 3.0-week
  empirical lag; key-less `otcMarket/weeklySummary`; the user's FINRA API key still 401s on
  regData — it looks truncated, user will reissue). Data doc + fetcher: research/sim/finra_ats.py;
  cache data/research/finra/ats_etf.parquet; conditioning runner research/sim/venm.py
  (venm_out.txt). Result: LEVEL buckets non-monotone (LOW +10.1 / MID +28.9 / HIGH -4.5bp),
  change buckets t < 2 with halves flips, and the PERMUTED-SYMBOL placebo separates more than the
  real state (+15.9 t 2.68): bucketing = sample noise. Ceiling: ±20bp x ~40 trades/yr = +0.6-0.8pp/yr
  MAX — below the +8pp gate an order of magnitude. Per-stock night-leg attachment: feasible-but-
  heavy; priors inherited from the placebo failure; a new mechanism hypothesis would be required.
- Program N = 867.

## Research memory — session "FinBERT / open NLP discovery" (2026-10-06)
- Ledger + gate math: `research/drafts/nlp_ledger_2026-10-06.md`. Only CEF-TXT (FinBERT tone of N-CSR shareholder
  reports as a filter on CEF-RV, N 887->889) cleared the gate; **KILL both arms** (level -58bp t -1.86 wrong sign; change
  -31bp t -0.79; 0/7 checks). Lazy prices, PREF-EX/Form 4/FOMC/night-leg text filters, CEF proxy text, classifier
  forced-flow discovery: killed at the gate (regex on full text beats a classifier for contractual clauses).
- **Verdict: open-source financial NLP adds no edge beyond price data at this account's reach**; fast text is priced at
  the open, slow text (CEF letters) is commentary. Do not re-open NLP as a signal source.
- Unregistered lead (price-only): CEF-RV entries after a trailing-26w NAV fall are its best trades (dropping them costs
  -705bp t -5.1, both halves); needs its own pre-registration on data CEF-RV was not judged on.
- System `python3` has torch+transformers but a mismatched torchvision: block it (`sys.modules["torchvision"]=None`)
  before importing transformers.
- **CEF-OOS / NAVFALL (N 890-891), same session.** CEF-RV PASSES on untouched 1999-2014 (+333bp t 5.3, alpha +237 t 5.2
  after 0.53*SPY). **But its 2016-26 alpha after 0.76*SPY over the hold is +46bp t 0.74**: the recent "+409..486bp" is
  mostly levered equity beta bought after selloffs. NAV-fall filter passes as registered (+376bp t 3.45 OOS) but ~half is
  SPY rebound. `cef_rv.next_close` fixed (pre-window signals took the window's first close).
- **CEF-ALPHA (N 892-893, 2026-10-07) SUPERSEDES the "+46bp t 0.74" line above** (that used an in-window fitted beta; the
  intercept is beta-sensitive because entries precede big rebounds). Pre-registered beta-matched comparators: CEF-RV minus
  the EW CEF universe incl. delisted = **+125bp/trade t 5.6 (2016-26), +187 t 9.4 (1999-2014)**; minus out-of-window
  beta x SPY = +159 t 3.5. CEF-RV has real alpha in both eras; raw is ~2/3 market. ~+4.8pp/yr excess on deployed capital
  (below the +8pp stand-alone gate; a Roth upgrade over holding beta). Open: same-category peer comparator.
- **CEF-SURV99 (N 895-896): 1999-2014 survivorship is MATERIAL.** Dead CEFs are 71% of 1999-2014 proxy entries; on a
  price-only proxy live funds beat dead funds by +186bp/trade (both halves, ex-2008-09 +104). Bound on the OOS alpha:
  ~+105bp central, ~0 at the conservative end (`cef_surv99_out.txt:22-28`). Pre-2010 dead CEFs often died badly (16%
  lost >10% in the final 6m vs 6% in 2015-26). => The 1999-2014 "OOS pass" is NOT established; 2016-26 (+125bp vs EW CEF,
  benign-death era, ~2pp/yr gap) remains the evidence. History cannot settle it (no dead-fund NAV): the decisive test is
  forward (open-cross execution + log-only shadow). Program N = 896.

## CEF-RV forward shadow LIVE (2026-10-07)
- `swingtrader/daily/cef_rv_shadow.py` runs in research-shadows (08:20 ET), REGISTRY "CEF-RV: CEF discount reversion vs
  the CEF universe"; gate in round1_prose.md "CEF-RV-FWD" (60 closed forward trades, >= 10 entry weeks, excess vs EW CEF
  >= +60bp t >= 2). First forward signal week 2026-10-09; Sept/10-02 signals are backfill.
- **CEFConnect blocks the server's IP** (Akamai "request blocked"). The weekly NAV panel must be refreshed from the Mac:
  `make cef-rv-panel` (fetch + scp to him:llm-trader/state/). Without it the shadow reuses a stale panel and logs so.
- Live execution test (`research/sim/cef_open_test.py`, 1 share, Roth, pre-open opg order) is USER-RUN: the auto-mode
  classifier blocks Claude from placing real orders.

## Research memory — session "ROTH-STACK" (2026-10-08)
- **ROTH-STACK (N 896->897): PASS-SMALL.** PREF-EX+ETDX (CO, 10bp RT, official crosses 2021-26) funded only from the idle cash of the AL1 cash-Roth
  book, whole shares, 5% of ex-ante auction $, BIL kept (GFV-safe): +10.5pp/yr at $1k, +8.4 at $3k, +5.4 at $10k, +3.6 at $25k (halves equal, ex-top-5 same,
  median +27bp, hit 72%). PREF-first priority over the night buys beats night-first by ~+2pp; BIL-sold (unsettled funds) is +5pp more but GFV-risky.
  **3x cost leaves +1.6pp ($3k) / +0.9 ($10k)**: depends on the measured cross cost. Placebo uninformative. `research/sim/roth_stack.py`, `roth_stack_out.txt`.

## Research memory — PREF-INDEX (2026-10-08): CEILING-KILL, DATA-LIMITED, no N, no backtest
- Pref-index inclusion/deletion forced flow (PFF/PGX/PGF/FPE): iShares `asOfDate` holdings CSV re-tested 2026-10-08 -> still HTML (no PIT holdings history); inclusion date unobservable, only a first-listing proxy. Prior probes stand: new-issue first close vs $25 +0.28% median (pref), 0.00% (ETD), 20d drift = accrued coupon (no concession); month-end rebalance flow <= 12 x ~50bp on part of capital.
- Ceiling at $10k: ~100 listings/yr x <=30bp x ~5-10% of account per name ~ +0.2-0.4pp/yr (even 1/3 of listings x 50bp x 100% = ~5pp is unreachable given thin-paper caps and auction-only fills). Far below +8pp. Deletion side (calls/redemptions) is a price-to-par pull, already in PREF-EX/ETDX carry. Reopen only if PIT holdings (paid ICE/iShares archive) appear.

## Research memory — EXDATE-OOS (2026-10-08, N 898 -> 899)
- Ex-date night (buy close E-1, sell open E) on Sharadar raw prices, `research/sim/exdate_oos.py`, out `data/research/program/exdate_oos_out.txt`. NOT clean OOS (all Sharadar years touched); judged 1998-2012.
- Forward splits 1998-2012 n 3109: +82bp raw-SPY, median +43, hit 64%, clustered t 12, ex-top5 +77, halves +89/+58, tier net +69 (2x tier_hi +45, median +8); 2013-26 n 578 +105bp, median +40. Stronger in thin names and 1.5:1/2:1, ~0 above 3:1. Daily-bar opens, not crosses: official 2021-26 median is +17.
- Spin-offs (parent + child open) WEAK: t 1.4/1.8, ex-top5 negative. Reverse splits: data/convention problem, untested. Shadow: keep forward splits; spin-off arm is unsupported.

## Research memory — SPLIT-CROSS (2026-10-08, N 899 -> 900)
- Forward-split ex-date night at OFFICIAL SIP crosses, 2016-20 (`research/sim/split_cross.py`, `split_cross_out.txt`): n 152, gross vs SPY +158bp (median +58, t 2.09, ex-top5 +44); net of 2x tier +129 (median +28, ex-top5 +15) but day-clustered t 1.73 -> FAILS the registered t >= 2. 2016-18 median +60 vs 2019-20 +18 (net2 median -2): decaying.
- Daily open == official open cross in 2016-20 (median gap 0bp), open cross never missing. So the 1998-2012 Sharadar +43 median is NOT a first-print artifact; the 2021-26 shadow backfill (median +18 all, -17 at close-cross >$1M, 43% of splits with no cross) reflects decay plus a junk universe (OTC ADRs/foreign lines).
- Buckets (gross median / net2 mean): <$5M ADV +69 / 0; $5-50M +39 / +268 (outlier-carried); >$50M +57 / +76 (t 2.4). Ratio 1.5:1 best (+70, t 2.35); >=3:1 ex-top5 negative. Shadow rule recommendation (gate unchanged): ADV20 >= $50M or at least $5M, ratio <= 2:1, exclude ADR/OTC symbols.

## Research memory - session "idea scan: leg selection/sizing" (2026-10-08)
- Scanned 18 shape-A/B ideas for choosing/sizing the IBS/night names (`research/drafts/idea_scan_2026-10-08.md`): 13 already DEAD in ledgers (rank, sector, earnings, 8-K,
  dow/TOM, index IBS, short interest, basket drift, volume/gap/price, issuer class), repeat-loser already in forward shadow, QI-HIST duplicate. Every conditioner acts on a ~4%/yr leg: ceiling < +1pp, none clears the gate.
- **FUND-STATE (N 901): FAIL.** Night picks split by Sharadar pe sign (1999-2015, 13.7k picks): profitable +59bp vs loss-making +82bp, paired -51bp t -3.5 (wrong sign, placebo 0th), 2016-26 -1bp t -0.1. Marketcap/value splits null. No EPS filter or tilt; process slip: prose written after the run (disclosed).
- Left open, not run (ceiling < 0.5pp each): S&P membership, dividend-payer, beta/ma200 state. Selection-conditioning on the night leg is a closed class; stop scanning it.

## Research memory — session "events scan, shape B/C" (2026-10-08)
- `research/drafts/idea_scan_events_2026-10-08.md`: 23 forced-flow/structural mechanisms (CEF ends/tenders, ETF/ETN closures, thrift, SPAC floor, Dutch/odd-lot, rights, pref calls, DRIP, demut., appraisal, split-offs, stubs, OTC deletions, spin when-issued, bankruptcy rights, stock-for-stock arb) deduped against NEXT/prose/sim.
- 17 already tested or dead, 4 ceiling-killed (<0.3pp), 4 unobservable/untradable. The only survivors (CPC bundle +8.8pp at $10k, pref chain +5-7pp, thrift +2.6pp) are existing forward-validation items, not new. No test run, no N consumed (N 900). No SEC_USER_AGENT in .env; EDGAR-text variants have ceiling < 0.3pp so it does not matter.
- Verdict: the free-data forced-flow space is exhausted for shape B/C; do not rescan it without a new data source (borrow fees, PIT ratings, ETN/rights deal tables).

## Research memory — QI-HIST (2026-10-08, N 897 -> 898)
- 15:40 SIP NBBO quote imbalance (BB's QI) on the 2016-20 exact night picks (5,602 scored): sell-heavy tercile +24bp vs +66 / +55 (1x cost). "Skip sell-heavy"
  = +12.2bp/trade (gate was +30), day-clustered t -2.16, halves +8.6/+13.2, ex-top-5 +11.5, placebo 99th pct; sell-heavy still positive net. **DEAD as registered.**
- Direction agrees with BB's forward peek but the effect is ~1/4 of the peek and the skipped tercile is not a loser; no live filter. BB stays forward-only. Runner `research/sim/qi_hist.py`.

## Research memory - noise leg recent check (2026-10-08)
- `research/sim/noise_recent.py`, `research/drafts/noise_recent_2026-10-08.md`: QQQ+SMH PROD replay, post-2024-05 at 1bp RT: no-lag +3.65bp/trade (t 1.5, Sharpe 0.14), one-bar lag +3.14 (t 1.5, Sharpe 0.22); ~0 at 4bp RT; 2026 Jan-May negative (-0.2 / -1.1). Lag costs only ~0.5bp post-2024 (3.62 vs 2.31 pre), so the lag fix is nearly moot; the leg itself is marginal and cost-bound (user decision).
- Lagged replay reproduces live fills within a few bp (live is one bar late, confirmed); 7 live round trips so far: mean -14bp, median +3, too few to judge.

## Research memory — recent-regime replay (2026-10-08)
- Night leg exact 15:40 replay through 2026-10-07 (`research/sim/recent_night.py`, data `data/research/recent/`, `research/drafts/recent_regime_2026-10-08.md`): 2026-06..10-07 +113bp/trade gross (+98 at 7.5bp/side, day-clustered t 1.8-2.3) vs 2021-26 baseline +26 (+11); last 10 live-window sessions -55bp. Live fills match replay on 67 shared trips (corr .998, +-11bp), so the live shortfall is a 2-week sample, not execution or a regime break.
- Noise leg (QQQ+SMH) ~0/negative all 2026 (YTD -0.5 no-lag / -1.1 lag at 0.5bp/fill, Sharpe -0.7/-1.0 vs +0.6..0.8 in 2021-25); no sizing change on either leg.

## Research memory — session "recent regime: IBS leg" (2026-10-08)
- IBS replay through 10-07 (`research/drafts/recent_ibs_2026-10-08.md`, `research/sim/recent_ibs.py`): adjusted 2021-25 +15.8bp t 1.9, 2026 YTD +67bp t 3.1 (+57 at 5bp/side), Jun-Oct +77; live fills match replay (corr 0.99, 5/5 scorable). But paired excess vs the same-day unconditional top-3 basket is +1.7 (2021-25) / +12 (YTD) / +31 (Jun-Oct), t 0.5-1.2: 2026 strength is mostly basket beta, 2024 negative. No sizing change.
- Data gotcha: raw (price-only) open-to-open is ~10bp/trade lower than the adjusted panel in 2021-25 because IBS trades span ex-dates and the holder receives the dividend; use adjustment=all for ETF replays.

## Research memory — deploy loop + autonomous run (2026-10-10)
- Live auction cost re-audited on 216 auction fills since 09-23: 213 printed exactly at the official SIP price (night close mean
  -0.04bp, night open +0.60, IBS/T-bill 0.00). S2 night size-up deployed as profile `nx_s2` (night 0.65, IBS 0.5, taxable only;
  user "go" 2026-10-10, armed via DAILY_LIVE_PROFILE on him). S1 losing-night x2 NOT built (~$20-230/yr, recommended against).
- Schwab order endpoint cannot resolve preferreds by symbol (BAC/PRP -> "Could not resolve instrument"); it needs symbol + CUSIP.
  `SchwabAdapter._cusip` attaches it for slash symbols (previewOrder validated). JRI CEF open-cross test: both legs 0.0bp vs the
  official open (AUTO route, pre-open market order). PREF-EX shadow 0/60 forward; Sept backfill CO on-backtest, CC weak (t 0.4).
- **BREAK-REV2 (N 930 -> 931): FAIL, wrong-signed.** CIK-mapped 85 new events: A2 -2.84% median -4.22 hit 32%; pooled 128 <= 0.
  Post-deal-break reversal class CLOSED; do not buy a deal database for it. Program N = 931.
