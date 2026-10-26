# Research memory — session "exact night + noise audit" (2026-10-04, part 3)

### PHASE 1 (exact): the night leg at the live 15:40 rule, pre-2021
- `research/sim/night_exact_pre2021.py` (out parquet `night_exact_pre2021.parquet`): Alpaca
  SIP MINUTE bars 2016-2020 for candidate down-days (low touched -8%), exact signal at 15:40
  (day_ret = p15:40/prev_close-1 <= -8%, IBS(15:40) < 0.10), buy the close, sell the next open.
- Result: 2016-18 **+3.0bp (t 0.25, ex-top-5 -6bp)**; 2016-19 ex-2020 +26.3bp (t 2.57);
  2020 +76.5bp; pooled +63bp. Per year: 2016 -2.1, **2017 -23.1**, 2018 +15.5, 2019 +91.9,
  2020 +76.5. **After 7.5bp/side cost: 2016-18 -12.0bp, ex-2020 +11.3bp (t 1.10).**
- **Verdict: the exact night leg does NOT have a stable pre-2021 edge. The daily-close proxy
  (+108bp) was flattering; the positive exact average is a 2019-2020 high-volatility regime
  effect. Do NOT size up the night leg; it remains unproven as durable alpha and is largely a
  vol-regime bet (consistent with the reversal premium scaling with vol).**
- Caveats: survivorship-limited (inactive names in, fully-removed dead tickers out); minute
  close as the 15:40 proxy. **This 2016-2020 window is the "touched" one: the run is exploratory.
  The formal Study NX judge is 2003-2015 on delisted-complete vendor data (round1_prose.md, N
  806->809; purchase awaiting user OK). Do not treat this run as the NX verdict.**

### PHASE 2: intraday noise residual audit
- `research/sim/noise_audit.py` (out `data/research/program/noise_audit_out.txt`). The ~13%
  residual is **NOT** a vol-targeting artifact (unlevered alpha 10.2%, t 4.29; levered 17.8%,
  t 3.93) and **NOT** an omitted market factor (QQQ beta ~0; alpha unchanged adding QQQ/IWM/UVXY;
  it is long-vol: UVXY beta +0.03-0.05, t 7-8).
- But it is **fragile**: by year the levered mean is 2016 -2.6, 2017 +2.3, 2019 +0.3, 2025 +0.1,
  2026 +2.5 bp vs 2018 +19.8, 2020 +11.1, 2022-24 +9-11bp. And **cost-dominated**: 1.65 fills/day;
  Sharpe 1.07 at 0.5bp/fill, 0.19 at 2bp, -0.94 at 4bp.
- **Verdict: the intraday residual is genuine (not an artifact) but time-unstable and entirely
  inside the execution cost; it is not a durable standalone edge at realistic flip costs.**
- Factor rule: the noise leg is intraday (open->close), night is close->open, IBS is
  open(d+1)->open(d+2). Factors MUST be window-matched; close-to-close SPY is wrong.

### PHASE 3: execution realism
- Night: entry = 16:00 close auction, exit = 09:30 open auction. Research uses 7.5bp/side; the
  OOS above is quoted both at 0 and 7.5bp/side. Live measured ~0bp but on 34 fills (too few).
- Noise: 30-min bar-close execution, ~1.65 fills/day; the edge is gone above ~1.5-2bp/fill.
  Never assume midpoint; the flip pays the spread each leg.

### PHASE 4: OPRA data status (not yet tested)
- Databento OPRA.PILLAR `statistics` (daily OPEN INTEREST, 2013+) + `definition`
  (strike/expiry/type) + `cbbo-1m` (NBBO). Verified: ~$1.75/symbol-week (SPY.OPT), ~$1.88
  (QQQ.OPT) for OI; ~$180/yr for SPY+QQQ. Key in `.env`.
- **Dealer gamma / OI concentration / expiration flows = DATA TARGET (accessible, paid).** The
  mechanism to test is a structural constraint on the UNDERLYING from options positioning, not
  another calls/puts/condor backtest.

### Frontier ledger (updated)
| mechanism | status |
|---|---|
| Night-leg durability | **weakened**: exact pre-2021 rule is ~0 outside 2019-2020 after costs; do not size up |
| Intraday noise residual | **genuine but fragile**: real alpha, cost-bound, unstable across years |
| Dealer positioning / vol surface | **TARGET** (Databento OPRA statistics; ~$180/yr SPY+QQQ) |
| Borrow / HTB / recalls | **BLOCKED** (no fee history); proxies FINRA SI (2020+) + FTD |
| Fallen angels | **TARGET** (no free PIT ratings; TRACE/bond-spread proxy) |
| ETF creation/redemption | **TARGET** (scrape shares-outstanding/NAV) |
| Margin cascades | **NO DATA** (price proxy only) |
