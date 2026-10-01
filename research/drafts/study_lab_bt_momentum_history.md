# Study Lab-BT — long top-decile momentum vs the market, 1963-2015 (Ken French library): PASS, with a faded modern era (program N 734 -> 735)

Stamp: round1_prose.md Lab Round 42 (commit 56b2824). Script `daytrade/research/bt_replay.py`. Value-weighted "Hi PRIOR"
(12-2 momentum) decile minus the market (Mkt-RF + RF), CRSP 202608. Costs: full monthly turnover, 20bp (1x) / 40bp (2x).

| | excess / month, 1x | 2x |
|---|---|---|
| **judged 1963-07 .. 2015-12** | **+39.7bp** (t **3.0**; without best 5 +30.1) | +19.7 |
| half 1 1963-07 .. 1989-12 | +54.7 | **+34.7** |
| half 2 1990-01 .. 2015-12 | +24.4 | **+4.4** |
| reference 1927 .. 1963-06 | +35.7 | +15.7 |
| reference 2016-01 .. 2026-08 | +16.5 | **−3.5** |

By decade (1x): 1960s +87, 1970s +66, 1980s +2, 1990s +64, **2000s −5, 2010s −1**, 2020s +35bp/month.
CAGR 1963-2015: top decile 14.2% vs the market 10.1%; 2016-26: 15.5% vs 15.0%. Worst 12-month excess −50% (to 1933-05).

**PASS on the registered bar.** The reading matters more than the label:
- The long-only momentum premium is real over six decades, but it **faded after 2000**: about 0 in the 2000s and 2010s,
  and slightly negative after 2x costs in 2016-26.
- It carries crash risk.
- It is a priced risk factor with a fat left tail, not a cost-free anomaly. Expect it to earn little more than the
  market most of the time, a lot in some regimes (2022-26), and to lose badly in sharp reversals.

Per the registration: build a monthly momentum sleeve as a **PAPER SHADOW only** (`daytrade/shadow_momentum.py`), to
gather forward evidence. No orders, no live change, and the $500 gate applies to any future live test.
