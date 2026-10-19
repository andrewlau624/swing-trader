# CRASH-A: trend-rule exit + inverse-ETF short (2026-10-18, N 1023 -> 1024)
Runner `research/sim/crash_a.py`; output `data/research/program/crash_a_out.txt`; pre-reg + result in `round1_prose.md` (Study CRASH-A).

## Verdict
KILL as registered (all 3 rules fail the non-crash bleed gate; R1 and R3 also fail the episode gate). But the
episodes themselves are not noise: in the three slow crashes the rules beat SPY by 60-75pp. It is **insurance with a real
premium, not free crisis alpha**, and the premium measured here (6-8pp/yr in non-crash years) is larger than the pre-registered 3pp tolerance.
Crash timing is not forecastable (VTS, PLUM, MFLW, SHAR-CRASH dead); the rules do not forecast, they react ~1-6 weeks late.

## Rules (canonical, frozen before any outcome)
R1 Faber: SPY month-end < 10-month SMA. R2: 200d SMA, 1% band (exit < 0.99 SMA, re-enter > 1.01). R3 Moskowitz: 12m return < 12m cash return.
Risk-off book D1 = 50% inverse (-1x SPY) + 50% cash (gated); D2 = 100% cash (reported). Signal close t, trade close t+1
(Schwab MOC, executable), 3bp/notional. SH actual from 2006-06; before that SYNTHETIC (-1x SPY total - 0.9%/yr + cash),
check vs SH on 5,103 overlap days: corr 0.981, cum -92.5% (SH) vs -94.1% (synthetic) (out:1). Cash = FRED DTB3 - 0.1%.

## Full period 1998-2026 (out:4-13)
| | CAGR | maxDD | Sharpe |
|---|---|---|---|
| SPY | 9.35% | -55.2% | 0.45 |
| 60/40 (2002-08+; SPY same window 11.29%/-55.2%) | 8.37% | -32.6% | 0.66 |
| R1 D1 / D2 | 7.03% / 8.68% | -31.6% / -26.2% | 0.39 / 0.55 |
| R2 D1 / D2 | 6.77% / 8.55% | -27.8% / -20.7% | 0.39 / 0.56 |
| R3 D1 / D2 | 8.45% / 9.52% | -35.9% / -33.7% | 0.46 / 0.56 |

Read: over 28 years the rules roughly tie SPY on CAGR (D2 variants) with 20-35pp shallower drawdown and a better Sharpe
(0.55 vs 0.45), i.e. they pay for themselves over a sample with two 50% crashes. D1 (the short half) is worse than D2 in every case
on CAGR and Sharpe: the short earns in crashes but bleeds in whipsaws and V rebounds.

## Per episode, D1 account return (SPY peak to trough), out:15-43
| episode | SPY | R1 | R2 | R3 |
|---|---|---|---|---|
| 2000-03..2002-10 | -47% | +18% | +16% | +25% |
| 2007-10..2009-03 | -55% | +20% | +7% | +13% |
| 2020-02..2020-03 | -33% | +6% | -13% | -33% |
| 2022-01..2022-10 | -24% | -14% | -8% | -6% |
Excess vs SPY (pp): R1 66/75/39/10; R2 63/62/20/16; R3 73/68/0/18. Gate (a) >= 15 each: only R2 passes. R1 misses 2022 (10pp), R3 misses 2020 (0).
Caveat: 2000-02 and 2007-09 are each ONE episode; the D1 gains partly come from the SYNTHETIC short before mid-2006 (2000-02) and are the best case for any trend rule.

## Bleed in non-crash years (all but 2000-02, 2008, 2020, 2022), out:45-52
SPY non-crash CAGR 16.8%. D1 cost vs SPY: R1 8.4, R2 7.9, R3 5.9pp/yr. D2 cost: 5.4 / 5.1 / 3.8pp/yr. Worst single year -15 to -33pp
(2009 rebound and V-shaped recoveries). Gate (b) <= 3pp: all FAIL. Note the non-crash set includes 2009 and 2010-11 whipsaws by pre-registration.
Whipsaws (out:54-57): R1 20 risk-off spells in 28.7y, 15 where SPY rose through the spell; R2 43 spells, 32 whipsaws (mean 60 days); R3 8 spells, 6 whipsaws.

## Speed: 2020 and 1987 (out:59-62)
- 2020: R2 flipped (held) 2020-03-02 at SPY -8.6%, but re-risked 03-04 and was whipsawed back into the crash (D1 -13%, still +20pp vs SPY).
  R1 held off from 03-03 at -11.3% (good, +39pp, partly luck of a Feb month-end below the SMA after the Feb 24-28 leg), re-risked 06-02 (missed the rebound from the trough).
  R3 flipped 04-02 at -25.1%, AFTER the trough (03-23): 0pp, no protection. A 5-week crash is the test of speed, and monthly rules are coin flips there.
- 1987-style one-day -20%: cannot be tested (data from 1998) and no close-based rule can exit before it happens; the rule would be long through the day, exit at the
  next MOC, and then own the V-shaped aftermath only if it re-risks. State: this class is NOT protected.

## Dollars (D1, whole account, out:64-70)
For a stylised -35% crash B&H $2,300 -> $1,495; applying each rule's MEDIAN episode excess (R1 +52, R2 +41, R3 +43pp; stylised, not a forecast):
R1 $2,699 / $11,734 / $29,335; R2 $2,433 / $10,580 / $26,449; R3 $2,480 / $10,783 / $26,956 at $2.3k / $10k / $25k.
Realised episodes: 2008-09 R1 $2.3k -> $2,758 (SPY -55%); 2020 R2 $2.3k -> $1,991, R3 $1,532 (R3 = no help).
Bleed per non-crash year at $10k: ~$590-840 (D1) / ~$380-540 (D2) vs holding SPY.

## Schwab execution
Taxable margin: SH or short SPY both fine (inverse ETF needs no short locate; 1x SH is not margin-restricted beyond normal marginability, unverified at Schwab). Roth: SH/PSQ/SDS and BIL/SHV allowed, no shorting; D1 and D2 are Roth-feasible. Taxable tax drag
(short-term gains on each switch, wash-sale on SPY loss/re-buy within 30d) is NOT modelled: it makes the bleed worse; R2 with 43 spells is the worst.
Roth is the natural home (no tax drag on switches).

## Honest read
1. Crisis alpha or cost of insurance: **cost of insurance with large payoff in slow bears**, near-zero or negative payoff in fast crashes (2020), and ~-6 to -8pp/yr of bleed
   against a bull market. Over 1998-2026 the bleed was paid back only because of two ~50% bear markets in the sample. 2 independent bears = low power.
2. Not a profit engine for "the biggest drawdown of your life": a fast crash (2020, 1987, Aug 2024 style) leaves the rule long or whipsawed. Best-case payoff is the R1/R2 slow-bear cases.
3. If the user wants an implementable version: the least-bad shape is R2-style cash-only (D2) in the Roth (cost ~5pp/yr, maxDD -21%), not the short. Not validated by this gate.
4. Unverified: QQQ variant (not run), tax, Schwab marginability, SH/synthetic fee drag at larger sizes, SPY-only; episode definitions are peak-to-trough on SPY.
Process note: the gate used pre-registered calendar-year non-crash set; changing it (e.g. exclude 2009) is post hoc and not done.

## EXTENSION: Great-Crash scale, CRSP VW index 1926-1998 (pre-registered before reading; pre-1998 = untouched)
Runner `research/sim/crash_a_ext.py`; out `data/research/program/crash_a_ext_out.txt`; data `data/research/crash_a/` (crsp.dsi, mcti t30ret cash). Same frozen R1/R2/R3, 1-day lag, 3bp.
The VW index is not investable and 1926-52 `dsi` includes Saturdays (200d SMA = ~33 weeks there; 252-day annualisation not used).
| window | VW | R1 D1 / D2 | R2 D1 / D2 | R3 D1 / D2 |
|---|---|---|---|---|
| W1 1929-09..1932-07 | -78.3% (peak 1929-09-03 to trough 1932-06-01: -84.0%) | +22% / -23% | +20% / -24% | +8% / -30% |
| W2 1937-03..1938-03 | -49.2% | +7% / -14% | +14% / -11% | -6% / -22% |
| W3 1973-01..1974-12 | -41.6% | +1% / -10% | +21% / +1% | +29% / +6% |
Excess D1 vs VW (pp): W1 +101/+98/+86, W2 +56/+64/+44, W3 +43/+63/+70. Extension gate (D1 >= +15pp in W1, W3): all three PASS (out ~line 15-25).
- Speed: the 1929 crash was slow enough for a monthly rule: R1 off 1929-11-06 (VW already -34% from peak), R2 off 1929-10-25 (-18%), R3 off 1929-12-03 (-31%). They missed the first third, then held risk-off 92-94% of the window.
- 1930-31 bear rallies: ZERO whipsaws for R1/R3 (one spell, VW -67%/-68% over it); R2 had 3 spells (two 1930 spells lost ~2% each, the last -69%). The spring-1930 rally in this index is only +20.7% low-to-high (1930-01-02 -> 04-10), not +45% (Dow-based figure differs); not enough to trip the 1% band / monthly signals. Whipsaw counts here are small because of a ~$ index drop that stayed below the SMA for 2.5 years.
- -1x leg path decay: daily-rebalanced synthetic -1x from the 1929-09 peak to the 1932 trough = +346% vs static short +89% (index -84%). In a one-way multi-year decline, daily rebalance COMPOUNDS gains (convexity), it does not decay; decay is the loss in choppy/rallying regimes (1932-33 rebound, a 100%+ rally from the trough). D1 holds only 50% -1x with daily rebalance, so W1 is +22%, not +173%: the half-short book bleeds through 1931-32 volatility (daily vol 3-5%).
- $ at $2.3k / $10k / $25k: W1 D1 R1 $2,812/$12,228/$30,570; R2 $2,760/$12,000/$30,001; R3 $2,487/$10,813/$27,033; buy-and-hold $500/$2,172/$5,431. D2 (all cash) in W1 ends -23 to -30% because 1929-11 exit was already after a -18..-34% drop. W3 D1: R1 $2,333/..; R2 $2,783/$12,101/$30,252; R3 $2,957/$12,859/$32,147; B&H $1,343/$5,839/$14,597.
- Non-crash 1926-50 bleed (excl 1929-32, 1937-38; VW CAGR 17.8% incl. 1933 rebound; my annualisation is approximate): D1 R1 10.2, R2 6.3, R3 5.8pp/yr; D2 6.6/3.8/3.5. Bleed is again 4-10pp/yr, above the 3pp tolerance; 1926-50 CAGR: R2 D1 10.9% vs VW 7.05% (maxDD -44% vs -84%), R3 D1 8.6%, R1 D1 6.1%.
- Read: in a 1929-type event, the rules would have beaten buy-and-hold by ~85-100pp and even made money with the 50% short; this is the strongest case for them and rests on ONE giant event (1929-32) plus 1937 and 1973. They did NOT call the top: they exit after -18..-34%. The question is then purely the 4-10pp/yr insurance premium in the other 20+ years.
- Optional Japan 1990-2003 (Datastream): NOT run (not Schwab-tradable; optional).
### Systemic risks a 1929-scale event adds (not modelled; each can void the synthetic P&L)
- Inverse-ETF issuer/closure/counterparty risk: SH/SDS/PSQ are swap/derivative funds; in a -50%+ move 2x funds (SDS) hit reset/closure triggers, ProShares has terminated funds, and swap counterparties are banks (Lehman 2008 precedent). Use 1x SH, not SDS/SQQQ.
- Short-sale bans / uptick rules: Sept 2008 SEC ban on 799 financials; Rule 201 circuit breaker; a ban hits shorting stocks, not buying SH, but the ETF's own swaps/futures hedge can be impaired (premium/discount blowouts).
- Exchange closures and trading halts: NYSE closed Sept-Dec 1914, Bank Holiday March 1933, Sept 2001 4 days: close-based rules cannot exit while closed; limit-down gaps, MOC imbalance days.
- SIPC limits: $500k per customer ($250k cash) covers broker failure, not market losses; margin accounts: a short through a V-shaped rally can be bought-in or margin-called (the taxable D1 short is exactly the position that can be force-closed at the bottom).
- Government response: 1933 devaluation/gold seizure, 1934 SEC rules, today's circuit breakers, Fed backstops make the 1932 -> 1933 rebound (+100%) faster; a short leg is the one that fails then.
