# Studies J3 / J4 (jump hunt ideas R4-5 / R4-6): 8-K "strategic alternatives" with a financial advisor / with confidentiality agreements — both DEAD (judge half)

Session llm-trader-51, 2026-10-02, `prompt_jump_hunt.md`. Pre-registered in `round1_prose.md` (Amendment — Jump hunt,
Studies J3 and J4; program N 762 -> 764). k = 4 after these.

**Rules:** EDGAR full-text search on 8-Ks: J3 `"strategic alternatives" "financial advisor"`, J4 `"confidentiality
agreements" "strategic alternatives"`; first per company in 365 days; fd = file date; 20-day ADV$ < $20M. Buy the next
open, hold 20 sessions (`jump_edgar.py`, `jump_runner`).

| study | window | line (as printed) | verdict |
|---|---|---|---|
| J3 | select 2016-23 | `hold20 n 155 (19/yr) jump 14.2% vs base 8.8% (x1.6) mean net +3.5% ex-top3 +1.1% median -0.5% vs stock's usual +4.4% hit 47% worst -55% best +149% P(mean<=0) 0.04` | ride MEETS; same-day control +4.4% (P 0.004) |
| J3 | judge 2024-01..2025-06 | `hold20 n 54 (27/yr) jump 9.3% vs base 8.1% (x1.1) mean net -1.7% ex-top3 -6.3% median -2.5% vs stock's usual +1.7% hit 33% worst -40% best +106% P(mean<=0) 0.71` | **RIDE VERDICT: DEAD** |
| J4 | select 2016-23 | `hold20 n 24 (3/yr) jump 20.8% vs base 8.0% (x2.6) mean net +6.0% ex-top3 +1.7% median +3.5% vs stock's usual +6.9% hit 62% worst -30% best +41% P(mean<=0) 0.04` | jump MEETS; control +4.9% (P 0.057) |
| J4 | judge 2024-01..2025-06 | `hold20 n 7 (4/yr) jump 0.0% vs base 4.5% (x0.0) mean net -4.9% ex-top3 -9.2% median -0.7% vs stock's usual -3.0% hit 29% worst -22% best +3% P(mean<=0) 0.96` | **JUMP VERDICT: DEAD** |

**Why they died:** LOTTERY. The select-half edge was a right tail of completed sales (median difference vs the control
~0); in 2024-25 the tail did not show up (J3: 1 in 3 profitable, median -2.5%), and J4 had 7 trades. Passing a
same-day control on select did not make the tail repeat.

**Do not redo:** other phrases for the same sale-process footprint (banker hired, NDAs, special committee, retention,
CIC severance, pills: R4-1..R4-4 also dead on select).
