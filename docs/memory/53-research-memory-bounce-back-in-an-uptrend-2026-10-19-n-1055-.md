# Research memory — "bounce back in an uptrend" (2026-10-19, N 1055-1056)

- Branch list first (rule): trend-filter+dip, indicator turn-ups, intraday level bounces and momentum pullback were already dead in the
  ledgers (W4/U1/F7/U5/AT3/TREND-NIGHT; U9/H5/F3-F5; VOLDAY/INPLAY/LEVEL-BOUNCE/STOP-RUN; ARETE-DIP). Two untested shapes were run.
- **HL-BOUNCE (N 1055): KILL.** Swing-structure higher low (k=3 pivots, rising pivot highs, first close back above the pivot bar's high),
  buy next open, excess vs EW liq universe: stocks H5 -5.5 / -7.4bp gross (2016-26 / 2003-15), ETFs -12.2 / -8.9; net -15..-22; higher
  low minus lower low -5..-10bp, t < 1.1. Deepest pullbacks worst. `research/sim/hl_bounce.py`, `hl_bounce_out.txt`.
- **BNC-IBS (N 1056): KILL.** On the 18 IBS ETFs, entering after an up-close on d+1 (open d+2 -> d+3) earns +12.4 / +6.2bp vs the
  live dip form +16.9 / +13.2; up-close minus down-close paired -0.3 / -7.7bp (t -0.1 / -2.1): confirmation carries no information,
  and the non-bouncers are the better buys in 2016-26. `research/sim/bnc_ibs.py`, `bnc_ibs_out.txt`.
- **Class verdict:** "buy the confirmed bounce" is closed at the daily tier in every form tried (structure, up-close, reclaim, indicator
  turn-up, intraday level). The repo's durable edges buy the dip close/next open BEFORE the bounce (IBS, night); waiting for confirmation
  forfeits them. Not tested: stop/target structure exits, weekly bars, breakout-level retest, 3-10d deep momentum pullback.
- **DEEP-PULL (N 1057) + BRK-RETEST (N 1058): KILL, 4/4 cells** (level 2 of the tree). Bounce from a 5-20% pullback in recent
  52w-high names, 10d hold: stocks -1.6 / +3.5bp gross, net -11.6 / -6.5; ETFs net -7.7 / -32.5. First touch-and-hold of a 50d
  breakout level, 5d hold: stocks +8.3 / -1.0 gross, net -1.7 / -11.0, and the FAILED retest earns the same. `research/sim/pull_retest.py`.
- **Tree closed (two levels down):** confirmed-bounce entries are dead in every form the user's idea implies at daily tier; only weekly
  bars remain unrun (ceiling < 1pp). Program N = 1058.
- **ETF-PD (N 1059): KILL; ETF premium/discount family CLOSED delisted-complete.** CRSP MF daily NAV (6,602 ETFs 2010-26, pulled to
  `data/research/etf_pd/nav.parquet`) x Sharadar SFP: deepest-discount decile +0.9bp gross/session, NAV moves toward price
  (+23..+61bp per 100bp), price only -13..-19bp; tails are ~20bp so the residual is ~3bp. Fallen-angel issuer equity ceiling-killed
  on paper (~0.4pp/yr). Program N = 1059.
- **F-SALE2 (N 1060): KILL; flow-pressure family closed at every horizon.** CRSP MF holdings + monthly TNA/returns (no MFLinks needed;
  server-side yearly queries, `data/research/fsale2/`): fire-sold decile -273bp in the pressure quarter (t -6.3, monotone) but +15bp next
  quarter (t 0.5) and -183bp over 6 quarters: information, not a snap-back. F-SALE (N 1054) decile labels were INVERTED (sign comment
  wrong); KILL stands, mechanism statement withdrawn. Rule: print the mean signal per decile beside its label on every sort.
  Program N = 1060.
