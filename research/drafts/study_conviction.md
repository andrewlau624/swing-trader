# Study CC — Conviction Concentration / Leverage (RGTI level test)

**Status:** PRE-REGISTERED, one look, exploratory. NO DEPLOYMENT, NO MARGIN CHANGES, NO LIVE TRADES.
Registered 2026-10-05 before any return conditioned on the band was read (only RGTI's date range,
schema, and the no-split check were inspected). Program N 820 -> 821.

Motivation (user): test whether instrument-specific setups exist whose conditional next-day
distribution is strong enough that concentrating capital or using moderate leverage materially
raises profit-generation capacity. Motivating example: *"RGTI around \$14-\$16 has historically
produced a strong next-day bounce."* The question is whether the conditional distribution is strong
enough to justify further consideration — NOT whether the claim is true or guaranteed.

## Frozen rule (does not move after any result)

- Instrument: RGTI only (Rigetti Computing, NASDAQ). Verified no splits/dividends: raw == adjusted
  for all 1,361 rows (raw/adj ratio 1.0000), so level tests need no adjustment.
- Data: `data/cache/bars/RGTI.parquet` (daily OHLCV). 2021-05-04 .. 2026-09-21, 1,268 sessions.
  Cross-checked against `data/research/night/raw_close.parquet` (1,361 rows, 2021-04-22+).
- Signal day d: `close(d)` in **[14.00, 16.00] inclusive** (raw, unadjusted).
- Liquidity floor: trailing-20d median dollar volume (close x volume) >= **\$5M** (excludes the
  2021 SPAC doldrums). RGTI's active-period ADV is far above this.
- Entry: **open of d+1** (no close lookahead).
- Primary exit: **close of d+1** (the "next-day bounce", one session). Max holding = 1 session.
- Costs: `book.cost_bps` model `tier` and `tier_hi`, both sides (round trip = 2x per-side). For
  RGTI $10-20 the tiers are 10 and 15 bps/side. Also report "+tick".
- Consecutive signals: primary counts **every** qualifying day as an independent signal (overlaps
  allowed). Report-only subset: "fresh cross" = first day the close enters the band after being out.
- Position sizing (unlevered): 100% of the sleeve on a single signal day (concentration is the
  question). No leverage in the primary.

## Judged primary (one look, all 1,268 sessions)

`excess = mean(net_ret | close in band)  -  mean(net_ret | all liquid days, same costs)`

where `net_ret = close(d+1)/open(d+1) - 1 - 2*cost_bps("tier", open(d+1), adv20(d))/1e4`.

- **PASS (VALIDATED):** conditional net mean >= +50bp AND > unconditional net mean AND positive in
  both 2021-23 and 2024-26 AND ex-best-5 positive AND still positive at `tier_hi`.
- **PROMISING:** net mean > 0 but exactly one gate fails.
- **REJECTED:** net mean <= 0, or not positive in both halves, or ex-best-5 <= 0.
- **SMALL / NON-SCALABLE:** statistically real but the dollar capacity at $2-25k is negligible.
- **DATA-LIMITED:** if the strict untouched judge cannot be formed.

## Untouched judge (honest limits)

The band \$14-\$16 is **given by the user with hindsight** (RGTI trades ~\$16 in Sep-2026), so no
split makes it out-of-sample. The judge is therefore: freeze the band, run once, and rely on
(1) conditional-vs-unconditional, (2) the band placebo, and (3) the chronological split. The
chronological split (2021-23 vs 2024-26) is *not* a clean OOS because the band came from the full
chart; it is reported as within-regime stability only. A future forward shadow would be the only
clean OOS.

## Artifact controls (pre-specified)

- **B — level vs generic oscillation:** apply the identical rule to pre-set equal-width bands
  [8,10],[10,12],[12,14],[16,18],[18,20],[20,22]. If all bands bounce similarly, the level is not
  special (it is RGTI's volatility/mean reversion).
- **C — regime:** per-year net mean; 2021-23 vs 2024-26.
- **D/E — selection/hindsight:** flagged; the band is hindsight-chosen. Placebo entry = random
  liquid RGTI days, 2,000 draws, same horizon/costs, to get the null distribution of the mean.
- **F — hidden exposure:** regress the same-window trade return on SPY and QQQ open(d+1)->close(d+1);
  report beta and alpha. Also report RGTI's unconditional same-window return (the conditional is
  already measured against it).
- **Volatility:** net mean by trailing-20d realized-vol tercile.
- **Prior move:** net mean by day-d return bucket (is it just "after a down day"?).
- **Earnings/news:** no point-in-time earnings calendar on disk for RGTI -> DATA-LIMITED, noted.
- **Gap risk:** distribution of open(d+1)/close(d)-1 for signals (worst overnight gap).

## Leverage (secondary, modelled only if the primary is at least PROMISING)

Report 1x/1.5x/2x/3x/4x: financing at 8%/yr on the borrowed fraction, Reg T 50% initial / 25%
maintenance, forced liquidation flag, worst day, max drawdown, and P(ruin) on the signal-day
equity path. Only RGTI signals exist, so the two-simultaneous-conviction correlation question is
N/A here.

## Search expansion (only if RGTI survives)

Pre-specified classes (NOT run now): recurring oversold levels, large one-day drawdown -> next-day
reversal, gap-down -> open-to-close recovery, volatility-shock overnight reversal, post-event
dislocations, distance from VWAP/mean. Do not brute-force arbitrary thresholds.

## Runner / output

`research/sim/conviction.py` -> `data/research/program/conviction_out.txt`. One look. If the
primary FAILs, the branch stops: no search expansion, no leverage study, no deployment.

## Hard rule

Never "guaranteed". Standard: high conditional probability + positive EV + controlled tail risk +
sufficient liquidity + reproducibility + capacity.
