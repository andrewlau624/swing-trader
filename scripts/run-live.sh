#!/bin/bash
# cron wrapper: absolute paths, venv python, append-only logging.
cd /Users/andrewlau/Documents/Code/Projects/swing-trader || exit 1
mkdir -p logs
exec ./.venv/bin/python scripts/live.py >> logs/cron.log 2>&1
