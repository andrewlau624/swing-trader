# Deploying on the SSH box

This replaces the old `llm-trader` deployment in the same repo. Do it in this
order — stop the old trader *before* starting the new one, so two processes are
never touching the same Alpaca account.

## 1. Pull the new code

```bash
cd ~/swing-trader        # wherever the old clone lives
git fetch origin
git reset --hard origin/main
```

Your `.env` is gitignored, so **Alpaca keys survive this**. That was the point.

## 2. Stop the old trader

```bash
./scripts/kill-old-trader.sh          # dry run — shows what it found
./scripts/kill-old-trader.sh --yes    # actually stop it
```

It handles every way the old loop could be running: a systemd system unit, a
systemd *user* unit, the `supervise.sh` restart loop, a bare `nohup`'d
`live.py`, cron entries, and launchd jobs. It verifies nothing survives and
exits non-zero if something does.

It does **not** touch open Alpaca positions. Check those yourself:

```bash
make positions
```

If the old strategy left positions open, close them in the Alpaca dashboard
before starting the new loop — otherwise the new book will adopt them and
manage them under *its* rules, which is probably not what you want.

## 3. Set up

```bash
make setup                 # venv + dependencies
make env                   # only if .env is missing
$EDITOR .env               # add RESEND_API_KEY, NOTIFY_EMAIL, NOTIFY_FROM
make test                  # 36 tests, none touch the network
make dry                   # one full cycle, submits nothing
```

## 4. Start it

```bash
make persist        # systemd user timer on Linux, cron on macOS
make persist-status # confirm it is actually scheduled
```

On Linux this installs a `swing-trader.timer` firing at 09:05, 09:47 and
15:52 **America/New_York**, declared in the unit, so the host's timezone does
not matter. `loginctl enable-linger` is set so it keeps running after you log
out of SSH — without that, systemd user units stop when your session ends,
which is the usual reason a "running" bot quietly isn't.

## 5. Watch it

```bash
make results     # positions, P&L, measured slippage, recent activity
make slippage    # the number that decides whether the backtest was honest
make logs        # live tail
journalctl --user -u swing-trader -n 100 --no-pager    # Linux
```

Email lands automatically whenever an order is placed, a fill happens, or
anything warns. Quiet runs send nothing — with ~40 trades a year and 1.29 mean
concurrent positions, most days are quiet, and that is normal rather than a
malfunction.

## Stopping it

```bash
make unpersist   # remove the schedule
```

Open positions keep their GTC stops at the broker and are unaffected.
