# JUMP HUNT: find signals that pick stocks about to jump +20-50%, and don't stop until one is FOUND

The user is asleep or away. Don't ask questions: decide, write down why, keep going. You are in
`~/Documents/Code/Projects/swing-trader`. Other sessions share this working tree and repo (run `ListAgents`; tell
any session working here that you're running this file, and message it whenever you register an N). Only
`git add` files you name; never clean, stash, reset or checkout files you didn't write.

## 0. The goal, made precise
The user wants **"jump" trades**: a public, timestamped signal after which a stock jumps **+20% or more** within
1-20 sessions far more often than that same stock normally does, **and** buying every signal makes money after
small-cap costs. Rare (a few a year) or frequent are both fine. Unusual, outside-the-box mechanisms are preferred
over textbook ones. LLMs are welcome as tools (section 3).

**FOUND** means exactly this, and nothing else: an idea that (1) meets the explore gate on the select half, (2) is
pre-registered and pushed, (3) prints `JUMP VERDICT: PASS` on the judge half, and (4) prints `CONFIRMED` on the
untouched confirm window, all with `research/sim/jump_runner.py` (or, for an LLM-window idea, PASSes and then gets a
forward shadow; see 3c). **Do not stop until FOUND** (stop rules in section 7). Never redefine FOUND, never loosen a
gate, never re-run a judge or confirm with new settings. The gates live in code so they can't drift.

**Why the three windows matter:** the longer you search, the more likely a fluke passes one test. The confirm
window (2025-07..2026-09) is looked at only after a judge PASS, once. Count every judged idea (k) and report it
next to any FOUND.

## 1. Read first (30 min, no data)
- `NEXT.md` (top, and the do-not-redo table), `RESULTS.md` (grep your keywords), `runbook_notes.md` (Round 33:
  13 event families dead, and the lesson **news moves in the gap; the session after is ~0**),
  `discovery_log_c5.md` / `study_discovery_round33b.md` (contract payoffs, mostly dead), `outside_box_ideas.md`,
  `study_ev2_first_insider_buy.md` (the one family that works: insiders' own money), `runbook_claims.md`.
- **Implication for jumps:** a jump that happens AT the news (the gap) can't be bought. You need signals that are
  public **before** the jump: slow-to-be-noticed data (government databases, filings nobody reads, numbers that
  need arithmetic to matter), mechanical squeezes that build over days, or attention that arrives late.

## 2. Hard rules
1. Research only. Never edit `scripts/`, `config.yaml`, `deploy/`, `.env`, or any order path. The one exception is
   a FOUND idea: add a **shadow/alert module** (logs and emails, never orders) under `swingtrader/daily/`, with
   tests, and register it in `swingtrader/daily/testing.py` (CLAUDE.md rule: it then shows in the weekly digest).
2. Select data only while exploring: `jump_runner explore` (event dates <= 2023-12-31 by default). No 2024+ outcome
   before pre-registration is committed and pushed.
3. No money. Free data only. The user's OpenCode Go subscription (`deepseek-v4-flash`, `swingtrader/daily/news_judge.py`
   `make_client("opencode-go")`) is allowed, with at most 3,000 calls per idea, counted in the log. No per-token
   paid APIs. If an idea needs paid data, write the request (source, price, why) in the log and move on.
4. Git: `git fetch && git merge origin/main` before every push; never rebase or force. Claim ideas in
   `runbook_claims.md` before any data work (prefix `Jump hunt`); skip ideas others claimed.
5. A command that fails twice: drop the idea, log the error, move on.
6. Verdicts copied exactly as printed.
7. Small accounts (CLAUDE.md): whole shares, long only (works in the Roth too). Report $/yr at $2.3k / $10k / $25k,
   with 10% of equity per signal.

## 3. Using LLMs without fooling yourself
LLMs know how past events turned out. An LLM judging an old filing ("is this bullish?") can be leaking the outcome
(Round 25 BC: the model knew events through at least 2025-10).
- **3a. Extraction is allowed on any window.** Asking the LLM to pull FACTS printed in a document (a dollar amount,
  a customer's name, a date, "is the counterparty a Fortune 100 company: name it") is allowed if: the prompt holds
  only the document (no ticker history, no dates after it), the output is validated (the number or name must
  appear verbatim in the text), and the signal is a rule on those facts (e.g. contract $ / market cap >= 50%).
  Prefer regex/XBRL when it works; use the LLM where text is messy. This is the big lever: **reading 10,000
  filings that no human reads.**
- **3b. Judgment only after the cutoff.** An LLM opinion as the signal (importance, surprise, tone) may only be
  tested on events after the model's cutoff + 2 months. Place the cutoff first with
  `research/sim/news_judge_hist.py probe`, extended to dated questions through 2026-08 (a new pre-registration,
  following Round 25b's rules). Then run `jump_runner ... --start <cutoff+2 months> --split <midpoint> --confirm none`.
- **3c. Forward-only ideas.** LLM-judgment ideas with too few clean events, and data you can only collect from today
  (borrow fees, live trending lists), can't be FOUND on history. If one meets the explore gate on its clean window,
  write a shadow spec, register it in `testing.py` as a shadow, and keep hunting (it doesn't end the hunt).
- **3d. LLM as idea generator.** Allowed and encouraged: ask it for mechanisms, for data sources and for "who is
  forced to buy". Every idea still goes through the dead-list check and the runner.

## 4. Where jumps come from: seeds (verify each, extend freely, prefer the strange)
Write the cause sentence for every idea: "<who> will have to / start to buy <what> after <public signal>, but most
people only notice when <later event>, so the price jumps then."

**A. Numbers that need arithmetic to matter (relative magnitude).** The size of a contract, order, grant, award
or settlement relative to the company's market cap (shares from XBRL `dei:EntityCommonStockSharesOutstanding`, via
the free companyfacts API). A $40M contract is nothing to Lockheed and +100% to a $30M company. Sources: 8-K Item
1.01 / 8.01 text; **defense.gov daily contract announcements** (17:00 ET, archive to ~2014, free); USAspending.gov
API; SAM.gov awards; state contracts; BARDA/NIH/DoE grants; court judgments and settlements (CourtListener free API).
**B. Regulators' databases update before the press release.** openFDA (510(k), De Novo, PMA decisions and
dates), Drugs@FDA, ClinicalTrials.gov (status changes, results-posted dates), USPTO patent grants (Tuesdays), FCC
equipment authorizations, FAA certificates, EPA/USDA approvals, ITC rulings, Federal Register. Signal = a small
cap's item appearing in the database; the jump = when the company or newswire tells everyone.
**C. Validation by a giant.** A mega-cap or famous holder shows up in a tiny company's 13F/13G/13D, Form 4, 8-K
counterparty text, or as a customer ("purchase order from Amazon"). E.g. Nvidia's 13F listing small AI names
(Feb 2024: SOUN/SERV jumped 60-100%, but AT the next open, so that jump itself was not buyable). The hunt asks whether more follows after the gap, or finds the giant EARLIER (a customer or investor named in an 8-K or S-1 weeks before). Corporate-VC 13F filers are a short list: build it.
**D. Squeezes that build mechanically.** Reg SHO threshold-list entries (Nasdaq/NYSE daily files, free archive)
+ small float (XBRL) + rising FINRA short interest (bimonthly, free): forced buy-ins. Check DS4/AY on the dead list
first: they were *tilts on night picks*; a jump hunt on squeeze setups is a different question, so say why.
De-SPACs and post-reverse-split names with a tiny free float (425 / 8-K float language) also qualify.
**E. Attention that arrives late.** Wikipedia pageviews API (free, daily, 2015+): a company page's views spiking
x5 while the price is still flat; Hacker News (Algolia API, free) front-page posts about a small public company's
product; GitHub stars on a public company's open-source repo; app-store rank jumps if free data exists; name
changes into a hot theme (8-K Item 5.03 / new name contains AI, quantum, nuclear, drone, crypto); first-ever
analyst initiation of a microcap (8-K/press text "initiated coverage").
**F. Insiders' own money, in the tail.** EV2 (first purchase in 2 years) and big buys in MICROCAPS (ADV < $20M,
which EV2 never tested); CEO buys > 10% of their own annual salary (DEF 14A pay data); several insiders buying
after a 50% drawdown.
**G. Turnarounds with a dated trigger.** Going-concern warning removed (10-K/10-Q text), bankruptcy plan confirmed
with old equity kept, a delisting notice cured, debt fully repaid early ("repaid in full"), first quarter of
positive operating income in a microcap (XBRL OperatingIncomeLoss turns positive).
**H. The bot's own data.** The night leg's 15:40 pool and its logs (fills, skips, news-judge verdicts, quote sizes):
which picks bounced +20% next day, and what did 15:40 know? Forward-only unless the data exists historically.
Not allowed (dead or banned): plain 8-K phrase -> next-session drift, FDA approvals / topline / Breakthrough
(lotteries, Round 33), uplisting, index adds, spin-offs, announcement-gap drift (Lab-BH), theme-breakout momentum,
earnings drift, technical indicators, news sentiment scores on historical data.

## 5. Process
1. **Setup:** merge, `PYTHONPATH=. .venv/bin/python -m pytest tests/ -q` (must pass), read the current N (last
   `## Amendment` in `research/drafts/round1_prose.md`). Create `research/drafts/jump_hunt_log.md` with a **STATE**
   block at the top: N, k (judged so far), current idea, the next 5 ideas, and data sources verified or broken.
   **Update STATE after every idea**, so a session that resumes after a context summary knows exactly where it is.
2. **Diverge:** `research/drafts/jump_ideas.md`, **>= 40 ideas**: letter (A-H or new), cause sentence, data source
   (free? verified reachable?), est. signals/yr, why it isn't dead or banned (cite the grep), novelty 1-5 (what you
   searched to check). Commit + push before any outcome is computed.
3. **Rank:** expected jump rate x payoff x signals/yr x novelty x P(data works). Do data-reachability checks (one
   request each) on the top 15 before ranking finally.
4. **Per idea:**
   1. Claim it.
   2. Build `data/research/program/events_jump_<name>.parquet` (`sym`, `fd` = the date the signal was PUBLIC;
      for after-close data, that date; never earlier). Save the builder as `research/sim/jump_<name>.py`.
   3. Run `jump_runner explore` ONCE. That one run shows 6 cells (hold 1/5/20 x hold/tp20); the look is the run, so
      log all 6. You may also try ONE variant of the event rule (a threshold you wrote down BEFORE the first
      run), logged as a second look.
   4. If a cell MEETS: write the cause sentence, who is on the other side, why it persists; pre-register in
      `round1_prose.md` (`## Amendment — Jump hunt, Study J<k>: <idea> (pre-register; <looks> looks, program N a -> a+1)`)
      naming the ONE cell (shortest hold that met). Commit + push. If another session took that N, renumber before
      judging.
   5. Judge once. If PASS: confirm once. If CONFIRMED: FOUND (section 6).
   6. Write `research/drafts/study_jump_<name>.md` (all numbers, verdicts as printed), a NEXT line, and a
      do-not-redo row if dead. Update claims + STATE, commit, push.
5. **When the list runs low** (< 5 untested ideas): generate 20 more with a method you haven't used yet (rulebook
   reading, another field's analogy, an LLM brainstorm on "who is forced to buy small caps", the form-type census,
   government data catalogs at data.gov). Dead-check them, commit, continue.
6. **Every 5 ideas:** tests pass, git clean for your files, re-read sections 0 and 2, and update STATE with a
   one-line pattern of why things are dying (it should change what you try next).

## 6. FOUND protocol
1. Writeup with: select / judge / confirm lines as printed; k (ideas judged in this hunt) and N; cause sentence;
   what kills it (crowding, a data source closing); **$/yr at $2.3k / $10k / $25k** (10% per signal, whole shares,
   the runner's costs); how often it fires; what the user does by hand, if anything.
2. Build the shadow/alert: `swingtrader/daily/<name>_watch.py` (daily check at a fixed time; logs each signal to
   `state/<name>.jsonl`; scores each one at its exit; emails the signal; **never orders**). Add tests, a Makefile
   target, a `testing.py` REGISTRY entry (gate: 20 forward signals, mean net > 0) and a NEXT line. Run the full
   test suite.
3. Commit, merge, push. Append a summary to `jump_hunt_log.md`, then STOP and reply to the user in plain words:
   what it is, why it might be real, the three verdict lines, k, the money at three sizes, and what happens next
   (the shadow).

## 7. Stop rules (the only ones)
- FOUND (section 6).
- Tests fail and you can't fix them without touching live code: stop and write why.
- Every idea source is exhausted after **at least 3 rounds of new idea generation** AND **>= 60 ideas explored**:
  stop and write the honest summary (what came closest and why it failed). "Nothing found" after an honest search is
  a result; a fluke dressed up as FOUND is a disaster.

Before any stop, update STATE and append to `jump_hunt_log.md` a table
`idea | source | signals/yr | best select cell (jump vs base, mean net, ex-top3) | judged? | verdict | confirm`,
plus the closest near misses. Commit, merge, push.
