# Research memory — session "futures roll" (2026-10-04, part 10)

Study FUT-ROLL (`research/sim/fut_roll.py`, pre-reg `study_fut_roll.md`). Data: Databento `GLBX.MDP3`
`ohlcv-1d`, individual contracts 2011-2025 for ES/NQ/CL/NG (~$0.02/root-year; the parent also publishes
the actual calendar-spread instruments, e.g. `ESH0-ESM0`). Spread S = F1-F2, LTD = last day a contract
is front.

- **Mechanism is real in equity-index futures.** Rolling institutions vacate the front: the front
  contract's volume share falls monotonically 0.48 -> 0.37 into LTD (ES/NQ), then jumps back to ~0.59.
  Spread daily volatility in the roll window is **3-4.6x** the baseline for ES/NQ. So scheduled roll
  pressure exists and is measurable.
- **The tradable distortion is small and decaying.** Short-spread (short front/long back) into LTD:
  ES +16.6bp t 2.0 (but 2011-15 +21.9 t 1.66, 2016-20 +19.0 t 1.34, **2021-25 +1.3 t 0.14**);
  NQ +8.2bp t 0.97 (**2021-25 +3.0 t 0.16**). CL sign-unstable. NG has the **opposite** sign (-94bp).
  One-tick round trip is only ~1-6bp, so cost is not the killer — the effect itself has decayed to ~0.
- **Verdict: ARTIFACT-ADJACENT / INTERESTING, not RESEARCH.** A genuine mechanism (roll migration) with
  a real but small spread effect that has been **arbitraged away in ES/NQ since ~2021** and is
  contract-specific (NG reverses). Equity-index rolls were the right mechanism example but are now
  too crowded; commodity "roll" is carry/seasonality, not the same forced flow.
- **Spread liquidity (capacity):** the published ES calendar spread instruments trade heavily in the
  roll weeks (multi-million contracts/day on the active spreads) — capacity is NOT the constraint.
  The constraint is that the edge is gone.
- **Did futures fail, or just roll pressure?** Not settled. Roll *pressure* is arbitraged, but the
  futures universe is still largely unsearched for other structural mechanisms (settlement/SOQ,
  first-notice/warehouse flows in commodities, futures-based volatility-target/CTA repositioning,
  cross-asset basis). Recommend pivoting to those, not to more roll variants.
