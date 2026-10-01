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

## Lab-BU — volatility-scaled version (Barroso & Santa-Clara; Lab Round 43): DEAD by its bar, but a real crash cut
Weight = min(1, 12% / trailing 6-month vol of the momentum excess); the rest in the market. 1x:

| period | excess bp/month scaled / unscaled | Sharpe scaled / unscaled | worst 12m scaled / unscaled |
|---|---|---|---|
| judged 1963-2015 | +38.7 / +39.7 | 0.451 / 0.412 | **−23.5% / −30.6%** |
| 1963-89 | +49.1 / +54.7 | **0.589 / 0.611** (fails) | −21.0% / −21.3% |
| 1990-2015 | +28.0 / +24.4 | 0.318 / 0.237 | −23.5% / −30.6% |
| ref 1927-63 | +37.3 / +33.6 | 0.437 / 0.321 | **−25.5% / −50.4%** |
| ref 2016-26 | +15.2 / +16.5 | 0.138 / 0.130 | −29.7% / −30.8% |

t 3.3; 2x positive both halves. **DEAD** only on bar (a): the 1963-89 Sharpe is 0.02 lower. Recorded for the shadow:
scaling halves the worst historical crash at almost no cost to the mean. A live version would register it as its
risk control.

## Lab-BV — long-only long-term reversal, the bottom 60-13-month decile vs the market (Lab Round 44): DEAD
| | judged 1963-2015 | 1963-89 | 1990-2015 | ref 1927-63 | ref 2016-26 |
|---|---|---|---|---|---|
| 1x excess bp/month | +27.9 | +18.1 | +38.0 | +60.1 | **−12.0** |
| 2x | +17.9 | +8.1 | +28.0 | +50.1 | −22.0 |

t **1.76** (fails 2.0); without best 5 +12; worst 12m −41% (to 2019-08). By decade: 1950s −35, 1980s −34, **2010s −56**,
2020s +46. **DEAD**: positive on average but too noisy, and negative for the decade before this program's data.

## Lab-BW — industry momentum, top 5 of French's 49 industries (Lab Round 45): PASS, durable
| | judged 1963-2015 | 1963-89 | 1990-2015 | ref 1927-63 | ref 2016-26 |
|---|---|---|---|---|---|
| 1x excess bp/month | **+48.6** (t **3.3**; without best 5 +38.4) | +51.2 | +45.9 | +52.7 | +13.1 |
| 2x | +38.6 | **+41.2** | **+35.9** | +42.7 | +3.1 |

By decade (1x): 1920s +116, 1930s +46, 1940s +68, 1950s +24, 1960s +79, 1970s +64, 1980s +15, 1990s +47, **2000s +63**,
2010s +6, 2020s +27. Worst 12m −41% (to 2009-06).

**PASS.** Unlike stock momentum (Lab-BT), industry momentum stayed positive in every decade, including the 2000s. It
is weaker since 2010 (+6 / +27bp, about +3bp at 2x in 2016-26). Lab-BS (11 broad sector SPDRs) failed in 2017-26, so
granularity matters. Next: the implementable version on liquid US industry ETFs (Lab-BX), and a paper shadow.
