# CRASH-D: trend-gated inverse sleeve vs T-bills (2026-10-18, N 1027 -> 1028)
Runner `research/sim/crash_d.py`; output `data/research/program/crash_d_out.txt`; pre-reg + result in `round1_prose.md` (Study CRASH-D).

## Verdict
KILL as registered, all three rules: arm (a) fails (non-crash cost 4.1-4.8%/yr of sleeve capital vs gate 2.0), arm (b) passes
(every rule gains +41% to +142% of sleeve capital in 1929-32, 1937-38, 2007-09). So the cost is about HALF of CRASH-A's 6-8pp
(that included missed SPY upside), but still ~2x the tolerance. Insurance with a real payoff; the premium is above the gate.

## Setup (frozen before outcomes)
Same R1/R2/R3 as CRASH-A, signal close t, trade close t+1, 3bp per switch. Sleeve = 1x inverse when risk-off, T-bills otherwise.
Series: CRSP VW 1926-1997 spliced to SPY 1998+; inverse = synthetic -1x (-0.9%/yr) except actual SH from 2006-06-22 (out:1).
Excess = compounded sleeve minus compounded T-bills, as % of sleeve capital.

## Per episode (out:5-11); * = gate arm
| episode | R1 | R2 | R3 | index |
|---|---|---|---|---|
| 1929-09..1932-07* | +142% | +130% | +129% | -78% |
| 1937-03..1938-03* | +53% | +59% | +43% | -49% |
| 1973-74 | +30% | +47% | +53% | -42% |
| 2000-03..2002-10 | +54% | +51% | +61% | -47% |
| 2007-10..2009-03* | +52% | +41% | +46% | -55% |
| 2020-02..03 | +31% | +15% | 0% | -33% |
| 2022-01..10 | +5.5% | +9.6% | +12% | -24% |

## Non-crash years (n 87 since 1926; 23 since 1998), mean excess per year (out:14-16)
| | 1926-2026 | 1926-97 | 1998-2026 | median | worst |
|---|---|---|---|---|---|
| R1 | -4.81 | -4.44 | -5.84 | -2.28 | -34.5 (1933) |
| R2 | -4.06 | -3.64 | -5.22 | -3.06 | -34.2 (1933) |
| R3 | -4.18 | -4.37 | -3.65 | 0.00 | -30.9 (1975) |
Including crash years (out:37-40): R1 -2.78, R2 -1.89, R3 -2.24 %/yr over 1926-2026; since 1998 -3.67 / -3.55 / -1.95. Net, the sleeve
has NOT paid for itself on average, even with 1929; it is insurance whose price is about its expected payoff.
Whipsaws (spell sleeve excess < 0; out:19-25): R1 62 of 71 spells (1998+: 18/21), R2 102/120 (37/43), R3 36/41 (7/8). Risk-off ~27-29% of days.

## Dollars (50% sleeve, vs that half in T-bills; out:27-30)
1929-32 replay at $2.3k / $10k / $25k: R1 +$1,630 / +$7,086 / +$17,715; R2 +$1,500 / +$6,522 / +$16,304; R3 +$1,478 / +$6,424 / +$16,060.
Average non-crash year: R1 -$55 / -$241 / -$602; R2 -$47 / -$203 / -$507; R3 -$48 / -$209 / -$523.
Read: at $2.3k the premium is ~$50/yr (negligible); at $25k ~$500-600/yr. Payoff only in a slow multi-year bear; none in a 2020-style crash (R3 0%, R2 +15%).

## Cheapest per unit of payoff (out:42-45) and the multiple-testing caveat
Payoff (sum of 3 gate episodes) / cost per year: R2 57, R3 52, R1 51 (R2 230%/4.06; R3 217%/4.18; R1 246%/4.81). The spread is within noise:
the cheapest rule is R2 only by ~5 points of ratio, chosen after seeing results, so it is a multiple-testing pick, NOT a finding. R3
has the lowest all-years cost since 1998 but gives zero in 2020 (no help in fast crashes). All three reported, none dropped.

## MODERN -83% test: QQQ itself, signal and sleeve on QQQ (pre-registered before output; `research/sim/crash_d_qqq.py`, out `crash_d_qqq_out.txt`)
PSQ actual from 2006-06-22 (corr to synthetic 0.992), synthetic -1x QQQ -0.95%/yr before. QQQ 2000-03-10..2002-10-09: -82.6%.
| window (sleeve excess vs T-bills) | R1 | R2 | R3 | QQQ |
|---|---|---|---|---|
| 2000-03..2002-10 (pre-reg gate arm) | +99% | +104% | +104% | -83% |
| 2007-11..2009-03 | +27% | +29% | +27% | -52% |
| 2020-02..03 | 0% | +5% | 0% | -27% |
| 2021-11..2022-12 | +27% | +23% | +15% | -35% |
Non-crash years (n 21, 2000-26): cost R1 7.13, R2 7.81, R3 6.22 %/yr; all years -3.0/-3.6/-2.1. Whipsaws R1 23/26, R2 39/44, R3 13/15. Gate: all KILL (cost).
Read: the 2000-02 payoff is the same ~+100% as 1929 (+130-142%) on a modern, algorithmic, decimalised market, so the payoff is not a pre-1998
artifact; the cost is HIGHER on QQQ (6-8%/yr vs 4-5% on SPY) because the inverse leg of a high-vol index bleeds in every V-rebound (2009, 2011, 2019). 2008 and 2020 payoffs are weak (+27%, ~0).
Modern independent -80% events: only ONE (QQQ 2000-02); the other modern drawdowns are -52% and -35%. The claim "three modern -80% declines" is NOT supportable.
Nikkei 1990-2003: SKIPPED. WRDS Datastream (tr_ds_equities.ds2indexdata) has no clean Nikkei 225 index series (only `LJAPDOWA` constituent list); TSE TOPIX there starts 1997-07 (code 6164, mapping dsindexcode = indexlistintcode assumed, not verified), Large Cap 1992-01, so the 1990-92 collapse is missing. Also not Schwab-tradable.

## Caveats and unverified
- Pre-2006-06 inverse is SYNTHETIC; 1929-32 gain >100% is the daily-rebalanced -1x convexity in a one-way bear (CRASH-A ext note); real SH-like fund
  risks (closure, swap counterparty, short-sale bans, bank holiday closures) are not modelled and could void it.
- Pre-1952 data includes Saturdays; cash 1926-97 is monthly CRSP t30ret; years excluded as crash fixed in the pre-reg (1933 rebound and 2009 stay in).
- 1929-32, 1937, 2007-09 are 3 independent events; power is low; 1929 supplies most of the payoff.
- Taxable tax drag on switches and Schwab margin/marketability of SH not modelled; Roth is the natural home (SH allowed, no short).
- Sleeve cost is per unit of sleeve capital while the sleeve is only 27-29% of days risk-off; T-bill yield in the 1930s-40s was ~0 so the "cash" floor is lower than today.
