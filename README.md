# swing-trader

Tests whether a range-bound mean-reversion swing strategy — buy the dip near the
bottom of a range, sell the bounce back to the mean — generalises beyond a single
stock, and whether running it across many names at once actually compounds.

**Status: Phase 2 — running autonomously on an Alpaca PAPER account.**
Phase 1 (research) cleared the decision gate; see `RESULTS.md`.

## The question

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

## Design

### Walk-forward (the part that matters)

Stocks are selected on a **formation window** and traded only in a **disjoint,
strictly later trading window**:

```
fold k:   [ formation 126d ][ trade 42d ]
fold k+1:          [ formation 126d ][ trade 42d ]
```

Selecting stocks over the same window you then trade means picking them *because*
they ranged — guaranteed to produce a beautiful, fictional equity curve.

### Selection metrics (formation window only)

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

### Strategy

Entry when the 20-day z-score `< −2`, exit on reversion to `z ≥ 0`, 20-day time
stop. Stop-loss is a **tested grid** (none / −10% / −15%), not an assumption: the
original method has no stop, and whether patience or cutting wins is empirical.

### Three things that would otherwise fake the result

- **Survivorship.** The universe unions Alpaca's ACTIVE *and* INACTIVE assets.
  Delisted names are ~14% of it, and they are disproportionately the dips that
  never bounced — exactly this strategy's worst trades.
- **Split adjustment.** Alpaca defaults to raw bars. NVDA's 10:1 split shows as
  **−89.9%** raw vs **+0.9%** adjusted; a dip-buyer on raw data buys phantom
  crashes. Everything uses `adjustment="all"`, and `fetch_bars` refuses `"raw"`.
- **Trading calendar.** Sessions come from Alpaca's calendar endpoint, not
  `weekday() < 5`, which silently counts market holidays as trading days.

## Controls

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

## Quick start

```bash
make setup                 # venv + deps
make doctor                # where .env is, what is set, what is missing
make notify-setup EMAIL=you@example.com KEY=re_xxx
make test                  # 36 tests
make kill-old              # stop any previous llm-trader (dry run)
make persist               # schedule it
make results               # positions, P&L, measured slippage
```

Updating an existing clone after a force-push: `make pull` (plain `git pull`
reports "divergent branches" and stops — the old commits are gone, so there is
nothing to merge).

Replacing an existing `llm-trader` deployment on a server? See **DEPLOY.md**.

## Alerts

Email via [Resend](https://resend.com) on every order, fill, or warning —
including positions, P&L, measured slippage against the 20bps the backtest
assumed, and the run log. Quiet runs send nothing; with ~40 trades a year most
days are quiet. `make notify-test` proves the key works, `make digest` forces a
report on demand.

## Live paper loop

```bash
python scripts/live.py --dry-run   # decide and log, submit nothing
python scripts/live.py             # live (paper) orders
python scripts/live.py --status    # books, positions, measured slippage
crontab -l                         # the schedule;  crontab -r  removes it
```

Two books run side by side:

| book | mode | why |
|---|---|---|
| **reversion** | **LIVE** — places paper orders | Survived the falsification controls, parameter sweeps and three rounds of bug fixes |
| **momentum** | SHADOW — logs only | Its parameters were chosen after seeing results; it earns out-of-sample evidence before it earns order flow |

Schedule (machine is Pacific; ET = local + 3h year-round):

| local | ET | what it does |
|---|---|---|
| 06:05 | 09:05 | decide on yesterday's close, submit market-on-open (Alpaca OPG cutoff is 09:28 ET) |
| 06:47 | 09:47 | reconcile fills, arm GTC stops, **measure slippage** |
| 12:52 | 15:52 | pre-close sweep — nothing unprotected overnight |

Timing mirrors the backtest exactly: decide on the last complete daily bar,
execute at the next open.

**The number this exists to produce** is measured fill slippage in bps against
the 20bps per side the backtest assumed. `--status` prints it once fills land.
If it comes in materially worse, the backtest edge shrinks and that is the
finding — the whole point of running live is that no further backtesting can
answer it.

### Safety properties

- **Idempotent orders.** Deterministic `client_order_id` per (book, symbol, day,
  kind); re-running a decision cannot double-fill. Verified against the live API.
- **Pending ≠ position.** A submitted-but-unfilled OPG order is tracked
  separately. Treating it as a lost position would re-submit under the next
  day's id and open the position twice.
- **Never unprotected overnight.** Every position carries a working GTC stop,
  re-armed on every run; failures log loudly.
- **Single writer.** `AccountLock` (flock) prevents two runs trading one
  account — ported from llm-trader, which learned it by leaving a position
  unprotected overnight.
- **Paper-key assertion.** The broker refuses to start on a key that is not `PK…`.

## Usage

```bash
python scripts/fetch_universe.py          # one-time bulk cache (~6 min)
python scripts/scan.py --cohort highvol   # what looks tradable now
python scripts/backtest.py                # full matrix -> out/
python scripts/backtest.py --quick        # long-only, no stop, no controls
pytest tests/ -q
```

Config lives in `config.yaml`; unknown keys warn rather than being silently
dropped, so a typo'd parameter can't look like a swept one.

## Decision gate for Phase 2 (live paper trading)

Out-of-sample, the strategy must show: positive expectancy after slippage and
still positive at +4bps; Sharpe meaningfully above the buy-and-hold-candidates
control; bootstrapped `P(mean trade ≤ 0) < 5%`; flipped/random controls clearly
losing; survivable drawdown; and results that hold in the high-vol cohort without
collapsing entirely in the broad one.

**What this cannot tell us:** 2021–2026 is one regime, containing a small-cap
speculative boom unusually kind to dip-buying. A clean pass is evidence the edge
existed recently, not proof it persists.
