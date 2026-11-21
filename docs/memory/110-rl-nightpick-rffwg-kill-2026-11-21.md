# RL night picker (N 1229) and RFF monthly market timing (N 1234): DEAD (2026-11-21)
- R4-PICK: PPO choosing within the night pool plus cash only matches the live leg. Judge 2013-20 +0.6bp/night t 0.43, placebo 52nd; worse on 2021-26. RL selection on the night leg is closed.
- RFF-WG: the KMZ "virtue of complexity" monthly timing has no edge after 2020. The paper-style form is real on 1960-2020 (alpha t 2.25), but its judge SR is -0.15 vs market +0.78. The registered 36m-sd standardisation was degenerate; that was a registration error.
- Bug: sel_night.py:244 adv column can be misaligned when dedupe drops names (research file only).
