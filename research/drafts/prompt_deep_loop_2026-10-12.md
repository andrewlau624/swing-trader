# Prompt: deep research loop (diverse ideas + luck track + crypto)

Paste this as the /loop prompt, or run `/loop follow research/drafts/prompt_deep_loop_2026-10-12.md`.

---

You are running an open-ended research loop on the swing-trader repo. **Do not stop, summarize-and-wait, or ask
"should I continue?". Keep iterating until the user says stop.** When one line of work ends (pass, kill or
blocked), write it up and immediately start the next. If you're blocked on a user decision, log it in the
"Waiting on user" list and move to a different track. Don't sit idle.

## 0. Read first (every new context window)
- `CLAUDE.md` (all research-memory sections, the research-priority gate, the data-buy rule and the
  validation protocol), `NEXT.md` (do-not-redo table), `MISTAKES.md`, and `research/drafts/round1_prose.md`
  (current program N).
- This loop's own ledger, `research/drafts/deep_loop_ledger.md`. Create it if it's missing, with columns:
  iter, track, idea, **class tags** (mechanism / data source / asset / horizon / counterparty), ceiling at
  $10k, status, evidence path.

## 1. Goal
Raise **%/yr on the user's real money**: taxable ~$4.5k, Roth ~$7k growing +$7.5k/yr. Report every result
at $2.3k / $10k / $25k, plus one capacity line at $100k. The benchmark to beat is an **index fund at 8-10%/yr**
and the live book's realistic ~10-12%/yr. An idea matters if it adds **>= +8pp/yr at $10k** under
honest capture (<= 50% of the backtest effect), or if it makes the existing book materially more robust
(cuts drawdowns, keeps legs alive in bad regimes) at a cost of <= 1-2pp/yr.

## 2. Three tracks, rotated
Rotate in roughly this mix: **A 50% / B 20% / C 30%**. Never run more than 2 iterations in a row on one track.

### Track A: mechanism-first research (improve or replace the strategy)
Any of these is fair game: new edges, improving the live legs (robustness, sizing, regime survival,
the leg-health controller from the 10-12 chat), portfolio construction across legs, Roth vs taxable placement,
and execution. Pivot freely: if a direction gives only tiny gains, **name the class, mark it dead and leave it.**

### Track B: discovery by luck (random strategy search, done honestly)
The point is to find things no one would think to look for, without fooling ourselves.
1. **Generator.** Build a random-rule grammar once (`research/sim/luck_gen.py`): random feature(s) from the
   panels (price, volume, IBS, gaps, calendar, fundamentals, insider, short volume, crypto features) x random
   operator/threshold x random horizon (overnight / 1d / 5d / 20d) x random universe x long/short. Seed every run
   and log the seed.
2. **Discovery split only.** Score thousands of random rules on ONE discovery period/asset. Before scoring,
   write down which periods each data family has already touched (CLAUDE.md lists them), and keep a
   period/asset that no rule has seen as the confirmation set.
3. **Null calibration (mandatory).** Run the same generator on shuffled/permuted returns (and a time-shift
   placebo) to get the number of "passes" expected by chance. A batch counts only if the real survivor count
   clearly beats that null distribution. Otherwise the batch is luck, so log it and move on.
4. **Survivors.** Take the top few survivors that also have a plausible after-the-fact mechanism. Pre-register
   each in `round1_prose.md` (bump N by the number of rules *scored*, not just the survivors, or apply DSR at the
   true trial count), then judge it ONCE on the confirmation set at `tier` cost and a 2-3x cost shock.
5. Every 3rd Track B iteration, **change the grammar** (new feature families, new horizons, new assets). Don't
   just re-roll seeds.

### Track C: crypto
- Known so far: crypto IBS/reversal is **rejected** (`ibs_xasset_scan.py`), and `crypto_daily.parquet` is
  majors-only 2021+ (survivorship-flattered). Don't re-run IBS on crypto.
- **Access first (date-versioned):** before any economics, verify what this user can actually trade. US
  residency, Schwab spot crypto availability, Roth eligibility, US-regulated perps/futures (e.g. CME, Coinbase
  Derivatives), fees and minimums. Quote the source and date. Account access never changes a statistical verdict.
- **Data:** look for free public history with delisted coins (e.g. exchange bulk kline/funding-rate dumps).
  Verify depth, delisting coverage and timestamps (UTC day vs. US session) before using it. Paid data follows
  the data-buy rule (user OK required).
- **Mechanism ideas to rank (ceiling math first, then test only what clears it):** perp funding-rate carry /
  extremes, spot-perp basis, weekend and Monday-open effects (24/7 vs. ETF hours), spot-ETF creation/flow vs. spot,
  token unlocks and vesting cliffs (named forced sellers), exchange listings/delistings, stablecoin depegs, and
  liquidation cascades (forced flow with a named counterparty). Also cross-checks of equity mechanisms that
  should transfer (forced flow, auctions) rather than ones already rejected.

## 3. Diversity rule (hard)
Before starting an idea, compare its class tags with the ledger and with NEXT/MISTAKES/round1_prose.
- **Reject** it if it shares mechanism AND data source with any of the last 10 ledger rows, or if it is a
  known dead class in a new costume (new threshold, filter, window, universe slice, or asset with the same mechanism).
- Each iteration must change at least two of: mechanism, data source, asset class, horizon, counterparty.
- If you catch yourself writing "variant", "v2", "with a filter", or "tweaked", stop and pick something else.

## 4. Per-iteration protocol
1. Pick an idea that passes the diversity rule. Write the **ceiling math** first:
   `events/yr x net edge/event x share of account deployable x capture rate` at $2.3k / $10k / $25k / $100k,
   plus who pays, why it persists, independence from the book, and the cheapest kill test.
   **Kill before coding if the $10k ceiling is < +8pp/yr** (unless it's a robustness idea; see §1).
2. Pre-register in `round1_prose.md` (rule, data, gate, kill rule), bump N, commit, THEN read outcomes.
3. Run it. Broad exploration and heavy number-crunching go to subagents that return conclusions with file:line
   evidence; keep raw output out of the main context (bound commands, save logs, grep them).
4. Run the failure-mode checklist in order: data bug, lookahead, survivorship, selection, multiple testing (DSR),
   costs and 2-3x shock, median vs. ex-top-5, in the gap?, adverse fills, overlapping windows. Before accepting
   any PASS, have a fresh subagent adversarially try to break it.
5. Verdict: PASS / WEAK / KILL / DATA-LIMITED. Record it in the ledger, `NEXT.md` (do-not-redo if dead), and
   a short `CLAUDE.md` research-memory entry. Commit with a short casual message.
6. Anything that passes goes to **forward shadow only**, with a REGISTRY entry in `swingtrader/daily/testing.py`
   in the same commit (see CLAUDE.md).

## 5. Hard limits (never cross without the user's explicit OK)
- No live orders, no changes to live config/sizing, nothing deployed or changed on the server (`ssh him` is read-only).
- No data purchases. No touching judged/touched windows for a second look (NX 2003-15, SHAR-IBS, etc.).
- No editing a pre-registration after outcomes are read. No weakening tests.
- Keep the Polymarket project and its data out of this repo.

## 6. Every ~5 iterations: checkpoint (then keep going)
Append to `research/drafts/deep_loop_ledger.md`: what was tried, what died and why, any survivors, the current
best addition at $2.3k / $10k / $25k vs. the index, and the "Waiting on user" list. If the last ~10 iterations
produced nothing above the gate, **pivot the track mix or open a new class** (new asset, new data source, new
counterparty). Don't dig deeper in the same place. Then continue the loop.
