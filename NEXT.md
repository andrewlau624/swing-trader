# Pending decisions

Short, current, and the first thing to read when picking this up again.
Full evidence lives in `RESULTS.md`; this file is just what is *waiting*.

---

## 0. Uncap the candidate list — READY, YOUR CALL

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

## Ideas not yet tested

- Backtest with the executor's daily re-selection (see item 0)

- Multiple formation horizons (5/10/20d) simultaneously — the one remaining
  structural fix for 14% capital utilisation
- Cross-sectional ranking instead of a binary z-threshold (always deployed)
- Crypto sleeve (24/7, AVAX/DOT/LTC screen as tradable)
- Limit orders at the bid instead of market-on-open — this strategy *supplies*
  liquidity, so it may earn the spread rather than pay it

---

## 6. PDT-capped TQQQ breakout leg — FOUND, NOT BUILT

<= 3 day trades per 5 days, first QQQ noise-area breakout of the day with
strength >= 0.341 sigma, traded as TQQQ (up) / SQQQ (down) with 50% of
equity. Book 23.8%/1.46 -> 36.0%/1.84, same -14% max drop (addendum 8).
Must hard-block a 4th day trade in 5 days.

---

## 5. Swing sleeve inside the daily book — FOUND, BLOCKED ON ITEM 0

Adding the swing strategy as a third of the capital: Sharpe 1.46 -> 1.58+,
max drop -14% -> -9% (RESULTS.md addendum 7). First build the daily-refresh
swing backtest (item 0); if it holds, run swing on the live account at 1/3
with night/IBS at 1/3 each.

---

## 4. Daily-cadence book — RUNNING (paper), $3k virtual equity

**The plan:** paper-test now. Then real money starting at $3k, with the
same two overnight legs. When the real account reaches $25k, the QQQ
intraday leg switches on by itself (`daytrade_mode: auto`).

**Going real-money** (paper keeps running beside it, for comparison):
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
| QQQ intraday momentum | noise-area breakout, 30-min decisions, flat at the close | **shadow** until book equity >= `daily.daytrade_min_equity` ($25k) |

Weights 0.5 / 0.5 of book equity: 1x, no margin. Backtest (honest, 15:50
signal, 7.5bp/side): 21.8% CAGR, Sharpe 1.30, maxDD -11%. Both at 1.0 is
44.5% / -22% and needs 2x overnight margin: one line each in config.yaml.

**Why $25k for the switch:** FINRA's pattern-day-trader rule. Below $25k, a
margin account may make at most 3 day trades in 5 days. The intraday leg makes
one to two a day. The shadow ledger (`make daily-status`) accumulates
out-of-sample evidence for it until then.

**What to watch:**
- night-leg slippage vs the 15:40 reference price (`make daily-status`).
  Research assumed 7.5bp/side. The edge is gone around 15bp.
- whether 2021-23-style weakness shows up: that leg's return was almost all 2024+.
- CLS/OPG rejections in the email. Paper has not yet been proven to accept
  auction orders from this code; the first 15:40 run is the test.

**Not modelled:** at $3k, whole-share rounding on auction orders ($150 per
name), and names above ~$150 buy one share or none.
