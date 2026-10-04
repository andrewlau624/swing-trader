# Study EF: ETF creation/redemption flow (run 2026-10-04; registered in round1_prose.md, commit 30251ec; N 810 -> 813)

Runner `research/sim/etf_flow.py`, data builder `research/sim/etf_flow_data.py`, data `data/research/etf_flow/` (untracked).
Judge window 2008-01-02..2026-09-30, one look; every rule run once at entry t+1 (registered baseline) and t+2 (stress).
Costs: `book.cost_bps` tier. Raw output kept at scratchpad `ef_out.txt` (re-runnable).

## Verdict: all three REJECTED. No shadow proposed, nothing built.

## Data
SSGA navhist (NAV, SO, TNA) for 27 SPDR funds, ~252 rows/yr; sectors/SPY/DIA SO from 2006-06, XBI KRE XOP XRT XHB XME
2006, JNK 2007-12, SJNK 2012-03, MDY 2011-01, XLRE 2015-10, XLC 2018-06, SPSB/SPIB/SPLB 2009. GLD downloaded but excluded
(grantor trust). Prices: Yahoo 2007+, matches Alpaca SIP 2016+ (median open/close-ratio diff 0.1-0.5bp). Pre-2016 opens are
first consolidated prints, not auction prints. XRT/XOP/KRE/XHB have very noisy SO (XRT median daily |dSO| 6.8%); the
registered 3% threshold therefore fires mostly on thin-SO funds (H3: XRT 1700 of 6308 events, XOP 885, KRE 597).
Date convention: only internal evidence. corr(dSO_t, premium_{t+k}) peaks at k=-1 in 2024-26 (SPY .19, JNK .37): row t
records orders placed at the t-1 close (T+1 settlement); earlier eras too weak to date. Publication lag unknown
(SPY file lacked 10-02 on 10-04, GLD had it). Row t treated as actionable at open t+1 (not proven), t+2 as stress.

## Results (net of tier costs)
| Rule | n | mean net | t | median | ex-top | yrs>0 | 2x cost | t+2 stress |
|---|---|---|---|---|---|---|---|---|
| H1 LS (low-3 minus high-3 20d net creation, weekly, taxable) | 977 wk | -21.9bp/wk | -2.9 | -15bp | -26 (ex5) | 32% | -47bp | -27.7bp |
| H1 Roth: LOW minus EW(EQ) | 977 | -10.8bp | -2.5 | -10bp | -13.6 | 32% | -23bp | -13.8bp |
| H2 JNK/SJNK discount <= -1% (AR vs beta*SPY, 5d) | 15 ep | -15.9bp | -0.13 | +29.6bp | -185 (ex5) | 3/4 | -77bp | -20.8bp |
| H3 long after f <= -3% (AR vs SPY, 1d; cost 2x tier/side as registered) | 6308 | -31.7bp | -15.0 | -31.5bp | -32 | 0% | -58bp | -27.4bp |

Gross: H1 LS +5.0bp/wk (t+2: -0.9), below the ~27bp/wk round trip on 6 ETFs. H3 gross AR -5.2bp at t+1 (-0.9 at t+2), net at
plain tier -18bp. H2: carried by March 2020 (ex 2020-02..04: +73bp, but that removes 9 of 15 episodes); no 2008-09 episode
(JNK never closed 1% below NAV there on this NAV series), raw return net +14bp; 15 episodes = the minimum n, 4 years.

## Timing (reported)
Decile of f (all 19 funds, 168k fund-days): heaviest redemption decile +5.5/+5.7/+4.1bp AR vs SPY over the flow session / entry
session / t+2; heaviest creation decile -2.2/-3.5/-1.3bp. Direction matches BDR/pressure-reversal but is 4-6bp a day,
below any round-trip cost. Around H3 events the move is BEFORE the flow is knowable: AR segments k=-3,-2,-1 = -5, +19, +41bp
(redemptions follow outperformance), k=0 -1bp, entry segment k=1 -5bp. The price effect sits in the untradable window.
IBS overlap: 23% of H3 events have IBS_t < 0.2 (so flow adds nothing the IBS leg does not already see). Capacity not an issue
(liquid ETFs); the binding constraint is cost vs a ~5bp gross edge.

## Executable %/yr
None. Net mean is negative at $2.3k, $10k and $25k alike (cost-bound, not size-bound).

## What remains
SO date convention is inferred, not verified; corporate-bond ETFs beyond JNK/SJNK (SPIB/SPLB/SPSB) were downloaded but not
judged; GLD excluded by pre-registration. A sharper creation measure (unit-level, daily, with AP data) is not free.
