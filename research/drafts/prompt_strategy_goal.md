# STANDING GOAL: find a strong strategy that actually hits at $2-25k. Never stop.

Run it as: `/loop follow research/drafts/prompt_strategy_goal.md` (no interval: self-paced, it never finishes).
Every iteration is one unit of work: read STATE, do the next step, commit, update STATE, schedule the next wake-up.
**There is no "done".** FOUND starts the next hunt (section 7). The user is away. Don't ask questions: decide, write
down why, keep going.

Work in `~/Documents/Code/Projects/swing-trader` (research data lives here; `llm-trader` is the live checkout). Other
sessions share this tree: on the first iteration run `ListAgents`, tell every session here that you're running this
file, and message them whenever you register an N. Only `git add` files you name; never clean, stash, reset or checkout
files you didn't write. Your files: `goal_log.md` (STATE at the top), `goal_ideas.md`, `study_goal_*.md`,
`research/sim/goal_*.py`. Claims prefix: `Goal`.

## 0. The goal
The user doesn't want a small edge. They want **a strategy that makes big money on small balances**: taxable ~$2.3k
(adding $1-2k/month), Roth $8.5k (+$7.5k/yr). It counts as "strong" only if it **beats the index by a wide margin after
costs and tax, in the recent years, and still does on data it never saw.** It can be a new standalone strategy, a
bigger version of something that already works, or a combination. It must be something the server can run (or < 5
minutes of manual work per event).

**Be honest about where big returns come from at this size.** Roughly four sources:
1. **Concentration in a real edge**: fewer, larger bets on the highest-conviction cases of something that already
   survived here (e.g. EV2 >= $500k buys: +75bp/trade on the judge half, robust to dropping its best days).
2. **Leverage on a high-Sharpe, short-hold edge** (the night leg's Sharpe ~2 is the raw material; margin 1.3-2x
   taxable, 3x ETFs in the Roth).
3. **Large contract payoffs** (split-offs ~+7% in 8 days; tenders; conversions; mechanisms in
   `prompt_hidden_edges.md` section 2) that a fund can't scale.
4. **Convex payoffs** (long options on events with a mechanical catalyst), only when the payoff comes from a known
   mechanism, not a lottery.

Everything else ("a new indicator that hits 70%") has been tried here ~800 times and died. Don't spend iterations on it.

## 1. Read before the first iteration
- `NEXT.md` (all of it, especially "Things already tested — do NOT redo these").
- `prompt_index_beat.md` section 1 (the death map) and `prompt_hidden_edges.md` (the five-question edge test, where
  to dig). Both apply here.
- `study_reddit_round.md` (the latest sweep: what the public internet has, and that it's all dead).
- What survived: ID3 / EV2 (`study_ev2_first_insider_buy.md`), B1 / B2 contract payoffs (`study_round32_events.md`), the
  live book (README "What runs"), and the AU3 tilt shadow.
- Lanes owned by other hunts: Jump hunt (hype / news -> jumps), Index-beat hunt (regime robustness, after-tax account
  structure). Read their logs for STATE; build on their dead lists, but don't run their ideas.

## 2. Tracks (rotate: never more than 3 iterations in a row on one track)
- **T1 SCALE WHAT WORKS.** Concentrate, lever or combine proven survivors:
  - EV2-big as a sized standalone book, not a 2x weight inside ID3.
  - Night leg at 1.3-2x on its highest-conviction subset.
  - Contract payoffs stacked across both accounts.

  Each design must say why the bigger version doesn't break the edge (capacity, impact, whole shares, margin rules,
  correlation on bad days; R4 found the legs don't co-lose).
- **T2 BIG CONTRACT PAYOFFS.** Mechanisms with a written payoff >= 5% per event (`prompt_hidden_edges.md` A-D): split-offs,
  exchange offers, odd-lot programs, ADR terminations, calls at par below market, conversions, due-bill mispricing.
- **T3 RULE-BOUND FLOW, CONCENTRATED.** Second-tier index events, structured-note barrier hedging (424B2), forced OTC
  sellers, convert-issuance shorts, ESPP dates. Trade only the top decile of expected flow / ADV.
- **T4 CONVEX.** Long calls or puts (taxable; check Roth options level) around mechanical catalysts from T2/T3, where the
  move size is predictable from terms. Price with real historical option quotes if available; else bound with a
  conservative IV assumption and say so.
- **T5 COMBINE.** A book of the survivors plus any new one, sized by each one's own risk, both accounts, after tax.

## 3. Every iteration
1. Read `goal_log.md` STATE: round, k (ideas judged), N, what's running, next step.
2. Do ONE of: write 10 ideas (each with the five answers from `prompt_hidden_edges.md` section 1, plus "which source of
   big return from section 0, and why it's big") / count events from documents / register one study / run one study /
   write up one verdict / build one shadow.
3. Commit (named files only) and push. Update STATE: one line saying what you did, what's next, k, N.
4. Schedule the next wake-up. Long jobs: run them in the background and wake up in 20-30 minutes; otherwise 60-120 s.
5. Every 10 judged ideas: one paragraph in the log on what came closest and why it failed. The next 10 ideas must aim
   at that gap.

Quota per round of 40 ideas: >= 8 per track T1-T4, >= 4 for T5. Zero ideas may start from a chart, an indicator, a
calendar or a sentiment score.

## 4. Validation (non-negotiable: big backtests are where fakes live)
- Pre-register before ANY outcome. Written to `round1_prose.md` (studies, N++) or the DL convention (deal rules, no N).
  Commit and push the registration first.
- Select 2021-23, judge 2024-26, holdout 2016-20. Raw-price pool (`load_sim(raw_price=True)`). Real costs (tier AND
  tier_hi; odd-lot touch spreads for thin names; options at the quoted bid/ask, never mid). Whole shares. Margin
  interest. Short-term tax in the taxable account (`taxable_frontier.after_tax`).
- **Lottery test (new, mandatory):** the result must stay positive after removing its best 5% of trading days AND its
  best 5 single trades. EV2 plain fails this; EV2-big passes. A strategy whose return lives in a few trades is a
  lottery ticket, not a strategy.
- **Causality:** decisions use only data available at the decision time (`tests/test_causality.py` style:
  poison the future and get the same picks).
- Placebo / random-pick null >= 95th percentile; NW t >= 2 on the judge half; DSR at the current N reported.
- Name the worst single event and the worst month, at each size.

## 5. FOUND (don't loosen, don't redefine)
A strategy is FOUND when ALL hold, at **$2.3k and $10k**, both after whole shares and costs:
- **Judge half (2024-26) CAGR beats SPY by >= 10pp/yr** after tax in the taxable account (or untaxed in the Roth). For an
  add-on, the increment to the shipped book is >= +5pp/yr.
- Holdout 2016-20 beats SPY too (or is >= 0 pp for add-ons). Select half is consistent.
- Max drawdown <= 35% (taxable) / <= 45% (Roth); the worst month is stated.
- >= 100 independent trades in the judge half (or >= 30 contract-payoff events with every one listed).
- The validation in section 4 is passed, including the lottery test.
- The server can run it, or the manual step is < 5 minutes per event.

Report k next to any FOUND. If something clears every bar but one, call it **NEAR** and log exactly which bar it missed;
NEAR ideas get one pre-registered follow-up, never a re-run with new settings.

## 6. Shipping
FOUND -> build it behind an `.env` switch that defaults **OFF**, as a shadow that logs what it would do live. Add the
`swingtrader/daily/testing.py` REGISTRY entry in the same commit (CLAUDE.md rule). Write a NEXT.md section with $/yr at
$2.3k / $10k / $25k, the worst case, and one capacity line ($100k / $500k). **The user switches it on.** Never change
live sizing, leverage or accounts yourself.

## 7. Never stop
After FOUND, keep hunting for the next one (a second, uncorrelated strategy is worth as much as the first). If a round
of 40 is exhausted with nothing NEAR, write the next round from the mechanism that came closest, with the opposite
holding period, the other account, or the other track. If data is blocked (rate limit, paywall), log it, switch track,
and come back later. The only acceptable reason to end the loop is the user telling you to.
