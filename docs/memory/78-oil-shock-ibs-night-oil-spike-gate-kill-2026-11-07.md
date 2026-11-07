# OIL-SHOCK (N 1111-1112, 2026-11-07): scale MR legs down while crude spikes — KILL

- Rule: FRED DCOILWTICO as of signal day; P = WTI 20-obs return >= +20%, S = WTI at a 252-obs high; arm = IBS leg to cash on ON sessions.
  Judge IBS 1986-2020: ^GSPC IBS proxy (close->close, Yahoo opens stale) 1986-93-01, SPY open->open to 1998, EQ18 Sharadar 1999-2017-02,
  ibs_oos 2017-20. Night + book descriptive (1999-2015 Sharadar, NX judging reserved). Runner `research/sim/oil_shock.py`, out
  `data/research/program/oil_shock_out.txt`, data `data/research/oil_shock/`.
- P ON 3.8% of sessions, 41 episodes but most are post-crash rebounds (1986, 1999, 2009, 2016, 2020); real stagflation shocks n ~3-5.
  IBS ON +0.04 vs OFF +0.59bp/session, placebo p 0.44, halves mixed, ex-1990 positive; x0 arm: no maxDD gain. S is wrong-signed (ON better).
- Only bad episode: 1990 Gulf War (-5.0% on ON sessions). 2008 H1 +1.5%, 2022-01 -4.6% / 2022-03 0, 2026-03..04 +10.0%.
- VIX overlap: 37% of P-ON days have VIX>25 (P-ON = 9% of VIX>25 days); P's damage lives in that subset -> vol-gate relabel. S ~independent.
- Night leg earns MORE in spikes (1999-2015 +30 vs +10bp/session). Book x0 costs ~1.7pp/yr pre-2016, ~2pp/yr 2021-26 for <=2.4pp maxDD.
- Not tested: other thresholds, Brent/products/EIA shocks, OVX sizing, oil AND equity-down conjunction (closed class), dropping energy
  ETFs from IBS picks in spikes, pre-1986.
