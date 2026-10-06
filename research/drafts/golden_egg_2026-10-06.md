# Golden-egg overnight loop — 2026-10-06

Data: `daily-price-history` = byte-identical copy of the Sharadar bundle already at `~/data/sharadar` (1997-12-31..2026-10-05,
delisted included). No new data; the new tool is a cached long-history panel (`research/sim/lh_panel.py`). Execution
verification on Alpaca official SIP cross prints 2021-2026 (free data API, no spend). Program N 843 -> 849.

## Leaderboard

| candidate | mechanism | evidence | net / cost | capacity | freq / hold | independence | status |
|---|---|---|---|---|---|---|---|
| **SPLIT-T0**: buy close cross E-1, sell open cross E (forward-split ex-date) | retail market buys at the first post-split open; session reverts | vendor 2013-26 n 540 +105bp t 5.0 med +42 ex-top5 +68; 1998-2026 every era > 0; official 2021-26 n 174 +120bp t 2.42 med +17 | 5bp/side leaves ~all; official $10k half-account median yr +11% | open cross median $0.55M, p10 $38k: fine to ~$10k, binding ~$25k | ~34 event nights/yr, 1 night | event-driven, not IBS/TME/night selection; long-only, Roth-OK | **STRONG CANDIDATE** |
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
