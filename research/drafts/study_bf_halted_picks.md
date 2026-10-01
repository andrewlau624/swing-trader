# Study BF (Round 28) — night picks that LULD-halted that day: DEAD (too rare) (N 719)

Pre-registration: `round1_prose.md` Round 28 (commit 214b606). Idea from the lab's halt studies (Lab-AY / Lab-BA:
after an inferred halt, big movers slide ~−130bp over 30 minutes). Data: free Alpaca SIP 1-minute bars 09:30-15:49
for every night pick 2021-26 (`research/sim/halt_study.py fetch`, 21 min); halt rule = the lab's (>= 5 silent
minutes right after a >= 5% 5-minute move), unit-tested (`tests/test_halt_study.py`).
Output `data/research/program/halt_study_out.txt`.

## Result
- **Coverage:** 100% of picks have minute bars. **Only 0.6% halted (53 picks), 0.4% on a down move.** The night
  leg's names fall ~8% steadily into the close and rarely trip LULD bands.
- **Per pick (2.5bp/side):**

  | | halted | down-halt | not halted | diff t |
  |---|---|---|---|---|
  | 2021-23 | −86.5bp (n 18) | −85.7bp (n 9) | +9.6bp | −0.77 |
  | 2024-26 | +35.7bp (n 35) | −42.6bp (n 25) | +6.7bp | +0.10 |

  Down-halts are bad in both halves, matching the lab, but on 34 picks in total.
- **Book:**
  - BF1 (drop halted picks): +0.6..+0.7pp/yr, both halves positive; t 0.5, placebo 65-67%, shuffle 80%, DSR 0.004.
  - BF2 (half weight): +0.3pp.
  - **Both DEAD.** Even if real, they would be worth < 1pp.
- **Not worth a forward watch.** At ~9 halted picks a year it would take decades to measure.
