# REGIME-X (N 1160-1164, 2026-11-07): drawdown-control rules on the daily-bar book — all KILL

User priority: drawdowns. Book = 0.5 IBS + 0.5 night daily-bar form (REGIME-10M harness, Sharadar SEP/SFP delisted-complete, 5bp/side).
Per-leg cache `data/research/regime_x/legs.parquet` (1999-01..2026-09; 0.5/0.5 sum equals `upro_gate/book.parquet` exactly) — reuse it.
Judge 1999-2015 (base 16.0% CAGR / -25.7% maxDD, the DD is 2000-02); report 2016-26 (7.5% / -13.5%).
Gate: maxDD cut >= 1/3 AND CAGR give-up <= 20% in BOTH windows, Calmar > static de-lever at the same mean exposure, placebo >= 90th.

- N 1160 CREDIT (BAA10Y > 252d SMA -> cash, 44% OFF): judge 8.2%/-7.8% (give-up 49%), 2016-26 no DD cut, give-up 66%. KILL.
- N 1161 VIX30: OFF days are the book's best (+15bp vs +5 judge; +25 vs +2 2016-26, IBS +37 vs +2). KILL. Confirms add. 26a / OIL-SHOCK.
- N 1162 GZ-DD (e = clip((W/M-.75)/.25, .25, 1)): judge cut 33.3% give-up 13%; 2016-26 cut 18%, Calmar = static. KILL.
- N 1163 EQ-SMA (ungated book equity > 200d SMA): judge cut 45% give-up 19%; 2016-26 cut 18%, Calmar 0.63 < static 0.67, placebo 85th. KILL.
  Lag trap: book row d-1 holds IBS open(d)->open(d+1), unknown at close d; a lag-1 version looked like a near-pass (2016-26 cut 33%). Use lag 2.
- N 1164 SLEEVE 25% (whole shares, $2.3k/$10k/$25k identical within 0.3pp): TLT 2016-26 maxDD worse (-16.4%), GLD +return no DD cut,
  WTMF/DBMF cut DD 5-9% for 17-30% give-up; none beats 75% book + 25% bills on Calmar. KILL.
- Read: the book's drawdowns are not forecastable by state; stress states are where its liquidity-provision edge pays most. The only
  drawdown lever that survives is plain size (static de-lever) — and the Roth UPRO core's own trend gate (UPRO-GATE, separate).
- Not tested: 0.5x partial de-risk on stress gates, per-leg gates, HY OAS (FRED 3y only), breadth (no free history), pre-2011 MF proxies,
  intraday stops, noise leg, other thresholds (deliberately). Runner `research/sim/regime_x.py`, out `data/research/program/regime_x_out.txt`.
