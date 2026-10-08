# Shadow spec (DRAFT, not deployed): repeat-loser log on the night candidate list

Source: window-signal loop Round 6/8 (`research/drafts/window_signals_loop_2026-10-07.md`, L1).
Status: FORWARD CANDIDATE. Needs the user's OK before any server change; deploying it means a REGISTRY entry
in `swingtrader/daily/testing.py` in the same commit (CLAUDE.md rule).

- **What it logs (no orders):** at 15:40, for EVERY night candidate that passes the live rule (before dedupe, vol,
  cash and wash filters), one row: date, sym, repeat (= the symbol was a candidate in the prior 5 sessions), gap in
  sessions, price, vol20, day_ret. Outcome filled next morning from the official open (or the SIP open for names not
  traded): close(15:40 ref and official close) -> official open.
- **Gate (frozen):** after >= 150 repeat candidates: repeat minus first-time, night-paired, >= +30bp at the official
  crosses, t >= 2.0, both halves same sign; kill if <= 0 at 150. One read.
- **If it passes:** the action is a sizing tilt (repeat x1.5, capped by the existing name cap), Roth first (no wash
  sales), decided together with tilt v2 (addendum 23), never a new leg.
- **Why a candidate log, not fills:** repeats are ~5% of live fills (4/75 so far); logging candidates gives ~1-2/night.
