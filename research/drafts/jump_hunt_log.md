# Jump & ride hunt log (prompt_jump_hunt.md), session llm-trader-51

## STATE (update after every idea)
- program N: 768. k (ideas judged or registered): 8 — J1-J4 judged DEAD; **J5 (R2-25 buyback >= 15% of mcap,
  un-gapped, JUMP tp205), J6 (S5 forward split, JUMP trail20), J7 (R2-19 two upgrades in 10 days, JUMP tp205), J8
  (R3-15 initiation with a 2x target, RIDE hold60) registered, judges pending** the news archive reaching 2025-07
  (rebuild with `jump_rebuild.py`: select-half hashes must match; they matched on the archive through 2024-03).
- Ideas explored: 77 (see the log). Rounds of idea generation: 4 written (R1 62 + R2 20 + R3 20 + R4 20 = 122).
- dropped before a run (data): H11/C8, S1/S1v, D7, R3-4, R3-20.
- running / queued: R4-18, R4-19 (EDGAR builds + explore queue), H21 D1 D8 C6 C5 (explore queue), R3-18 (10-K
  themes, queued), R3-7 (LLM extraction, after R3-18), R3-6 (13F; explore after the news download: 13k symbols of
  bars), H4/V1/H13 (WSB 2021 still downloading: January 2021 alone is enormous).
- data sources verified: news (at 2024-04, 3 threads till Sunday 16:47), Reddit (small subs; WSB 2016-20 + 2022-24),
  Wikipedia (+ CEOs), EDGAR FTS/form.idx/companyfacts/frames, CT.gov, openFDA, Federal Register, SEC FTD, SEC 13F,
  Form 345 2014-26, FINRA SI 2020-06+, Nasdaq earnings calendar.
- data sources broken: defense.gov (403), PatentsView bulk (403), Yahoo trending 2016-17 snapshots.
- why things die (running): EXIT LIQUIDITY (crowd attention), TWO-WAY, LOTTERY (incl. J1, J3, J4), PRICE PROXY /
  REGIME (J2; H16, R3-17, H9 = market timing vs a same-day control), TOO WEAK (informed buyers, filing milestones,
  sale-preparation paperwork earn ~ the stock's usual), TOO RARE. What survives explore + control so far: company-
  or analyst-driven events with a size condition (J5) or a retail-catalyst calendar (J6), and analyst clusters (J7, J8).
  Standing rule: a MEETS must beat a same-day control (and a same-stock control when a price condition is involved).

## Log
- 12:45 setup: the prompt names `swing-trader`; the session started in the `llm-trader` checkout (no data caches); work in
  `~/Documents/Code/Projects/swing-trader` (same GitHub repo, 13 GB of caches). Fetched 079aa21; tests 356 passed. N 760 (EV2).
  Peers told (llm-trader-9b, 198-eb). Memory note: a prior session ran `jump_runner explore` on FDA approvals (fdaapp)
  while building the runner (all fail); that was a runner smoke test, not part of this hunt, and counts toward nothing here.
- 12:50 probes, one request each: Alpaca news REST 427/975/1357 items on 3 sample days; Arctic Shift posts OK (100/page);
  Wikimedia pageviews OK; openFDA OK; USAspending OK; EDGAR submissions + XBRL frames OK. Started background downloads
  (`research/sim/jump_data.py`): news 2016-01..2026-09 (3 threads), Reddit subs in sequence, Wikipedia pageviews (6 threads).
- 13:05 reachability: defense.gov 403 (D3 falls back to news headlines); ClinicalTrials.gov v2 OK; Wayback CDX OK
  (Yahoo trending-tickers: 2,275 daily snapshots 2016-24, ~350/yr 2017-20); Arctic Shift subreddit metadata OK.
  Added idea **H24** (first appearance of a small cap on Yahoo's trending-tickers page, Wayback snapshot) before any
  outcome.
- 13:10 **H17** trade-count spike, quiet price: built (`jump_h17.py`, 9,571 events, 3,685 in select); explore running.
- 13:15 **D5** hot-word renames (`jump_d5.py`; EDGAR form.idx names at filing time, so delisted renamers are kept):
  131 renames, 91 with a ticker, 43 in select -> 10 trades. Explore (1 look), all 12 cells fail:
  `hold60 n 10 jump 20.0% vs base 10.7% (x1.9) mean net +44.3% ex-top3 -12.3% median -1.9% vs usual +51.2% P 0.10`
  (one +274%); `tp205 n 10 jump 10.0% vs 8.9% mean -4.2%`; `hold20 mean -11.0% median -11.7%`. **DEAD: TOO RARE +
  LOTTERY** (most hot renamers trade OTC or under $1; 2 tradable a year).
- 13:40 runner speed: `jump_runner._rets` (numpy) replaces the per-row Python loop in `trades()`; `_ret` stays the
  reference and `test_vectorized_returns_match_reference` checks all 12 cells on random bars; D5 explore re-run
  prints identical lines. H17 explore: 47 s instead of > 20 min. No gate, cost or window changed.
- 13:42 **H17** explore (1 look; the slow run was killed before printing): 3,685 events -> 2,233 trades (558/yr).
  `hold1 jump 1.4% vs base 0.5% (x3.1) mean net -1.0% median -1.2%`; `hold5 jump 6.4% vs 3.1% (x2.1) mean -1.2%`;
  `tp2020 jump 34.0% vs 25.2% (x1.4) mean -0.2% median -0.2% P 0.69`; `trail60 mean -1.2% vs usual +1.4%`;
  `hold60 mean -7.4%`. All 12 cells fail both tracks. **DEAD: new death TWO-WAY** — attention without a price move
  raises the jump rate 2-3x at 1-5 days, but it raises the drop rate too (worst −43% at 1 day): attention predicts
  size, not direction; the small-cap cost then makes the mean negative.
- 13:55 **D9** first Phase 3 posted on ClinicalTrials.gov by a small listed sponsor (`jump_d9.py`, 12,534 industry
  Phase 3 studies, exact sponsor-name match): 227 events, 150 select -> 111 trades. Explore (1 look), all fail:
  `hold5 jump 9.0% vs base 3.5% (x2.6) mean net +1.4% ex-top3 -0.6% median -0.8% P 0.18`; `trail60 mean +1.7% vs
  usual +3.9% ex-top3 -3.4% median -8.4%`; `hold1 x5.2 mean -0.6%`. **DEAD: LOTTERY** (the registry is a slow venue,
  and the 5-day lift is real, but 3 trades carry the mean).
- 14:20 **D4** first 8-K naming a hot theme (`jump_d4.py`; 14 themes, FTS 8-K by quarter 2014-26, 730-day "first",
  ADV$ < $20M): 2,690 events, 1,191 select -> 752 trades. Explore (1 look), all fail:
  `hold1 jump 0.8% vs 0.3% (x2.6) mean -0.9%`; `tp201 x3.5 mean -0.8%`; `hold20 mean +0.3% ex-top3 -1.3% median
  -1.3% vs usual +1.6% P 0.44` (one +646%); `trail60 mean -1.9%`. **DEAD: TWO-WAY + LOTTERY** (a theme word in an 8-K
  is not news the market pays for).
- 14:25 Wayback refused connections (archive.org rate limit) with 3 fetch threads for H24; stopped, deleted 55 failed
  (empty) snapshot files, fetcher now one request every ~4 s and skips failures. Retry later; a second failure drops H24.
- 14:30 `jump_news.py` written (h7 h8 h9 h10 h11 h12 h14 h21 h22 s1 s1v s2 s2v s3 s4 s5 w2 w5), smoke-tested on
  2016-01..2018-01 news (no outcomes). Pre-registered S variants (one allowed per idea, written before any run):
  S1/S3 primary = buy at the announcement if the date is >= 7 sessions later; S1v = fd 6 sessions before the date
  (hold5 ends the session before). S2 primary = fd 21 sessions before the PDUFA date (hold20 ends the session before);
  S2v = 6 sessions (hold5). Benzinga 2016-17 carries few PR-wire stories (S1: 20 conference stories in 2 years).
- 14:55 **D6** first profitable quarter (`jump_d6.py`): 726 events, 473 select -> 299 trades. Explore (1 look):
  `hold60 n 299 mean net +7.3% ex-top3 +4.5% median -0.6% vs usual +7.2% P 0.00 | ride MEETS`; `tp2060 mean +2.9%
  median +18.5%`; `hold20 mean +2.3% P 0.03`; `hold1 x3.4 mean -0.8%`. Diagnostics on select only (no rule change):
  ticker mapping 63% (2016) .. 92% (2025) = survivorship risk; year means +21/+14/-1/-8/+42/-5/-5/+14%.
- 15:00 Registered **Study J1** (RIDE hold60, N 760 -> 761, b555a07); peers told (llm-trader-ee; llm-trader-9b gone).
- 15:02 **J1 judge** (once): `hold60 n 48 (24/yr) jump 33.3% vs base 21.7% (x1.5) mean net +5.5% ex-top3 -1.8% median
  +3.3% vs stock's usual +3.7% hit 52% worst -81% best +142% P(mean<=0) 0.21` -> **RIDE VERDICT: DEAD**. k = 1.
  Write-up `study_jump_d6_first_profit.md`. LOTTERY (3 trades carry the mean) on too few trades.
- 15:20 survivorship fix before any Reddit/news outcome: `stock_symbols()` now keeps symbols Alpaca lists as OTC (names
  delisted to OTC keep their ticker); Reddit bare words use exchange symbols + OTC symbols of >= 4 letters; added
  SSB/LINE/RHPS and common words to STOP after a 20k-title extraction check (top: PLTR GME NOK TSLA SNDL NIO).
- 15:25 H24 data check: Yahoo trending-tickers snapshots 2016-17 load the list client-side (no tickers in the HTML);
  2019/2021 snapshots carry it (`/quote/XXX?p=`). Fetcher restarted at one request per ~4 s.
- 15:40 Reddit mentions (5 subs incl. WSB to 2018-06 so far; H1-H3 use the small subs only) -> **H1, H2, H3** explored
  (1 look each), all 12 cells fail:
  - **H1** first small-sub mention after a year (603 select events -> 374 trades): `hold1 jump 5.3% vs 0.5% (x10.7)
    mean net -0.7% ex-top3 -2.3% median -2.2%`; `tp205 x2.8 mean -1.5%`; `hold60 mean -9.6% median -15.8%`.
  - **H2** velocity without a move (524 -> 294): `hold1 x2.1 mean -1.3%`; `hold60 mean -7.1% median -17.9%`.
  - **H3** shortsqueeze DD (168 -> 112): `tp201 x4.3 mean -1.3%`; `hold20 mean -13.2%`; `hold60 mean -18.3%`.
  **DEAD: new death EXIT LIQUIDITY** — Reddit attention gives a 4-10x one-day jump rate, but the names then slide
  (−7..−18% over 60 sessions vs the stock's usual −0..−9%): a long-only buyer of crowd hype is the crowd's exit.
  Dodge: buyers who are informed or forced (insiders, options flow, contracts, index rules), not the crowd itself.
- 15:55 Reddit collisions, 1 look each, all fail (SI = FINRA, public settle + 12 days):
  - **C4** velocity + days-to-cover >= 5 (250 -> 188): `hold1 x9.1 mean -1.0%`; `hold5 x2.2 mean -0.3% ex-top3 -2.8%`;
    `hold60 mean -7.2% median -18.4%`.
  - **H18** first "squeeze" post + DTC >= 7 (193 -> 148): `tp201 x6.9 mean -0.1%`; `hold20 mean -6.0%`.
  - **C7** velocity within 60 days after a reverse split (55 -> 44): `hold1 x14.0 mean -6.4%`; `hold20 mean -22.1%
    median -35.3%`.
  - **C10** short position +50% + velocity (237 -> 146): `tp201 x6.1 mean -0.5%`; `hold5 mean -5.4%`.
  **DEAD: EXIT LIQUIDITY** (4 more; 7 of the last 10 ideas). Per section 6, the next 10 ideas are informed or forced
  buyers, not crowd attention: H11 option flow, D8/C6 insiders with no news, D2 un-gapped contracts, S2 PDUFA run-up,
  H10 initiations, D1 510(k), D11 predicted Russell adds, S5 forward splits, plus round-2 ideas.
- 15:58 checkpoint (12 explored): tests pass; sections 0-2 re-read; why-things-die line updated in STATE.
- 16:15 **R2-4** big own-money buy (>= $100k and >= 20% of ADV$, ADV$ < $5M; 2,552 select -> 1,568 trades), 1 look:
  `tp205 x1.9 mean -0.0%`; `tp2020 mean +0.4% P 0.13`; `hold60 mean +2.4% ex-top3 +1.7% median -1.0% vs usual +4.8%
  P 0.00` (< +3%). All fail. **Explored-dead: too weak** (own money is directional here, but < +3% at 60 and no lift).
- 16:20 **R2-5** insider buy after a 30% fall (3,483 -> 2,379), 1 look: `tp205 jump 15.1% vs 5.8% (x2.6) mean +0.5%
  ex-top3 +0.5% median +0.3% P 0.02 | jump MEETS`; RIDE MEETS at hold20 (+3.5%), tp2020 (+3.3%), hold60 (+8.7%),
  tp2060 (+5.5%). Diagnostics (select only, no rule change): 2020 = 681 of 2,379 trades; **control** (same stocks,
  falls without insider buys, 4,753) tp205 +0.93%, hold20 +4.8% = as good: the insider adds nothing (PRICE PROXY).
- 16:25 Registered **J2** (JUMP tp205 by the shortest-hold rule; N 761 -> 762, bbdac52; peer told), control stated.
- 16:27 **J2 judge** (once): `tp205 n 378 (189/yr) jump 9.5% vs base 7.2% (x1.3) mean net +0.5% ex-top3 +0.3% median
  -0.2% vs stock's usual +1.4% hit 49% worst -38% best +20% P(mean<=0) 0.18` -> **JUMP VERDICT: DEAD**. k = 2.
  Write-up `study_jump_r2_5_insider_after_fall.md`.
- 16:40 found the 3 WSB chunk downloads had never run (zsh did not split the year-range variable: "not enough values
  to unpack"); restarted with explicit arguments at 16:40. WSB-dependent ideas (H4, V1, H13) wait.
- 16:55 **R2-13** listing compliance regained (`jump_edgar.py`, FTS 8-K "regained compliance", 1,527 events; 831 select
  -> 337 trades, most others under $1), 1 look, all fail: `hold1 x3.4 mean -0.9%`; `tp205 x1.5 mean -1.6%`;
  `hold60 mean -7.9% median -16.1%`. **Explored-dead: the compliant names keep sliding** (distress, not relief).
- 17:25 **R2-17** insider buy into heavy shorts (DTC >= 5 published; 4,213 select -> 3,178 trades), 1 look, all fail:
  `tp205 jump 5.3% vs 3.9% (x1.3) mean +0.2% P 0.09`; `hold60 mean +1.5% ex-top3 +1.2% median -0.2% P 0.00` (< +3%);
  `tp2060 +1.3%`. **Explored-dead: too weak** (no squeeze lift; insiders in shorted names earn ~ the stock's usual).
- 17:25 news download cut to 2 threads at 17:05: at 3 threads Alpaca returned X-RateLimit-Remaining 0 and a 429; the
  production server may share the key, so ~2/3 of the limit is the ceiling.
- 17:40 **R2-2** going-concern doubt removed (`jump_edgar.py`; next 10-K without "substantial doubt"+"going concern"
  after one with; 1,028 select -> 673 trades), 1 look, all fail: `hold60 mean +2.0% ex-top3 +1.0% median +0.3% vs
  usual +2.5% P 0.06`; `tp2060 +1.7%`; `tp201 x2.6 mean -0.5%`. **Explored-dead: too weak** (< +3%, no jump lift).
- 18:10 **R2-20** 8-K Item 1.01 naming a big counterparty (FTS, 10 names, 82 events; 48 select -> 28 trades), 1 look,
  all fail: `hold1 x16.3 mean +0.1% ex-top3 -2.4%`; `hold20 mean -4.6%`; `hold60 -0.8% median -8.4%`. **Explored-dead:
  TOO RARE + LOTTERY.**
- 18:12 `jump_common.cik_sym()` (10,086 CIKs: EDGAR tickers + every historical filer name matched to Alpaca assets)
  and `shares_hist()` (XBRL dei cover-page shares, 169,945 rows, 7,299 symbols) for $-vs-market-cap rules (D2, C5,
  R2-25, C3), written before any of their outcomes.
- 18:12 news back to 3 threads for the weekend (production trades Mon-Fri; Friday 21:00 ET now); back to 2 by Sunday
  evening if still running.
- 18:30 data checks (no outcomes): Benzinga "Option Alert" headlines exist only 2016-2017 (1,821 / 582), so **H11/C8
  cannot be judged** (no 2024+ events) -> dropped as untestable, not explored. "to Present at" 2-8 stories a year
  -> S1/S1v **TOO RARE** before any run (Alpaca's Benzinga feed carries few PR-wire stories) -> dropped. **D7**
  (uplistings) untestable in the runner: a new listing has no 15 sessions of ADV before its first bar -> dropped.
  PDUFA 48-141/yr, strategic alternatives ~120/yr, upgrades ~4-5k/yr, dividend raises parsed 2,453 (2016-20).
- 18:45 **R2-15** share count shrinks 3-50% between cover counts (frames + accession filing dates, reverse splits
  excluded; 972 select -> 689 trades), 1 look, all fail: `hold60 mean +1.7% ex-top3 +1.2% median -0.2% vs usual
  +0.7% P 0.01`; `tp2060 +1.6%`; no jump lift (x0.7-1.2). **Explored-dead: too weak.**
- 19:40 new round-3 sources verified (1 request each): SEC fails-to-deliver files (page links; older months use
  different paths), Federal Register API (FDA notices; sponsors only in the full text), SEC 13F data sets (54 zips),
  cached Nasdaq earnings calendar (report dates, no announcement dates). A `pkill -f "jump_ftd fetch"` also killed
  a background shell whose command line contained that text (the R3-9 explore, before it printed); re-run, 1 look.
- 19:45 **R3-9** short interest down >= 50% with a flat price (`jump_ftd.py`; FINRA, published settle + 12 d;
  8,601 select -> 6,595 trades), 1 look, all fail: `hold1 hit 17% mean -0.9% median -0.8%`; `hold60 mean -1.1%`;
  `tp2060 -0.6%`. **Explored-dead** (mostly illiquid names that don't move; cost = the loss).
- 19:55 **R3-5** earnings reported >= 7 days earlier than the same quarter a year before (`jump_r3_5.py`; fd 2
  sessions before the report; 3,554 select (2020-10..2023) -> 2,569 trades), 1 look, all fail: `hold5 jump 5.7% vs
  2.3% (x2.5) mean +0.0% median -0.4%`; `tp205 x2.1 mean -0.0%`; `hold60 mean -1.4%`. **Explored-dead: TWO-WAY**
  (early reporters move more through the release, both ways).
- 20:15 three more, 1 look each, all 12 cells fail:
  - **R2-1** first executed buyback (`jump_xbrl.py`; companyfacts original filings; 527 select -> 342):
    `hold60 mean +0.4% vs usual -0.8%`; `tp2060 +0.5% median +2.9% P 0.31`; no lift. **Explored-dead: too weak.**
  - **R3-2** fails-to-deliver >= 0.5% of shares (`jump_ftd.py`; public file end + 20 d; 3,998 -> 2,671):
    `hold1 x1.7 mean -0.7%`; `tp2060 +0.6% P 0.13`; `hold60 median -5.3%`. **Explored-dead** (no squeeze lift).
  - **R3-16** fails back under 0.05% after a spike (1,918 -> 1,241): `tp2020 mean +0.8% P 0.06`; `tp2060 +1.2% P 0.05`;
    `hold60 +1.6% ex-top3 -0.1%`. **Explored-dead: too weak.**
- 20:35 **R3-4** dropped before any build: PatentsView bulk files return 403 (source broken).
- 20:40 **R3-3** FDA advisory-committee run-up (`jump_r3_3.py`; Federal Register full texts, "sponsored by",
  fd 6 sessions before the meeting; 58 events, 53 select -> 35 trades), 1 look, all fail: `hold5 jump 5.7% vs 1.4%
  (x4.1) mean -5.7% median -1.2% worst -71%`; `hold60 +0.6%`. **Explored-dead: TOO RARE + GAP** (FDA posts briefing
  documents ~2 business days before the meeting, inside the run-up window).
- 21:30 Wikipedia ideas (`jump_wiki.py`; 3,511 articles), 1 look each:
  - **H5** spike without a move (1,585 -> 1,380): `hold60 mean +1.9% vs usual -0.6%`; `hold20 +0.7% P 0.04`. Dead.
  - **H6** slow build (251 -> 223): `hold60 +1.2% P 0.17`; no lift. Dead.
  - **H15** article born (222 -> 106): `hold60 mean -5.0%`. Dead.
  - **C1** spike + insider buy (38 -> 33): `hold60 +6.9% ex-top3 -0.8% P 0.12`. Dead (too rare, lottery).
  - **H16** weekend spike, Monday open (656 -> 377): `hold60 n 377 jump 20.4% vs base 14.9% (x1.4) mean net +5.4%
    ex-top3 +4.2% median +3.5% vs stock's usual +2.9% hit 57% P(mean<=0) 0.00 | ride MEETS`.
  - **R3-17** 2-year-high views within 30 d after an insider buy (119 -> 90): `hold60 n 90 mean net +6.5% ex-top3
    +2.3% median +3.4% vs stock's usual +4.0% P 0.02 | ride MEETS`.
- 21:40 select-only diagnostics for the two MEETS (no rule change): by year H16 +8/+9/0/+9/+12/-5/+5/0%; vs IWM over
  the same 60 sessions +1.2% (median -0.1%); **same-day control** (600 random Wikipedia-universe stocks bought on the
  same entry mornings, 60,915 trades): control +3.3%, **event minus control +0.4% (median -0.5%, 49% above,
  bootstrap P 0.39)**. R3-17: event minus same-day control **-0.3% (P 0.56)**. Both "excesses" are market timing
  (attention spikes cluster at sell-offs such as March 2020; anything bought those mornings rebounded).
  **Not registered**: the RIDE judge gate (mean > 0, beats the stock's usual) would likely pass a pure timing artifact
  in 2024-26 (April 2025 crash -> rebound), i.e. a fluke dressed up as FOUND. Logged as explored-dead (REGIME).
  **Standing rule from here (tightening only, FOUND unchanged):** a MEETS is registered only if, on the select half,
  it beats a same-day control (event minus same-entry-day control, bootstrap P < 0.10) and, for event types with a
  price condition, a same-stock no-event control. J2 was registered before this rule (and died).
- 22:10 round-4 8-K footprints (`jump_edgar.py`, FTS, first per company in 365 d, ADV$ < $20M), 1 look each, all fail:
  - **R4-1** change-in-control severance (245 -> 190): `hold60 -0.1%`; no lift (x0.8-1.0). Dead.
  - **R4-2** retention bonus + change in control (513 -> 335): `hold60 -2.7%`. Dead.
  - **R4-3** poison pill, Item 3.03 (597 -> 365): `hold1 x7.1 mean -1.1% worst -100%`; `tp201 x8.4 mean -0.8%`;
    `tp2060 median +12.3% mean -0.0%`. **TWO-WAY** (pills come with distress as often as with bids).
  - **R4-4** special committee + proposal (142 -> 97): `tp205 x2.3 mean +0.1%`; `hold60 +2.2% ex-top3 -1.3%`. Dead.
  **Sale-preparation paperwork carries no takeover premium for a buyer at the next open.**
- 22:10 `jump_control.py` committed: the standing rule's same-day control (idea's own stocks, same entry mornings).
- 22:40 **R4-5** strategic alternatives + financial advisor (519 events; 303 select -> 155): `hold20 mean +3.5% ex-top3
  +1.1% P 0.04 | ride MEETS` (also trail20, hold60 +7.3%, trail60). **R4-6** + confidentiality agreements (92; 50 ->
  24): `hold20 jump 20.8% vs 8.0% (x2.6) mean +6.0% ex-top3 +1.7% P 0.04 | jump MEETS | ride MEETS`. Standing-rule
  control (`jump_control.py`): R4-5 event minus same-day control +4.4% (P 0.004), R4-6 +4.9% (P 0.057) -> both pass.
- 22:45 Registered **J3** (R4-5, RIDE hold20) and **J4** (R4-6, JUMP hold20), N 762 -> 764 (04a1c85); peer told.
- 22:47 **J3 judge**: `hold20 n 54 (27/yr) jump 9.3% vs base 8.1% (x1.1) mean net -1.7% ex-top3 -6.3% median -2.5%
  vs stock's usual +1.7% hit 33% worst -40% best +106% P(mean<=0) 0.71` -> **RIDE VERDICT: DEAD**.
  **J4 judge**: `hold20 n 7 (4/yr) jump 0.0% vs base 4.5% (x0.0) mean net -4.9% ex-top3 -9.2% median -0.7% vs stock's
  usual -3.0% hit 29% P(mean<=0) 0.96` -> **JUMP VERDICT: DEAD**. k = 4. Write-up `study_jump_r4_strategic_alternatives.md`.
- 23:50 batch (1 look each unless noted; summary = cell x(jump lift) mean/ex-top3/median P):
  - **R3-8** (178 select -> 137 trades); hold1 x0.0 -2.8%/-3.1%/-2.2% P1.00; tp205 x0.4 -3.9%/-4.4%/-2.8% P1.00; hold20 x0.2 -7.0%/-7.7%/-6.3% P1.00; hold60 x0.9 -9.8%/-11.6%/-12.9% P1.00; tp2060 x0.7 -8.4%/-9.1%/-9.9% P1.00; all fail
  - **R3-10** (158 select -> 107 trades); hold1 x0.0 -0.4%/-0.7%/-0.7% P0.82; tp205 x1.8 -0.8%/-1.3%/-0.9% P0.82; hold20 x0.3 -2.7%/-3.9%/-1.4% P0.99; hold60 x0.7 -1.2%/-3.4%/-1.2% P0.72; tp2060 x0.7 -0.2%/-0.9%/-0.2% P0.55; all fail
  - **S2** (95 select -> 89 trades); hold1 x0.0 -0.2%/-0.5%/-0.3% P0.75; tp205 x2.1 +1.1%/+0.1%/+0.3% P0.18; hold20 x1.5 +2.9%/+0.0%/-0.2% P0.11; hold60 x0.8 -1.6%/-6.2%/-4.7% P0.66; tp2060 x1.0 +0.2%/-1.2%/+4.0% P0.45; all fail
  - **S2V** (100 select -> 93 trades); hold1 x11.7 -0.1%/-0.6%/-0.2% P0.60; tp205 x2.5 +0.1%/-0.6%/-1.2% P0.45; hold20 x1.1 -5.5%/-7.5%/-3.4% P0.99; hold60 x0.8 -3.2%/-6.3%/-3.9% P0.84; tp2060 x0.9 -2.5%/-3.4%/+0.3% P0.84; all fail
  - **D2** (871 select -> 588 trades); hold1 x2.3 -0.2%/-0.3%/-0.2% P0.89; tp205 x1.1 -0.3%/-0.4%/+0.1% P0.84; hold20 x0.9 -0.1%/-0.5%/+0.3% P0.60; hold60 x1.0 +2.4%/+0.3%/+0.6% P0.06; tp2060 x1.0 +1.0%/+0.8%/+3.9% P0.12; all fail
  R3-8 (Russell inclusion announced) is strongly NEGATIVE (-7% at 20 sessions, -10% at 60: sell the news after the run-up into the recon) - long-only can't use it. S2v is S2's pre-registered second look (fd 6 sessions before the PDUFA date). All dead.
- 00:30 news batch (archive through 2024-01; select events don't depend on later news), 1 look each; summary = cell x(lift) mean/ex-top3/median P:
  - **R2-7** (439 select -> 331 trades); hold1 x3.6 -0.6%/-0.9%/-0.4% P0.96; tp205 x1.3 -0.4%/-0.7%/-0.4% P0.82; hold20 x0.9 +0.3%/-0.5%/+0.0% P0.38; hold60 x1.0 +0.6%/-0.7%/-0.5% P0.34; tp2060 x0.9 -0.0%/-0.4%/+1.2% P0.51; all fail
  - **H10** (1213 select -> 820 trades); hold1 x2.1 -0.9%/-1.2%/-1.3% P1.00; tp205 x1.4 -1.0%/-1.1%/-1.5% P1.00; hold20 x1.2 -1.7%/-2.2%/-2.8% P0.99; hold60 x1.1 -2.5%/-4.0%/-5.0% P0.95; tp2060 x1.1 -1.9%/-2.1%/+3.0% P0.99; all fail
  - **H12** (121 select -> 104 trades); hold1 x0.0 -1.5%/-2.0%/-0.3% P0.99; tp205 x1.2 -2.5%/-3.2%/-1.0% P0.99; hold20 x0.7 -6.5%/-8.0%/-2.5% P1.00; hold60 x0.4 -10.1%/-14.2%/-9.8% P0.99; tp2060 x0.9 -1.6%/-2.5%/+8.3% P0.74; all fail
  - **H14** (1981 select -> 1370 trades); hold1 x7.0 -1.4%/-1.5%/-1.1% P1.00; tp205 x2.0 -1.3%/-1.3%/-1.2% P1.00; hold20 x1.1 -1.2%/-2.0%/-1.4% P0.95; hold60 x1.2 +0.8%/-0.1%/-1.6% P0.23; tp2060 x1.1 +0.6%/+0.3%/+5.8% P0.19; all fail
  - **H22** (47 select -> 31 trades); hold1 x0.0 -2.0%/-2.6%/-1.0% P1.00; tp205 x0.5 -3.2%/-5.4%/-3.2% P0.93; hold20 x0.3 -6.5%/-9.5%/-5.8% P0.99; hold60 x0.5 -10.8%/-14.8%/-13.3% P1.00; tp2060 x0.7 -7.0%/-10.1%/-9.3% P0.95; all fail
  - **S3** (6 select -> 3 trades); all fail
  - **S4** (670 select -> 449 trades); hold1 x4.2 -0.8%/-1.0%/-0.9% P0.99; tp205 x1.1 -1.9%/-2.1%/-1.5% P1.00; hold20 x0.9 -3.5%/-4.8%/-7.0% P0.99; hold60 x1.0 -2.6%/-4.2%/-10.4% P0.88; tp2060 x1.0 -2.1%/-2.9%/+18.5% P0.93; all fail
  - **W2** (267 select -> 143 trades); hold1 x5.4 -0.5%/-1.9%/-1.0% P0.72; tp205 x2.2 -1.4%/-2.0%/-1.8% P0.89; hold20 x1.1 -5.2%/-6.7%/-5.1% P1.00; hold60 x1.2 -2.8%/-7.2%/-4.0% P0.76; tp2060 x1.1 -2.2%/-3.9%/+6.9% P0.80; all fail
  - **W5** (50 select -> 39 trades); hold1 x9.0 -0.7%/-2.5%/-0.3% P0.67; tp205 x3.2 -1.6%/-3.8%/-1.1% P0.70; hold20 x0.4 -7.4%/-9.9%/-3.3% P0.99; hold60 x1.5 +9.2%/-10.1%/+1.0% P0.32; tp2060 x1.1 -4.5%/-7.0%/+2.6% P0.85; all fail
  - **R2-22** (69 select -> 49 trades); hold1 x0.0 -0.1%/-0.7%/-0.9% P0.58; tp205 x0.0 -1.0%/-1.8%/-0.9% P0.81; hold20 x0.0 -2.5%/-3.5%/-1.2% P0.94; hold60 x0.6 +0.9%/-1.1%/+1.3% P0.34; tp2060 x1.0 +2.1%/+0.9%/+1.4% P0.16; all fail
  - **R2-14** (6 select -> 4 trades); hold1 x0.0 -4.5%/-13.9%/-1.6% P1.00; tp205 x0.0 -0.4%/-12.2%/+0.3% P0.55; hold20 x3.6 +64.4%/-4.9%/+4.8% P0.13; hold60 x1.4 +59.3%/-27.7%/+7.9% P0.20; tp2060 x2.3 +14.2%/-1.5%/+19.2% P0.00; all fail
  - **R3-11** (20 select -> 13 trades); hold1 x0.0 -6.3%/-9.4%/-6.6% P1.00; tp205 x1.0 -8.8%/-16.6%/-9.1% P0.96; hold20 x0.9 -7.8%/-19.4%/-19.4% P0.84; hold60 x1.1 -1.6%/-39.2%/-31.5% P0.56; tp2060 x0.8 -16.2%/-27.0%/+2.3% P0.94; all fail
  - **R3-12** (5 select -> 2 trades); all fail
  - **R3-14** (19 select -> 16 trades); hold1 x12.7 -0.7%/-4.1%/-2.5% P0.62; tp205 x3.7 +7.5%/+4.1%/+9.5% P0.01; hold20 x1.7 +8.2%/-13.9%/-10.0% P0.29; hold60 x1.7 +26.7%/-9.2%/-10.9% P0.15; tp2060 x1.3 +14.0%/+2.2%/+19.2% P0.07; all fail
  - **H7** (371 select -> 207 trades); hold1 x3.7 -2.0%/-2.3%/-1.3% P1.00; tp205 x1.9 -3.7%/-4.1%/-1.6% P1.00; hold20 x1.0 -5.9%/-7.9%/-3.0% P1.00; hold60 x1.0 -5.8%/-9.2%/-4.9% P0.97; tp2060 x1.0 -5.9%/-6.4%/-0.2% P1.00; all fail
  - **C3** (43 select -> 17 trades); hold1 x0.0 -4.9%/-6.7%/-2.1% P1.00; tp205 x1.4 -8.1%/-13.9%/-7.2% P0.97; hold20 x0.0 -13.5%/-19.0%/-9.7% P1.00; hold60 x0.9 -10.8%/-26.1%/-11.5% P0.83; tp2060 x1.0 -7.1%/-12.9%/+12.5% P0.80; all fail
  - **H23** (678 select -> 429 trades); hold1 x4.9 -0.2%/-0.5%/-0.3% P0.80; tp205 x2.2 +0.8%/-0.1%/-0.2% P0.17; hold20 x0.9 +0.8%/+0.1%/-0.1% P0.13; hold60 x1.0 +4.4%/+2.4%/+1.5% P0.00; tp2060 x1.0 +2.6%/+1.7%/+2.9% P0.01; all fail
  MEETS (logged in detail with their registrations): **R2-25** (J5), **S5** (J6), **R2-19** (J7), **R3-15** (J8); each beat the standing-rule same-day control. **R3-20** dropped (dropped-coverage headlines ~1 a year: too rare in this feed).
- 01:00 rebuild check (`jump_rebuild.py`): J5-J8 event files rebuilt on the archive through 2024-03 hash-MATCH their
  registered select-half pins (r2_25 ee4fb4de291419c5, s5 8490e20097b8a31f, r2_19 0715cbe8f4bb7105, r3_15
  95c3dafbbf6fdeb6): the rules use only past news, so the judge files can be built when the archive reaches 2025-07.
- 01:05 **H9** first "why is X trading higher" explainer (1,141 select trades): `hold60 mean +6.1% ex-top3 +4.7%
  median +0.1% vs usual +5.6% P 0.00 | ride MEETS` (also trail60). Standing-rule controls: same-day control 156,104
  trades: **event minus control -1.0% (median -5.4%, 40% above, P 0.75) -> FAILS**; same stocks on same-size up days
  without an explainer: +4.7% (median -5.2%). Year means: 2020 +29%, 2021-23 -4..-8%: market timing (the 2020
  rebound). **Not registered; explored-dead (REGIME + price-first).**
