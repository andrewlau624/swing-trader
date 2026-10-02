# Goal hunt log (`prompt_strategy_goal.md`, session llm-trader-ec)

## STATE (update every iteration)
- round 1 · ideas written 10 (G1-G10) · k (judged) 0 · program N 772 (G2 took 769-772; next free 773)
- running: `goal_g2 build` (2014-21 Form 345 -> EV2-big events 2016-21, counts only)
- track streak: T1 x1 (G2)
- NEXT: read the build counts; if the holdout has >= 100 G2 trades, run `goal_g2 judge` once (the one look) and write
  `study_goal_g2.md`. Then rotate to T5 (G1 contract stack) or T2 (G4 ADR terminations count).

## Notes carried in from other hunts (read 2026-10-02)
- Index-beat (llm-trader-ee): HAIRCUT: at edge-halves the live bot ~= SPY in both accounts; the only thing that beat the
  index at edge-halves was beta under the bot (R6-5 stacked on a SPY core, near miss). So any Goal book should be an
  overlay on an index core, not a replacement of it. No N registered there.
- EV2-big's >= $500k cut saw 2024-26; it can't be judged on 2024-26. Insider data here starts 2020-01 (events 2022+),
  so 2016-21 is untouched for every insider rule: that is the only honest holdout left for T1.
- llm-trader-3e's N = 593 message is stale (pre-Round 17); program N is 768 per llm-trader-51 / -ee.

## Log
- 2026-10-02 16:30 setup: read NEXT.md (dead list), prompt_hidden_edges.md, prompt_index_beat.md death map, EV2 study,
  index_beat_log STATE. Messaged all 6 peer sessions. Round 1: G1-G10 written before any outcome (T1 x2, T2 x3, T3 x3,
  T4 x1, T5 x1). Round quota so far: T1 2/8, T2 3/8, T3 3/8, T4 1/8, T5 1/4.
- 2026-10-02 16:45 G2 pre-registered (e6316e8, N 768 -> 772: G2a, G2b, two report rows). Correction to the
  registration text: "2016-20 has never been looked at for any insider rule" is not quite right: the Jump hunt's J2
  (insider buy after a 30% fall, +20% within 5 sessions) used 2016-23 insider buys on its select half. Different rule
  (conditioned on a crash, 5-day jump target), different exit; the EV2-big open->close rule was never computed on 2016-21.
  Using llm-trader-51's 2014-19 Form 345 zips (data/research/jump/insider/, read-only); my own duplicate downloads in
  night/insider were deleted so `outside_box.insider_buys()` (which globs that folder) can't change.
