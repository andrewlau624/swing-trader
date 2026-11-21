# Kronos zero-shot and fine-tuned on night picks: DEAD (N 1232-1233, 2026-11-21)
- Kronos-small (HF 2025-06-30; pretraining to 2024-06). Tilt night picks by the forecast next open; judged 2025-09..2026-09, after release.
- Zero-shot: +6.6bp/night, t 1.00, second half ~0, placebo 87th. Fine-tuned on 2003-22 dip windows: val loss -7%, judge +4.4bp, t 0.60, placebo 75th.
- Lower token loss did not give better ranking. Direction hit is below the base rate of up nights. Consistent with the dead PATTERN/SEQ/MINPATH-NIGHT results.
- Repo, weights and cache are in data/research/exp_kronos (gitignored). Runner research/sim/exp_kronos.py.
- Not tested: base/large models, intraday/15:40 bars, full 30-epoch fine-tune, other targets, filter shape.
