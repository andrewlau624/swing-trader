# Golden-egg overnight loop — 2026-10-06

Data: `daily-price-history` = byte-identical copy of the Sharadar bundle already at `~/data/sharadar` (1997-12-31..2026-10-05,
delisted included). No new data; the new tool is a cached long-history panel (`research/sim/lh_panel.py`). Execution
verification on Alpaca official SIP cross prints 2021-2026 (free data API, no spend). Program N 843 -> 849.

## Leaderboard

| candidate | mechanism | evidence | net / cost | capacity | freq / hold | independence | status |
|---|---|---|---|---|---|---|---|
| **SPLIT-T0**: buy close cross E-1, sell open cross E (forward-split ex-date) | retail market buys at the first post-split open; session reverts | vendor 2013-26 n 540 +105bp t 5.0 med +42 ex-top5 +68; 1998-2026 every era > 0; official 2021-26 n 174 +120bp t 2.42 med +17; **official 2016-20 n 145 +77bp t 2.99 med +57 (registered PASS)** | 5bp/side leaves ~all; official $10k half-account median yr +11% | open cross median $0.55M, p10 $38k: fine to ~$10k, binding ~$25k | ~34 event nights/yr, 1 night | event-driven, not IBS/TME/night selection; long-only, Roth-OK | **STRONG CANDIDATE** |
| **SPIN-T0**: hold spin-off parent into ex-date open; sell parent + child at E opens | same price-drop salience (+ child's first open) | vendor n 409 med +70bp (mean +43 t 1.24); **official 2021-26 n 78 +83bp t 2.03 med +54, registered PASS** | 5bp/side fine | child open cross median $0.22M | ~13/yr, 1 night | event-driven | PROMISING (execution: child shares must be sellable at E open) |
| Reverse split / ADR ratio nights | mirror (price up -> retail sells) | reverse split T+0..T+2 -26..-105bp; ADR T+0 +108 then T+1 -130 | short only / noisy | — | — | — | REJECTED long |
| **LETF-NIGHT** (independent region): buy the close / sell the open on names whose single-stock LETF $vol share > 2% after a <= -5% day | LETF desks must sell L(L-1)·r·AUM at the close; the open reverts | 2024-26 only (in-sample): official crosses n 2009 +44bp t 2.17 med +32; within-name pre/post +4 -> +39 median; vol-matched controls ~0; asymmetric (+8% days -> -32bp) | 2.5bp/side sleeve 2024 +62%, 2025 +61%, 2026 +28% (vendor) | liquid names (MSTR, COIN, SMCI, IONQ...) | ~1000 events/yr, 44% of sessions | partly overlaps the night leg; adds beyond its filters | **PROMISING** (beta 2.9: beta-adjusted edge ~+15-20bp vs non-LETF names; no OOS history) |
| De-SPAC first night | retail attention at new identity | official n 261 med +99bp t 1.32; 2021 bubble only; 2023 -1361bp | — | open cross median $50k | ~50/yr then collapsing | yes | WEAK / untradeable |
| Split nights T+1..T+4 | same, decaying | official: T+1 +27 med; T+2/T+4 -30..-35bp | — | — | — | — | REJECTED (registered basket WEAK) |
| Spin-off parent ex-date | open under-adjustment | official n 88 +197bp t 1.16, ex-top5 < 0 | — | — | — | — | WEAK (outliers) |
| OTC->exchange uplisting | dilution/promoter supply after uplist | -17% abnormal over 250d, t -8, every era | short only | — | — | — | REJECTED long (short-side, borrow unknown) |
| Ex-dividend overnight capture | tax clientele / unadjusted sell limits | official n 13,199: robust +3bp | < cost bar | — | — | — | REJECTED (= Round 22 AZ) |
| Ticker change first night | attention | official -67bp, median -24 | — | — | — | — | REJECTED (vendor stitching artifact) |
| Chapter 11 emergence | forced creditor selling | name-match n 23 | — | — | — | — | DATA-LIMITED |
| Name change, same ticker, first night | attention | vendor -0.2bp (n 1715) | — | — | — | — | REJECTED (attention needs the price/identity event) |
| S&P 500 add/remove effective nights | index-fund close flow then open | 2013+ add night +20/+10bp, remove -12bp | — | — | — | — | REJECTED (decayed; = known S&P rows) |
| Split pre-ex-date run-up (E-10..E-1) | announcement-to-ex attention drift | 2013+ +33bp med +32 t 0.8; E-5..E-1 -3bp | — | — | — | — | REJECTED (no extension of SPLIT-T0) |
| Stock-deal acquirer nights after closing | target holders dump unwanted acquirer shares | vendor 2013+ T+0..T+4 overnight +3/+5/-2/+4/0bp medians (n ~690) | — | — | — | — | REJECTED (flow absorbed; no open footprint) |
| Spin-off child first nights | forced parent-holder selling at the open | vendor medians -23..-34bp/night | short only | — | — | — | REJECTED long |

Meta-pattern: event *drifts* in this data are on the short side (uplisting, spin child, delisting notice, parent spin);
the one long-side mechanism that survives is **retail open pressure on a scheduled salience event**, and only forward
splits survive the official-cross check (vendor open = official cross to 0.1bp there; for ticker changes they disagree).

# GOLDEN EGG REPORT

1. **Best candidate:** SPLIT-T0 — hold a stock overnight into its forward-split ex-date open.
2. **Why it should exist:** a split lowers the per-share price on a known date. Retail investors (price-level salience,
   "now affordable" headlines) send market buy orders into the first post-split opening cross; the cross clears above
   fair value and the session gives back ~36bp. The pressure is on the open, so a seller in the opening cross collects it.
   Counterparty: retail open buyers. Persistence: each event is small (cross ~$0.5M) and risky (one-name overnight,
   sd ~3%), so funds do not bother; documented since the 1980s (Grinblatt-Masulis-Titman ex-split day effect).
   Spin-off children (forced sellers) show the mirror sign at the open; reverse splits are negative (-100bp).
3. **Rule:** for every forward split (ratio > 1) of a common stock with raw close >= $5 and $vol >= $1M on E-1, buy the
   closing cross on E-1 and sell the opening cross on E. Ex-dates come from the exchange/Alpaca corporate-actions feed
   (record date weeks earlier). Equal-weight same-night events; cap the sleeve at ~50% of the account per night.
4. **OOS performance:** no untouched historical data remains (all Sharadar years were screened). Official SIP crosses
   2016-20 (pre-registered SPLIT-T0, PASS): n 145, +77bp t 2.99, median +57bp, ex-top-5 +38bp, both halves > 0. Official
   2021-26 (verification, same period): +120bp t 2.42, median +17bp, ex-top-5 +31bp, hit 57%. Per year medians:
   2021 +36, 2022 +50, 2023 -17, 2024 +39, 2025 -1, 2026 +10. Vendor long history: 1998-2002 +112, 2003-07 +62,
   2008-12 +69, 2013-17 +63, 2018-20 +90, 2021-26 +99bp (mean raw-SPY, all t > 2).
5. **Realistic net economics:** at the measured ~0bp auction cost the edge is gross = net; at 5bp/side: official
   2021-26, half the account per event night, $10k: yearly +13/+10/-2/+12/+54/-1% (median +11%). Vendor 2013-26 same
   setting: median year +13%, 12/14 years > 0. Under the program's <= 50% capture haircut: ~+5-6pp/yr — **at, not
   above, the +8pp gate**.
6. **Capacity:** ~34 event nights/yr; open cross median $0.55M, p10 $38k. Keeping orders <= 5% of the cross: full
   effect at $1k-$10k; at $25k the half-account sleeve drops to a median year of ~+0-3% (official) because big tickets
   must skip thin crosses. Breaks well before $100k.
7. **Drawdown:** worst official single event -5.3% (raw); vendor 2013+ worst -18.5% (at half-account = -9% of
   account in one night). No losing year worse than -3% at half-account.
8. **Independence:** selection is a calendar of corporate actions, not price signals; it does not use IBS, the night
   leg's loser screen, or Treasury month-end. Raw minus SPY overnight is the reported number (beta removed). It does
   compete for the same overnight capital as the night leg on ~34 nights/yr.
9. **Strongest attack:** the vendor "open" could be a non-executable print (it was for ticker changes) and the long
   history could be bubble-era. Also: multi-night extension and the ex-dividend analogue looked equally strong on
   vendor data and died.
10. **What survived:** official SIP crosses reproduce the split-night open (vendor vs official median |diff| 0.1bp),
    the effect is positive in every 5-year era 1998-2026, robust to ex-top-5, median > 0, date-shift placebo flat
    (T-5..T-1 nights +10-15bp vs T+0 +94bp), and splits are announced weeks before the ex-date (no lookahead).
11. **Profit (half-account per event night, 50% capture of the official 2021-26 median year):** $1k ~$55-70/yr
    (whole shares bind: post-split prices are $25-100), $5k ~$275/yr, $10k ~$550/yr, $25k ~$100-400/yr (capacity
    binds). At full official capture the median year roughly doubles these.
12. **Most likely killer:** a forward shadow over the next ~40 events showing median <= 0 (2023 and 2025-26 medians
    were already ~0: the effect may be retail-regime dependent and fading).
13. **Deserves deeper research:** yes — as a forward shadow (log the E-1 close cross and E open cross for every
    announced forward split; gate ~40 events), not as a deployment. It is a small, capacity-limited sleeve, not an
    order-of-magnitude edge.

## Mechanism check (not used to tune the rule)
T+0 effect by post-split price quintile (vendor, raw-SPY): 1998+ median +75 / +56 / +44 / +33 / +32bp from cheapest to
dearest; 2013+ +65 / +65 / +35 / +32 / +13bp. Monotonic in the price level, as price-level salience predicts; reverse
splits (price goes UP) show the mirror sign (-100bp), spin-off children (forced sellers) negative opens.

## Forward-shadow spec (not built; building it needs a REGISTRY entry in swingtrader/daily/testing.py in the same commit)
- Source: Alpaca `/v1/corporate-actions?types=forward_split` (ex_date, old/new rate) each session after the close.
- For every forward split with ex_date = next session: common stock (not ETF/ETN), raw close >= $5, $vol >= $1M ->
  log intended MOC buy (closing cross price) and MOO sell (next opening cross price), no orders.
- Gate: 40 logged events. Pass = median raw-SPY > 0 and mean > 10bp; kill = median <= 0 after 40.

## Meta-search (after ~20 hypotheses)
- Event *drifts* (uplisting, delisting notice, spin parent/child, reverse split) sit on the short side; long-only cannot
  harvest them.
- Forced *institutional* flows with sharp dates are absorbed (acquirer shares after stock deals: ~0bp at every open; S&P
  effective nights decayed). Forced flows that do leave a footprint are where the counterparty is **retail at the open**
  (splits, spin-off parents, de-SPACs) or a holder dumping a new unwanted security (spin child, short side).
- Vendor overnight effects around **identity** events (ticker change) are stitching artifacts; only events where the
  security keeps its symbol (splits, spins) agree with the official tape.
- Gate kills (no test): dividend-aristocrat index adds (1 rebalance/yr, a few names: ceiling far below +8pp);
  futures/OPRA ideas need paid Databento (not allowed tonight).
- Conclusion: the free daily-bar frontier is close to exhausted again; the one live lead is the ex-date open family,
  now a forward shadow on `him`.

## Update after the domain-jump phase (2026-10-06, ~25 unrelated regions; ledger `region_ledger_2026-10-06.md`)
**Top 5 surviving candidates**
1. **SPLIT-T0** — STRONG CANDIDATE, forward shadow live on `him`. Official crosses 2016-20 +77bp t 2.99 median +57
   (registered PASS); 2021-26 +120bp t 2.42 median +17. ~34 events/yr; capacity to ~$10-25k. Shrinking median.
2. **SPIN-T0** — PROMISING (same class). Official 2021-26 n 78 +83bp t 2.03 median +54 (registered PASS). ~13/yr;
   child-share crediting risk. In the same shadow.
3. **LETF-NIGHT** — PROMISING, independent region (product-induced forced flow at the close). Official crosses 2024-26
   n 2009 +44bp t 2.17 median +32; ~half is beta (median beta 2.9): beta-adjusted edge vs non-LETF names ~+15-20bp,
   concentrated on market-down days. ~1000 events/yr, 83% outside the night leg's rule. No history before 2024 ->
   forward-only registration; not deployed (needs the user's OK).
4. **OPEX SOQ open reversal** — PROMISING-small (mechanism confirmed): S&P members' opening gaps reverse intraday
   -0.19 x gap on monthly OPEX Fridays vs -0.10 otherwise; 12 days/yr, ~4%/yr ceiling.
5. **Listing-transfer first night** (NYSE<->Nasdaq) — PROMISING-small: +30bp t 2.54 median +23; ~17/yr, ~4%/yr.
   (Dual-class spread reversion is stronger statistically — t 9-11 — but cost/short-bound; listed in the ledger.)

**Class finding.** Every positive this night is a one-night distortion in an official auction caused by a forced,
price-insensitive participant (retail after splits, spin parents, LETF hedge desks, SPX option settlement, venue
change). Long-horizon long-only events die on the delisted-complete small-cap drift. Mid-cap closing crosses
themselves are efficient (CLOSE-DISLOC: 0.13 dislocations >= 1% per session). No golden egg: nothing has untouched OOS
except SPLIT-T0's official 2016-20 window, and its economics sit at the +8pp gate.
