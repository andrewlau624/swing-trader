# Prompt: find where the bot leaks return, then turn proven edges into more dollars

Paste everything below the line into a fresh session in `swing-trader/`.

---

Read CLAUDE.md first (the priority is % return at $2.3k / $10k / $25k, and the testing-registry
rule applies). Then NEXT.md and the top of RESULTS.md for the live book's legs.

## Context (from the 2026-10-03/04 session)
- **Why this matters now.** A friend and I are running a joint experiment. His bot is doing about
  2x better and faster on low capital. We can't share any information. From the outside it looks
  like **leverage (options or shorts) plus high turnover** (semi-day-trading, frequent trades, big
  wins). I don't want more signal hunting: 788 goal-hunt variants already exist and new signals
  are not the gap. The gap is probably in how proven edges become dollars.
- **Live record is short.** On 2026-09-29, the LIVE account's trading P&L net of deposits was
  +$18.94 (+0.8%). The "+127%" equity figure is mostly deposits. Forward gates are far from full
  (EV2 0/60).
- **The server is behind.** It runs code 28 commits behind origin/main, and research-shadows
  doesn't run cef_activist_watch yet. See DEPLOY.md / `make pull`. Check this first if the
  Monday 12:20 UTC run hasn't happened yet.
- **New rules to use.** The SEC approved the end of the $25k pattern-day-trader minimum
  (FINRA Notice 26-10, effective 2026-06-04). Schwab stopped counting day trades on 2026-06-08.
  A $2k+ margin account can now day-trade without the 3-trades-a-week limit, under risk-based
  intraday margin. Nasdaq 23x5 trading starts 2026-12-06. Any leg or sizing rule written around
  PDT limits is now stale.
- **Crypto is closed.** A separate repo, `../crypto-lab`, ran 35 pre-registered variants and none
  passed. Don't revisit it. Its lesson for this repo: when reading Alpaca `/v2/stocks/auctions`,
  take the primary exchange's largest-size 'O'/'6' auction trade, never the last 'Q'/'M' row.
  The last row is often another venue's late odd lot. swing-trader's readers use max-size and are
  fine. Treat a 90-100% win rate in any backtest as a bug until proven otherwise.

## Task 1: Audit (measure before changing anything)
Use the live logs on the server (`make results`, journals, fills) plus the backtests. For each live
leg and for the book as a whole:
1. **Capital use.** On what share of days, and with what share of equity, was money actually
   invested? What was the return on invested capital vs on total equity? Hypothesis: idle cash
   explains most of the gap to a bot that trades daily.
2. **Live vs backtest.** For every live trade, compare the backtest's expected entry and exit,
   fill and P&L with what actually happened. Break the gap into slippage, missed or skipped
   signals, timing, and downtime. Name the leg that leaks most.
3. **Tax drag and account placement.** Short-term gains at ~30% in the taxable account vs the
   Roth (+$7.5k/yr of new money). Would moving the highest-turnover leg into the Roth gain points?
4. **Rules still assuming PDT.** List every place in the code or config where the $25k rule
   shaped a decision.
Output: a table, "where the return goes", with the size of each leak in %/yr at $2.3k.

## Task 2: Leverage and concentration on proven edges only (pre-register first)
Use only legs with holdout or forward evidence. Pre-register in the usual log and count N.
- **Concentration.** Run all signals through one daily queue, best first, at full size, and size
  up when only one signal fires. Compare against the current allocation.
- **Leverage.** Run the top 1-2 legs at 1.5x and 2x (Reg T margin in taxable; none in the Roth),
  capped at half-Kelly from the holdout edge and variance, with a hard drawdown stop written into
  the code.
- Report CAGR, max drawdown, worst month and ruin odds at $2.3k / $10k / $25k, after margin
  interest and tax. State plainly where leverage turns a good leg into a blowup risk.
- **Options.** Only as a leverage overlay on a proven signal, with the premium as the defined max
  loss, and only if real option-chain history is available. Never on hunches.

## Task 3: An intraday leg (matches his trading frequency, keeps our discipline)
Now that PDT is gone, revisit `research/drafts/prompt_daytrade_lab.md` and the `daytrade/`
package. Scope one intraday mechanism with a named counterparty that pays at $2-25k, and
pre-register it. Don't build it until Tasks 1-2 say how much of the gap is left.

## Rules
- Any new shadow, switch or forward weight goes into the `swingtrader/daily/testing.py` REGISTRY in
  the same commit (`tests/test_testing_registry.py` enforces this).
- Be blunt. "The gap is mostly leverage and variance, and copying it would risk the account" is an
  acceptable finding. So is "idle capital explains it; here's the fix."
- Final deliverable: a ranked list of changes with expected %/yr at $2.3k / $10k / $25k, the risk
  each adds, and the smallest live version of the top one.
