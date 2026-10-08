# Window-signal loop (overnight /loop, started 2026-10-07)

User request: research technical-indicator WINDOW patterns (crosses, time in zone, divergences, squeeze
duration, histogram sequences) over multi-day horizons; alternate to a new family each time one dies.
Runner: `research/sim/winsig.py` (harness) + `research/sim/winsig_fam.py` (families). Exploratory program;
Program N bumps are listed per family below (to merge into round1_prose.md).

## Frozen gate (written before any family was run; identical for every family)
- Universe: Sharadar SEP common stocks incl. delisted, raw price >= $5, prior-20d $ADV >= $20M (~1,340 names/day).
- Signal on the close of day t from bars <= t. Trade: buy open t+1, sell close t+5 (primary; 1/3/10 diagnostic),
  total return. Excess = minus the equal-weight liquid-universe return over the same window.
- Cost 10bp round trip; shock 30bp. Stats: daily mean series by entry date, Newey-West t (lag = H).
- DISCOVERY 2016-01..2026-09 PASS needs ALL: net excess >= +25bp/trade, NW t >= 3.0 (multiple-testing bar),
  both halves > 0, median excess > 0, ex-top-5-days mean > 0.
- A discovery PASS gets ONE confirm look on 2003-2015 (untouched for these rules): net excess > 0 with t >= 2.0,
  then the +8pp/yr ceiling check (events/yr x net edge x deployable share). No parameter changes after a look.
- Kill = fail discovery. Killed families are not re-tuned; the loop moves to a different family.
- Delisted names exit at their last close (no delisting return): small optimistic bias, stated.

## Family queue (each fully specified before it runs)
F1 TTM Squeeze release: BB(20,2) inside KC(20,1.5xATR20) for >= 5 bars ending t-1, OFF at t, momentum
   histogram (20-bar linreg of close - mean(donchian mid, sma20)) > 0 and rising at t -> long.
   Control arm: same release with histogram < 0 and falling.
F2 TMO(14,5,3): main crosses above signal at t while main <= -10 (oversold cross) -> long.
F3 MACD(12,26,9): histogram turns > 0 at t after >= 5 bars < 0, with MACD line < 0 -> long.
F4 Stochastic(14,3,3): %K crosses above %D at t, both < 20, after >= 3 bars with %K < 20 -> long.
F5 Bollinger re-entry: close back above lower BB(20,2) at t after >= 2 closes below -> long.
F6 RSI(14) bullish divergence: low_t < min(low t-20..t-5), RSI_t > RSI at that prior low, RSI_t < 40 -> long.
F7 ADX trend pullback: ADX(14) > 25, +DI > -DI, close crosses above EMA20 at t after >= 3 closes below -> long.
F8 NR7 breakout: day t-1 is NR7 (narrowest range of 7) and inside day; close t > high t-1 -> long.
F9 OBV divergence: close_t is a 20-day low close but OBV_t is above its 20-day low -> long.
F10 Contraction breakout: BB width at t-1 is its 120-day low; close t > 20-day high (Donchian) -> long.
F11 Weekly MACD: weekly histogram (Fri closes) turns > 0 with weekly MACD < 0; enter Monday open, hold 5d.

## Results log
### Round 1 (F1-F11, liquid single stocks, long): ALL KILLED (Program N +11 exploratory, 11 families)
Full lines: `research/sim/winsig_out.txt`. H5 excess vs EW universe (bp/trade, gross), NW t, net of 10bp:
| family | n/yr | H5 gross | t | net | median | halves | verdict |
|---|---|---|---|---|---|---|---|
| F1 TTM squeeze release, hist>0 rising | 2790 | -7.5 | -1.8 | -17.5 | -11.0 | -16.6/-6.4 | KILL (wrong sign) |
| F1 control: release, hist<0 falling | 2314 | +5.5 | +0.8 | -4.5 | -4.9 | -4.7/+16.3 | KILL |
| F2 TMO oversold cross-up | 5285 | -0.4 | +0.2 | -10.4 | -10.5 | +14.7/-11.1 | KILL |
| F3 MACD hist turns + below zero | 7290 | -8.6 | -2.0 | -18.6 | -10.3 | -10.6/-13.8 | KILL (wrong sign) |
| F4 Stochastic cross-up < 20 | 9372 | +2.7 | +1.2 | -7.3 | -7.5 | +16.5/-0.7 | KILL |
| F5 BB lower re-entry | 5476 | +1.9 | -0.0 | -8.1 | -6.4 | +3.7/-3.9 | KILL |
| F6 RSI bullish divergence | 20331 | +12.3 | +1.6 | +2.3 | +1.5 | +17.2/+0.0 | KILL (closest; t<3, net<25) |
| F7 ADX trend pullback | 1118 | -19.0 | -0.8 | -29.0 | -23.9 | -21.8/+0.5 | KILL |
| F8 NR7 inside-day breakout | 6470 | -5.7 | -3.0 | -15.7 | -9.7 | -17.5/-9.9 | KILL (breakouts fade) |
| F9 OBV divergence at 20d low | 16277 | +8.5 | +2.0 | -1.5 | -0.7 | +16.1/+3.4 | KILL |
| F10 contraction breakout | 506 | -8.3 | -0.8 | -18.3 | -6.8 | -18.2/+1.0 | KILL |
| F11 weekly MACD turn | 1665 | -1.3 | +0.3 | -11.3 | -11.6 | +16.8/-12.0 | KILL |
Read: every classic window pattern on liquid single stocks is within +-20bp/5d of the universe, below a 10bp
round trip. Breakout/trend arms (F1, F3, F7, F8, F10) lean NEGATIVE (breakouts fade: consistent with the
book's reversal edges); oversold/divergence arms (F6, F9) lean slightly positive (+8-12bp) but far under the bar.
Class verdict: textbook TA window patterns as stand-alone long signals in liquid US stocks = DEAD. Next: change
the SHAPE (ETFs; thin names where small size is an advantage; breadth as a market-timing state; conditioning
the live IBS edge), not more indicator variants on the same universe.

## Round 2 queue (frozen before run; same gate, same harness unless stated)
G1 ETF universe: F1-F11 rules on SFP ETFs (non-leveraged, non-inverse, $ADV >= $20M), excess vs EW ETF universe.
G2 Thin names: F6 + F9 (the two positive-leaning arms) on raw price >= $5, $ADV $1-20M (small-account capacity),
   cost 40bp round trip (shock 100bp). Same pass thresholds on NET.
G3 Breadth timing: share of liquid stocks with TMO <= -10 (and, separately, in a squeeze); long SPY open t+1 ->
   close t+5 when breadth-oversold share is in its top decile of the trailing 252d; vs unconditional SPY.
G4 Conditioning the live IBS rule on ETF window state: IBS < 0.2 entries split by TMO oversold days (>=5/10),
   squeeze on/off, MACD hist sign; pass = one split beats the other by >= 15bp/trade with t >= 2.5, both halves.

### Round 2 (G1-G4): ALL KILLED (Program N +4 families; G1 = 11 rules x ETFs, G2 = 2 rules x thin)
- **G1 ETFs** (810 non-levered ETFs, ~209/day at $ADV>=$20M): all 11 rules fail; H5 excess -14..+4bp, none t>2 in the
  right direction; F1 squeeze release again NEGATIVE (-6.6bp, H10 -18.5 t -3.3). Patterns are no better on ETFs.
- **G2 thin names** ($ADV $1-20M, 40bp RT): F6 +10.6 gross -> -29.4 net; F9 -0.4 gross. Positive lean vanishes.
- **G3 breadth timing** (share of stocks TMO<=-10 / in squeeze, top decile of trailing 252d -> SPY next 5d):
  2016-26 excess +2.6bp (t 0.1) / +4.8bp (t 0.2). KILL. PROTOCOL SLIP: the runner also printed 2003-15 for both arms
  although the spec said "confirm only after a discovery pass" (os +25.3 t 0.9; sq -20.4 t -0.8). Both are null, but
  2003-15 is now TOUCHED for breadth-of-window timing; runners print the confirm window only after a pass from now on.
- **G4 IBS<0.2 on ETFs** (open t+1 -> open t+2, base +2.2bp excess / +9.3 raw), split by TMO oversold days, squeeze,
  MACD sign: paired differences +3.1 / -3.0 / -2.8bp, |t| <= 1.4. Window state adds nothing to the live IBS rule.
Read: the indicator state is information-free at every shape tried (stand-alone, ETFs, thin, breadth, as a filter).

## Round 3 queue (frozen before run): count/sequence and volume-signature windows (different mechanism class:
## exhaustion / capitulation, not oscillator state). Liquid stocks AND ETFs, same gate, long.
H1 TD Sequential buy setup: 9 consecutive closes < close 4 bars earlier, completed at t -> long.
H2 Selling climax: close-to-close <= -5% over 3 days, day-t volume >= 3x 50d avg, close in top 40% of day range -> long.
H3 Pocket pivot: up day, volume > max down-day volume of prior 10 bars, close above SMA50 -> long.
H4 Island reversal: gap down at t-k (k 1-5) left unfilled, then gap up at t above the prior island's high -> long.
H5 Heikin-Ashi flip: first HA green bar after >= 5 consecutive HA red bars -> long.
H6 Multi-timeframe on the live IBS rule (G4 gate): IBS<0.2 ETF entries split by weekly RSI(14) < 35 vs >= 35.

### Round 3 (H1-H6, exhaustion/volume-signature windows): ALL KILLED (Program N +6 families, 11 cells)
| rule | stocks H5 gross (t) | ETFs H5 gross (t) |
|---|---|---|
| H1 TD Sequential buy 9 | +6.9 (1.4), net -3.1, halves +24/-1 | +6.3 (-0.1) |
| H2 selling climax (vol>=3x, close top 40%) | -12.3 (-0.5), median -42 | -37.6 (-0.7), n 41/yr |
| H3 pocket pivot | -5.6 (-2.9) wrong sign | -2.9 (-1.1) |
| H4 island reversal | +10.5 (-0.5), median -0.1, halves both < 0 | +2.8 (-1.1) |
| H5 Heikin-Ashi first green after >=5 red | -8.8 (0.0) | -9.2 (-1.4) |
| H6 IBS<0.2 ETFs, weekly RSI<35 vs >=35 | paired -4.6bp (t -1.1), halves +2.0/-11.3 | |
Read: exhaustion counts and volume signatures are as empty as oscillators. Breakout-flavoured arms (pocket pivot,
F8, F1) are consistently slightly NEGATIVE (-3..-9bp/5d, t up to -3): a real but tiny "breakouts fade" tilt, far
below shortable size (ceiling at 10bp RT + borrow: < 0). Class closed: **daily-bar technical window patterns, all shapes.**

## Round 4 queue (frozen before run): switch class -> SAME-DAY windows (the opening gap) and vol-state windows.
Same gate numbers (net >= +25bp/trade, t >= 3, halves > 0, median > 0, ex-top-5 > 0); cost 5bp RT for auction-to-auction
ETF trades (measured live ~0bp), 10bp for stocks; shock 3x.
I1 ETF opening-gap fade: open_t / close_{t-1} - 1 <= -1% -> buy open t, sell close t (excess vs EW ETF open->close).
I2 Stock opening-gap fade: gap <= -3%, liquid stocks, same trade.
I3 Vol-compression: SPY/QQQ/IWM 5d realized vol / 60d realized vol <= 0.5 -> long open t+1 -> close t+5 vs unconditional.

### Round 4 (I1-I3, same-day gap windows + vol-state): ALL KILLED (Program N +3)
- I1 ETF gap <= -1% fade: open->close excess -0.2bp pooled, day-mean NW t **-3.6** (gap-down ETFs LAG the rest
  intraday: continuation, not fade), halves -4.9/-10.1. KILL (wrong sign; short side ~5-10bp, below cost+borrow).
- I2 stock gap <= -3% fade: +19.8bp pooled, day-mean t 0.5, halves +6.5/-1.5, ex5 -1.6. KILL (pooled mean = outliers).
- I3 vol compression (5d/60d <= 0.5) on SPY/QQQ/IWM: +2.7/+7.3/-3.6bp vs unconditional, |t| <= 0.6. KILL.

## Round 5 queue (frozen before run): switch class -> CROSS-SECTIONAL window ranks with a liquidity-provision
## mechanism (the one family the book's IBS/night edges belong to). Same gate.
K1 Industry-residual 5-day reversal: r5 (close t-5 -> t) minus EW r5 of the same Fama industry (liquid names);
   bottom decile each day -> long open t+1 -> close t+5. Liquid universe.
K2 Same with a 2-day window (r2), bottom decile.
K3 K1 restricted to $ADV $20-100M (mid-liquidity: capacity is not the user's constraint).

### Round 5 (K1-K3, industry-residual short-window reversal ranks): ALL KILLED (Program N +3)
- K1 resid r5 bottom decile: +8.6bp/5d (t 1.4), median -13.1, net -1.4. K2 (r2): +9.5 (t 1.8), net -0.5.
  K3 (ADV $20-100M): +7.5 (t 1.2). The textbook weekly-reversal premium survives at ~+9bp gross from a next-open
  entry: below a 10bp round trip.
- **Gap-location diagnostic (no gate, `winsig_gap.py`):** close t -> open t+1 excess for K1/F6/F9/H1/F1/H3/F8 is
  -0.4..+2.9bp. The window rules' small edges are NOT hiding in the overnight gap either (unlike the book's
  -8% / IBS edges, whose whole edge is the next overnight). So MOC entry would not rescue them.
Read after 5 rounds / ~45 rule-universe cells: daily technical window patterns and short-window rank reversal carry
<= ~10bp/5d of information in liquid US stocks/ETFs, at any entry. The book's edges exist only at EXTREME, forced
moves (-8% days, IBS<0.2 on ETFs), and their payoff is the first overnight. That is the class boundary.

## Round 6 queue (frozen before run): stay at the class boundary -> windows ON THE LIVE NIGHT EDGE'S OWN EVENTS
## (state gates on an existing edge; the only form left). Night-rule picks = nx daily-bar panel, 2016-26 (touched).
## Outcome: overnight close t -> open t+1 return of the pick, vs same-night other picks. Pass = split difference
## >= 30bp/trade, night-clustered t >= 2.5, both halves same sign, median difference same sign.
L1 Repeat loser: name also made the pick list within the prior 5 sessions vs not.
L2 Drop streak: pick closed down on each of the 2 prior sessions too (3-day slide) vs fresh drop after an up day.
L3 Sector crowding: >= 3 picks in the same Fama industry that night vs a pick alone in its industry (replaces a gap-share
   arm: gap share is already dead, add. 23). Direct test of the "sector cap" idea raised after the 10-06 gap night.

### Round 6 (L1-L3, windows on the night rule's own picks; nx daily-bar proxy, delisted-complete, 2016-26 touched)
n 10,693 picks / 2,097 nights, mean overnight +41.7bp (daily-close proxy; ~2x optimistic vs 15:40 per NX).
- **L1 repeat loser (picked <= 5 sessions earlier): PASS-WEAK (letter of the gate), FORWARD CANDIDATE.**
  A +67.6bp (n 1,674) vs B +36.9bp; night-paired A-B **+85.2bp, t 3.4**, halves +81.5/+88.9. Raw medians +41.0 vs
  +36.4 (+4.6bp, same sign; the registered "median of night-demeaned d" was degenerate: single-pick nights give d=0,
  so the raw-median reading is used and flagged). Hit rate LOWER (55.6% vs 57.2%). Ex-top-1% still A +34.9 vs B +10.4.
  A > B in 8/11 years (not 2019, 2021, 2023). Read: repeat losers carry a fatter RIGHT tail, not a better typical
  night. Overlaps the v2 night tilt (addendum 23: adds yesterday's return, "every year better but borderline"):
  L1 is independent, delisted-complete support for the same direction. Multiple testing: ~50th cell of this loop;
  t 3.4 survives a Bonferroni-50 bar only marginally (p ~0.03). 2003-15 is TOUCHED for the night leg (NX): no
  historical confirm is allowed -> forward shadow only. Note for taxable: a repeat loser re-bought within 30 days
  of a LOSS sale is a wash sale; the Roth is where a repeat-loser up-weight is clean.
- L2 3-day slide vs fresh drop after an up day: -24.3bp (t -1.0). KILL.
- L3 >= 3 picks in one industry vs alone: crowded picks +28.9 vs +38.4bp; paired +22.8 (t 0.9, sign flips vs the
  pooled means). KILL as a per-pick filter. Portfolio view: nights WITH a >=3 industry cluster have a LOWER night-EW
  sd (286 vs 361bp) and the same 5th percentile (-383 vs -380bp); worst night -1,099 vs -2,544bp. **A sector cap is
  not supported**: clustered nights are not the fat-left-tail nights in 10 years of history (10-06 was ordinary).

## Round 7 queue (frozen before run): repeat-event windows on the IBS ETF leg (the L1 analogue), G4 gate
## (paired difference >= 15bp/trade, |t| >= 2.5, halves same sign), open t+1 -> open t+2, liquid ETFs 2016-26.
M1 IBS<0.2 on day t AND on day t-1 (2nd consecutive signal) vs first signal.
M2 IBS<0.2 with >= 2 IBS<0.2 days in the prior 5 sessions vs none.

### Round 7 (M1-M2, repeat-signal windows on the IBS ETF rule): KILLED (Program N +2)
- M1 2nd consecutive IBS<0.2 vs first: paired -1.4bp (t -0.7). M2 >= 2 signals in prior 5 vs none: +1.8bp (t 0.8).
  The L1 "repeat" tail is specific to -8% single-stock losers; ETF IBS repeats carry nothing extra.

## Round 8 queue (frozen before run): FALSIFY the L1 lead (no new parameters; mechanism checks on the same picks)
Mechanism claim: a name still on the -8% list within days is under CONTINUING forced selling, so its bounce tail is fatter.
P1 dose-response: gap since the prior pick 1 / 2-3 / 4-5 / 6-20 sessions / none. Prediction: decreasing in the gap,
   and 6-20 (placebo-ish) close to "none". Falsified if 6-20 >= 1-5 or no ordering.
P2 confounds: A-B within raw-price terciles and within vol20 terciles; prediction A-B > 0 in all 6 cells.
   Falsified if the effect lives in one tercile only (then it is a price/vol tilt, not "repeat").
P3 the 2020 / 2021 burst: A-B excluding 2020-03..2020-06 and 2021-01..2021-03 (meme/crash months). Must stay > +30bp.

### Round 8 result: L1 SURVIVES all three falsification checks (status: FORWARD CANDIDATE, strengthened)
- P1: gap 1 / 2-3 / 4-5 sessions vs none: +92.4 (t 1.9) / +90.8 (t 2.3) / +98.4 (t 3.7); **6-20 sessions: +2.3 (t 0.1)**
  = none. Not a smooth dose-response (flat inside 1-5), but a STEP at ~5 sessions: the placebo window is null, which is
  what "still under the same selling episode" predicts and what a generic "this name is volatile" tilt would not.
- P2: A-B positive in every price tercile (+53 / +57 / +54bp) and every vol20 tercile (+10 / +28 / +120bp): not a
  price tilt; strongest in high-vol names (consistent with the night premium scaling with vol).
- P3: excluding the 2020-03..06 crash and 2021-01..03 meme months: **+74.7bp, t 2.8**.
- Caveats unchanged: daily-close proxy (~2x optimistic), right-tail effect (medians close), ~55th cell of the loop,
  2003-15 not available for confirmation. Next step is a user decision: a no-order forward log ("[repeat]" line on
  each night pick + REGISTRY entry), judged on >= 150 live repeat picks; or test it inside the v2 tilt decision.

## Round 9 queue (frozen): live read-only check (descriptive, no gate) - in the live fills since 2026-09-23, how many
## night picks were repeats (picked <= 5 sessions earlier, any account) and how did they do vs first-time picks.

### Round 9 result (descriptive): live repeats are rare and too few to read
Live night fills 2026-09-23..10-07: 4 of 75 were repeats (<= 5 sessions after a prior pick in any account): BYND -24,
CNXC -96, GRML -596 (the 10-06 gap night), APMD +5bp; first-time picks n 71, mean -21, median 0. 5% repeats live vs
16% in the 2016-26 proxy (likely the taxable wash guard + small book). n 4 says nothing; at ~5% repeats a 150-repeat
forward gate would take ~3,000 picks (years). **Practical consequence: L1 cannot be judged forward at the current
book size on its own; it can only be judged inside the v2-tilt decision, or by logging the full candidate list
(not just fills) every night, which raises the repeat count to ~1-2/night.**

### Loop multiple-testing ledger (after 9 rounds)
~57 rule-universe cells judged. Only L1 cleared its bar: t 3.4 -> one-sided p ~0.0003, Bonferroni-57 ~0.02,
Holm the same (every other cell |t| < 3.0 in the right direction). It survives deflation, narrowly. Everything else
is consistent with the null.

## Round 10 queue (frozen before run): window rules on CLOSED-END FUNDS (retail-priced, capacity-limited: a small-
## account universe). SFP category CEF, raw price >= $5, prior-20d $ADV >= $1M. Cost 20bp RT (shock 60bp).
## Excess vs EW CEF universe. Same pass thresholds on NET. Rules: F1, F2, F4, F5, F6, F9, H1 (7 cells).

### Round 10 result (CEFs, ~165 funds/day): ALL KILLED at the registered 20bp cost (Program N +7)
| rule | H5 gross (t) | H3 gross (t) | net | median | halves |
|---|---|---|---|---|---|
| F1 squeeze release | -2.4 (-0.8) | -0.3 | -22.4 | -6.7 | -7.8/+0.5 |
| F2 TMO oversold cross | +5.5 (-0.1) | +10.4 (1.2) | -14.5 | -1.2 | +3.1/-3.8 |
| **F4 Stochastic cross-up < 20** | **+17.6 (2.6)** | **+15.5 (4.1)** | -2.4 | +7.3 | +17.7/+7.5 |
| F5 BB lower re-entry | +5.7 (1.4) | +4.9 (1.8) | -14.3 | +3.6 | +12.4/+2.7 |
| F6 RSI divergence | +1.1 (1.1) | -0.6 | -18.9 | +0.9 | +3.5/+8.7 |
| F9 OBV divergence | -5.4 (0.2) | -6.7 | -25.4 | -1.9 | +2.2/-0.5 |
| H1 TD Sequential 9 | +16.6 (1.0) | +9.9 | -3.4 | +6.1 | -1.6/+15.6 |
Observation (NOT a pass): CEFs are the first universe where an oscillator arm has a real gross effect (F4: +15-18bp,
t 2.6-4.1, median +7, both halves). It is the same retail-CEF short-term reversal that CEF-RV/CEF-TL2 already found
cost-bound ("real GROSS, cost-bound at retail"). It would matter only if CEF auction-to-auction cost is ~0 (PREF-EX
found crosses print at the NBBO mid on $25-par paper). Any retest needs its OWN registration with a MEASURED CEF
cross cost (e.g. from a log-only CEF MOC shadow); no re-run on these numbers with a lower assumed cost.

## Round 11 queue (frozen before run): window rules on $25-PAR INCOME PAPER (SEP Domestic Preferred Stock + SFP ETD
## baby bonds), raw price >= $5, $ADV >= $200k. Cost 40bp RT (shock 120bp; quoted spreads 38-88bp, crosses ~mid).
## Excess vs EW universe; ex-dividend nights are inside the windows (total return via closeadj). Rules F2, F4, F5, H1.

### Round 11 result ($25-par preferreds + baby bonds, ~213/day): ALL KILLED at the registered 40bp cost (Program N +4)
F2 TMO cross +4.9bp/5d (t 2.2), F4 Stochastic +18.0 (t 2.6; H10 +23.7 t 4.2), F5 BB re-entry +9.9 (t 2.8; H10 +18.5
t 3.8), H1 TD-9 +5.3 (H10 +10.9 t 3.1). Medians +5..+10, hit 52-53%, both halves positive, 2021-26 stronger.
**Class observation across rounds 1-11:** oscillator-oversold windows carry a REAL gross short-term reversal ONLY in
thin, retail-held income paper (CEFs +15-18bp, preferreds/baby bonds +10-24bp per 5-10d), and NOTHING in liquid
stocks/ETFs. Same mechanism as CEF-RV / CEF-TL2 / PREF-EX (retail liquidity provision in $25-par / CEF paper). Every
arm is cost-bound at quoted-spread costs; the open question is entirely the real cross cost, which only a forward
log can measure. No backtest re-run with a lower cost assumption.

## Round 12 queue (diagnostic, no gate): where does the CEF/preferred F4/F5 reversal sit in time? Compare close t ->
## close t+5 (MOC-to-MOC, the Schwab-executable form) vs open t+1 -> close t+5, and close t -> open t+1 alone.

### Round 12 diagnostic: the thin-paper reversal is SPREAD OVER DAYS, not in the overnight
| universe / rule | close t->open t+1 | open t+1->close t+5 | close t->close t+3 | close t->close t+5 (MOC-MOC) |
|---|---|---|---|---|
| CEF F4 stochastic | +0.3 | +17.6 (t 2.6) | +15.9 (t 3.9) | +18.4 (t 2.4, med +6.4) |
| CEF F5 BB re-entry | -0.5 | +5.7 | +5.0 | +5.6 |
| PREF F4 stochastic | +1.9 | +18.0 (t 2.6) | +12.8 | +19.8 (t 3.0, med +8.3) |
| PREF F5 BB re-entry | -2.1 | +9.9 (t 2.8) | +4.3 | +7.7 (t 2.9) |
Read: the MOC-to-MOC form (the one Schwab can execute: no MOO) keeps all of it. Ceiling for CEF F4 at full deployment:
~1,100 signals/yr, ~20 concurrent 5-day holds, +18bp/5d excess -> ~9%/yr GROSS excess on deployed capital IF the
cross cost is ~0; at 5bp/side it is ~4%/yr (below the +8pp gate). So the whole case rests on a measured CEF/pref
MOC cost. Cheapest honest next step (user decision): add CEFs/preferreds to a log-only MOC-cost shadow (official
close cross vs NBBO mid at 15:59), not another backtest.

## Round 13 queue (frozen before run): one more thin, retail-held, anchored universe -> ADRs (SEP "ADR Common Stock*"),
## raw price >= $5, $ADV >= $1M, cost 20bp RT (shock 60). Rules F4, F5, H1. Excess vs EW ADR universe.

### Round 13 result (ADRs, ~289/day): ALL KILLED (Program N +3). F4 -2.1bp (median -18.5), F5 -4.4, H1 +1.1.
**Falsification of "thin = reversal":** ADRs are thin and anchored yet show NOTHING. The CEF/preferred effect is not a
thinness effect; it is specific to retail-held INCOME paper (the CEF-RV / PREF-EX clientele).

## Round 14 queue (frozen before run): does it extend to income COMMONS? Universe = SEP common stocks with Sharadar
## industry "REIT - *" (mortgage REITs are the most retail/income-held), raw >= $5, $ADV >= $1M, cost 20bp RT (shock 60).
## Rules F4, F5. Arms: all REITs; mortgage REITs only. Excess vs EW REIT universe.

### Round 14 result (REIT commons ~?/day; mortgage REITs): ALL KILLED (Program N +4)
REIT F4 -4.1bp, F5 +3.7; mREIT F4 -0.4, F5 +1.2 (all |t| < 1). (Two lines in winsig_out.txt labelled without a
universe tag are accidental re-runs of the stock universe from a quoting bug; ignore them.)
**Class boundary sharpened:** the oscillator reversal exists in exchange-traded FIXED-INCOME-LIKE paper with a hard
anchor (CEF NAV, $25 par/call price) and retail flow; not in thin stocks (ADRs), not in income COMMONS (REITs,
mREITs), not in liquid stocks/ETFs. Mechanism = retail liquidity provision against an anchor.

## Round 15 queue (frozen before run): anchor test inside preferreds/baby bonds. F4 PREF signals split by raw price
## below $24 (discount to $25 par) vs >= $24. Prediction: below-par arm stronger (pull to par). Gate (G4-style):
## paired difference >= 15bp/5d, |t| >= 2.5, halves same sign. Close t -> close t+5 (MOC-MOC) excess.

### Round 15 result: anchor prediction RIGHT in sign, short of the bar (fail by the letter)
F4 preferreds below $24: +29.5bp/5d MOC-MOC (median +9.2) vs >= $24: +10.4 (median +7.9); paired +35.8bp, t 2.3
(< 2.5), halves +44.1/+27.6. Supports "pull toward the $25 anchor" as the mechanism, but medians are close (the
below-par edge is partly tail, incl. distressed issues). No more splits of this panel (forking-paths stop).

## Round 16 queue (frozen before run): new class -> CEF DISTRIBUTION-CUT windows (retail yield clientele sells on a cut).
## Event: CEF distribution falls >= 10% below the median of its prior 3 distributions, which were within 2% of each
## other (a stable regular payout; excludes specials/year-end gains as the comparator). Sharadar actions dividend rows.
## Entry: close of the ex-date of the first cut distribution (cut known at declaration, before ex; ex-date is a safe
## later point). Long close -> close +5 / +10 / +20 (primary +10), excess vs EW CEF universe; cost 20bp RT.
## Pass: net >= +25bp... scaled for 10d: net >= +50bp/event, NW t >= 2.5, halves > 0, median > 0. 2016-26 only.
## Mirror (diagnostic): the same window BEFORE the cut ex-date (-10 -> 0) to see whether the selling is already done.

### Round 16 result: CEF distribution cuts -> CONTINUATION, not reversal. Long arm KILLED; strong avoid-signal found.
363 cut events 2016-26 (34/yr, 210 funds). Excess vs EW CEFs: pre-ex 10d **-152bp** (t -5.2); after ex: +5d -54
(t -3.6), **+10d -88bp (t -3.8, median -45, hit 40%)**, +20d -99bp (t -3.4, median -75); both halves negative,
ex-top-5 more negative. Retail yield holders keep selling for weeks after the cut; nobody fades it.
- As a stand-alone SHORT: ~34/yr x ~0.9% before borrow/cost x a small capital share -> ~3%/yr ceiling: below the
  +8pp gate (and CEF borrow is uncertain). Not pursued.
- **As a STATE GATE on the live CEF-RV shadow** (the program's preferred use for this shape): CEF-RV buys discount
  widenings; funds that just cut distributions widen for a reason and keep falling. Round 17 tests that overlap.

## Round 17 queue (frozen before run): CEF-RV signals split by "distribution cut (as in R16) within the prior 30
## sessions" vs not. Pass (avoid-screen): cut-arm excess <= -50bp/trade vs the rest, t <= -2.0, halves same sign.

### Round 17 result: **PASS as an avoid-screen on CEF-RV** (2016-26)
CEF-RV trades (3,731, frozen rule) entered within ~30 sessions (42 calendar days) after a distribution cut: n 83,
excess vs EW CEFs **-260bp/trade (median -240)** vs the rest +62bp (median +60); diff **-322bp, t -3.3**, halves
-328/-321. Dropping them lifts CEF-RV's average ~+7bp/trade (2.2% of trades) and removes a clearly losing pocket.
Mechanism: R16 (retail yield holders keep selling for weeks after a cut; the discount widening is information).
One confirm look allowed (gate rule): 2003-2014 entries (CEF-RV's own OOS window; my CEF panel starts 2002-06),
pass if diff <= 0 with t <= -2.0. Survivorship caveat for that era (CEF-SURV99) applies to both arms equally.
**CONFIRMED on 2003-2014 (one look):** CEF-RV trades 3,171; after-cut n 62 excess **-182bp (median -117)** vs rest
+163bp (median +104); diff **-344bp, t -2.6**, halves -518/-183. The avoid-screen holds in an era its rule never saw.
Status: **VALIDATED (small, defensive)** - the loop's first confirmed result. Effect on CEF-RV: removes ~2% of trades
that lose ~3pp each vs the rest. Action (user decision, not done): add "distribution cut (>=10% below the median of 3
stable prior payouts) within 30 sessions -> skip" to the CEF-RV forward shadow and log both arms; REGISTRY entry for
CEF-RV gets a note in the same commit. Data: Sharadar actions (dividends) on the Mac, or CEFConnect distribution
history (same IP block caveat as the NAV panel: refresh from the Mac).

## Round 18 queue (frozen before run): the R16 MIRROR, long-only (Roth-friendly). CEF distribution INCREASE: payout
## >= 10% ABOVE the median of 3 stable prior payouts (within 2%). Entry close of the ex-date, hold +5/+10/+20 (primary
## +10), excess vs EW CEFs, cost 20bp RT. Pass: net >= +50bp/event, NW t >= 2.5, halves > 0, median > 0.
## Caveat written in advance: an "increase" row can be a special/year-end gain distribution (one-off), unlike a cut;
## arm B requires the NEXT payout to stay >= 1.05x the old median is NOT allowed (look-ahead), so specials stay in.

### Round 18 result: increases are PRICED IN BEFORE the ex-date; no post-ex drift. KILLED (Program N +1)
418 increases (39/yr): pre-ex 10d **+110bp** (t 4.5, hit 66%), then +5d -16 (t -2.3), +10d +1.5 (t -0.4, median -9),
+20d -18. Asymmetry vs R16: good news is bought ahead of the ex-date; bad news (cuts) keeps being sold after it.
Consistent with a retail clientele that sells slowly and buys early. No long-only CEF distribution signal.

## Round 19 queue (audit diagnostic on the LIVE night leg, no gate): can an ex-dividend drop fake a -8% signal?
## In the nx daily panel the rule uses split-adjusted closes, but live Schwab quotes may compare the 15:40 price to an
## UNADJUSTED prior close. Count 2016-26 days where a liquid name has an ex-dividend >= 3% of price (Sharadar actions)
## and its raw close-to-close return is <= -8% while the dividend-adjusted return is > -8% (a fake signal), and how
## such names did overnight.

### Round 19 audit: the live night leg is PROTECTED from ex-dividend fake signals (no action)
Raw-close fakes (raw <= -8% but total return > -8%, ex-div >= 3%): 428 in 2016-26 (40/yr; ZIM-style specials), and
they do NOT bounce (overnight -15.6bp, median -1.4 vs +44.6bp for real -8% days). Live code: the night rule's
prev_close comes from Alpaca daily bars fetched with adjustment="all" (split AND dividend adjusted:
`swingtrader/daily/marketdata.py:58/80`), so the fake drop is removed; and `signals.prev_close_mismatch` (tol 3%)
skips any name whose bar close disagrees with the quote feed's own previous close, which a >= 3% dividend triggers.
Side effect: real -8% signals on a big-dividend ex-date are skipped too (rare). (The 10-05/10-06 "DDS skipped" lines
are NOT this: DDS's only recent dividend was $0.30 ex 09-30; that mismatch has another cause, unexamined.)

## Round 20 queue (frozen before run): window state as a STATE GATE on PREF-EX (the strongest small-account candidate).
## Events: preferred + baby-bond ex-dates (Sharadar dividends), raw price >= $5, $ADV >= $200k. Trade CC: buy close T-1,
## sell close ex-date, + dividend, raw prices. Split by the 10-session return into T-1 (raw closes): <= -3% (falling,
## R16 bad-news-continuation logic) vs > -3%. Pass (avoid-screen): diff <= -15bp/event, day-clustered t <= -2.5, halves
## same sign. Discovery 2016-26; one confirm look on 2005-15 only after a pass. Diagnostic arm: F4-oversold at T-1.

### Round 20 result: no avoid-screen needed for PREF-EX. KILLED as a screen (Program N +1)
15,289 ex-events 2016-26 (CC +30.0bp, median +27.0). Preferreds that fell >= 3% in the 10 sessions before T-1 capture
MORE, not less: +34.0 vs +29.7bp, paired +21.7 (t 2.1), halves +21.7/+21.8 (wrong sign for an avoid-screen).
F4-oversold at T-1: +7.4 (t 0.8). PREF-EX is robust to recent price declines; the R16 bad-news logic does not carry
over to preferred ex-nights. (Note for the LLM news judge discussed this session: 8-K bad-news items as a night-pick
DROP filter are already dead, NEXT.md:233, so its prior is weak.)

## Round 21 queue (frozen before run): PRE-EX accumulation window in CEFs (dividend-capture demand by retail).
## Events: CEF ex-dates with a stable prior payout (3 prior within 2%, as R16) and no cut/increase >= 10%.
## Trade: buy close T-10 -> sell close T-1 (before the ex-night), excess vs EW CEFs, cost 20bp RT.
## Pass: net >= +25bp/event, NW t >= 3, halves > 0, median > 0, ex-top-5 > 0.

### Round 21 result: CEF pre-ex accumulation is REAL GROSS (strongest t of the loop), KILLED at the 20bp cost
16,030 stable-payout ex-events 2016-26 (1,498/yr): close T-10 -> close T-1 excess vs EW CEFs **+29.8bp (t 8.7)**,
median +18.8, hit 54%, halves +34.6/+24.8, ex-top-5 +38.3. Net of 20bp RT +9.8 < +25 bar -> fail (no confirm look).
Same mechanism as R18's pre-ex run-up (retail dividend-capture demand before the ex-date; DM/Hartzmark-Solomon in a
homogeneous universe, so not a size tilt). Ceiling if rotated continuously (~28 nine-day windows/yr): ~8%/yr gross
excess on deployed capital at ~0 cost, ~3%/yr at 20bp RT.

### Cross-round synthesis: THREE CEF/preferred effects now hinge on one number - the real auction (MOC) cost
- R10 CEF stochastic oversold: +18bp/5d gross (t 2.4-4.1).
- R11 preferred/baby-bond oversold: +10-24bp/5-10d gross (t 2.2-4.2).
- R21 CEF pre-ex window: +30bp/9d gross (t 8.7).
Each is dead at quoted-spread costs (20-40bp RT) and live at ~0-5bp/side (which PREF-EX found for $25-par crosses).
**The single highest-value next step from this loop is not another backtest: it is a log-only MOC cost shadow for
CEFs (official closing cross vs the 15:59 NBBO mid on ~20 CEFs/day).** User decision (server change + REGISTRY).
Plus the validated R17 avoid-screen for CEF-RV.

## Round 22 queue (frozen before run): the R21 pre-ex window in PREFERREDS + baby bonds (the PREF-EX universe).
## Same construction (stable prior 3 payouts within 2%, payout within 10% of their median), T-10 close -> T-1 close,
## excess vs EW pref universe, cost 40bp RT. Same pass thresholds. Diagnostic: does the pre-ex drift ADD to the
## PREF-EX ex-night (i.e. T-10 -> ex close) or is the ex-night itself smaller after a pre-ex run-up?

### Round 22 result: preferred pre-ex window real gross (+39bp, t 7.3, median +25.5, hit 57%, halves +23/+52), net -1.0
at 40bp RT -> fail as registered. **Diagnostic (2016-26, touched):** chaining it with the PREF-EX ex-night in ONE round
trip (buy close T-10, sell close on the ex-date, dividend included) = **+68.2bp excess (median +48.4, NW t 10.2)**,
+28.2bp net of a single 40bp round trip. The ex-night is a bit smaller after a big run-up (+31 / +21 / +17 by run-up
tercile) but stays positive; the two windows ADD.

## PRE-REGISTRATION "PREF-CHAIN" (frozen now, after the 2016-26 diagnostic; Program N +1)
Rule: preferreds + baby bonds (SEP Domestic Preferred + SFP ETD), raw >= $5, $ADV >= $200k, stable payout (3 prior
within 2%, current within 10% of their median); buy the close 10 sessions before the ex-date, sell the ex-date close;
total return incl. the dividend; excess vs EW pref universe; cost 40bp RT (shock 120bp).
Judge window: **2005-2015, ONE look** (the chained rule was never run there; the ex-night alone was seen in the PREF-EX
probe, disclosed). Pass: net >= +25bp/event, NW t >= 3, both halves (2005-10 / 2011-15) > 0, median > 0, ex-top-5 > 0.
Kill: anything else. Note in advance: pre-2014 has few liquid issues (PREF-EX probe: n 1-27/yr) -> low power there.

### PREF-CHAIN verdict (2005-2015, one look): **PASS** (narrowly on net; robust otherwise)
n 1,540 events; chained excess +65.6bp (median **+56.8**), **net of 40bp RT +25.6bp** (bar +25), NW t **4.0**, halves
+33.4 / +74.7, ex-top-5 +34.3; **positive in all 11 years** (2005 +44 ... 2011 +7 ... 2015 +89). Components as in
2016-26: pre-ex +46.3, ex-night +21.0. Fails the 3x shock (120bp RT: -54.4; not a registered gate but a stated risk).
**Status: VALIDATED-SMALL, cost-dependent.** It holds out-of-sample in an era the rule never saw, at the median, every
year. The margin over quoted-spread cost is thin, so the cross cost decides the size of the prize again.
Implementation shape (user decision; not done): PREF-EX's forward shadow already logs these ex-dates; logging a
T-10 entry arm beside its T-1 arm costs nothing and measures the chain forward. Roth only (dividends untaxed, no wash
issue). Rough economics at $10k (Roth), fully rotated 10-session windows: ~25 cycles/yr x ~+26bp net excess ~= +6.5%/yr
excess over holding the EW preferred universe (whose own ~5-7% yield comes on top), before participation limits in
thin issues (median close participation ~2% at $10k per the PREF-EX shadow; fine at $2-25k).
Caveats: 2015 is 48% of the judge sample (n 745); pre-2014 issues are few; survivorship of called/delisted preferreds
follows Sharadar SEP coverage (delisted included); daily closes, not official crosses.

## Round 23 queue (frozen before run): FALSIFY PREF-CHAIN (2016-26 + 2005-15, no new parameters)
Q1 placebo windows on the same names: (a) T+5 close -> T+15 close (after the ex-date), (b) the same 10-session span
   ending on a random non-ex date >= 20 sessions from any ex-date. Prediction: excess ~0. Falsified if either placebo
   >= half the chained effect (>= +34bp).
Q2 liquidity: $ADV >= $1M subset: chained gross stays >= +40bp (net >= 0 at 40bp RT).
Q3 sub-universes: SEP preferreds alone and SFP ETD baby bonds alone: both chained gross > +30bp.
Q4 payout frequency: monthly vs quarterly payers both > 0 (a rule that only works for one frequency is fragile).

### Round 23 result: PREF-CHAIN survives the placebo and frequency checks; liquidity/sub-universe checks PARTIAL
| check | 2016-26 | 2005-15 | prediction | verdict |
|---|---|---|---|---|
| chained (reference) | +68.2 (n 12,404) | +65.6 (n 1,540) | | |
| Q1a post-ex T+5->T+15 | -1.8 | -0.9 | ~0 | pass |
| Q1b random 10d far from any ex-date | -11.2 | -6.1 | ~0 | pass (negative: the EW benchmark itself contains ex-windows) |
| Q2 $ADV >= $1M | +55.0 (n 3,907) | **+28.9** (n 611) | >= +40 | pass / **FAIL** |
| Q3 SEP preferreds / ETD baby bonds | +67.0 / +74.1 | +98.5 / **+19.1** | both > +30 | pass / **FAIL (ETD)** |
| Q4 monthly / quarterly payers | +95.6 / +66.2 | +40.9 / +69.9 | both > 0 | pass |
Read: the effect is tied to the ex-date (both placebos null) and is not a frequency artifact. In the older era it is
weaker in the most liquid issues and in baby bonds: it scales with ILLIQUIDITY, as a retail liquidity-provision premium
should (and as the $2-25k capacity rule favours). The 2016-26 era is uniformly strong. Status unchanged:
VALIDATED-SMALL, cost-dependent; forward logging is the next step (user decision).

## PRE-REGISTRATION "CEF-CHAIN" (frozen before any chained CEF number is computed; Program N +1)
Rule = PREF-CHAIN transplanted unchanged to CEFs (SFP CEF, raw >= $5, $ADV >= $1M, stable payout as R16/R21): buy the
close 10 sessions before the ex-date, sell the ex-date close, total return; excess vs EW CEFs; cost 20bp RT (shock 60).
Judge: **2003-2015, one look** (R21 used only 2016-26 and only the T-10 -> T-1 part). 2016-26 printed as touched context.
Pass: net >= +25bp, NW t >= 3, halves (2003-09 / 2010-15) > 0, median > 0, ex-top-5 > 0. Known risk stated in advance:
CEF ex-nights decayed to < 10bp since 2020 (FXD), so the chain leans on the pre-ex window.

### CEF-CHAIN verdict (2003-15, one look): **KILL** (net +8.9bp < +25)
Judge 2003-15: chained +28.9bp (median +21.8, t 5.9, halves +35.6/+25.4, 11/13 years > 0), net of 20bp RT +8.9.
Context 2016-26: +21.9bp, net +1.9. Why it fails where PREF-CHAIN passes: the CEF EX-NIGHT is NEGATIVE vs EW CEFs
(-5.0 / -7.5bp; -16bp after a big run-up), so holding through the ex-date gives back part of the run-up.
The PRE-EX window alone is the persistent part: +33.7bp (2003-15) and +29.5bp (2016-26), i.e. a 23-year retail
dividend-capture bid in CEFs that is fully reversed at the ex-date. Cost-bound at 20bp RT (R21: net +9.8); joins
the "needs a measured CEF cross cost" list. No re-run of T-10 -> T-1 as a judged rule (R21 already failed it).

## Round 25 queue (frozen before run): NEW-ISSUE window in $25-par paper (forced index flow: PFF/PGX-type preferred
## ETFs add new issues after seasoning, typically at a month-end rebalance). Universe: SEP preferreds + SFP ETD whose
## first price date is in the window; skip the first 5 sessions (when-issued noise); buy the close of session 5 after
## listing, sell the close of session 30 and (diagnostic) 45. Excess vs EW pref universe (liquid), cost 40bp RT.
## Pass (frozen gate): net >= +25bp, NW t >= 3, halves > 0, median > 0, ex-top-5 > 0. Discovery 2016-26; one 2005-15
## confirm only after a pass. No liquidity filter at entry other than raw >= $5 (new issues have no 20d ADV yet).

### Round 25 result: preferred NEW-ISSUE window KILLED (Program N +1)
964 new issues 2016-26 (90/yr, entry median $25.18): session 5 -> 30 excess -30.2bp (median +15.8, hit 53%, t -1.3),
halves -13/-62, ex-top-5 -43.8. Typical issue drifts up a little; a tail of issues that break par sinks the mean.
s5 -> s45: +4.0 (median +41). No index-inclusion lift visible at the daily tier; the left tail dominates.

---
## MORNING SUMMARY (written at round 25; later rounds append below)
**Validated (each one look on a window the rule never saw):**
1. ~~PREF-CHAIN~~ **CORRECTED AFTER ROUND 35: PREF-CHAIN FAILS its registered net bar.** A bug (my "3 stable prior
   payouts" test let events with only 1-2 priors through: pandas skips NaN) inflated the 2005-15 judge. As registered:
   n 1,168, gross +57.0bp (median +58.3, t 3.5, all 11 years > 0) but **net of 40bp RT +17.0 < +25 -> KILL**.
   Status: REAL GROSS OUT-OF-SAMPLE, cost-bound (joins the CEF/pref list below). 2016-26 unchanged (+68.1, net +28.1).
   The T-10 arm in the PREF-EX shadow is still the cheapest way to measure it forward, but it is NOT validated.
2. ~~CEF-RV distribution-cut avoid-screen~~ **CORRECTED AFTER ROUND 36: NOT CONFIRMED (by a hair).** A second bug
   (EW benchmark built from pct_change on liquid-only rows) inflated it. Corrected, and matching an independent
   re-implementation: 2016-26 diff -255bp (t -2.9, halves -188/-363); 2003-14 diff -191bp, **t -1.98 vs the
   registered -2.0**, cut-group median +41. Direction holds in both eras; status PLAUSIBLE (defensive), not validated.
**After both corrections, NOTHING in this loop is validated.**
**Forward candidate (independently replicated, round 37: +103bp paired, t 4.1, halves stable; non-monotone gap buckets, tail-driven after 2021):** L1 repeat loser on the night leg (+85bp/night vs first-time picks, t 3.4, survives placebo /
price / vol / ex-crisis checks; right-tail effect; too rare in live fills to judge without logging candidates).
**Real gross, cost-bound (all hinge on a measured CEF/pref auction cost):** CEF oscillator reversal (+18bp/5d),
preferred oscillator reversal (+10-24bp), CEF pre-ex window (+30bp/9d, 23 years).
**Dead classes (~75 cells):** every classic indicator window (TTM, TMO, MACD, stochastic, BB, RSI/OBV divergence,
ADX, NR7, contraction breakout, weekly MACD, TD-9, climax, pocket pivot, island, Heikin-Ashi) on liquid stocks, ETFs,
thin stocks, ADRs, REITs; breadth timing; IBS-leg window filters; gap fades; vol compression; residual reversal;
CEF distribution increases; preferred new issues; sector-crowding cap on night picks.

## Round 26 queue (frozen before run): does the retail pre-ex bid extend to HIGH-YIELD COMMONS?
## Universe: liquid common stocks (raw >= $5, $ADV >= $20M) with trailing-4-payout yield >= 6% at T-10 and a stable
## payout (3 prior within 2%, current within 10% of their median; quarterly or monthly). Arm A: T-10 close -> T-1 close;
## Arm B (chain): T-10 close -> ex-date close incl. dividend. Excess vs EW liquid universe; cost 10bp RT.
## Pass (frozen gate) on Arm B: net >= +25bp, NW t >= 3, halves > 0, median > 0, ex-top-5 > 0; then one 2003-15 look.

### Round 26 result: high-yield COMMONS have no pre-ex bid. KILLED (Program N +1)
1,617 events 2016-26 (288 names, yield >= 6%): pre-ex T-10 -> T-1 -14.3bp (median -30.9); chain -17.5 (median -38.9,
t -0.2). The retail dividend-capture bid is specific to $25-par / CEF paper (PREF-CHAIN, R21), absent in liquid
commons (consistent with the dead DM / EXDIV-OPEN studies).

## Round 27 queue (frozen before run): ISSUER-CRASH window on preferreds (same-issuer, slow retail reaction; R16 logic).
## Map preferred "XXX-P?" -> common "XXX" (Sharadar naming). Event: the issuer's common has a total-return day <= -8%.
## Measure the preferred's excess vs EW prefs close t -> close t+1/+5/+10 (description), and the AVOID-SCREEN test:
## PREF-CHAIN events whose T-10 entry falls within 10 sessions after an issuer-common crash vs the rest.
## Avoid-screen pass: diff <= -50bp/event, t <= -2.5, halves same sign. 2016-26 discovery, one 2005-15 look on a pass.

### Round 27 result: OPPOSITE of the R16 logic - preferreds REBOUND after the issuer's common crashes
2016-26: 3,002 issuer-crash preferred events (458 prefs): excess vs EW prefs +1d +5.7, +5d +14.8 (median -1.3),
**+10d +123.5bp (median +67.8, t 2.4)**. Clustered in 2020-03 (1,212 events); excluding 2020-02..05: +10d +117.1
(median +33.8). Per-year +10d mean mixed (2017 -57, 2022 -6; the other 9 years positive), medians mostly positive.
Avoid-screen on PREF-CHAIN fails in the wrong direction: PREF-CHAIN entries within ~10 sessions after an issuer crash
earn MORE (+164.7 vs +65.7bp, diff +99, t 1.7). Read: retail preferred holders over-sell senior fixed-coupon paper
when the common crashes, then it recovers over ~2 weeks. The 5d->10d jump is unexplained (watch for an artifact).

## PRE-REGISTRATION "PREF-CRASH" (frozen now; Program N +1)
Event: issuer common (preferred "XXX-P?" -> common "XXX") total-return day <= -8%, common raw >= $3. Buy each liquid
preferred of that issuer ($ADV >= $200k, raw >= $5) at the close of t+1 (one session later than the discovery run:
conservative, no same-close timing), sell the close of t+11. Excess vs EW prefs; cost 40bp RT.
Judge **2005-2015, one look**. Pass: net >= +25bp, NW t >= 3, halves (2005-09 / 2010-15) > 0, median > 0, ex-top-5
days > 0. Disclosed: 2008-09 will dominate the event count (financial-issuer preferreds), the analogue of 2020-03.

### PREF-CRASH verdict (2005-15, one look): **KILL by the letter - the judge window is effectively EMPTY**
Only 51 events (32 preferreds), all in 2014-15: the "XXX-P?" -> "XXX" issuer mapping plus the $200k ADV filter finds
almost no pre-2014 liquid preferreds in Sharadar (same thin pre-2014 coverage the PREF-EX probe showed). Excess +83.3
(median +23), but NW t undefined, first half empty, ex-top-5 -64 -> fails. This is UNTESTABLE history, not a refutation.
Status: OBSERVATION ONLY (2016-26, crisis-clustered). Not to be re-judged on another historical slice; if pursued, a
log-only forward watch (issuer crash -> its liquid preferreds, +10 session excess) is the only honest route.

## Round 28 queue (frozen before run): R21's pre-ex bid as a TIMING GATE on CEF-RV. Split CEF-RV trades by whether the
## entry falls within the 10 sessions (14 calendar days) BEFORE one of the fund's ex-dates vs not. Pass (state gate):
## diff >= +50bp/trade (excess vs EW CEFs), t >= 2.5, halves same sign; then one 2003-14 look. Same R17 machinery.

### Round 28 result: pre-ex timing adds nothing to CEF-RV. KILLED (Program N +1)
CEF-RV entries within ~10 sessions before an ex-date: +66bp (median +74) vs +49 (median +44); diff +16bp, t 0.5.
CEF-RV holds for weeks; a 9-day pre-ex bid is diluted inside that hold.

## Round 29 (data audit, no gate): is PREF-CHAIN an adjusted-price artifact? Recompute the chain from RAW prices
## ((close_T + dividend) / close_{T-10} - 1, closeunadj) for the 2016-26 and 2005-15 events and compare with the
## closeadj version; also check whether R27's 10-day preferred windows contain ex-dates more often than the benchmark's.

### Round 29 audit: PREF-CHAIN is NOT an adjusted-price artifact
Raw-price chain ((close_T + dividend) / close_{T-10} - 1) vs closeadj chain, before benchmarking: 2005-15 +90.7 vs
+90.7bp (median 79.7 vs 79.2); 2016-26 +89.4 vs +90.0 (median 73.9 vs 74.2); |adj - raw| median 0.1-0.2bp, > 50bp in
0.1-0.2% of events. The excess numbers (+65-68bp) are these minus the EW pref universe. R27's issuer-crash windows
contain an ex-date as often as any (13.6% vs 13.9%), so the R27 5d->10d jump is not an ex-date artifact (still open).

## Round 30 (practical diagnostic, no gate): PREF-CHAIN at the user's size. Concurrency (how many 10-session windows
## are open on a typical day), entry-day $ADV, and the share of daily volume a $500 / $1,000 position would be.

### Round 30 result: PREF-CHAIN fits the user's size with room to spare
2021-26: 1,289 events/yr; open 10-session windows per day median 45 (10th pct 27, 90th 82); entry $ADV median $535k
(25th pct $314k); a $500 slot = 0.09% of median daily dollar volume, $1,000 = 0.19%; entry price median $23.54 (no
whole-share problem). At $10k with 20 x $500 slots the book is always full (>= 27 windows open on 90% of days).
Capacity is not a constraint below ~$100k; cost per fill is (thin crosses).

## Round 31 (portfolio diagnostic, no gate): PREF-CHAIN as a book. Each day hold every open T-10 -> ex window equally
## weighted (fully invested when >= 1 window open), raw total return, cost 40bp per position charged over its 10
## sessions; compare with buy-and-hold of the EW liquid pref universe. CAGR, vol, max drawdown, by year, 2005-26.

### Round 31 result: PREF-CHAIN as a book - strong when diversified, catastrophic when not
| era | PREF-CHAIN book (net 40bp RT) | EW pref buy & hold | open windows/day (median) |
|---|---|---|---|
| 2005-2009 | CAGR **-10.1%**, vol 37%, **maxDD -80%** | +9.5%, maxDD -55% | **2** |
| 2010-2026 | CAGR **+15.2%**, vol 15.6%, maxDD -44.5% | +8.3%, maxDD -42.4% | 29 |
| 2013-2026 | CAGR **+15.2%** | +6.3% | 34 |
By year (chain / EW): 2007 -32/-14, 2008 -42/-10, then 2010-26 ahead in 15 of 17 years (2014 +23/+12, 2016 +18/+5,
2020 +33/+21, 2023 +29/+17, 2024 +25/+12, 2025 +19/+8). Read:
- **The event edge is real but the book carries full PREFERRED CRASH BETA** (2020 maxDD -44.5%, like holding prefs).
  Size it as a preferred allocation, not as a hedged edge.
- **Concentration kills:** with ~2 open windows (2005-09, thin coverage) the book was a few financial preferreds into
  2008 (-80%). Rule for any live use: require >= ~15-20 concurrent windows across issuers, cap any one issuer.
- At the diversified scale available since 2010 it beat EW prefs by ~+7-9pp/yr (net of 40bp RT). That clears the
  +8pp gate at the book level only in 2013-26 (mostly the touched era); treat as an upper estimate.

## Round 32 (diagnostic, no gate): PREF-CHAIN's EDGE-ONLY risk. Daily (book - EW pref) series 2010-26: CAGR of the
## spread, its max drawdown, worst year; and issuer concentration of the open windows (top issuer share per day).

### Round 32 result: the EDGE itself (book minus EW prefs, 2010-26)
Spread CAGR **+6.5%/yr**, vol 7.3%, max drawdown -17.9%, worst year -7.9% (2012), positive in 15/17 years.
Issuer concentration of the open windows: top issuer = 16% median, 33% at the 90th pct (big multi-series issuers
such as banks/REITs with many preferreds going ex the same day). A per-issuer cap (e.g. <= 10% of the book) belongs
in any live version. Read: ~+6.5pp/yr of edge with a modest drawdown, carried on top of full preferred beta;
consistent with the R22/PREF-CHAIN per-event numbers (~+26bp net x ~25 rotations).

### Round 33 (live read-only, no gate): CORRECTION to Round 30 - the AUCTIONS are thin even where daily volume is not
PREF-EX shadow on him (`state/pref-ex.jsonl`, 287 scored ex-events since 2026-09): official closing-cross dollar
volume median **$7,140** (25th pct $2,595); opening cross $11,550; exit-day close cross $4,796; the shadow's own
"typical cross" median **$3,597**. So a $500 PREF-CHAIN slot is ~7-14% of a typical cross and $1,250 (the $25k slot)
~20-35%. Round 30's "$500 = 0.09% of daily $ volume" is true of the whole day but NOT of the cross; via auctions the
capacity binds near ~$10k, the same plateau PREF-EX found. PREF-CHAIN does not need auctions (10-session window):
entering/exiting with passive limit orders in continuous trading is the natural route, but then the cost is a
fraction of the quoted spread (38-88bp), not ~0. Also: the shadow's slip_co/slip_cc are a MODEL (constant
COST + impact x half-spread, `pref_ex_shadow.py:134-135`), not a measurement - no measured pref/CEF cross cost exists yet.

### Round 34 (no new data): PREF-CHAIN cost bracket from the measured PREF-EX quote study
`research/sim/pref_quotes_out.txt` (296 events with quotes): closing quoted spread median 38.4bp (mean 58.8), opening
88.2bp; official closes print at the NBBO mid (close_vs_mid median +2.1bp). So for PREF-CHAIN (entry close T-10,
exit close on the ex-date):
- **MOC both legs:** ~mid fills, cost ~impact only (~0-10bp RT) -> net ~+55-65bp/event, but cross capacity is
  ~$50-250/event at 1-5% participation (pref_exec_out.txt section 3) - a $2-5k book.
- **Marketable limits in continuous trading:** ~one quoted spread RT (~38bp median) -> net ~+27-30bp, the registered
  40bp case; capacity then follows the day's volume ($535k median ADV).
- Breakeven RT cost: ~65bp (2005-15 gross +65.6), ~68bp (2016-26).
The registered 40bp assumption sits at the median quoted spread; the edge survives anything short of paying ~1.7x the
median spread on every round trip. Fat-spread issues (mean 58.8bp) should be skipped or worked passively.

## Round 35 queue: INDEPENDENT RE-IMPLEMENTATION of PREF-CHAIN by a subagent that has not seen my code (bug hunt on
## the loop's main positive). Pass = its numbers land within ~10bp of mine for both eras.

### Round 35 result: INDEPENDENT RE-IMPLEMENTATION FOUND A BUG; PREF-CHAIN's pass is RETRACTED
A subagent rebuilt PREF-CHAIN from the written spec without seeing my code: 2016-26 matched (12,033 events, +68.1 vs
my +68.2); 2005-15 did not (1,168 events, +57.0 vs my 1,540, +65.6). Diff: all 372 extra events were mine, each with
only 1-2 prior payouts. My stable-payout test `(P.max/P.min - 1) <= 0.02` and `P.median` skip NaN in pandas, so
"3 prior payouts within 2%" silently passed with fewer than 3. Fixed in every loop script (`P.notna().all(axis=1)` /
`p3.notna()`), all affected rounds re-run:
| result | before fix | after fix | verdict change |
|---|---|---|---|
| **PREF-CHAIN judge 2005-15** | net +25.6, t 4.0 -> PASS | **n 1,168, gross +57.0 (median +58.3, t 3.5, halves +32.6/+66.2, all 11 yrs > 0), net +17.0** | **PASS -> KILL (net bar)** |
| PREF-CHAIN 2016-26 context | +68.2 | +68.1 (n 12,033, net +28.1) | none |
| R23 placebos / frequency | null / both > 0 | post-ex -1.2/+1.6, random -11.2/-6.1; ADV>=$1M 2005-15 +26.3; ETD 2005-15 +17.1 | none (same partial fails) |
| R31 book 2010-26 | +15.2% CAGR, DD -44.5% | +15.0% vs EW +8.3%, DD -44.6% | none |
| R32 edge-only 2010-26 | +6.5%/yr, DD -17.9% | +6.3%/yr, DD -22.7%, 14/17 yrs; top issuer 90th pct 50% | slightly worse |
| R16 CEF cuts | +10d -88 (t -3.8) | -92.3 (t -3.7), n 349 | none |
| **R17 CEF-RV cut avoid-screen** | -322 (t -3.3); confirm -344 (t -2.6) | **-312 (t -3.2); confirm -344 (t -2.6)** | **still VALIDATED** |
| R18 increases / R21 CEF pre-ex | dead / +29.8 net +9.8 | dead / +30.2 net +10.2 | none |
| CEF-CHAIN judge | net +8.9 KILL | net +9.0 KILL | none |
Lesson (for MISTAKES.md if adopted): **any "N prior values" rule built from shifted columns must assert the N values
exist; pandas reductions skip NaN.** The independent re-implementation is what caught it - keep doing that for every
positive before calling it validated.

### Round 36 result: independent re-check of the CEF cut screen found a SECOND bug; screen NOT CONFIRMED
Subagent re-implementation (imports cef_rv unchanged): 2016-26 cut -143 vs other +126 (diff -268, t -3.02);
2003-14 cut -15 (median +41) vs +176 (diff -191, t -1.98). My R17 benchmark built the EW CEF index from
`pct_change` over LIQUID-ONLY rows, so a fund leaving and re-entering the liquid set produced a multi-day "daily"
return (worst in 2008-09). Fixed (`winsig_r17.py`, `winsig_r17c.py`, `winsig_r28.py`: returns on each fund's
consecutive bars, then averaged over liquid funds). Corrected numbers now match the independent run:
2016-26 diff **-255bp (t -2.9)**, halves -188/-363; 2003-14 diff **-191bp (t -1.98)**, halves -218/-165 -> the
registered confirm bar (t <= -2.0) is MISSED by 0.02. Cut windows cluster (2008-09, 2020), so t is if anything
overstated. Status: PLAUSIBLE avoid-screen, NOT validated. R28 (dead) re-uses the same helper; its verdict stands.
Other loop results do not use that helper (they benchmark with per-date means of per-row returns computed on full
panels).
Lessons: (1) "N prior values" rules must assert the values exist (pandas reductions skip NaN); (2) never pct_change a
FILTERED panel - compute returns on the full series, then filter. Both bugs were found only by independent
re-implementation of the two positives; both pushed a pass to a fail.

### Round 37 result: independent re-check of L1 (repeat loser) REPLICATES, with caveats
Subagent re-implementation (nx/shar_surv picks unchanged; gap in real trading sessions): repeat (gap 1-5) n 1,502
mean +74.9bp (median +47.2) vs non-repeat (no pick within 20 sessions) n 7,230 +36.9 (median +34.9); night-paired
**+103.4bp, t 4.11** (725 nights); halves +104.1 (t 2.55) / +103.1 (t 3.25); top-1%-trimmed means +41.6 vs +10.3.
Matches my +85 (t 3.4) in sign and size (my non-repeat arm included the 6-20 gap names; my gap used the pick-date
index, not trading sessions). Caveats it adds: raw gap buckets are NOT monotone (gap 1 +102.8, 2-3 +38.0 ~ none,
4-5 +99.8; 6-20 +33.8 = none), and after 2021-06 the medians differ by only ~8bp (tail-driven). Nights cluster in
stress episodes (t not corrected for serial correlation). Status: FORWARD CANDIDATE, unchanged; the only lead from
the loop that survived an independent re-implementation without a correction.

---
## LOOP END (round 38): search space exhausted at this data tier; final state
~85 judged cells + 6 diagnostics + 3 independent re-implementations. After the two bug corrections:
- **Validated: none.**
- **Forward candidate:** L1 repeat loser on the night leg (independently replicated; tail-driven; needs a candidate log).
- **Plausible (missed its confirm bar by t 0.02):** CEF-RV distribution-cut avoid-screen.
- **Real gross out-of-sample, cost-bound (all wait on a MEASURED pref/CEF execution cost):** PREF-CHAIN (2005-15
  gross +57bp, every year > 0, net +17 at 40bp RT; book +15%/yr vs +8% EW prefs 2010-26 with full pref crash beta),
  CEF pre-ex window (+30bp/9d, 23 years), CEF and preferred oscillator reversals (+10-24bp).
- **Dead:** every classic technical window pattern on every universe tried; breadth, gap, vol-state, residual
  reversal; CEF distribution increases; pref new issues; high-yield common pre-ex; sector cap; pre-ex timing of CEF-RV.
Why stopping: the remaining untested ideas fail the +8pp ceiling gate before a backtest (calendar effects in income
paper) or need data the repo does not have (call dates, NAV for preferreds, quotes for crosses). The one action that
would move three findings at once is the user decision below, not more backtests.
**User decisions:** (1) a log-only execution-cost shadow for CEFs/preferreds (official cross vs 15:59 NBBO mid,
plus a T-10 arm in the PREF-EX shadow); (2) a nightly candidate log for L1; (3) optionally log the CEF-cut flag in
the CEF-RV shadow. Each needs a REGISTRY entry in the same commit. Nothing was deployed or committed in this loop.

## DEPLOYED 2026-10-08 (user OK; copied to him, NOT committed or pushed - a `make pull` there would revert it)
- pref_ex_shadow: PREF-CHAIN T-10 arm vs PFF + measured closing-cross cost vs the 15:55-16:00 SIP mid; CEF-RV: cut42
  flag; new repeat_shadow (15:40 candidate log via executor hook, scored next morning); REGISTRY + research-shadows
  service updated; 450 tests pass locally and on him.
- Backfill read (2026-09-01..10-07, 16 ex-nights, 222 stable events): T-10 +44bp vs PFF night-mean (median event +56)
  vs T-1 +16bp; difference +28bp, t 0.94 (per-event means reverse: +34.7 vs +44.9) -> no verdict. MEASURED cross cost:
  median 0.0bp on buys, +2.8bp on the sell; means +1.2 (T-10 buy) / +3.6 (T-1 buy) / +5.7 (sell); p10-p90 about
  -35..+45bp per leg (the cross lands anywhere inside a ~20bp half-spread). Round trip ~7-9bp mean vs the 40bp the
  loop assumed. Net of measured cost: T-10 +37bp vs T-1 -2bp. cut42: 0 of 124 CEF-RV rows flagged so far.

---
## COMBO LOOP (/loop started 2026-10-08): do two signals TOGETHER beat the better one ALONE?
Runner `research/sim/combo.py` (reuses winsig.py panel/harness: signal on close t, buy open t+1, sell close t+5,
total-return excess vs EW universe, delisted included, last close as exit). Output `data/research/program/combo_out.txt`.
**Frozen combo gate (written before any combo was run; identical for every combo):** on 2016-01..2026-09, with
cost = 10bp RT stocks / 8bp RT prefs+CEFs (measured), the combo A&B must have ALL of
(1) combo net excess - max(net A alone, net B alone) >= +15bp/trade; (2) date-paired difference (combo trades vs the
better single's non-combo trades, same entry dates) NW t >= 3; (3) combo net NW t >= 3; (4) combo net halves > 0 and
improvement > 0 in both halves; (5) combo net median > 0; (6) combo net ex-top-5-days > 0.
A pass gets ONE look on 2003-15 (same gate, no changes), then an independent subagent re-implementation from this
spec before the word "validated" is used. Every combo counts toward N (ledger below); no tuning after a look.
Context: every single signal used here was already judged ALONE in Rounds 1-11 (mostly dead), so the singles are
not new tests; the combo is.

### Combo C1 (frozen before run): TTM squeeze release x IBS
Universe liquid SEP stocks ($5, $ADV20 >= $20M). A = F1 squeeze release (2sd(20) < 1.5 ATR(20) for >= 5 bars, then
not), any momentum direction. B = IBS < 0.2 on the bar. Combo = release bar that closes in the bottom 20% of its range
(mechanism claim: the vol-expansion bar that closes on its low is a forced liquidation into a range break, the
liquidity-provision setup IBS harvests, made more extreme by the squeeze). Cost 10bp RT.

### Combo C1 result: KILL (combo N 1)
A squeeze release net -10.4bp (t -2.4); B IBS<0.2 net -8.2 (t -1.6); combo n 14,137 net -4.7 (median -11.8, t -1.8,
halves -19.4/-8.2); improvement +3.5bp pooled but negative in both halves; date-paired -4.1bp t -0.5. Stock IBS is
not the ETF IBS edge at a 5-day hold, and the squeeze adds nothing. Family "vol-state x close-location" dead.

### Combo C2 (frozen before run): TMO oversold cross-up x recent loser (different family: momentum oscillator x
### forced-selling event). Liquid SEP stocks, cost 10bp RT.
A = F2 TMO cross-up with main <= -10 (unchanged). B = a total-return day <= -8% (closeadj/closeadj_{t-1}-1) on any of
bars t-4..t (the -8% night-rule loser event, repeated-window form). Combo = TMO turns up within 5 sessions of a -8%
day (mechanism claim: the oscillator turn marks the END of the forced-selling episode that L1 says is still running).

### Combo C2 result: KILL (combo N 2)
A TMO net -10.4 (t -1.1); B -8% day in last 5 net -11.4 (median -53.9); combo n 5,197 net +12.3 but median -25.1,
t -0.7, halves -0.9/-32.6, ex5 -37.3: the pooled mean is a few explosive rebounds; date-paired -12.4bp t -0.5.
The L1 repeat-loser tail is an OVERNIGHT effect on the night rule's picks; on a 5-day hold it is gone.

### Combo C3 (frozen before run): oversold x pre-ex window, $25-par income paper (family switch: dividend clientele)
Universe = pref panel (SEP preferreds + SFP ETD baby bonds, raw >= $5, $ADV20 >= $200k). Cost 8bp RT (measured).
A = F5 BB lower re-entry (>= 2 closes below the 20d lower band, then a close back inside). B = a Sharadar dividend
ex-date falls on bars t+2..t+5 (inside the open t+1 -> close t+5 hold; preferred ex-dates are scheduled, known at t).
Total return incl. the dividend (closeadj). Combo = oversold re-entry right before an ex-date (mechanism claim: the
pre-ex dividend-clientele bid (R21/PREF-CHAIN) absorbs the forced selling faster than an ordinary week).

### Combo C3 result: KILL (combo N 3)
A BB re-entry net +1.9 (t 1.6); B ex-date in t+2..t+5 net +21.3 (t 6.8, both halves +25/+24 - the known pre-ex bid,
touched); combo n 612 net +49.8 (median +22.6) but t 1.7, halves -7.4/+79.5, improvement -33/+55 by half,
date-paired +28bp t 1.2. Too few events; the lift lives in 2021+ only. Not tuned.

### Combo C4 (frozen before run): insider buy x oversold, liquid stocks (family switch: information x liquidity)
A = an officer/director Form 4 (incl. RESTATED-4) open-market purchase (code P, securityadcode NA, value > 0) with
SF2 filing date on bars t-4..t (filing date <= t; entry open t+1). B = 5-session total-return <= -5%
(closeadj_t / closeadj_{t-5} - 1). Combo = insiders bought within the last week AND the stock is down >= 5% over it
(mechanism claim: informed buyers + noise overselling = the price is below an insider's value AND under transient
pressure). Cost 10bp RT. SF2 starts 2008: the one confirm look on a pass is 2008-15, stated in advance.

### Combo C4 result: KILL (combo N 4)
A insider buy filed t-4..t net -15.5 (t -1.8; open t+1 -> close t+5 is AFTER the filing gap, consistent with H-POOL
living on the filing day); B 5d <= -5% net +3.1 (t 0.0); combo n 13,571 net -29.4, date-paired -2.8bp t -0.2.

### Combo C5 (frozen before run): short-term loser x LOW volume (Campbell-Grossman-Wang 1993; Llorente et al. 2002)
Liquid SEP stocks, cost 10bp RT. A = 5-session total return <= -5% (C4's B, unchanged). B = mean volume over bars
t-4..t <= 0.8 x mean volume over bars t-24..t-5 (quiet week). Combo = a drop on light volume (mechanism claim:
price moves without volume are liquidity/noise moves that revert; moves on heavy volume carry information).

### Combo C5 result: KILL (combo N 5)
A 5d <= -5% net +3.1 (t 0.0); B quiet week net -12.1 (t -5.7: quiet names lag the EW universe); combo n 119,837 net
+1.3 (median -25.3, t -0.3); date-paired -6.3bp t -0.6. Low-volume drops do NOT revert more at a 5-day hold in
liquid US stocks 2016-26.

### Combo C6 (frozen before run): short-term loser x CHEAP (family switch: fundamental anchor; Da-Liu-Schaumburg 2014)
Liquid SEP stocks, cost 10bp RT. A = 5d total return <= -5% (unchanged). B = Sharadar DAILY price-to-book in the
bottom quintile of that day's liquid universe (pb > 0 only; DAILY uses fundamentals as of their filing date; restated
`lastupdated` values are a small look-ahead risk, stated). Combo = a cheap stock that just dropped (mechanism claim:
a price drop without a fundamental change reverts faster where a value anchor exists).

### Combo C6 result: KILL (combo N 6)
A net +3.1; B cheap P/B net -4.0 (t -1.0); combo n 115,242 net +3.5 (median -15.0, t 0.2); improvement +0.4bp;
date-paired +5.4bp t 0.5. A value anchor does not speed the 5-day reversal. Stock 5-day combos of
{close-location, oscillator, event, volume, valuation} x reversal are now all dead (C1, C2, C4, C5, C6).

### Combo C7 (frozen before run): IBS x turn-of-month, liquid non-leveraged ETFs (family switch: calendar x liquidity)
ETF panel (SFP ETFs minus leveraged/inverse, raw >= $5, $ADV20 >= $20M). Cost 10bp RT. A = IBS < 0.2 on bar t.
B = bar t is one of the last 2 trading days of its calendar month (the open t+1 -> close t+5 hold then spans the
month turn). Combo = an oversold close into month-end (mechanism claim: scheduled month-start contribution/rebalance
inflows are the buyer that absorbs the oversold liquidity). Excess vs EW ETFs (removes the market-wide TOM drift).
