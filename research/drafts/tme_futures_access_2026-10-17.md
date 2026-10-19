# TME through Treasury futures: access and ceiling (2026-10-17, desk research, no N)

Verdict: NO. Futures do not clear +8pp at $10k at a sane risk level. They are leverage on a ~1.0 (full capture) / ~0.5 (honest) Sharpe, 3-day-a-month edge, and the per-contract commission eats most of a micro contract's edge. TMF in the Roth is cheaper per unit of leverage. Not a real-money candidate.

## 1. Access (sources; margins are unverified/stale)
- Standard: ZN/ZB/UB/TN are $100k face, tick $31.25 on ZB/UB. ZB initial margin ~$4.1k (Barchart Dec-26 page, ~Jan 2026: $4,070 init / $3,700 maint), UB ~$6.4k (CME micro page figure). ZB DV01 ~$185, UB ~$200 (NexusFi). A 30y contract = ~11x a $10k TLT position in duration. Unusable below ~$100k. https://www.barchart.com/futures/quotes/ZB*0/profile , https://nexusfi.com/a/instruments/ultra-t-bond-ub-futures
- Micro Ultra 10y (MTN) and Micro Ultra T-Bond (MWN): launched 2024-03-25, $10k face, 1/10 size of TN/UB (MTN DV01 $8.80, tick $1.5625; MWN margin ~$640 est.). https://www.cmegroup.com/articles/2024/understanding-micro-treasury-futures.html (search summary; page fetch timed out)
- Micro Treasury Yield futures (2/5/10/30y): launched Aug 2021, $10/bp DV01, cash-settled to BrokerTec yields; 30Y yield margin ~$290 (CME micro page). Long TLT = SHORT yield future. https://www.cmegroup.com/markets/interest-rates/micro-treasury-futures.html
- No new micro ZN/ZB-based note contract found for 2025-26 (search only; not exhaustively confirmed).
- Schwab: futures need margin approval and $1,500 minimum; IRAs (incl. Roth) need $25,000 NLV and 125% of initial margin; $2.25/contract/side plus exchange/NFA fees; thinkorswim. https://www.schwab.com/futures/faqs , https://disclosures.schwab.com/SchwabDashboard/61330/REG23060.pdf . So a Roth under $25k is excluded: futures are taxable-account only at these sizes.
- UNVERIFIED: whether Schwab lists micro yield futures or MWN at all (futures-markets page returned access-denied); current CME margins; micro yield tick/ADV (thin liquidity risk); Section 1256 60/40 treatment of cash-settled yield futures; exact per-contract exchange fees (I assume ~$7.5 round trip for MYY30, ~$10 for MWN incl. slippage).

## 2. Model
Source: `data/research/program/tme_out.txt` (2002-15 judge: gross window +40.2bp, net AR +32.3bp t 2.76) and `tme_leverage_out.txt` (2009-26 windows, n 209, TLT 1x net +35.9bp/window, sd 128bp, worst -2.92%, Sharpe/window 0.28 = ~0.97/yr). Descriptive reuse only, no new return look.
Assumptions: TLT duration 16.5, so $10/bp DV01 = ~$6.06k TLT-equivalent; futures lack the ~3.7bp of 3-day coupon carry, so gross ~36bp full capture, 18bp at the 50% honest capture; 12 windows/yr; %/yr is on the whole account (idle cash would add T-bill yield).

| size | instrument | leverage on TLT | %/yr @50% | %/yr @100% | ann. vol | worst window | margin used |
|---|---|---|---|---|---|---|---|
| $2.3k | 1 MYY30 | 2.64x (forced, indivisible) | +1.8 | +7.5 | 11.7% | -7.7% | 13% |
| $10k | 1 MYY30 | 0.61x | +0.4 | +1.7 | 2.7% | -1.8% | 3% |
| $10k | 4 MYY30 | 2.42x | +1.6 | +6.9 | 10.7% | -7.1% | 12% |
| $10k | 6 MYY30 | 3.64x | +2.5 | +10.3 | 16.1% | -10.6% | 17% |
| $10k | 2 MWN | 2.42x | +2.8 | +8.1 | 10.7% | -7.1% | 13% |
| $25k | 4 MWN | 1.94x | +2.3 | +6.5 | 8.6% | -5.7% | 10% |
| $25k | 8 MWN | 3.88x | +4.5 | +12.9 | 17.2% | -11.3% | 20% |

- Margin calls: not from a single window (worst historical -2.9% x leverage stays well under initial margin even at 3.6x), but CME margin hikes in a rate shock plus 2022-style multi-month drawdown of the unhedged leg are not modelled; sleeve only holds 3 sessions/month so it is flat otherwise.
- Cost is the killer: a $10/bp contract earns ~$11 per window at 50% capture and pays ~$7.5 round trip, i.e. ~70% of the edge (TLT/TMF in Schwab pays $0 commission and ~2-5bp). Standard ZB has lower cost per DV01 but is 11x too big.
- Needed for +8pp at $10k at 50% capture: ~3.6x+ leverage on a 0.5-Sharpe edge, i.e. ~16% annual vol, ~-10.5% worst month, and still short because of cost (6 MYY30 gives +2.5; only MWN at 4+ lots gets close, which is ~5x leverage). The +8pp is reachable only at full (published) capture and 2.4-3.6x leverage: that is the unhaircut number, not an honest one.

## 3. Verdict and comparison
- Futures: best honest case at $10k is +1.6 to +2.8pp (2.4x leverage, ~11% vol); +8pp needs full capture. Fails the gate.
- TMF 3x in the Roth (prior ceiling-kill): +5.8pp at 50% capture on full-account deployment, vol similar (~13% annual from sleeve), commission-free, no $25k IRA gate, no margin. Strictly better access than futures for this edge below $25k; futures only add 60/40 tax (unverified) in the taxable account and a cheaper-than-ETF-drag leverage at much larger size.
- TME-in-taxable at 2x via MWN is the only futures form near the gate, and only at the unhaircut capture rate.
- Conclusion: the ceiling-kill stands. Reopen only with a measured forward capture rate for TME itself (never shadowed) or at >=$100k where ZN/ZB lots are divisible.
