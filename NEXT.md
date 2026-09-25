# Pending decisions

Short, current, and the first thing to read when picking this up again.
Full evidence lives in `RESULTS.md`; this file is just what is *waiting*.

---

## Live checkpoint (2026-09-24, `make review SINCE=2026-09-22`)

Schwab brokerage live since 09-22 on a $1k cap. Night exits **19/50**; open
sells **−2.1bp/side** vs the auction print (buys −0.5bp), well inside the
10bp gate. Live beat the backtest on the same trades (−1.75% vs −1.92%); the
losses are one bad night, not execution. `daily-status`'s +33bp is vs the 15:50
decision price, not a cost. At 50 exits ≤ 10bp: overnight leverage opens by
itself, and the aggressive profile (addendum 22) becomes an option.

## Addendum 25 (2026-09-24): micro futures, nothing new to run

No new edge in futures. The live QQQ noise leg on MNQ passes (both halves,
placebo, stress), and so does IBS overnight weakly, but both are bets the book
already holds. MNQ's advantage over QQQ is about +1.6pp/yr after tax (1256
60/40, lower cost, no wash sales). The blocker is size: one MNQ is about $61k
notional, so staying at or below 2x needs about $30k per contract. Revisit
when the brokerage book reaches about $30k: move the noise leg from QQQ to
MNQ in a futures account instead of adding a second copy. ORB on NQ/ES: dead.

## Addendum 24 (2026-09-24): leap book, SHADOW ONLY, off

No tested rule 5x's in months: P(5x in 12 months) is 7% at best; ~4 years median,
about the aggressive profile's pace with 2-4x its drawdown. Two survivors, built
in shadow only (`swingtrader/leap/`, `leap.enabled: false`, no order path):
SOXL IBS < 0.2 (robust) and SOXL 15-min ORB (fragile: ~0 in 2016-20, dies
at 10bp or a 1-min fill delay). Going live needs a separate Schwab account and a
wash-sale plan against the Roth's SOXL/SOXS intraday leg. The shadow logger is
not scheduled yet: it needs a minute-bar feed (the streaming process). Wire
that, run a few months of shadow, then decide.

## Addendum 23 (2026-09-24): tilt v2 built, OFF

`daily.night_tilt_model: v2` adds yesterday's return to night sizing: replay +$23k
($260.6k → $283.7k), every year better, but borderline (sign opposite the prior, best of 9).
The 15:40 log shows what v2 would weight. Decide after the fill-cost checkpoint.

## Addendum 22 (2026-09-24): experimental growth profile, OFF by default

`DAILY_LIVE_PROFILE=aggressive` in `.env` runs the brokerage book at 1.3x overnight
(ungated), 20% per name, conviction live, intraday 0.6x. Remove the line to go back.
`make daily-status` names the active profile and its real overnight size (`=== LIVE (real money) profile aggressive ===`, `overnight size 1.30x`).
Recommended only AFTER ~50 night exits confirm open-sell cost ≤ 10bp/side: if the
edge is half what history says, it earns ~22%/yr vs ~18% for a 68% chance of a >30% drop.
Also shipped: the intraday cap now charges TQQQ/SQQQ 75% margin (cap 1.0 → 0.75 once conviction is live).

## Addendum 21 (2026-09-24): nothing adopted

SOXL conviction, bear-hedge overlays and thin-volume night names: dead. One
conditional: once ~50 live night exits exist, check the cost of names under
$10 in `make review`; if ≤ ~20bp/side, set `daily.night_price_min: 3.0`.

## Addendum 20 (2026-09-24): review fixes + Roth IRA book

- **Live now (on `make pull`):** one-share probes for night picks that round
  to 0 shares (≤ $150), and the intraday leg goes live on a capped book when the
  ACCOUNT is ≥ $2,000. With the $1k cap that means real QQQ/SMH day trades
  (small: whole shares). Keep watching `route ...: bps, % at the auction print`.
- **Decision rule for the broker:** if Schwab's open sells average > ~10bp/side
  after ~50 exits, move the brokerage book to Alpaca live (real OPG orders):
  each bp/side is ~0.85pp/yr.
- **Roth, to switch on:** (1) apply for limited margin on the Roth at Schwab;
  (2) set `SCHWAB_ACCOUNT_NUMBER` (brokerage) and `SCHWAB_ROTH_ACCOUNT_NUMBER`
  in `.env` BEFORE re-running `make schwab-login` with the Roth ticked, or the
  brokerage book stops (two accounts linked, it refuses to guess); (3)
  `ROTH_LIMITED_MARGIN=yes`; (4) sell the Roth's ETFs yourself (the bot never
  touches your holdings); (5) `make daily-roth-check`, then `make daily-roth-on`.
- **Dead:** cheaper margin as the lever, SGOV for night cash, −6..−8% night
  names, intraday diversification into bonds/gold/oil/SPY.

## Addendum 19 (2026-09-24): conviction trade built, SHADOW

TQQQ strong-first-breakout trade, ~70 days/yr, 0.5 of equity inside the same
daytime margin. Simulator: 40.7% → 49.8%/yr at the same Sharpe. It logs as
`[conv]` and places nothing until `daily.conviction_mode: auto`. Switch it on
after the regular intraday leg has about a week of clean live fills (entries at
:01/:31, flat by 15:57). `make daily-status` shows its shadow record.

## Addendum 18 (2026-09-24): crash guards shipped

`night_max_corr` 0.9 → 0.7 and `night_weekend_scale` 0.5. COVID crash on the
book −17% → −4%; 2021–26 Sharpe 1.81 → 1.98. Weak spot left: the intraday
leg is the only short side, and it is fading. If it dies, a slow bear is unhedged.

## Addendum 16 (2026-09-24): what changed, what is waiting

- **Shipped:** night sizing tilt, QQQ + SMH intraday split, Schwab open sells
  directed to the listing exchange's opening auction, pre-registered kill
  rules, swing book off the schedule. Simulator: 35.2% / 1.76 → **41.3% /
  1.89** (tiered costs 33.0 → 39.2).
- **Waiting on live fills, and automatic:** overnight leverage (0.65 + 0.65)
  opens only after 50 night exits average ≤ 10bp/side vs the official open.
- **Watch first:** the 15:40 log line `route NASDAQ/NYSE/...: n, bps, % filled at
  the auction print`. If directed orders are refused, the log says so and
  the bot falls back to Schwab routing. If they are accepted but the hit rate is
  low, set `daily.schwab_open_route: auto` and compare the two.
- **Kill rules are live** (`signals.KILL_*`). Do not loosen them after seeing
  results. Status: `make daily-status`. Undo: `python scripts/daily.py
  --unkill LEG --account live`.
- **On the server:** `make pull && make persist` (reinstalls the schedule
  without the swing timer). The swing paper book's open positions keep their
  broker stops; flatten them in the Alpaca paper dashboard if you want it clean.
- **Next research:** after ~2 months, fit a per-name cost model on
  `logs/daily-decisions-live.jsonl` (quoted spreads) + `daily-fills-live.jsonl`,
  and replace the assumed tiers in `research/sim/book.py`.

## ⚠ Read addendum 14 first (2026-09-23)

- The daily book's published numbers were inflated by a research lookahead
  and a few bad bars. Corrected live book (no intraday leg): **20.1% / Sharpe
  1.27 / −14%**, was 23.8% / 1.46. Full book 36.5% / 1.57 (was 40.7% / 1.70).
- The swing headline (15.1% / 0.95) is one lucky fold alignment; over six
  offsets it averages ~12% / 0.72, about SPY. At the live cadence (daily
  re-selection) it is 11.2% / 0.67 / −27.7%. **Items 0 and 0b below do not
  help at that cadence and stay OFF.** The swing book stays on paper.
- The first real test of the night leg is the Schwab open sells (no
  market-on-open order at Schwab). `make review` after ~50 round trips.

---

## 0. Uncap the candidate list — DEAD at the live cadence (addendum 14)

**Status:** found 2026-09-22, validated (RESULTS.md addendum 5), **not enabled.**

`selection.top_n: 8 -> 999` plus `portfolio.position_pct: 0.10`:
Sharpe 0.95 -> 1.16, CAGR 15.1% -> 22.3%, maxDD -14.4% -> -15.3%,
risk-matched 15.1% -> ~21%. The rank score has no predictive power (ranks 9+
earn the same as 1-8), shuffle/flip controls pass, beats baseline every year.

**Why now is cheap:** the systemd unit failed with 216/GROUP on every run until
924d854, so the live slippage sample is ~empty. Switching before fills
accumulate costs the experiment nothing.

**Open question before trusting live numbers:** live re-selects daily; the
backtest re-selects every 42 days, and an honest 21-day refresh scored far
worse (9.5%). Build a short-refresh backtest that matches the executor.

**Pair it with the correlation cap below** — on the uncapped book the cap is
where most of the risk-adjusted gain comes from.

---

## 0b. Correlation cap on new entries — DEAD at the live cadence (addendum 14: 1d uncapped + 0.7 = 8.5% / 0.58)

**Status:** researched and validated (RESULTS.md addendum 13); implemented in
`swingtrader/backtest.py`, `swingtrader/live/executor.py` (the live swing loop)
and `config.yaml` as `strategy.max_corr` (**null = off**). Setting it now governs
live as well as backtest.

**What it is:** walk candidates best-ranked first, drop any whose trailing
20-day returns correlate above `max_corr` with an already-held (or same-bar
pending) name. The same duplicate-bet rule the night leg already uses
(`daily.night_max_corr`, addendum 11). Eight slots should be eight bets.

**What it buys** (deployable uncapped config, −10% stop, cash BIL):

| | uncapped | + max_corr 0.7 | + max_corr 0.6 |
|---|---|---|---|
| Sharpe | 1.16 | **1.33** | **1.47** |
| max drawdown | −15.3% | **−10.3%** | **−8.0%** |
| CAGR | 22.3% | 20.2% | 20.5% |
| risk-matched | 21.0 | 28.4 | 37.2 |

Robust to the correlation window (10–40d), passes flip/shuffle, bootstrap
P(mean ≤ 0) = 0.0004, survives +10bps/side. Crucially it **beats a matched
random-drop control** (keep 67% at random → risk-matched 12.0), so the gain is
the correlation, not the reduced trade count. On the *live top8* config the
gain is small (15.1/0.95 → 13.8/1.02 at 0.7); its value is on the uncapped book.

**To enable:** set `strategy.max_corr: 0.7` in `config.yaml`. Do it in the same
change as the uncap (item 0) — that is where the benefit lives. (The live
executor applies it now; `live/executor.decide` shares the backtest's formation
length, overnight gate and correlation cap.)

---

## 1. Switch on the overnight-gap filter — WAITING ON LIVE FILLS

**Status:** researched, validated, committed, **deliberately not enabled.**

**What it is:** require that a dip be made mostly of overnight gaps
(`prev_close -> open`) rather than intraday selling, over a 5-day window.
Implemented as `strategy.min_overnight_share` in `config.yaml`, currently
`null`.

**What it buys** (walk-forward, 2021-2026, high-vol cohort, −10% stop, cash in BIL):

| | now (off) | with filter 0.3 |
|---|---|---|
| Sharpe | 0.95 | **1.34** |
| max drawdown | −14.4% | **−11.1%** |
| avg per trade | +2.46% | **+5.00%** |
| risk-matched CAGR | 15.1% | **22.3%** |
| months to significance | 40.5 | **19.5** |
| trades | 207 | 111 |

**Why it is off:** the live run exists to measure real slippage against the
20bps/side the backtest assumes. Changing the strategy mid-experiment
contaminates that measurement, and the underlying feature was only nominally
significant (Spearman +0.158, p=0.020, failing Bonferroni across 9 features).

**Trigger to turn it on:** roughly **20 real fills** collected, i.e. measured
slippage has converged (`make slippage` shows n ≥ 20).

**Then:**
```bash
make slippage                      # record the before number
$EDITOR config.yaml                # strategy.min_overnight_share: 0.3
make dry                           # sanity check
git commit -am "enable overnight filter after N fills"
```
Keep the before/after clean — that comparison is the whole point of waiting.

**If measured slippage comes back far worse than 20bps** (say >50bps/side),
turn the filter on *sooner*: its per-trade edge is +5.00% vs +2.46%, so it
tolerates roughly twice the cost before the edge disappears.

---

## 2. Lingering on the server — CHECK THIS

`make persist-status` must say `lingering: ON`. If it says OFF, the systemd
timer dies the moment the SSH session closes and the bot silently never runs.
As root: `loginctl enable-linger ihearthim`.

---

## 3. Email — never actually verified

`make notify-test` has not been run successfully. Until it has, assume alerts
do not work. `trading@andrewlau.dev` is a verified domain so it should be fine,
but "should" is not "did".

---

## Things already tested — do NOT redo these

| idea | verdict | why |
|---|---|---|
| News sentiment filter | **dead** | mean P&L diff +0.97pp, p=0.63 |
| FF3 residual z-score | **dead here** | FF3 explains only 22% of variance in this universe; strips little, adds 4 params of noise |
| Bertram optimal thresholds | **dead** | prescribes −0.4σ entry; risk-matched return falls monotonically as entry loosens. −2.0 was already optimal |
| Trailing / let-winners-run exits | **dead** | selection screens for *non*-trending names; a trend-following exit contradicts it |
| Long/short (shorting range tops) | **dead** | negative in every configuration |
| Looser entry for more trades | **dead** | raises CAGR, raises drawdown faster |
| Broad-market cohort | **weak** | 1.6% CAGR vs 15.1% — the edge needs high volatility |
| Momentum sleeve at 25% | **promising, unvalidated** | blend Sharpe 1.09 vs 0.95, but standalone CAGR swings 1.2–43.6% across settings |
| Parking idle cash in BIL/SGOV | **ADOPTED** | 86% of position-days were idle; +3.3pp CAGR, free |
| Uncapped candidates (top_n 999) | **found, pending** | risk-matched 15.1 -> 21.0%, controls pass (addendum 5) |
| z_window 10 / 40, formation 63 / 252 | **dead** | all 4-9% risk-matched vs 15.1% |
| −10% stop vs no stop | **ADOPTED** | 11.8% vs 8.6% CAGR, and lower drawdown |
| Shock-share filter (dip = one big down day) | **dead** | rm 27.7 but threshold is a spike (0.5), non-monotone per-trade — overfit (add. 13) |
| Volume-z dip filter | **weak** | rm 18–23, at or below the matched random-drop control (~20) |
| IBS / close-at-low as an entry gate | **dead** | closing at lows is a falling knife — worst bucket (+0.56%/trade) |
| z-turn-up, z-depth band, 52w-high distance | **dead** | no robust effect, unstable across halves |
| Regime gates (SPY 5d return, VIXY fear proxy) | **dead** | unstable across halves; SPY>200dma only buys Sharpe for return |
| Fixed take-profit exit | **dead** | worse at every level (cutting winners, same as trailing) |
| Inverse-vol / overnight-share position sizing | **weak** | top8 +5pp CAGR at best, no gain on the uncapped book |
| Correlation cap on new entries (`max_corr`) | **dead at live cadence** | uncapped Sharpe 1.16→1.33 at 42d refresh; 8.5%/0.58 at the live 1d refresh (add. 14) |
| Night leg: index filler for unused capital | **dead** | helps 2024–26 only (add. 16) |
| IBS idle half in SPY/QQQ/overnight index | **dead** | helps 2024–26 only; BIL stays (add. 16) |
| Night leg: skip high-cost names | **dead** | cheap thin names are the best bounces (add. 16) |
| Daily-bar spread estimators as cost model | **dead** | measure volatility, not spread, on these names (add. 16) |

## Ideas not yet tested

- Multiple formation horizons (5/10/20d) simultaneously — the one remaining
  structural fix for 14% capital utilisation
- Cross-sectional ranking instead of a binary z-threshold (always deployed)
- Crypto sleeve (24/7, AVAX/DOT/LTC screen as tradable)
- Limit orders at the bid instead of market-on-open — bounded by addendum 13:
  paying 0 vs 20bps is worth ~+2pp CAGR, so the upside is real but modest

---

## 6. TQQQ strongest-breakout leg — FOUND, NOT BUILT (optional)

The PDT rule is gone (addendum 9), so the full QQQ intraday leg is now live
instead. Revisit this only after ~3 months of real intraday fills: the
TQQQ variant scores Sharpe 1.79-1.83 vs 1.70 with a smaller max drop.
First breakout of the day, strength >= 0.341 sigma, TQQQ up / SQQQ down.

---

## 5. Swing sleeve inside the daily book — RESOLVED: not worth it

Daily-refresh swing backtest (matches live): 12.3% CAGR, Sharpe 0.87. As a
sleeve it only trades return for drawdown (addendum 10). Keep it as its own
paper book.

## 7. Add SMH to the intraday leg — DONE (addendum 16, `daily.noise_extra`)

Split the 3.5x intraday budget QQQ/SMH: Sharpe 1.70 -> 1.78, max drop -20%
-> -16%, same return. Needs the noise leg generalised to several
instruments (book.noise is single-instrument today).

---

## 4. Daily-cadence book — RUNNING (paper + Schwab live since 2026-09-22)

**The plan (original, 2026-09-22):** paper-test, then real money. Done:
Schwab live since 09-22 on a $1k cap. The intraday leg switches on by itself
once the ACCOUNT holds $2,000 (`daytrade_mode: auto`; PDT retired 2026-06-04).

**Going real-money — via SCHWAB, see SCHWAB.md** (paper stays on Alpaca and
keeps running beside it). The Alpaca-live steps below still work if
`daily.live_broker: alpaca`.
```bash
# 1. Alpaca dashboard: open the LIVE account, make sure it is a MARGIN
#    account (a cash account causes good-faith violations with this book),
#    fund it, create live API keys (they start with AK)
# 2. on the server, add to .env:
#      ALPACA_LIVE_API_KEY=AK...
#      ALPACA_LIVE_SECRET_KEY=...
make daily-live-check    # connects, shows balance + margin, changes nothing
make daily-live-on       # type REAL MONEY; sets DAILY_LIVE=on in .env
make daily-status        # PAPER and LIVE side by side
make daily-live-off      # back to paper only (warns if it still holds positions)
```
The switch is stored in `.env` on purpose. `make pull` does `git reset
--hard`, so a switch kept in config.yaml would be silently undone on the next pull.

**Honest timeline:** 3k -> 25k at the backtest's 21.8%/yr is ~11 years. At the
2x setting (44.5%/yr, -22% DD) it's ~6 years. Deposits count: the live book
sizes from the real balance.


**Status:** built 2026-09-22 (`scripts/daily.py`, `swingtrader/daily/`),
research in RESULTS.md addendum 6.

| leg | what | live? |
|---|---|---|
| IBS tech ETFs | QQQ/SMH/XLK, IBS<0.2 on the last bar -> buy at the open (fractional DAY order), hold while it stays <0.2 | **live** |
| overnight losers | 15:40 ET scan: down >= 8%, within 10% of the day's low -> buy at the close auction, sell at the open auction | **live** |
| QQQ intraday momentum | noise-area breakout, 30-min decisions, flat at the close | **live** from $2k (PDT rule retired 2026-06-04; addendum 9) |

Weights 0.5 / 0.5 of book equity: 1x, no margin. Backtest (honest, 15:50
signal, 7.5bp/side): 21.8% CAGR, Sharpe 1.30, maxDD -11%. Both at 1.0 is
44.5% / -22% and needs 2x overnight margin: one line each in config.yaml.

**Day-trading gate:** $2,000 (Reg T). The $25k pattern-day-trader floor was
retired 2026-06-04. For the REAL account, ask Alpaca for a leverage-enabled
margin account (4x intraday); a standard margin account caps this leg at 1.5x.

**What to watch:**
- night-leg slippage vs the 15:40 reference price (`make daily-status`).
  Research assumed 7.5bp/side. The edge is gone around 15bp.
- whether 2021-23-style weakness shows up: that leg's return was almost all 2024+.
- CLS/OPG rejections in the email. Paper has not yet been proven to accept
  auction orders from this code; the first 15:40 run is the test.

**Not modelled:** at $3k, whole-share rounding on auction orders ($150 per
name), and names above ~$150 buy one share or none.
