# Pending decisions

Short, current, and the first thing to read when picking this up again.
Full evidence lives in `RESULTS.md`; this file is just what is *waiting*.

> **Standing note (2026-09-30, replaces 09-29): % return at small balances first.** Rank ideas by
> %/yr at $2-25k (taxable ~$2.3k, Roth $1-3k + $7.5k/yr). Large sizes ($100k/$500k) are one
> capacity line, not a ranking criterion. (Also in CLAUDE.md.)

---

## Day-trading lab (2026-10-01, Lab Rounds 18-38): 25 studies (intraday, events, multi-day, market-neutral, vol premium, cross-section), four momentum-family PASSES on 1963-2015 (BT, BW, BY, BZ) that all lag the index in 2016-26; paper shadows only; recorder LIVE (program N 744)

**Overnight bottom line (for the user, 2026-10-01 morning).**
- Every intraday idea tested at real costs is dead. The recurring pattern:
  - Single-stock intraday signals gross 0-10bp; the spread costs 5-40bp.
  - The two strong effects found are untradable at retail:
    - Post-halt slides (−130bp/30 min): shorts profit only on unborrowable names.
    - The closing-imbalance signal (+6bp, real out of sample): the spread eats it, and passive entry is adversely
      selected.
  - The one cheap instrument (QQQ) carries the edge the live noise leg already trades.
- Three false passes were caught by the outlier/fill checks (MISTAKES.md):
  - a stop filled above the market;
  - TRF sub-penny prints counted as fills;
  - compounding stats.
- Two registrations were untestable (Nasdaq publishes near prices only from 09:28 / 15:55).
- **Databento: lab $100.22 + main ~$16 = ~$116 of the $125 credit. No more pulls.**
- **Recorder: live on the server since 2026-10-01 09:20 ET** (first session: ~97k rows by 11:30, no gaps, 106 MB).
  Note: the 09:25 gapper sweep picked a corporate action (CTVA −81%, a separation). **Fixed in 1ebf2c8** (it now skips
  |gap| >= 50% and split ratios); it reaches the server on the next `make pull` there (the timer picks it up the next
  morning, no reinstall needed).
- **Lab-BH/BI (announcement-gap drift, daily, multi-day): DEAD.** In 2022-26 gappers UNDERPERFORM SPY by 185bp over
  20 days (every year), but the short + hedge judged on unseen 2017-21 fails (t 0.6; 2018 and 2020 lose).
  study_lab_bh_bi_event_drift.md.
- **Lab-BJ (calendar-month seasonality, monthly top 20 of 500): DEAD** (−69bp/month vs the universe 2021-26).
- **Waiting on the user: insider-purchase drift (not registered, no N).** Officer/director open-market buys
  (Lakonishok & Lee 2001; Cohen, Malloy & Pomorski 2012) are the strongest untested multi-day idea with free data:
  SEC quarterly Form 3/4/5 datasets. The SEC returns 403 without a contact email in the User-Agent. The repo's
  convention (`swingtrader/daily/news_judge.sec_headers`) uses `NOTIFY_EMAIL` or `SEC_USER_AGENT` from `.env`, and
  the Mac's `.env` has neither. Set one (your choice) to unblock; the lab will register and run it.
- **Lab-BK (short LETF pairs), Lab-BL (stock pairs), Lab-BM (post-split drift), Lab-BN (SVXY in contango): DEAD.** Crypto was already dead in RESULTS.md.
- **Lab-BT: PASS (with caveats).** Long top-decile momentum beat the market by +40bp/month 1963-2015 (t 3.0; 2x
  positive both halves, the second only +4bp), but the excess was about 0 in the 2000s, the 2010s and 2016-26 after
  costs, with crash risk (−50% worst 12 months). A priced risk factor, not a free edge.
  -> **Built as PAPER SHADOWS**: `make daytrade-momentum` logs, monthly, the top 20 of 500 stocks by 12-1 momentum
  (Lab-BR) with Lab-BU's vol-scaled weight, and the top 5 of 20 industry ETFs (Lab-BW passed 1963-2015 in every
  decade; the ETF version Lab-BX tied SPY in 2017-26). No orders. study_lab_bt_momentum_history.md.
- **Forward evidence, automatic (after `make pull` on the server):** the recorder now logs, at the end of each
  session, Cboe SKEW's z-score (Lab-CC) and, on the first session of each month, both momentum shadows with the
  vol-scale and trend-filter fields, to `data/daytrade/forward-signals.jsonl`. No orders.
- **Nothing to switch on.** The live book is unchanged. The next real look is Lab-AT after 40 recorded sessions
  (~early Dec). Expect few signals (Lab-AV).

Brief: `research/drafts/prompt_daytrade_lab.md`. Lab README: `daytrade/README.md`. It has its own package, account
and state, and does not touch the live book.
- **Recording: NOT YET RUNNING.** The recorder is built and tested against fake messages. This session could
  not write to the server. On the server: `make pull && make daytrade-smoke && make daytrade-persist`, then
  check `make daytrade-status` after the first session. It starts 09:20 ET, runs its own unit (350 MB cap)
  and its own token copy, and records the core 5 ETFs + 10 gappers.
- **In replay:**
  - **Lab-AS (gap + premarket volume, VWAP reclaim): DEAD.** 3,308 trades 2022-26: −18.9bp/trade at 1x
    (t −3.2), −36bp at 2x (both halves negative), gross −1.7bp, placebo 59th pct. $2.3k -> $568 through
    the risk layer. `research/drafts/study_as_gap_vwap.md`.
  - **Lab-AU (5-min ORB on Stocks in Play, Zarattini-Barbon-Aziz 2024): DEAD** (and already dead in RESULTS.md).
    −23.5bp/trade at 5bp/side; the optimistic fill bound grosses ~+10bp, below costs. study_au_orb_in_play.md.
  - **Lab-AW (VWAP trend, QQQ/TQQQ): DEAD.** Real signal (+6.7bp/day gross, placebo 97th) but 16 switches/day
    cost more. study_aw_vwap_trend.md.
  - **Lab-AX (+25% movers held 15:00-15:55, long): DEAD.** −33.7bp/trade at 20bp/side, H2 −53.6; gross +6bp: the run-up
    is over by 15:00. study_lab_ax_late_mover.md.
  - **Lab-AY (buy the reopening after a halt, up or down): DEAD.** Both lose ~−130bp gross in 30 minutes (t −4..−5).
    A first "PASS" was a fill-model bug (MISTAKES.md). The post-halt drift is DOWN either way, which points to the
    short side (Lab-BA). study_lab_ay_halts.md.
  - **Lab-BA (short the reopening after a halt): DEAD, closes the halt family.** +40bp means are a few 40-55%
    collapses; medians −100..−308bp, negative without the top 20, t ≤ 1.2; on easy-to-borrow names −70bp gross.
    study_lab_ba_halt_short.md.
  - **Lab-AZ/BB/BC (Nasdaq closing imbalance, Databento, $64.88): signal REAL, not tradable.** A big early imbalance
    predicts ~+6-7bp from 15:54 to the close, out of sample (H2 holdout, placebo 100th pct). But crossing the spread
    at 15:54 costs as much: Lab-BC H2 +0.3bp net at 1x, −5.7 at 2x. Lab-AZ was untestable (near price published only
    from 15:55). study_lab_bb_close_imbalance.md. Main BD found the effect already priced into night returns.
  - **Lab-BD (QQQ only, every day, H2 holdout): DEAD.** Gross fell from +3.2bp (H1) to +1.3bp (H2): +0.17bp net.
  - **Lab-BE/BF (Nasdaq opening-cross imbalance, Databento $35.34): DEAD.** Reversal is the wrong sign (−7.8bp gross,
    placebo 0.4th). The continuation was +13.5bp gross in H1 but +1.9bp in H2, below the ~3.7bp exit cost (not
    registered: H2 is spent). Lab-BE was untestable (near price only from 09:28). study_lab_be_bf_open_cross.md.
  - **Lab-BG (closing imbalance, passive entry at the touch): DEAD.** Adverse selection: filled trades earn −0.6bp mid ->
    close in H2; the captured spread leaves +2.2bp, t 1.6. A first "pass" counted off-exchange sub-penny prints as
    fills (MISTAKES.md). study_lab_bg_passive_close.md.
  - Databento credit: lab $100.22 + main BD/BE ~$16 = ~$116 of $125. No more pulls.
  - **Lab-AV (Lab-AT's opening imbalance on SIP ticks, QQQ/SPY): DEAD, underpowered.** The 0.20 QI threshold fired on
    89 of ~2,400 symbol-days (NBBO sizes sit within ±0.15); +3.3bp t 1.35, 2x H2 negative.
    study_lab_av_open_imbalance_ticks.md. Lab-AT (the same rule on the recordings) will fire rarely too.
  - **Lab-AT (opening L1 imbalance): waiting.** First look after 40 unflagged recorded sessions (~early Dec).
  - **Decision for the user:** Alpaca's free plan has historical SIP tick NBBO quotes and trades back to
    at least 2018 (verified). Lab-AT could be re-registered on that history now (+1 N) instead of waiting
    8 weeks.
- **Paper: not started.** It needs a second Alpaca paper account (`ALPACA_DAYTRADE_API_KEY/_SECRET_KEY`), a
  lab Schwab account (`SCHWAB_DAYTRADE_ACCOUNT_NUMBER`) and a strategy that passes replay. None exists yet.
- **$500 gate** (README §8):
  - replay > 0 at 2x costs in both halves, t ≥ 2, placebo ≥ 95th pct;
  - ≥ 40 paper round trips, with drift < half the edge;
  - 0 rule breaks;
  - HALT tested on the live lab account at $0 risk;
  - the guard proven on the server;
  - the user's written approval.

  At $500 (cash, one turn a day) even a 20bp edge is ~$1/day: tuition.

> **Read first (2026-10-01 overnight): `research/drafts/overnight_2026-10-01.md`.** The next switch, `moderate10c`
> (conviction + 15% name cap), simulates at +16pp/yr (37.6 -> 54.0% at $2.3k, 2.5bp/side; +9pp at tier_hi), both halves.

## Round 26-27 (2026-10-01, overnight): Databento key -> closing imbalance (BD) and IBS opening gap (BE) running; everything-on simulated
- **Everything-on as ONE simulation** (study_everything_on.md; live sizing map, official-cross night returns,
  2.5bp/side, fixed $10k): live today 39.4%/yr (Sharpe 2.0, maxDD −14%) -> + tug-of-war 42.7 -> + 15% name cap
  51.4 -> + conviction 60.3 -> + 4x intraday 64.9 -> + 1.3x overnight **76.6%** (Sharpe 2.2, maxDD −21%,
  P(DD>50%) 0%). At tier_hi: 22.3 -> 42.0%. Edge-halves (the program's standard haircut): 17.8 -> 31.1%.
  Roth cash book: 20.9% (EH 10.0%), + tug-of-war + 15% cap 31.3% (EH 14.5%).
- The weekly digest's plan lines are now exactly these edge-halves numbers (were judgment calls: 17% / 22% / Roth 15%,
  the Roth one too high); its backtest lines are the simulation (were a sum of separate estimates, too low).
- **BD (closing imbalance at 15:50, Databento): DEAD.** Sell/buy-imbalance buckets flip sign between halves; the
  tilt is +0.3pp (t 0.6, shuffle 62%); dropping buy-imbalance picks is −6pp (lost exposure: shuffle 60%). The
  imbalance feed is not worth buying for the night leg. study_bd_closing_imbalance.md.
- **BE (skip IBS entries indicated to gap up at 09:28): DEAD.** Gap-up entries earn as much or more (2024-26:
  +51bp at ≥ 0.5%, +84bp at ≥ 1%); skipping costs −1.9..−2.0pp (t −1.5). study_be_ibs_open_gap.md.
- **BF (night picks that LULD-halted that day; lab's idea): DEAD — too rare.** 0.6% of picks halt; down-halted
  picks −86 / −43bp (n 9 / 25) but dropping them is +0.6pp, t 0.5. study_bf_halted_picks.md.

---

## Rounds 20-21 (2026-10-01): free-data night tilts — AX, AY DEAD; AU3 holds on cross prices and combines (N 682 -> 686)
- **AX (Round 20): trailing closing-/opening-cross share of volume** (Alpaca auction sizes, free; the stand-in for
  closing imbalance, which stays parked: the user does not want a Databento account unless necessary). AX1
  closing share flips halves (t 0.1); AX2 opening share +1.2pp both halves but t 1.5, placebo 94%: DEAD.
  study_ax_auction_share.md.
- **AU3 robustness:** TOW built from the official crosses still +2.4-2.9pp, t 2.5-2.6 (R1); under the moderate
  15% name cap +4.4pp, t 3.0, and on top of tilt v2 +2.7pp, t 2.5 (R2). No conflict with either.
- **Noise leg after publication (report, study_noise_decay.md):** SPY's rule went to Sharpe −0.4 after May 2024
  (matches a public replication); QQQ ~halved (4.1 → 2.5bp/day, t 1.1 post); SMH intact (5.1bp/day). No action
  (kill rule stands); plan QQQ at ~2.5bp/day.
- **AY (Round 21): FINRA daily short-volume ratio, both signs: DEAD** (|inc| ≤ 0.4pp, t ≤ 0.6, shuffle 53%).
  study_ay_finra_short.md.

---

## Round 23 (2026-10-01): LLM news judge — BUILT, SHADOW, forward test pre-registered (N 689)
- After the 15:40 orders, an LLM — **OpenCode Go `deepseek-v4-flash`** (user's choice, Round 23b; Claude available
  via `news_judge_provider: anthropic`) — reads each night pick's news + SEC filings since the previous close and logs
  fundamental / liquidity / unclear + confidence to `state/news-judge.jsonl`. Never changes an order; failures are
  logged and swallowed. ≤ 20 new calls a night, shared by all books (pennies/month). `daily.news_judge: shadow`
  (off = disable); no-op without `OPENCODE_API_KEY` in .env.
- **Server setup:** add `OPENCODE_API_KEY=...` to .env (SEC contact = the Resend `NOTIFY_EMAIL`), then `make news-smoke SYM=<a ticker that fell today>`.
- **Gate:** `make news-eval` prints progress; the BA1 verdict (fundamental conf ≥ 0.7 at x0.25) is read once at
  300 judged picks (~2-4 months), scored on the official crosses. Forward only: a historical LLM backtest is
  contaminated by the model's knowledge.

- **Round 24 BB (forward): 15:40 quote imbalance.** The night leg now logs Schwab bid/ask sizes + day volume per
  pick in `daily-decisions*.jsonl` (free stand-in for the parked imbalance feed). `make qi-eval`; verdict at 300.

---

## Round 25 (2026-10-01): LLM judge on PAST picks — BC does not run (probe void; model knows events through 2025-10)
- Probe v2: `deepseek-v4-flash` answered all 8 dated questions through Oct 2025 correctly, and invented "Roku" for
  a fabricated Apple acquisition. Every 2025 pick is inside the model's memory, and the clean 2026 window is too
  short for 300 picks. Historical verdicts collected are not scored. study_bc_news_hist.md.
- The forward test (BA, `make forward-status`) is the only valid test of the judge.

---

## Round 22 (2026-10-01): Roth ex-dividend overnight capture — AZ DEAD (N 688)
- Large caps going ex do drop by only 0.90-0.96 of the dividend (+7.4bp / +3.9bp vs SPY per event, 2021-23 / 2024-26),
  but that is one round trip: as a sleeve on idle Roth cash it is −0.1..−0.8pp/yr at 2.5bp/side, −5pp at 5bp,
  matched placebo 87-90%. study_az_exdiv_roth.md.

---

## Round 19 (2026-10-01): outside-first scan — AU3 tug-of-war tilt SHADOW, AW restates the night leg, AV dead (N 677 -> 682, counting the lab's Round 18)

Brief: `research/drafts/prompt_max_edge.md`. 44 sourced candidates (`max_edge_candidates.md`); summary
and ranked table `study_round19_summary.md`. Pre-registration dc53fcb (branch `round19-max-edge`).
- **AU3 — SHADOW (the one new edge).** Tilt night picks by the 20-session "tug of war" count (overnight
  up, day down; Akbas et al. JFE 2022). Monotone terciles in both halves (−13 / +11 / +24bp net 2024-26);
  ~orthogonal to vol20/depth/prev. V7 +3.1 / +3.2 / +2.8pp/yr at $2.3k / $10k / $25k (+$70 / +$323 / +$705),
  t 2.6-3.0, placebo 99-100%; Roth +$64 / +$296 / +$645. Holds on auction prints and in a second
  implementation. Against it: DSR 0.46 at N 680, 2022-23 ≈ 0, and it needs the uncapped post-tilt weights
  (a hard 10% cap after the tilt cuts it to +0.4pp). **BUILT, OFF:** `daily.night_tilt_tow: false`; the
  15:40 log prints `[night] tow shadow:` and decisions jsonl records `tow`. **Gate = `make review` §9:** turn
  on (`night_tilt_tow: true`) at ≥ 300 night round trips if high-TOW (≥ 6) out-earns low-TOW (< 4); same rule kills it.
- **AW — REPORT: the backtest's next open is the vendor first print, not the cross.** On Alpaca's official
  auction prints the night leg earns 3.8bp/trade less (t −7.5; worst < $10). Every book with a night leg is
  ~2pp/yr lower (V7 2.5bp: 34.6 → 32.3% at $10k; Roth cash: 23.0 → 20.9%). No verdict flips.
  **Re-run AQ on crosses: Roth cash IBS+night vs IBS-only crossover 3.7bp/side (vendor 5.4; 2021-23 1.9)** —
  the `roth_cash_ira` gate is now live night cost ≤ ~3bp/side (measured ~0). IBS ETF opens audited too:
  −0.3..−0.7bp/leg, immaterial. New night studies use `auction_audit_picks.pkl` (`auction_audit.with_rets`).
- **AV — IBS state exits DEAD.** IBS > 0.5 exit −5.9pp (t −2.3); close > prior high −0.8pp (t −0.1).
- **AU1/AU2 DEAD.** 20d mean overnight return as a tilt t 1.6; as a filter −1.6pp at 2.5bp.
- Not tested: closing imbalance (data: candidate-only Databento pull may fit the $125 credit; live NYSE
  feed $588/yr via Massive) and HF forecasters (clean holdouts too short to have power).

---

## Round 18 (2026-09-30): two ideas from a quant Discord — AS, AT both DEAD (N 669 -> 675)

Triage, results and an AQ correction: `research/drafts/study_as_at_discord.md`. Most of the chat
was already covered (order-book imbalance: data; decay monitors: add. 37; ML: Study E; placebos =
the "null model"). Two untested ideas, pre-registered (b025d63):
- **AS: split the overnight budget IBS/night by trailing metrics (softmax of Sharpe, inverse vol)
  — DEAD.** At 2.5bp/side, ~0 to −1.5pp/yr. The tier_hi "gains" (AS2 +2.5..+3.4pp, t 1.8) come only
  from a lower mean night weight (0.40) when the night leg nets ~0. That is AQ's cost gate again, not timing.
- **AT: vol-ratio (10d/60d) and 50d trend-slope filters on IBS picks — DEAD.** VR gates flip sign
  vs the 2016-20 holdout. **Trend filter is harmful: −7pp/yr, t −3.1.** Downtrend dips revert the
  most (+72bp vs −1bp in 2024-26). Never add a short trend filter to an MR leg.
- **Correction to AQ:** its cost sweep is PER SIDE (`ret − 2·c`), not round trip. The brief's 2×
  stress (5bp RT) is 22.0%/yr for the cash-IRA book, not 19.0%; the night crossover is ~5-6bp/side
  (~10-12bp RT). Conservative error: the IBS+night Roth verdict stands, with a wider gate.

---

## Round 17 (2026-09-30): more %/yr at $2-25k — AL/AQ Roth cash book SHADOW, AP dead, AM/AN/AO dead or report (N 642 -> 669)

Brief: `research/drafts/prompt_small_account_profit.md`. Pre-registration: round1_prose.md Round 17.
- **AL + AQ: the idle Roth — SHADOW (the one new thing).** The Roth has never traded (blocked on
  `ROTH_LIMITED_MARGIN`). A plain cash IRA is GFV-safe on the IBS leg (buy open d+1, sell open d+2,
  the funding sale's T+1 date) and the night leg (buy close d, sell open d+1); only the 3x-ETF
  intraday leg needs limited margin. **The cash-IRA book is IBS .5 + night .5**: at the brief's
  cost of 5bp/side (~10bp round trip, ~4x measured) it earns **19.0%/yr**; at the brief's real 2x
  stress (2.5bp/side = 5bp RT) **22.0%** (Round 18: AQ's sweep is per side). At 5bp/side: halves
  13.0/26.0, NW t vs BIL 3.06, placebo 99%, P(DD>50%) 0%, maxDD −12% (= M3). **AQ corrected AL:**
  the earlier "IBS-only" call used `tier_hi` (15-50bp), which is 5-10x measured, not the brief's 2x.
  The night leg's **crossover is ~6bp PER SIDE (~12bp round trip; Round 18 correction: AQ's sweep was per side)** (night-only: 0bp 31.3%; 5bp/side 18.9%; tier_hi −3.4%); the
  taxable V7 book is 32.0%/yr at 5bp/side, 18.6% at tier_hi. So run IBS+night now with the cost gate;
  IBS-only (17.9% at tier_hi) is the fallback above ~6bp/side. The delay costs ~$890-1,010/mo vs idle.
  Spec: `daily.roth_cash_ira` (default off, IBS+night, no intraday) — BUILT + tested.
- **AP: IBS selection — DEAD.** Cross-sectional rank-1 (threshold/always), all-18 rank-1, rank-2 and
  a stricter 0.1 gate all lose −0.3..−7.6pp vs the shipped top-3/IBS<0.2 leg. The overnight-reversal
  edge needs the shipped breadth.
- **AM: night-leg limit orders — DEAD.** Best realistic close-buy (20bp below 15:50) is +0.96pp in
  2021-23 but +0.15pp 2024-26, NW t 1.74. Sell-side limits lose (−1.6..−2.6pp). The buy-at-the-low
  upper bound (+7.6/+8.7pp) is look-ahead. add. 13's +2pp was optimistic; needs quotes.
- **AN: pick-quality classifier — DEAD.** A point-in-time EDGAR classifier (fixes Study U's mislabels)
  confirms FOREIGN ADR picks earn ~+5bp and US operating ~0, and LETF is not an edge (Study W). The
  tilts are ≤1.3pp/yr at tier_hi and fail t ≥ 2. FOREIGN is only 1.7% of picks.
- **AO: whole-share drag — REPORT.** ~2.0pp/yr at $2.3k (tier), ~0.2pp by $25k. IBS top2 +0.63pp,
  cheaper look-alikes +0.48pp, top2+look (post-hoc) +1.0pp — short of the 2.0pp adopt bar.

---

## Round 16 (2026-09-30): the conviction trade, the user's ideas (prompt_conviction_research.md)
**Bottom line (study_round16_summary.md):**
- The shipped rule is already the best version the data finds. Magnitude sizing, confirmations, exits, more setups
  and more TQQQ weight are all dead.
- Two things add money, and neither touches the signal:
  (1) switch the built trade on: +$3.4k/yr at $100k, +$16.9k at $500k;
  (2) later, run it in MNQ: SHADOW, +$2.7-5.6k at $100k. It needs a futures-API broker and ≥ $30k.
**Small-account priority (user, 2026-09-30): % return at today's size first.**
- MNQ (≥ $29k) and the L1 recorder are parked. The small-money levers are, in order:
  1. Conviction on (`DAILY_LIVE_PROFILE=moderate10c`): +3.3pp/yr at mult 2. Gate: ~5 clean intraday days in review §7.
     Fixed 49a0b07: the conviction shadow now scores trades held to the close (it dropped ~1/3 of them).
  2. `DAILY_INTRADAY_MULT=3.33|4` (built, default empty = broker ~2.48). With conviction on, it lifts the
     turn-on value to ~+5.1pp/yr (AI, mult 4). Add. 40 rates the multiplier itself SHADOW (t 1.6).
     Gate: Schwab.com Balances shows Intraday Margin Buying Power ≥ 3.5x equity. Revert by emptying it.
- **AF: size the conviction weight by predicted magnitude: DEAD (N 623).**
  - m̂ (gap, range, rvol, VIX at 09:30) predicts the day's size (R² 0.13-0.24) and the trade's |gross| (corr +0.22..+0.31).
  - The trade's EV peaks in the MIDDLE tercile (+34..+41bp in every half), and the loud tercile is −44bp in 2024-26.
  - Every variant (m̂ .5/1/1.5, 0/1/2, VIX .5/1/1.5, inverse) fails both-halves and t ≥ 2 (best full t +0.5).
  - Keep the flat 0.5. TQQQ capacity is fine to $500k (median 0.8% of the entry minute). study_af_magnitude_sizing.md.
- **AG: confirmations at the breakout minute: DEAD (N 624).** No confirmation raises EV monotonically: strength, SMH/SPY/IWM
  agreeing, breakout-bar volume, VIX, VIX9D/VIX. The only monotone one (time of day) loses when used.
  Breadth and NQ-lead are untestable (no data). Most of them peak in the middle tercile (≈ one vol observation, post-hoc).
  Forward check only: join Cboe VIX to the `[conv]` shadow log by trade date; at ~60 round trips, compare VIX(d−1) > 21 trades with the rest.
  study_ag_confirmations.md.
- **AH: exits: DEAD (N 630).**
  - Targets cut winners, as predicted: 2u −1.5 / −2.0pp/yr (2016-23 / 2024-26), half-off −0.7 / −1.0.
  - The pullback limit entry fills on the losers: −7 / −5pp, t −2.8.
  - A 1u stop halves the worst trade (−7.9 → −4.1%) but is −2.1pp in 2024-26 (t 0.6).
  - Keep the band/VWAP exit. study_ah_exits.md.
- **AI: more capital for the conviction trade: DEAD as variants (N 634). Turning the built switch on is the one positive.**
  - w 0.75 / 1.0 in TQQQ adds ~0 (t 0.5): each unit takes 0.75 of margin from the noise leg.
  - w 2.0 via MNQ: +15..+35pp/yr, t 2.2, but maxDD −36% and P(DD>50%) 38%.
  - Turn-on (0 → 0.5), mult 2: +3.3pp/yr 2024-26, t 1.5; P(DD>50%) 0.9 → 1.7%.
    +$844 / +$3.4k / +$16.9k per yr at $25k / $100k / $500k (pre-tax).
  - The trade's own edge ≈ +11%/yr per unit weight at 3bp/side, NW t ≈ 2.2 over 2016-26. study_ai_capital.md.
- **AJ: the conviction trade in MNQ instead of TQQQ: SHADOW (AJ1 w 0.5, AJ2 w 0.75; N 637).** Same trades
  (corr 0.999 with TQQQ); cheaper; frees TQQQ's 75% margin for the noise leg; 60/40 tax.
  - AJ1: +3.3 / +4.1 / +2.5pp/yr (2016-20 / 21-23 / 24-26), t 4.3, P(DD>50%) 2.0%. AJ2: +5.1 / +9.9 / +5.3, P(DD>50%) 3.5%.
  - **Blocker: Schwab's Trader API cannot place futures orders** (also true of every earlier "MNQ past $160k" plan).
    It needs a second broker (e.g. IBKR); parked cash there costs an est. 0.5-1.5pp/yr, not simulated.
  - Needs equity ≥ ~$29k (one contract ≈ $43k). $/yr AJ1: $100k +$2.7k, $500k +$15.9k.
  - Spec only: `conviction_instrument: tqqq | mnq`, default tqqq; gates and kill rule in study_aj_mnq.md.
- **AK: more setups: DEAD (N 642).**
  - A second TQQQ breakout after a failed first is positive in every half (+0.4..+0.9pp/yr) but t 0.9.
  - SMH / SPY / IWM on no-TQQQ days: 0 / −1.7 / −7.0pp in 2024-26 (IWM t −2.7). SPY is the same bet (corr 0.75).
  - Latency: a 1-minute fill delay costs 2.4bp of 15.3bp per trade (−16%), so faster triggers have little to gain.
  - The L1 recorder was not built (it runs on the live server: user's call). study_ak_setups_latency.md.

## Round 13 (2026-09-30): the "use the day" ideas — Z, AB dead; AA small; AC needs data; AD is the news (N 619)
- **Z SPX put-write overlay: DEAD.** PUT (monthly) is positive every period (+4.9..+8.5%/yr over BIL at tier_hi)
  but fails NW t (1.93 < 2.0) and the crash bound (−15.5% in 21 days, 2020-03). WPUT and iron condors are
  negative after costs. Do not rerun with a new k. In the Roth, PUT loses to a held index (8.4 vs 15.2%/yr).
- **AA box financing:** the overnight debit averages only 3.6% of equity at 1.3x, so it saves ~$320/yr at $100k;
  at 2.0x ~$1.7k/$100k. Only worth it with the MAX profile at ≥ $100k. $0 today (leverage off).
- **AB fade QQQ inside the noise band: DEAD** (−2..−4pp/yr at 1bp/side, NW t −1.1..−1.3, placebo 41-82).
- **AC closing imbalance:** untested; needs Databento/Nasdaq imbalance data (2018+, $125 free credit may cover
  a test) and a paid live feed. User's call.
- **AD SPY held + noise overlay (taxable): beats the full book after tax at every size ≥ $25k** (MOD, MNQ:
  $100k 21.5 vs 14.5%/yr; $1M 19.1 vs 11.2), both halves pre-tax. Not a new edge: beta held for tax deferral
  plus the uncorrelated noise leg. Costs: max DD −17% (2021-26) / −31% (2020) vs the book's −10%. Taxable only
  (Roth has no intraday margin). **Decided (Round 14): switch the taxable account at $100k, not $25k.** Live code
  caps the noise leg at 1.0 on top of held SPY, and at a 10%/yr index the overlay only ties the book at $100k and
  loses at $25k. Gates: noise not killed, >= 60 live sessions, fills <= 1.5bp/side, user re-confirms the drawdown.
  Build `daily.taxable_mode` when taxable nears $100k.
  research/drafts/study_z_ad_day_ideas.md.

## Study T (2026-09-29): SEC offering filings on the night picks -> SHADOW (N 607)
E3 (424B or S/F-1/3 accepted between the prior close and 15:40) DROP passes the pre-registered
bar at tier and tier_hi, but only after fixing an ETN mapping bug (BMO's 424B flood), t −2.13,
most of it 2024-26. Not adopted. The OOS check is a rerun of `night_filings.py` on post-09-29
picks at ~100 events. Side note: mapped (operating, still-filing) picks net −11bp vs unmapped
+15bp at tier; worth its own pre-registered look. Details: research/drafts/study_t_filings.md.

## Study U (2026-09-29): dead as registered, but it found where the leg's gross is richest (N 609)
Diagnostic: leveraged/inverse ETF picks +45bp gross (2024-26) and foreign ADRs +41bp vs US operating
stocks +17bp. Study W then showed the LETF gap is leverage, not edge (dead, N 611). ADRs untested.

## Study V (2026-09-29): the night leg does not scale — cap it in dollars
Best case (sqrt(Q/ADV), Y 0.5) its $/yr peaks at ~$250k of equity (~$11k/yr) and turns negative
by ~$1M; auction-sized impact models put the peak far lower. Plan: cap the night leg at a fixed
$ size (shared by taxable + Roth), send growth to IBS / noise / MNQ, and start logging auction
participation per fill so Y can be fitted from ~$25k. study_v_capacity.md.

## 23/5 trading (from 2026-12-06): the bot is session-agnostic; regime check pre-registered
- Every leg trades only the 09:30 / 16:00 auctions or the regular session, which 23/5 does not change.
- The book's session now comes from the exchange's REGULAR-hours calendar (`signals.regular_clock`);
  the broker clock is a canary (`[session]` warning at 09:15 if it drifts, e.g. a 20:00 "close").
- Daily bars are labelled by trade date (evening stamps roll forward, `md.trade_date`).
- 09:15 canary: yesterday's SPY/QQQ daily bars must equal regular-hours minutes (warns if not).
- Intraday open: Schwab's quote open is cross-checked against the 09:30 consolidated minute (>10bp -> minute).
- After launch, watch: the first `[session]` warnings; `make review` section 1 (live picks vs the
  RTH-minute replay: catches a quote high/low that starts including the overnight session).
- ~March 2027: run the pre-registered 23/5 regime check (round1_prose.md Round 11).

## Study X + scale plan (2026-09-29): impact cap BUILT (off), measurement loop live (N 614)
- `daily.night_impact_y: null`: turn on (4, or review section 8's fitted UB) once the account passes ~$25k.
- Night decisions now log `adv20` / `pct_adv`; `make review` section 8 fits the impact coefficient Y.
- Scale order (research/drafts/scale_plan.md): night leg stops ~$100-250k; noise QQQ ~$1M (MNQ past
  ~$160k fixes both tax and capacity); SMH ~$250k; IBS low single-digit $M.

## Live checkpoint (2026-09-29): costs fine, edge unproven, overnight leverage off

LIVE (Schwab, since 09-22, 6 sessions): **+$18.99 (+0.8%)** on ~$2,240 (deposit
09-29 took equity $1,000 -> $2,259; P&L excludes it). In line with the backtest's
~0.5% for 6 days, but that is noise at this sample.
- night 34 trades, 38% win, **+0.08%/trade**, +$10.34. SE per trade is ~1%, so
  this says nothing about the edge yet.
- ibs 2 trades, 2 wins, +$12.76. noise 1 trade, −$4.17 (live from 09-29).
- shadows (noise QQQ/SMH, conviction TQQQ): 1-4 days each, not readable.
- **Costs are settled:** live night buys median −2.5bp, sells median 0.0bp
  (research assumed 7.5bp/side; the edge dies ~15bp). Paper night is not
  evidence (Alpaca paper open sells ~+200bp, see item 4).

**Decided 2026-09-29:**
1. **Intraday leg stays live on real money** (`daytrade_mode: auto`, 2.06x
   intraday cap; on since the deposit crossed $2,000). It is the researched
   design (addendum 9); the kill rules cover it. Off switch:
   `daily.daytrade_mode: off`.
2. **Overnight leverage OFF: `daily.lever_weight: null`.** It would have opened
   by itself at 50 night exits (34 now): both legs 0.5 -> 0.65, 1.3x overnight.
   The gate (`signals.lever_ok`) proves costs, not edge. Revisit at ~100 live
   night trades; to re-arm, set `lever_weight: 0.65` (the gate still applies).

**`make review SINCE=2026-09-23` (2026-09-29 17:53 ET):**
- **Same-trade test (§4) passes early:** live night +0.08%/trade vs the backtest on the SAME
  trades −0.08% → live is +16bp/trade better (buy −0bp, sell −1bp vs the 15bp assumed). The bot
  reproduces the backtest; the flat result is the market over these 34 trades, not execution.
- Open sells vs the official open: mean −1.2bp, 95% UB +8.5bp (n 34). G1 needs 8 exit days
  (has 4). Kill check: n 34, t +0.11, 66 round trips to a verdict.
- Signal agreement (§1): live missed 15 of 49 backtest names (09-23 to 09-28, at $1k): small-book
  rounding and the leg budget, as Study R predicts. Recheck at $2,259.
- Intraday hygiene (§7): 1 clean day of 1. Conviction (profile moderate10c) needs ~5.
- Paper night sells +53bp vs the official open (n 6): the Alpaca paper simulator, as found above.

**Re-arm leverage (`lever_weight: 0.65`) when, at ~100 live night trades:** the kill rule has
not fired AND §4's live-minus-backtest gap on the same trades is ≥ −10bp/trade. That proves the
bot captures the backtest; the edge itself needs ~3,000 trades (~2 years) and rests on the research.

**Addendum 21's `night_price_min: 3.0` conditional: NO, decided 2026-09-29. Keep $5.** Its
evidence came from split-adjusted bars, which let in sub-$5 lookahead winners (addendum 36).
On raw prices (RESULTS.md ~L2379) the $3 floor is −1.7 / +0.7pp (2021-23 / 2024-26) at
tier+tick, −0.8 at tier_hi 2024-26, and the added names lose 33bp/trade in 2021-23 (placebo
7%). Cheap live sub-$10 costs (~0bp) were necessary, not sufficient. Do not revisit on cost.

---

## Round 3-4 verification (2026-09-29): one bug fixed, nothing adopted, Roth blocked

- **Roth has never traded: it is blocked by design, not broken.** `executor.py:165` returns before
  any phase unless `.env` has `ROTH_LIMITED_MARGIN=yes` (a plain cash IRA would take good-faith
  violations). Get Schwab's margin-in-IRA approval, then set the flag on the server.
- **Study R (Roth sizing, pre-registered):** whole shares + probe vs fractional, tier, pp/yr:
  $1k −3.5, $2k −2.5, **$3k −1.2 (first size inside the −2.0 bar)**, $5k −0.8. At $1k the IBS
  leg (~$167/ETF) buys 0 QQQ/SPY/SMH. Fund the Roth to ~$3k before judging it.
- **Study P (probe off, pre-registered):** KEEP the 1-share probe. No-probe wins the full
  period and Sharpe at every size (e.g. $2,259 tier 12.9 vs 12.3%, Sharpe 1.07 vs 0.95) but
  loses 2024-26 CAGR at $2k-$3k (16.8 vs 17.6% at $2,259), which the rule required it to win.
  Only at $1k is it better everywhere. Do not revisit on these numbers.
- **Study H corrected:** the round-3 "tie-break mirage" was a bug in `research/sim/ibs_24_univ.py`
  (it traded the alphabetically-first 3 of the top 8; 15-name "EQ18"; baseline never reset).
  Rerun (control reproduces baseline exactly): 24-ETF IBS +3.0pp/yr, t 1.1; with the corr
  dedupe +4.0pp, t 1.4; both halves positive, both below the t ≥ 2 bar. **F2 stays dead by t,
  not as an artifact.** Live code was never affected. Details: `research/drafts/study_fg.md`.
- **Study S (short the night picks after the open, pre-registered): DEAD.** 75% of picks are
  SSR (Rule 201) the next morning and cannot be shorted at the open. The shortable 25% drift
  only +8..+13bp gross by 10:30, below the ~20-35bp spread cost: every variant is negative in
  both halves at tier (NW t -0.4..-3.0). The post-open drop lives in the SSR names (+35..+45bp
  gross), which are exactly the ones you cannot short. `research/drafts/study_s_night_short.md`.
- Program N: 581 + 10 (R) + 2 (P) + 8 (S) = **601**. Nothing clears the bar.

---

## Addenda 40-41 (2026-09-29): day trading after the PDT rule — nothing to adopt, one shadow

**40, intraday buying power: SHADOW.** Schwab gives margin accounts ≥ $2k *Intraday Margin Buying Power*
(up to 4x maintenance excess) since 2026-07-13. The live code still reads 2.48 (Reg T `buyingPower`), and
the broker multiplier is not the binding constraint:
- 3-4x adds **+0.5-0.6pp EH after tax** (tier_hi, raw prices) to V7 / moderate10c. NW t is 1.6-1.7, and
  2024-26 t is 0.5-0.6. On moderate10 (no conviction) it adds ~0 (+0.03pp): **dead**.
- The size that matters is the noise target. Kelly x1.5 (`noise_target_vol` 0.02 → 0.03) at 4x adds
  **+1.2-1.4pp EH-AT** (NW t 2.0, placebo 98th pct). It is downgraded to shadow for these reasons:
  - DSR 0.10; 2024-26 t 0.64; t 1.1-1.3 without the 5 best days; 2026 YTD −3.8pp.
  - Every increment turns negative at 2x the tier_hi intraday costs (break-even ~2bp per noise fill).
  - P(DD>30%) doubles (23 → 46%). P(DD>50%) goes 0.3 → 3.7% on V7 and 0.9 → 3.3% on moderate10. It is
    **5.4% on moderate10c, over the bound**.
- $/yr: +$35 at $3k, +$1,169 at $100k (V3 on moderate10, tier_hi); negative under the cost stress.
  Multiplier alone on V7: +$18 / +$601.
- Roth: a limited-margin IRA gets no intraday margin, so there is nothing to change.

**Switch (spec only, NOT built, default OFF, taxable margin book only).** Nothing in `config.yaml` or
`swingtrader/` changed. A build would add these knobs:
- (a) `daily.intraday_mult: broker | <float>` with `.env DAILY_INTRADAY_MULT=3.33`. `executor._gate` would use
  `min(value, 4)` instead of the API ratio (MARGIN account, equity ≥ $2k).
  - Gate: Schwab.com Balances shows Intraday Margin Buying Power ≥ 3.5x equity (or a `make daily-live-check`
    `currentBalances` dump names an API field; then read that instead).
  - Useful only with the conviction trade on.
- (b) `noise_target_vol: 0.03` as an opt-in profile key, run as a shadow noise equity beside the live 0.02 leg
  for 60 sessions first.
  - Go live only if realised noise fills are ≤ 1.5bp all-in, the shadow increment is > 0, and the book's
    P(DD>50%) is ≤ 5% (so never moderate10c + Kelly).
  - On conviction books, use it only together with (a) ≥ 3.33.
- Kill: revert (a) to `broker` if Schwab rejects ≥ 3 intraday orders for margin in 20 sessions. Revert (b) to
  0.02 if the intraday legs' 60-session drawdown exceeds 15% of equity or the existing noise `KILL_*` fires.

**41, noise rule on single stocks (top 5/10/20 by dollar volume): DEAD, no switch.**
- Every variant lowers V7 and moderate10c in both halves at the measured spread, and still at zero stock
  cost. Best S10t: −0.8pp EH-AT, −$24/yr at $3k, −$802/yr at $100k.
- The megacaps carry QQQ's edge; QQQ is the cheapest wrapper of it (basket corr 0.72, 3x the cost per side).

Program variant count: 546 + 7 (add. 40) + 6 (add. 41) = **559**. Nothing clears DSR 0.95.

## Live checkpoint (2026-09-24, `make review SINCE=2026-09-22`)

Schwab brokerage live since 09-22 on a $1k cap. Night exits **19/50**; open
sells **−2.1bp/side** vs the auction print (buys −0.5bp), well inside the
10bp gate. Live beat the backtest on the same trades (−1.75% vs −1.92%); the
losses are one bad night, not execution. `daily-status`'s +33bp is vs the 15:50
decision price, not a cost. At 50 exits ≤ 10bp: overnight leverage opens by
itself, and the aggressive profile (addendum 22) becomes an option.

## Addenda 30-39 (2026-09-28): research program

**Restatement (add. 30): every night-leg number before addendum 30 is ~1/5 too high.** The research
night pool used split-adjusted prices (later reverse splits made penny stocks look like $5+ names).
Raw-price baseline, 2021-26: V7 shipped **47.2% / 2.06 / −14 at 3bp**, **29.4% / 1.41 at tier_hi**,
EH tier_hi 13.3%; live today (no conviction) 40.6% / 23.7%; Roth M3 35.3% / 22.4%. Live code was
always right (it sees real quotes). New research must use `load_sim(raw_price=True)`. Nothing new
survives multiple-testing deflation (N=546, best increment A2 DSR 0.34); what the program changes is
structure: about **+$520/yr** at user size EH tier_hi, mostly the wash guard (add. 39).

**Shadows now running, log only** (`config.yaml` `daily.*`, all `shadow`, set `off` to silence):
`[fomc]` F3 (`fomc_filler_mode`, taxable only), `[roth-cash]` M2L (`roth_night_cash_log`),
`[oversold] SHADOW Roth A2` (rides `oversold_mode`), `[lever-g1]` (`lever_g1_log`), `[wash-guard]`
G4s (`wash_guard_mode`). None changes an order or a size.

**Decide BEFORE `make daily-roth-on`: the wash guard.** The live guard (symmetric 31 days, taxable
first) starves the Roth: its IBS leg almost never gets QQQ/SMH and its night leg gets only names the
taxable book skipped (Roth EH ~8.8% vs ~13% under G4s; add. 31, 39). G4s = the Roth owns the shared
night names, the Roth trades different-index look-alikes only (XLK→VGT, SMH→SOXX, sector SPDR→Vanguard;
never same-index SPLG/QQQM/IVV), and skips names the taxable book sold at a loss in 30 days or holds.
Worth ~+$363/yr at user size (+$5.3k at 100k); costs ~0.7% of taxable losses permanently disallowed.
G4s is post-hoc. **Built (b): `daily.wash_guard: roth_first` is set in `config.yaml`** (tests in
`tests/test_wash_guard.py`). With both books on, the Roth runs before the taxable book each phase; the
taxable book keeps the symmetric 31-day rule on every leg. Revert: `wash_guard: symmetric` (old
behavior, taxable first). First week, read `[wash] roth_first:` lines: the Roth night block count
should be small (taxable loss sales 30d + held/pending); IBS look-alikes (XLK->VGT...) must never be
bought AND sold same-morning (no VGT churn); the taxable 15:40/09:15 runs now start after the Roth's, so
check the taxable open sells still land before 09:28 and night buys before 15:50. Roth F3
stays **off** under either guard (Roth QQQ buys disallow 1-10% of taxable losses for ~$0 edge).

**Order, each gated on live evidence** (at the 10-08 checkpoint unless noted):
1. `make review` §2b clean (open sells ≤ ~5bp over 50 exits; `[lever-g1]` agrees): raise or remove
   `DAILY_LIVE_CAPITAL` / `DAILY_ROTH_CAPITAL` so deposits are not held behind a cap (add. 38), and
   deploy the rest of the Roth once the guard decision above is made.
2. Taxable leverage: `DAILY_LIVE_PROFILE=moderate10` (cap .15, never levers; EH-AT 9.3 vs 1.3x's 9.1 at
   tier_hi). Plain `moderate` turns into 1.3x as soon as the lever gate opens. Moderate at 1.3x (what you get when the gate opens with moderate on) now needs a new
   sign-off: P(DD>50%) 5% net / 9% on the balance at tier_hi. Take it only if §2b stays ~0-3bp.
   Aggressive: no (P(DD>50%) 14% at tier_hi on raw prices).
2b. Conviction trade live (taxable): `DAILY_LIVE_PROFILE=moderate10c` in `.env` (= moderate10 + conviction auto), gated on `make review`
   §7 showing ~5 clean live intraday days (entries at :01/:31, flat by 15:57, fill cost near the
   quote). Raw prices: +6pp/yr (40.6 -> 47.2% at 3bp, 23.7 -> 29.4% tier_hi; EH after tax 7.2 -> 8.6).
   It shrinks the intraday cap to 0.75 (TQQQ 75% margin). Roth conviction stays off (fails 2016-20).
   Kill: the existing `KILL_*` rule for the conv leg; undo = back to `DAILY_LIVE_PROFILE=moderate10`.
3. F3 (taxable): ADOPTed (add. 33) but tiny (~$3/yr at $3k, ~$100/yr at $100k); the order path is
   not built. Build it when convenient and keep the self-score.
4. M2L (Roth pro-rata night sizing on the real 15:40 cash): sizing only, +$94/yr. Decide from
   `[roth-cash]` once the Roth trades (does requested exceed funded on long-3x days, as modelled).
5. A2 (Roth V6 on all idle overnight money): stays shadow until V6 itself leaves shadow (add. 27 rule).

**Pre-registered kill / de-risk rules for the new shadows:**
- F3: auto-disable after **16 FOMC eves with mean net < 0** (scored at 3bp/side); the status line
  shows `AUTO-DISABLE PROPOSED`; then `daily.fomc_filler_mode: off`. The calendar in
  `swingtrader/daily/events.py` ends 2028-01-26; extend it before the <60-day warning starts emailing.
- A2: lives or dies with V6's shadow record (`oversold SPY/QQQ` line).
- G1 gate: logging only. It needs n ≥ 20, ≥ 8 distinct exit days and a day-clustered 95% UB ≤ 10bp;
  the live gate (`lever_ok`) is unchanged. Do not open leverage by hand on G1.
- No automatic de-risk on leg CUSUMs (add. 37: costs 1-14pp/yr with nothing decayed). The `KILL_*`
  rules stay as they are. Plan on a walk-forward haircut of ~0-8pp/yr; edge-halves stays the stress.

## Addendum 29 (2026-09-28): live costs ~0bp; a `moderate` profile, OFF

**Adjusted-pool numbers (too high, see add. 30).** On raw prices: V7 3bp 47.2 / 2.06, 1.3x 53.4 /
2.04, moderate 1.3x .15 64.2 / 2.10 (tier_hi P(DD>50%) 8% pre-tax); the best Sharpe at 3bp is now
moderate as built (1.0x .15) 2.15, and the differences are small.

Live open sells −1.0bp/side (26 exits). At a 3bp stand-in: V7 58.0% / 2.33 (was 47.5 / 1.99),
1.3x 68.3% / 2.32. New `DAILY_LIVE_PROFILE=moderate` = 15% night-name cap only (best Sharpe
at measured costs, 2.42; EH 34%/yr, P(DD>30%) 32% in 5y). Decision order at the 10-08
checkpoint, each only if `make review` 2b still shows open sells <= ~5bp over 50 exits:
(1) the gate opens 1.3x by itself; (2) `conviction_mode: auto` after ~5 clean intraday days;
(3) `DAILY_LIVE_PROFILE=moderate`; (4) aggressive only if you accept ~44% odds of a >30% drop.
Raise `DAILY_LIVE_CAPITAL` in steps alongside; capital is still the biggest lever.

## Addendum 27 (2026-09-25): oversold overnight in SHADOW, three patterns dead

`daily.oversold_mode: shadow`: SPY/QQQ after 3 down closes or RSI(2) < 10, close auction
-> next open, idle IBS money. Backtest V7 47.5% / 1.99 -> 49.9% / 2.04 (edge-halves
17.5 -> 18.2%), but the variant is post-hoc, so it only logs `[oversold]` and scores itself.
Decide after ~15-30 shadow nights (`make daily-status` line `oversold SPY/QQQ`): if its
average is positive and near the backtest's +10..+30bp/night, build the order path (reuse
the night leg's MOC buy / open-auction sell on SPY/QQQ).

## Addendum 26 (2026-09-24): watchdog shipped, two Sharpe levers dead

- **Server, once:** add `HEALTHCHECK_URL=` to `.env` (a free healthchecks.io check: cron
  `1,31 10-15 * * 1-5`, America/New_York, grace 30 min). Then `make notify-test`: until
  that email arrives, no alert (including the new watchdog) is proven to reach you.
- **New in the email:** the 16:10 run warns `watchdog: today's schedule has gaps` if a
  phase did not run. `make review` now shows §2b (lever gate with a 95% upper bound),
  §6 (night cost by price: the addendum 21 `night_price_min` check) and §7 (intraday
  fill hygiene: the conviction switch-on evidence).
- **Dead:** moving budget from overnight legs to the intraday leg on high-vol or
  after-drop days (placebo-level, −0.23 Sharpe in 2024–26); an 11-ETF trend sleeve
  (placebo fails in both halves, +0.06 Sharpe at best for −4.6pp/yr). Retest trend only
  with 20+ futures markets (~$30k account).
- **Unchanged and waiting (the user's 2–3 week hold):** aggressive profile, conviction
  `auto`, raising `DAILY_LIVE_CAPITAL`. Decide with §2b / §7 of `make review`.

## Addendum 25 (2026-09-24): micro futures, nothing new to run

No new edge in futures. The live QQQ noise leg on MNQ passes (both halves,
placebo, stress), and so does IBS overnight weakly, but both are bets the book
already holds. MNQ's advantage over QQQ is about +1.6pp/yr after tax (1256
60/40, lower cost, no wash sales). The blocker is size: one MNQ is about $61k
notional, so staying at or below 2x needs about $30k per contract. Revisit
when the brokerage book reaches about $30k: move the noise leg from QQQ to
MNQ in a futures account instead of adding a second copy. ORB on NQ/ES: dead.

## Addendum 24 (2026-09-24): leap book, SHADOW ONLY, off

No tested rule 5x's in months: P(5x in 12 months) is 7% at best; ~4 years median,
about the aggressive profile's pace with 2-4x its drawdown. Two survivors, built
in shadow only (`swingtrader/leap/`, `leap.enabled: false`, no order path):
SOXL IBS < 0.2 (robust) and SOXL 15-min ORB (fragile: ~0 in 2016-20, dies
at 10bp or a 1-min fill delay). Going live needs a separate Schwab account and a
wash-sale plan against the Roth's SOXL/SOXS intraday leg. The shadow logger is
not scheduled yet: it needs a minute-bar feed (the streaming process). Wire
that, run a few months of shadow, then decide.

## Addendum 23 (2026-09-24): tilt v2 built, OFF

`daily.night_tilt_model: v2` adds yesterday's return to night sizing: replay +$23k
($260.6k → $283.7k), every year better, but borderline (sign opposite the prior, best of 9).
The 15:40 log shows what v2 would weight. Decide after the fill-cost checkpoint.

## Addendum 22 (2026-09-24): experimental growth profile, OFF by default

`DAILY_LIVE_PROFILE=aggressive` in `.env` runs the brokerage book at 1.3x overnight
(ungated), 20% per name, conviction live, intraday 0.6x. Remove the line to go back.
`make daily-status` names the active profile and its real overnight size (`=== LIVE (real money) profile aggressive ===`, `overnight size 1.30x`).
Recommended only AFTER ~50 night exits confirm open-sell cost ≤ 10bp/side: if the
edge is half what history says, it earns ~22%/yr vs ~18% for a 68% chance of a >30% drop.
Also shipped: the intraday cap now charges TQQQ/SQQQ 75% margin (cap 1.0 → 0.75 once conviction is live).

## Addendum 21 (2026-09-24): nothing adopted

SOXL conviction, bear-hedge overlays and thin-volume night names: dead. One
conditional: once ~50 live night exits exist, check the cost of names under
$10 in `make review`; if ≤ ~20bp/side, set `daily.night_price_min: 3.0`.

## Addendum 20 (2026-09-24): review fixes + Roth IRA book

- **Live now (on `make pull`):** one-share probes for night picks that round
  to 0 shares (≤ $150), and the intraday leg goes live on a capped book when the
  ACCOUNT is ≥ $2,000. With the $1k cap that means real QQQ/SMH day trades
  (small: whole shares). Keep watching `route ...: bps, % at the auction print`.
- **Decision rule for the broker:** if Schwab's open sells average > ~10bp/side
  after ~50 exits, move the brokerage book to Alpaca live (real OPG orders):
  each bp/side is ~0.85pp/yr.
- **Roth, to switch on:** (1) apply for limited margin on the Roth at Schwab;
  (2) set `SCHWAB_ACCOUNT_NUMBER` (brokerage) and `SCHWAB_ROTH_ACCOUNT_NUMBER`
  in `.env` BEFORE re-running `make schwab-login` with the Roth ticked, or the
  brokerage book stops (two accounts linked, it refuses to guess); (3)
  `ROTH_LIMITED_MARGIN=yes`; (4) sell the Roth's ETFs yourself (the bot never
  touches your holdings); (5) `make daily-roth-check`, then `make daily-roth-on`.
- **Dead:** cheaper margin as the lever, SGOV for night cash, −6..−8% night
  names, intraday diversification into bonds/gold/oil/SPY.

## Addendum 19 (2026-09-24): conviction trade built, SHADOW

TQQQ strong-first-breakout trade, ~70 days/yr, 0.5 of equity inside the same
daytime margin. Simulator: 40.7% → 49.8%/yr at the same Sharpe. It logs as
`[conv]` and places nothing until `daily.conviction_mode: auto`. Switch it on
after the regular intraday leg has about a week of clean live fills (entries at
:01/:31, flat by 15:57). `make daily-status` shows its shadow record.

## Addendum 18 (2026-09-24): crash guards shipped

`night_max_corr` 0.9 → 0.7 and `night_weekend_scale` 0.5. COVID crash on the
book −17% → −4%; 2021–26 Sharpe 1.81 → 1.98. Weak spot left: the intraday
leg is the only short side, and it is fading. If it dies, a slow bear is unhedged.

## Addendum 16 (2026-09-24): what changed, what is waiting

- **Shipped:** night sizing tilt, QQQ + SMH intraday split, Schwab open sells
  directed to the listing exchange's opening auction, pre-registered kill
  rules, swing book off the schedule. Simulator: 35.2% / 1.76 → **41.3% /
  1.89** (tiered costs 33.0 → 39.2).
- **Waiting on live fills, and automatic:** overnight leverage (0.65 + 0.65)
  opens only after 50 night exits average ≤ 10bp/side vs the official open.
- **Watch first:** the 15:40 log line `route NASDAQ/NYSE/...: n, bps, % filled at
  the auction print`. If directed orders are refused, the log says so and
  the bot falls back to Schwab routing. If they are accepted but the hit rate is
  low, set `daily.schwab_open_route: auto` and compare the two.
- **Kill rules are live** (`signals.KILL_*`). Do not loosen them after seeing
  results. Status: `make daily-status`. Undo: `python scripts/daily.py
  --unkill LEG --account live`.
- **On the server:** `make pull && make persist` (reinstalls the schedule
  without the swing timer). The swing paper book's open positions keep their
  broker stops; flatten them in the Alpaca paper dashboard if you want it clean.
- **Next research:** after ~2 months, fit a per-name cost model on
  `logs/daily-decisions-live.jsonl` (quoted spreads) + `daily-fills-live.jsonl`,
  and replace the assumed tiers in `research/sim/book.py`.

## ⚠ Read addendum 14 first (2026-09-23)

- The daily book's published numbers were inflated by a research lookahead
  and a few bad bars. Corrected live book (no intraday leg): **20.1% / Sharpe
  1.27 / −14%**, was 23.8% / 1.46. Full book 36.5% / 1.57 (was 40.7% / 1.70).
- The swing headline (15.1% / 0.95) is one lucky fold alignment; over six
  offsets it averages ~12% / 0.72, about SPY. At the live cadence (daily
  re-selection) it is 11.2% / 0.67 / −27.7%. **Items 0 and 0b below do not
  help at that cadence and stay OFF.** The swing book stays on paper.
- The first real test of the night leg is the Schwab open sells (no
  market-on-open order at Schwab). `make review` after ~50 round trips.

---

## 0. Uncap the candidate list — DEAD at the live cadence (addendum 14)

**Status:** found 2026-09-22, validated (RESULTS.md addendum 5), **not enabled.**

`selection.top_n: 8 -> 999` plus `portfolio.position_pct: 0.10`:
Sharpe 0.95 -> 1.16, CAGR 15.1% -> 22.3%, maxDD -14.4% -> -15.3%,
risk-matched 15.1% -> ~21%. The rank score has no predictive power (ranks 9+
earn the same as 1-8), shuffle/flip controls pass, beats baseline every year.

**Why now is cheap:** the systemd unit failed with 216/GROUP on every run until
924d854, so the live slippage sample is ~empty. Switching before fills
accumulate costs the experiment nothing.

**Open question before trusting live numbers:** live re-selects daily; the
backtest re-selects every 42 days, and an honest 21-day refresh scored far
worse (9.5%). Build a short-refresh backtest that matches the executor.

**Pair it with the correlation cap below** — on the uncapped book the cap is
where most of the risk-adjusted gain comes from.

---

## 0b. Correlation cap on new entries — DEAD at the live cadence (addendum 14: 1d uncapped + 0.7 = 8.5% / 0.58)

**Status:** researched and validated (RESULTS.md addendum 13); implemented in
`swingtrader/backtest.py`, `swingtrader/live/executor.py` (the live swing loop)
and `config.yaml` as `strategy.max_corr` (**null = off**). Setting it now governs
live as well as backtest.

**What it is:** walk candidates best-ranked first, drop any whose trailing
20-day returns correlate above `max_corr` with an already-held (or same-bar
pending) name. The same duplicate-bet rule the night leg already uses
(`daily.night_max_corr`, addendum 11). Eight slots should be eight bets.

**What it buys** (deployable uncapped config, −10% stop, cash BIL):

| | uncapped | + max_corr 0.7 | + max_corr 0.6 |
|---|---|---|---|
| Sharpe | 1.16 | **1.33** | **1.47** |
| max drawdown | −15.3% | **−10.3%** | **−8.0%** |
| CAGR | 22.3% | 20.2% | 20.5% |
| risk-matched | 21.0 | 28.4 | 37.2 |

Robust to the correlation window (10–40d), passes flip/shuffle, bootstrap
P(mean ≤ 0) = 0.0004, survives +10bps/side. Crucially it **beats a matched
random-drop control** (keep 67% at random → risk-matched 12.0), so the gain is
the correlation, not the reduced trade count. On the *live top8* config the
gain is small (15.1/0.95 → 13.8/1.02 at 0.7); its value is on the uncapped book.

**To enable:** set `strategy.max_corr: 0.7` in `config.yaml`. Do it in the same
change as the uncap (item 0) — that is where the benefit lives. (The live
executor applies it now; `live/executor.decide` shares the backtest's formation
length, overnight gate and correlation cap.)

---

## 1. Switch on the overnight-gap filter — PARKED (swing book quarantined)

**Status:** researched, validated, committed, **deliberately not enabled.**
**Parked 2026-09-29:** the swing book has been off the schedule since
a3ddb52 (2026-09-24, addendum 14: 11.2% / 0.67 at the live cadence, behind
SPY; only scheduled with `SWING_BOOK=on` in `.env`). Its last run was
2026-09-23 and `make slippage` has no fills, so the trigger below can never
trip. The daily book's night-leg fills are a different strategy and do not
count. Revisit only if the swing book is un-quarantined.

**What it is:** require that a dip be made mostly of overnight gaps
(`prev_close -> open`) rather than intraday selling, over a 5-day window.
Implemented as `strategy.min_overnight_share` in `config.yaml`, currently
`null`.

**What it buys** (walk-forward, 2021-2026, high-vol cohort, −10% stop, cash in BIL):

| | now (off) | with filter 0.3 |
|---|---|---|
| Sharpe | 0.95 | **1.34** |
| max drawdown | −14.4% | **−11.1%** |
| avg per trade | +2.46% | **+5.00%** |
| risk-matched CAGR | 15.1% | **22.3%** |
| months to significance | 40.5 | **19.5** |
| trades | 207 | 111 |

**Why it is off:** the live run exists to measure real slippage against the
20bps/side the backtest assumes. Changing the strategy mid-experiment
contaminates that measurement, and the underlying feature was only nominally
significant (Spearman +0.158, p=0.020, failing Bonferroni across 9 features).

**Trigger to turn it on:** roughly **20 real fills** collected, i.e. measured
slippage has converged (`make slippage` shows n ≥ 20).

**Then:**
```bash
make slippage                      # record the before number
$EDITOR config.yaml                # strategy.min_overnight_share: 0.3
make dry                           # sanity check
git commit -am "enable overnight filter after N fills"
```
Keep the before/after clean — that comparison is the whole point of waiting.

**If measured slippage comes back far worse than 20bps** (say >50bps/side),
turn the filter on *sooner*: its per-trade edge is +5.00% vs +2.46%, so it
tolerates roughly twice the cost before the edge disappears.

---

## 2. Lingering on the server — VERIFIED ON (2026-09-29)

`make persist-status` said `lingering: ON` on 2026-09-29. It must stay ON. If it says OFF, the systemd
timer dies the moment the SSH session closes and the bot silently never runs.
As root: `loginctl enable-linger ihearthim`.

---

## 3. Email — VERIFIED (2026-09-29)

Alerts arrive (confirmed by hand 2026-09-29). `make notify-test` re-checks it.

---

## Things already tested — do NOT redo these

| idea | verdict | why |
|---|---|---|
| News sentiment filter | **dead** | mean P&L diff +0.97pp, p=0.63 |
| FF3 residual z-score | **dead here** | FF3 explains only 22% of variance in this universe; strips little, adds 4 params of noise |
| Bertram optimal thresholds | **dead** | prescribes −0.4σ entry; risk-matched return falls monotonically as entry loosens. −2.0 was already optimal |
| Trailing / let-winners-run exits | **dead** | selection screens for *non*-trending names; a trend-following exit contradicts it |
| Long/short (shorting range tops) | **dead** | negative in every configuration |
| Short the night picks after the open (Study S) | **dead** | 75% are SSR; the shortable rest drift +10bp, below the spread |
| Looser entry for more trades | **dead** | raises CAGR, raises drawdown faster |
| Broad-market cohort | **weak** | 1.6% CAGR vs 15.1% — the edge needs high volatility |
| Momentum sleeve at 25% | **promising, unvalidated** | blend Sharpe 1.09 vs 0.95, but standalone CAGR swings 1.2–43.6% across settings |
| Parking idle cash in BIL/SGOV | **ADOPTED** | 86% of position-days were idle; +3.3pp CAGR, free |
| Uncapped candidates (top_n 999) | **found, pending** | risk-matched 15.1 -> 21.0%, controls pass (addendum 5) |
| z_window 10 / 40, formation 63 / 252 | **dead** | all 4-9% risk-matched vs 15.1% |
| −10% stop vs no stop | **ADOPTED** | 11.8% vs 8.6% CAGR, and lower drawdown |
| Shock-share filter (dip = one big down day) | **dead** | rm 27.7 but threshold is a spike (0.5), non-monotone per-trade — overfit (add. 13) |
| Volume-z dip filter | **weak** | rm 18–23, at or below the matched random-drop control (~20) |
| IBS / close-at-low as an entry gate | **dead** | closing at lows is a falling knife — worst bucket (+0.56%/trade) |
| z-turn-up, z-depth band, 52w-high distance | **dead** | no robust effect, unstable across halves |
| Regime gates (SPY 5d return, VIXY fear proxy) | **dead** | unstable across halves; SPY>200dma only buys Sharpe for return |
| Fixed take-profit exit | **dead** | worse at every level (cutting winners, same as trailing) |
| Inverse-vol / overnight-share position sizing | **weak** | top8 +5pp CAGR at best, no gain on the uncapped book |
| Correlation cap on new entries (`max_corr`) | **dead at live cadence** | uncapped Sharpe 1.16→1.33 at 42d refresh; 8.5%/0.58 at the live 1d refresh (add. 14) |
| Night leg: index filler for unused capital | **dead** | helps 2024–26 only (add. 16); the FOMC-eve subset (F3) is a pre-registered conditional, not a redo, and passes (add. 33) |
| IBS idle half in SPY/QQQ/overnight index | **dead** | helps 2024–26 only; BIL stays (add. 16) |
| Night leg: skip high-cost names | **dead** | cheap thin names are the best bounces (add. 16) |
| Daily-bar spread estimators as cost model | **dead** | measure volatility, not spread, on these names (add. 16) |
| Cross-leg regime tilt (overnight → intraday on high-vol / after-drop days) | **dead** | placebo-level; every leg earns more on high-vol days (add. 26a) |
| Cross-asset ETF trend sleeve (TSMOM, 11 ETFs) | **dead** | placebo fails both halves; +0.06 Sharpe at best, a drawdown dial (add. 26b) |
| Friday dips held over the weekend | **dead** | the worst down day to buy (SPY Fri <= -1%: negative all 3 periods) (add. 27) |
| Day-of-week, turn-of-month, chase-the-up-day, 52w highs, fear spikes | **dead** | unstable across periods or ~0 (add. 27 scan) |
| Pre-holiday session | **watch** | +14..+31bp 2021-26, mixed 2016-20, ~9 days/yr: never provable (add. 27) |
| Multi-day oversold SPY/QQQ, next-open entry (IBS timing) | **dead** | the edge is in the overnight gap; V6 (close -> open) is in shadow (add. 27 R1) |
| Night leg: 2/3/5-day losers | **dead** | slow slides continue; book worse every variant (add. 27 R2) |
| Last-half-hour intraday momentum (Gao et al.) | **dead** | sign flips across periods; overlaps the noise leg (add. 27 R3) |
| Sector-loser reversal, ETF pairs, international close->open | **dead** | duplicates IBS / no edge after costs (add. 27 R4) |
| Theme-explosion sleeve (breakouts, top-1% momentum, theme clusters, residual momentum) | **dead** | no rule beats vol-matched random picks; trails SPY; caught quantum late and got stopped out (add. 28) |
| Night pool $5 floor / cost tier / share rounding on split-ADJUSTED prices | **bug, fixed** | 16% of V7 night trades were really < $5; lookahead winners. Every earlier night level ~1/5 too high; use `raw_price=True` (add. 30, 36, 39) |
| Lower `night_price_min` to $3 / $2 / $1 (raw pool) | **dead** | added names lose 33-73bp in 2021-23, placebo 2-7%; add. 21's live-cost conditional ($3 if sub-$10 costs ≤ ~20bp) still stands (add. 30) |
| Classify listings by CURRENT asset name on old bars | **bug** | delisted names kept at volume 0, tickers reused (INFO, FB, PCLN): split listings first (add. 36) |
| Roth: smaller intraday cap (0.75 / 1.0x underlying) | **dead** | lower growth both halves; the Roth is below its Kelly peak (add. 31) |
| Roth: full-weight IBS after a no-pick night | **dead** | 2024-26 negative, placebo 15/50 (add. 31) |
| Roth: 3x ETFs up to 3.0x on all daytime cash | **borderline** | +2.8pp but 2016-20 Sharpe −0.07, worst month −11.7% (add. 31) |
| Roth: TQQQ/SQQQ conviction from the IBS idle cash | **borderline** | +24pp hist but 2016-20 Sharpe −0.10, EH P(DD>30%) 18% (add. 31) |
| Both accounts running the same legs without a wash guard | **dead** | 82% of taxable losses permanently disallowed (add. 31) |
| Loss-aware / look-alike guard with taxable first | **weak** | same-day night-name collisions: Roth still ~22% vs ~47% with Roth priority (add. 31) |
| Flatten the Roth intraday leg before the 15:40 close buys | **dead** | −0.4..−1pp/yr; night starvation is neutral-to-better at tier_hi (add. 31, 38) |
| Roth F3 (FOMC-eve QQQ) beside a taxable QQQ noise leg | **dead** | 1.1% (G1) / 8.8-9.9% (G4s) of taxable losses permanently disallowed for ~$0 edge (add. 39) |
| Vol-targeted overnight gross (0.5-1.5x on trailing book vol) | **dead** | de-levers in 2024-26, NW t −1.8/−2.4 vs fixed, placebo 9/20 (add. 32) |
| Aggressive / 1.5x profiles for the taxable book after tax | **dead** | +0.7pp EH after tax for +12-17pp P(DD>30%); raw tier_hi P(DD>50%) 14% (add. 32, 30) |
| 1.3x moderate (cap .15) as the taxable knee at tier_hi | **borderline → dead at tier_hi** | raw: EH-AT 9.1 vs as-built 1.0x .15 at 9.3; P(DD>50%) 5% net / 9% balance; increment t 1.0 (add. 32, 39) |
| QQQ noise half → MNQ below ~$200k; IBS index legs → micro futures | **dead** | one MNQ ≈ $61k > the leg's share of equity; IBS parks 7% margin and most picks are sector ETFs (add. 32) |
| FOMC eve in SPY instead of QQQ | **borderline** | same sign, half the size; F3 (QQQ) dominates (add. 33) |
| Pre-FOMC drift in the day session (close → 13:59) | **dead** | faded after 2023, placebo pct 78; the overnight part carries it (add. 33) |
| Night ×1.5 on FOMC eves | **dead** | placebo pct 67: same as 1.5x on random nights (add. 33) |
| Night ×0.5 on CPI/NFP nights; ×0.5 before weekly claims | **dead** | the night leg earns MORE across 08:30 releases; the claims rule is a Wednesday rule (add. 33) |
| Night ×1.5 on CPI/NFP nights | **borderline** | placebo 98th pct but gone in 2024-26 at tier_hi, more DD>30% (add. 33) |
| IBS ×1.5 when its night spans CPI/NFP | **watch (shadow at most, not built)** | both halves up but 2016-20 holdout negative, t 1.7 (add. 33) |
| Noise leg off / up on FOMC or CPI/NFP days | **dead** | FOMC ≈ 0; off on CPI/NFP costs 2-5pp (add. 33) |
| S&P 500 add/delete trades after the announcement | **dead** | the move is in the after-close announcement gap; tradable windows flip sign (add. 34) |
| Russell recon reversal | **untestable** | no membership/shares data; IWM−SPY proxy t ±0.4, n 11 (add. 34) |
| LETF-flow conditioned last half hour / night size-up after big down days | **dead** | small momentum the noise leg already holds (add. 34) |
| Night ×0.5 on QQQ ≤ −2% at 15:30 (LETF-selloff flag) | **borderline** | post-hoc; holdout = 3 COVID nights, 3/6 years negative, \|move\| ≥ 2% both signs does better, placebo 72% (add. 34) |
| Month-end pension rebalancing (SPY−TLT MTD) as IBS sizing | **watch** | right sign all periods, ~6 trades/yr, +0.15pp/yr, placebo 63% (add. 34) |
| Options calendar (OPEX Fri / week / post-OPEX) as sizing for noise, IBS, night | **dead** | pinning only in 2016-20; post-OPEX flips 2024-26 (add. 35) |
| Witching-day night entry | **dead (weak watch)** | vs other pre-weekend entries diff −23bp, t −1.3, placebo 14th pct (add. 35) |
| 0DTE era as noise-leg decay | **no decay** | 0DTE era +2.2bp/day ≈ 2016-20; plan on ~+2bp/day (add. 35) |
| Rule-based IBS universe (all liquid equity ETFs, corr-dedupe, momentum top-3) | **dead** | picks theme funds at momentum peaks; −6..−12pp 2021-23 vs the 18 ETFs (add. 36) |
| Night leg: exclude or 2x up-weight new listings | **dead** | exclude costs −14pp; up-weight was 5 reverse-split penny names, fails 2021-23 on raw prices (add. 36) |
| New-ETF overnight basket (first year) | **dead** | bid-ask bounce in thin funds; gone at ADV ≥ $10M (add. 36) |
| Walk-forward annual refit of leg parameters | **report / dead as a method** | refits lose 0-8pp/yr vs shipped; use as a haircut (add. 37) |
| Automatic de-risk on leg CUSUM / rolling-t | **dead** | costs 1.3-14pp/yr with nothing decayed; a false alarm switches a healthy leg off for years (add. 37) |
| Any leg decaying 2016-26 | **no** | all NW trend t > −2; noise QQQ 2024-26 a watch (t −1.8) (add. 37) |
| Evidence-keyed capital ramp (cap doubles per 15 exits) | **dead** | a 2-3 day P&L band can't tell edge from none; slower than deploying at the checkpoint (add. 38) |
| Sequential lever gate for speed | **dead as a money lever** | ~1 session earlier, ~$0; G1 logged only for its stricter false-open rate (add. 38) |
| Stacking the program's survivors as additive edges | **report** | no increment clears DSR 0.95 at N=546 (best A2 0.34, F3 0.035); the gain is structural (add. 39) |
| More intraday buying power (3 / 3.33 / 4x) for a book WITHOUT the conviction trade (moderate10) | **dead** | the extra exposure lands on calm days, where the noise leg nets ~0 after tier_hi costs: +0.03..+0.18pp EH-AT, NW t 0.6-1.1, placebo 69-83 (add. 40) |
| Intraday cap at 3-4x for the conviction books (V7, moderate10c) | **shadow at most** | +0.5-0.6pp EH-AT tier_hi, both halves + 2016-20 positive, but NW t 1.6-1.7 (2024-26 t 0.5-0.6), DSR 0.05; negative at 2x tier_hi intraday costs; live already reads 2.48, not 2 (add. 40) |
| Noise leg Kelly x1.5 (`noise_target_vol` 0.03) at 4x | **shadow** | +1.2-1.4pp EH-AT, NW t 2.0, placebo 98, but DSR 0.10, 2024-26 t 0.64, 2026 YTD −3.8pp, negative at 2x tier_hi intraday costs, P(DD>30%) 23→46%; moderate10c P(DD>50%) 5.4% fails (add. 40) |
| Roth intraday leg sized up after the PDT change | **not possible** | limited-margin IRA gets no Intraday Margin Buying Power (add. 40; 3x on all daytime cash already borderline, add. 31) |
| Noise-area rule on the top 5/10/20 stocks by 63d dollar volume (replacing the SMH half or as a third stream) | **dead** | book −3 to −9pp CAGR in BOTH halves at the measured spread (~1.65bp/side), −5..−11pp at 3bp, negative even at zero stock cost; basket corr 0.72 with QQQ; best S10t −$24/yr at $3k, −$0.8k at $100k (add. 41) |
| Same noise rule on liquid stocks outside the top 40 (ranks 41-100) | **dead** | gross ~0 bp/day, placebo 71%, book −15pp: the trend-day persistence lives only in the most traded names, which QQQ holds (add. 41) |
| Single-stock intraday noise legs as an "attention" diversifier to QQQ | **dead** | top-5 gross edge ≈ QQQ's; across name-years it scales with vol (t 6.8), not dollar volume (t 1.3); QQQ is the cheapest wrapper (add. 41) |
| Night leg: SEC offering filings (Study T) | **shadow** | E3 DROP passes by a hair after an ETN-mapping fix (t −2.1, 2024-26-heavy, 2021 positive); E1/E2/DOUBLE dead; OOS rerun at ~100 events (late 2028), no live code (study_t_filings.md) |
| Night leg: issuer classes via EDGAR (Study U: drop/only 'ETP') | **dead as registered; classes mislabeled** | EDGAR's index misses ETF series ('unmapped' = leveraged ETFs) and 'non-operating' = foreign ADRs; LETF (+45bp gross 24-26) and ADR (+41) buckets beat US stocks (+17) in a diagnostic: needs a proper classifier (study_u_classes.md) |
| Night leg: leveraged-ETF picks up/down-weighted (Study W) | **dead** | per unit of vol an LETF pick = a same-vol non-LETF pick (z +0.017, t 0.6); no L(L−1) gradient; the +45bp gross was leverage (study_w_letf.md) |
| Night leg: SSR (Rule 201) flag as a long-side tilt | **not run** | ≈ drop depth (picks need −8% and IBS ≤ .10; SSR = low ≤ −10%): no new information, not worth N |
| SPX put-write overlay (Cboe PUT / WPUT / CNDR, k 0.5, Round 13 Z) | **dead** | PUT positive every period but NW t 1.93 and −15.5% worst 21d (2020); WPUT/CNDR negative after costs; in the Roth PUT < held index |
| Fade QQQ inside the noise band while the noise leg is flat (Round 13 AB) | **dead** | in-band drift < one side of cost; −2..−4pp/yr, NW t ≈ −1.2, placebo 41-82 |
| Box-spread financing of the overnight debit (Round 13 AA) | **report** | debit ~3.6% of equity at 1.3x: ~$320/yr at $100k; ~$1.7k at 2.0x; only with MAX leverage |
| Closing-auction imbalance (Round 13 AC) | **dead (Round 26 BD)** | tested on Databento history 2021-26: no ex-ante signal |
| SPY held + noise overlay for the taxable account (Round 13 AD) | **report → switch at $100k (Round 14)** | beats B2 after tax, both halves; at the live cap 1.0 and a 10% index it ties at $100k, loses at $25k; more drawdown (−17% / −31% in 2020); taxable only |
| High-frequency QQQ/SPY scalping (1-15 min momentum/reversal, ~100+ trades/day; diagnostic 2026-09-30, not pre-registered) | **dead** | minute autocorr ~0.01; non-overlapping 5-min reversal after a 2-sd move: −1.0..+0.3bp gross/trade, sign flips across periods, no t ≥ 2; QQQ's 0.13bp spread alone eats it. The pooled −0.47bp "reversal" was overlap + a full-sample sd threshold |
| Anatomy of the biggest intraday swings -> a direction rule at the open (Round 15, Study AE) | **dead (nothing selected)** | gap size, yesterday's range and volume make a 3σ open->close move 2-2.7x likelier, equally up and down; no feature's extreme decile predicts sign (best t −2.5 on 2021-23, −3bp vs ~10-30bp cost); AE1-5 not run |
| Conviction weight x predicted magnitude (gap/range/rvol/VIX terciles; Round 16 AF) | **dead** | size is predictable (R² .13-.24) but the trade's EV peaks in the middle tercile, loud days −44bp 2024-26; all 4 variants fail both halves and t (best +0.5), placebo 9-80 |
| Conviction confirmations at the breakout minute: strength buckets, SMH/SPY/IWM agreement, bar volume, VIX, VIX9D/VIX, time (Round 16 AG) | **dead** | none monotone in 2016-23 except time (flat), and dropping 10:00 entries loses −2..−5pp/yr; breadth / NQ lead untestable (no data) |
| Conviction exits: stop 1u/2u, target 2u/4u, half off at 2u, pullback limit entry (Round 16 AH) | **dead** | targets cut the winners (−1.5..−2pp/yr), pullback fills only the failures (t −2.8); 1u stop halves the worst trade but −2.1pp in 2024-26 |
| Conviction weight 0.75 / 1.0 in TQQQ (mult 2 or 4), 2.0 via MNQ (Round 16 AI) | **dead** | TQQQ's 75% margin comes out of the noise cap: +0..+2pp, t 0.5; MNQ 2.0 t 2.2 but maxDD −36%, P(DD>50%) 38% |
| Conviction trade in MNQ instead of TQQQ (Round 16 AJ) | **shadow (AJ1 .5, AJ2 .75); AJ3 1.0 dead** | same trades, cheaper, frees the noise leg's margin, 60/40: +2.5..+5.3pp 2024-26, t 4+; Schwab API cannot trade futures, needs a second broker; ≥ ~$29k |
| More conviction setups: second breakout after a failed first; SMH/SPY/IWM on no-TQQQ days (Round 16 AK) | **dead** | 2nd breakout +0.4..+0.9pp all halves but t 0.9; SPY = same bet (corr .75); SMH/SPY/IWM fill-ins 0..−7pp 2024-26 (IWM t −2.7) |
| Gap ≥ 4% + premarket vol ≥ 250k, pullback to VWAP, reclaim, 2R target (Lab-AS, day-trading lab) | **dead** | gross −1.7bp/trade, −18.9 at 10bp/side (t −3.2), −36 at 2x both halves; placebo 59th pct; $2.3k -> $568 over 2022-26 |
| 5-min ORB on Stocks in Play, re-test at 5/10bp per side, 2022-26 (Lab-AU, day-trading lab) | **dead (again)** | −23.5bp/trade, 19k trades, t −16.7; even the optimistic fill bound grosses only ~+10bp: −9bp at 10bp/side both halves. Already dead in RESULTS.md (check RESULTS.md's dead tables too) |
| VWAP trend on QQQ / TQQQ, flip on every 1-min VWAP cross (Lab-AW, day-trading lab) | **dead** | signal real (placebo 97th pct, +6.7bp/day gross on QQQ) but 16 switches/day cost 16bp: −9.3bp/day QQQ, −27.7 TQQQ; the band that fixes it is the live noise leg |

| +25% movers at 15:00 held to 15:55, long only (Lab-AX, day-trading lab) | **dead** | gross +6bp/trade, −33.7 at 20bp/side, H2 −53.6; the run-up is done by 15:00 |
| Buy the reopening after a LULD halt, up or down (Lab-AY, day-trading lab) | **dead** | ~−130bp gross per 30 min either way (t −4..−5); post-halt drift is down; short side = Lab-BA |
| Short the reopening after a halt (up; ETB-only; down without SSR) (Lab-BA, day-trading lab) | **dead** | a lottery: a few 40-55% collapses in unborrowable names; negative without the top 20; ETB names −70bp gross |
| Nasdaq early closing imbalance (15:54) as an intraday trade to the close (Lab-AZ/BB/BC, day-trading lab) | **dead: real signal, spread-bound** | +6-7bp gross out of sample (placebo 100th) but the 15:54 spread eats it: H2 +0.3bp net 1x, −5.7bp 2x |
| Nasdaq opening-cross imbalance, reversal by 10:00 (Lab-BE/BF, day-trading lab) | **dead** | wrong sign (−7.8bp gross, placebo 0.4th); continuation decayed from +13.5bp (H1) to +1.9bp (H2), below the exit spread |
| Closing-imbalance signal with a passive limit at the touch until 15:55 (Lab-BG, day-trading lab) | **dead** | adverse selection: filled trades −0.6bp mid -> close (H2); net +2.2bp t 1.6; a false pass came from counting TRF sub-penny prints |
| Announcement-gap drift (gap >= 5% on 3x volume), long 5/20d; and the short+SPY hedge (Lab-BH/BI, lab) | **dead** | long −185bp 20d excess 2022-26; the short fails out of sample on 2017-21 (t 0.6; 2018, 2020 negative): a post-2021 regime |
| Calendar-month return seasonality, top 20 of 500 most traded, monthly (Lab-BJ, lab) | **dead** | −69bp/month vs the EW universe 2021-26, placebo 3.9th pct |
| Short both legs of a 3x LETF pair (TQQQ+SQQQ, UPRO+SPXU), weekly (Lab-BK, lab) | **dead** | weekly rebalancing keeps only daily-minus-weekly variance (~3.8%/yr gross on QQQ); shorts pay the bear ETFs' T-bill distributions; ~0 after 2-4% borrow, negative at HTB rates |
| Distance-method stock pairs on the top 100 (Gatev et al.), 6-month periods (Lab-BL, lab) | **dead** | −13bp/month, negative 8 of 10 years, placebo 68th pct |
| Drift after forward-split ex-dates, 60 days (Lab-BM, lab) | **dead** | −250bp excess at 2x, both halves negative; the same stocks on random dates beat SPY by ~12%: splitters underperform right after the split |
| SVXY only in VIX/VIX3M contango, else BIL (Lab-BN, lab) | **dead** | 13.7%/yr, −45% max DD vs SPY 14.6%/−32%; t 1.5, placebo 76th pct |
| Monthly top 20 of 500 by 52w-high nearness / low vol / 1-month reversal (Lab-BO/BP/BQ, lab) | **dead** | excess −8.5 / −50 / +13bp per month, all fail 2x in a half; t ≤ 0.2 |
| Monthly 12-1 momentum, top 20 of 500 (Lab-BR, lab) | **dead by t (watch)** | 22.6%/yr vs universe 12.2%, placebo 100, but t 1.5 and 2017-21 2x only +0.9bp/month with a worse Sharpe: the 2022-26 AI rally. A new registration needs pre-2016 history |
| Sector-SPDR 12-1 momentum, top 3 monthly (Lab-BS, lab) | **dead** | 2017-21 −31bp/month at 2x; only 2022 (energy) helps; 13.6%/yr < SPY 15.1% |
| Long top-decile momentum vs market, 1963-2015 French data (Lab-BT, lab) | **PASS (registered bar), shadow only** | +40bp/month, t 3.0, but ~0 in the 2000s/2010s and −3.5bp at 2x in 2016-26; −50% worst 12m. Paper shadow built; no live change |
| Vol-scaled top-decile momentum, 12% target (Lab-BU, lab) | **dead by bar (useful risk control)** | 1963-89 Sharpe 0.589 vs 0.611 fails "better in both halves"; but the worst 12m −50% -> −25% (1927-63), −31% -> −24% (1963-2015), t 3.3 |
| Long-term reversal, bottom 60-13 decile vs market, French 1963-2015 (Lab-BV, lab) | **dead** | +28bp/month but t 1.76; 2010s −56bp, 2016-26 −22bp at 2x; worst 12m −41% |
| Industry momentum, top 5 of French's 49 industries, 1963-2015 (Lab-BW, lab) | **PASS (registered bar)** | +49bp/month t 3.3, 2x +41/+36 both halves, positive every decade incl. the 2000s; weaker since 2010 (+3bp at 2x 2016-26); worst 12m −41% (2009) |
| Industry-ETF momentum, top 5 of 20 fixed ETFs vs SPY, 2017-26 (Lab-BX, lab) | **dead (shadow kept)** | ties SPY (15.2% vs 15.1%), t 0.3; picks the better ETFs (placebo 97th) but not the index; paper shadow logs it forward |
| Top-decile momentum only while the market > 10-month SMA, else T-bills, 1963-2015 (Lab-BY, lab) | **PASS (registered), recent era poor** | 13.9%/yr, Sharpe 0.84, max DD −29% vs market 10.1% / 0.71 / −50%; but 2016-26 7.4% vs 15.0%. Shadow records the filter; no live change |
| Industry momentum + 10-month market filter, 1963-2015 (Lab-BZ, lab) | **PASS (registered), recent era poor** | 14.6%/yr Sharpe 0.91 max DD −28% vs market 10.1%/0.71/−50%; but 2016-26 5.6% vs 15.0%. Momentum family: 4 long-history passes, all lag the index since 2016: do not deploy on the 60-year record |
| 3x daily-levered market with a 200-day exit (Gayed & Bilello), French daily 1963-2015 (Lab-CA, lab) | **dead (risk bars)** | 17.4%/yr vs 10.0% but Sharpe ≈ market's (fails 1990-2015), max DD −75%, worst 12m −55%; real UPRO 2016-26 24.5% vs SPY 15.0% with −51% DD: leverage, not edge |
| Equity put/call (10d mean) high -> higher 20-day market returns, 2006-19 (Lab-CB, lab) | **dead** | right sign both halves (+49/+58bp) but NW t 0.9 |
| Cboe SKEW high -> lower 20-day market returns, 1990-2026 (Lab-CC, lab) | **PASS (predictive), not adopted** | −30bp (1990-2007) / −110bp (2008-26), NW t −2.34; main declined it as a sizing input (its legs don't earn market direction; add. 26a); logged forward daily by the recorder |
| Overnight budget IBS/night by trailing Sharpe softmax (63/252d) or inverse vol (Round 18 AS) | **dead** | ~0..−1.5pp at 2.5bp/side; tier_hi gains are just a lower night weight when night ≈ 0 (AQ's cost gate), t ≤ 1.8 |
| IBS picks gated on 10d/60d vol ratio, either sign (Round 18 AT1/AT2) | **dead** | 2016-20 holdout has the opposite sign; −0.5 / −3.4pp/yr |
| IBS picks only when the ETF's 50d slope > 0 (MR "aligned with trend", Round 18 AT3) | **dead, harmful** | −7pp/yr, t −3.1; downtrend dips revert most in every period |
| Night leg: tug-of-war tilt (Round 19 AU3) | **shadow** | +2.8-3.2pp/yr at 2.5bp, t 2.6-3.0, holds on auction prints; DSR 0.46, 2022-23 ≈ 0; spec only (study_au_tow.md) |
| Night leg: 20d mean overnight return as tilt / filter (Round 19 AU1, AU2) | **dead** | tilt t 1.5-1.7; filter −1.4..−1.7pp at 2.5bp (its tier_hi gain is the cost gate) |
| IBS leg: hold until IBS > 0.5 or a close > prior high (Round 19 AV) | **dead** | IBS > 0.5 −5.9pp (t −2.3, both halves); prior-high exit −0.8pp (t −0.1): holds past the overnight bounce |
| Night exit later than the open auction (9:35 / 10:00 / 10:30) | **dead** | add. 7: open auction +20.1bp vs +1.9 / −9.3 / −21.5 (was only in RESULTS.md) |
| Night tilts on gap share, relative volume, late selling, idio move, 20d/52w distance, price | **dead** | add. 23: none monotone, most flip halves (was only in RESULTS.md) |
| IBS leg decided at 15:50 and bought in the close auction | **dead** | add. 6: QQQ 13.9 → 8.8%; trade at the next open (V6 index version is separate, shadow) |
| Zero-shot TS foundation models (Chronos/TimesFM/Moirai/Kronos) as filters | **not run: power** | clean post-release holdouts 11-30 months ≈ 1/6 of the trades needed; published: ~51% direction, net-negative at 11-21bp (Round 19 list #35-38) |
| Night leg: trailing closing-cross share of volume (Round 20 AX1) | **dead** | flips sign between halves (+1.1 / −1.1pp), t 0.1; mostly a low-vol proxy |
| Night leg: trailing opening-cross share of volume (Round 20 AX2) | **dead** | +1.2pp both halves but t 1.5, placebo 94%, terciles not monotone; do not retest with a new window |
| Night leg: FINRA off-exchange short-volume ratio, either sign (Round 21 AY) | **dead** | 2021-23 terciles flat; book ±0.4pp, t ≤ 0.6, feature shuffle 53% |
| Roth: buy large caps the night before their ex-dividend date with idle cash (Round 22 AZ) | **dead** | drop ratio 0.90-0.96 = +4..+7bp/event vs SPY, about one round trip; book −0.1..−0.8pp at 2.5bp/side, matched placebo 87-90% |
| Backtesting an LLM news judge on past picks (Round 25 BC) | **invalid by construction** | the model (OpenCode Go deepseek-v4-flash) knows events through 2025-10 and hallucinated a control; past verdicts can carry outcome memory. Test LLM signals forward only |
| Night leg: closing-auction imbalance at 15:50 as tilt or buy-imbalance filter (Round 26 BD, Databento) | **dead** | side buckets flip halves (sell +27.5 -> −4.8bp); tilt t 0.6, shuffle 62%; filter = lost exposure (shuffle 60%). Do not buy a live imbalance feed for this leg |
| IBS leg: skip entries indicated (09:28 opening imbalance) to gap up ≥ 0.5% / 1% (Round 27 BE) | **dead** | gap-up entries earn as much or more (2024-26 +51 / +84bp); skipping −1.9..−2.0pp, t −1.5 |
| Night leg: drop / halve picks that LULD-halted that day (Round 28 BF) | **dead (too rare)** | 0.6% of picks halt; +0.6pp, t 0.5, shuffle 80%; ~9 halted picks a year |
| Roth sleeve: UPRO when SPY > 200d SMA else BIL (lab's Lab-CA follow-up, not registered) | **user decision, not research** | leverage, not edge (1963-2015 Sharpe ≈ market, maxDD −75%; 2016-26 24.5%/yr but −51% DD); competes with IBS+night for the cash IRA's money; would fail P(DD>50%) ≤ 5%. Only as a deliberate risk choice by the user |
| Size the legs down when Cboe SKEW z >= +1 (lab's Lab-CC follow-up, not registered) | **declined** | SKEW forecasts 20-day market direction, which the legs don't earn (night = idiosyncratic overnight bounce, IBS = next-day reversal, noise = two-way intraday); market-regime size dials are dead here (add. 26a: every leg earns MORE on stressed days); t −2.34 at N 744 with clustered signal days |

## Ideas not yet tested

- Multiple formation horizons (5/10/20d) simultaneously — the one remaining
  structural fix for 14% capital utilisation
- Cross-sectional ranking instead of a binary z-threshold (always deployed)
- ~~Crypto sleeve~~ (already dead: RESULTS.md "crypto trend (BTC/ETH SMA...) = buy-and-hold Sharpe, −60% DDs; basket negative after 25bp fees")
- Limit orders at the bid instead of market-on-open — bounded by addendum 13:
  paying 0 vs 20bps is worth ~+2pp CAGR, so the upside is real but modest

---

## 6. TQQQ strongest-breakout leg — BUILT, SHADOW (addendum 19, `daily.conviction_mode`)

The PDT rule is gone (addendum 9), so the full QQQ intraday leg is now live
instead. Revisit this only after ~3 months of real intraday fills: the
TQQQ variant scores Sharpe 1.79-1.83 vs 1.70 with a smaller max drop.
First breakout of the day, strength >= 0.341 sigma, TQQQ up / SQQQ down.

---

## 5. Swing sleeve inside the daily book — RESOLVED: not worth it

Daily-refresh swing backtest (matches live): 12.3% CAGR, Sharpe 0.87. As a
sleeve it only trades return for drawdown (addendum 10). Keep it as its own
paper book.

## 7. Add SMH to the intraday leg — DONE (addendum 16, `daily.noise_extra`)

Split the 3.5x intraday budget QQQ/SMH: Sharpe 1.70 -> 1.78, max drop -20%
-> -16%, same return. Needs the noise leg generalised to several
instruments (book.noise is single-instrument today).

---

## 4. Daily-cadence book — RUNNING (paper + Schwab live since 2026-09-22)

**The plan (original, 2026-09-22):** paper-test, then real money. Done:
Schwab live since 09-22 on a $1k cap. The intraday leg switches on by itself
once the ACCOUNT holds $2,000 (`daytrade_mode: auto`; PDT retired 2026-06-04).

**Going real-money — via SCHWAB, see SCHWAB.md** (paper stays on Alpaca and
keeps running beside it). The Alpaca-live steps below still work if
`daily.live_broker: alpaca`.
```bash
# 1. Alpaca dashboard: open the LIVE account, make sure it is a MARGIN
#    account (a cash account causes good-faith violations with this book),
#    fund it, create live API keys (they start with AK)
# 2. on the server, add to .env:
#      ALPACA_LIVE_API_KEY=AK...
#      ALPACA_LIVE_SECRET_KEY=...
make daily-live-check    # connects, shows balance + margin, changes nothing
make daily-live-on       # type REAL MONEY; sets DAILY_LIVE=on in .env
make daily-status        # PAPER and LIVE side by side
make daily-live-off      # back to paper only (warns if it still holds positions)
```
The switch is stored in `.env` on purpose. `make pull` does `git reset
--hard`, so a switch kept in config.yaml would be silently undone on the next pull.

**Honest timeline:** 3k -> 25k at the backtest's 21.8%/yr is ~11 years. At the
2x setting (44.5%/yr, -22% DD) it's ~6 years. Deposits count: the live book
sizes from the real balance.


**Status:** built 2026-09-22 (`scripts/daily.py`, `swingtrader/daily/`),
research in RESULTS.md addendum 6.

| leg | what | live? |
|---|---|---|
| IBS tech ETFs | QQQ/SMH/XLK, IBS<0.2 on the last bar -> buy at the open (fractional DAY order), hold while it stays <0.2 | **live** |
| overnight losers | 15:40 ET scan: down >= 8%, within 10% of the day's low -> buy at the close auction, sell at the open auction | **live** |
| QQQ intraday momentum | noise-area breakout, 30-min decisions, flat at the close | **live** from $2k (PDT rule retired 2026-06-04; addendum 9) |

Weights 0.5 / 0.5 of book equity: 1x, no margin. Backtest (honest, 15:50
signal, 7.5bp/side): 21.8% CAGR, Sharpe 1.30, maxDD -11%. Both at 1.0 is
44.5% / -22% and needs 2x overnight margin: one line each in config.yaml.

**Day-trading gate:** $2,000 (Reg T). The $25k pattern-day-trader floor was
retired 2026-06-04. For the REAL account, ask Alpaca for a leverage-enabled
margin account (4x intraday); a standard margin account caps this leg at 1.5x.

**What to watch:**
- night-leg slippage vs the 15:40 reference price (`make daily-status`).
  Research assumed 7.5bp/side. The edge is gone around 15bp.
  2026-09-29, split by side: LIVE buys n=34 median −2.5bp, sells n=34
  median 0.0bp (mean +40.8, a few outliers). PAPER sells n=24 median
  **+200bp**: Alpaca paper open sells (expired OPGs resent at market, and/or a
  stale 09:15 mark) cost ~2%/trade, which is roughly the whole gap between paper
  night (−2.07%/trade) and live (+0.08%). Paper night P&L is not evidence
  about the strategy; judge the night leg on live fills only.
- whether 2021-23-style weakness shows up: that leg's return was almost all 2024+.
- CLS/OPG rejections in the email. Paper has not yet been proven to accept
  auction orders from this code; the first 15:40 run is the test.

**Not modelled:** at $3k, whole-share rounding on auction orders ($150 per
name), and names above ~$150 buy one share or none.

## Study Y — the book's rate at size (2026-09-30, report, `research/drafts/study_y_scale_book.md`)
- Book (IBS + noise, night capped) at CENTRAL impact: ~20% pre-tax at $100k, 17.8% at $500k,
  15.9% at $1M, 8% at $5M. Taxable after yearly ST tax (32%): 12.5% at $500k.
- **Roth beats a held index to ~$2.5M; taxable only to ~$250k** (SPY same window 15%/yr,
  13.5% after deferred tax). Taxable money past ~$250k -> held index unless a new liquid edge.
- Next candidate study: noise leg as an intraday overlay on an index-held account.

## Round 17d (2026-09-30): brief #6 (0DTE) and #7 (tax location) — report, nothing to build
- **#6 0DTE conviction trade: parked.** One QQQ 0DTE contract controls ~$60k notional (17x the
  0.5-weight TQQQ trade's ~$3.45k QQQ exposure at $2.3k). Needs ~$30-40k equity to be sizable, and
  ThetaData is $960/yr = ~42% of a $2.3k account. No options data in the repo. `study_ar_remaining.md`.
- **#7 asset location: structural, no change.** Every leg is <= 1 session (all short-term); the only
  lever is which account + the wash guard. Run IBS + night in the tax-free Roth (Study AQ), keep the
  G4s guard (add. 39), F3 off in the Roth. `study_ar_remaining.md`.
