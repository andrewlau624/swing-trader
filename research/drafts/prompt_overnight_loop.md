# OVERNIGHT LOOP: keep finding event edges while the user sleeps (two sessions at once)

The user is asleep. Two sessions run this file at the same time. Work continuously until a STOP condition below.
Every idea goes through `research/drafts/prompt_event_runbook.md` exactly. That file's hard rules apply
unchanged: no live code, no 2024-26 before registering, no money, merge (never rebase), and verdicts as printed.

## 0. Who you are
- If your session was started with "SESSION A", you take menu rows 1, 3, 5, 7, 9 first; "SESSION B" takes
  rows 2, 4, 6, 8, 10. If you weren't told, run `ListAgents`, pick the letter the other session did not take, and
  tell it with `SendMessage`.
- Tell the other session (SendMessage) whenever you claim an idea, register an N, or finish a study.

## 1. Claims file: never work on an idea the other session has
Before starting an idea:
```bash
git fetch && git merge origin/main
cat research/drafts/runbook_claims.md   # create it if missing, with a header line
```
If the idea is not listed, append `| <idea> | SESSION <X> | claimed <time> | in progress |`, then commit and push
immediately (`git commit -m "claim: <idea>"`). If the push fails because the other session pushed first, merge,
re-check the claims file, and choose another idea if it took this one. When you finish, update the line to
`done: <MEETS/FAILS or PASS/DEAD>`.

## 2. Trial numbers (N): claim them the same way
At Step 5 of the runbook, after merging, read the last amendment in `round1_prose.md`. Your N is the next free
number. Commit and push the amendment at once. If the push is rejected, merge: if the other session used that N,
renumber yours to the next free N in a new commit before running the judge. Never run the judge on an
unpushed registration.

## 3. The loop
Repeat:
1. Take the next unclaimed idea from your rows of the runbook menu, then from the other rows once yours are done.
2. Run it through the runbook (build events → explore/deals → notes → register → judge → write up).
3. Update the claims file, `runbook_notes.md` and NEXT.md; commit; push.
4. When both menus are used up, **make new menu rows** in `research/drafts/runbook_menu_extra.md`, with the same
   four-part shape (public timestamped event; who pays; small-size advantage; long-only whole shares) and the
   same dead-list check (NEXT + RESULTS + earlier notes). Good sources: other EDGAR form types (use
   `F.full_index(...).form.value_counts()` to see what exists), other 8-K phrases (full-text search), and
   combinations of an event with the night leg's 15:40 picks. Commit the new rows (claim them) before testing
   any of them. Max 10 new rows per session.

## 4. Sanity checks every 3 ideas
- `PYTHONPATH=. .venv/bin/python -m pytest tests/ -q` must pass. If it doesn't, STOP and write why.
- `git status` must be clean after your push; no stray large files (events parquet files are small; never commit
  anything over 20 MB).
- Re-read the runbook's hard rules.

## 5. STOP conditions (stop when any is true)
- You have finished 8 ideas (judged or explored-dead) this session.
- Both menus and 10 extra rows are used up.
- Tests fail, or the same command fails 3 times across ideas.
- A study PASSES: finish its writeup and its Step 8 spec, tell the other session, then continue. Do not stop on a
  pass, but never build live code.

## 6. Before you stop (always)
Append a morning summary to `research/drafts/runbook_notes.md`:
- a table: `idea | session | track | events/yr | verdict | $/yr at $2.3k / $10k / $25k`;
- in plain words: what passed (if anything) and why it might be real; what died; what the user should look at first.

Commit, merge, push. Then reply with that summary, in plain words, short.
