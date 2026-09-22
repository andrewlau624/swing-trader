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
        results status positions slippage logs once dry digest notify-test \
        notify-setup doctor pull scan backtest clean

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
	@echo "  unpersist      stop and remove the schedule"
	@echo "  persist-status is it actually scheduled and running?"
	@echo ""
	@echo "  results        positions, P&L, measured slippage, recent activity"
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
ifeq ($(UNAME),Linux)
	@echo "installing systemd user units..."
	@mkdir -p $(HOME)/.config/systemd/user
	@sed -e 's|__USER__|$(USER_)|g' -e 's|__APP_DIR__|$(APP)|g' \
	    deploy/swing-trader.service.in > $(HOME)/.config/systemd/user/swing-trader.service
	@cp deploy/swing-trader.timer.in $(HOME)/.config/systemd/user/swing-trader.timer
	@systemctl --user daemon-reload
	@systemctl --user enable --now swing-trader.timer
	@loginctl enable-linger $(USER_) 2>/dev/null || \
	  echo "  NOTE: could not enable linger; the timer may pause when you log out."
	@echo ""
	@systemctl --user list-timers swing-trader.timer --no-pager || true
	@echo "installed. 'make persist-status' to check, 'make unpersist' to remove."
else
	@echo "installing cron entries (macOS)..."
	@( crontab -l 2>/dev/null | grep -v 'swing-trader/scripts/run-live.sh' ; \
	   echo '# swing-trader — ET = local + 3h (Pacific). 09:05 / 09:47 / 15:52 ET' ; \
	   echo ' 5 6 * * 1-5 $(APP)/scripts/run-live.sh' ; \
	   echo '47 6 * * 1-5 $(APP)/scripts/run-live.sh' ; \
	   echo '52 12 * * 1-5 $(APP)/scripts/run-live.sh' ) | crontab -
	@crontab -l | grep -A3 swing-trader
	@echo "installed. macOS may require Full Disk Access for cron."
endif

unpersist:
ifeq ($(UNAME),Linux)
	@systemctl --user disable --now swing-trader.timer 2>/dev/null || true
	@rm -f $(HOME)/.config/systemd/user/swing-trader.{service,timer}
	@systemctl --user daemon-reload
	@echo "schedule removed."
else
	@crontab -l 2>/dev/null | grep -v 'swing-trader/scripts/run-live.sh' | \
	  grep -v '^# swing-trader' | crontab - || true
	@echo "cron entries removed."
endif

persist-status:
ifeq ($(UNAME),Linux)
	@systemctl --user list-timers swing-trader.timer --no-pager 2>/dev/null || echo "timer not installed"
	@systemctl --user status swing-trader.service --no-pager -n 20 2>/dev/null || true
else
	@crontab -l 2>/dev/null | grep -B1 -A3 swing-trader || echo "no cron entries installed"
	@echo "--- last cron run ---"
	@tail -5 logs/cron.log 2>/dev/null || echo "(no cron log yet)"
endif

# --------------------------------------------------------------- results
results: status slippage
	@echo ""
	@echo "=== recent activity ==="
	@tail -30 $$(ls -t logs/live-*.log 2>/dev/null | head -1) 2>/dev/null || echo "(no runs yet)"

status:
	@$(PY) scripts/live.py --status

positions:
	@$(PY) -c "from swingtrader.live.broker import PaperBroker; b=PaperBroker(); \
	  p=b.positions(); s=b.stops_by_symbol(); \
	  print(f'{len(p)} open position(s)'); \
	  [print(f\"  {k:6} {float(v.qty):7.0f} sh @ {float(v.avg_entry_price):8.2f}  \
P&L {float(v.unrealized_pl):+9.2f} ({float(v.unrealized_plpc)*100:+5.1f}%)  \
stop {'YES' if k in s else 'MISSING'}\") for k,v in p.items()]"

slippage:
	@$(PY) -c "import json,numpy as np,pathlib; \
	  p=pathlib.Path('logs/slippage.jsonl'); \
	  rows=[json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []; \
	  print('no fills recorded yet') if not rows else None; \
	  v=np.array([r['slippage_bps'] for r in rows]) if rows else None; \
	  print(f'slippage over {len(v)} fills: mean {v.mean():+.1f} bps  median {np.median(v):+.1f}  p90 {np.percentile(v,90):+.1f}') if rows else None; \
	  print(f'backtest assumed +20.0 bps/side -> ' + ('HOLDING UP' if v.mean()<=25 else 'WORSE THAN MODELLED, edge shrinks')) if rows else None"

logs:
	@tail -f $$(ls -t logs/live-*.log 2>/dev/null | head -1)

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
