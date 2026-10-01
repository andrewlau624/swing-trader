# Build prompt: a separate day-trading lab

You are working in the `swing-trader` repo. Build a **day-trading lab**: a separate package, a separate brokerage
account, its own state and logs. It must never touch the live book (`swingtrader/daily`) or its accounts.
Read these before writing code:
- CLAUDE.md: priority = % return at $2-25k; sessions come from `signals.regular_clock`; label by `marketdata.trade_date`.
- NEXT.md: "Things already tested — do NOT redo these", Round 13 (AB), Round 15 (AE), Round 16, addenda 40-41.
- research/drafts/study_round16_summary.md and study_ak_setups_latency.md (a 1-minute fill delay costs 16% of the
  conviction edge — latency matters here).
- swingtrader/daily/brokers.py (Schwab adapter, account pinning) and marketdata.py (`rth_minutes`).

## 1. Honest starting point (goes at the top of `daytrade/README.md`)
State these facts before any strategy:
- **Most day traders lose.** Large full-population studies find only about 1-3% make money reliably:
  - Taiwan (Barber, Lee, Liu & Odean): fewer than 1% of day traders are predictably profitable after costs.
  - Brazil (Chague, De-Losso & Giovannetti, 2019): of people who day-traded futures for 300+ days, 97% lost
    money and ~1% earned more than the minimum wage.
  Cite the papers properly in the README.
- **Daily profit = account size × net profit per trade × trades per day.** At $2-25k, $1,000/day means making
  4% (at $25k) to 50% (at $2k) of the account **every day**. No measured edge in this repo comes within two orders
  of magnitude of that.
- **A table of what each strategy earns per day** at $2.3k, $10k and $25k, from its *measured* net bp/trade and
  trades/day, with buying power modelled honestly (cash account: settled cash only; margin ≥ $2k: Schwab intraday
  buying power, add. 40). Add one column: "account size needed for $1k/day at this edge". Keep the table current;
  every strategy adds a row once it has replay numbers. Illustration only (not a measured edge): $10k × 4x intraday
  buying power × 10bp net × 5 trades = $200/day; the same at $2.3k with no margin = $12/day.

## 2. Record market data from day one
Most trading ideas here died for lack of data (AC needed imbalance data; AG could not test breadth or the NQ
lead). Build the recorder first and start it before any strategy exists.
- During the regular session (from `signals.regular_clock`, never the broker clock), save **second-by-second
  quotes (bid/ask/sizes) and trades** for a watchlist: QQQ, SPY, TQQQ, IWM, SMH, plus the morning's top gappers by
  premarket volume (cap the list; say the cap).
- Find out what the feeds actually give before you rely on them (Schwab streamer level-one / chart; Alpaca IEX vs
  SIP). Write what each feed has and lacks in the README. Do not assume time-and-sales exists.
- Storage: daily Parquet partitions under `data/daytrade/`, labelled by `trade_date`. Log gaps and reconnects;
  a day with a gap is flagged, not silently used.
- Run it as its own service on the server, separate from the live bot's timers.

## 3. Strategies are plug-ins, each with a written plan first
- One file per strategy under `daytrade/strategies/`, one interface (on_bar / on_quote / on_fill → orders).
- **Before its first trade (replay or paper), each strategy gets `daytrade/plans/<name>.md`:** the idea, why it
  could work, the exact rules, the size, and **the drop condition** (e.g. "drop if replay net < 0 at 2x costs, or
  if 40 paper trades average below X"). Commit the plan before computing anything.
- Anything run on historical data is a study: pre-register it in research/drafts/round1_prose.md and add it to the
  program N (642 now), same rules as every other study.

## 4. One engine, three modes
- The same strategy code runs in **replay** (recorded seconds, and `rth_minutes` history), **paper** and **live**.
  No strategy may branch on the mode.
- Fills: replay models spread, queue position for limits, and a latency setting (default 1s; report 0s and 60s too).
- **Drift report:** for every paper/live trade, the replay fill it would have got. Report the gap in bp by strategy
  each week. A strategy whose paper fills drift worse than its edge is dead regardless of replay.

## 5. Hard risk limits (enforced in the engine, not the strategy)
- Daily loss limit (default 2% of lab equity): flatten and stop for the day.
- Max risk per trade (default 0.5% of equity, sized from the stop) and max position notional.
- No adding to a losing position. No averaging down.
- Flat by 15:55 ET from `regular_clock` (stop new entries earlier, say when). Nothing held overnight.
- **Emergency stop:** a `state/daytrade/HALT` file (and a `make daytrade-halt` target) cancels all orders and
  flattens. Checked every loop.
- **Its own brokerage account.** Pin it by a new env var (e.g. `SCHWAB_DAYTRADE_ACCOUNT_NUMBER`). Refuse to start
  if it equals `SCHWAB_ACCOUNT_NUMBER` or `SCHWAB_ROTH_ACCOUNT_NUMBER`, or if unset. Tests must prove this.
- Under $2k the account is cash-only: settled cash, T+1, no good-faith violations. Model it in replay too.

## 6. Built to learn
- **Trade journal:** every trade with entry/exit reason, the replay fill, the plan it belongs to, and a free-text note.
- **Weekly review** (`make daytrade-review`): per strategy, trades, net bp, drift, rule breaks, and a decision of
  **drop / continue / change course**, written down with the reason.
- Two running logs in `daytrade/`: `MISTAKES.md` (what went wrong, what changed so it cannot repeat) and
  `PLAN_CHANGES.md` (every change to a plan, with why, dated). A changed plan is a new variant and counts toward N.

## 7. First experiments
- **A popular day-trader pattern, turned into fixed rules:** a big early mover (gap ≥ X% and premarket volume
  ≥ Y on a stock) pulls back to VWAP, then entry on a reclaim, stop below the pullback low, exit at a fixed R or
  by 15:55. Fix X, Y and every threshold in the plan before the first replay. Check the dead list first: Study AE
  (direction at the open), AB (fading QQQ in the band), AK (second breakouts) and add. 41 (noise rule on single
  stocks) are dead; this must differ from them in a way the plan states.
- **One that needs the recorded data:** something minute bars cannot see, e.g. quote imbalance or trade-flow
  in the first minutes, or spread behaviour at the open. It can only be replayed once enough days are recorded;
  the plan says how many days before the first look (and that look is pre-registered).

## 8. Paper first, then at most $500
- Paper trading only at the start. No live orders until the gate below is met and the user approves.
- Write in `daytrade/README.md` **what would justify a first $500 real-money test**, before any paper results
  exist. At minimum: replay net > 0 at 2x costs in both halves, ≥ N paper trades with drift smaller than the edge,
  no risk-limit breaks in paper, the HALT path tested live-safe. Say what N is and why.
- At $500 the money is tuition, not income: write the expected $/day honestly from the table.

## Rules
- Live code (`swingtrader/`) is untouched. Reuse its helpers by import; do not edit them for the lab.
- Regular session only. Every bar or quote read says why it is regular-hours.
- Tests for: the account guard, the risk limits, flat-by-close, HALT, mode-independence of strategy code. Run
  `make test`.
- Commit and push in small steps.

## Deliverable
- `daytrade/` package with recorder, engine (replay/paper/live), risk layer, the two strategy plans, journal and
  review, README with the honest starting point and the $/day table.
- The recorder running on the server.
- A short status line in NEXT.md: what is recording, what is in replay, and the $500 gate.
- Say plainly what does not work yet.
