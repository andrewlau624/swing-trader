"""Walk-forward backtest across cohorts, directions, stop grid, and controls."""
import argparse, json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from swingtrader import backtest, report
from swingtrader.config import Config, ROOT
from swingtrader.data import fetch_bars
from swingtrader.universe import all_assets

OUT = ROOT / "out"


def load_bars(cfg):
    u = all_assets()
    bars = fetch_bars(u.symbols + ["SPY"], cfg.data.start, cfg.data.end,
                      feed=cfg.data.feed, adjustment=cfg.data.adjustment, verbose=False)
    return {s: d for s, d in bars.items() if len(d) > 150}, u


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cohorts", default="highvol,broad")
    ap.add_argument("--modes", default="long,longshort")
    ap.add_argument("--stops", default="none,10,15")
    ap.add_argument("--controls", default="none,flip,random,shuffle")
    ap.add_argument("--quick", action="store_true", help="long-only, no stop, no controls")
    a = ap.parse_args(argv)

    cfg = Config.load()
    OUT.mkdir(exist_ok=True)
    print("loading bars from cache...")
    t0 = time.time()
    bars, u = load_bars(cfg)
    print(f"  {len(bars)} symbols with >150 bars ({time.time()-t0:.0f}s)")
    print(f"  universe was {u.n_active} active + {u.n_inactive} delisted "
          f"({u.inactive_pct:.1f}% delisted - survivorship mitigation)")

    cohorts = a.cohorts.split(",")
    modes = ["long"] if a.quick else a.modes.split(",")
    stops = [None] if a.quick else [None if s == "none" else float(s)
                                    for s in a.stops.split(",")]
    controls = [None] if a.quick else [None if c == "none" else c
                                       for c in a.controls.split(",")]

    summary = []
    for cohort in cohorts:
        for mode in modes:
            for stop in stops:
                for control in controls:
                    if control and (stop is not None or mode != modes[0]):
                        continue  # controls only need one configuration
                    tag = (f"{cohort}_{mode}_stop-{'none' if stop is None else int(stop)}"
                           f"{'_' + control if control else ''}")
                    print(f"\n### {tag}")
                    res = backtest.run(bars, cfg, cohort,
                                       allow_short=(mode == "longshort"),
                                       stop_pct=stop, control=control, verbose=False)
                    txt = report.render(res, bars, title=tag)
                    (OUT / f"{tag}.txt").write_text(txt)
                    pd.DataFrame([t.to_dict() for t in res.trades]).to_csv(
                        OUT / f"{tag}_trades.csv", index=False)
                    res.equity.to_csv(OUT / f"{tag}_equity.csv")
                    cs = report.curve_stats(res.equity)
                    ts = report.trade_stats(res.trades)
                    summary.append({
                        "run": tag, "n_trades": ts.get("n_trades", 0),
                        "cagr_pct": cs.get("cagr_pct"), "sharpe": cs.get("sharpe"),
                        "maxdd_pct": cs.get("max_drawdown_pct"),
                        "win_rate_pct": ts.get("win_rate_pct"),
                        "profit_factor": ts.get("profit_factor"),
                        "avg_pnl_pct": ts.get("avg_pnl_pct"),
                    })
                    print(f"  trades={ts.get('n_trades',0)} "
                          f"CAGR={cs.get('cagr_pct',float('nan')):.1f}% "
                          f"sharpe={cs.get('sharpe',float('nan')):.2f} "
                          f"maxDD={cs.get('max_drawdown_pct',float('nan')):.1f}%")

    sdf = pd.DataFrame(summary)
    sdf.to_csv(OUT / "summary.csv", index=False)
    print("\n" + "=" * 78)
    print(sdf.to_string(index=False, float_format=lambda v: f"{v:9.2f}"))
    print(f"\nwrote {len(summary)} runs to {OUT}")


if __name__ == "__main__":
    main()
