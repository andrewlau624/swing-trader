# Research memory — REV-TONE (2026-10-16, N 1008): Amazon review tone, KILL

- Jin (2023 JBFA) review-tone replication on 20 Amazon-heavy consumer firms (McAuley Amazon Reviews 2023 via HF, streamed
  and filtered by `store`; live Amazon review pages need sign-in). 1.99M reviews scored with cardiffnlp roberta sentiment.
  dTONE (YoY) predicts neither sales acceleration (t -0.7), EA CAR (t -0.5) nor a hold to EA+1 (top-bottom net +63bp t 0.5,
  ex-top-5 negative); the 2014-18 paper era is null too. Tone ~ stars (corr 0.97). The "tone called Nike's fall" story is
  hindsight: tone fell in all 20 firms 2015-23 (platform drift), Nike's mid-pack, and it bottomed in 2021 at the stock's peak.
  Data/code: `data/research/reviews/`, `research/sim/rev_tone.py`, `research/sim/rev_tone_build/`. Do not re-open review
  sentiment without a per-product sales panel or a cross-section of hundreds of firms.
