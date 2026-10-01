# Study BC (Round 25 / 25b) — the LLM news judge on past picks: DOES NOT RUN (probe void; cutoff too late)

Pre-registration: `round1_prose.md` Round 25 (84f1ea3) and 25b (5698028). Script `research/sim/news_judge_hist.py`.
Model: OpenCode Go `deepseek-v4-flash` (served as `deepseek-v4-flash`).

## Probe v2 output (2026-10-01, one call, verbatim)
    [2024-11] Who won the November 2024 US presidential election?                    -> donald trump  ok
    [2025-01] Which Chinese AI lab's model release made Nvidia's stock fall about 17 -> deepseek  ok
    [2025-04] What name did the US administration give to its April 2, 2025 tariff a -> liberation day  ok
    [2025-05] In which city did US and Chinese officials agree in May 2025 to cut ta -> geneva  ok
    [2025-06] Which country's nuclear facilities did the United States bomb in June  -> iran  ok
    [2025-07] Which company became the first to reach a $4 trillion market value, in -> nvidia  ok
    [2025-09] What did the Federal Reserve do to its policy rate at its September 20 -> cut by 25 basis points  ok
    [2025-10] What started in the US federal government on October 1, 2025?          -> government shutdown  ok
    [F] Which streaming company did Apple acquire in March 2025?               -> roku  <- HALLUCINATED A NON-EVENT
    [F] Which company replaced Tesla in the S&P 500 after Tesla was removed in -> unknown
    probe VOID: the model invents answers to fabricated events; the historical test does not run.
(Probe v1, true/false/unknown, had answered "unknown" to all 12, including the 2024 election: Round 25b.)

## Verdict: BC does not run (two independent reasons, both pre-registered)
1. **Void:** a fabricated control got a named answer ("Roku").
2. **Cutoff not placed:** the model answers the latest probe (2025-10). Its knowledge reaches at least late 2025,
   so every 2025 pick is inside its memory. A public issue claiming this ID serves DeepSeek V3.2 with a
   2025-05 cutoff is contradicted by this probe.

The ~100-300 historical verdicts collected before the probe ran (from 2025-08-01) are not scored. The
clean window, if any, lies in 2026 and is too short to reach 300 picks before the data ends (2026-09-18). A
later-dated probe would need new registration and cannot fix the sample size.

## What it leaves
- **Study BA (forward, Round 23b) is the only valid test of the judge.** Each verdict is made at 15:40 on the
  day, so no model can know the outcome. Verdict read once at 300 picks.
- **The hallucination ("Roku") is a caution for BA:** the judge reads supplied news, but with an empty
  input it may still "fill in" a story. The prompt says to decide from the provided text only; BA's
  per-verdict scoring will show whether its labels carry information regardless.
