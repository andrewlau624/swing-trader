# Study Lab-AY — buy the reopening after a LULD-style halt: DEAD, both variants (program N 697 -> 699)

Stamp: `round1_prose.md` Lab Round 23 (commit 7dcf193); plan `daytrade/plans/halt_resume.md`. Script
`daytrade/research/ay_replay.py` (the lab's `HaltResume` code; halts inferred from 5+ silent minutes after a ±5%
5-minute move, active names; Lab-AX's big-mover stock-days, 2022-01 to 2026-09).

**The first run showed a false PASS for Lab-AY2** (+757bp/trade, t 3.9). It came from a fill-model bug: a stop already
through the market filled at the stop price (MISTAKES.md). Fixed in 73ef35e, with the stop measured from the fill as
the plan says. These are the corrected numbers.

| variant | n | gross bp | 1x net (median) | win | t | 1x H1 / H2 | 2x H1 / H2 | placebo pct |
|---|---|---|---|---|---|---|---|---|
| Lab-AY1 buy after halt UP | 1,153 | **−126** | −166 (−801) | 32% | −4.2 | −122 / −195 | −175 / −228 | 0 |
| Lab-AY2 buy after halt DOWN | 1,186 | **−140** | −180 (−676) | 35% | −5.0 | −210 / −163 | −248 / −201 | 0 |

- Robust to outliers: winsorized 1/99, −174 / −187bp. Each variant has ~550 stop exits at −10%.
- Placebo: a random 30-minute hold on the same names earns +112bp on halt-up days (look-ahead: these names close
  up big) and −59bp on halt-down days. The post-halt 30 minutes are much worse than a random 30 minutes.
- **Reading: after a volatility halt in either direction, these names drift DOWN over the next 30 minutes.**
  - The long side is dead.
  - The short side is the open question: Study Lab-BA, pre-registered separately, with SSR and borrow as the
    real constraints.
