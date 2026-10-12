# Live-vs-backtest fidelity audit: night leg, IBS leg, Roth variants (2026-10-08)

Scope: report only, no code changed. Live evidence = `him:~/llm-trader/logs` (daily-live-*, daily-roth-*, daily-decisions-{live,roth}.jsonl, daily-fills-{live,roth}.jsonl, daily-source-diff.jsonl), 2026-09-23..10-08 (19 close runs, 213 signals, 70 night buys, 85 night sells, 14 IBS fills).
Scratch scripts (not committed): scratchpad `recompute.py`, `srcdiff.py`, `fills.py`, `cut.py`.

## Verdict
The noise-leg bug (a bar late on IEX) has no analogue in the night or IBS legs: both read Schwab consolidated quotes (night) or finished SIP daily bars (IBS), and the live numbers reproduce from SIP. The real gaps are (1) decision time 15:42 vs research 15:50 (net harmless), (2) account-size effects the replay may not model (taxable wash exclusion, 1-share probes, whole-share rounding), and (3) a Schwab-only dependency whose fallback is materially worse. None of them looks like a third-of-the-edge loss.

## Assumption table

| item | research / backtest | live code | match? |
|---|---|---|---|
| Night decision time | p50 = close of last minute bar before **15:50**; H/L = day's H/L unless extreme printed after 15:50 (`data/research/night/t1550.py:7-17`, `research/sim/data.py:31`, `fetch_late.py:11`) | timer 15:40, run starts ~15:42:10, scan 15:42:29, orders 15:42:41 (log 2026-10-07); phase window 15:38-15:50 (`executor.py:50-58`) | **NO, 8 min earlier** |
| Night price source | SIP 1-min bar close | Schwab real-time last trade + quote day high/low (`marketdata.py:142-181`, `quote_source: auto`); fallback Alpaca IEX last trade + (IEX daily bar U 15-min-delayed SIP daily bar) range (`marketdata.py:200-233`) | Schwab ~yes; fallback no |
| Night IBS | (p-L)/(H-L) with H,L incl. p (`signals.py:165-174`, shared by `research/sim/book.py:100`) | same function | yes |
| prev_close / day_ret | adjusted (adjustment=all) SIP daily close | `eligibility` SIP daily adjustment=all (`marketdata.py:111-129`), vs raw Schwab price; guarded by `prev_close_mismatch` 3% (`executor.py:969`) | yes except same-day ex-div (<3%, not guarded; research strips it, live keeps it) |
| Universe | close>=$5, 20d $ADV>=$10M, vol20>=60% (std of 20 log rets, bars < today) | identical, built 09:15, cached (`marketdata.py:101-136`) | yes |
| Dedupe corr | `night_days(max_corr=0.9)` default, 0.7 in live-mirror callers (`book.py:83`) | 0.7 (`config.yaml night_max_corr`) | yes if callers pass 0.7 |
| Crowding count n_raw | after dedupe, before vol filter (`book.py:109-112`) | same order (`executor.py:987-997`) | yes |
| Names excluded | none | `foreign` = other-leg/IBS symbols/open positions + wash guard (`executor.py:958-962`, `_roth_night_wash`/`_wash_symbols` `:1691-1724`) + quote older than 10 min / no hi-lo dropped (`marketdata.py:162-166`) | **NO** (see 2, 5) |
| Entry | close auction price C | MOC (`tif=cls`) | fills n=85: **-0.1bp** vs official close, none >20bp |
| Exit | official next open | OPG via Schwab AUTO routing | fills n=85: **-1.2bp** mean vs official open, median 0; 14/85 (16%) fill >20bp off the print, symmetric; log says 65% fill at the auction print |
| Sizing | frac = min(1/n, 10%) x min(1, 30/n); fractional $ | whole shares `floor` (`executor.py:~1050`), **1-share probe if target<1 sh and price<=$150** (`night_probe_max_usd`) | NO at $2-3k (see 3) |
| IBS decision | last complete daily bar d, buy open d+1, sell open d+2, re-evaluated daily (`book.py:124-141`, `ibs_oos.py`) | 09:15 on SIP daily bars < today, DAY order submitted 09:17, `momentum_top` 12-1 at last month-end (`executor.py:788-852`, `signals.py:57-73`) | yes |
| IBS fills | official open | DAY orders at the open | n=7 buys / 7 sells: -2.0bp / -0.1bp vs official open, none >20bp |
| IBS sizing | equal weight of leg | `notional=` order, whole shares | NO (see 3) |
| Roth IBS | same ETF | signal on original ETF, trade look-alike (XLE->VDE, SMH->SOXX, XLK->VGT; `executor.py:1726-1747`, `signals.py:286-291`) | **NO**: different index, untested instrument |

## 1. Decision time 15:42 vs 15:50: ~22-25% of picks differ, net effect ~0 or slightly favourable
- Research candidate minutes `data/research/night/lm1` (2020-11..2026-09, 84k name-days passing live filters: adv>=10M, c>=5, vol20>=0.6), signal re-evaluated at cutoffs 15:42 (live) and 15:50 (research); outcome = close -> next open, unweighted gross:
  - both: n 11,231, +28.6bp (t 5.2)
  - live-only (signal at 15:42, gone by 15:50): n 3,248, +22.0bp, median +21, ex-top-5 +13
  - research-only (appears by 15:50, not at 15:42): n 3,633, +10.5bp, median +2
  - all 15:42 = +27.1bp (n 14,479); all 15:50 = +24.2bp (n 14,864); day-level EW 39.5bp (t 4.1) vs 32.2bp (t 3.2).
  - So the live timing swaps ~23% of picks and is not worse than the research timing. Caveat: lm1 only has minutes from 15:30, so 15:42 H/L uses the daily extreme unless it printed after the cutoff (same convention as t1550.py). Per-year wobble is large (2021 -15 vs -20, 2025 +5.5 vs -5.1).
- Live sample: of the 70 live night buys, 18 (26%) would not be signals at 15:50 by SIP.
- Mechanism for the swap: 15:42-15:50 bounces (leave) and fresh lows (enter). Bounced names are the worse overnight trades (fetch_late.py comment); that is why 15:42 is not worse.

## 2. Live inputs reproduce from SIP; Schwab is the faithful feed
- 70 live night decisions (10 days, both accounts) recomputed from SIP raw minute bars to 15:42 (bars < 15:42): price diff median 0bp, mean -6bp, sd 31bp (15/70 >30bp: last trade vs last minute bar close, thin names); day_ret diff median 0; IBS diff mean -0.006, sd 0.026, 11/70 differ >0.03. Last minute bar available: 15:41 for every run.
- 66/70 (94%) still pass day_ret<=-8% & IBS<0.10 on SIP at 15:42. The 4 that do not: BIAF (live IBS 0.015 vs SIP 0.162), ZCSH (0.088 vs 0.129), CNXC (0.061 vs 0.108), USDE (0.097 vs 0.105): Schwab's day high/low or last print differs slightly from RTH-SIP (cause unverified; possibly extended-hours extremes). 5.7% false-positive rate.
- False negatives: names SIP-signalled that Schwab missed. From `daily-source-diff` (Alpaca-only names) 6 of 13 are genuine SIP signals at 15:42 (e.g. JAGX 09-28 ret -23%, IBS 0.076) => Schwab misses roughly 6/213 = ~3% of signals.
- Schwab-only picks (vs the Alpaca/IEX shadow): 30 names, 87% confirmed by SIP.
- IEX/SIP question: Alpaca is not used live. All 19 close runs say `prices from SCHWAB` (3,499-3,551 fresh quotes of ~3,620 eligible, so ~2.5% of eligible names drop for stale quote >10 min or missing hi/lo, plus 28-36 wash-excluded).
- Alpaca fallback (what would happen if the Schwab token lapses): it finds 181 of Schwab's 213 signals (85%) and adds 10 extras (46% confirmed on SIP). Design reason: IEX last trade can be 10 min old and the range union uses `DataFeed.DELAYED_SIP` (15 min stale at 15:42), so IBS is overstated. This is the same class as tonight's noise-leg finding, but latent, not active.

## 3. Account-size / execution deviations not in the replay
- Wash guard (taxable runs after the Roth; exact-symbol 31d on all legs): taxable close-run signal counts vs Roth same days (09-29..10-07): 58 vs 90 signals, 19 vs 40 after vol20 filter. The taxable book sees ~36% fewer signals and ~half the names. Per-trade edge is unchanged (random sample of the same population); the cost is exposure and a different n_raw for the crowding rule. Not modelled in `book.py`.
- 1-share probe oversize (`executor.py` night loop, `night_probe_max_usd` 150): 9 probes in 19 runs, targets $23-49 bought as $70-131 (1.7x-3.1x target: UCTT $23->$72, MRNX $42->$132, TEM $41->$72, CRWL $49->$104, FEIM $47->$80). Plus 9 `skip: $X buys 0 shares` (e.g. TWST $47, STX $33, 4 on 09-23 at $20). So about 18 of ~65 selected names (28%) are either distorted or dropped by rounding at the $2.3k scale.
- IBS whole shares: 2026-10-07 target $818/name -> SMH 1 sh $622 (76%), XBI 5 sh $747 (91%). Roth $500 slot -> VDE 2 sh $343 (69%). Average deployment ~80% of the intended leg.
- Roth IBS runs on the look-alike (VDE for XLE, SOXX for SMH); research used the original ETF. The ex-ante mismatch is unquantified (different index methodology, ~0.98 correlation assumed).
- Early-close skip (`executor.py:945`) matches research (half days excluded).

## 4. Fill-cost check against official prints (n scored 85 night buys, 85 sells, 7 + 7 IBS)
Night buy vs official close -0.1bp, night sell vs official open -1.2bp (median 0), IBS buy/sell vs official open -2.0 / -0.1bp. Execution assumptions (~0bp, `tier` costs conservative) hold. The jsonl `slippage_bps` field is vs the decision reference, not the auction print (known; do not read it as cost).

## Possible bugs / hygiene (report only)
1. Probe sizing (above): 1 share can be 3x the intended weight and breaks the `max_name_pct`/tilt weights; also a $150 price cap means expensive names are skipped (STX $803, TWST $168).
2. Silent fallback to IEX/delayed-SIP in `decision_rows` (`marketdata.py:184-197`) when Schwab returns nothing: logs only a "falling back" line; the 15-min-stale range makes `loser_picks` IBS too high. Consider failing loud or using `rth_minutes` (SIP minutes, 16-min delay) for the range instead.
3. `daily-decisions-*.jsonl` logs price/day_ret/IBS but not the high/low or quote time, so live IBS cannot be audited exactly; add high, low, trade_age_min, and the 15:41 minute bar.
4. Same-day ex-dividend: live day_ret includes the dividend drop, research (adjustment=all) does not; guard tolerance is 3%.
5. 11/70 live IBS values differ >0.03 from RTH-SIP; check whether Schwab `highPrice/lowPrice` include extended hours (compare `quote` fields to `regular`).

## What I did not verify
- IBS leg has only 7 live round trips; IBS fidelity is established from code and the 09:15 session canary, not P&L.
- 15:42 vs 15:50 test covers 2020-11..2026-09 candidates only (names whose daily low touched -8%), unweighted, no dedupe/sizing, no costs.
- Whether Schwab quote hi/lo include pre/post-market (cause of the 4 false positives).
