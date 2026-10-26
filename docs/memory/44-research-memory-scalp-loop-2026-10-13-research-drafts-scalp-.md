# Research memory — scalp loop (2026-10-13, `research/drafts/scalp_loop_ledger.md`)

- **SECT-LAG (N 978): KILL.** Sector-ETF 2-sd 5-min move -> thin laggard constituents: gross +0.08bp over 1-15 min (TAQ 2010-14), c ~9bp;
  no cross-asset catch-up survives the first minute even pre-2015. Judge era 2015-19 untouched for this class.
- WRDS standby is read-only (no temp tables) and NBBO day scans are ~40s/query: always pass an explicit `sym_root IN (...)` list (15s -> 0.5s).
- **Scalp cost table (Alpaca SIP 2018/2025, `scalp_cost_out.txt`, ledger):** RT c median >$1B 3-10bp (midday ~6), $10-50M 12-78bp, ETFs ~0.5bp;
  limit TP "through" fill rate ~half of "touch". A single-stock scalp needs >= ~2x these in gross 1-30 min drift.
- **SCALP-CLF (N 980): KILL.** Price/volume-path GBM for +30 before -30bp: top-5% p 0.43 vs p* 0.56-0.62; time-shift null equal. Path
  features forecast volatility, not direction.
- **ISO-BURST (N 979): KILL.** Large-cap ISO buy sweeps: drift vs matched control ~0 at 1-10 min (TAQ 2010-14). After SECT-LAG/ISO/CLF:
  no minute-scale directional footprint found; the scalp problem is zero gross drift, not cost.
- **RETAIL-HERD (N 981): KILL.** First-hour BJZZ retail buy imbalance in mid caps: no intraday continuation (fades -4.5bp by +60m, ns).
- **STOP-RUN (N 983): KILL.** Prior-day-low breach + volume burst: 0.14 events/day in >$500M names; the burst arm falls (-14.5bp/30m) while
  quiet breaches revert. No stop-cascade overshoot.
- **LEVEL-BOUNCE (N 984): KILL.** Quiet prior-day-low touch in mid caps: +3bp gross, same as a placebo level; prior-day levels carry no
  support liquidity worth a scalp.
- **SCALP-OFI (N 982): KILL.** Order-flow classifier (OFI, quote imbalance, ISO, BJZZ): top bucket p 0.38 vs p* 0.61, drift ~0.
- **CLASS VERDICT (checkpoint 2): minute-scale directional scalps in single US stocks are dead at retail costs** — no signal family moves
  1-60 min drift by more than a few bp (7 studies). The loop moved to auction-executed session-horizon trades (c ~ 0).
- **UPG-DAY0 (N 985): KILL.** Pre-open upgrade, open cross -> close cross: +10bp in 2010-14, ~+2bp (t 0.4) in 2015-19. Post-hoc pocket
  (gap <= 0, +28bp) tested below.
- **ETF-CLF (N 986): KILL.** Cross-asset ETF classifier: top bucket p 0.46 vs p* 0.57; ~2bp/30m drift. ETF minute-scale scalps also dead.
- **UPG-POCKET (N 987): KILL.** UPG-DAY0 pocket gap <= 0 on untouched 2020-24: n 1,496, net 2bp/side -3.7bp (t -0.35), ex-top-5 -8.6, halves -8.2/+6.1; equals all gap<=0 name-days. Post-hoc pockets of a dead rule are mining artifacts; UPG family closed.
- **GOLD-IFVG (N 988, 2026-10-15): closed unjudged, treated dead.** Reddit "first 15m IFVG in Asia, gold, 1:1" = 50% in its own claimed month;
  outside systematic tests of SMC/FVG/order blocks match random entries. ICT-style chart patterns are a closed class; no reopen without a mechanism.
  Reddit access: reddit.com and PullPush block/429 this machine; Arctic Shift API works with a User-Agent and ~6s pacing (title search on big subs).
- **VOLDAY (N 989-993, 2026-10-15): KILL all 5.** Retail alert setups (ORB15, VWAP reclaim, HOD break, flush reversal, gap fade) on a
  point-in-time top-10 realized-vol, ADV >= $500M watchlist, Alpaca SIP 1m 2016-26, 46k trades: net -5..-15bp/trade at 5bp/side; breakout arms
  ~+3bp over random entries (tiny real continuation), cost 10bp. Volatile names do not rescue day-trading alerts; class closed.
- **INPLAY (N 994-996, 2026-10-15): KILL all 3.** In-play scanner (RVOL30, gap catalyst, two-way deep-liquidity names, PDH/PDL/OR/VWAP levels) x
  fade / burst / bot-direction mix, 2019-26, 23k trades: net -8.5..-14.4bp/trade; fade and the direction score are worse than random; no scanner
  feature separates good trades in both halves. Day-trading alert scanners on bar data are closed (with VOLDAY, Lab-AS/AU, scalp loop).
