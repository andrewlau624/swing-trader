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
- **A kill must say what was tested AND what was not (user, 2026-10-19).** Every verdict names the exact form:
  features (snapshot values vs sequences over the lookback), period, and shape (fixed rule / learned model;
  filter / tilt / standalone entry). "Closed as a class" is allowed only when every form is listed as tried.
  Each do-not-redo row carries a `not tested:` field. A verdict that cannot name the untested forms is a result
  about one form, not a class. (Origin: PATTERN-NIGHT snapshot-only was reported as closing selection; sequences
  were untested until SEQ-NIGHT.)
- **Test before pushing back.** If the user's idea can be run in under an hour on data already on disk, register
  and run it first; argue after there is a number. Pushback without a cheap test is not a verdict.
- **Branch before you test (user, 2026-10-19).** When the user hands over material (an idea, a tool, a forum post, "what about
  ML / streaming / X"), the first output is a BRANCH LIST: the 3-5 genuinely different strategies the material implies, including
  the ones that need new data, infrastructure or a different instrument. Each branch names its input (what information it uses),
  its fill (which auction / mid-session / other), and its mechanism, and says whether it is already in a ledger. The user picks.
  Never collapse the material into the shape that runs fastest on data already on disk (bars -> learned model -> long -> auction
  exit); that is the local optimum's own gravity, and "cheap to test" is a property of the data on disk, not of the idea. If only
  one branch is cheap, say so and still list the others. (Origin: "ML / LLM / streaming / any-interval checker" was folded into
  one tape-model test; reopening auctions, a pre-market-tape model on the two free crosses, and an LLM over a timestamped event
  stream were never listed.) The material is a TREE: the user's root idea need not work for its branches to; a kill at one leaf closes that leaf only, and every sibling stays open until it is run or ceiling-killed with its own number. Go two levels down before calling the root dead.

### Do not assume the current legs are the answer
The live book (IBS + night + intraday) is a local optimum, not the global one. Its Sharpe is
mostly one bet (long liquid equity/tech, timed with oversold closes). The user's real
objective is **%/yr on $2-25k**, where structural, odd-lot and forced-flow trades that no
fund can run are worth more than another 0.1 Sharpe on a $2.3k account. Search there first.

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

## Standing rules recorded during sessions
### Data-buy rule (user, permanent)
Buy research data only if **expected information value > data cost**: (1) structurally compelling
mechanism, (2) free evidence does not already weaken it, (3) experiment specified enough to
falsify it, (4) payoff materially larger than existing edges, (5) no cheaper dataset answers it.
- **Sharadar $69: DEFERRED, not rejected.** Do not purchase or request the key now; NX is
deprioritized. Apply the rule retroactively.

## Memory lives in `docs/memory/`
Before proposing an experiment, a design, or a claim about what was already tried, read `docs/memory/INDEX.md` and then only the files whose subject matches. 46 files, 26,238 tokens in total; this file carries the rules that apply every turn. New findings go into a new file there plus one index line, never into this file.
