# Noise leg one-run lag fix (2026-10-08) - branch noise-lag-fix, NOT deployed

## Evidence
Server logs (daily-live-*, daily-roth-*), every logged noise transition since 09-28:
a decision labelled HH:00 / HH:30 (bar start, = backtest m) is logged at HH:31 / HH+1:01,
e.g. "10:30 px ..." at 11:01 ET (15:01 UTC), "10:00 ..." at 10:31, "12:30" at 13:01 (17:01 UTC),
"13:30" at 14:01. 100% of transitions are one run (30 min) late; none logged at the HH:01 run
right after their bar. Backtest/shadow decides on C[m] and fills at that price.

## Root cause
executor.py `_intraday_one` (and `_conviction_one`) used `last_done = last_minute - 1`
("current minute is still forming"). At the 10:01 run the newest IEX bar is the 10:00 bar
(last_minute=30), so last_done=29 and m=30 waits; it runs at 10:31 (last_minute=60, last_done=59).
The guard dates to the original daily-cadence commit 452718e (no later rationale in git log).
But at HH:01:2x the 10:00 bar (10:00:00-10:00:59) is already closed; the -1 is only needed when the
run lands inside the newest bar's minute. Replay: lag costs ~1.2bp/trade of ~3.6bp.

## Fix
`_last_done_minute(mins, today, now)` in executor.py: newest bar counts as final once
now >= bar start + 60s + 3s grace (BAR_GRACE_S), else last-1. Used by both noise and
conviction loops. Timers (deploy/daily-trader.timer.in, HH:01 / HH:31) unchanged: the HH:01 run
now decides the HH:00 bar, which is exactly the backtest bar.
Test: tests/test_daily.py::test_noise_decides_the_bar_that_just_closed (10:01:20 -> m=30,
10:31:20 -> m=60, 10:00:30 -> 29, past day -> 389). tests/test_daily.py: 100 passed.

## Risks
- Incomplete bar: if IEX serves the just-closed minute late/partial at :01:20 the decision uses a
  slightly stale close. Grace is 3s on a run that starts ~20s after the minute; the old code had
  the same exposure one bar later. Check first live logs: px in the log vs SIP close of that minute.
- Missing IEX bar (thin minute): last_minute stays earlier, so the decision for m is skipped to the next
  run with ffilled close (same as before; no regression).
- IEX vs SIP: bands/backtest use SIP, live uses IEX closes; unchanged by this fix.
- Earlier fill raises order timing exposure: positions now change ~30 min sooner; Roth TQQQ/SOXL
  (long-only, no margin) path uses the same function, nothing separate. `_sync_noise_live` takes
  c[last_done], i.e. now the freshly closed bar's price, consistent with decision price.
- Not tested against real Alpaca latency; unit test pins only the index arithmetic.

## Deploy (user decision)
Review diff on branch noise-lag-fix, merge, `git pull` + restart on him (daily-trader.service picks up
code per run), watch the next session's [noise] lines: transitions should log at HH:01/HH:31 with
the HH:00/HH:30 label of the same hour. Roll back = revert the commit.
