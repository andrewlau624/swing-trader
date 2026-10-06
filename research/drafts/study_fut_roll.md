# Study FUT-ROLL: futures calendar-spread distortion at the scheduled roll (pre-registered 2026-10-04)

Free/low-cost data. Mechanism probe, before reading any outcome.

## Mechanism
Beta/passive futures holders must roll: they sell the expiring front contract and buy the next one
in a scheduled window (equity-index: the week into the 3rd-Friday expiry; energy: the week into the
~3rd-business-day-before-the-25th expiry). This is mechanical, calendar-known **front-selling /
back-buying**. If the roll pressure is not fully anticipated, the calendar spread (front - back)
should *weaken* into the roll and recover after it.

## Data
Databento `GLBX.MDP3`, schema `ohlcv-1d`, parent `ES.FUT`/`NQ.FUT`/`CL.FUT`/`NG.FUT`, 2011-2025.
`symbol` is the OSI-style CME code: root + month-code + year. The parent also publishes *calendar
spread* instruments (e.g. `ESH0-ESM0`) with their own OHLCV — these are the actual tradable
spreads and are preferred over a synthetic subtraction.

## Rule (frozen)
1. For each root, take the two nearest contracts by expiry at each date; call them F1 (front) and F2.
2. Roll window: the last **5 trading sessions** before F1's **last trading day** (LTD), by expiry.
   LTD is the equity-index 3rd Friday, energy ~3 business days before the 25th of the prior month —
   approximate mechanically as the last date F1 has volume, which is set by the exchange, not by us.
   **Do not tune this window.**
3. Calendar spread S = F1_close - F2_close (synthetic) AND the published spread instrument where
   present. Normalize by F2 price (percent) and by F2 daily volatility (z).
4. Event study: t = LTD. Mean spread change over [t-5, t], [t, t+5], and the whole [t-5, t+5];
   compare to the same window shifted to placebo dates.
5. Costs: assume 1 tick on each leg (ES 0.25 pt = $12.50; NQ 0.25 = $5; CL 0.01 = $10; NG 0.001=$10)
   plus half-spread; require the move to exceed the round trip.
6. Regimes: 2011-2015 / 2016-2020 / 2021-2025; bull/bear; exclude the covid 2020-03 window.

## Kill
No sign-stable, mechanism-timed spread move that survives one round trip = KILL. Distinguish:
ARTIFACT (stale settlement / spread instrument not tradable), INTERESTING (real but < costs),
RESEARCH (mechanism + executable), HIGH-UPSIDE (also capacity).
