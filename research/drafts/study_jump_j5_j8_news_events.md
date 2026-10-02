# Studies J5-J8 (jump hunt): buyback size, forward splits, upgrade clusters, big-target initiations — all DEAD (judge half)

Session llm-trader-51, 2026-10-03, `prompt_jump_hunt.md`. Pre-registered in `round1_prose.md` (Amendments — Jump hunt
J5; J6; J7 and J8; program N 764 -> 768). Builders in `research/sim/jump_news.py` (Alpaca/Benzinga headlines). Each
judge file was rebuilt on the archive through 2025-09 with `jump_rebuild.py`; all four select-half hashes MATCHED the
registered pins before judging. Every MEETS here had beaten the standing-rule same-day control on the select half.
k = 8 judged ideas in the hunt after these.

| study | idea / rule | select (only look) | judge 2024-01..2025-06 (as printed) | verdict |
|---|---|---|---|---|
| J5 | R2-25 buyback authorization >= 15% of market cap, next open gap < 3%; JUMP tp205 | `n 162 jump 6.2% vs base 2.4% (x2.6) mean net +2.1% ex-top3 +1.8% median +1.7% P 0.00`; control +1.9% (P 0.001) | `tp205 n 68 (34/yr) jump 8.8% vs base 1.8% (x4.8) mean net +0.8% ex-top3 -0.1% median +0.4% vs stock's usual +1.0% hit 56% worst -23% best +20% P(mean<=0) 0.23` | **JUMP VERDICT: DEAD** |
| J6 | S5 forward split announced; JUMP trail20 | `n 78 jump 9.0% vs 4.1% (x2.2) mean +2.2% ex-top3 +0.8% median +2.6% P 0.06`; control +2.0% (P 0.054) | `trail20 n 28 (14/yr) jump 10.7% vs base 5.8% (x1.8) mean net +2.6% ex-top3 -1.1% median -0.1% vs stock's usual +0.8% hit 50% worst -17% best +50% P(mean<=0) 0.16` | **JUMP VERDICT: DEAD** |
| J7 | R2-19 second upgrade within 10 days, small caps; JUMP tp205 | `n 277 jump 8.3% vs 3.1% (x2.6) mean +0.7% ex-top3 +0.5% median -0.1% P 0.09`; control +1.0% (P 0.021) | `tp205 n 25 (12/yr) jump 16.0% vs base 6.7% (x2.4) mean net +1.0% ex-top3 -1.5% median +1.7% vs stock's usual +1.5% hit 64% worst -24% best +20% P(mean<=0) 0.34` | **JUMP VERDICT: DEAD** |
| J8 | R3-15 initiation with a target >= 2x price, micro caps; RIDE hold60 | `n 140 mean +6.1% ex-top3 +2.7% median +1.0% P 0.05`; control +5.0% (P 0.079) | `JUDGE HALF: events 2024-01-01..2025-06-30 -> 0 trades` / `JUMP VERDICT: DEAD (no trades)` (the runner prints JUMP on an empty half) | **DEAD (no trades)** |

**Why they died:** the jump rates held up out of sample (J5 x4.8, J7 x2.4, J6 x1.8), but the means shrank and became
carried by their top three trades (ex-top3 -0.1% / -1.1% / -1.5%), on 25-68 trades: LOTTERY plus too few events to
separate +1% from 0. J8's headline format (initiation with a target in the headline) stopped appearing after 2020.
Confirm windows were not run (judge failed).

**Closest miss:** J5 (big buybacks, un-gapped): positive mean and median both halves, jump rate 2.6x then 4.8x the
stock's normal; dead on the ex-top-3 rule and P 0.23. At 10% per signal and +0.8%/trade, ~34 signals a year would be
~+$60 / $270 / $680 a year at $2.3k / $10k / $25k before tax, if it were real.

**Do not redo:** these rules with other thresholds (buyback % of cap, gap filter, split ratios, upgrade windows, PT
multiples) or exits — they were judged.
