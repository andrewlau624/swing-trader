# Scalp loop ledger (started 2026-10-13)

Question: can an intraday momentum signal hit a small take-profit (+G) before a stop (-S) often enough to beat
real costs? Prompt: `research/drafts/prompt_scalp_loop_2026-10-13.md`.

p* = (S + c) / (G + S). Ceiling at $10k = trades/day x net bp x share deployed x 50% x 250 (gate +8pp/yr).

| iter | track | idea | class tags (mech / data / universe / tod / counterparty) | p* | ceiling $10k | status | evidence |
|---|---|---|---|---|---|---|---|
| 1 | C | TAQ cost table: quoted/effective spread, TP touch-vs-through, stop slippage by liquidity x time of day (2012/2018/2025) | infra / TAQ->Alpaca SIP / all common + ETFs / all day / n.a. | n.a. | n.a. | rerunning on Alpaca (WRDS standby too slow: read-only, 40s+ per NBBO scan, connection cap) | `research/sim/scalp_cost.py` |
| 2 | A | SECT-LAG: sector ETF 5-min 2-sd up move -> buy laggard same-SIC constituents, G=S=0.5xETF move (15-50bp), T 15m (N 978) | lead-lag / TAQ 2010-19 / $10M-1B sector names / 10:00-15:30 / stale limit orders | 0.786 (c 9.4bp, G=S 16.7) | negative (net 1x -9.3bp) | **KILL** (judge era unopened): gross +0.08bp, p 0.25 vs p* 0.79; control/placebo identical | `sect_lag_out.txt:18-34` |
| 3 | A | ISO-BURST: ISO buy sweep >= 0.25% of ADV in 1 min (3x sell ISO) in large caps -> long, G=S=20bp, T 10m (N 979) | order-flow / TAQ 2010-19 / >=$200M ADV large caps / 10:00-15:30 / urgent institutional parent | ~(20+c)/40 ~0.6 | gate binds on net | running | round1_prose ISO-BURST |
## Cost table (Track C output, used by every A/B idea)

(pending iteration 1)

## Waiting on user

(none yet)

## Checkpoints
