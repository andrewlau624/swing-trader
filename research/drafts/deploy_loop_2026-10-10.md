# Deploy loop (started 2026-10-10)

Order: PHASE 1 items 1-4 (deploy small validated items, log-only until "go"), then PHASE 2 (shadow readouts / one data question / new mechanism).
Read each wake-up: CLAUDE.md, NEXT.md do-not-redo table (line ~1204), trend_loop_2026-10-10.md (free frontier exhausted, N 930).

## Item 1 - PREF-EX + ETDX (Roth) - WAITING (gate 0/60 forward ex-nights)
Source: him `state/pref-ex.jsonl` (349 rows: 287 scored, 52 upcoming, 10 no_cross), read 2026-10-10 06:15 UTC; FORWARD_FROM 2026-10-07,
BACKFILL 2026-09-01, gate NEED 60 forward ex-nights with >= 1 eligible event (pass = net CO night-mean >= +20bp, median > 0, t >= 2).
- Forward: 0 nights (first forward ex-dates 10-09 DBRG.PRH/PRI/PRJ, T.PRA/PRC score on the next run; then 10-13/14/15/16/21).
- Backfill Sept (d0 2026-08-31..10-01), per-night stats, model slippage = 10bp RT + sqrt(5)/10 x half-spreads (CO 24.2bp, CC 18.6bp):

| cls | nights/events | CO gross (t) | CO median | CO net | CC gross (t) | CC median | CC net | backtest CO / CC |
|---|---|---|---|---|---|---|---|---|
| pref | 15 / 207 | +55.7bp (3.5), hit 90% | +59.9 | +31.6 (t 2.0) | +6.9 (0.4) | +15.2 | -11.7 (t -0.7) | +38 / +28 (median +35 / +26) |
| etd | 7 / 71 | +35.4 (6.1), hit 80% | +30.2 | +11.3 (t 1.9) | +14.1 (1.1) | +30.8 | -4.5 (t -0.3) | +44 / +39 |

- Measured cross-vs-mid cost (median, + = worse): buy at d0 close +0.0bp (n 277), buy at T-10 close +0.0 (n 276), sell at E close
  +2.8bp (n 276). Quoted half-spread at the close ~20.5-21.1bp. => the crosses print at mid; the model's 18.6-24bp slippage is ~6x
  the measured ~3bp RT. At measured cost pref CC is ~+4bp night-mean / +12 median, pref CO ~+53 / +57.
- Reading: CO (sell at the open cross) reproduces the backtest; CC (MOC both legs, the only Schwab-placeable form) is much weaker
  in the Sept sample (night-mean +7 gross, t 0.4) than the 2021-26 backtest (+28). One month, 15 nights: not a verdict, but the
  Schwab-safe form is the one under question. Nothing to deploy until the forward gate reads.
- Broker eligibility still "unverified": `logs/pref-cross-test.jsonl` shows only a resolve + two dry_run buys of T/PRA (10-08);
  no live 1-share test order yet (user-run).
- Gate ETA: ~15 pref ex-nights/month -> 60 forward nights ~ early-to-mid Feb 2027 (etd gate separate, ~7/month -> later).
- Money (backtest CO, 5% of auction $, 10bp RT, from pref_exec_out / ETDX): ~$380/yr at $2.3k, ~$790 at $10k, ~$920 at $25k
  (dollars plateau above ~$5k); CC form ~60-70% of that. With ETDX ~1.5x. Live Sept CC would have been ~0.
- Action: none (no live module written; gate not met). Next read: after the 10-13..10-16 ex-nights score (>= 5 forward nights).
- research-shadows runs as a systemd user timer (weekdays 12:20 UTC; next Mon 2026-10-12), so the 10-09 ex-nights score on 10-12.

## Item 2 - CEF-RV (Roth) - WAITING (gate 0/60 forward closed trades; panel refreshed)
Source: him `state/cef-rv.jsonl` (124 rows: 118 open, 5 closed, 1 pending), FORWARD_FROM 2026-10-08 (first forward signal week Fri 10-09),
gate NEED 60 closed forward trades over >= MIN_WEEKS 10 entry weeks, excess vs EW CEF (open->open) >= +60bp, t >= 2, median > 0; KILL = mean <= 0.
- Forward: 0 closed, 0 open. The 10-09 signal week had not been processed: the server panel ended 2026-10-02 (stale).
  **Refreshed from the Mac (`make cef-rv-panel`): 354 funds (7 failed), latest week 2026-10-09, pushed to him.** Monday's 12:20 UTC
  research-shadows run will log the first forward entries (entry = Mon 10-12 open).
- Backfill (signal weeks 09-04..10-02, entries 09-08..10-05): 5 closed / 2 entry weeks: excess vs EW CEF OO +295bp (median +230, hit 5/5,
  t 6.7), CC +158bp; raw net OO -72bp (CEF tape fell; the excess is relative). NUW +185, EIM +230, IGI +439, PDX +436, WIW +186 (bp).
  5 trades over 2 weeks: a sign check only. 118 open positions across 5 backfill weeks (~24 entries/week).
- **Execution question RESOLVED (user-run live test, Roth, 1 share JRI, `research/sim/cef_open_test.py`):** pre-open market "opg"
  orders, NYSE-directed route refused (400), AUTO route used. Buy 10-08 filled 10.40 at 13:30:00Z = official open cross 10.40
  (cross size 7,607 sh); sell 10-09 filled 10.58 at 13:30:04Z = official open cross 10.58 (cross 2,402 sh). **0.0bp on both legs.**
  Read from Schwab order status directly (the script's `report` command only works on the trade date; Alpaca auctions 403 on a
  weekend date) - the report rows are NOT appended to `logs/cef-open-test.jsonl` (left untouched). This also supports the PREF-EX CO
  form's open-leg sell (same AUTO pre-open path), though on a CEF not a preferred.
- Gate ETA: 10 forward entry weeks = signal 2026-12-11 at the earliest; 60 closed trades depends on exit signals (backfill holds
  1-3 weeks so far) -> plausibly late Dec 2026 / Jan 2027.
- Money (CEF-ALPHA: ~+125bp/trade excess vs EW CEF, ~+4.8pp/yr on deployed capital, Roth, long-only): ~$110/yr at $2.3k,
  ~$480 at $10k, ~$1,200 at $25k on top of the CEF beta held. Below the +8pp stand-alone gate; a Roth upgrade over holding beta.
- Action: panel refresh only (authorized procedure). No live module. Next read after >= 2 forward entry weeks (10-19+).

## Item 3 - Night-leg size-ups within NX (S1 losing-night x2, S2 1.3x cap .15) - PRESENTED, user decides
### Live auction-cost audit, every fill since 09-23 (him `logs/daily-fills-{live,roth}.jsonl`, read 2026-10-10)
245 fills (live 149, roth 96). Auction fills scored against the official SIP print (Alpaca `/v2/stocks/auctions`, sip) of the
same session: open-auction fills stamped 13:30Z, close-auction fills 20:00Z. Cost = fill/official - 1, signed so + = worse.

| leg / auction | n | mean bp | median bp | fills > 1bp off |
|---|---|---|---|---|
| night buy, close auction (MOC) | 97 | -0.04 | 0.00 | 2: SPCM 09-23 -11.8 (cross 235 sh, favourable), SKDD 10-01 roth +7.8 (cross 1,900 sh) |
| night sell, open auction | 95 | +0.60 | 0.00 | 1: QCML 09-29 +56.8 (3 sh vs a 446-sh open cross, filled 13:30:02 - likely missed the cross) |
| IBS, open auction | 14 | 0.00 | 0.00 | 0 |
| T-bill, open auction | 10 | 0.00 | 0.00 | 0 |
| noise, intraday (vs decision ref) | 29 | +0.44 | -1.45 | n/a (ref is not an auction) |

- 213 of 216 auction fills printed exactly at the official auction price. **True cost still ~0bp/side** (prior audit: 130 fills,
  same). One night buy (RBLX 09-28, 1 sh, filled 20:04:50Z) was not an auction print: the 1-share night probe filled after the
  close; immaterial, noted.
- Night exits measured: 95 (all since 09-23) at +0.6bp/side mean -> `lever_ok` thresholds (>= 50 exits, <= 10bp/side) are met on
  the taxable book; the gate is off only because `lever_weight: null`. The `[lever-g1]` shadow on 10-09 reads n 50, mean -1.9bp,
  clustered 95% UB +0.5bp -> would_open yes. The re-arm review point in signals.py is 100 night round trips: we are at 95.
- Live-vs-replay (research/drafts/recent_regime_2026-10-08.md): 67 shared trips, corr .998, within +-11bp -> the "gap >= -10bp/trade"
  re-arm condition is met on that read. `scripts/review.py --since 2026-09-23` ran to exit 0 on him but printed nothing to stdout
  (not chased; the memo covers section 4).

### S2 - "moderate 1.3x cap .15" (NX: +0.59bp/night, t 3.10; subs 2003-07 +0.39 / 2008-09 +0.54 / 2010-15 +0.78; maxDD 9.2% vs 6.2%)
- NX S2 definition (research/sim/nx.py:57,799): night leg weight 0.65 (from 0.50) with per-name cap 0.15, IBS leg UNCHANGED at 0.50
  -> 1.15x gross overnight. The cap half is already live (commit e4d9126, `night_max_name_pct: 0.15`, both books).
- The existing `lever_weight: 0.65` key is NOT S2: it lifts BOTH legs to 0.65 (1.3x gross, add. 29 "moderate"); IBS at 0.65 was
  never judged by NX and SHAR-IBS found IBS weak/cost-bound pre-2016. Keep IBS at 0.5.
- Roth: cash account -> `_lever_gate` forces levered=False and `_cash_scale` rescales to 1.0x total; S2 cannot apply there (it
  would only shift the Roth mix to night 0.565 / IBS 0.435). Taxable book only.
- **Proposed diff (NOT applied), exact NX-S2 on the taxable book via the existing profile mechanism (swingtrader/config.py:302:
  DAILY_LIVE_PROFILE applies to "live" only):**
  ```yaml
  # config.yaml, under daily.profiles:
      nx_s2:                       # Study NX S2 (2026-10-06, nx_out.txt:81): night 0.65, IBS 0.5, cap .15; taxable only.
        night_weight: 0.65         # 1.15x gross overnight on the margin book; Roth unaffected (profile is live-only)
        night_max_name_pct: 0.15
  ```
  plus on him `.env`: `DAILY_LIVE_PROFILE=nx_s2` (user action), and a REGISTRY entry "NX-S2 live" in the same commit (what it tests:
  the +0.59bp/night increment forward; reader: night-leg P&L at 0.65 vs the 0.5 counterfactual from the same fills).
  Preconditions: Schwab margin enabled and equity >= $2,000 (taxable ~$2.3k is close to the floor; a drawdown below $2k ends the
  margin and the extra 0.15 would be refused, not forced); open-sell cost stays ~0bp (`make review` 2b / this audit).
- Money (NX basis +0.59bp/night ~ +1.5pp/yr on the leg's capital; add. 29 in-sample says more, ~+4pp): taxable $2.3k ~+$35/yr,
  $10k ~+$150, $25k ~+$370; Roth $0 (not applicable). The 2021-26 regime pays ~2x NX, but NX is the honest number.

### S1 - "losing-night x2" (NX: +0.37bp/night, t 2.31; 227 flagged nights of 2003-15; maxDD 7.9% vs 6.2%)
- NX S1 definition (nx.py:57,795): if yesterday's night-leg equal-weight return <= -2%, tonight's night weight x2 (0.5 -> 1.0).
- **Not implemented in live code**: no config key, no executor logic (grep: losing/prev_night/S1 absent). It needs new code
  (yesterday's realised night return from `book.closed`, a `night_lose_mult`/`night_lose_thresh` pair, REGISTRY entry, tests)
  and 1.5x gross on flagged nights -> taxable margin book only; impossible in the Roth (cash scale).
- Ceiling: +0.37bp/night ~ +0.9pp/yr on leg capital, on ~7% of nights, concentrated in the worst tapes (the day after a >= 2%
  leg loss). Money: $2.3k ~+$20/yr, $10k ~+$90, $25k ~+$230. Recommendation: do not build; the increment is below the cost of
  the extra margin risk on a $2.3k account and below any gate in CLAUDE.md. User decides.

### Status
- S2: config diff presented (above); waiting for "go" (then: commit profile + REGISTRY + test; user sets DAILY_LIVE_PROFILE on him).
- S1: presented as decline-recommended; no code until the user asks.
- Item 4 (ROTH-STACK ordering + ETF twins) is gated on items 1-2 being ON: both WAITING -> item 4 DEFERRED, not run.
- PHASE 1 state: 1 WAITING, 2 WAITING, 3 PRESENTED (user), 4 DEFERRED. PHASE 2 may start (forward-shadow readouts first).

## PHASE 2(a) - forward-shadow readouts vs registered gates (him `state/`, `testing.status`, read 2026-10-10)
None of the six is at its gate; none has a kill triggered. No verdicts, no deployment.

| shadow | gate (frozen) | where it stands | read |
|---|---|---|---|
| CROWD-HOLD (hold crowded-night picks to the close) | 30 crowded nights; PASS mean hold >= +20bp, t >= 2, halves > 0, median > 0; KILL mean <= 0 | 1/30 crowded nights: -250bp (one night) | nothing; 1 night |
| BB (15:40 quote imbalance on night picks) | 300 picks logged, verdict once at 300 | 59/300 (+45 this week) | nothing until 300; QI-HIST (N 898) already says the effect is ~1/4 of the peek, skip-tercile still positive -> low prior |
| ID3 (insider-day, ADV >= $20M) | 300 scored, mean net > 0 and NW t >= 2 to propose; mean <= 0 at 300 retires | 10/300, mean +22.0bp, t 0.78 | nothing; EV2 0/60, EV2-big 0/60, ID3-big 3/60 (+1.0 vs rest +31) |
| M1 methodology track (ID1/ID2/EV1/N2) | ID1 5,400 / ID2 2,650 / EV1 560 / N2 48 | ID1 10 (+116 vs pred +15, t 1.58), ID2 6 (+79 vs +16, t 1.02), EV1 0, N2 0 | nothing; needs years at this rate |
| CPC ledger (split-offs, odd-lot tenders, round-ups) | 12 months, >= 2 independent events, >= +8pp/yr at $10k after costs | 5 events: MDT split-off 10-02 **MISSED**; 4 reverse-split round-ups **ACTION_REQUIRED** (SUGP 10-07 - past; POAS, NXGL, ZBAO effective 10-12); completed 0; realized $0 | manual (user) actions; the ledger cannot act. Round-up value ~$10-40 each if Schwab rounds up (unverified, B1) |
| SPLIT-T0 / SPIN-T0 (ex-date night at official crosses) | 40 forward common-stock events; PASS median raw-SPY > 0 and mean > 10bp; KILL median <= 0 | forward 0/40; backfill n 37 mean +77 median +21 hit 57%; next spin SKYD 10-13 | nothing; SPLIT-CROSS (N 900) recommended the shadow filter ADV >= $5M/$50M, ratio <= 2:1, no ADR/OTC - not yet applied to the shadow (recommendation stands, gate unchanged) |
| LETF-NIGHT (single-stock LETF desk selling at the close after a <= -5% day) | spec only (golden_egg 10-06, "PROMISING, half is beta, forward-only") | **no shadow module, no state file, no REGISTRY entry** | not instrumented. Building it = a log-only shadow (needs LETF $vol share per underlying; Alpaca bars for the LETF list). User said "forward shadow OK" (resurrection session): build is allowed but not a deploy item; ceiling unquantified (2024-26 official crosses only) |

Other registry items worth one line: Lever gate G1 shadow would_open yes (n 50, mean -1.9bp, UB +0.5bp); IBS 1.25x overlay 3 scored (delta -0.10pp);
Daybook PROD 6 sessions -4.4bp/day (Config B -9.8, C -19.7); TME-L first window Oct-2026 month-end; TOP2 / Hedge / Repeat-loser 0 scored;
Capacity shadow 9 sessions: night at $250k gross +111 / net +79bp (max 0.10% ADV).

### What needs the user from 2(a)
- CPC round-ups POAS / NXGL / ZBAO (effective 10-12): manual 1-share buys before the effective date if the user wants the
  round-up tested (B1 "does Schwab round up" is still unverified; ~$10-40 each). Not a bot action.
- LETF-NIGHT: say "build the shadow" if wanted (log-only, REGISTRY entry in the same commit). Otherwise it stays a spec.

## PHASE 2(b) - data-buy-rule math, two user decisions (no purchase made, no code run)
Rule (CLAUDE.md, part 7): buy only if expected information value > cost: (1) compelling mechanism, (2) free evidence does not
already weaken it, (3) experiment specified enough to falsify, (4) payoff materially larger than existing edges, (5) no cheaper
dataset answers it. Research-priority gate: ceiling at $10k >= +8pp/yr at <= 50% capture.

### (i) Deal-break database for BREAK-REV
- Mechanism (1): PASS - merger-arb funds are forced sellers of the target in the sessions after a deal breaks (named counterparty,
  must liquidate, capacity-limited in the small account's favour).
- Free evidence (2): MIXED-WEAK. `break_rev_out.txt` (n 44, 2007-2026, EDGAR FTS item 1.02 => 1,008 hits => 44 clean breaks,
  <= 6/yr): A2 D0c->D5c net +3.04% t(month) 1.53, median +2.92, halves +1.18/+3.65, hit 55%, control -0.18 (diff +3.22 t 1.52);
  **ex-top-5 -0.44%** (the mean is 5 outliers); A1 D1c->D10c median -1.97; A3 D3c->D20c -3.48% t -1.59. Path peaks +4.4% at day 9
  and is ~0 by day 15. Shock buckets: the biggest breaks (<= -20%) earn +0.21%, the mild ones (-12..-7%) +5.06% - inverted vs the
  forced-selling story (deeper break = more forced flow should mean a bigger bounce). Read: unproven, and the free sample's shape
  argues against the mechanism as much as for it.
- Specified (3): PASS - BREAK-REV is pre-registered (N 924-927), bar +1.0%/event net, arms frozen; a new sample would be judged once.
- Ceiling (4): events/yr x net x deployable x capture. US-listed public-target breaks with tradable targets ($ADV >= $1M): realistic
  15-30/yr, not the 40 assumed in trend_loop. At 25/yr x +1.0% (the registered bar; the honest median after ex-top-5 is ~0) x 70%
  x 50% = **+8.8pp/yr at $10k only if the +1% median survives**; at the free-sample ex-top-5 (~0) the ceiling is ~0. At $2.3k the
  same %, ~$200/yr; at $25k ~$2.2k/yr but position caps in thin post-break names start to bind.
- Cheaper dataset (5): **no retail-priced deal database exists** (Dealogic / Refinitiv SDC / Mergermarket are institutional, $10k+
  /yr); Sharadar `actions` has only completed deals (acquisitionof/by/cash/stock, spacmerger) - no announced/terminated deal
  table (checked 2026-10-10). The cheaper path is FREE work, not a purchase: widen the EDGAR extraction (8-K item 1.01/1.02
  "termination of merger agreement", DEFM14A/PREM14A universe cross-matched to a later 8-K 1.02, 425 filings, 'terminat*' FTS
  with issuer-name matching) to recover the ~2/3 of breaks the current fetch misses. Expected yield 15-25/yr vs 6 now.
- **Verdict: DO NOT BUY (fails 2, 4 is conditional, 5 has a free alternative).** Decision for the user: (a) spend one research
  session on the free EDGAR widening (then re-judge BREAK-REV once on the enlarged pre-2021 sample as a registered re-run; N+1), or
  (b) leave BREAK-REV DATA-LIMITED. Recommendation: (a) only if nothing else is runnable - the free-sample ex-top-5 and shock-
  bucket inversion make a PASS unlikely.

### (ii) OPRA signed dealer gamma (Databento OPRA statistics + definitions, SPY+QQQ)
- Cost: ~$180/yr of history per the observed $0.36-0.37/day; the decisive one-shot test in `study_gamma_precast.md` is ~$30 windowed
  (OPEX + flip weeks) to ~$360 for 10 years of both symbols; NOT a subscription.
- Mechanism (1): PASS - dealers short gamma must hedge with the move (sell into drops, buy into rallies): a named, constrained
  counterparty; the effect is on the UNDERLYING (not the killed OI-pinning strike effect).
- Free evidence (2): WEAKENS. The free proxy (SqueezeMetrics GEX, `data/research/gamma/DIX.csv`, 2011-2026, model-signed) gave
  +8.3bp t 1.9 in the market-map probe and failed the untouched 2016-20 window (memory, 2026-10-05); COTX/CBAS/VTS (derivatives
  frontier) found every free derivative state arbitraged flat or drift-only at the daily tier; OI-pinning killed. Prior lowered
  three times; the paid data would sharpen the sign of G_t, not change the tier.
- Specified (3): PASS - GAMMA-STAT spec frozen (flip-day close -> +5 sessions, both halves, min +25bp/flip-day net, 25bp/leg cost,
  2x shock); kill = forward net <= 0 after ~120 short-gamma days (`shadow_dealer_gamma.md`).
- Ceiling (4): FAILS the +8pp gate. Flip days ~10-20/yr x +25bp x 100% of the SPY sleeve x 50% = +0.1-0.25pp/yr standalone; as a
  protective GATE on the night/IBS legs the spec's own honest estimate is +1-2pp/yr (VENM's class). Money at $10k: ~$100-200/yr
  best case; $2.3k ~$25-45; $25k ~$250-500.
- Cheaper dataset (5): the free GEX proxy already exists and already underperformed; a forward log-only shadow on it costs $0 and
  would show whether the state has any 2026 bite before paying for history.
- **Verdict: DO NOT BUY (fails 2 and 4; 5 says run the free proxy forward first).** Consistent with the spec's own
  "DO NOT PURCHASE YET". Decision for the user: fund $30-360 anyway (information value: closes the last derivatives gap, ~+1-2pp/yr
  protective ceiling), or leave DATA-TARGET. Recommendation: leave it; if anything, add the free-proxy gamma state as a log-only
  column on the night/IBS shadows (REGISTRY entry) - zero cost, forward evidence.

### 2(c) - new mechanism: none runnable
No candidate on hand has all three of (named forced counterparty, never-inspected history, small-account capacity) without a user
data decision: the idea scans of 10-08/10-10 enumerated and killed the free-data space (trend_loop idea 8-9 and the "killed without
code" list). Nothing to pre-register this wake-up.

## LOOP END STATE (2026-10-10)
| item | status | needs the user |
|---|---|---|
| 1 PREF-EX + ETDX | WAITING 0/60 forward ex-nights (ETA ~Feb 2027); Sept backfill CO on-backtest, CC weak; measured cross cost ~3bp RT | live 1-share Roth MOC test on a preferred (unverified broker path) |
| 2 CEF-RV | WAITING 0/60 closed; panel refreshed to 10-09; JRI open-cross test 0.0bp both legs | nothing |
| 3 night size-ups | cost ~0bp on 216 auction fills (213 exact); S2 = profile `nx_s2` (night 0.65, taxable only) PRESENTED; S1 not built, recommended against | "go"/decline on S2; S1 yes only if wanted despite ~$20-230/yr |
| 4 ROTH-STACK + twins | DEFERRED (gated on 1-2 ON) | - |
| 2(a) shadows | none at gate; CPC: MDT split-off MISSED, 3 round-ups ACTION_REQUIRED 10-12; LETF-NIGHT not instrumented | round-up 1-share buys (manual) if wanted; "build the LETF-NIGHT shadow" if wanted |
| 2(b) data buys | deal-break DB: DO NOT BUY (free EDGAR widening is the alternative); OPRA gamma: DO NOT BUY (run free proxy forward) | fund anyway, or approve the free EDGAR widening session |

## User decisions (2026-10-10): "go for 1, 2"
- Item 3 / S2: COMMITTED as profile `nx_s2` (config.yaml), REGISTRY "NX-S2 night size-up (taxable, profile nx_s2)" (testing.py),
  test `test_nx_s2_profile_raises_only_the_night_weight` (tests/test_daily.py). Arms only when the user sets
  `DAILY_LIVE_PROFILE=nx_s2` in `.env` on him and the repo there is pulled; until then live runs at the base 0.5.
- Item 1 / live preferred MOC test: USER-RUN via `research/sim/pref_cross_test.py` (Roth, 1 share, --go). Candidate: BAC.PRP
  (ex 2026-10-15, div 0.2578): buy MOC Wed 10-14 before 15:43 ET, sell MOC Thu 10-15, `report` after 16:15 ET each day. Alternates:
  NEE.PRW (ex 10-14, buy 10-13), BAC.PRO (ex 10-15). Run `resolve` first for the Schwab symbol format (T/PRA worked on 10-08).

## Autonomous run (user out; approvals deferred to the end) — item A1: BREAK-REV2 (N 930 -> 931) FAIL
- Free widening done: 710/1,008 FTS hits had no display-name ticker; Sharadar TICKERS carries CIKs (36,723 delisted) -> 85 NEW events
  (all by CIK), 128 pooled, 5.8 breaks/yr. Pre-registered before any price read (round1_prose.md "Study BREAK-REV2").
- **FAIL x3, wrong-signed** on the new sample: A2 D0c->D5c -2.84% net (t -1.22, median -4.22, hit 32%); A1 -2.26; A3 +1.62 t 0.3
  (ex-top5 -5.86). Pooled 128 all <= 0. Deeper breaks fall further. Prediction (thinner targets bounce more) falsified.
- Consequence for 2(b)(i): the deal-database question is CLOSED, not just "do not buy": more events would not flip the sign.
  Post-break reversal class closed. No approval needed.

## Autonomous run — item A2: LETF-NIGHT log-only shadow BUILT (not deployed)
- `swingtrader/daily/letf_night_shadow.py` (LOG_NAME letf-night.jsonl): the frozen forward rule from round1_prose.md "Amendment —
  Study LETF-NIGHT" (N 851 -> 852): close >= $5, session $vol >= $10M, r <= -5%, lagged 20d single-stock-LETF $vol share > 2%;
  closing cross -> next opening cross at official SIP prints, 2.5bp/side; control = same screens, no LETF; gate 120 event days.
  LETF -> underlying map `swingtrader/daily/letf_map.json` (531 funds / 294 underlyings, Sharadar fund names;
  `research/sim/letf_map_build.py` refreshes it from the Mac). Universe = the night leg's eligibility cache. REGISTRY entry
  "LETF-NIGHT: single-stock LETF close rebalancing -> overnight reversal" (need 120 event days); 4 tests; ExecStart line added to
  `deploy/research-shadows.service.in`.
- Local smoke run on the server's 10-09 universe snapshot (real Alpaca bars + crosses, read-only): 
  4/120 event days, 32 events: net -34.7bp/day (median day -47.6, median event +79.1, hit 59%, t -0.39); vs SPY +22.6; control 7 days -0.9bp; night-leg overlap 3/32
scanned [('2026-09-30', 2, 31), ('2026-10-01', 0, 49), ('2026-10-02', 0, 30), ('2026-10-05', 0, 29), ('2026-10-06', 1, 73), ('2026-10-07', 11, 96), ('2026-10-08', 18, 72), ('2026-10-09', 1, 38)]
control scored 380
  10-07: 6 treated events (all negative, -1.6..-2.9%); 10-08: 18 treated (16 positive; AAOI/COHR/LITE +5-6%), 3 overlap the night leg.
  Two days, not evidence. Caveat logged in the module: the universe cache has no asset class, so the control can include ETFs.
- **Approval needed to deploy:** on him `git pull` + `bash scripts/install-schedule.sh` (regenerates research-shadows.service with
  the new line). Until then the shadow only exists in the repo.
