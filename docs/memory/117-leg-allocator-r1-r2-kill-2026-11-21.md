# Learned leg allocation IBS/night/cash (linear, TS, PPO): DEAD (N 1225-1228, 2026-11-21)
- No variant beats live 0.5/0.5 or best-fixed on 2013-20. PPO 0/5 seeds; drawdown reward only de-levers.
- With R4 (night picker) and R5 (overlay) this closes "find an RL leg" on top of the existing legs: learned exposure control adds leverage, not timing.
- pool.map hang once (cause unknown); exp_legalloc now has a resumable EXP_LA_CACHE.
