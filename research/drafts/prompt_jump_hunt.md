# JUMP & RIDE HUNT: find hype, news and attention signals that catch big moves, and don't stop until one is FOUND

The user is asleep or away. Don't ask questions: decide, write down why, keep going. You are in
`~/Documents/Code/Projects/swing-trader`. Other sessions share this working tree and repo (run `ListAgents`; tell
any session working here that you're running this file, and message it whenever you register an N). Only
`git add` files you name; never clean, stash, reset or checkout files you didn't write.

## 0. The goal, made precise
The user wants to catch **big moves**, on any schedule (often or rare), from **unusual signals**: news, hype,
attention, odd data, LLM reading at scale. Two tracks, both graded by `research/sim/jump_runner.py`:
- **JUMP:** after the signal, the stock jumps **+20% or more** far more often than that same stock normally does.
- **RIDE:** get in **before or while a stock is hot** and keep a chunk of the run (exit rules incl. a 15% trailing
  stop, holds up to 60 sessions): mean net >= +3% a trade and >= +2% better than the stock's usual return.

Both must make money after small-cap costs (built into the runner), with no single lottery ticket carrying it.

**FOUND** means exactly this: an idea that (1) meets a track's explore gate on the select half, (2) is pre-registered
and pushed, (3) prints `JUMP VERDICT: PASS` or `RIDE VERDICT: PASS` on the judge half (`--track` as registered), and
(4) prints `CONFIRMED` on the untouched confirm window (2025-07..2026-09). An LLM-window idea instead PASSes and then
gets a forward shadow (3c). **Do not stop until FOUND** (section 8). Never redefine FOUND, never loosen a gate,
never re-run a judge or confirm with new settings. The gates live in code so they can't drift. Count every judged
idea (k) and report it next to any FOUND: the more you judge, the likelier a fluke.

## 1. Why ideas have died here: the death map (read this, then design around it)
Eight hundred tested variants died for a short list of reasons. **Every idea you write must name the death it is
built to dodge, and how.** If you can't name one, it is probably the same dead idea again.

| death | what it looked like here | how to dodge it |
|---|---|---|
| **GAP** | 8-K events, FDA approvals, S&P adds, Nvidia's 13F: the move happens at the next open, before you can buy | be earlier than the news: slow databases, arithmetic nobody does, hype building in a place markets don't watch |
| **LOTTERY** | biotech, spin-offs, first buybacks: a few huge winners, median negative | many independent events; the runner's ex-top-3 test; signals that move the median, not just the tail |
| **COST** | intraday lab ideas, closing imbalance: real +6bp signals eaten by the spread | only moves big enough (>= +5%) to dwarf a 75bp-a-side small-cap cost |
| **REGIME** | theme momentum 2020-21, 13G only in 2023, momentum lagging since 2016 | ask "why would this work in 2017 AND 2025?" before testing; three windows catch the rest |
| **PRICE PROXY** | retail trade size (rho .83 with price), vol-like tilts | the runner compares each stock to itself; avoid signals that are just "small, cheap, volatile" |
| **TEXTBOOK** | PEAD, Ikenberry buybacks, 12-1 momentum: published, crowded, decayed | data no paper uses; mechanisms specific to 2020s retail/social markets |
| **TOO RARE** | contract payoffs at ~1 a year | >= 6 signals a year, or a family of similar events |
| **LOOKAHEAD** | LETF close cross; LLM memory of outcomes | timestamp audit: when exactly was the signal public, and could you trade the open after it? |

Also read before writing ideas: `NEXT.md` (top + the do-not-redo table), `RESULTS.md` (grep), `runbook_notes.md`,
`discovery_log_c5.md`, `study_discovery_round33b.md`, `outside_box_ideas.md`, `study_ev2_first_insider_buy.md`,
`runbook_claims.md`, and `jump_hunt_log.md` if it exists (resume from its STATE).

## 2. Hard rules
1. Research only. Never edit `scripts/`, `config.yaml`, `deploy/`, `.env`, or any order path. One exception, a
   FOUND idea: add a **shadow/alert module** (logs and emails, never orders) under `swingtrader/daily/`, with tests,
   registered in `swingtrader/daily/testing.py` (CLAUDE.md: it then shows in the weekly digest).
2. Select data only while exploring: `jump_runner explore` (event dates <= 2023-12-31 by default). No 2024+ outcome
   before pre-registration is committed and pushed.
3. No money. Free data only. The user's OpenCode Go subscription (`deepseek-v4-flash`,
   `swingtrader/daily/news_judge.py make_client("opencode-go")`) is allowed, at most 3,000 calls per idea, counted
   in the log. No per-token paid APIs. If an idea needs paid data, write the request (source, price, why) and move on.
4. Git: `git fetch && git merge origin/main` before every push; never rebase or force. Claim ideas in
   `runbook_claims.md` before any data work (prefix `Jump hunt`); skip ideas others claimed.
5. A command that fails twice: drop the idea, log the error, move on. Respect every site's rate limits and terms
   (identify yourself in User-Agent; SEC needs `sec_headers()`).
6. Verdicts copied exactly as printed.
7. Small accounts (CLAUDE.md): whole shares, long only (works in the Roth too). Report $/yr at $2.3k / $10k / $25k
   with 10% of equity per signal.

## 3. Using LLMs without fooling yourself
LLMs know how past events turned out (Round 25 BC: this model knew events through at least 2025-10).
- **3a. Extraction: any window.** Pulling FACTS printed in a document or post (a dollar amount, a customer's name,
  the tickers mentioned, "is this a product launch: yes/no", supplier names from a 10-K) is allowed if the prompt
  holds only that text (no ticker history, nothing dated after it) and the output is validated (the number or name
  appears verbatim). The signal is then a rule on the facts. **This is the big lever: reading 100,000 filings,
  posts and pages no human reads.** Prefer regex/XBRL where it works.
- **3b. Judgment: only after the cutoff.** An LLM opinion as the signal (hype quality, surprise, "would retail get
  excited") only on events after the model's cutoff + 2 months. Place the cutoff first with
  `research/sim/news_judge_hist.py probe`, extended to dated questions through 2026-08 (a new pre-registration under
  Round 25b's rules). Then `jump_runner ... --start <cutoff+2mo> --split <midpoint> --confirm none`.
- **3c. Forward-only.** Judgment ideas with too few clean events, and data you can only collect from today (live
  trending lists, borrow fees), can't be FOUND on history. If one meets an explore gate on its clean window, write a
  shadow spec, register it in `testing.py`, and keep hunting.
- **3d. Brainstorm partner.** Use it to generate mechanisms, data sources and collisions (section 5). Its ideas go
  through the same death map, dead-list check and runner.

## 4. Raw material: weird, free data (verify each with one request before relying on it)
- **Hype and attention, with history:** Reddit comment/post dumps (Arctic Shift / academic torrents: r/wallstreetbets,
  r/pennystocks, r/smallstreetbets, r/shortsqueeze; ticker-mention velocity, first-mention dates); Wikipedia
  pageviews API (daily, 2015+); Hacker News (Algolia API); GitHub stars/forks over time; Google Trends (rate-limited,
  pytrends); **Alpaca/Benzinga news archive** (with this repo's Alpaca keys; headline counts, first-ever coverage,
  news velocity by ticker; COUNTS and FACTS, not sentiment); YouTube/podcast titles if a free API allows.
- **The Wayback Machine as a time machine** (archive.org CDX API, free): point-in-time snapshots of "trending
  tickers" pages (Yahoo, StockTwits, Robinhood's top lists), app-store top charts, conference presenter lists,
  careers pages (hiring bursts), product pages and price lists. Anything a website showed on a past date.
- **Slow official data:** defense.gov daily contracts (17:00 ET), USAspending, SAM.gov, openFDA (510(k), De Novo,
  PMA), ClinicalTrials.gov, USPTO grants, FCC IDs, FAA, Federal Register, CourtListener (judgments), SEC comment
  letters (CORRESP/UPLOAD), XBRL companyfacts (shares, revenue, cash), Reg SHO threshold lists, FINRA short interest.
- **This repo:** EDGAR helpers (`research/sim/event_fetch.py`), Form 4s (`insider_buys()`), raw and split-adjusted
  bars (`jump_runner.split_bars`), the night leg's logs and picks (`state/`, `logs/` on the server; forward only).

## 5. Creativity engine (mandatory: the idea list must show these)
Write `research/drafts/jump_ideas.md` with **>= 50 ideas** before computing any outcome. Each idea: track (JUMP or
RIDE), method tag (below), the cause sentence ("<who> starts / is forced to buy <what> after <public signal>; most
people only notice at <later event>; that's when it moves"), the **death it dodges**, data source (verified?),
signals/yr, novelty 1-5 with what you searched. Quotas:
- **>= 20 hype/attention/news ideas** (data where crowds talk: social, search, pageviews, news counts, trending pages).
- **>= 10 death-dodges:** take a specific DEAD study, name its death, change exactly that. Example: FDA approvals
  died of GAP + LOTTERY, so try device clearances that sit in openFDA days before the press release, on companies
  where the device is most of the revenue.
- **>= 10 collisions:** two unrelated signals at once, each weak alone. Examples: a Wikipedia spike plus an insider
  buy; a contract award plus a float under 10M shares; a first Reddit mention plus a fresh 13G.
- **>= 5 hype-venue lags:** hype shows up in one place before another. Examples: small subreddits before WSB; HN or
  GitHub before finance media; Korean/Japanese retail theme stocks before US-listed peers; a theme leader's earnings
  before its unknown suppliers (supplier names LLM-extracted from 10-Ks).
- **>= 5 scheduled-hype run-ups (RIDE):** buy the rumor into a known date, then exit before it. Examples:
  small caps presenting at a mega-conference (GTC, CES, JPM Healthcare), investor days, product launches, FDA
  adcom dates, crypto/AI-themed index inclusion dates.
- **>= 5 wildcards:** ideas that feel silly. Examples: a ticker spelling a hot word, a CEO going viral, an
  earnings call that mentions "AI" 20 times, Wikipedia edit wars, a company's app hitting the top-100 chart.
Banned as-is (dead or banned; only allowed as a named death-dodge): plain 8-K phrase -> next-session drift, FDA
approvals / topline / Breakthrough, uplisting, index adds, spin-offs, announcement-gap drift (Lab-BH), price-first
theme/breakout momentum (theme-explosion sleeve), earnings drift, technical indicators, LLM or sentiment scores on
pre-cutoff news. **RIDE ideas must be attention-first or event-first, not price-first**: price breakouts died.

## 6. Process
1. **Setup:** merge; `PYTHONPATH=. .venv/bin/python -m pytest tests/ -q` must pass; read the current N (last
   `## Amendment` in `research/drafts/round1_prose.md`). Create/resume `research/drafts/jump_hunt_log.md` with a
   **STATE** block at the top: N, k, current idea, next 5 ideas, data sources verified/broken, and the running "why
   things die" line. **Update STATE after every idea** (a resumed session must know exactly where it is).
2. **Diverge:** the idea list (section 5). Commit + push before any outcome.
3. **Rank:** (P it dodges its death) x (signals/yr) x (payoff) x (novelty) x (P the data works). One reachability
   request each for the top 15 before the final ranking. Work down the list.
4. **Per idea:**
   1. Claim it.
   2. Build `data/research/program/events_jump_<name>.parquet` (`sym`, `fd` = the date the signal was PUBLIC; for
      after-close data, that date, never earlier). Save the builder as `research/sim/jump_<name>.py`.
   3. Run `jump_runner explore` ONCE (12 cells: holds 1/5/20/60 x exits hold/tp20/trail, each graded for JUMP and
      RIDE). That run is the look; log all 12 lines. You may try ONE variant of the event rule, with its threshold
      written down BEFORE the first run, logged as a second look.
   4. If a cell MEETS: write who is on the other side and why it persists; pre-register in `round1_prose.md`
      (`## Amendment — Jump hunt, Study J<k>: <idea> (pre-register; track <JUMP|RIDE>, cell <rule><hold>, <looks>
      looks, program N a -> a+1)`). Commit + push. Renumber before judging if another session took that N.
   5. `jump_runner judge EVENTS HOLD RULE --track <jump|ride>` once. If PASS: `confirm` once, same arguments. If
      CONFIRMED: FOUND.
   6. Write `research/drafts/study_jump_<name>.md` (all numbers, verdicts as printed), a NEXT line, and a
      do-not-redo row if dead. Update claims + STATE, commit, push.
5. **Refill** when < 5 untested ideas remain: 20 new ones, using a method or data source you haven't used yet.
   Re-read the death map first, and add the new deaths you've seen. Commit, continue.
6. **Every 5 ideas:** tests pass, your files clean in git, re-read sections 0-2, update the "why things die" line.
   If the last 10 ideas died the same way, the next 10 must be built to dodge THAT death.

## 7. FOUND protocol
1. Writeup: select / judge / confirm lines as printed; k and N; cause sentence; the death it dodged; what would kill
   it (crowding, a data source closing); **$/yr at $2.3k / $10k / $25k** (10% per signal, whole shares, the
   runner's costs); signals a year; the manual steps, if any.
2. Shadow/alert: `swingtrader/daily/<name>_watch.py`: a daily check at a fixed time; logs each signal to
   `state/<name>.jsonl`; scores each at its exit; emails the signal; **never orders**. Tests, a Makefile target, a
   `testing.py` REGISTRY entry (gate: 20 forward signals, mean net > 0) and a NEXT line. Full test suite passes.
3. Commit, merge, push. Append the summary to `jump_hunt_log.md`. STOP and reply to the user in plain words: what it
   is, why it might be real, the three verdict lines, k, the money at three sizes, what happens next.

## 8. Stop rules (the only ones)
- FOUND (section 7).
- Tests fail and can't be fixed without touching live code: stop, write why.
- **At least 4 rounds of idea generation AND >= 80 ideas explored**, and no source left: stop with the honest
  summary (what came closest and the death that got it). "Nothing found" after an honest search is a result; a
  fluke dressed up as FOUND is a disaster.

Before any stop: update STATE and append to `jump_hunt_log.md` the table
`idea | track | method | death dodged | signals/yr | best select cell | judged? | verdict | confirm`, plus the near
misses. Commit, merge, push.
