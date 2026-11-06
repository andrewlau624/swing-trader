# VIX-ETP rebalance flow (2026-11-06, no N): CEILING-KILL

- Forced flow L(L-1) x AUM x r at the 16:15 settle: UVXY 1.5x / SVXY -0.5x factor .75, SVIX -1x factor 2. Post-2018 combined AUM
  ~$2-3B -> ~$0.25B per 10% VX move vs ~$5B/day VX notional (~5% of volume; the pre-2018 XIV-era flow was far larger).
- Ceiling at $10k: ~10 events/yr (|r_long| > 10%) x ~1% next-day instrument move x ~0.3 deployable (10% worst-day cap on
  30-60% daily movers) x 50% capture = ~1.5pp/yr, far below +8pp.
- Unregistered descriptive on the synthetic VX series (`research/sim/vrp_data.py`): next-day mean after |r_long| > 10% up-days
  +0.18% (2006-11), +1.92% (2012-18), -0.86% (2018-26); medians -2.1..+0.8 - sign flips by era, no stable reversal/continuation.
- Not tested: intraday 15:45-16:15 VX pre-positioning (needs CFE intraday), AUM-scaled flow, ETP NAV premium on rebalance days.
