# Deploying on the SSH box

This replaces the old `llm-trader` deployment in the same repo. Do it in this
order — stop the old trader *before* starting the new one, so two processes are
never touching the same Alpaca account.

## 1. Pull the new code

```bash
cd ~/llm-trader      # the clone directory; its name does not matter
make pull            # or, before this Makefile exists:
                     #   git fetch origin && git reset --hard origin/main
```

**`git pull` will not work here**, and the error is expected:

```
hint: You have divergent branches and need to specify how to reconcile them.
fatal: Need to specify how to reconcile divergent branches.
```

main was force-pushed, so the old llm-trader commits no longer exist upstream.
There is nothing to merge — `reset --hard` is the correct move, not a
workaround. `make pull` does exactly that.

If the remote still points at the old repo name, that is fine: GitHub redirects
`andrewlau624/llm-trader` to `andrewlau624/swing-trader`, which is why the fetch
worked. To stop relying on the redirect:

```bash
git remote set-url origin https://github.com/andrewlau624/swing-trader.git
```

### Where is .env?

In the clone directory, next to the Makefile — `~/llm-trader/.env`. It is
gitignored, so **`git reset --hard` does not touch it** and your Alpaca keys
survive. To confirm what is set, masked:

```bash
make doctor
```

That prints the absolute path, which variables are present, whether Alpaca
answers, whether email is configured, and whether anything is scheduled.

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
make setup     # venv + dependencies
make doctor    # where .env is, what is set, what is missing
make test      # 36 tests, none touch the network
make dry       # one full cycle, submits nothing
```

Add email alerts (appends to `.env`, then sends a test):

```bash
make notify-setup EMAIL=andrew.lau@berkeley.edu KEY=re_xxxxxxxx
```

**The sender matters.** `onboarding@resend.dev` is Resend's shared test address
and only delivers to the mailbox that owns the Resend account. If alerts must
reach a *different* address than the one you signed up with, verify a domain in
Resend and pass it:

```bash
make notify-setup EMAIL=andrew.lau@berkeley.edu KEY=re_xxx FROM=alerts@yourdomain.com
```

`make notify-test` reports Resend's actual error if delivery is refused, so you
will not be left guessing.

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

### How long a run takes

| run | market | what it does | time |
|---|---|---|---|
| 09:05 ET | closed | refreshes ~14,760 symbols, decides, submits | **1–3 min** |
| 09:47 ET | open | reconciles fills, arms stops, measures slippage | ~10 s |
| 15:52 ET | open | pre-close sweep | ~10 s |

Only the decision run pays for the data refresh, and it prints progress with an
ETA. If `make dry` looks frozen on `refreshing recent bars...`, it is working —
give it a few minutes, or watch the percentage tick up.

**You do not need to wait for it.** `make persist` only installs the timer; it
runs no cycle. Ctrl+C a long `make dry` and run `make persist` straight away,
or use a second SSH session.

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
