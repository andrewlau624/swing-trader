# Scalp loop ledger (started 2026-10-13)

Question: can an intraday momentum signal hit a small take-profit (+G) before a stop (-S) often enough to beat
real costs? Prompt: `research/drafts/prompt_scalp_loop_2026-10-13.md`.

p* = (S + c) / (G + S). Ceiling at $10k = trades/day x net bp x share deployed x 50% x 250 (gate +8pp/yr).

| iter | track | idea | class tags (mech / data / universe / tod / counterparty) | p* | ceiling $10k | status | evidence |
|---|---|---|---|---|---|---|---|
| 1 | C | TAQ cost table: quoted/effective spread, TP touch-vs-through, stop slippage by liquidity x time of day (2012/2018/2025) | infra / TAQ->Alpaca SIP / all common + ETFs / all day / n.a. | n.a. | n.a. | **DONE** (Alpaca SIP 2018+2025, 2,357 samples; WRDS attempt stalled) | `research/sim/scalp_cost_alpaca.py`, `scalp_cost_out.txt` |
| 2 | A | SECT-LAG: sector ETF 5-min 2-sd up move -> buy laggard same-SIC constituents, G=S=0.5xETF move (15-50bp), T 15m (N 978) | lead-lag / TAQ 2010-19 / $10M-1B sector names / 10:00-15:30 / stale limit orders | 0.786 (c 9.4bp, G=S 16.7) | negative (net 1x -9.3bp) | **KILL** (judge era unopened): gross +0.08bp, p 0.25 vs p* 0.79; control/placebo identical | `sect_lag_out.txt:18-34` |
| 3 | A | ISO-BURST: ISO buy sweep >= 0.25% of ADV in 1 min (3x sell ISO) in large caps -> long, G=S=20bp, T 10m (N 979) | order-flow / TAQ 2010-19 / >=$200M ADV large caps / 10:00-15:30 / urgent institutional parent | 0.584 (c 3.4bp) | negative | **KILL** (judge unopened): gross +0.10bp; drift vs matched control +0.06bp at 10m (t 0.1) | `iso_burst_out.txt:2-16` |
| 4 | B | SCALP-CLF: GBM P(+30 before -30bp, 30m) on F1 price/volume path, >$1B names, 10:30-15:00; purged WF 2016-18, judge 2019 (N 980) | classifier / Alpaca SIP minute / >$1B ADV / midday / none named (pattern) | 0.56 (1x) / 0.62 (2x) | negative | **KILL**: 2019 top bucket p 0.431 (lo 0.420); net -6.6bp 2x t -12.5; time-shift null 0.413 ~= real (model learns vol, not direction) | `scalp_clf_out.txt:28-55` |
| 5 | C | SCALP-PASSIVE: buy limit at the NBB, fill only on trade-through (pess) / at-or-below (opt), 1/5/15m markout vs aggressive entry; reuses iteration-1 samples | infra / Alpaca SIP cached / all buckets + ETFs / all day / adverse selection | n.a. | n.a. | **DONE**: passive saves ~2bp in >$1B (c 7-10 vs 9-12bp; midday 1-5bp) at 40-46% fill; nothing for ETFs; in thin names the saving is adverse selection (15m markout -15..-21bp) | `scalp_passive_out.txt` |
| 6 | A | RETAIL-HERD: 09:30-10:30 BJZZ retail buy imbalance >= 0.5 (retail $ >= 0.5% ADV) and up -> long top 5 at 10:30, G=S=40bp, T 60m (N 981) | retail herding / TAQ sub-penny TRF / $50M-1B / 10:30 fixed / wholesaler hedge + late retail | 0.554 (c 4.4bp) | negative | **KILL** (judge unopened): gross -0.10bp, net -4.5bp; herd fades -4.5bp by +60m vs no-retail momentum +4.4 (t -1.3) | `retail_herd_out.txt` |
| 7 | B | SCALP-OFI: GBM on order-flow/quote features (Cont OFI, quote imbalance, signed $, ISO/retail/odd-lot shares) for +20 before -20bp in 15m, >$500M names; WF 2011-13, judge 2015 (N 982) | classifier / TAQ quotes+trades / >$500M / 10:00-15:30 / informed + liquidity demanders | ~0.58 (1x) | gate binds on precision | running | round1_prose SCALP-OFI |
| 8 | A | STOP-RUN: first prior-day-low breach with 3x volume footprint -> long at breach+3m, G=S=30bp, T 30m; controls no-footprint + PDL+50bp placebo level (N 983) | forced stops (reversal) / TAQ 2010-19 / >$500M / 10:00-15:00 / stop-loss sellers | 0.579 (c 4.7bp) | -0.16pp (0.14 events/day) | **KILL**: n 14 in 100 days (registration error: universe too small, 200-trade gate unreachable); footprint arm -14.5bp at +30m vs no-footprint +36.9 (mechanism sign wrong) | `stop_run_out.txt:18-64` |
| 9 | A | LEVEL-BOUNCE: quiet first touch of prior-day low (< 1.5x vol) in $50-500M names -> long at m+4, G=S=40bp, T 30m; controls burst / PDL+50bp / random minute (N 984) | resting liquidity at a level / TAQ 2010-19 / $50-500M / 10:00-15:00 / limit buyers at support | 0.578 (c 6.2bp) | negative | **KILL** (judge unopened): gross +3.0bp, net -3.2bp; +30m drift = placebo level (+7.3 both): generic dip reversal, not a level | `level_bounce_out.txt` |

## Cost table (Track C output, used by every A/B idea)

Source `data/research/program/scalp_cost_out.txt` (Alpaca SIP, 10 days/yr, ~30 name-days per bucket-year; c = quoted
half-spread in + out, median; means ~1.5-2x medians, driven by the open).

2025 round-trip c (bp), by 20d $vol bucket x time of day:

| bucket | 0930-45 | 0945-1030 | 1030-12 | 12-14 | 14-1530 | 1530-16 |
|---|---|---|---|---|---|---|
| >$1B | 10.2 | 9.1 | 7.1 | 5.6 | 5.0 | 3.4 |
| $200M-1B | 19.7 | 11.2 | 9.0 | 6.9 | 5.5 | 3.9 |
| $50-200M | 33.5 | 18.2 | 10.2 | 10.2 | 7.7 | 6.3 |
| $10-50M | 78 | 29 | 22 | 15 | 15 | 12 |
| $2-10M | 82 | 55 | 37 | 20 | 19 | 17 |
| ETFs (SPY/QQQ/IWM/SMH/TQQQ) | 0.4-0.7 all day | | | | | |

- 2018 is cheaper in large caps (>$1B 4.7 -> 2.7bp across the day); $2-10M 66 -> 14bp.
- **Minimum G (c <= 25% of G):** >$1B 2025 14-41bp (midday ~22); $2-10M 67-327bp; ETFs 2-3bp.
- **Limit TP realism (G 20bp, 30m):** touch 0.44-0.51 but THROUGH (lit, size >= 100) only 0.08-0.29 (2025). A bar/touch backtest
  overstates TP fills ~2x: always use "through".
- **Stops:** median slippage ~0 in liquid names; thin names have fat tails ($2-10M 2025: mean 33-39bp, p90 ~105-113bp past the stop).
  Entry at the ask with S < spread triggers immediately (trigger rate ~0.9 at S 10bp).
- Rule of thumb for every idea: single-stock scalps need a 1-30 min gross drift of >= ~2x the c above (>= 10-20bp in large caps
  midday, >= 40bp in $10-50M names); only ETFs have c small enough for a few-bp edge, and ETF minute momentum is already dead.
- **Passive entry (iteration 5, `scalp_passive_out.txt`):** a bid at the NBB fills (trade-through) 40-46% in >$1B, 14-26% in thinner
  names; effective round trip ~2bp below aggressive in >$1B (midday ~1-5bp), no gain in ETFs, and in $10M-$50M / $2-10M names the
  fills are adversely selected (unfilled drift up, filled drift -20..-41bp). **For a MOMENTUM scalp passive entry is structurally
  wrong:** a resting bid fills when the price falls, i.e. exactly when the momentum signal is failing; the 2bp saving applies only to
  mean-reversion entries.

## Waiting on user

(none yet)

## Checkpoints

## Ceiling-killed before coding (no N)
- **Post-FOMC 14:00-14:30 ETF momentum + 10:00 macro-release momentum (SPY/QQQ/TLT), 2026-10-13.** ~8 FOMC + ~60 10:00 releases/yr:
  0.27 events/day x ~10bp net x 4x intraday BP x 50% x 250 ~ +3pp/yr at the optimistic end; below +8pp. Pre-FOMC drift already dead.

### Checkpoint 1 (2026-10-13, after iterations 1-5)
- **Tried:** cost table (C), SECT-LAG lead-lag (A), ISO-BURST order-flow (A), SCALP-CLF classifier on price paths (B), passive-entry
  markouts (C). RETAIL-HERD (A, iter 6) running. FOMC/10:00-release ETF momentum ceiling-killed.
- **Died and why:** every signal had gross drift ~0 over 1-30 min (SECT-LAG +0.08bp, ISO-BURST +0.10bp, CLF top bucket net < 0 with a
  time-shift null equal to the real model). The loss is exactly c plus the barrier asymmetry. No sign of a minute-scale directional
  footprint from lead-lag, sweeps or price/volume paths, even in 2010-14.
- **Best hit rate vs p*:** SCALP-CLF top 5% p 0.431 vs p* 0.560 (1x). ISO-BURST 0.248 vs 0.584; SECT-LAG 0.254 vs 0.786.
- **Best net bp/trade (pessimistic, 1x):** ISO-BURST -3.26bp (cheapest names). Nothing positive.
- **Cost table:** see above (large caps 3-10bp RT, mid caps 7-20, thin 12-80, ETFs 0.5; passive saves ~2bp in large caps only).
- **Read so far:** optional stopping makes the TP/stop frame equivalent to "mean drift to exit > c"; none of the three mechanisms
  produced ANY drift, so the problem is not cost, it is the absence of minute-scale predictability. Continue with different
  counterparties/horizons (retail flow running); if iterations 6-10 are also ~0 gross, name single-stock minute momentum dead as a class.
- **Waiting on user:** none.
