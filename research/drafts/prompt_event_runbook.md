# RUNBOOK: find event edges (frequent, semi-rare, and rare-but-big). Written so any model can follow it.

Follow the steps IN ORDER. Do not skip steps. Do not improvise outside the rules. When a step says STOP, stop.
You are in the `swing-trader` repo on the Mac. Use the exact commands shown.

## What we want (the user's words, made precise)
The user likes **high-confidence event signals that pay**: the insider-buy day trade (ID3) and odd-lot tenders.
Find more, in three tracks:

| track | how often | what counts as good (on 2016/2021-2023 data) |
|---|---|---|
| FREQUENT | 100+ trades a year | net ≥ +10bp per trade, hit rate ≥ 50%, t ≥ 2 |
| **SEMI-RARE (best)** | 24-100 a year (2-8 a month) | net ≥ +50bp per trade, hit rate ≥ 55%, t ≥ 2 |
| RARE, BIG SWING | 6-24 a year | hit rate ≥ 65%, average ≥ +3% per deal, worst deal ≥ −15% |

The tool picks the track for you from the event count. You never decide it yourself.

## Hard rules (break one = the session's results do not count)
1. Never edit anything under `swingtrader/`, `scripts/`, `config.yaml`, `deploy/` or `.env`. Research only.
2. Never look at 2024-2026 results until the idea is pre-registered and committed (Step 5). The `explore` and
   `deals ... select` commands only use data up to 2023-12-31. Use only those while exploring.
3. Never spend money. Never call paid APIs. EDGAR and Alpaca are free.
4. Git: `git fetch && git merge origin/main` (never rebase, never force-push) before every push.
5. If a command fails twice, STOP that idea, write the error into `research/drafts/runbook_notes.md`, and move to
   the next idea.
6. At most 6 ideas per session.
7. Copy verdicts exactly as the tool prints them (MEETS/FAILS, PASS/DEAD). Do not reinterpret.

## Step 0. Setup (run once)
```bash
cd ~/Documents/Code/Projects/swing-trader
git fetch && git merge origin/main
PYTHONPATH=. .venv/bin/python -m pytest tests/ -q        # must say "passed"; if it fails, STOP and report
grep -n "^## Amendment" research/drafts/round1_prose.md | tail -1   # note the last "N a -> b": b is CURRENT N
```
Read these files fully: `NEXT.md` (top section and the "Things already tested — do NOT redo these" table),
`research/drafts/event_edge_candidates.md`, `research/drafts/outside_box_explore_log.md`.

## Step 1. Pick ideas from this menu, in order (skip any marked done or found dead in NEXT.md / RESULTS.md)
Check each with: `grep -n -i "<keyword>" NEXT.md RESULTS.md research/drafts/*.md | head`. If it is already
tested, skip it and say so.

| # | event (SEC form or text) | expected track | status |
|---|---|---|---|
| 1 | Cluster insider buys: 2+ different officers/directors buy within 5 days (from `insider_buys()`) | semi-rare | new |
| 2 | First insider purchase at a company in 2+ years (from `insider_buys()`) | semi-rare | new |
| 3 | `SC 13G` originals: a new passive 5% holder | frequent | new |
| 4 | `SC 13D/A` amendments: an activist adding shares | semi-rare | new |
| 5 | 8-K text "strategic alternatives" (sale or merger review), via full-text search | rare/big | new |
| 6 | 8-K text "special dividend", via full-text search | rare/big | new |
| 7 | 8-K text "share repurchase" + "accelerated", via full-text search (ASR buybacks) | semi-rare | new |
| 8 | `25-NSE` delisting notices (forced selling) | rare/big | new |
| 9 | Spin-off completion (8-K text "completed the spin-off" / "distribution of all of the outstanding") | rare/big | new |
| 10 | `S-8` filings (new stock plans) | frequent | low prior |
| — | officer/director buys (ID3), 13D originals (A1), 10%-owner buys (A2), 424B offerings (T), NT 10-K, Form 144, odd-lot tenders | — | **done: skip** |

## Step 2. Build an events file (columns `sym`, `fd` = filing date)
Use ONE of these two snippets, edited only where marked `<<<`. Save the file as
`data/research/program/events_<short_name>.parquet`.

**A. By form type** (menu rows 3, 4, 8, 10):
```python
from research.sim import event_fetch as F
import pandas as pd
FORM = "SC 13G"                                                     # <<< exact form type
tick = F.company_tickers()
rows = []
for y in range(2020, 2027):
    for q in range(1, 5):
        if (y, q) > (2026, 3):
            break
        D = F.full_index(y, q)
        D = D[D.form == FORM]
        busy = D.cik.value_counts()
        D = D[D.cik.map(busy) <= 50]          # drop filers/agents that file this form > 50x a quarter (banks, funds)
        for cik, d in zip(D.cik, D.date):
            for t in tick.get(str(int(cik)), []):
                rows.append((t, d))
X = pd.DataFrame(rows, columns=["sym", "fd"]).drop_duplicates()
X["fd"] = pd.to_datetime(X.fd)
X.to_parquet("data/research/program/events_13g.parquet")           # <<< file name
print(len(X), X.fd.min(), X.fd.max())
```
**B. By text in 8-Ks** (menu rows 5, 6, 7, 9):
```python
from research.sim import event_fetch as F
import pandas as pd
hits = F.fts_years('"strategic alternatives"', "8-K", 2020, 2026)  # <<< the exact phrase, in double quotes
print(hits[0].keys())                                               # look at the fields once
# map each hit to (ticker, filing date): use the hit's ticker field if present, else company_tickers() by CIK
```
For B, print the fields first, then write the mapping. Every row must have a ticker and a filing date.

**C. From insider purchases** (menu rows 1, 2): `from research.sim.outside_box import insider_buys`;
`X = insider_buys()`; keep `X[X.insider]`; build the rule (e.g. group by `sym`, keep dates where 2+ different
filings fall within 5 days); save `sym`, `fd`.

Check: `len(X) > 0`, dates span 2020-2026, tickers look real. If the file is empty or wrong, fix it once; if it's
still wrong, follow rule 5.

## Step 3. Explore on the SELECT half only
```bash
PYTHONPATH=. .venv/bin/python -m research.sim.event_runner explore data/research/program/events_<name>.parquet
```
- If it prints `TRACK ... MEETS`, go to Step 4 with the 1-session trade.
- If it prints `RARE (< 24/yr): use the deal report`, run the deal report with holds of 1, 5 and 20 sessions:
  ```bash
  PYTHONPATH=. .venv/bin/python -m research.sim.event_runner deals data/research/program/events_<name>.parquet 5 select
  ```
  Pick the ONE hold (1, 5 or 20) whose gate prints `MEETS`. If several meet, pick the shortest. If none
  meets, the idea is explored-dead.
- If it prints `FAILS`, the idea is explored-dead. Write one line into `research/drafts/runbook_notes.md`
  (idea, events/yr, net, hit, t, "explored-dead") and go to the next idea.

You may try ONE liquidity floor besides the default (`explore FILE 1e6` for $1M ADV) per idea, and must write
that you did. No other tuning.

## Step 4. Write down why it should work (before registering)
In `runbook_notes.md`, under the idea, write three lines: **who** is on the other side; **why** they keep
paying; **why** big funds don't take it (too small, too rare, too manual). If you cannot write these, do not
register it.

## Step 5. Pre-register (BEFORE any 2024-26 number)
Append this block to the end of `research/drafts/round1_prose.md`, filling every `<...>`. CURRENT N is from
Step 0; the new N is CURRENT N + 1.
```
## Amendment — Round <R>, Study <LETTERS>: <one-line idea> (pre-register; 1 variant, program N <N> -> <N+1>)

`date`: <today> (stamped by the commit), before any 2024-26 number. Runbook: research/drafts/prompt_event_runbook.md.
Event: <exact form type or text query>, events file data/research/program/events_<name>.parquet (built by <snippet A/B/C> with
<the exact rule>). Trade: buy the opening cross of the first session after the filing date, sell the closing cross
<hold> session(s) later; ADV >= $<floor>. Track: <FREQUENT | SEMI-RARE | RARE>. Who pays: <line>. Why it persists: <line>.
Select-half result (2021-23): <paste the explore/deals summary lines>.
Judge: FREQUENT/SEMI-RARE -> `event_runner run` (the registered Study ID bar, PASS/DEAD as printed);
RARE -> `event_runner deals ... judge` (hit >= 60%, mean > 0, worst >= -20%; PASS/DEAD as printed).
```
Then:
```bash
git add research/drafts/round1_prose.md research/drafts/runbook_notes.md data/research/program/events_<name>.parquet
git commit -m "Round <R> pre-registration: Study <LETTERS>, <idea>, N <N> -> <N+1>"
git fetch && git merge origin/main && git push
```
If the merge shows that someone else used N+1 in the meantime, renumber yours (next free N) in a new commit
BEFORE Step 6.

## Step 6. Run the judge ONCE
- FREQUENT / SEMI-RARE (1-session trade):
  `PYTHONPATH=. .venv/bin/python -m research.sim.event_runner run data/research/program/events_<name>.parquet "<LETTERS> <idea>" <N+1>`
- RARE: `PYTHONPATH=. .venv/bin/python -m research.sim.event_runner deals data/research/program/events_<name>.parquet <hold> judge`

Never re-run with different settings after seeing the result. The printed PASS/DEAD is final.

## Step 7. Write it up (for every judged idea)
Create `research/drafts/study_<letters_lowercase>_<name>.md`:
```
# Study <LETTERS> — <idea>: <PASS or DEAD>
Pre-registration: round1_prose.md Round <R> (commit <hash>). Runner: research/sim/event_runner.py.
Events: <form/query>, <count> events, <per year>/yr. Track: <track>. Hold: <n> session(s).
Select half (2021-23): <paste>. Judge half (2024-26): <paste the key lines: net per trade, hit, t or worst, verdict>.
$/yr if real: <net per trade × trades per year × position size> at $2.3k / $10k / $25k (position size = 10% of equity).
Who pays / why it persists: <lines>.
```
Add one line to the top Round section of `NEXT.md`. If DEAD, also add a row to the do-not-redo table:
`| <idea> (Round <R> <LETTERS>) | **dead** | <one-line reason with the numbers> |`.
Commit and push (rule 4).

## Step 8. If something PASSES
Do NOT build live code (rule 1). Add a section to the writeup titled "Spec for a shadow (for the next session)"
listing: the event source, the daily check time, the entry and exit orders, position size (10% of equity, at most 2%
of equity at risk per event), the kill rule (≥ 60 trades with a losing mean → off), and the line for the weekly
digest. A stronger session or the user builds it.

## Step 9. End of session
Write a closing table at the end of `research/drafts/runbook_notes.md`:
`idea | track | events/yr | select result | judged? | verdict | $/yr at $2.3k / $10k / $25k`. Commit and push.
Tell the user in plain words: what passed, what died and why, and what to run next.
