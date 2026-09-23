# swing-trader — mean-reversion swing strategy on Alpaca paper.
#   make help        what everything does
#   make kill-old    stop the previous llm-trader deployment
#   make persist     install + start the scheduled loop (systemd or cron)
#   make results     positions, P&L, measured slippage, recent activity
SHELL := /bin/bash
PY    := ./.venv/bin/python
PIP   := ./.venv/bin/pip
APP   := $(shell pwd)
USER_ := $(shell whoami)
UNAME := $(shell uname -s)
.DEFAULT_GOAL := help

.PHONY: help setup env test lint kill-old persist unpersist persist-status \
        daily-status daily-dry daily-once daily-logs daily-live-check daily-live-on daily-live-off schwab-login \
        results status positions slippage logs once dry digest notify-test \
        notify-setup doctor pull scan backtest clean stop persist-stop linger _lastlog pending

help:
	@echo "swing-trader"
	@echo ""
	@echo "  doctor         where is .env, what is set, what is missing"
	@echo "  pull           update from GitHub (survives a force-push)"
	@echo "  setup          create venv and install dependencies"
	@echo "  env            create .env from the example (then edit it)"
	@echo "  test           run the test suite"
	@echo ""
	@echo "  kill-old       STOP the previous llm-trader (dry run; add YES=1 to apply)"
	@echo "  persist        install + start the scheduled loop (systemd timer, or cron)"
	@echo "  stop           stop and remove the schedule (alias: unpersist)"
	@echo "  linger         how to make a systemd timer survive logout"
	@echo "  persist-status is it actually scheduled and running?"
	@echo ""
	@echo "  results        positions, P&L, measured slippage, recent activity"
	@echo "  pending        decisions waiting on something (from NEXT.md)"
	@echo "  positions      open positions straight from Alpaca"
	@echo "  slippage       measured fill cost vs the 20bps the backtest assumed"
	@echo "  logs           tail the run log"
	@echo ""
	@echo "  once           run one cycle now (live paper orders)"
	@echo "  dry            run one cycle now, submit nothing"
	@echo "  digest         email a status report right now"
	@echo "  notify-test    prove the Resend key works"
	@echo "  notify-setup   add email settings to .env (EMAIL=... KEY=... [FROM=...])"
	@echo ""
	@echo "  daily-status   daily book: equity, positions, legs, slippage"
	@echo "  daily-dry      run the daily book's current phase, submit nothing"
	@echo "  daily-once     run the daily book's current phase now (paper orders)"
	@echo "  daily-logs     tail the daily book log"
	@echo "  schwab-login      create/renew the Schwab API login (every 7 days!)"
	@echo "  daily-live-check  connect to the REAL-money account, change nothing"
	@echo "  daily-live-on     start trading real money too (asks you to type REAL MONEY)"
	@echo "  daily-live-off    stop trading real money (paper keeps running)"
	@echo ""
	@echo "  scan           what looks tradable today"
	@echo "  backtest       full walk-forward (slow; writes out/)"

# ---------------------------------------------------------------- setup
doctor:
	@$(PY) scripts/doctor.py 2>/dev/null || python3 scripts/doctor.py

# `git pull` cannot reconcile after a force-push -- the old commits are simply
# gone, so there is nothing to merge and git stops with "divergent branches".
# Discard local history and take the remote exactly. .env, state/ and logs/ are
# gitignored, so credentials and books survive this.
pull:
	@git fetch origin
	@git reset --hard origin/main
	@echo ""
	@git log --oneline -1
	@echo "(.env, state/ and logs/ are gitignored and were not touched)"

setup:
	@test -d .venv || python3 -m venv .venv
	@$(PIP) install -q --upgrade pip
	@$(PIP) install -q -r requirements.txt
	@echo "venv ready: $$($(PY) --version)"

env:
	@test -f .env && echo ".env already exists - not overwriting" || \
	  { cp .env.example .env; echo "created .env - now fill in ALPACA_* and RESEND_API_KEY"; }

test:
	@PYTHONPATH=. $(PY) -m pytest tests/ -q

lint:
	@$(PY) -m ruff check swingtrader scripts 2>/dev/null || echo "(ruff not installed)"

# ------------------------------------------------------- stop the old one
kill-old:
ifeq ($(YES),1)
	@./scripts/kill-old-trader.sh --yes
else
	@./scripts/kill-old-trader.sh
	@echo ""
	@echo "This was a DRY RUN. To actually stop it:  make kill-old YES=1"
endif

# ----------------------------------------------------------- persistence
persist:
	@./scripts/install-schedule.sh

linger:
	@echo "A systemd USER timer stops when you log out unless lingering is on."
	@echo "It needs root, so run this yourself:"
	@echo ""
	@echo "    sudo loginctl enable-linger $$(whoami)"
	@echo ""
	@echo "or, if this shell came from 'su -' and has no sudo, exit to root and run:"
	@echo ""
	@echo "    loginctl enable-linger $$(whoami)"
	@echo ""
	@echo "Then confirm with:  make persist-status"

stop persist-stop: unpersist

unpersist:
	@-./scripts/sysd.sh disable --now swing-trader.timer 2>/dev/null
	@-./scripts/sysd.sh disable --now daily-trader.timer 2>/dev/null
	@-rm -f $(HOME)/.config/systemd/user/swing-trader.service \
	        $(HOME)/.config/systemd/user/swing-trader.timer \
	        $(HOME)/.config/systemd/user/daily-trader.service \
	        $(HOME)/.config/systemd/user/daily-trader.timer
	@-./scripts/sysd.sh daemon-reload 2>/dev/null
	@-crontab -l 2>/dev/null | grep -v 'run-live.sh' | grep -v 'run-daily.sh' \
	  | grep -vE '^CRON_TZ=America/New_York|^# swing-trader|^# *[0-9]{2}:[0-9]{2} PT' \
	  | crontab - 2>/dev/null
	@echo "schedule removed (systemd timer and cron entries)."

persist-status:
	@echo "--- systemd user timer ---"
	@./scripts/sysd.sh list-timers swing-trader.timer daily-trader.timer --no-pager 2>/dev/null \
	  | grep -E "swing-trader|daily-trader|NEXT" || echo "  not installed"
	@printf "  lingering: "; \
	  if loginctl show-user $$(whoami) -p Linger 2>/dev/null | grep -q "Linger=yes"; \
	  then echo "ON (survives logout)"; \
	  else echo "OFF  <-- timer dies at logout. run: make linger"; fi
	@R=$$(./scripts/sysd.sh show swing-trader.service -p Result --value 2>/dev/null); \
	  W=$$(./scripts/sysd.sh show swing-trader.service -p ExecMainExitTimestamp --value 2>/dev/null); \
	  if [ -n "$$R" ] && [ "$$R" != "success" ]; then \
	    echo "  last timer run: $$R at $${W:-?}  <-- FAILED (stale if before your last fix)"; \
	  elif [ -n "$$R" ]; then echo "  last timer run: success at $${W:-?}"; fi
	@R=$$(./scripts/sysd.sh show daily-trader.service -p Result --value 2>/dev/null); \
	  W=$$(./scripts/sysd.sh show daily-trader.service -p ExecMainExitTimestamp --value 2>/dev/null); \
	  if [ -z "$$W" ] || [ "$$W" = "n/a" ]; then \
	    [ -n "$$R" ] && echo "  daily book last run: not run by the timer yet"; \
	  elif [ "$$R" != "success" ]; then \
	    echo "  daily book last run: $$R at $$W  <-- FAILED"; \
	  else echo "  daily book last run: success at $$W"; fi
	@echo "--- cron ---"
	@crontab -l 2>/dev/null | grep -A12 'swing-trader' || echo "  no cron entries"
	@echo "--- clocks ---"
	@echo "  server $$(date '+%H:%M %Z')   US/Eastern $$(TZ=America/New_York date '+%H:%M %Z')"
	@echo "--- last run (log file: includes manual/dry runs) ---"
	@$(MAKE) --no-print-directory _lastlog N=6

# --------------------------------------------------------------- results
results: status daily-status slippage pending
	@echo ""
	@echo "=== recent activity ==="
	@$(MAKE) --no-print-directory _lastlog N=30

pending:
	@if [ -f NEXT.md ]; then \
	  echo ""; echo "=== pending (NEXT.md) ==="; \
	  awk '/^## [0-9]/{f=1} /^---$$/{f=0} f' NEXT.md | grep -E '^## |^\*\*Status|^\*\*Trigger' \
	    | sed 's/\*\*//g;s/^/  /'; \
	fi

status:
	@$(PY) scripts/live.py --status

positions:
	@$(PY) -c "from swingtrader.live.broker import PaperBroker; from swingtrader.daily.book import owned_by_daily; \
	  from swingtrader.config import ROOT; d=owned_by_daily(ROOT/'state'); b=PaperBroker(); \
	  p=b.positions(); s=b.stops_by_symbol(); \
	  print(f'{len(p)} open position(s)'); \
	  [print(f\"  {k:6} {float(v.qty):7.0f} sh @ {float(v.avg_entry_price):8.2f}  \
P&L {float(v.unrealized_pl):+9.2f} ({float(v.unrealized_plpc)*100:+5.1f}%)  \
stop {'daily book (no stop by design)' if k in d else 'YES' if k in s else 'MISSING'}\") for k,v in p.items()]"

slippage:
	@$(PY) -c "import json,numpy as np,pathlib; \
	  p=pathlib.Path('logs/slippage.jsonl'); \
	  rows=[json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []; \
	  print('no fills recorded yet') if not rows else None; \
	  v=np.array([r['slippage_bps'] for r in rows]) if rows else None; \
	  print(f'slippage over {len(v)} fills: mean {v.mean():+.1f} bps  median {np.median(v):+.1f}  p90 {np.percentile(v,90):+.1f}') if rows else None; \
	  print(f'backtest assumed +20.0 bps/side -> ' + ('HOLDING UP' if v.mean()<=25 else 'WORSE THAN MODELLED, edge shrinks')) if rows else None"

# `tail` with no filename argument reads STDIN and blocks forever, which is
# how `make persist-status` appeared to hang. Every log target goes through
# here so the empty case is handled once.
_lastlog:
	@N=$${N:-20}; \
	 LOG=$$(ls -t logs/live-*.log 2>/dev/null | head -1); \
	 if [ -n "$$LOG" ] && [ -f "$$LOG" ]; then tail -n $$N "$$LOG"; \
	 elif [ -f logs/cron.log ]; then tail -n $$N logs/cron.log; \
	 elif ./scripts/sysd.sh list-units swing-trader.service >/dev/null 2>&1; then \
	   journalctl --user -u swing-trader -n $$N --no-pager 2>/dev/null \
	     || echo "  (no runs yet)"; \
	 else echo "  (no runs yet)"; fi

logs:
	@LOG=$$(ls -t logs/live-*.log 2>/dev/null | head -1); \
	 if [ -n "$$LOG" ] && [ -f "$$LOG" ]; then echo "tailing $$LOG (ctrl-c to stop)"; tail -f "$$LOG"; \
	 elif ./scripts/sysd.sh list-units swing-trader.service >/dev/null 2>&1; then \
	   echo "no log file yet - following journald (ctrl-c to stop)"; \
	   journalctl --user -u swing-trader -f; \
	 else echo "no runs yet. after the first fire, this follows logs/live-<date>.log"; fi

# ------------------------------------------------------------ daily book
daily-status:
	@$(PY) scripts/daily.py --status

daily-dry:
	@$(PY) scripts/daily.py --dry-run

daily-once:
	@$(PY) scripts/daily.py

schwab-login:
	@$(PY) scripts/schwab_login.py

daily-live-check:
	@$(PY) scripts/daily_switch.py check

daily-live-on:
	@$(PY) scripts/daily_switch.py on

daily-live-off:
	@$(PY) scripts/daily_switch.py off

daily-logs:
	@LOG=$$(ls -t logs/daily-2*.log 2>/dev/null | head -1); \
	 if [ -n "$$LOG" ] && [ -f "$$LOG" ]; then echo "tailing $$LOG (ctrl-c to stop)"; tail -f "$$LOG"; \
	 elif ./scripts/sysd.sh list-units daily-trader.service >/dev/null 2>&1; then \
	   journalctl --user -u daily-trader -f; \
	 else echo "no daily-book runs yet"; fi

# ----------------------------------------------------------------- runs
once:
	@$(PY) scripts/live.py

dry:
	@$(PY) scripts/live.py --dry-run

digest:
	@$(PY) scripts/live.py --digest

notify-test:
	@$(PY) -c "from pathlib import Path; from swingtrader.live.notify import Notifier; \
	  n=Notifier(Path('state')); \
	  print('enabled:',n.enabled,'|',n.reason or 'ready'); \
	  print(n.send('[swing-trader] notification test', \
	    '<p>If you are reading this, alerts work.</p>', dedupe_key=None))"

notify-setup:
ifndef EMAIL
	@echo "usage: make notify-setup EMAIL=you@example.com KEY=re_xxx [FROM=alerts@yourdomain.com]"
	@echo ""
	@echo "FROM must be a Resend-VERIFIED domain. The default shared sender"
	@echo "(onboarding@resend.dev) only delivers to the address that owns the"
	@echo "Resend account, so a different destination needs your own domain."
	@exit 1
endif
	@touch .env
	@sed -i.bak -E '/^(RESEND_API_KEY|NOTIFY_EMAIL|NOTIFY_FROM)=/d' .env && rm -f .env.bak
	@echo "RESEND_API_KEY=$(KEY)" >> .env
	@echo "NOTIFY_EMAIL=$(EMAIL)" >> .env
	@echo "NOTIFY_FROM=$(if $(FROM),$(FROM),onboarding@resend.dev)" >> .env
	@chmod 600 .env
	@echo "wrote email settings to .env (chmod 600)"
	@$(MAKE) --no-print-directory notify-test

scan:
	@$(PY) scripts/scan.py --cohort highvol --top 15

backtest:
	@$(PY) scripts/backtest.py --quick --cohorts highvol

clean:
	@rm -rf __pycache__ */__pycache__ .pytest_cache
	@echo "cleaned (cache, state and logs left alone)"
