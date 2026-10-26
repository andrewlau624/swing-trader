# Research memory - noise leg recent check (2026-10-08)

- `research/sim/noise_recent.py`, `research/drafts/noise_recent_2026-10-08.md`: QQQ+SMH PROD replay, post-2024-05 at 1bp RT: no-lag +3.65bp/trade (t 1.5, Sharpe 0.14), one-bar lag +3.14 (t 1.5, Sharpe 0.22); ~0 at 4bp RT; 2026 Jan-May negative (-0.2 / -1.1). Lag costs only ~0.5bp post-2024 (3.62 vs 2.31 pre), so the lag fix is nearly moot; the leg itself is marginal and cost-bound (user decision).
- Lagged replay reproduces live fills within a few bp (live is one bar late, confirmed); 7 live round trips so far: mean -14bp, median +3, too few to judge.
