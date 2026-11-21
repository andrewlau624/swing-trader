# RL on stock/sector universes D2a-d (N 1219-1222): KILL, judged 2011-20, 2026-11-20
- PPO over 10 ranked slots + cash: week winners, vol top, day losers (close->close), sectors. Benchmark EW basket of the slots.
- Agent alphas +3.3 / +1.1 / +0.7 / -0.8bp/day, no seed at t 2. RL learns only to dodge the worst slots.
- Side observation: the top-10 5-day winners basket lost ~8bp/day in 2011-20 -> WEEKWIN-SHORT pre-registered on 2003-10.
- Not tested: shorts, close->open, longer training, reservoir obs.
