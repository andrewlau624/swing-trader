# Contest hunt T7: EV2-big insider buy -> long call, open -> close — DEAD

Pre-registered `round1_prose.md` (8a3935e, N 800 -> 803). Runner `research/sim/contest_straddle.py` (`fetch7` / `run7`).
401 EV2-big events 2023-01..2026-09 (officer/director code-P >= $500k, no code-P filing for 730 days, raw prior close >= $5);
270 with a quoted call at the strike nearest the prior close and the earliest Friday / third Friday >= trade day + 5.
Buy on the 09:35 NBBO at the ask, sell on the 15:51 NBBO at the bid, $0.65/leg.

| | n | return on premium | median | win |
|---|---|---|---|---|
| select 2023-24 | 131 | **-28.7%** | | |
| judge 2025-26 | 139 | **-31.5%** | -34.6% | 18% |
Judge P(mean <= 0) 0.997, ex-best-5 -31.5%; every year -26..-49%. 3.3% of exits had no bid (counted 0); without them -27.6%.
Why: **the median 09:35 bid-ask spread on these names' calls is 23% of the ask**. Insider-buy names are small/mid caps
with thin chains; a +35-69bp underlying edge (x ~10 delta-leverage = ~5% of premium) cannot pay a 23% round trip.
Money table not run (per-trade gates fail by a mile).
