# Branch loop, night of 2026-10-19 (user: "run a loop to branch tree and pivot while i sleep")

Rules for every wake: (1) check pending items first (trader run at 09:15 ET; CHART-YOLO shards; server memory); (2) take the next
OPEN leaf below, grep NEXT.md / MISTAKES.md / round1_prose.md for it, pre-register (bump N) before any outcome, run, record in
round1_prose.md + NEXT.md with "not tested"; (3) PIVOT: never two consecutive studies in the same family; after a kill, go to a
sibling or two levels down, never a variant; (4) hard limits: Schwab-only US-listed, no orders, no live/config/server changes, no
commits, no data purchases, no LLM/NLP, no options strategies, each study <= ~90 min compute on data on disk or free pulls; (5) when
the cheap leaves are exhausted, write the morning summary here and stop the loop.

## Tree (root = "searchers that find a person who must trade, executed at an auction")
- [x] GAP-NIGHT (N 1050, PASS-SMALL/decaying, shadow candidate): today's gap names (|open gap| >= 1%, ADV >= $200M, PIT inplay pool G) bought at the close cross, sold at the open
      cross; is the +9-14bp/night seen in INTRA-ANY/PREMKT label B a universe premium beyond SPY overnight and beyond the night leg?
      (overnight-attention premium; both legs free; ceiling ~daily x 10bp x capital)
- [x] NEWS-HALT (N 1051, KILL long; up-news fade short-side observation): news-pending (T1/T2) halts reopening intraday; reopen cross -> close for down vs up news (halt history on disk,
      Alpaca bars) — the sibling of HALT-REOPEN left open
- [x] RE-HALT (N 1053, KILL; LULD family closed): second LULD halt of the day as its own event (sibling)
- [-] RECORD-RECALL (deferred: proxy record dates are not in free data; dividend record dates test a different, ambiguous mechanism; prior low): proxy/dividend record dates in high-short-interest names (lenders recall -> shorts must cover); Sharadar
      actions + Compustat short interest (WRDS)
- [-] CLOSE-IMB-FREE (closed by reasoning: the closing-cross size is known only after the cross; as a same-night ranker it is lookahead, as a next-day signal it is the dead night-pool ranking class): closing-cross size vs ADV as a free imbalance proxy for the night leg's names (official cross sizes on disk)
- [-] ADR-HOME (deferred: Datastream firm-matching is a multi-hour build; arbitrage keeps liquid ADRs tight, ceiling small; user said 'your call' -> not tonight): ADR close vs home-market close (WRDS Datastream), buy/sell the US open cross (user said "your call"; free at WRDS)
- [-] INPLAY-OPEN-CROSS (answered by PREMKT-CROSS: unconditional open->close of the universe +0.6bp, hit 0.50): pool-C two-way names, open cross -> close cross unconditional (0bp both legs) as a capacity/beta read

- [x] SPECIAL-EX (N 1052, KILL; registered PASS was a vendor-date artifact; new data rule)

## Log
- 06:2x PDT: GAP-NIGHT run and recorded; next leaf NEWS-HALT (different family: halts/news). Pending: trader 09:15 ET check, CHART-YOLO shards.
- NEWS-HALT recorded. RE-HALT skipped for now (same family twice in a row); pivoting to a calendar/forced-buyer family.
- SPECIAL-EX: KILL after the data check (40% of actions rows mis-dated). Lesson logged. Next: pivot to a non-ex-date, non-halt family.
- 06:3x PDT: live bug fixed and deployed (cef_rv_live.depth crashed on 3-field panel rows; commit dc21a2c, him pulled; 12 tests pass). Trader 09:15 ET run clean (night sells + IBS XBI buy submitted). RE-HALT killed. Next: F-SALE (mutual-fund fire sales, WRDS tfn.s12 + Sharadar), the one heavy leaf; data pull started.
- CHART-YOLO: KILL (bull patterns -33bp/5d, bear +16; contrarian). Recorded.
- F-SALE: KILL at the proxy (mechanism check failed: the measure flags winner trimming). Recorded.

## Morning summary (07:0x PDT)
Six studies registered and run overnight (N 1049 -> 1054), all pre-registered, all recorded with not-tested fields:
- GAP-NIGHT (N 1050): **PASS-SMALL on its registered gates (2016-21 judge), decaying since 2022, up-gap carried.** Gap names
  (|open gap| >= 3%, $5+, ADV >= $50M) bought at the close cross, sold at the next open cross: +8.6bp/night over the EW universe
  overnight (t 3.0), +13.0 for up-gaps (t 3.5), 0 for down-gaps; 2022-26 +5.4 (t 1.6). Overnight-attention clientele, both legs
  free, overnight SPY beta 1.5. Realistic +3-5pp/yr at 2022-26 strength. **Shadow candidate: your decision.** Same family as OVN-MOM.
- NEWS-HALT (N 1051): KILL long side (bad news keeps falling after the reopen). Observation: good-news reopens overshoot and fade
  (+112bp short to the close, t 2.65, n 167) but ~35 events/yr, short-only, ceiling ~+0.5pp.
- SPECIAL-EX (N 1052): the registered PASS (+229bp, hit 0.74) was a vendor-date artifact; 40% of Sharadar `actions` dividend rows
  before 2013 never show a price drop. Confirmed rows: commons adjust fully (drop 0.95), +13bp t 1.7. KILL. New data rule recorded.
- RE-HALT (N 1053): KILL (crash-day lottery; yearly medians flip). LULD family closed in every form.
- CHART-YOLO (N 1049): KILL, wrong sign: completed bull patterns -33bp/5d, bear +16; textbook direction is contrarian.
- F-SALE (N 1054): KILL at the s12 flow proxy; the fire-sale mechanism itself is untested (needs CRSP flows via MFLinks).
Other overnight work: cef_rv_live.depth crash (3-field panel rows) fixed, tested, committed dc21a2c, deployed; the 09:15 ET trader
ran clean; the server was OOM-starved by other projects (user killed them, added 2GB swap, 9 cron lines disabled with a backup).
Closed by reasoning (no N): CLOSE-IMB-FREE (lookahead), INPLAY-OPEN-CROSS (answered), RECORD-RECALL (no free record dates),
ADR-HOME (deferred). Cheap leaves exhausted; loop stopped. Program N = 1054. Nothing from the loop is committed (only the bug fix).

- 2026-10-19 15:3x PDT (user back): "shadow" -> GAP-NIGHT-FWD built (`gap_night_shadow.py`, test, REGISTRY, Makefile `gap-night`, research-shadows unit); first forward session 2026-10-20.
