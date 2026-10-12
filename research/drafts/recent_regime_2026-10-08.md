# Recent regime: night + noise legs replayed through 2026-10-07 (2026-10-08)
Data extension (separate cache `data/research/recent/`): Alpaca SIP daily (adj=all) for the night universe 2026-09-17..10-07 (`research/sim/recent_fetch.py`), 15:30-16:00 minutes for -8%-low candidates 09-22..10-07 (`recent_night.py fetch`; earlier days already in `night/lm1`, which runs to 09-21, so the real gap was only 09-22..10-07), QQQ/SMH full minutes 2026-05-01..10-07 (`recent_fetch_qm.py`).
Runners: `research/sim/recent_night.py` (exact 15:40 rule on lm1 + extension; equal-weight per trade, NO dedup/corr/tilt/crowd scaling/weekend scale, so it is the raw signal, not the book), `research/sim/recent_noise.py` (reuses `noise_recent.trades_for/stats`, PROD QQQ+SMH). Nothing tuned.
Caveats: night next-open is the SIP daily-bar open (not always the 'O' print); 10-07 picks cannot be scored (10-08 open not in panel). Panel = today's listing universe plus whatever the cache holds (survivorship of the fetch universe; SHAR-SURV says ~-4bp).

## Night leg (bp per trade, buy close, sell next open; day-clustered t on daily means)
| period | n (days) | 0bp/side mean / med / hit / t | 2.5bp | 7.5bp |
|---|---|---|---|---|
| 2021-02..2026-09-21 (baseline) | 14022 (1385) | +26.0 / +20.3 / 53% / 4.31 | +21.0 / 3.76 | +11.0 / 2.65 |
| 2026-06..10-07 | 1581 (89) | +112.7 / +74.4 / 59% / 2.27 | +107.7 / 2.11 | +97.7 / 1.80 |
| 2026 YTD | 3081 (190) | +92.7 / +68.3 / 59% / 0.61 | +87.7 / 0.40 | +77.7 / -0.04 |
| live window 09-23..10-07 | 100 (10) | -55.3 / -23.5 / 38% / 0.14 | -60.3 | -70.3 |
Per year, 0bp: 2021 -14, 2022 +8, 2023 +45, 2024 +17, 2025 +5, 2026 +93. By month 2026-06..10: Jun +169, Jul +133, Aug +60, Sep +50, Oct(1-6) -149 (n 43). Ex-top-5 for 06..10-07: +98.8. Daily-mean sd ~300bp, so YTD day-clustered t is low (0.6) even at +93: the trade-level mean is large but concentrated in high-dispersion days (n/day 1..101).
Read: the night rule is NOT dead in the current regime; Jun-Aug 2026 is the best stretch since 2023 (higher-vol small-cap loser tape), fading through Sep, and the last 10 sessions are negative (-55bp, a 2-week negative run is ~1 SD of the daily noise). Costs matter much less here than in 2025 (2025: +4.9 gross, -10 at 7.5bp).

## Noise leg (QQQ+SMH PROD, bp per trade unlevered, net; per-fill cost)
| period | no-lag 0.5/fill mean (t, Sharpe) | lag 0.5/fill | no-lag 1/fill | lag 1/fill |
|---|---|---|---|---|
| 2016-2025 | +3.89 (4.2, 0.54) | +2.73 (3.4, 0.15) | +2.89 | +1.73 |
| 2021-2025 | +5.35 (3.6, 0.78) | +3.72 (2.9, 0.61) | +4.35 | +2.72 |
| 2026-01..05 | -1.53 (-0.4, -1.07) | -1.67 (-0.5, -0.89) | -2.53 | -2.67 |
| 2026-06..10-07 (n 143) | +0.91 (0.1, -0.19) | -0.32 (-0.05, -1.16) | -0.09 | -1.32 |
| 2026 YTD (n 352) | -0.54 (-0.15, -0.69) | -1.12 (-0.34, -1.01) | -1.54 | -2.12 |
| live 09-23..10-07 (n 14) | -17.1 | -10.1 | -18.1 | -11.1 |
Read: the noise leg has been ~0 or negative for all of 2026 (Sharpe -0.7 to -1.0 YTD, vs +0.6..0.8 in 2021-25) and the lag does not rescue it. Jun-Oct is flat before costs.

## Live overlay (09-23..10-07; fills from `ssh him` logs/daily-fills-{live,roth}.jsonl, night leg, buy-fill -> next sell-fill)
- 85 live night trips; 67 match a replay (date, sym) pick. On those 67: realized mean -37.4bp vs replay -40.2bp, corr 0.998, mean |diff| 10.7bp, median diff 0. Execution tracks the replay almost exactly (consistent with ~0bp measured cost).
- 18 live trips have no replay pick (12 are the 10-07 buys, unscorable; the rest: EVER, BKKT, SMU, GRML x2, SNK, ALMR etc., live signal differences such as vol20/ADV/ref-price timing).
- Replay raw picks 100 (09-23..10-07, excl 10-07); 67 traded live (live dedups/caps/whole-share). Replay mean -55bp (-24 ex JAGX -2110bp on 09-23); live taxable +8.2 (n 50; replay on its matched trades -9.4), Roth -107.7 (n 35; replay on matched -99.0).
- So live is consistent with the replay: both are the same noisy two-week negative stretch (SE ~60bp/trade); the taxable +8 vs Roth -108 gap is pick selection (wash-sale/dedup/cash) on correlated 10-06/10-07 selloff days, not execution.
- Noise live: 7 round trips earlier doc `noise_recent_2026-10-08.md` (live -14bp) vs lagged replay -10bp over 14 replay trips; same sign and scale.

## Verdict
Night: recent regime is positive in the aggregate (2026-06..10-07 +113bp gross, +98 at 7.5bp/side, t 1.8-2.3), far above the 2021-26 average (+26 / +11), so the live shortfall is a two-week sample, not a regime break. Because 2026 gains are concentrated in Jun-Jul and the replay is un-deduped, do not read +93bp as the book's expectation; no sizing change. Noise: no evidence of an edge in 2026 at any cost (consistent with earlier verdict: marginal, cost-bound). Keep as is; revisit the noise leg at user's discretion.
