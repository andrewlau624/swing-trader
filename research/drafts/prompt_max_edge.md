# Research prompt: get the most out of the current bot (look outside first)

You are working in the `swing-trader` repo (the research data lives here, not on the server).
Read these before running anything:
- CLAUDE.md: priority = % return at small balances ($2.3k / $10k / $25k).
- NEXT.md: the top section, and the "Things already tested — do NOT redo these" table.
- research/drafts/study_round16_summary.md, study_round17_summary.md (Studies AL-AR) and prompt_small_account_profit.md.
- research/drafts/study_e_ml.md (the program's earlier ML attempt) and study_w_letf.md.
- RESULTS.md addenda 13, 27, 31, 32, 33, 34, 37, 40.

## Goal
Raise the current book's **%/yr after costs at $2.3k, $10k and $25k** (taxable), and in the Roth
(+$7.5k/yr, no shorting, no intraday margin). Improve or add to what exists: night leg, IBS ETFs,
QQQ/SMH noise leg, conviction trade (shadow). Do not build a new bot.

This round is different from every earlier one: **look outside before testing anything.** Seventeen
rounds of in-house ideas have produced N = 669 variants and few survivors. The next idea should come
from what others have found and published, then be checked against our data and our costs.

## Step 1: the candidate list (no backtests yet)
Build a list of **at least 25 candidate ideas** in `research/drafts/max_edge_candidates.md`. Each row:
- **idea**, one line;
- **link(s)** to the source;
- **why it should work**, one line (the mechanism, not the backtest);
- **who is on the other side** (who pays us, and why they keep paying). No answer → drop the idea;
- **which leg it touches** (night / IBS / noise / conviction / Roth / new) and whether it fits
  $2-25k with whole shares;
- **dead-list check:** the closest row in NEXT.md's do-not-redo table, and what is different. If
  nothing is different, drop it;
- **reported edge**, then the **decayed edge** (below), then a rough %/yr at $2.3k / $10k / $25k;
- **data needed** and whether we have it.

### Sources it must cover (at least 2 candidates from each)
- **Research papers:** arXiv (q-fin), SSRN, NBER, and the main finance journals (JF, JFE, RFS, JFQA,
  Review of Finance, Journal of Portfolio Management, Financial Analysts Journal).
- **Strategy collections:** Quantpedia (including its screener's out-of-sample notes), Alpha Architect,
  Allocate Smartly, CXO Advisory.
- **GitHub repos.** Before a repo's idea counts, check its backtest for:
  - **lookahead:** signals that use the same bar's close/high/low to trade that bar, `shift` mistakes,
    full-sample normalisation or thresholds, survivorship-biased universes, split-adjusted prices
    used for price filters (our own add. 30 bug);
  - **missing costs:** no spread, no commission, no borrow, fills at the close or open with no auction
    slippage, no whole-share rounding.
  Write down what you found in each repo. A repo with lookahead is a source of a hypothesis only.
- **Hugging Face forecasting models:** Chronos / Chronos-Bolt, TimesFM, Moirai, Lag-Llama, TimeGPT
  (if free). Two traps to address before any test:
  - **pretraining leakage:** these models were trained on public series that may include our test
    years. Only data after a model's release (or its stated data cutoff) is a clean holdout. Say what
    that leaves;
  - **cost of running:** CPU/GPU time per daily decision on the server.
  The prior is weak (Study E: ML added nothing). A candidate here must say what a zero-shot forecaster
  sees that our hand-built signals do not.
- **Forums:** r/algotrading, QuantConnect forums and its strategy library, Elite Trader, public quant
  Discords, Wilmott. **For ideas only, never as evidence.** A forum claim needs a paper, a mechanism
  or our own data behind it before it can rank.

### Topics it must cover
- **Optimal exit timing:** optimal stopping, time-based exits, and exits for mean-reverting trades
  (Ornstein-Uhlenbeck / Bertram style; note Bertram thresholds are already dead for entries). Which leg
  could exit better: the IBS leg's hold, the night leg's open sell (sell at the open auction vs the
  first minutes), the conviction exit (Study AH killed stops and targets).
- **Kelly position sizing:** fractional Kelly across legs with estimation error, Kelly with drawdown
  constraints, and sizing by the confidence in the edge (Bayesian/shrunk Kelly). Already known: the
  Roth sits below its Kelly peak (add. 31); noise Kelly ×1.5 is shadow (add. 40); vol-targeted
  overnight gross is dead (add. 32). Say what a new idea adds beyond these.
- **Spotting when the market changes behaviour:** regime and change-point detection (hidden Markov
  models, Bayesian online change-point, CUSUM, structural breaks), used as a size dial or an on/off.
  Already dead: SPY/VIX regime gates, cross-leg regime tilt (add. 26a), automatic de-risk on CUSUM /
  rolling t (add. 37). A candidate must beat a false alarm that switches a healthy leg off for years.
- **Auction effects:** open and close auction imbalance, MOC/LOC order flow, auction price impact and
  reversal, odd-lot behaviour. Closing imbalance (Round 13 AC) is untested only for lack of data:
  price the data (Databento, Nasdaq/NYSE feeds) and say what it would cost.
- **Overnight vs intraday returns:** the overnight drift literature (Lou-Polk-Skouras, Kelly-Clark,
  Cliff-Cooper-Gulen, Bogousslavsky), tug-of-war, and who earns the overnight premium. Our night leg
  and IBS leg live here: look for refinements, not the base effect.
- **Money flows from leveraged ETFs:** LETF end-of-day rebalancing (Cheng-Madhavan, Ivanov-Lenkey,
  Shum et al.), volatility-ETP flows, 0DTE dealer hedging. Already dead: LETF-flow last half hour and
  night size-up (add. 34), LETF picks in the night leg (Study W). Say what is new.
- Anything else the search turns up that fits $2-25k: thin names, odd lots, auctions, short-dated
  options, tax placement between the accounts.

### Discount published strategies
Published anomalies lose a large part of their return after publication (McLean & Pontiff 2016:
~26% lower out of sample, ~58% lower after publication). **Mark every published edge down by at least
a third**, and by more when:
- the paper is old and the strategy is easy to run (cut by half or more);
- the edge lives in large, liquid names that funds can trade (more crowding);
- the source reports gross returns or a backtest with no costs.
A forum or blog idea with no paper gets no credit for its reported edge; rank it on mechanism alone.

### Rank and pick
Rank on: decayed %/yr at $2-25k after our costs × chance it survives our pass bar × independence from
the current legs (correlation; same-bet rule ≥ 0.7) × data in hand × build effort. Small size counts as
an advantage (no capacity limit in thin names, auctions, odd lots).

**Commit and push the candidate list before any backtest.** It is the record of what was chosen and
why.

## Step 2: test only the best few
Pick the **top 3-6** candidates. For each one:
- **Pre-register first:** append a dated amendment to research/drafts/round1_prose.md (source, the
  variants, pass bars, what gets reported) and commit it BEFORE computing any result. Program N = 669 (check round1_prose.md for anything later);
  report DSR at the new N.
- **Select on 2016-23 (or 2021-23 for the night pool), judge once on 2024-26.** Report both halves. For
  a Hugging Face model, judge only on data after its release/cutoff.
- **Use raw prices** (`load_sim(raw_price=True)`).
- **Costs:** the measured ones (night buys ~−2.5bp, sells ~0bp; QQQ 0.13bp; TQQQ ~1.5bp), stressed at
  2x. Whole-share rounding and the $2,000 margin / intraday minimums at $2.3k.
- **Pass bar (SHADOW), the same as every earlier study:**
  - increment > 0 in both halves at the stressed cost;
  - Newey-West t ≥ 2.0;
  - placebo ≥ 95th pct;
  - book max DD not worse by > 2pp;
  - 5y P(DD>50%) ≤ 5%.
- **Constraints:**
  - Taxable: short-term tax, wash sales vs the Roth (`wash_guard: roth_first`).
  - Roth: no shorting, no intraday margin, settled cash.
  - Regular session only (`signals.regular_clock`, `marketdata.rth_minutes`); label by
    `marketdata.trade_date`.
- **Do not redo the dead list.**

## Nothing gets switched on
Live code and live config are untouched. If a variant passes, write a spec for a switch (default
off, kill rule, tests) in its writeup; do not build or enable it in this round.

## Deliverable
- `research/drafts/max_edge_candidates.md`: the ≥ 25-row list, with sources, decay, counterparty and
  the dead-list check; the GitHub lookahead/cost notes; dropped ideas and why.
- One writeup per tested study in research/drafts/, and a NEXT.md entry for each (dead ones go in the
  do-not-redo table). Commit and push each study.
- **A final ranked table:** idea | source | verdict | %/yr and $/yr at $2.3k / $10k / $25k | capacity
  line ($100k / $500k, where it breaks) | who pays | what live evidence would change it.
- Say plainly what failed, and which outside sources turned out to have lookahead or no costs.
