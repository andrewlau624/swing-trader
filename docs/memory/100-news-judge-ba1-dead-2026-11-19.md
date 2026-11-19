# LLM news judge BA1 (Study BA, N 689): DEAD, forward, read 2026-11-19

- Forward test 2026-10-01..2026-11-18: an LLM (OpenCode Go deepseek-v4-flash, then v4.1-flash from 11-09 after v4 was retired)
  labels each night pick's drop fundamental / liquidity / unclear at 15:40. BA1 = x0.25 on fundamental conf >= 0.7.
- 305 scored picks on official crosses: +1.39bp/night, NW t 1.33, sign-flip 83%, shuffle 28% -> DEAD. 93% of picks are called
  liquidity; the 13 "fundamental" picks earned +13.5bp, not a loss. The label does not find the falling knives.
- Ended: `daily.news_judge: off`, `RETIRED` in news_judge.py (module kept: sec_headers / _cik_map are shared), REGISTRY + digest rows gone.
- Lesson: the model switch went in without an amendment; a forced provider change mid-count must be logged as one.
- Not tested: different question, skip rule, IBS/PREF-EX picks, frontier model, other news windows, `unclear` (n 8, post-hoc).
