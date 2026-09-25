# Deploying on the SSH box

**Already deployed?** The routine is at the bottom: "Routine operation".

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
make test      # none touch the network
make daily-dry # the daily book's current phase, submits nothing
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

`make persist` picks whatever the box actually supports and says which it used.
It installs `daily-trader.timer` and `schwab-reminder.timer`. The swing book's
`swing-trader.timer` is installed only when `.env` has `SWING_BOOK=on`
(quarantined since addendum 14).

### "Failed to connect to bus: No medium found"

This is the normal result of reaching the account with `su - ihearthim` from
root: you get a shell, but no D-Bus session and no `XDG_RUNTIME_DIR`, so
`systemctl --user` has nothing to talk to. It is not a permissions problem and
nothing is broken.

`make persist` detects it and **falls back to cron automatically** — cron needs
no session, survives logout, and is entirely adequate here. If that is what you
see, you are done.

To use systemd instead (slightly cleaner: timezone lives in the unit, and it
catches up a missed run after a reboot), as **root**:

```bash
loginctl enable-linger ihearthim
```

then reconnect as the user directly rather than via `su`:

```bash
ssh ihearthim@<host>
cd ~/llm-trader && make persist
```

Lingering is what keeps a user timer alive after you disconnect. **Without it
the timer looks perfectly installed and simply never runs** once you close the
SSH session — the single most likely way this ends up quietly dead.

`make persist-status` reports lingering on its own line, and `make linger`
prints the exact command.

### Timezones

The systemd unit declares `America/New_York`, so the host's timezone is
irrelevant. The cron fallback sets `CRON_TZ=America/New_York`, which
Debian/Ubuntu cron and cronie honour. Every run stamps ET in the log, so after
the first fire confirm it landed when you expected:

```bash
make persist-status   # shows both clocks side by side
make logs
```

### How long a run takes

| daily-book run (ET) | what it does | time |
|---|---|---|
| 09:15 | sell the night leg at the open, rebalance IBS, build the night universe | ~30-60 s |
| 09:50, 16:10 | reconcile fills | ~10 s |
| 10:01-15:31, every 30 min | intraday decision | ~10 s |
| 15:40 | scan for night picks, buy at the close auction (cutoff 15:50) | ~30-60 s |
| 15:57 | flatten the intraday leg | ~10 s |

`make persist` only installs the timer; it runs no cycle. `make daily-dry`
runs the current phase and submits nothing.

## 5. Watch it

```bash
make daily-status   # every account: equity, positions, legs, profile, overnight size, slippage
make daily-logs     # live tail
journalctl --user -u daily-trader -n 100 --no-pager    # Linux
```

Email lands on every order, fill, warning and failed run. Quiet runs send nothing.

## The daily book

`scripts/daily.py`, its own timer (`daily-trader.timer`), one state file per
account (`state/book-daily*.json`). Paper runs on Alpaca with a $3,000 virtual
equity that changes only through its own fills; real money runs on Schwab and
sizes from the real balance, capped by `DAILY_LIVE_CAPITAL`. Research:
RESULTS.md addendum 6 onward. What each leg does: README.md.

The books never share a symbol: positions net per symbol at the broker, so a
shared name would corrupt both ledgers. Each book skips anything held at the
broker by someone else, and the brokerage and Roth books keep a 30-day
wash-sale gap between them. Daily positions carry no stop by design.

Real money: **SCHWAB.md** (`make daily-live-check`, then `make daily-live-on`).
Every switch lives in `.env` (`DAILY_LIVE`, `DAILY_ROTH`, `DAILY_LIVE_CAPITAL`,
`DAILY_LIVE_PROFILE`), so `make pull` cannot undo it. Each run reads `.env`
fresh: no restart needed after editing it.

## Routine operation

| when | do |
|---|---|
| every 7 days | `make schwab-login`, **on the server** (a login anywhere else revokes the server's) |
| weekly | `make review SINCE=2026-09-22 ARGS=--no-replay`: open-sell cost vs the auction, exits so far, kill-rule progress. Drop `ARGS` for the slow signal replay |
| weekly | `make daily-status`: no `KILLED` lines, intraday fills clean |
| after any `git push` | `make pull` here |
| decisions | `make pending` (NEXT.md) |
| once | `HEALTHCHECK_URL` in `.env` (see `.env.example`) and `make notify-test`: the 16:10 watchdog and the dead-man ping only help if alerts arrive |

## Stopping it

```bash
make stop        # aliases: make persist-stop, make unpersist
```

Removes the systemd timers and any cron entries. Open positions stay open at
the broker: the daily book's night and IBS positions have no stops, so close
them yourself if you stop it for long.
