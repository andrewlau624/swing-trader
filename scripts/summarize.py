"""Rebuild the cross-run summary table from whatever is in out/."""
import sys, glob, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas as pd
from swingtrader import report
from swingtrader.config import ROOT

OUT = ROOT / "out"
rows = []
for eq_path in sorted(glob.glob(str(OUT / "*_equity.csv"))):
    tag = os.path.basename(eq_path)[: -len("_equity.csv")]
    tr_path = OUT / f"{tag}_trades.csv"
    if not tr_path.exists():
        continue
    eq = pd.read_csv(eq_path, index_col=0, parse_dates=True).iloc[:, 0]
    tr = pd.read_csv(tr_path)
    cs = report.curve_stats(eq)
    rows.append({
        "run": tag, "n_trades": len(tr),
        "cagr_pct": cs.get("cagr_pct"), "sharpe": cs.get("sharpe"),
        "maxdd_pct": cs.get("max_drawdown_pct"), "calmar": cs.get("calmar"),
        "win_rate_pct": 100.0 * (tr["pnl"] > 0).mean() if len(tr) else None,
        "avg_pnl_pct": tr["pnl_pct"].mean() if len(tr) else None,
    })
df = pd.DataFrame(rows).sort_values("sharpe", ascending=False)
df.to_csv(OUT / "summary.csv", index=False)
print(df.to_string(index=False, float_format=lambda v: f"{v:9.2f}"))
