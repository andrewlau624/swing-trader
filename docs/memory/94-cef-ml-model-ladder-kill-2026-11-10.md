# CEF-ML (N 1205-1207, 2026-11-10): learned ranking of CEF-RV candidates KILL; depth already carries it

Question: does Ridge (rung 2) or a shallow GBM (rung 4) rank CEF-RV signals better than the live depth sort (rung 1)?
Runner `research/sim/cef_ml.py` (needs scikit-learn: not in stvenv, used a uv venv), out `data/research/program/cef_ml_out.txt`,
pre-reg + result in round1_prose.md "CEF-ML". Trades = frozen rule on the Nasdaq NAV panel (cef_stress_trades.csv, live funds only),
label = exc vs EW CEF incl. delisted. Walk-forward annual refits 2016-26, purged by exit date; first model sees 2008-15 only.

- Prior coverage before this: only single features (depth SEL-CEF, category CEF-PEER, stress CEF-STRESS, tone CEF-TXT, NAV-fall,
  cut42, Dec tax-loss). No model had been fit.
- Judge (279 weeks with >= 3 signals, top third picked): Ridge vs depth +61bp t 2.07 but halves -10/+118, DSR 0.24 -> FAIL.
  GBM vs Ridge -34bp t -1.7 -> FAIL. Ridge filter (pred < 0 skipped) kept-minus-dropped +101bp t 3.75 but DSR 0.14 -> FAIL.
  IC: depth .110, Ridge .117, GBM .105. Ridge's top weight is depth every year.
- Slot replay %/yr vs depth: Ridge -0.1 / 0.0 / -0.5pp at $2.3k / $10k / $25k; GBM -0.6 / -1.9 / +1.2. No shadow.
- Fit-period map (2008-15, n 2,124, mean +128bp): depth Q1 +402 vs Q5 -46; pref_conv +415 (n 140), muni +229 (589) vs intl -48
  (287), sector -30; VIX top quintile +358 vs bottom +4; SPY dd worst quintile +319; smallest ADV +215 vs largest +22; lowest NAV
  vol -12; Nov +235, May +8. Mostly depth/stress/illiquidity restated: these are the "pay for panic spread" states (CEF-STRESS).
- Survivorship: death-hazard logit (only ADV matters) moves no delta by > 1bp; it does not bound the level bias (CEF-SURV99).
- Not tested: leverage, AUM, NAV total return, option-income as its own class, distribution announcement dates, discount
  SEQUENCES (path shape over the lookback), exit-side model, rung 3 sizing curve, rank/sign targets, other hyperparameters,
  Monday-open (OO) labels, pre-2008 data (CEFConnect panel gone), dead-fund NAVs.
