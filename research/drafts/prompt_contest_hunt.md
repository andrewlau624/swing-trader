# Contest hunt: find and build the strategy that beats the friend's bot

Read CLAUDE.md first (sessions rule, testing-registry rule, $2.3k / $10k / $25k reporting). Then the top of
NEXT.md, `research/drafts/study_goal_l.md` (the leverage study from 2026-10-04) and the dead lists named below.

## Running unattended (I'm away: dinner, then sleeping)
This runs as a self-paced `/loop`. Each iteration does the next step and never waits on me.
- **Server:** `ssh him` (repo at `~/llm-trader`). It's approved: read logs, run `make pull`, run `make results`, deploy.
- **State:** keep progress in `research/drafts/contest_hunt_log.md`, and also in the claude-mem work_state list
  `contest-hunt`. At the start of every iteration, read the log and resume from the first unfinished step.
  Commit after each finished step, so a crash loses at most one step.
- **Never block on me:**
  - If something needs my answer (e.g. buying a data source), log the question, take the best free path, and move on.
  - If a family's data doesn't exist, mark it untestable and test the next one.
- **Live deploy while I'm away:** only allowed if all of these are true. Otherwise leave it built and staged, with the
  exact start command in the log.
  - Tests pass.
  - The dry run shows the order path.
  - The risk limits below are in code.
  - Max loss per trade is at most 5% of that account.
- **When to stop the loop:**
  - Step 4 is done, or
  - every family in the Step 1 top list has been tested and killed, and 4 more families have been tested past that.
- **Final report:** write it to the top of the log, under `## Morning summary`.
  - The Output section below, in 15 lines or fewer.
  - What is live now, and how to stop it (`make daytrade-halt` or the new leg's kill switch).

## Contest facts (edit these lines if they are wrong)
- A friend and I each run a bot. Score = **% return on our own money over the contest window** (net of deposits).
- His bot is beating mine by about 2x, and faster, on low capital. We share no information.
- What his bot looks like from the outside: **leverage (options or shorts), high turnover, near-daily trading,
  occasional big wins.**
- My money: Schwab taxable ~$2.3k (margin, can short, $2k+ so no PDT limit since 2026-06-04), Roth IRA $1-3k
  (+$7.5k/yr, long-only, no margin buying power). Both accounts trade today; the Roth has been trading (I get its
  emails). An audit on 2026-10-04 claimed the Roth book never traded. That came from reading code, not logs, and
  it is wrong; check the server before repeating any claim about what is live.
- Contest window left: assume **3 months** unless I say otherwise. Per-strategy loss budget I accept:
  **up to 30% of the account it trades in**, enforced in code (hard stop, defined-risk positions).

## What I want
**A different strategy from what the bot does now.** It can be completely unrelated: options, shorts, leveraged
ETFs, intraday momentum, futures, event trades, anything legal at Schwab (or Alpaca if Schwab can't do it).
Do not answer with "wait for the forward gate", "flip a config switch", "turn on the Roth book" or "more
deposits". Those were the last session's answers and they don't win a 3-month contest. The deliverable is
**new code that trades live at small size by the end of this session**, behind a hard risk limit.

What the 2026-10-04 audit already settled (don't redo):
- Levering the current legs (IBS + night) at 1.5x/2x and concentrating them is DEAD on the holdout
  (`study_goal_l.md`, N 791). The night leg's Kelly fraction is negative at tier_hi cost. Leverage alone is not the answer;
  leverage on something with a **bigger per-trade edge or bigger convexity** might be.
- Idle cash is 63% of equity-hours at $2.3k. A new strategy that uses the **daytime hours and the idle cash** of
  the current book stacks on top of it instead of competing for money.

## Step 1: reverse-engineer the friend's strategy class (1 hour, no code)
List the 8-12 strategy families that fit "leverage + high turnover + big wins + 2x a small book in weeks". For
each: the mechanism, who pays us (named counterparty), the typical per-trade and per-month return and drawdown
from public evidence (papers, broker data, well-documented retail results; cite them), whether it runs at $2-25k
with whole shares or contracts, and whether data to backtest it exists. Start from, at least:
- 0DTE / 1DTE SPX/SPY/QQQ options, long premium on intraday breakouts, or defined-risk spreads
- Long calls/puts as a convex overlay on the repo's one strong intraday signal (EV2-big insider buys, +35-69bp/trade)
- Opening-range breakout on "stocks in play" (relative volume, gap, news) with leverage (Zarattini et al. ORB papers)
- Intraday time-series momentum in SPY/QQQ via TQQQ/SQQQ or futures (Gao-Han-Li-Zhou last half hour; Zarattini-Aziz-Barbon
  "noise area"). Check how this differs from the live noise leg before counting it as new.
- Short-side: shorting gap-up low-float runners or failed breakouts (borrow cost and locate at Schwab)
- Earnings-move trades: options on post-earnings drift, or pre-earnings implied-vol run-up
- Micro futures (MES/MNQ) intraday with day margin. Check Schwab's actual day-trade margin and account
  minimums; memory says Schwab IRA futures need $25k NLV.
- Leveraged ETF rebalancing flow / end-of-day momentum
Rank by expected % return over 3 months at $2.3k and $10k, after costs, together with the odds of losing the 30% budget.
Pick the top 3 to test. Say plainly which family the friend most likely runs.

## Step 2: get the data
- Check what's in the repo first: Alpaca SIP minute bars, auction prints (`/v2/stocks/auctions`: take the primary
  exchange's largest-size 'O'/'6' trade, never the last 'Q'/'M' row), the daytrade recorder on the server, EDGAR, the
  earnings calendar.
- Options: there is **no option-chain history in the repo**. Check what Alpaca's options historical data API
  actually covers (start date, bars vs quotes, NBBO). If it's too thin, name the cheapest real source
  (ThetaData, Polygon/Massive, CBOE DataShop) with its price, and ask me once before buying. Never price options
  from Black-Scholes on a hunch; use real quotes and fill at the far side of the spread.

## Step 3: test fast, but honestly
- Pre-register each variant in the usual log before looking at results and count N (N 791 at start).
- One select period, one untouched judge period. Costs: real spreads (options at the ask/bid), borrow fees for
  shorts, margin interest ~12.5%/yr, 30% short-term tax in taxable.
- Report for each: CAGR and **3-month return distribution** (median, 10th/90th percentile) at $2.3k / $10k / $25k,
  max drawdown, worst day, and P(losing 30% in 3 months), all from a block bootstrap.
- **Treat a 90-100% win rate as a bug until proven otherwise.** Check for look-ahead, split-adjusted prices
  (`load_sim(raw_price=True)`), survivorship, and auction-row bugs. Lesson from crypto-lab: a whole family of
  "passes" was one auction-price bug.
- Already dead, don't repeat (grep before testing): RESULTS.md, `research/drafts/goal_log.md`, `jump_hunt_log.md`,
  `pick_quality_log.md`, the daytrade lab dead list (Lab-AS/AU/AW/AX/AY/AZ/BA/BB/BC/BD/BE/BF/BG/AV), `../crypto-lab`
  (all 35 dead, closed).

## Step 4: build and ship the best one, live, small
For the best variant that survives its judge period (or, if none passes, the best one, **labelled plainly as
unproven**, at a size I can afford to lose):
- Build it in the repo's style (`daytrade/` engine or a new `swingtrader/daily/` leg), with tests.
- Hard risk in code: max loss per trade, daily loss stop, a kill switch at the 30% budget, defined-risk positions
  only (no naked short options; shorts carry a hard stop).
- Regular-hours rules from CLAUDE.md (`signals.regular_clock`, `marketdata.trade_date`).
- A `swingtrader/daily/testing.py` REGISTRY entry in the same commit (`tests/test_testing_registry.py`).
- Deploy: the server is behind origin/main. Run `make pull` there, start the leg live at the smallest size
  that clears whole-share / one-contract rounding, and confirm the first order path with a dry run.

## Output
1. The strategy-family table from Step 1 with the most likely match to the friend's bot.
2. Test results per variant (table), with N before and after.
3. What was built, the commit hashes, how it's sized at $2.3k, the hard limits, and the exact commands that
   start it on the server.
4. One blunt paragraph: the odds this beats a 2x lead in 3 months, and what it costs me if it fails.
