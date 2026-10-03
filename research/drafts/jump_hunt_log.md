# Jump & ride hunt log (prompt_jump_hunt.md), session llm-trader-51

## STATE (final, 2026-10-02 19:55 PDT): STOPPED by rule 3 — NOT FOUND
- program N used by this hunt: 761-768 (J1-J8; peers have since registered up to 778). k = 8, all DEAD on the judge
  half; no confirm window reached. Ideas explored: 97 of 122 written in 4 rounds (+ S2v as S2's second look).
- Summary, the full idea table and near misses are at the end of this log ("STOP" section).
- Data built and cached for reuse (data/research/jump/): Alpaca/Benzinga news 2016-01..2025-09 (downloader stopped;
  2025-10..2026-09 not fetched), Reddit posts for 8 subs incl. full WSB 2016-2026, Wikipedia pageviews for 3,511 company
  and 692 CEO articles, Yahoo trending snapshots 2018-24, SEC FTD 2015-26, SEC 13F 2013-26, Form 345 2014-26,
  XBRL shares history, openFDA 510(k), ClinicalTrials Phase 3, Federal Register adcom texts, 2,019 LLM extractions.

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
- 02:00 batch, 1 look each:
  - **H8** (4072 select -> 3072 trades); hold1 x5.4 -0.8%/-0.8%/-0.7% P1.00; tp205 x1.5 -0.8%/-0.8%/-0.7% P1.00; hold20 x0.9 -1.0%/-1.1%/-1.0% P1.00; hold60 x0.9 -0.4%/-0.6%/-1.5% P0.82; tp2060 x0.8 -1.0%/-1.1%/+0.3% P1.00; all fail
  - **H21** (817 select -> 370 trades); hold1 x7.7 -1.8%/-2.1%/-0.9% P1.00; tp205 x1.9 -1.9%/-2.1%/-1.1% P1.00; hold20 x0.7 -3.6%/-4.1%/-1.5% P1.00; hold60 x0.9 -5.2%/-5.5%/-2.4% P1.00; tp2060 x1.0 -2.2%/-2.4%/-0.9% P0.99; all fail
  - **D1** (218 select -> 180 trades); hold1 x0.0 -0.4%/-0.5%/-0.4% P0.99; tp205 x0.4 -0.7%/-1.0%/-0.2% P0.90; hold20 x1.1 -0.5%/-1.2%/-0.1% P0.71; hold60 x1.0 +1.0%/-0.5%/+1.0% P0.30; tp2060 x1.0 +1.2%/+0.7%/+2.4% P0.20; all fail
  - **D8** (982 select -> 673 trades); hold1 x3.1 -0.5%/-0.7%/-0.7% P1.00; tp205 x1.7 -0.2%/-0.3%/-0.5% P0.76; hold20 x1.4 -0.1%/-0.4%/+0.0% P0.59; hold60 x1.1 -0.2%/-1.0%/-0.4% P0.58; tp2060 x1.1 +0.6%/+0.5%/+1.8% P0.19; all fail
  - **C6** (6107 select -> 4431 trades); hold1 x2.2 -0.4%/-0.5%/-0.8% P1.00; tp205 x1.5 -0.4%/-0.5%/-0.6% P1.00; hold20 x1.3 -0.0%/-0.1%/-0.3% P0.51; hold60 x1.2 +0.8%/+0.6%/-0.3% P0.03; tp2060 x1.1 +0.6%/+0.6%/+2.1% P0.01; all fail
  - **C5** (218 select -> 109 trades); hold1 x0.0 -0.3%/-0.7%/-0.3% P0.80; tp205 x0.9 -1.4%/-2.0%/-1.1% P0.95; hold20 x1.1 -2.0%/-3.2%/-2.9% P0.92; hold60 x1.4 +6.4%/-0.5%/+1.2% P0.13; tp2060 x1.0 +0.8%/+0.1%/+6.2% P0.34; all fail
  - **R4-18** (26 select -> 16 trades); hold1 x0.0 +1.0%/-0.7%/+0.1% P0.16; tp205 x1.0 -0.1%/-3.4%/-1.7% P0.56; hold20 x1.6 +3.2%/-1.3%/+3.1% P0.16; hold60 x1.4 -1.3%/-9.0%/+4.0% P0.57; tp2060 x1.2 +2.8%/-1.2%/+13.7% P0.30; all fail
  - **R4-19** (297 select -> 216 trades); hold1 x5.3 -0.9%/-1.2%/-0.7% P0.99; tp205 x1.5 -0.4%/-0.7%/-0.8% P0.74; hold20 x0.9 +0.0%/-1.2%/-0.6% P0.50; hold60 x1.0 -1.0%/-2.7%/-1.7% P0.70; tp2060 x1.0 -0.3%/-0.6%/+3.7% P0.58; all fail
  All dead (D1 510(k) before the press release: +1.0% at 60, no lift; D8/C6 insider buys with no news: ~ the stock's usual; C5 big contract in a small float: +6.4% at 60 but ex-top3 -0.5%).
- 03:20 news archive complete through 2025-09; `jump_rebuild.py`: J5-J8 select-half hashes all **MATCH** the pins.
- 03:25 judges (once each), all **DEAD**: J5 `tp205 n 68 jump 8.8% vs base 1.8% (x4.8) mean net +0.8% ex-top3 -0.1%
  median +0.4% P 0.23`; J6 `trail20 n 28 (x1.8) mean +2.6% ex-top3 -1.1% median -0.1% P 0.16`; J7 `tp205 n 25 (x2.4)
  mean +1.0% ex-top3 -1.5% median +1.7% P 0.34`; J8 `0 trades` (headline format gone after 2020). k = 8.
  Write-up `study_jump_j5_j8_news_events.md`.
- 03:30 **R3-18** first 10-K naming a hot theme (1,066 select -> 684): `hold20 -3.0%`, `hold60 -5.3%`. Dead. 78 explored.
- 04:10 collisions on finished data (`jump_combo.py`), 1 look each:
  - **V2** (78 select -> 33 trades); hold1 x0.0 -0.1%/-1.1%/-0.7% P0.57; tp205 x2.4 +1.1%/-0.7%/+0.4% P0.27; hold20 x1.7 +4.5%/+1.3%/+4.4% P0.04; hold60 x1.1 -0.8%/-7.9%/-6.9% P0.57; tp2060 x1.4 +7.8%/+6.6%/+19.2% P0.01; MEETS: hold20 ride MEETS, tp2020 ride MEETS, trail20 ride MEETS, tp2060 ride MEETS
  - **C2** (345 select -> 222 trades); hold1 x4.1 -0.3%/-0.9%/-0.7% P0.67; tp205 x3.1 +0.1%/-0.4%/-0.1% P0.44; hold20 x1.8 +5.0%/+1.6%/-1.4% P0.03; hold60 x1.6 +14.7%/+10.0%/+2.7% P0.00; tp2060 x1.5 +5.7%/+5.3%/+19.2% P0.00; MEETS: hold20 ride MEETS, hold60 ride MEETS, tp2060 ride MEETS
  - **C11** (10 select -> 6 trades); hold1 x0.0 -4.1%/-7.5%/-2.4% P1.00; tp205 x0.0 -12.2%/-19.2%/-10.5% P1.00; hold20 x2.3 -3.9%/-16.2%/-5.8% P0.73; hold60 x1.4 -7.4%/-24.3%/-6.1% P0.80; tp2060 x0.9 -5.6%/-24.3%/-6.1% P0.72; all fail
  V2 and C2 MEET (RIDE hold20 the shortest) but **FAIL the standing-rule same-day control**: V2 event minus control +2.9% (median +0.7%, P 0.164; 2021 carries it, +13%); C2 +3.0% (median -2.2%, P 0.123; 2018 and 2020 carry it, 2021-23 negative). Not registered: meme-era timing. C11 too rare (6 trades). 81 explored.
- **Clock correction (real time 2026-10-02 16:25 PDT):** the HH:MM stamps on entries after ~13:10 in this log were
  written from a wrong mental clock, not read from the system (entries stamped 18:00-04:10 all happened between
  ~13:10 and 16:25 PDT on 2026-10-02). Order of entries is correct; times are not. The "Friday 21:00 ET" note on the
  3-thread news download was really ~18:10 ET, still after the US close (no production trading runs until Monday).
  From here, stamps come from `date`.
- 16:20 PDT **H19** theme Wikipedia spike -> theme small caps (`jump_more.py`; 14 theme pages, members = companies whose
  8-K/10-K named the theme in the prior 730 days; 1,051 select -> 628): `hold20 -1.5%`, `hold60 -2.5%`. Dead. 82 explored.
- 16:29 PDT batch, 1 look each:
  - **C9** (7066 select -> 4139 trades); hold1 x1.1 -0.8%/-0.8%/-0.9% P1.00; tp205 x1.0 -1.0%/-1.0%/-1.2% P1.00; hold20 x0.9 -3.9%/-4.1%/-2.8% P1.00; hold60 x1.1 -2.5%/-2.8%/-3.6% P1.00; tp2060 x1.0 -2.2%/-2.3%/+0.8% P1.00; all fail
  - **R4-10** (21 select -> 16 trades); hold1 x0.0 -0.4%/-2.3%/-1.0% P0.61; tp205 x3.9 +1.3%/-3.5%/-1.4% P0.33; hold20 x1.3 +0.6%/-4.5%/-1.1% P0.46; hold60 x1.0 +5.2%/-4.9%/+1.0% P0.23; tp2060 x1.3 +6.3%/+2.6%/+15.7% P0.06; all fail
  - **R4-13** (364 select -> 225 trades); hold1 x2.6 -0.8%/-1.1%/-0.8% P0.99; tp205 x2.2 +0.1%/-0.2%/-0.6% P0.44; hold20 x1.3 +2.2%/-2.1%/-1.9% P0.34; hold60 x1.0 -2.1%/-5.4%/-4.9% P0.79; tp2060 x1.1 -0.6%/-1.0%/+2.2% P0.67; all fail
  - **R4-17** (1 select -> 0 trades); all fail
  - **D10** (54 select -> 36 trades); hold1 x16.7 -0.7%/-1.7%/-1.0% P0.83; tp205 x1.2 -1.6%/-3.0%/-1.6% P0.89; hold20 x0.7 -4.4%/-7.7%/-3.2% P0.95; hold60 x0.8 -2.5%/-6.5%/+1.8% P0.73; tp2060 x1.2 +0.2%/-1.6%/+14.1% P0.47; all fail
  All dead (C9 theme news spike -> theme small caps loses 2-4%; R4-10, R4-17, D10 too rare). 87 explored. R3-7 (LLM extraction) restarted after a run where every call failed (no OpenCode key in this checkout's environment; the 2,020 cached failures were deleted, failures are no longer cached; the key is loaded from the llm-trader checkout's .env of the same repo); ~24 calls/min.
- 16:37 PDT **R3-13** new-CEO-era insider buys (1,324 select -> 881): `hold60 +1.9% ex-top3 +1.2% median -0.8% P 0.04`, `tp2060 +1.3%`; too weak. **R3-6** 13F discovery (21,088 select -> 8,451): every cell negative (`hold60 -2.5%`). Both dead; 89 explored. (An empty R3-7 event file left by the crashed run was 'explored' by the queue with 0 events: deleted, not a look.)
- 16:37 PDT:
  - **R2-24** (33 select -> 26 trades); hold1 x0.0 -0.7%/-1.5%/-0.8% P0.87; tp205 x0.0 -3.2%/-4.3%/-2.0% P1.00; hold20 x1.1 +0.4%/-3.3%/-1.1% P0.46; hold60 x1.2 +4.5%/-1.8%/+2.4% P0.17; tp2060 x0.8 +1.1%/-1.4%/+2.4% P0.36; all fail
  - **R4-7** (15 select -> 10 trades); hold1 x0.0 -2.3%/-3.6%/-2.1% P1.00; tp205 x0.0 -3.3%/-5.5%/-1.2% P0.99; hold20 x3.2 +12.2%/-0.2%/+4.5% P0.03; hold60 x1.5 +10.8%/-12.2%/-5.5% P0.23; tp2060 x1.7 +8.0%/+3.0%/+18.5% P0.09; all fail
  Both too rare (26 / 10 trades). 91 explored.
- 17:08 PDT:
  - **H20** (185 select -> 128 trades); hold1 x3.7 -1.3%/-2.0%/-1.0% P0.96; tp205 x1.5 -1.7%/-2.5%/-2.1% P0.90; hold20 x1.2 -3.7%/-7.5%/-6.7% P0.89; hold60 x1.0 -5.6%/-13.0%/-14.0% P0.83; tp2060 x1.0 -2.4%/-4.0%/+13.3% P0.82; all fail
  **H20** (a subreddit created for the ticker; Arctic Shift subreddit metadata for 1,610 tickers with >= 20 mentions): dead, EXIT LIQUIDITY (median -14% over 60 sessions). 92 explored.
- 18:16 PDT **R3-7** LLM fact extraction (OpenCode Go deepseek-v4-flash, 2,019 calls of the 3,000 budget, 1 timeout skipped; prompt holds only the 8-K text; value and counterparty validated verbatim): 2,021 small-cap 8-K Item 1.01 filings -> 239 sales contracts, 244 with a stated value, 41 valid, 29 events with value >= 25% of revenue:
  - **R3-7** (15 select -> 7 trades); hold1 x248.5 +12.4%/-0.3%/+3.0% P0.03; tp205 x2.4 +1.9%/-5.2%/-1.2% P0.32; hold20 x0.0 -2.5%/-13.3%/-6.0% P0.69; hold60 x1.7 +9.2%/-12.1%/+9.9% P0.20; tp2060 x1.6 +8.9%/+0.4%/+19.2% P0.09; all fail
  Dead: TOO RARE (7 select trades). 93 explored.
- 19:19 PDT WSB complete 2016-01..2026-09 (2021: 12 months; January alone 533k posts). Mentions rebuilt with full WSB; small-sub rows for 2016-2023 identical month by month to the table H1-H3/C4/H18/C7/C10 used (extra rows only in 2024+, where those subs were still downloading then). 1 look each:
  - **H4** (3110 select -> 2187 trades); hold1 x6.0 -1.2%/-1.4%/-1.0% P1.00; tp205 x2.3 -0.6%/-0.7%/-0.8% P0.97; hold20 x1.5 -0.9%/-1.2%/-1.5% P0.95; hold60 x1.2 +0.1%/-0.4%/-2.6% P0.46; tp2060 x1.2 +1.2%/+1.0%/+10.0% P0.01; all fail
  - **V1** (763 select -> 409 trades); hold1 x9.1 -1.6%/-2.7%/-3.1% P0.92; tp205 x2.5 -2.1%/-2.6%/-3.1% P0.98; hold20 x1.3 -6.9%/-8.9%/-12.6% P1.00; hold60 x1.3 -5.4%/-12.1%/-23.3% P0.86; tp2060 x1.3 +1.3%/+0.0%/+19.2% P0.23; all fail
  - **H13** (484 select -> 289 trades); hold1 x11.8 -1.5%/-3.4%/-2.8% P0.85; tp205 x2.9 -1.4%/-2.0%/-0.8% P0.90; hold20 x1.6 -4.6%/-7.2%/-8.6% P0.96; hold60 x1.2 -6.3%/-9.3%/-15.7% P0.97; tp2060 x1.2 -0.3%/-1.3%/+18.5% P0.57; all fail
  All dead: EXIT LIQUIDITY again (6-12x one-day jump rate; V1 small subs -> WSB median -23% over 60 sessions; H13 cross-sub spread median -16%). 96 explored.


## STOP (stop rule 3): 4 rounds, >= 80 explored, no feasible source left — **NOT FOUND**

Session llm-trader-51, 2026-10-02 (12:40-19:55 PDT), `prompt_jump_hunt.md`. Nothing met FOUND (explore gate + registration + judge
PASS + CONFIRMED). This is the honest result after 97 explored ideas (122 written in 4 rounds), 8 registered
and judged (k = 8, program N 761-768), and a same-day control rule added mid-hunt to stop market timing from being
registered.

**Judged (all DEAD on the judge half; no confirm window was ever reached):**
| study | idea | select (only look) | judge | why it died |
|---|---|---|---|---|
| J1 | first profitable quarter after >= 6 losses (RIDE hold60) | +7.3%, ex-top3 +4.5% | +5.5%, ex-top3 -1.8%, P 0.21 | lottery; select flattered by survivorship + 2016/2020 timing |
| J2 | insider buy after a 30% fall (JUMP tp205) | jump x2.6, +0.5% | x1.3, P 0.18 | the fall, not the insider (a no-insider control did as well) |
| J3 | 8-K strategic alternatives + financial advisor (RIDE hold20) | +3.5%, control +4.4% | -1.7%, P 0.71 | takeover tail did not repeat |
| J4 | 8-K strategic alternatives + NDAs (JUMP hold20) | +6.0% (24 trades) | 7 trades | too rare |
| J5 | buyback >= 15% of market cap, un-gapped (JUMP tp205) | +2.1%, x2.6, control +1.9% | x4.8, +0.8%, ex-top3 -0.1%, P 0.23 | closest miss: lottery on 68 trades |
| J6 | forward split announced (JUMP trail20) | +2.2%, control +2.0% | +2.6%, ex-top3 -1.1%, P 0.16 | lottery, 28 trades |
| J7 | two upgrades in 10 days, small caps (JUMP tp205) | +0.7%, control +1.0% | +1.0%, ex-top3 -1.5%, P 0.34 | lottery, 25 trades |
| J8 | initiation with a 2x target, micro caps (RIDE hold60) | +6.1%, control +5.0% | 0 trades | the headline format vanished after 2020 |

**Met the explore gate but failed the same-day control (not registered):** H16 weekend Wikipedia spike, R3-17
pageview high + insider buy, H9 "why is X trading higher" explainers, V2 Reddit-before-Benzinga, C2 first Reddit
mention + insider buy: each equal to stocks bought on the same mornings (market timing: 2020 and 2021 rebounds).

**Why things die here (the death map, updated):**
- EXIT LIQUIDITY (new): crowd attention (Reddit, subreddits, PR blitzes, explainers) gives a 4-14x one-day jump rate,
  then the names slide 5-22% over 20-60 sessions; a long-only buyer is the crowd's exit.
- TWO-WAY (new): attention without direction (trade-count spikes, theme 8-Ks, poison pills, early earnings dates) raises
  the up AND down jump rates; costs make the mean negative.
- LOTTERY: every judged idea died with its out-of-sample mean carried by its top three trades or with too few trades.
- REGIME / timing: 60-day rides on attention signals are market timing unless they beat a same-day control.
- TOO WEAK: own-money and filing milestones (buybacks executed, going-concern removal, share shrink, first profit,
  insider buys into shorts) earn about the stock's usual +1-2% over 60 sessions — real but below the +3% RIDE bar.

**Money:** nothing to deploy. If J5 had been real at its judge-half +0.8%/trade, 34 signals a year at 10% per signal
would be ~+$60 / $270 / $680 a year at $2.3k / $10k / $25k before tax — too small to matter even if it were real.

**Not tested (listed with the reason):** H11/C8 (option-alert headlines end in 2017), S1 (rare in this feed), D7
(runner needs ADV before a new listing), R3-4 (PatentsView 403), R3-20 (rare); not built because the data is
unavailable or very heavy, or the prior is very low: D3 (defense.gov 403; D2 covered contracts), D11 (no Russell
membership history), V3 (customer links need XBRL dimensions), V4 (no Korean/Japanese theme data), V5, W1, W3, W4,
W6, R2-3, R2-9 (STOCK Act data not fetched), R2-16, R2-18, R2-21, R2-23, R3-1, R3-19, R4-9, R4-20.
WSB-based H4, V1, H13 ran once WSB 2021 finished downloading (all EXIT LIQUIDITY); H24 ran on 2,193 Wayback snapshots (EXIT LIQUIDITY); R3-7 used 2,019 of the 3,000 LLM calls (too rare).

**What would change the answer:** a source that gives DIRECTION before the crowd (e.g. order-flow imbalance, borrow
fees, options open interest) — all paid here; or forward-only LLM judgment on post-cutoff events (prompt 3b/3c), which
needs months of shadow logging, not history.

### Every idea (prompt section 8 table; best select cell = highest mean net, as mean / ex-top3 / median, P(mean<=0))

| idea | track | method | death dodged | signals/yr | best select cell (mean/ex-top3/median) | judged? | verdict | confirm |
|---|---|---|---|---|---|---|---|---|
| H1 Reddit first mention after silence: a ticker named in >= 2 posts withi | R | H | GAP: Reddit precedes the press; PRICE PROXY: each stock vs i | 200+ | hold1 n374 -0.7%/-2.3%/-2.2% P0.75 | no | explored-dead |  |
| H2 Mention velocity without a price move: posts naming a ticker on day d  | R | H | GAP (attention before price), RIDE not price-first | 100+ | tp201 n294 -1.2%/-1.4%/-1.5% P1.00 | no | explored-dead |  |
| H3 Shortsqueeze-sub DD: first r/Shortsqueeze or r/shortsqueeze post with  | R | H | GAP; LOTTERY tested by ex-top-3 | 50-150 | tp201 n112 -1.3%/-1.9%/-1.8% P0.92 | no | explored-dead |  |
| H4 WSB first mention of a small cap (ADV$ < $20M at the time): first WSB  | R | H | GAP; PRICE PROXY | 100+ | tp2060 n2187 +1.2%/+1.0%/+10.0% P0.01 | no | explored-dead |  |
| H5 Pageview spike, no price move: Wikipedia views >= 5x the trailing-60d  | R | H | GAP (attention before price), PRICE PROXY (vs itself) | 100+ | hold60 n1380 +1.9%/+1.4%/+1.4% P0.00 | no | explored-dead |  |
| H6 Pageview slow build: 20-day mean views >= 2x the prior 120-day mean, m | R | H | REGIME (not a theme bet), RIDE not price-first | 30-80 | hold60 n223 +1.2%/+0.4%/+1.7% P0.17 | no | explored-dead |  |
| H7 First Benzinga coverage: a ticker's first-ever news story in the archi | R | H | GAP: test both buy-open and only-if-gap-small; TEXTBOOK (no  | 50-200 | tp201 n207 -1.7%/-2.0%/-1.3% P1.00 | no | explored-dead |  |
| H8 News velocity burst without a move: >= 4 stories in 5 days vs < 1/mont | R | H | GAP; PRICE PROXY | 100+ | hold60 n3072 -0.4%/-0.6%/-1.5% P0.82 | no | explored-dead |  |
| H9 "Why is X trading higher" first explainer: Benzinga's first "why is .. | R | H | TEXTBOOK; risk PRICE-FIRST (named; graded anyway as a wildca | 200+ | hold60 n1141 +6.1%/+4.7%/+0.1% P0.00 MEETS | no | MEETS; failed the same-day control |  |
| H10 First-ever analyst initiation on a micro cap ("initiates coverage" hea | R | H | TEXTBOOK (initiation drift is published on larger caps; micr | 100+ | hold1 n820 -0.9%/-1.2%/-1.3% P1.00 | no | explored-dead |  |
| H11 Unusual options activity headlines on small caps (Benzinga "unusual op | J | H | GAP (headline is intraday; buy next open); LOTTERY (many eve | 100+ |  | no | not explored (data / rarity: see log) |  |
| H12 "Short squeeze" in a headline, first time for a ticker | J | H | LOTTERY (ex-top3); GAP | 50-150 | trail60 n104 +1.7%/-3.7%/-6.5% P0.39 | no | explored-dead |  |
| H13 Cross-sub spread: ticker first named in one small sub, then within 10  | R | H/V | GAP; LOTTERY | 50-150 | tp2060 n289 -0.3%/-1.3%/+18.5% P0.57 | no | explored-dead |  |
| H14 PR blitz by a micro cap: >= 4 press releases (Benzinga wires: Globe/PR | R | H | GAP; LOTTERY (trail exits) | 50-150 | hold60 n1370 +0.8%/-0.1%/-1.6% P0.23 | no | explored-dead |  |
| H15 Wikipedia article born: first day with >= 50 views for a listed ticker | R | H | GAP | 20-50 | hold20 n106 -0.8%/-2.6%/+0.2% P0.66 | no | explored-dead |  |
| H16 Weekend pageview spike: Sat+Sun views >= 5x a normal weekend, bought M | J | H | GAP (named; tests it directly) | 50+ | hold60 n377 +5.4%/+4.2%/+3.5% P0.00 MEETS | no | MEETS; failed the same-day control |  |
| H17 Trade-count spike, quiet price: trade_count >= 5x its 60d median, abs  | R | H | PRICE PROXY (vs itself), RIDE attention-first; TEXTBOOK (the | 300+ | tp2020 n2233 -0.2%/-0.6%/-0.2% P0.69 | no | explored-dead |  |
| H18 Squeeze talk + short interest: Reddit posts naming a ticker with "sque | J | H/C | LOTTERY; GAP | 30-100 | tp201 n148 -0.1%/-0.5%/-0.7% P0.54 | no | explored-dead |  |
| H19 Wikipedia theme spike -> theme small caps: a theme article (Quantum co | R | H/V | REGIME (a family of 15 themes, any year); price-first banned | 20-60 | trail60 n628 -0.3%/-1.7%/-5.6% P0.63 | no | explored-dead |  |
| H20 Reddit mention by a new sub for the ticker: a subreddit named after th | R | H/W | GAP | 10-50 | trail5 n128 -1.2%/-2.5%/-2.7% P0.81 | no | explored-dead |  |
| H21 News count drought, then a non-earnings story: first story in >= 180 d | R | H | GAP | 100+ | tp201 n370 -1.3%/-1.5%/-0.8% P1.00 | no | explored-dead |  |
| H22 Big-name partnership headline on a micro cap: headline names NVIDIA /  | J | H | GAP: only when the next open gaps < 10% (the market under-re | 50-150 | hold1 n31 -2.0%/-2.6%/-1.0% P1.00 | no | explored-dead |  |
| H23 Pageview spike of the CEO's article (Wikidata P169 CEO -> pageviews),  | R | H/W | GAP | 10-30 | hold60 n429 +4.4%/+2.4%/+1.5% P0.00 | no | explored-dead |  |
| H24 First appearance on Yahoo Finance trending tickers (Wayback daily snap | R | H/V | GAP (the list itself is the venue; test it), PRICE PROXY | 50-150 | tp201 n2032 -1.5%/-1.5%/-1.4% P1.00 | no | explored-dead |  |
| D1 FDA approvals died of GAP + LOTTERY -> 510(k) clearances in openFDA be | J | D | GAP (earlier than news), LOTTERY (many clearances) | 50+ | tp2060 n180 +1.2%/+0.7%/+2.4% P0.20 | no | explored-dead |  |
| D2 Announcement-gap drift (Lab-BH) died of GAP -> material-contract stori | R | D | GAP (only un-gapped), COST (big moves) | 50-150 | hold60 n588 +2.4%/+0.3%/+0.6% P0.06 | no | explored-dead |  |
| D3 8-K phrase drift died -> slow databases: defense.gov daily contract an | J | D | GAP (a slow venue), TEXTBOOK | 20-60 |  | no | not explored (data / rarity: see log) |  |
| D4 Theme momentum died of REGIME/price-first -> theme pivot by filing tex | R | D | REGIME (family across themes and years), price-first (filing | 50-200 | hold20 n752 +0.3%/-1.3%/-1.3% P0.44 | no | explored-dead |  |
| D5 Spin-offs / index adds died of GAP -> corporate name change to a hot w | R | D/W | GAP (EDGAR effective date vs press), LOTTERY | 20-60 | hold60 n10 +44.3%/-12.3%/-1.9% P0.10 | no | explored-dead |  |
| D6 Earnings drift (TEXTBOOK) -> first profitable quarter ever (XBRL NetIn | R | D | TEXTBOOK (milestone, not surprise) | 50-150 | hold60 n299 +7.3%/+4.5%/-0.6% P0.00 MEETS | yes (J1, RIDE hold60) | DEAD (+5.5%, ex-top3 -1.8%, P 0.21) | not run |
| D7 Uplisting (banned) died of concurrent offerings -> uplistings with NO  | R | D | the death (dilution), LOTTERY | 20-50 |  | no | not explored (data / rarity: see log) |  |
| D8 First insider buys (EV2, a 1-day effect) -> RIDE version on micro caps | R | D/C | REGIME (L19 20d drift was 2020-only): only the uncovered sub | 50-150 | tp2060 n673 +0.6%/+0.5%/+1.8% P0.19 | no | explored-dead |  |
| D9 Breakthrough/topline died -> ClinicalTrials.gov first posting of a piv | R | D | GAP (slow registry), LOTTERY | 30-60 | hold60 n111 +1.9%/-3.0%/-7.2% P0.32 | no | explored-dead |  |
| D10 13D originals died of GAP -> activist 13D/A that raises the stake (ame | R | D | GAP (amendments get little attention) | 50-100 | tp2060 n36 +0.2%/-1.6%/+14.1% P0.47 | no | explored-dead |  |
| D11 Index adds died of GAP -> predicted Russell 2000 adds (rank by XBRL sh | R | D | GAP (arithmetic before the list), REGIME (published, decayed | 100+ (once a year) |  | no | not explored (data / rarity: see log) |  |
| C1 Wikipedia spike + insider buy within 10 days | R | C | each weak alone; PRICE PROXY | 10-30 | hold60 n33 +6.9%/-0.8%/+2.6% P0.12 | no | explored-dead |  |
| C2 First Reddit mention + an insider buy in the prior 30 days | R | C | GAP; LOTTERY | 10-40 | hold60 n222 +14.7%/+10.0%/+2.7% P0.00 MEETS | no | MEETS; failed the same-day control |  |
| C3 First news coverage + low float (shares outstanding < 10M, XBRL) | J | C | LOTTERY (median test) | 30-80 | hold1 n17 -4.9%/-6.7%/-2.1% P1.00 | no | explored-dead |  |
| C4 Reddit velocity + high days-to-cover (FINRA SI) | J | C | LOTTERY | 30-80 | trail5 n188 +0.4%/-2.5%/-2.5% P0.45 | no | explored-dead |  |
| C5 Contract $ >= 10% of mcap (D2) + float < 20M shares | J | C | GAP (un-gapped only) | 10-40 | hold60 n109 +6.4%/-0.5%/+1.2% P0.13 | no | explored-dead |  |
| C6 Insider buy + no news in 90 days | R | C | REGIME | 30-80 | hold60 n4431 +0.8%/+0.6%/-0.3% P0.03 | no | explored-dead |  |
| C7 Reddit mention spike within 60 days after a reverse split | J | C | LOTTERY; PRICE PROXY (vs itself) | 20-60 | tp201 n44 -1.8%/-3.3%/-0.6% P0.74 | no | explored-dead |  |
| C8 Unusual options headline (H11) + no other news that day | J | C | GAP | 30-80 |  | no | not explored (data / rarity: see log) |  |
| C9 Theme news spike (headline counts of a theme word >= 3x 90d) + a small | R | C/V | REGIME (family), price-first | 20-60 | hold1 n4139 -0.8%/-0.8%/-0.9% P1.00 | no | explored-dead |  |
| C10 Short interest up >= 50% in a FINRA period + Reddit/news attention spi | J | C | LOTTERY | 20-60 | tp201 n146 -0.5%/-0.9%/-2.8% P0.68 | no | explored-dead |  |
| C11 Trade-count spike (H17) + first news story in 90 days the same day | R | C | GAP | 30-100 | hold20 n6 -3.9%/-16.2%/-5.8% P0.73 | no | explored-dead |  |
| V1 Small subs -> WSB: >= 3 posts in the small subs within 5 days naming a | R | V | GAP | 50-150 | tp2060 n409 +1.3%/+0.0%/+19.2% P0.23 | no | explored-dead |  |
| V2 Reddit -> Benzinga: Reddit mention spike (H2 rule) with no Benzinga st | R | V | GAP | 50-150 | tp2060 n33 +7.8%/+6.6%/+19.2% P0.01 MEETS | no | MEETS; failed the same-day control |  |
| V3 Theme leader's big up day -> its small listed suppliers (XBRL Concentr | R | V | TEXTBOOK (Cohen-Frazzini customer momentum: monthly, large;  | 30-100 |  | no | not explored (data / rarity: see log) |  |
| V4 Korea/Japan retail theme stocks -> US peers (KOSDAQ theme leader +15%  | J | V | GAP (Asia trades first, a different venue) | 20-60 |  | no | not explored (data / rarity: see log) |  |
| V5 Benzinga premarket "movers" list of yesterday's after-hours: names tha | J | V | GAP | 100+ |  | no | not explored (data / rarity: see log) |  |
| S1 Conference run-up: micro/small caps announcing they will present at J. | R | S | GAP; LOTTERY | 100+ |  | no | not explored (data / rarity: see log) |  |
| S2 PDUFA run-up: buy 30 sessions before a PDUFA date (date extracted from | R | S | LOTTERY (exit before the binary) | 50-100 | hold20 n89 +2.9%/+0.0%/-0.2% P0.11 | no | explored-dead |  |
| S3 Investor/analyst day announced by a small cap: buy at announcement, se | R | S | GAP | 50+ | too few trades | no | explored-dead |  |
| S4 Medical-conference data presentations (ASCO/ASH/AACR/ESMO abstract pre | R | S | LOTTERY (exit before data) | 100+ | tp201 n449 -0.7%/-0.8%/-0.9% P0.99 | no | explored-dead |  |
| S5 Forward-split announcement -> run into the ex-date (Lab-BM tested AFTE | R | S | the dead study's window (after ex-date), GAP | 20-40 | trail20 n78 +2.2%/+0.8%/+2.6% P0.06 MEETS | yes (J6, JUMP trail20) | DEAD (+2.6%, ex-top3 -1.1%, P 0.16) | not run |
| W1 Ticker spells a hot word while that theme's news count spikes (e.g. AI | J | W | REGIME | 10-30 |  | no | not explored (data / rarity: see log) |  |
| W2 Press release that says "artificial intelligence"/"AI" >= 5 times, fir | R | W | REGIME (dates), GAP | 50-150 | trail60 n143 +3.1%/-0.3%/-6.9% P0.14 | no | explored-dead |  |
| W3 Wikipedia edit burst (>= 10 edits in a day on the company article vs < | R | W | GAP | 20-50 |  | no | not explored (data / rarity: see log) |  |
| W4 Super Bowl / big-event ad buyers that are small caps (announced in new | R | W | TOO RARE (named) | 2-5 |  | no | not explored (data / rarity: see log) |  |
| W5 "Meme stock" word in a headline for the first time for a ticker | J | W | GAP | 30-80 | hold60 n39 +9.2%/-10.1%/+1.0% P0.32 | no | explored-dead |  |
| W6 ARK Invest first buy of a small/mid cap (daily trade emails, archived) | R | W | REGIME (2020-21) | 20-50 |  | no | not explored (data / rarity: see log) |  |
| R2-1 First executed buyback: XBRL PaymentsForRepurchaseOfCommonStock > 0 (o | R | D | GAP + TEXTBOOK of buyback announcements (X3, Ikenberry): exe | 50-150 | tp2060 n342 +0.5%/+0.2%/+2.9% P0.31 | no | explored-dead |  |
| R2-2 Going-concern doubt removed: a 10-K without "substantial doubt" after  | R | D | LOTTERY (many events, survival is the bet), EXIT LIQ | 100+ | hold60 n673 +2.0%/+1.0%/+0.3% P0.06 | no | explored-dead |  |
| R2-3 Net cash above market cap: (cash + short-term investments − total liab | R | D/W | LOTTERY (a cash floor under the downside), EXIT LIQ (no crow | 50-200 |  | no | not explored (data / rarity: see log) |  |
| R2-4 Big own-money buy: an officer/director buys >= $100k in the open marke | R | C | EXIT LIQ; LOTTERY (many events) | 100+ | hold60 n1568 +2.4%/+1.7%/-1.0% P0.00 | no | explored-dead |  |
| R2-5 Insider buys after a 30% fall: officer/director buy when the stock is  | R | C | EXIT LIQ (the crowd already left); price is a filter, the Fo | 100+ | hold60 n2379 +8.7%/+8.4%/+5.2% P0.00 MEETS | yes (J2, JUMP tp205) | DEAD (x1.3, P 0.18) | not run |
| R2-7 Strategic-alternatives review announced (headline), RIDE: a sale proce | R | H/D | GAP (headline is mild), LOTTERY (many deals) | 30-80 | trail60 n331 +1.0%/-0.3%/-3.2% P0.21 | no | explored-dead |  |
| R2-9 Congress member buys a small cap (STOCK Act periodic transaction repor | R | W | EXIT LIQ | 20-50 |  | no | not explored (data / rarity: see log) |  |
| R2-13 Listing compliance regained (8-K / headline: "regained compliance" wit | R | D | EXIT LIQ (forced sellers done), GAP | 100+ | tp2060 n337 -0.2%/-1.4%/+18.5% P0.56 | no | explored-dead |  |
| R2-14 Emergence from Chapter 11 with new listed equity (headline) | R | D | LOTTERY, forced sellers | 10-30 | hold20 n4 +64.4%/-4.9%/+4.8% P0.13 | no | explored-dead |  |
| R2-15 Share count shrinks >= 3% in a quarter (dei cover-page shares, origina | R | D | TEXTBOOK (buyback announcements) -> execution; EXIT LIQ | 50-150 | hold60 n689 +1.7%/+1.2%/-0.2% P0.01 | no | explored-dead |  |
| R2-16 Revenue doubles year on year for the first time (XBRL Revenues, origin | R | D | TEXTBOOK (revenue drift: milestone, micro caps) | 50-150 |  | no | not explored (data / rarity: see log) |  |
| R2-17 Insider buy into heavy shorts: officer/director buy while the last pub | J | C | EXIT LIQ (no crowd buying); LOTTERY (many) | 50-150 | hold60 n3178 +1.5%/+1.2%/-0.2% P0.00 | no | explored-dead |  |
| R2-18 Double own money: an officer/director buy in a quarter in which the co | R | C | EXIT LIQ | 30-80 |  | no | not explored (data / rarity: see log) |  |
| R2-19 Two upgrades in 10 days on a small cap (headlines "Upgrades ... to Buy | R | H/D | TEXTBOOK (single upgrades) -> clusters on small caps | 50-150 | hold60 n277 +5.9%/+3.2%/+2.1% P0.00 MEETS | yes (J7, JUMP tp205) | DEAD (+1.0%, ex-top3 -1.5%, P 0.34) | not run |
| R2-20 Big-name counterparty in an 8-K exhibit (FTS 8-K "Amazon.com Services" | R | D | GAP (slow exhibit text) | 50-150 | hold1 n28 +0.1%/-2.4%/-1.2% P0.50 | no | explored-dead |  |
| R2-21 New major customer named in XBRL (ConcentrationRiskPercentage on a cus | R | D/W | GAP, EXIT LIQ | 30-80 |  | no | not explored (data / rarity: see log) |  |
| R2-22 Dividend raised >= 50% by a small cap (headline amounts) | R | D | TEXTBOOK (dividend initiation dead) -> big raises | 30-80 | tp2060 n49 +2.1%/+0.9%/+1.4% P0.16 | no | explored-dead |  |
| R2-23 Tiny-float de-SPAC: first session after a business combination closes  | J | W | LOTTERY (many 2021-23 deals) | 30-80 |  | no | not explored (data / rarity: see log) |  |
| R2-24 After an issuer's Dutch tender closes (SC TO-I final amendment): RIDE  | R | D | GAP (after, not at, the announcement) | 20-40 | hold60 n26 +4.5%/-1.8%/+2.4% P0.17 | no | explored-dead |  |
| R2-25 Buyback authorization >= 15% of market cap, un-gapped (headline $ amou | R | D | GAP (un-gapped only), TEXTBOOK | 30-80 | tp2060 n162 +3.6%/+3.3%/+6.7% P0.00 MEETS | yes (J5, JUMP tp205) | DEAD (x4.8, +0.8%, ex-top3 -0.1%, P 0.23) | not run |
| R3-1 First revenue ever: XBRL revenue > 0 in an original filing after >= 4  | R | D | TOO WEAK? milestone with a forced buyer (revenue screens) | 30-80 |  | no | not explored (data / rarity: see log) |  |
| R3-2 Fails-to-deliver spike: SEC FTD quantity >= 0.5% of shares outstanding | J | W | EXIT LIQ (forced buyers, not the crowd) | 100+ | tp2060 n2671 +0.6%/+0.3%/+7.5% P0.13 | no | explored-dead |  |
| R3-3 FDA advisory committee run-up: Federal Register notice of an adcom nam | R | S | LOTTERY (exit before the binary), GAP (notice weeks ahead) | 20-40 | hold60 n35 +0.6%/-8.5%/+1.1% P0.49 | no | explored-dead |  |
| R3-4 First patent ever granted to a listed micro-cap assignee (USPTO weekly | R | D | GAP (slow database), EXIT LIQ | 30-80 |  | no | not explored (data / rarity: see log) |  |
| R3-5 Earnings date moved earlier by >= 7 days vs the same quarter last year | J | D | TEXTBOOK (published, but not on small caps with a daily cale | 100+ | hold5 n2569 +0.0%/-0.1%/-0.4% P0.45 | no | explored-dead |  |
| R3-6 13F discovery: >= 3 different 13F filers open a new position in the sa | R | D | EXIT LIQ (institutions, not retail); TEXTBOOK (herding paper | 50-150 | trail60 n8451 -1.0%/-1.2%/-1.8% P1.00 | no | explored-dead |  |
| R3-7 LLM-extracted big contract vs revenue: 8-K Item 1.01 exhibit -> counte | R | D | GAP (slow text), TOO WEAK (big relative size only) | 30-80 | hold1 n7 +12.4%/-0.3%/+3.0% P0.03 | no | explored-dead |  |
| R3-8 Russell inclusion announced by the company (8-K/PR "set to join the Ru | R | S | REGIME (published effect; small adds only) | 100+ | tp201 n137 -2.7%/-3.1%/-2.2% P1.00 | no | explored-dead |  |
| R3-9 Short interest collapses >= 50% in one FINRA period with the price fla | R | D | PRICE PROXY (vs itself), EXIT LIQ | 100+ | tp2060 n6595 -0.6%/-0.8%/-0.7% P0.99 | no | explored-dead |  |
| R3-10 Unsolicited non-binding proposal made public (FTS 8-K/SC 13D "non-bind | R | D | GAP at the announcement (RIDE after it), LOTTERY | 30-80 | tp201 n107 +0.1%/-0.4%/-0.6% P0.38 | no | explored-dead |  |
| R3-11 Treasury in bitcoin announced by a small cap (headline "adds/purchases | J | W | REGIME (two waves), EXIT LIQ risk named | 20-60 | hold60 n13 -1.6%/-39.2%/-31.5% P0.56 | no | explored-dead |  |
| R3-12 Special dividend >= 10% of price announced (headline amount vs price), | R | D | GAP (un-gapped), TOO WEAK | 20-50 | too few trades | no | explored-dead |  |
| R3-13 New CEO buys stock in the first 90 days (8-K Item 5.02 new CEO + their | R | C | TOO WEAK (own money alone earns ~usual) -> only new-CEO buys | 30-80 | hold60 n881 +1.9%/+1.2%/-0.8% P0.04 | no | explored-dead |  |
| R3-14 Price target raised >= 50% in one note on a small cap ("Raises PT from | R | H/D | TEXTBOOK (revisions) -> only huge revisions on small caps | 100+ | hold60 n16 +26.7%/-9.2%/-10.9% P0.15 | no | explored-dead |  |
| R3-15 Initiation with >= 100% upside to the target on a micro cap | R | H | EXIT LIQ (institutional), TEXTBOOK | 100+ | hold60 n140 +6.1%/+2.7%/+1.0% P0.05 MEETS | yes (J8, RIDE hold60) | DEAD (0 trades) | not run |
| R3-16 Fails-to-deliver collapse after a spike (FTD back under 0.05% of share | R | W | PRICE PROXY | 50+ | hold60 n1241 +1.6%/-0.1%/-3.0% P0.15 | no | explored-dead |  |
| R3-17 Two-year high in Wikipedia views AND an insider buy within 30 days | R | C | EXIT LIQ (only with own money) | 10-30 | hold60 n90 +6.5%/+2.3%/+3.4% P0.02 MEETS | no | MEETS; failed the same-day control |  |
| R3-18 First 10-K risk factor naming a hot theme by a micro cap (FTS 10-K, no | R | D | TWO-WAY (D4 died) -> quieter venue | 50-150 | hold1 n684 -0.9%/-1.1%/-1.0% P1.00 | no | explored-dead |  |
| R3-19 LLM-extracted "first commercial sale / first order" in a 10-Q MD&A of  | R | D | GAP, EXIT LIQ | 30-80 |  | no | not explored (data / rarity: see log) |  |
| R3-20 Analyst coverage dropped by the last broker (headline "Discontinues/Su | R | C | EXIT LIQ, TOO WEAK | 10-30 |  | no | not explored (data / rarity: see log) |  |
| R4-1 Change-in-control severance plan adopted (8-K Item 5.02 "change in con | J | D | GAP (a quiet 5.02 filing), TWO-WAY (sale = up only) | 50-150 | trail60 n190 +0.3%/-1.3%/-6.0% P0.46 | no | explored-dead |  |
| R4-2 Retention bonus / retention plan adopted (8-K "retention bonus" OR "re | J | D | as R4-1 | 30-100 | tp2020 n335 -0.6%/-1.0%/-0.5% P0.80 | no | explored-dead |  |
| R4-3 Poison pill adopted (8-K Item 3.03 "rights agreement" + "adopted"), sm | J | D | GAP (the pill is not a bid), LOTTERY (many) | 30-80 | trail60 n365 +1.2%/-0.5%/-6.8% P0.25 | no | explored-dead |  |
| R4-4 Special committee of independent directors formed to evaluate a propos | J | D | GAP (the proposal may already be public: test) | 20-60 | trail60 n97 +2.5%/+0.1%/-0.5% P0.12 | no | explored-dead |  |
| R4-5 Financial advisor engaged to evaluate "strategic alternatives" in an 8 | J | D | GAP (8-K vs headline) | 50-150 | trail60 n155 +7.4%/+4.1%/-2.2% P0.00 MEETS | yes (J3, RIDE hold20) | DEAD (-1.7%, P 0.71) | not run |
| R4-6 Confidentiality / standstill agreements signed ("entered into confiden | J | D | GAP | 10-40 | hold20 n24 +6.0%/+1.7%/+3.5% P0.04 MEETS | yes (J4, JUMP hold20) | DEAD (7 trades) | not run |
| R4-7 Bylaw amendment: exclusive forum / advance notice right after a 13D (a | J | C | EXIT LIQ | 20-60 | trail60 n10 +16.0%/-4.2%/+0.9% P0.09 | no | explored-dead |  |
| R4-8 Large holder files 13D after holding a 13G (13G -> 13D switch: passive | J | D | GAP of fresh 13Ds (A1 died): this is a known holder switchin | 50-150 | hold60 n1446 +0.6%/+0.0%/-1.6% P0.25 | no | explored-dead |  |
| R4-9 Corporate (non-fund) filer takes a 5%+ stake (13D/13G filer is an oper | J | D | GAP | 20-60 |  | no | not explored (data / rarity: see log) |  |
| R4-10 Insider sells nothing for 12 months, then 3+ insiders buy in one windo | J | C | TOO WEAK alone (EV), combined | 10-30 | tp2060 n16 +6.3%/+2.6%/+15.7% P0.06 | no | explored-dead |  |
| R4-11 Debt covenant waiver / forbearance ends with a refinancing (8-K "forbe | R | D | EXIT LIQ | 20-60 | tp2020 n258 +0.4%/-0.2%/-0.8% P0.35 | no | explored-dead |  |
| R4-12 Auditor change to a Big-4 firm from a small auditor (8-K Item 4.01, ne | R | D | TOO WEAK? informed party | 30-80 | hold60 n54 +2.9%/-1.2%/-0.6% P0.20 | no | explored-dead |  |
| R4-13 CFO hired from a big company (8-K 5.02 text "previously served as ...  | R | D | TOO WEAK | 30-80 | hold20 n225 +2.2%/-2.1%/-1.9% P0.34 | no | explored-dead |  |
| R4-14 Nasdaq/NYSE transfer of listing from NYSE American / Nasdaq CM to Nasd | R | D | EXIT LIQ | 20-60 | trail60 n5 +7.3%/-7.4%/+9.8% P0.13 | no | explored-dead |  |
| R4-15 S-3 shelf WITHDRAWN (form RW on an S-3) by a small cap | R | D | TOO WEAK | 30-80 | tp2020 n64 -0.4%/-1.4%/+0.3% P0.58 | no | explored-dead |  |
| R4-16 Going-private proposal by management / controller made public (SC 13D/ | J | D | GAP at the proposal, then bumps | 10-30 | hold1 n18 -1.0%/-2.5%/-1.2% P0.85 | no | explored-dead |  |
| R4-17 Tender offer by a non-controlling holder for >= 10% at a premium (SC T | J | D | GAP | 10-30 | too few trades | no | explored-dead |  |
| R4-18 Merger agreement amendment raising the price (8-K "amendment to the ag | J | W | GAP | 10-30 | hold20 n16 +3.2%/-1.3%/+3.1% P0.16 | no | explored-dead |  |
| R4-19 Company buys back a block from a departing big holder (8-K "repurchase | R | D | TOO WEAK | 10-30 | trail20 n216 +0.1%/-1.1%/-1.8% P0.48 | no | explored-dead |  |
| R4-20 Merger-of-equals target in a sector consolidating (two sale announceme | J | V | GAP (peers, not targets), TOO RARE | 20-60 |  | no | not explored (data / rarity: see log) |  |

### Near misses
- **J5 big buybacks, un-gapped** (closest): both halves positive in mean and median, jump rate 2.6x then 4.8x the stock's normal; died on ex-top3 (-0.1%) and P 0.23 with 68 trades.
- **J1 first profitable quarter**: judge +5.5%/trade, median +3.3%, but ex-top3 -1.8%, P 0.21 (48 trades).
- **J6 forward splits / J7 upgrade clusters**: jump rates held (x1.8 / x2.4), means +2.6% / +1.0%, carried by 3 trades.
- **Explore-only, failed the same-day control**: H16, R3-17, H9, V2, C2 (60-day rides that were market timing).
