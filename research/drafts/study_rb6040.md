# Study RB6040: month-end 60/40 rebalancing as a SPY/IEF relative-value trade — ARTIFACT (registered statistic), executable effect weak and absent after 2015

Pre-registered `round1_prose.md` "Study RB6040" (commit e2c4aed, 15:48 PDT; N 816 -> 817). Runner
`research/sim/rb6040.py`; one look `data/research/program/rb6040_out.txt` (15:51; an earlier attempt crashed in the
final capacity block before printing or writing anything; all inputs deterministic, placebo seeded). Post-hoc
diagnostics `data/research/program/rb6040_diag_out.txt`.

**Mechanical result of the registered rule: "VALIDATED"** (AP net +114.2bp/window, t 4.63, all return and mechanism
gates, placebo 99th pct). **Overruled: the registered primary statistic is a construction artifact.**
- AP subtracts 3 x each leg's mean daily return over the month's OTHER sessions. For a window ending on T, those other
  sessions are exactly the month-to-date sessions that define the signal s. With direction -sign(s), the adjustment
  adds roughly 3 x |MTD spread drift| to every month: **+87.3bp of the +125.9bp gross AP (69%) is the adjustment term**.
  The same bias explains the placebo windows' +50bp mean and contaminates the registered mechanism gates (the dose
  slope and |s| terciles use the same abnormal spread). TME is unaffected (its signal is calendar-only).
- Executable P&L (raw, what an account earns): **+26.9bp net per window, median +13.3, t 1.16, hit 54%; ex-best-5
  +1.7bp; 2016-26 (touched) +1.7bp (t 0.08).**
- What survives on raw returns (post-hoc, can only lower confidence): direction/dose is real in-sample — raw spread on s
  -56bp per 1 sd (t -2.43); raw net by |s| tercile -9.9 / +26.1 / +64.4bp; raw mean at the 96th pct of random-window
  placebos. Reversal T -> T+2: -25bp (t -1.0, partial reversal in the predicted direction).
- 2021 Agg pricing-time natural experiment (day T, raw, signed; n 60 pre / 68 post): IEF 15:00 -> close moved AGAINST
  the predicted flow before 2021 (-3.7bp, t -5.0) and with it after (+2.1bp, t 1.2); IEF close(T-1) -> 15:00 ~0 in both.
  The last-hour flip is what a 15:00 -> 16:00 pricing move predicts, but the absent pre-15:00 pressure is not.
  Mixed, small, report-only.
- Capacity (if it were real): the IEF leg binds (h ~2.25): $10M was 41% of 3-session IEF volume in 2005, 4% in 2015,
  1% in 2025; futures (ZN) would be the vehicle above ~$10M.

**Classification: ARTIFACT** (registered statistic, construction). The executable stock/bond spread is at most
INTERESTING in 2002-15 (mechanism-consistent dose response, but t 1.16, carried by a few months) and absent in 2016-26
(DECAYED or never tradable after costs). Relationship to TME: corr -0.09; the unsigned bond strength in the window
(+37.7bp, t 2.2) is the TME effect itself.

**Program lesson (method bug class):** never benchmark an event window against the same month's other sessions when the
signal is built from those sessions. Use a pre-period or unconditional benchmark, and always gate on the executable
raw P&L as well as any abnormal statistic. Do not re-register month-end rebalancing variants.
