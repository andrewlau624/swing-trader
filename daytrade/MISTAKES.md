# Mistakes log

What went wrong, and what changed so it cannot repeat. Newest first. One entry per mistake:
date, what happened, the cost (in $ or bp, or "none, caught in replay"), the fix (code, test or rule).

## 2026-10-01 — a stop already through the market filled at the stop price (Lab-AY2's false "PASS")
- **What happened.** Lab-AY2 (buy after a halt down) "passed": +757bp/trade, t 3.9. The top trades exited "by stop"
  at 4-10x the entry (CIGL bought $2.17, "stopped" at $22.67). The stop was 10% below the pre-halt price, far
  ABOVE a reopening print 90% lower. An earlier refinement ("a stop placed inside a bar does not get the gap
  fill at the open") then filled it at the stop price: impossible, and always flattering.
- **Cost.** None, but a false edge came within one write-up of being reported. The top 10 trades were 74% of
  the P&L; without the top 20 the mean was +2.5bp.
- **Fix.**
  - `fills.SimBroker`: a stop placed inside a bar uses the market price at placement (its `ref_price`, the entry
    fill). If that is already through the stop, it fills there at once.
  - `Order.stop_pct`: the plan's "10% catastrophe stop" is measured from the actual fill.
  - Regression tests for both. Lab-AY is re-run.
  - Rule: before reading any PASS, look at the top 20 trades and the mean without them.

## 2026-10-01 — Study Lab-AU re-tested an idea RESULTS.md already had dead
- **What happened.** The Stocks-in-Play 5-min ORB was in RESULTS.md's "Dead (do not redo)" table (negative
  gross, −12bp/trade, 10% win). The pre-registration checked only NEXT.md's dead-list table, which does not
  copy every RESULTS.md table. Lab-AU reproduced it (−13.5bp gross, conservative fills; ~+10bp gross even with
  optimistic fills, which is below costs).
- **Cost.** 2 variants of N (671 -> 673) and ~1.5 h of compute. No money.
- **Fix.** Before any pre-registration, grep RESULTS.md AND NEXT.md for the idea's keywords
  (`grep -n -i "<keyword>" RESULTS.md NEXT.md`) and say so in the registration.

## 2026-10-01 — per-trade replay statistics compounded one account (Study Lab-AU first run)
- **What happened.** The "unconstrained" per-trade run used one $10M account across all days, with no
  notional cap. AU's tight stops (10% ATR) sized positions huge, losses drained the account, and from
  2024 later trades rounded to 0 shares: H2 had 12 trades vs 5,700 in H1. The first Lab-AU verdict
  ("DEAD") was computed on that broken run.
- **Cost.** None; caught before any write-up, because the half counts were absurd.
- **Fix.** Statistics mode now gives every day a fresh account (`as_replay.replay`, `au_replay.replay`).
  Lab-AS was re-run the same way to confirm its numbers. Rule: always print trades per half before reading
  a verdict.

