# Research memory — PREF-EX sell rejections + U5/U6 kills (2026-10-27)

- **PREF-EX live had never sold a position.** Every MOC sell since 10-21 was `REJECTED` ("Short sales are not permitted in
  this account type"). `SchwabAdapter._instructions` looked up the holding by the order symbol (`GS/PRD`); Schwab's positions
  endpoint keys it `GS-D`, so `have=0` and the order went as `SELL_SHORT`. Four positions (~$1,490: GS-D 47, GS-A 18, ADC-A
  10, PSEC-A 10) sat past their ex-dates; the Roth book's free equity fell to $429 vs the $1,000 sleeve (43% capital).
  Fix: `_position_qty` matches `symbol` or `uniformSymbol` (`swingtrader/daily/brokers.py`); `pref_ex_live` logs
  `sell-rejected` and keeps `state['open']` for retry. Verified on him: all four resolve to `SELL`; next 15:25 run sells.
- **Overlay sizing cap.** PREF-EX and CEF-RV now pass `equity = min(account equity, DAILY_ROTH_CAPITAL)` ($1,000) instead of
  the whole Roth account ($7.7k, mostly the index core). They no longer size 50% of money that is not the book's. The night
  leg still gets what the reservation hooks leave; a hard 50/50 split is an open user decision.
- **U6 crypto-ETF IBS (N 1067): KILL.** 371 trades, 2024-01..2026-09: +12.0bp gross (median +8.7, t 0.61), -3.0 at 7.5bp/side;
  vs the live 18-ETF leg same-day -34.1bp (t -1.75), 2024 +54.2 / 2025-26 -81.2 (t -3.70), ex-best-5 -52. Universe extension
  18->21: -10.0bp/day (t -1.88), -24.2 vs live on crypto-picked days. `research/sim/u6_crypto_ibs.py`.
- **U5 fire-sale 2-4q holds (N 1068): KILL.** 83,659 stock-quarters, 64 quarters 2009-24, ~131 names/q. Event-quarter D1
  -273bp; forward h=4 -62bp (median -3, t -0.79, NW -0.52, ex-top-5 -144), 2009-17 +66 (t 0.79) vs 2018-26 -225 (t -1.63);
  median stock -296bp. D10 -195 at h=4 (t -2.07). No reversal at any 1-4q horizon. `research/sim/u5_firesale_hold.py`.
- **Beta/alpha (already measured, no new run).** 2021-26 book: raw 38.6%/yr, alpha 24.5% t 4.26, R2 0.19, systematic 37%
  (MKT +10.2pp/yr). Night: alpha 17.0% t 3.47 (sys 16%). IBS: daily alpha 5.2% t 1.85, weekly alpha 0.0 (MKT beta 1.01 t 15,
  sys 100%). The night leg is the alpha; the IBS sleeve is a beta sleeve. `research/sim/beta_alpha_iso_out.txt`.
- **Process note:** U5/U6 were registered in `round1_prose.md` after the outcomes were read (post-hoc), disclosed as
  exploratory, not clean pre-registrations. With these two, the cheap Tier B extensions are exhausted; next is Tier C data
  (EDGAR full-text / daily ETF shares outstanding) or a user sizing decision, not another in-design-space variant.
