# CRASH-B: rolled tail puts on SPY (N 1025, 2026-10-18) — VERDICT: KILL at a 1.2%/yr budget
Pre-reg: `round1_prose.md` "Study CRASH-B". Runner `research/sim/crash_b.py`; out `data/research/program/crash_b_out.txt`; cache `data/research/crash_b/`.
Data: OptionMetrics opprcd 2005-01..2025-08-29 (SPY secid 109820, 5.2M put rows, DTE 15-130), far-side fills (buy ask / sell bid), no commissions.
Rule: first trading day of each month buy the ~90d put nearest 90% of spot, spend 0.10% of account (1.2%/yr); sell at bid when delta <= -0.70 or DTE <= 21.

## Gate results (calendar-year net P&L of the put book, % of account, after premium)
| arm | 2008 | 2020 | 2022 | cum 2010-19 net (spent) | worst non-crash yr | gate |
|---|---|---|---|---|---|---|
| PUT10 (primary) | +1.12 (0.9x budget) | +2.37 (2.0x) | +0.06 | -6.34 (12.0) | -1.17 | FAIL |
| PUT10 M0 hold-to-DTE21 (ref) | +1.63 | +0.21 | -0.11 | -7.70 | -1.48 | FAIL |
| SPR 90/75 | +0.78 | +1.47 | +0.31 | -6.18 (11.7) | -1.40 | FAIL |
| COND-IV (bottom tercile IV) | +0.07 | +1.01 | +0.20 | -3.23 (5.5) | -0.95 | FAIL |
| COND-SMA (SPY<200d) | +1.12 | -0.19 | -0.35 | -1.18 (1.8) | -0.35 | FAIL |
Gate needed >= +12% in both 2008 and 2020 (10x the 1.2% budget). Best arm reached 2.0x. Out lines 3-168.
Bleed in non-crash years is <= budget by construction (a few years exceed it because the M0/SPR arms lose the full premium plus spread).
Best single trades: 14.9x (Feb-2020 put), 11.6x (Jan-2020), 9.0x (Jul-2011), 9.0x (Feb-2025). 2008 best was 11.8x (M0, bought 2008-09-02).

## Why it fails (structural, not a tuning issue)
- 0.1%/month buys a put whose notional is only ~7-8% of the account (90d 10%-OTM put ~1.3% of spot at normal IV). A -46% 2008 or -34% 2020 move
  pays at most ~(drop-10%) x 8% x a few live rungs = 1-3% of account. Payoff ratio is high per dollar (10-15x) but the dollars are tiny.
- The delta<=-0.7 monetization sells near -8..-12% from strike and forfeits the rest of the fall; holding (M0) is better in 2008 and worse in 2020.
  Either way the gate fails by ~5x, so the monetization choice does not rescue it.
- Combined with 100% SPY (out 171-178): SPY alone 7.80x / CAGR 10.46% / maxDD -55.2%; SPY+PUT10 7.11x / 9.96% / -54.7%; +SPR 7.22x / -54.8%;
  +COND-IV 7.39x / -55.2%; +COND-SMA 7.72x / -54.6%. In the crash legs: 2008-09..2009-03 SPY -46.1% -> -45.3%; 2020 -33.7% -> -31.5%.
  The puts cost ~0.5%/yr of CAGR (~10% of terminal wealth over 21y) and cut maxDD by <1pp: they neither raise terminal wealth nor hedge.
- To hedge meaningfully you need ~10-20x the budget (a real hedge ratio), i.e. an insurance policy costing 10-25%/yr of the account. That is a
  different decision (de-risking), not a "profit from a crash" side bet.

## Whole contracts (2025 medians, out 180-184)
SPY contract notional $59k; 90d 90%-put ask $520; 90/75 spread debit $394 (XSP = SPX/10 has the same ~$59k notional: no help).
| account | 1.2%/yr budget | puts/yr affordable | ONE put per quarter costs |
|---|---|---|---|
| $2.3k | $28 | 0.05 | 90%/yr of account (infeasible) |
| $10k | $120 | 0.23 | 21%/yr (spread: 16%) |
| $25k | $300 | 0.58 | 8.3%/yr (spread: 6.3%) |
Smallest account for 1 put/month at 0.1%: $520k; 1 spread/month $394k; 1 put/quarter at 1.2%/yr $173k. Below ~$170k the program cannot even be run at its own budget.
Lower-notional ETFs (QQQ/IWM/sector) were not tested; they shrink the contract, not the payoff-per-premium, so the gate result carries over.

## MODEL, not a backtest: a Great-Crash-scale case (1929-32)
No option prices exist before 1996; CRSP vwretx (crsp.dsi) price index, 1929-09-03 peak to 1932-07-08 trough = -86.3% (first leg to 1929-11-13: -43.8%).
Same rule and budget; puts priced by Black-Scholes (r 3%, no dividends) at sigma = k x trailing 20d realized vol (floor 12%); far-side half-spread
1.9% of mid (2008 median); monetize delta <= -0.7 or DTE <= 21. Out lines 186-196.
- Measured put-IV/RV20: 0.93 in 2008-09..2009-03, 0.86 in 2020-02..04 (k=0.89), but 1.68 over all days. The crash-window ratio is low because RV is already
  spiking; it makes PRE-crash puts absurdly cheap (Sep-1929 put 0.24% of spot at RV 17%), so k=0.89 is an upper bound on payoff, not an estimate.
  k=1.68 prices calm-regime puts at a realistic ~1.8% of spot.
| pricing | 1929 | 1930 | 1931 | 1932 | cum 1929-06..1932-12 |
|---|---|---|---|---|---|
| k=0.89 (generous) | +14.0 | +29.7 | +9.0 | +1.3 | +52.6% = 43.8x budget |
| k=1.68 (realistic calm IV) | +1.9 | +3.6 | +1.1 | -0.2 | +5.7% = 4.7x budget |
- First leg (puts bought Jun-Oct 1929, n 5) vs grind (bought 1930-01..1932-06, n 30): k=1.68 mean multiple of premium 5.7x vs 2.6x, net +2.3% vs +4.8% of account.
  Early puts are cheap (IV low before the break) and pay a few multiples; once RV20 is 25-90% the 10% OTM put costs 6% of spot (Jul-1931) and the same 0.1% buys a third of the
  notional, so the grind pays less per premium but still positive in aggregate because the decline persisted for 3 years.
- Reading: even in an -86% world, a 1.2%/yr tail-put budget returns ~5x budget (+6% of account) under realistic pricing, vs ~-86% on a 100% equity book. It is "a small coupon",
  not a hedge or a windfall. Only if implied vol is priced at realized (k~0.9) does it clear 10x, and that is the assumption most likely wrong before a crash.
- Not modeled: skew, 1929 margin/credit conditions, dividends (~5% yield), market closures, bid-ask blowout in the gap, 1930s counterparty risk.

## Systemic and access risks (flagged, not tested)
- OCC clears all listed US options and is the guarantor: if it were impaired in a Great-Crash event, long puts are the instrument exposed to a payoff-side failure (the crash is exactly when you collect).
  Practically it survived 1987, 2008 (Lehman) and 2020 intact; 1987 had a clearing-member scare.
- Broker failure: Schwab holds the position; SIPC covers up to $500k per customer (securities, cash <= $250k) against broker insolvency, NOT against market loss, and does not make an
  uncollectable payoff whole. Options positions are customer property and are normally transferred, but delays in a failure can freeze exits during the very window you need them.
- Gap/halt risk: market-wide circuit breakers and single-name halts can stop you from selling; bid-ask on SPY puts widens in the gap (the 1.9% half-spread is a calm/crisis-2008 median, not a gap price).
- Position limits: irrelevant at this size (SPY limit ~250k contracts). Early exercise / assignment risk only on the short leg of a spread (25% OTM short put can be assigned deep ITM).
- Roth/IRA: long puts and debit spreads are permitted in IRAs in principle, but the Schwab options approval LEVEL needed (and whether spreads need a higher level than long options)
  is UNVERIFIED. Roth cannot margin or short; a debit spread is a defined-risk cash-paid position. Not verified in the account.
- Tax: puts monetized in a crash are short-term gains in a taxable account (taxed at ordinary rates in the year the book also has losses); Roth is tax-free. Not modeled.

## Verdict and unverified
KILL at the registered budget/gates: not the best arm either (COND-SMA bleeds least, 1.8% over 2010-19, but misses 2020). A 2008/2020-scale episode pays 1-2x the annual budget, the
Great-Crash model pays ~5x under realistic IV, and the program needs ~$170k+ to run in whole contracts. Only 2 real crash episodes in the sample (one-look, all touched).
Unverified: options approval level; commissions (~$0.65/contract, ~1-3% of a $520 put); OptionMetrics EOD quotes vs executable NBBO in the gap; 2025-09+ data (OptionMetrics sample ends 2025-08-29);
the combined-book curve scales put P&L by wealth and ignores the small put-book exposure to SPY returns (slightly understates the hedge).
