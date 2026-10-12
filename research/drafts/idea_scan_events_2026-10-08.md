# Idea scan 2026-10-08: shape B (~monthly x >=2% x ~100%) and shape C (rare x 10-20% x per-holder cap), outside night/IBS

Method: 23 mechanisms with a named constrained counterparty, each grepped against NEXT.md, round1_prose.md, CLAUDE.md, research/sim/.
Ceiling = events/yr x net edge x deployable share (per-holder cap) at $2.3k/$10k/$25k. Gate: >= +8pp/yr at $10k at <=50% capture.
No SEC_USER_AGENT in .env (not added), so EDGAR full-text events were not scannable; Sharadar actions/SFP/SF2 were.

| # | mechanism (counterparty) | prior test | status |
|---|---|---|---|
| 1 | CEF liquidation / open-ending / conversion (NAV convergence) | cef_ends.py Arm E: 700/704 dead CEFs, final-6m median +1.5..+4.8%, deaths mostly mergers (56%), liquidations 16% of share; announcement gap; CEF-RV shadow live | TESTED |
| 2 | CEF NAV tender offers with pro-ration | Round 31: 54/55 give odd lots no priority | DEAD |
| 3 | Interval-fund / BDC repurchase at NAV | repurchase is at NAV, no discount to capture; no price series | NO EDGE BY CONSTRUCTION |
| 4 | ETF closures (last-week buy) | DL6: 9 liquidations, median -0.24% | DEAD |
| 5 | ETN issuer early redemption / acceleration | no data on disk, not found in repo; ~5/yr x ~5% x 20% = <0.3pp | CEILING-KILL |
| 6 | Mutual-to-stock thrift conversions (depositor priority) | DL-G27: 18 deals, ~2.6/yr, needs depositor account 1-2y ahead; inside G1 bundle | TESTED (small, pre-positioning) |
| 7 | SPAC trust floor (redemption right) | Round 31 L16 closed: ~+0.1%/yr; trust yield only | CEILING-KILL |
| 8 | Dutch-auction self-tender, odd-lot priority | odd-lot study: 14 deals/10yr, ~$149/deal, manual Schwab election | TESTED (CPC) |
| 9 | Rights offerings + oversubscription | capital-proportional, payoff ~0, no per-deal table | DEAD by prior |
| 10 | Preferred / baby-bond ex-div & chain | PREF-EX, ETDX PASS (shadow live), pref_cross, pref_dip | TESTED / LIVE SHADOW |
| 11 | Preferred calls trading above call price | pref_* family; mirror (below par) is just yield | COVERED |
| 12 | DRIP discounts | CPC/G1, tiny | TESTED |
| 13 | Demutualization | <1/yr, no data | CEILING-KILL |
| 14 | Appraisal rights | institutional size + litigation, not tradable | UNTRADABLE |
| 15 | Split-offs / exchange offers | B2: 12/14, +7.4% median, ~1.4/yr; SPLIT-T0 candidate | TESTED (CPC) |
| 16 | Stubs / holdco vs sub | needs shorting; PAIR-CLASS killed by scale | DEAD |
| 17 | Deletion to OTC / regulatory / voluntary delisting | I22 (wrong side), announcement gap; Sharadar has 985+435 such rows but pre-event price is the gap | DEAD by prior |
| 18 | Spin-off when-issued / first night | SPIN-T0, spin child first nights | TESTED |
| 19 | Bankruptcy equity rights offerings | no data; backstopped by creditors, small public tranche | CEILING-KILL |
| 20 | Stock-for-stock merger target spread | same class as MERG-CASH (N 841): raw +1.82% t 25, SPY-abnormal +0.007% t 0.02; spread = drift | DEAD (class) |
| 21 | Cash tender / going-private odd-lot cash-outs | B3, B4 dead | DEAD |
| 22 | Reverse-split round-ups | B1, ~$370/yr, depends on Schwab rounding | TESTED |
| 23 | CEF activist 13D / merger targets | G45 +3.4%/yr at book; CEF-RV | TESTED |

## Ceiling math for the only items with a live mechanism and no kill
| item | events/yr | net edge | cap / deployable | $2.3k | $10k | $25k | note |
|---|---|---|---|---|---|---|---|
| Whole CPC complex (6, 8, 12, 15, 22 bundle, G1) | ~20 | +5..+12% | 99-share cap across accounts | +20.5pp after tax | +8.8pp | ~0 | already forward-validated (CPC ledger); manual elections |
| Thrift conversions alone | 2.6 | ~+10% first-day, pre-positioned | $2k order | ~+11pp if eligible | ~+2.6pp | ~+1pp | only 2 eligible deals/yr in scenario B |
| Pref chain (10) | ~128 nights | +38..44bp | ~5% of auction $ | +10pp (Roth) | +5..7pp | +3.6pp | plateau ~$5k; ROTH-STACK, not new |
| ETN accel, SPAC floor, demut., bankr. rights | <5 | <=5% | any | <0.3pp | <0.3pp | <0.3pp | kill |

Result: no new survivor clears +8pp at $10k. Every mechanism with a named counterparty and free data on disk is either already
tested in this repo (rows 1-4, 6, 8, 10, 12, 15, 17, 18, 20-23) or ceiling-killed (5, 7, 13, 19) or untradable/unobservable (3, 9, 14, 16).
The structural/forced-flow space the CLAUDE.md map points at is fully mined at the free-data tier. Nothing pre-registered, no N consumed
(N stays 900 per grep of round1_prose.md), no runner. Only the EDGAR-text-only variants (rows 5, 9, 13, 19) could be rescanned with a
SEC User-Agent, and their ceilings are < 0.3pp so the unlock does not change the result.
