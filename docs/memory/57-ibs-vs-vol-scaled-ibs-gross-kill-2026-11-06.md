# IBS-VS (2026-11-06, N 1068 -> 1070): vol-scaled IBS sleeve gross, KILL

- Question: after the 2026-11-06 sell-off, size the OOS-verified IBS leg's GROSS by realized vol of the firing ETFs (z = sigma20 / own
  252d median), either more capital when vol is high (z^+1) or constant risk (z^-1), vs flat at matched maxDD. L fit on 2021-26, judged 2016-20.
- Not a duplicate of VT-IBS (cross-name split), add. 32 A5 (inverse vol-target of the whole book), Round 18 AT1/AT2 (vol-ratio gate), PROVOL (night).
- Result: both arms dead. Taxable (cap 2x, flat 1.25x): z^+1 +1.2pp CAGR at matched DD on 2016-20 but -0.9pp on 2021-26, Sharpe below flat in
  both, NW t -0.54, signal-day median -5.8bp, placebo 48th; z^-1 -5.2pp on 2016-20. Roth (cap 1x): z^+1 saturates at the cap (= flat), z^-1 -1.9pp.
  Theory (premium ~ sigma => Kelly ~ 1/sigma => z^-1 best) also failed on the judge window. Flat leverage (CLE cap 1.25x) remains the only IBS
  sizing lever; whole shares, 2016-20 taxable flat 1.25x: 15.6% / 17.5% / 17.7%/yr at $2.3k / $10k / $25k (maxDD ~ -18..-20%).
- Oversold V6 (SPY/QQQ RSI(2)<10 or 3-down, close -> open): shares the oversold-close state with IBS (index IBS<0.2 on 39-51% of triggers; IBS leg
  fires on 56-65%) but harvests the adjacent close->open window (+15..23bp both periods); the next open->open (IBS window) on those days was ~0 in
  2016-20. Related state, different trade; not the IBS edge at index level.
- Not tested: VIX/market-level scaler, GARCH/intraday-RV forecasts, other clips/caps, night leg (banned until NX), stocks.
- Data caveat: Sharadar SFP split-adjusted bars (local etf_daily.parquet absent), through 2026-10-05.
- Files: pre-reg + result `research/drafts/round1_prose.md` (Study IBS-VS); runner `research/sim/ibs_vs.py`; out `data/research/program/ibs_vs_out.txt`; NEXT.md row.
