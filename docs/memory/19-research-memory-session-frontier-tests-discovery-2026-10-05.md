# Research memory — session "frontier tests + discovery" (2026-10-05)

- **Study BSPD (bond-SPDR premium/discount + creation flow, N 834 -> 835): KILL.** JNK/SJNK/SPSB/SPIB/SPLB,
  2007-12..2026-10, navhist + raw closes. Gross market-adjusted spreads ~0 (+0.32/-1.54/-1.25bp); every arm negative
  net (net_1x -6.6..-9.5bp, median ~-8, clus_t -3..-12), wrong sign, same in all sub-periods. No reversion to harvest.
  With SPY (ETC) and broad SPDRs (EF) rejected, the **ETF premium/discount + creation-flow family is CLOSED**.
- **Study DM (dividend-month clientele premium, N 835 -> 836): KILL.** Monthly payer-vs-non-payer +66.8bp (t 2.51,
  ex-top5 +31.2) passes the registered gates but is a size/value tilt (164 payers vs 3,081 smaller benchmark names);
  the ex-date mechanism test (T-5..T+5 vs SPY) is -6.9bp, median -19.7, t -0.04, and the monthly spread dies at 3x
  cost (-23.2bp). Panel 2021+ only. Hartzmark-Solomon does not survive at retail size/cost.
- **P01 EDGAR discovery layer built** (`swingtrader/daily/forced_flow_discovery.py`, REGISTRY "Forced-flow discovery
  (EDGAR forms)", `make forced-flow-discovery`): scans SC 14D-9 / DEFM14C / 425 / 8-K 2.01-5.01 / 25-NSE / S-4 /
  SC 13E3, flags per-holder-capped guaranteed-floor events to `state/forced-flow-discovery.jsonl`; discovery-only, no
  orders. Dry run 3 sessions: 85 docs, 1 candidate. The only new forward mechanism this cycle.
- **No new runnable edge. The free frontier is exhausted.** Remaining open ground is DATA-LIMITED/BLOCKED (borrow
  fees, PIT ratings, per-fund NAV) or the paid signed-gamma source, whose free proxy already failed the untouched
  2016-20 window. Do not re-open BSPD/DM/CEF-TL or the ETF-discount family without new data.
