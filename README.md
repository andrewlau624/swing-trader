# swing-trader

An automated trading bot, and the research behind it. It started as a test of
one range-bound swing strategy (the "Origin" section below). What runs today is
the **daily book**: three short-hold legs sized from one account, trading real
money at Schwab alongside an Alpaca paper control.

**Status (2026-09-24):** the daily book trades **paper (Alpaca) + real money
(Schwab brokerage, capped at `DAILY_LIVE_CAPITAL`)**. The Roth IRA book is built
but off. The original swing book is quarantined (`SWING_BOOK=off`).

> **Picking this up again?** Read `NEXT.md` first: what is waiting on what,
> and everything already tested and ruled out. `RESULTS.md` has the evidence
> (addenda 1-25).

## What runs

| leg | what it does | when (ET) | state |
|---|---|---|---|
| **IBS** | top 3 of 18 ETFs by 12-1 momentum; buy when IBS < 0.2, hold while it stays < 0.2 | 09:15 open | live |
| **night** | 15:40 scan for names down ≥ 8% near the day's low; buy at the close auction, sell at the next open auction | 15:40 / 09:15 | live |
| **intraday (noise)** | QQQ + SMH noise-band breakout, decisions every 30 min, flat by 15:57 | 10:01-15:31 | live once the account is ≥ $2,000 (Reg T; the PDT rule was retired 2026-06-04), shadow below |
| **conviction** | TQQQ, strong first breakout only (~70 days/yr) | intraday | shadow (`daily.conviction_mode`) |

Weights are 0.5 / 0.5 overnight (1.0x, no margin). Overnight leverage (1.3x)
opens by itself only after 50 live night exits average ≤ 10bp/side against
the official open, and the pre-registered kill rules (`signals.KILL_*`) switch
a leg off by themselves.

### Accounts

| account | broker | switch (in `.env`, so `make pull` can't undo it) |
|---|---|---|
| paper | Alpaca paper, $3,000 virtual equity | always on |
| live (brokerage) | Schwab margin account | `DAILY_LIVE=on`, cap `DAILY_LIVE_CAPITAL`, optional `DAILY_LIVE_PROFILE` |
| roth | Schwab Roth IRA, 1.0x overnight max, 3x-ETF intraday path, wash-sale guard vs the brokerage book | `DAILY_ROTH=on` (needs limited margin approved: `ROTH_LIMITED_MARGIN=yes`) |

The books never share a symbol, and each account has a single-writer lock.

### Built but off

| what | switch | evidence |
|---|---|---|
| aggressive profile: 1.3x overnight ungated, 20% name cap, conviction live | `DAILY_LIVE_PROFILE=aggressive` | addendum 22. Turn on only after the fill-cost checkpoint |
| night tilt v2 (adds yesterday's return) | `daily.night_tilt_model: v2` | addendum 23, borderline |
| leap book (SOXL IBS / SOXL ORB) and micro-futures sizing | `leap.enabled`, shadow only, no order path | addenda 24-25: nothing 5x's quickly; MNQ needs ~$30k per contract |

## Everyday commands

```bash
make daily-status                  # every account: equity, positions, legs, profile, overnight size, slippage
make review SINCE=2026-09-22 ARGS=--no-replay   # live fills vs the auction price, kill-rule progress
make review SINCE=2026-09-22       # the same plus the (slow) signal replay, weekly
make daily-logs                    # tail today's log
make schwab-login                  # EVERY 7 DAYS, on the server only
make pending                       # what NEXT.md says is waiting
make support                       # paste-safe debug bundle
```

Switches: `make daily-live-check|on|off`, `make daily-roth-check|on|off`.
`make help` lists everything.

## Setup

```bash
make setup      # venv + dependencies
make env        # .env from .env.example, then fill it in
make doctor     # where .env is, what is set, what is missing
make test       # no network
make persist    # install the timers (systemd user timer, or cron)
make persist-status
```

Server deployment: **DEPLOY.md**. Real money and the 7-day login: **SCHWAB.md**.
Updating a clone: `make pull` (it survives a force-push; plain `git pull` does not).

Alerts go by email ([Resend](https://resend.com)) on every order, fill,
warning, failed run, and Schwab login expiry. Quiet runs send nothing.

## Layout

```
swingtrader/daily/    the daily book: signals, executor, book state, broker adapters (Alpaca, Schwab)
swingtrader/leap/     leap book signals + futures sizing (shadow, off)
swingtrader/live/     shared lock, notifier, and the original swing executor
scripts/              daily.py (entrypoint), review.py, schwab_login.py, doctor.py, ...
research/sim/         the simulators behind every addendum
deploy/               systemd units (daily-trader, schwab-reminder, swing-trader)
config.yaml           parameters (reset by make pull)   .env  secrets + switches (survives it)
```

## Research standards

Every change to what trades goes through the same bar: realistic tiered costs,
no lookahead (signals at 15:50 with data available then), positive in both
halves (fit 2021-23, judge 2024-26, and the reverse), day-clustered t-stats,
shuffle/placebo controls, and a shadow period before real orders. Most ideas
fail; `NEXT.md` keeps the list so nobody retests them.

---

## Origin: the swing study (Phase 1)

The repo began as a test of whether a range-bound mean-reversion swing
strategy generalises beyond one stock. It passed a walk-forward gate, then
turned out to be about SPY at its live cadence (addendum 14), so it is
quarantined. The method carried over to everything after it.

### The question

The strategy came from trading RGTI: dips into $14–15 bounced to $16–17+. On real
bars that pattern is genuine — 9 of 10 de-clustered dips into that band tagged $16
within 15 trading days. Three problems make that insufficient evidence:

1. **n = 10.** Cannot distinguish an edge from a stock that chopped sideways for
   eight months.
2. **The band is not structural support.** RGTI was $0.83 in Sep 2024 and $56 in
   Oct 2025. $14–15 is just where it has been ranging lately.
3. **The payoff is short-volatility.** Nine wins averaged ~+11%; the one failure
   drew down −23.6%, and RGTI fell −64% peak-to-trough in Nov 2025. Win rate is
   the most flattering and least informative statistic such a strategy produces.

So this repo is built to be able to answer "no".

### Design

#### Walk-forward (the part that matters)

Stocks are selected on a **formation window** and traded only in a **disjoint,
strictly later trading window**:

```
fold k:   [ formation 126d ][ trade 42d ]
fold k+1:          [ formation 126d ][ trade 42d ]
```

Selecting stocks over the same window you then trade means picking them *because*
they ranged — guaranteed to produce a beautiful, fictional equity curve.

#### Selection metrics (formation window only)

| metric | meaning | gate |
|---|---|---|
| OU half-life | how fast it reverts — the "not for too long" filter | 3–15 days |
| Hurst | < 0.5 = anti-persistent (mean reverting) | ≤ 0.5 |
| drift t-stat | net direction, **Newey-West corrected** | \|t\| ≤ 2.5 |
| amplitude | 2σ/price = gross size of the round trip | ≥ 6% |
| efficiency ratio | \|net move\| / path length; low = chops | ≤ 0.25 |

The HAC correction is not cosmetic. Mean-reverting series are autocorrelated by
construction, and plain OLS returns \|t\| up to 5.9 on synthetic series whose true
slope is zero — a plain-OLS screen rejects exactly the stocks it should select.

#### Strategy

Entry when the 20-day z-score `< −2`, exit on reversion to `z ≥ 0`, 20-day time
stop. Stop-loss is a **tested grid** (none / −10% / −15%), not an assumption: the
original method has no stop, and whether patience or cutting wins is empirical.

#### Three things that would otherwise fake the result

- **Survivorship.** The universe unions Alpaca's ACTIVE *and* INACTIVE assets.
  Delisted names are ~14% of it, and they are disproportionately the dips that
  never bounced — exactly this strategy's worst trades.
- **Split adjustment.** Alpaca defaults to raw bars. NVDA's 10:1 split shows as
  **−89.9%** raw vs **+0.9%** adjusted; a dip-buyer on raw data buys phantom
  crashes. Everything uses `adjustment="all"`, and `fetch_bars` refuses `"raw"`.
- **Trading calendar.** Sessions come from Alpaca's calendar endpoint, not
  `weekday() < 5`, which silently counts market holidays as trading days.

### Controls

The headline return is the least informative output. What decides the question:

1. **Buy-and-hold the same candidates** — if holding beats trading them, the
   "edge" is just exposure to volatile stocks in a rising market.
2. **SPY buy-and-hold.**
3. **Candidate correlation** — eight range-bound speculatives is one bet wearing
   eight tickers; the compounding premise assumes independence.
4. **Falsification runs** — flipped and randomised signals must *lose*. If a
   control profits, the simulator is flattering itself and nothing else is valid.
5. **Bootstrap** (iid / block / stationary) → `P(mean trade ≤ 0)`, plus cost
   shocks at +0/2/4/6/10 bps and `months_to_significance()`.

### Swing research usage

```bash
python scripts/fetch_universe.py          # one-time bulk cache (~6 min)
python scripts/scan.py --cohort highvol   # what looks tradable now
python scripts/backtest.py                # full matrix -> out/
python scripts/backtest.py --quick        # long-only, no stop, no controls
```

Config lives in `config.yaml`; unknown keys warn rather than being silently
dropped, so a typo'd parameter can't look like a swept one.

### Decision gate it passed

Out-of-sample, the strategy must show: positive expectancy after slippage and
still positive at +4bps; Sharpe meaningfully above the buy-and-hold-candidates
control; bootstrapped `P(mean trade ≤ 0) < 5%`; flipped/random controls clearly
losing; survivable drawdown; and results that hold in the high-vol cohort without
collapsing entirely in the broad one.

**What this cannot tell us:** 2021–2026 is one regime, containing a small-cap
speculative boom unusually kind to dip-buying. A clean pass is evidence the edge
existed recently, not proof it persists.
