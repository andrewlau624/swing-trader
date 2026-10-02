# Jump & ride hunt log (prompt_jump_hunt.md), session llm-trader-51

## STATE (update after every idea)
- program N: 762 (J1, J2 registered and judged DEAD). k (ideas judged): 2. Ideas explored: 14 (H17 D5 D9 D4 D6 H1 H2
  H3 C4 H18 C7 C10 R2-4 R2-5). Rounds of idea generation: 1 (62 ideas) + 9 early round-2 adds.
- current idea: none; next ideas need the news archive (40/96 select months at 15:55).
- next 5 ideas (informed/forced buyers, per section 6): H11 option alerts, D8 first insider buy + no news, S2 PDUFA
  run-up, D2 un-gapped contracts, H10 first initiation. Then Wikipedia ideas when pageviews finish.
- data sources verified: Alpaca/Benzinga news (downloading), Arctic Shift (small subs complete; WSB 3 chunks running),
  Wikipedia pageviews (downloading, ~40%), EDGAR (FTS, form.idx 2016-26, companyfacts), ClinicalTrials.gov, openFDA,
  USAspending, Form 345 2014-2026, FINRA SI 2020-06+ (public settle + 12 d), Wayback 2018+ Yahoo trending (slow fetch).
- data sources broken: defense.gov (403); Yahoo trending 2016-17 snapshots (list loaded client-side).
- why things die (running): EXIT LIQUIDITY (crowd attention: 4-14x one-day jump rate, then -5..-22% over 20-60
  sessions: H1 H2 H3 C4 H18 C7 C10), TWO-WAY (attention without direction: H17 D4), LOTTERY (D5 D9 J1), PRICE PROXY
  + REGIME (J2: the fall, not the insider; 2020 bottom). Next ideas need an informed or forced buyer whose effect
  survives a same-stock no-event control, AND many independent events.

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
