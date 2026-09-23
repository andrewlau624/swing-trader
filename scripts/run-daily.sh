#!/bin/bash
# cron wrapper for the daily book: absolute paths, venv python, append-only log.
cd "$(dirname "$0")/.." || exit 1
mkdir -p logs
exec ./.venv/bin/python scripts/daily.py >> logs/cron-daily.log 2>&1
