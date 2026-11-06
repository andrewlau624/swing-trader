# VRP-POST (N 1076-1079, 2026-11-06): post-spike short-vol KILL; the VRP is not concentrated after spikes

- **Rule:** synthetic -1x (S1, SVIX/XIV-like) or -0.5x (S05, SVXY, Roth) 1-month constant-maturity VX ETP; armed after VIX >= 1.5x
  its 63d median, enter when F2 > F1 and VIX <= (1-X) x episode peak, exit on F1 >= F2 / H days / -30% loss cap / disarm, 1-day lag.
  Chosen X .20 H 21 on 2012-19 (Sharpe 1.30); judged 2004-11 + 2020-26.
- **Result (S1, 2x cost 20bp/side):** +4.9bp/in-day NW t 0.41; 14 judge episodes median -0.7%, 43% positive, ex-best-episode -53%.
  Post-spike in-position days +8.7bp vs ordinary judge contango days +18.6bp (Welch t -0.60, placebo 29th pct) - the prediction
  is wrong-signed. Account at w .62 (10% worst-day sizing from 2012-19): +2.4pp/yr 2004-11, +1.2pp/yr 2020-26, worst day -24%
  (2020-06-11), maxDD -53%. Roth -0.5x: +1.1 / -0.2pp/yr, maxDD -47%. DSR 0.002.
- **What works:** the F2 > F1 (front contango) filter keeps short-vol out of Oct-2008, Mar-2020 and Feb-5-2018 (first entries
  Dec-2008 / May-2020). It is crash avoidance, not alpha; Lab-BN already showed contango-gated SVXY does not beat SPY.
- **Data asset (reusable):** `research/sim/vrp_data.py` - Cboe CFE VX settlements 2004-2026 (archive `data/research/vrp/cfe/`
  CFE_{m}{yy}_VX.csv, expiries 2004-13, some with a disclaimer first line / trailing comma; per-contract `vx/VX_{expiry}.csv`
  2013+; pre-2007-03-26 prices are VBI = 10x), F1/F2 curve, SPVXSP-style synthetic r_long (corr VIXY .95 2011-17 / .985 2018-26,
  Feb-5-2018 +97%). Yahoo `^SHORTVOL` is NOT usable (flat on 2018-02-06 when SVXY fell -83%).
- Not tested: other spike thresholds; VIX-level or roll-yield-size entries; mid-term (VX4-7) short; exit on VIX normalisation;
  short UVXY/VXX with borrow; options (closed class).
- 2026-11-05: VIX 16.6 -> 28.2 (spike day; would arm an episode) - no action implied by this kill.
