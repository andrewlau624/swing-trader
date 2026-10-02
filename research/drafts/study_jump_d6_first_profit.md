# Study J1 (jump hunt idea D6): first profitable quarter after >= 6 losing quarters — DEAD (judge half)

Session llm-trader-51, 2026-10-02, `prompt_jump_hunt.md`. Pre-registered in `round1_prose.md` (Amendment — Jump hunt,
Study J1; program N 760 -> 761). k = 1 (first judged idea of the hunt).

**Rule:** XBRL companyfacts NetIncomeLoss, ~90-day quarters, earliest filing per quarter end; event = first positive
quarter after >= 6 consecutive negative reported quarters; fd = that 10-Q/10-K's filing date; 20-day ADV$ < $20M.
Buy the next open, hold 60 sessions (`jump_runner`, ADV-tiered costs). Builder `research/sim/jump_d6.py`.

| window | line (as printed) | verdict |
|---|---|---|
| select 2016-23 | `hold60 n 299 (37/yr) jump 25.8% vs base 20.5% (x1.3) mean net +7.3% ex-top3 +4.5% median -0.6% vs stock's usual +7.2% hit 49% worst -84% best +409% P(mean<=0) 0.00` | ride MEETS |
| judge 2024-01..2025-06 | `hold60 n 48 (24/yr) jump 33.3% vs base 21.7% (x1.5) mean net +5.5% ex-top3 -1.8% median +3.3% vs stock's usual +3.7% hit 52% worst -81% best +142% P(mean<=0) 0.21` | **RIDE VERDICT: DEAD** |
| confirm | not run (judge failed) | — |

**Why it died:** LOTTERY. The centre of the distribution moved the right way in the judge half (median +3.3%, 52% hit,
+3.7% over the stock's usual), but three trades carry the mean (without them −1.8%), and 48 trades a year and a half
is too few to tell +5.5% from 0 (P 0.21). The select half was also flattered by survivorship (63-70% of 2016-18
events mapped to a ticker vs ~90% recently) and by small-cap timing (year means −8% .. +42%), both stated before the
judge.

**Money if it had passed:** not computed (dead).

**Do not redo:** the same rule with other streak lengths, holds, or a ride/trail exit is a re-test of a judged idea.
