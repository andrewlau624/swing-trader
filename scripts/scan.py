"""What looks tradable right now? Ranks the current formation window."""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from swingtrader.config import Config
from swingtrader.data import fetch_bars
from swingtrader.scan import apply_filters, metric_table, rank
from swingtrader.universe import all_assets


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cohort", default="highvol")
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--asof", default=None, help="end of the formation window (YYYY-MM-DD)")
    a = ap.parse_args(argv)

    cfg = Config.load()
    cohort = cfg.cohort(a.cohort)
    end = pd.Timestamp(a.asof or cfg.data.end)
    start = end - pd.Timedelta(days=int(cfg.walkforward.formation_days * 1.5))

    u = all_assets()
    bars = fetch_bars(u.symbols, cfg.data.start, cfg.data.end,
                      feed=cfg.data.feed, adjustment=cfg.data.adjustment, verbose=False)
    win = {s: d.loc[(d.index >= start) & (d.index <= end)] for s, d in bars.items()}
    win = {s: d for s, d in win.items() if len(d) >= cfg.walkforward.formation_days * 0.8}

    tbl = metric_table(win, cohort)
    print(f"cohort={a.cohort}  formation {start.date()}..{end.date()}")
    print(f"  {len(win)} symbols with enough history -> {len(tbl)} pass the cohort prefilter")
    kept = apply_filters(tbl, cfg.selection)
    print(f"  {len(kept)} clear every hard gate")
    if kept.empty:
        print("\n  nothing qualified. loosen config.yaml:selection or widen the cohort.")
        return
    top = rank(kept, a.top)
    cols = ["score", "halflife", "hurst", "drift_t", "amplitude_pct",
            "efficiency_ratio", "annual_vol", "last_close", "dollar_vol"]
    print()
    print(top[cols].to_string(float_format=lambda v: f"{v:10.3f}"))
    if "RGTI" in tbl.index:
        r = tbl.loc["RGTI"]
        status = "SELECTED" if "RGTI" in kept.index else "filtered out"
        print(f"\n  RGTI ({status}): halflife={r['halflife']:.1f} hurst={r['hurst']:.3f} "
              f"|drift_t|={abs(r['drift_t']):.2f} ampl={r['amplitude_pct']:.1f}% "
              f"ER={r['efficiency_ratio']:.3f}")


if __name__ == "__main__":
    main()
