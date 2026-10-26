# Research memory — session "derivatives frontier: futures/options as infrastructure" (2026-10-06)

User directive: futures/options as a NEW frontier, mechanism-first, no brute force, NO data buys
($180 signed-gamma NOT funded). Three pre-registered studies (round1_prose.md; runners
research/sim/{cotx,cbas,vts}.py; outputs data/research/program/*_out.txt), ALL KILL; program
N renumbered to 866 (multiple parallel-session collisions: PAIR-CLASS/SSR-LIFT/PREF-EX consumed
857-861; canonical numbering now COTX 862, CBAS 863, VTS 864).
- **COTX (N 862) KILL:** CFTC COT weekly positioning state (free Socrata API: TFF + disaggregated;
  leveraged funds/dealers/asset managers, 9 products, 2006-2026, cached data/research/cot/) — no
  tradable 1-2wk footprint in any frozen arm (t 0.25..1.40, wrong signs, halves flip). The
  participant-state information that exists ONLY in CFTC data is invisible to P&L at weekly tier.
  CL/NG series end 2022-02 (CFTC dataset split; not the cause of the null).
- **CBAS (N 863) KILL + mechanism finding:** daily ES/NQ cash-futures basis (front close vs
  SPY/QQQ raw close, z vs 21d med/MAD, roll5 excluded): retail spot legs net-negative BOTH
  directions next-day (SPY follows the futures-led move ~1 day, against convergence, cost-bound);
  3d arm t 1.47. **The persistent daily basis-dislocation regime does not exist 2011-2025** (after
  a |z|>=2 flag, median z_(t+1) ~ 0, only 14-26% still flagged) — the arb is never balance-sheet
  constrained for days at this frequency; the "hedged convergence t=18-24" is 2xMAD
  regression-to-median baked into the flag definition. Basis family closed at the daily tier.
  **DATA BUG FIXED: Databento GLBX daily bars are stamped by SESSION START (evening), not trade
  date — trade_date = next business day (research/sim/cbas.py::trade_dates). Any new consumer of
  data/research/program/glbx_*_daily.parquet must remap; old fut_roll/FND event-window verdicts
  are label-shift invariant and stand.**
- **VTS (N 864) KILL:** VIX term structure via Yahoo ^VIX9D/^VIX3M (the ONLY free options-family
  data; note Yahoo range=max silently returns MONTHLY bars — use period1/period2 interval=1d).
  Contango 5d +17bp t 5.5 = unconditional SPY drift (per-year +-5bp noise, not excess) — rejected
  as a sensor; inversion arm wrong sign (market relief-bounces; short loses both halves). The
  unregistered MIRROR (LONG after inversion, ~+59bp/5d excess, 11% of days, overlapping windows)
  is an observation/forward-shadow candidate only, NOT a PASS.
- **META ANSWER (user question 12): NO.** Free derivative data (positioning, cash-futures basis,
  vol curve) reveals no harvestable forced behavior invisible in equity daily prices at this
  tier; each visible state is arbitraged flat, drift-only, or the wrong sign. What remains
  invisible-in-equity (OI by strike/signed gamma, margin-rate history, skew) is exactly the PAID
  tier, and its prior is now LOWER (OI-pin killed + these 3 kills). Do not fund automatically.
- **Data-limited (not tested, not rejected):** CME margin-hike forced deleveraging (no free
  historical margin-rate series; CME notices scrape is the spec; silver-2011 canonical), SOQ/
  expiration at minute tier (no power at daily), cross-contract spreads (generic-carry exclusion
  stands until a named constrained participant is written down).
- Derivatives share of the loop this session was ~100% by directive; the standing 60-70% rule
  resumes with the next session (open non-derivative ground per part 9-11 ledgers).
- **PREF-EX (preferred ex-dividend under-adjustment, N 860->861): STRONGEST small-account candidate of the clean-slate loop.**
  Buy the T-1 closing cross, sell the ex-date opening cross, collect the dividend: official crosses 2021-26 +38bp/event
  (median +35, t 20, every year), Sharadar 2005-26 22/22 years; drop ~0.8 x dividend (tax clientele, partial). Crosses
  print at the NBBO mid; quoted spreads (38/88bp) make it auction-only. Roth-only (dividend untaxed). Gross at a 10%
  participation cap: ~$840/yr at $3k, ~$1.6k at $10k, ~$2.4k at $25k; capital used ~128 nights/yr (stacks). Unverified:
  impact in thin crosses, broker MOC/MOO on preferreds, Roth T+1 settlement on back-to-back nights. Forward log-only, then
  a tiny live pilot (user decision). Common-stock ex-div capture stays dead (EXDIV-OPEN); this is a different class.
  Independent support: CEF ex-nights +13bp (drop 0.78), high-yield ETFs +17.5bp (drop 0.86), 2005-26, ~20/22 yrs each.
