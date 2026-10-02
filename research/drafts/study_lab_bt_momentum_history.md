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

## Lab-BX — industry-ETF momentum, top 5 of 20 fixed ETFs vs SPY, 2017-02 .. 2026-09 (Lab Round 46): DEAD
| | 1x excess vs SPY / month | 2x 2017-21 / 2022-26 | t | without best 5 | placebo (vs random 5 of the list) | CAGR (1x) vs SPY |
|---|---|---|---|---|---|---|
| Lab-BX | +9.5bp | −4.1 / +3.3 | 0.3 | −32 | 96.8 | 15.2% vs 15.1% |

By year (1x): 2020 +306, 2022 +187, 2025 +89; 2021 −130, 2023 −107. **DEAD**: momentum picks the better ETFs from the
list (placebo 97th) but only ties SPY, as Lab-BW's weak post-2010 decades predicted. As registered, a PAPER SHADOW was
built anyway (`make daytrade-momentum` now logs both shadows; first industry month, 2026-10: SMH, OIH, XBI, XPH, XOP).

## Lab-BY — top-decile momentum only while the market is above its 10-month average, else T-bills (Lab Round 47): PASS on 1963-2015, poor since 2016
| period (1x) | sleeve CAGR / Sharpe / max DD / worst 12m | market CAGR / Sharpe / max DD / worst 12m | time in |
|---|---|---|---|
| **judged 1963-2015** | **13.9% / 0.84 / −29% / −28%** | 10.1% / 0.71 / −50% / −43% | 74% |
| 1963-89 | 14.7% / 0.87 / −28% | 10.7% / 0.73 / −47% | |
| 1990-2015 | 13.0% / 0.80 / −29% | 9.4% / 0.68 / −50% | |
| ref 1927-63 | 11.3% / 0.66 / −55% | 9.0% / 0.49 / −84% | |
| **ref 2016-26** | **7.4% / 0.48 / −28%** | **15.0% / 0.98 / −25%** | 80% |

At 2x: 11.9% vs 10.1% (judged); both halves beat the market. About 1.4 switches a year.

**PASS on every registered bar** (CAGR >= market in both halves at 2x, a higher Sharpe in both, max DD and worst 12
months far better). It is the best risk profile of the lab, but **in 2016-26 it made half the market's return**:
- momentum's post-2000 fade (Lab-BT);
- whipsaws (2018, 2020, 2022).

As a small-account bot today it would most likely have lagged a plain index fund. Kept as a PAPER SHADOW signal: the
stock momentum shadow now records whether the trend filter is on each month.

## Lab-BZ — industry momentum (top 5 of 49) with the trend filter (Lab Round 48): PASS on 1963-2015, poor since 2016
| period (1x) | sleeve CAGR / Sharpe / max DD / worst 12m | market |
|---|---|---|
| **judged 1963-2015** | **14.6% / 0.91 / −28% / −25%** | 10.1% / 0.71 / −50% / −43% |
| 1963-89 | 13.9% / 0.85 / −28% | 10.7% / 0.73 / −47% |
| 1990-2015 | 15.2% / 0.97 / −23% | 9.4% / 0.68 / −50% |
| ref 1927-63 | 10.8% / 0.64 / −50% | 9.0% / 0.49 / −84% |
| **ref 2016-26** | **5.6% / 0.42 / −25%** | **15.0% / 0.98 / −25%** |

At 2x: 13.6% / 0.85 (judged). **PASS on every bar.** It is the strongest long-run result of the lab, and like Lab-BT and
Lab-BY it **lagged the market by ~9 points a year in 2016-26**.

## What the momentum results mean for "the most profitable bot"
- Four long-history passes (BT, BW, BY, BZ) and four failures in the era a bot would trade now (BR t 1.5, BX tied SPY,
  BY 7.4% vs 15.0%, BZ 5.6% vs 15.0%).
- The 2016-26 market was led by a few mega caps that a 5-of-49 industry book or a 20-stock momentum book only partly
  held; the trend filter also whipsawed out in 2018, 2020 and 2022.
- **Do not deploy on the 60-year record alone.** The recent decade is the relevant regime and it says "index".
- The paper shadows (stock and industry, with the vol-scale and trend-filter fields) collect forward evidence. Any
  live use needs a new registration judged on forward shadow months, the $500 gate and the user's approval.

## Deflated Sharpe audit of the lab's passes (2026-10-01, no new variant)
Bailey & López de Prado (2014), the program's formula (`research/sim/program_books.dsr`), on each pass's monthly 1x excess
over the market in its judged period (1963-07 .. 2015-12, T = 630), null V[SR] = 1/T:

| pass | Sharpe of excess (ann.) | SR0 at N 745 | DSR at N 745 | DSR at N 50 (the lab alone) |
|---|---|---|---|---|
| Lab-BW industry momentum | 0.46 | 0.44 | **0.55** | 0.85 |
| Lab-BT stock momentum | 0.41 | 0.44 | 0.43 | 0.76 |
| Lab-BZ industry momentum + trend filter | 0.30 | 0.44 | 0.16 | 0.46 |
| Lab-BY momentum + trend filter | 0.27 | 0.44 | 0.11 | 0.38 |

**None clears DSR 0.95**, the program's standard for a real edge, at the program's N, and not even at the lab's own ~50
trials. Read with the 2016-26 lag, the momentum findings are textbook factor premia that this search cannot
distinguish from luck at the required confidence. They stay paper shadows. (Lab-CC, SKEW, is a 20-day regression with
heavily overlapping windows; its NW t −2.34 is likewise below any multiple-testing bar at N 745.)
