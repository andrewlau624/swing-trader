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

`make persist` picks whatever the box actually supports and says which it used.

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

## The daily book (added 2026-09-22)

A second, independent book runs on the same paper account: `scripts/daily.py`,
its own timer (`daily-trader.timer`), its own state (`state/book-daily.json`),
and a **$3,000 virtual starting equity** that changes only through its own
fills. See RESULTS.md addendum 6 for the research, and NEXT.md item 4 for the rules.

To install it on a box that already runs the swing timer:

```bash
make pull
make test            # 55 tests, no network
make daily-dry       # runs the current phase, submits nothing, saves nothing
make persist         # re-installs BOTH timers (swing + daily)
make persist-status  # should list swing-trader.timer AND daily-trader.timer
```

Watch it with `make daily-status` (equity, positions per leg, slippage) and
`make daily-logs`. The first real activity is the 15:40 ET run: it buys
at the close auction. The 09:15 run next morning sells those at the open auction.

The two books never share a symbol. Alpaca nets positions per symbol, so a
shared name would corrupt both books' accounting. The daily book skips
anything the swing book holds or has pending. The swing executor ignores
anything listed in the daily book: it won't adopt it, stop it, or trade it.
Daily positions carry no stop by design; `make positions` labels them.

## Stopping it

```bash
make stop        # aliases: make persist-stop, make unpersist
```

Removes both the systemd timer and any cron entries. Open positions keep their
GTC stops at the broker and are unaffected.

Open positions keep their GTC stops at the broker and are unaffected.
