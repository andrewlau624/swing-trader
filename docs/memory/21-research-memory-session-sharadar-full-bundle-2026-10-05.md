# Research memory — session "Sharadar full bundle" (2026-10-05)

Data: full Sharadar bundle at `~/data/sharadar` (SEP stocks + SFP funds both 1997-12-31..2026-10-05, delisted included;
insiders=SF2 **2008-01-02+**; actions, sp500, fundamentals, daily, holdings), permaticker ids; loader
`github.com/andrewlau624/sharadar-data` (`from sharadar import prices, tickers, actions, table`). Daily bars only — no minute
data, so every 15:40/intraday rule is a labelled daily-close proxy. Backup at `~/Downloads/sharadar-backup/`. Program N 838 -> 839.

**Verdicts (all one-look, pre-registered in `round1_prose.md`; each adversarially checked before acceptance):**
- **SHAR-IBS (N 839): WEAK, not PASS.** The live IBS leg on the untouched 2003-15 ETF window: tier net +4.99bp, day-clustered
t 1.03 (gross +16.15bp t 3.34); halves +11.84 / -4.69; median +10.69bp; ex-best-5 +1.84bp; beta-adj SPY residual -8.58bp
t -2.89; 2/5 registered checks. **The positive gross is entirely eaten by `tier` costs (5bp/side), and the beta-adjusted
residual is negative pre-2016** (vs the +6.7bp/day 2017-20 residual in `beta_alpha_iso`). Read: the IBS liquidity premium is
real but **weak and cost-bound in the 2003-15 regime** and its pre-2016 alpha (net of beta) is not there; 2003-15 is now
TOUCHED — no IBS variants or tuning on it. (A verifier found a raw-open split bug on 2 leg-days; fixing it moved FAIL->WEAK.)
Runner `research/sim/shar_ibs.py`.
- **H-POOL on Sharadar (N 796): PASS at `tier`, NOT ROBUST.** The registered pooled insider-buy open->close rule, run
survivorship-free; SF2 starts 2008 so the judge is 2008-01..2015-12: tier +21.1bp, t 2.71, n 29,285; halves +37.2 / +10.6bp;
gross +40.2bp; **tier_hi +11.4bp t 1.46 (fails), ex-top-1% +5.4bp, DSR 0.842, decays to ~0 by 2013-15** (crisis/high-vol
tilt). Placebo 100th pct. The insider-buy family therefore transfers to a pre-2021 decade the program never saw, but only as a
conditional/crisis leg; keep it forward (ID3 shadow) and do not size up on this alone. Runner `research/sim/hpool_sharadar.py`.
- **SHAR-SURV (diagnostic): the 2021-26 night-leg results were survivorship-flattered by ~+4.1bp/trade at `tier`**
(survivor-only +18.86bp t 1.99 vs delisted-complete +14.75bp t 1.81; flat 2.5bp/side +33.95 vs +30.14). Delisted names are
24.1% of eligible but 16.0% of picks; the gap is one mis-valued -100% merger plus a 2021-23 concentration. Small but real:
quote night-leg panels as delisted-complete. Runner `research/sim/shar_surv.py`.
- **SHAR-CRASH (diagnostic, no N):** daily-bar 0.5 IBS + 0.5 night, no noise leg. 2000-02 cum +278%, maxDD **-24.07%**
(trips the -10% lever gate, not the -25% halt); 2008-09 maxDD -9.86%; 2011 -8.35%; 2015-16 -8.25%. The `-25%` halt would
never have fired in these windows; the `-10%` lever gate would have in 2000-02. Daily-close proxy is optimistic (~1.7x vs
the exact 15:40 rule per NX). Runner `research/sim/shar_crash.py`.
- **Dropped before testing (research-priority gate):** structural events (S&P 500 add/delete, spin-offs, reverse-split
round-ups) — S&P flow is in the announcement gap, spin-off effect in the distribution gap, round-ups ~$370/yr; all <
+8pp/yr at $10k. No generic fundamentals factor mining. Bounded errors found+fixed by adversarial checks: a raw-open
split bug (SHAR-IBS) and a dropped -100% delisting-outcome bug (SHAR-CRASH).
- **Net:** the bundle's new evidence does not add a new edge; it **qualifies two live legs** — IBS is weaker and
cost-bound in the oldest regime, the night leg is ~4bp/trade less good once delisting is included, and the insider-buy
family is validated-small/conditional on 2008-15. Nothing here changes live sizes; all sizing is a user decision and the
data-buy gate is vindicated (the open pre-2016 questions are now answered).
