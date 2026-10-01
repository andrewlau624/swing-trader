# Mistakes log

What went wrong, and what changed so it cannot repeat. Newest first. One entry per mistake:
date, what happened, the cost (in $ or bp, or "none, caught in replay"), the fix (code, test or rule).

## 2026-10-01 — Study AU re-tested an idea RESULTS.md already had dead
- **What happened.** The Stocks-in-Play 5-min ORB was in RESULTS.md's "Dead (do not redo)" table (negative
  gross, −12bp/trade, 10% win). The pre-registration checked only NEXT.md's dead-list table, which does not
  copy every RESULTS.md table. AU reproduced it (−13.5bp gross, conservative fills; ~+10bp gross even with
  optimistic fills, which is below costs).
- **Cost.** 2 variants of N (671 -> 673) and ~1.5 h of compute. No money.
- **Fix.** Before any pre-registration, grep RESULTS.md AND NEXT.md for the idea's keywords
  (`grep -n -i "<keyword>" RESULTS.md NEXT.md`) and say so in the registration.

## 2026-10-01 — per-trade replay statistics compounded one account (Study AU first run)
- **What happened.** The "unconstrained" per-trade run used one $10M account across all days, with no
  notional cap. AU's tight stops (10% ATR) sized positions huge, losses drained the account, and from
  2024 later trades rounded to 0 shares: H2 had 12 trades vs 5,700 in H1. The first AU verdict
  ("DEAD") was computed on that broken run.
- **Cost.** None; caught before any write-up, because the half counts were absurd.
- **Fix.** Statistics mode now gives every day a fresh account (`as_replay.replay`, `au_replay.replay`).
  AS was re-run the same way to confirm its numbers. Rule: always print trades per half before reading
  a verdict.

