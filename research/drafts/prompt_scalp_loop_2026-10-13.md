# Prompt: momentum scalp loop (confident +0.15% intraday signals)

Paste this as the /loop prompt, or run `/loop follow research/drafts/prompt_scalp_loop_2026-10-13.md`.

---

You are running an open-ended research loop on the swing-trader repo, focused on ONE question the user asked for:
**can we find intraday momentum signals confident enough that the price goes up at least +0.15% (15bp) before it goes
against us, and scalp that profitably after real costs?** Do not stop, summarize-and-wait, or ask "should I continue?".
Keep iterating until the user says stop. When a line of work ends (pass, kill, blocked), write it up and start the next.
If blocked on a user decision, log it under "Waiting on user" in the ledger and move on.

## 0. Read first (every new context window)
- `CLAUDE.md` (research memory, the research-priority gate, the data-buy rule, the validation protocol, and the
  2026-06 PDT change), `NEXT.md` (do-not-redo tables, especially the day-trading lab rows), `round1_prose.md` (program N).
- The day-trading lab: `daytrade/README.md` (honest starting point and the per-day earnings table), `daytrade/MISTAKES.md`
  (every fill-model trap already hit here; read all of it), `daytrade/PLAN_CHANGES.md`, `research/drafts/prompt_daytrade_lab.md`.
  New strategies are lab plug-ins (`daytrade/strategies/`, replay in `daytrade/research/*_replay.py`).
- This loop's ledger, `research/drafts/scalp_loop_ledger.md`. Create it if missing, with columns: iter, track, idea,
  class tags (mechanism / data / universe / time-of-day / counterparty), breakeven hit rate, ceiling at $10k, status, evidence.

## 1. The target, written as math (do this before every idea)
A scalp is: enter long at the decision time, exit at **take-profit +15bp**, a **stop at -S bp**, or a **time-out T**.
"Confident" means a **calibrated hit rate**, not a big mean: P(touch +15bp before -S) measured out of sample.
- Breakeven hit rate: `p* = (S + c) / (15 + S)`, where `c` = round-trip cost in bp (spread paid + slippage + fees).
  Example: S = 15, c = 4 -> p* = 63%. S = 10, c = 8 -> p* = 72%. Report p* and the measured p (with a CI) for every rule.
- Net per trade = `p x 15 - (1 - p) x S - c` (time-outs at their actual exit price). This must be > 0 at 2x cost.
- Ceiling gate (kill before coding if it fails): `trades/day x net bp/trade x share of account deployed x 50% capture
  x 250 >= +8pp/yr at $10k`. Report at $2.3k / $10k / $25k plus a $100k capacity line (thin names cap out fast).
- If the user meant **$0.15 per share**, not 0.15%, convert per name (15c on a $20 stock = 75bp) and say which you used.

## 2. What is already dead here (do not redo, do not re-costume)
Grep NEXT/RESULTS/daytrade before any idea. Dead with numbers: the live noise-area breakout leg on QQQ/SMH and EVERY
fix to it (vol gate, exits, time-of-day, hold-to-close; leg OFF since 2026-10-11, re-arm only via `noise_rearm_watch`);
high-frequency QQQ/SPY 1-15-min momentum/reversal (minute autocorrelation ~0.01); last-half-hour momentum; first-hour
continuation; gap + premarket volume + VWAP reclaim (Lab-AS); 5-min ORB on Stocks in Play (Lab-AU, -23.5bp/trade);
VWAP trend flips (Lab-AW); +25% movers into the close (Lab-AX); halt reopen long/short (Lab-AY/BA); QQQ every-day
(Lab-BD); closing imbalance passive (Lab-BG); opening imbalance (Lab-AV, Lab-AT waiting); news-headline continuation
(NEWS-DRIFT, absorbed in ~5 min); single-stock noise legs ranked by dollar volume; late-day signed flow (LATE-FLOW:
real but ~1bp). **The common killer:** a few bp of gross edge against 5-20bp of real spread + slippage on stocks.
Any new idea must explain why its gross move is several times the cost, not just positive.

## 3. Tracks, rotated (never more than 2 in a row on one track)
- **A. Mechanism-first (60%).** A named reason someone else must push the price for minutes after the signal:
  aggressive buy-sweep bursts / order-flow imbalance at the minute scale (TAQ trade signs), ETF-to-constituent and
  leader-to-laggard lead/lag inside a sector at 1-5 min, index-futures/ETF lead on single names, short-sale-restriction
  (Rule 201) days and squeeze dynamics, new-high-of-day on abnormal relative volume with a tight spread, liquidity
  vacuum after a large print. Each idea states the counterparty and why it has not been arbitraged at 15bp.
- **B. Honest classifier search (25%).** A model that outputs P(+15bp before -S) from microstructure features
  (spread, depth proxy, signed volume, return path, relative volume, time of day, sector move). Purged, embargoed
  walk-forward CV only; calibrate (reliability curve) and act only on the top-confidence bucket. Mandatory nulls:
  label permutation within day and a time-shift placebo. The batch counts only if top-bucket precision beats both
  nulls AND clears p* at 2x cost. Change the feature family every 3rd B iteration.
- **C. Execution realism / infrastructure (15%).** Measure what a scalp actually pays per name and time of day:
  quoted vs effective spread from NBBO, fill rates of a +15bp limit take-profit (did trades print THROUGH it with size?),
  stop slippage, queue position for passive entries. Build reusable cost tables that A and B must use.

## 4. Data, windows and fills
- **Data you have:** Alpaca SIP minute bars, trades and quotes 2016+ (keys in `.env`; inactive symbols included);
  **WRDS TAQ millisecond trades + complete NBBO 2003-2026** (`taqm_YYYY`; `research/sim/late_flow_day.py` shows the
  server-side per-day SQL pattern; <= 4 concurrent connections); CRSP daily for universes. No data purchases
  (Databento credit is nearly gone; the data-buy rule applies).
- **Touched windows:** single-stock intraday 2022-26 (the Lab-A* studies) and QQQ/SMH 2016-26 are TOUCHED. For a new
  rule class, discover on one era and judge once on another (e.g. discover TAQ 2010-14, judge TAQ 2015-19 or 2003-07),
  then forward paper in the lab. Never re-split 2021-26 and call it out of sample.
- **Fill rules (from daytrade/MISTAKES.md; non-negotiable):** market entries pay the ask (or the measured effective
  spread); a limit take-profit fills only if a lit trade prints at or through it with enough size (no off-exchange
  sub-penny prints); a stop already through the market fills at the next trade, not at the stop; if TP and stop are
  both inside one bar, assume the stop hit first unless tick data says otherwise; every feature must exist AT the
  decision timestamp (sample the field at that time on several days before registering). Report the result under an
  optimistic and a pessimistic fill bound; judge on the pessimistic one.

## 5. Account rules (date-versioned; check before economics)
- PDT day-trade counting is gone (FINRA 4210 amendments effective 2026-06-04; Schwab stopped counting 2026-06-08;
  intraday margin buying power for margin accounts >= $2,000 from 2026-07-13). Scalping belongs in the **taxable**
  account (~$4.5k). The Roth has no intraday margin and settles T+1: a sell's proceeds cannot re-buy the same day
  without good-faith-violation risk, so the Roth gets at most one round trip per settled dollar per day.
- Short-term gains are taxed at the ordinary rate: report after-tax %/yr at the user's bracket (35% as in CPC).
- Long-only unless a short idea also states borrow availability.

## 6. Per-iteration protocol
1. Pick an idea that passes the diversity rule (change >= 2 of mechanism, data, universe, time-of-day, counterparty vs
   the last 10 ledger rows; no "variant", "v2", "with a filter"). Write the section 1 math first; kill if it fails.
2. Pre-register in `round1_prose.md` (rule, data, windows, fill model, gate, kill rule) and in `daytrade/PLAN_CHANGES.md`
   if it becomes a plug-in; bump N; commit; THEN read outcomes.
3. Run it via subagents (they return conclusions with file:line evidence; raw output stays in files).
4. Failure-mode checklist in order: data bug, lookahead at the decision timestamp, survivorship, selection, multiple
   testing (DSR at N), fill model (optimistic vs pessimistic), cost at 2x, hit rate vs p*, median vs ex-top-5, time-of-day
   concentration, overlapping trades. A fresh subagent adversarially attacks any PASS before it is accepted.
5. Verdict PASS / WEAK / KILL / DATA-LIMITED in the ledger, NEXT.md (do-not-redo if dead) and a short CLAUDE.md line.
   Commit with a short casual message.
6. A PASS goes to **forward paper in the day-trading lab only** (`daytrade/forward_log.py`, lab paper broker), with a
   REGISTRY entry in `swingtrader/daily/testing.py` in the same commit. Live money needs the user's explicit OK.

## 7. Hard limits (never cross without the user's explicit OK)
- No live orders, no changes to live config/sizing, nothing deployed or changed on the server (`ssh him` is read-only).
- No data purchases. No second look at a judged window. No editing a pre-registration after outcomes are read. No
  weakening tests or fill rules to make something pass.
- Keep the Polymarket project out of this repo.

## 8. Every ~5 iterations: checkpoint (then keep going)
Append to the ledger: what was tried, what died and why, the best measured hit rate vs its p*, the best net bp/trade
under pessimistic fills, the cost table so far, and "Waiting on user". If ~10 iterations produce nothing above the gate,
say so plainly in the checkpoint, name the class as dead, and open a different class (a new universe, horizon or
counterparty), not more variants. If the honest conclusion is that 15bp scalps do not survive retail costs at any
confidence level, write that conclusion with its evidence; that is a valid result.
