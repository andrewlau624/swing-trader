# DEEP math round (N 1242-1257, 2026-11-21): price-only cross-section on liquid US stocks after 2010 is dead in every form tried

Origin: the user asked "look at stocks that went up in the 2026-10/11 selloff" and then for math-research-depth patterns; they picked all 4 branches.

- **PCA/RMT residual reversion** (Avellaneda-Lee, Marchenko-Pastur ~9 factors; N 1242/1248/1249/1253/1257):
  - The s-score has real gross information (placebo 100th percentile), about 1-4bp/day. It is dead after costs in every daily form: close-close LS/LO, K30, volume-time, overnight hold (gross 0), daytime open->close (+1.9bp gross vs ~20bp RT).
  - N 1242's LO "pass" vs SPY was an EW-universe-vs-SPY artefact (registration error). Benchmark vs the universe.
- **Path signatures** (Chen's identity, level 3 + lead-lag; N 1243/1252): they lose to a 4-feature snapshot (ret5, ret20, vol20, beta60). Both decay after 2010 (snapshot HGB 2011-26 +4.5bp/wk t 0.66; beta-matched negative).
- **Tail dependence / downside beta** (N 1244): crash-day information is all beta. Low LTD = high-idio-vol names, not defensive ones.
- **The user's question** (relative strength inside drawdowns, N 1250; rebound leaders, N 1254): after beta and sector, it does NOT persist; it slightly reverses (|rc| 0.02-0.03). The visible pattern in a selloff is beta.
- **TDA crash warning** (Gidea-Katz standardized / raw / cross-section H0, N 1245-1247): every form fails. The book's best days are inside stress, so any state off-switch removes them (same as REGIME-X). Cross-section H0 = mean correlation.
- **Vol ratio** (60d/20d sd, N 1255): nothing.
- **Thin names $2-10M in the night rule** (N 1256): a bigger bounce (+41bp/trade gross) but dead at the assumed tier_hi + 10bp. Live fills sit about 0bp vs the official print even under $10. The open question is whether Sharadar opens equal the official crosses in thin names (exp_thinauc report).
- **BUG (program-wide):** Sharadar SEP volume is split-adjusted, so closeunadj*volume ADV is lookahead (favours future splitters).
  - Audit: GAP-NIGHT N 1050 -> KILL as registered; QP-RUNUP weaker (book +4.8%/yr); EXDATE stands; live code clean.
  - Use close*volume. Helpers are fixed.
- Not tested: thin names on official crosses forward; non-US equity cross-sections; intraday-bar paths; s as a tilt inside existing legs; event-conditioned versions.
- THIN-AUC (official crosses 2016-26): thin per-$ = live per-$ (+33 vs +34bp), so the thin branch is closed. **Sharadar daily OPEN overstates night exits ~6.5bp/trade vs the official opening cross** (close is exact); NX's 2003-15 +3.07bp/night is an upper bound. Live fills remain the judge.
- IBS-AUC: the IBS leg re-priced on official opening crosses 2017-26 is unchanged (+29.7 vs +29.8bp OOS). The Alpaca ETF opens are unbiased; only Sharadar STOCK opens drift.
