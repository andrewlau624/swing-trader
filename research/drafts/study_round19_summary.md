# Round 19 summary: max edge from outside sources (prompt_max_edge.md), N 675 -> 680

What was searched: 44 candidates from papers (17), strategy collections (10: Quantpedia, Alpha Architect,
Allocate Smartly, CXO), GitHub repos (7, code read for lookahead/costs), Hugging Face forecasting models
(4 rows covering 12 models) and forums (6: Elite Trader, QuantConnect; reddit unreachable, Wilmott empty).
List, decay and dead-list check: `max_edge_candidates.md`. Most outside ideas were already harvested or
killed here. That included five that NEXT's table did not list but RESULTS.md had: night exit time (add. 7),
gap share / relative volume / late selling (add. 23), news days (add. 12) and IBS at the MOC (add. 6).
Tested: 3 studies, 5 variants + 1 report.

## Ranked table

| rank | idea | source | verdict | %/yr and $/yr at $2.3k / $10k / $25k (V7 taxable, 2.5bp/side, pre-tax) | capacity ($100k / $500k) | who pays | what live evidence would change it |
|---|---|---|---|---|---|---|---|
| 1 | **AU3: tilt night picks by the 20-day "tug of war" count** (overnight up, day down) | Akbas-Boehmer-Jiang-Koch JFE 2022; Aboody et al. JFQA 2018 | **SHADOW**: all 7 registered checks; holds on auction prints (6/6) and in a second implementation (t 2.9). DSR 0.46 at N 680; 2022-23 ≈ 0 | +3.1pp **+$70** / +3.2pp **+$323** / +2.8pp **+$705** (Roth +$64 / +$296 / +$645, tax-free) | ≈ +$2.8k at $100k; breaks with the night leg (~$250k, Study V); moot at $500k | retail buyers at the open in names with a persistent overnight clientele | ≥ 300 live picks with TOW logged: the high-TOW tercile must out-earn the low tercile on auction fills, else off |
| 2 | **AW: restate the night leg on official auction prints** | Quantpedia 2025 (OHLC open ≠ cross) | **REPORT**: the vendor open overstates the night leg by 3.8bp/trade (t −7.5); no verdict flips | −2.0pp −$46 / −2.3pp −$227 / −2.3pp −$583 (a correction, not a loss of money) | same | nobody (data artifact) | none needed; live fills are already measured against the cross |
| 3 | AV2: IBS exit at a close above the prior high | idousse repo (clean); Connors | **DEAD** (t −0.1; 2021-23 −2.6pp) | −0.4pp −$38 / −0.8pp −$82 / −0.8pp −$205 | IBS scales to $M | — | none |
| 4 | AU1: tilt by 20-day mean overnight return | Aboody et al.; CXO | **DEAD** (t 1.5-1.7) | +2.2pp +$51 / +2.3pp +$234 / +2.2pp +$558 | as AU3 | as AU3 | subsumed by AU3 |
| 5 | AU2: drop picks with negative 20-day overnight mean | same | **DEAD** (−1.4..−1.7pp at 2.5bp; the tier_hi gain is the cost gate) | −$33 / −$173 / −$413 | — | — | none |
| 6 | AV1: IBS exit at IBS > 0.5 | Pagonidis 2014 | **DEAD** (t −2.3, both halves negative) | −5.5pp −$126 / −5.9pp −$590 / −5.9pp −$1,478 | — | — | none |
| — | closing-auction imbalance (AC) | Bogousslavsky-Muravyev 2023; Elite Trader | not tested: data | unknown | — | passive close flow | a candidate-only Databento pull ($125 free credit) as a pilot; live ≥ $588/yr (NYSE only) |
| — | Chronos / TimesFM / Moirai / Kronos filters | HF; Rahimikia et al. 2025 | not tested: power | ~0 (published: ~51% direction, net-negative at 11-21bp) | — | — | a forward log only; clean holdouts are 11-30 months, about 1/6 of the trades needed |

## What failed, plainly
- **Both IBS exit rules failed.** Holding past the first session gives back the overnight bounce (AV1
  −5.9pp). AV2 is just more IBS exposure spread thinner.
- **The simpler overnight-persistence features failed.** AU1 missed the t bar and AU2 hurts at real costs.
  Only the tug-of-war count survived, and it is not significant after deflating for 680 trials (DSR 0.46).
- **The literature mostly re-finds what this program already harvests or killed.**
- **Outside sources with problems:**
  - toniker10/SPY-IBS: **lookahead** (earns the signal bar's own close-to-close; the README says next open), no costs.
  - perthoptions/overnight-research: a one-bar **feature leak**, a survivor universe, and the authors' own net result is negative.
  - **No costs in the headline:** codecat noise-area (slippage 0), giovannibrusco ORB (break-even 2.2¢/share), CazSyd IBS.
  - **Reported gross only:** Della Corte et al., Baltussen-Da-Soebhag, Pagonidis, TimesFM-fin.
  - **Our own backtest** had an open-price bias (AW): smaller than Quantpedia's GDX case, but real.
- **Decay watches from outside:**
  - codecat finds noise-area SPY Sharpe ~0 since 2025; ours is QQQ/SMH, watch it by year.
  - perthoptions's intraday-loser overnight spread collapsed in the last ~126 sessions on large caps.
  - Boyarchenko et al. say the index overnight drift is ~0 since 2021.

## Addendum (same day): Rounds 20-22 and the follow-ups (N 682 -> 688, counting the lab's Round 18)

| idea | source | verdict | $2.3k / $10k / $25k per yr | who pays |
|---|---|---|---|---|
| AU3 switch | — | **BUILT, OFF**: 15:40 shadow log, `tow` in the decisions log, `make review` §9 gate (≥ 300 round trips, high-TOW > low-TOW) | as above once on | — |
| AU3 robustness | — | holds with TOW from the official crosses (+2.4-2.9pp, t 2.5); +4.4pp (t 3.0) under the moderate 15% cap; +2.7pp on top of tilt v2 | — | — |
| Roth cost gate on crosses | Study AW | report: IBS+night beats IBS-only below **3.7bp/side** (was 5.4); measured ~0, gate comment now ~3bp | — | — |
| IBS ETF opens on crosses | Study AW | report: −0.3..−0.7bp/leg, immaterial | — | — |
| AX1/AX2 closing / opening cross share | Bogousslavsky-Muravyev 2023; Berkman et al. 2012 | **DEAD** (AX2 +1.2pp both halves but t 1.5, placebo 94%) | ~+$28 / +$134 / +$293 (AX2, unproven) | passive close flow / open buyers |
| AY FINRA short-volume ratio, both signs | Diether-Lee-Werner 2009; BJZ 2008 | **DEAD** (t ≤ 0.6) | ~0 | — |
| AZ Roth ex-dividend capture | Elton-Gruber; Ruan-Ma 2012 | **DEAD** (gap +4-7bp/event = one round trip) | −$7 / −$36 / −$30 | taxable holders (gap too small) |
| Noise leg after publication | codecat replication | report: SPY dead after May 2024, QQQ ~halved (t 1.1), SMH intact; no action | plan QQQ at ~2.5bp/day | — |
| Closing imbalance (AC) | — | parked: the user does not want a Databento account unless necessary; AX was the free stand-in | — | — |

**Net result of the session:**
- **One new edge, built and off:** AU3, +$70 / +$323 / +$705 a year at $2.3k / $10k / $25k, plus the Roth.
- **One correction:** every night-leg level is ~2pp/yr lower on official auction prints.
- **The Roth cost gate is tighter:** ~3bp/side.
- **Six new dead ideas,** recorded so they are not redone.
