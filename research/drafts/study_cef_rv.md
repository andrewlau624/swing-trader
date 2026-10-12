# Study CEF-RV — discount-to-NAV reversion on the CEFConnect weekly panel (N 859 -> 860)

Registered round1_prose.md 2026-10-06 (machinery-development; FIRST two-leg study). Runner
`research/sim/cef_rv.py`; out `cef_rv_out.txt`; trades `data/research/cefconnect/cef_rv_trades.csv`;
panel `data/research/cefconnect/cef_panel.parquet` (355 live funds, weekly 1996-2026, free).

**Result (one look; PASS on every registered gate).** 3,765 trades / 336 funds / 2016-2026.
Mean net **+473.8bp/trade** (50bp Rt), median +358.8bp, weekly-clustered **t 11.29**, hit rate
**77%**, halves +396.9 / +287.7bp, ex-top-5-funds +433.0bp, ex-top-5-dates +354.4bp, 3x-cost shock
+373.8bp. Frozen bands: enter disc <= own trailing-52w 10th pct, exit disc >= own median; max hold
26 weeks (811 of trades carried to the cap... recorded in the csv, hold weeks mean 14.0, median 9).

**Verdict: PROMISING-SURV-LIMITED** (pre-registered cap). Panel = LIVE FUNDS ONLY: dead CEFs would
carry the unresolved discounts; no free delisted-complete NAV source (CEFConnect 404s dead
tickers). A PASS cannot upgrade without a survivorship-corrected replication (a paid or scraped
NAV-history source; a user decision).

**Dollars (honest back-of-envelope on the survivor-flattered panel):** ~376 trades/yr, mean hold
14 weeks, mean concurrency 92 open positions (max 271 — crash-wave cohorts). At $10k with 40
~$250 positions and 100% slot coverage the slab CAPTURES ~+44%/yr measured; at $25k (92 slots)
~+19%; at $2.3k (9 slots) ~+194% — these numbers REQUIRE the replication + live fill economics
(thin CEF spreads at retail, buy-executable at ~mid via MOC) before they are trusted. The left
tail: 1% of trades -21.97% (2020-cohort discounts entered during the crash continuing to fall).

**Attacks noted.** (1) Survivorship: the registered concern; (2) NAV staleness/quality: spot
checks vs known funds (AGD -2.6%, AIO -10.6%, ACP -11.7% at 2026-10) = sane; (3) the band = own
trailing distribution, non-tuned; (4) the weekly disc measurement + next-session execution:
no lookahead (the disc at Friday = pre-known at Monday). (5) The mechanism (NAV reversion led by
tender/liquidation/activation) is the SAME class as the positively-validated tender/odd-lot family.

**Follow-up (2026-10-06): survivorship attack run — see `study_cef_rv_surv_2026-10-06.md`.**
`research/sim/cef_rv_surv.py` shows the missing 66% of the CEF universe die benignly
(delisted-complete 5.2%/yr vs survivors 7.2%/yr = ~2pp/yr gap), the 2005+ birth cohort is stronger
(+594bp), and the NAV anchor is non-decorative (permuted-NAV placebo +34bp). No free weekly delisted
NAV exists (N-PORT is monthly, a scrape target). The one open risk is the +281bp price leg: an
official-closing-cross execution test is the gate before any upgrade. Verdict unchanged:
PROMISING-SURV-LIMITED; shadow spec + Roth pilot prepared in the attack draft, not deployed.
