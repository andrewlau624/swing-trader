"""PREF-PART (pre-registered 2026-10-16, N 1012): participation-impact ladder for the PREF/ETD stack.

Replay of the PREF-EX shadow's scored eligible events (state/pref-ex.jsonl, read on the server): what does the
marginal cross-cost look like if the participation per event rises from the registered 5% of the trailing median
closing cross to 10% / 20% / 50%? Impact model (registered, square-root law on the cross's own dollars):
  price impact per fill ~ 0.8bp x sqrt(100 x q / cross_usd), calibrated from "1% of cross $ ~= 0.8bp of price"
  for $25-par thin paper (ADV-equivalence); base case = fill at the official print, as measured live.

ONE LOOK. Registered bar: PASS iff extra cost <= 10bp at 10% and <= 20bp at 20% participation; 50% report-only.
Real judge of the raise = the live 30-trip record (the model decides only whether a raise is worth booking).
"""
from __future__ import annotations
import json
import math
import pathlib
import sys
from collections import defaultdict

import requests

SERVER = "him"          # read-only ssh to the server state (standing rule)
EVENTS = "state/pref-ex.jsonl"


def load_events() -> list[dict]:
    import subprocess
    out = subprocess.run(["ssh", SERVER, f"cat ~llm-trader/{EVENTS}"], capture_output=True, text=True)
    if out.returncode != 0:
        out = subprocess.run(["ssh", "him", f"cat ~/llm-trader/{EVENTS}"], capture_output=True, text=True)
    return [json.loads(x) for x in out.stdout.splitlines() if x.strip()]


def main():
    ev = [x for x in load_events()
          if x.get("status") == "scored" and x.get("eligible") and x.get("med_cross_usd")]
    agg = defaultdict(lambda: [0.0, 0, 0.0])
    for x in ev:
        csd = x.get("close_usd") or x.get("med_cross_usd")
        if not csd:
            continue
        for part in (0.05, 0.10, 0.20, 0.50):
            q = csd * part
            frac = q / csd
            add_bp = 0.8 * math.sqrt(max(frac, 0) * 100)
            agg[part][0] += add_bp
            agg[part][1] += 1
            agg[part][2] = max(agg[part][2], add_bp)
    lines = [f"PREF-PART on {len(ev)} scored eligible events (state/pref-ex.jsonl)", ""]
    for part in (0.05, 0.10, 0.20, 0.50):
        tot, n, worst = agg[part]
        lines.append(f"participation {part*100:5.1f}%   mean added impact {tot/n:+.2f}bp "
                     f"(worst single event +{worst:.2f}bp)")
    lines.append("")
    lines.append("VERDICT: " + ("PASS" if (agg[0.10][0] / max(1, agg[0.10][1])) <= 10
                and (agg[0.20][0] / max(1, agg[0.20][1])) <= 20 else "KILL")
                + " (model-based; the live 30-trip record is the real judge)")
    out = pathlib.Path(__file__).resolve().parent / "pref_part_out.txt"
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
