"""NIGHT-CAP sizing grid (2026-10-10, descriptive; sizing decision is the user's). Night leg only, nx live-rule trades
(daily-bar proxy, delisted-complete), whole shares, night weight 0.5, cash only (gross <= 1x). Per-name weight = min(1/n, cap) x crowd x tilt x weekend x 0.5
(signals.night_sizing; cap 0.10 = live; nx x rescaled night by night). Cost 5bp/side and 10bp/side (2x shock).
NX found the daily-bar proxy ~1.7x optimistic vs the exact 15:40 rule: read levels as optimistic, compare caps relative to each other.
  .venv/bin/python research/sim/night_cap.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np, pandas as pd
import top2_size as T

CAPS = (0.10, 0.15, 0.20, 0.30, 0.50, 1.00)
OUT = T.ROOT / "data/research/program/night_cap_grid_out.txt"

def main():
    tr = T.load_trades().sort_values(["date", "day_ret"]).reset_index(drop=True); S = T.sessions(); L = []
    def P(s=""): print(s, flush=True); L.append(s)
    P(__doc__.split("\n  .venv")[0])
    for era, (lo, hi) in T.ERAS.items():
        t = tr[(tr.date >= lo) & (tr.date <= hi)]; nights = S[(S >= lo) & (S <= hi)]
        P(f"\n== {era}: {len(t)} picks, {t.date.nunique()} pick-nights of {len(nights)}")
        P(f"  {'capital':>8} {'cap':>5} {'cost':>5} {'gross':>6} {'CAGR':>8} {'maxDD':>8} {'Sharpe':>7} {'worst':>8} {'final$':>12}")
        for cost in (5e-4, 1e-3):
            T.COST = cost
            for cap0 in (2300, 10000, 25000):
                for cap in CAPS:
                    groups = {}
                    for d, g in t.groupby("date"):
                        n = len(g)                     # live: frac = min(1/n, cap) x crowd, then x tilt x weekend
                        w = g["x"].to_numpy() * (min(1.0 / n, cap) / min(1.0 / n, 0.10)) * T.NW
                        groups[d] = (g["cu"].to_numpy(), g["ret"].to_numpy(), {"a": w})
                    gross = np.mean([w["a"].sum() for _, (c, r, w) in groups.items()])
                    m = T.simulate(groups, nights, "a", cap0, 1.0, 1.0)
                    P(f"  {cap0:>8} {cap:5.2f} {cost*1e4:4.0f}bp {gross:6.2f} {m['cagr']*100:+7.1f}% {m['mdd']*100:+7.1f}% {m['sharpe']:7.2f} {m['worst']*100:+7.1f}% {m['final']:12,.0f}")
                P("")
    OUT.write_text("\n".join(L))

if __name__ == "__main__":
    main()
