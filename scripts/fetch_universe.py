"""One-time bulk fetch of daily bars for the whole universe into the parquet cache."""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from swingtrader.config import Config
from swingtrader.data import fetch_bars
from swingtrader.universe import all_assets

if __name__ == "__main__":
    cfg = Config.load()
    u = all_assets()
    print(f"universe: {len(u.symbols)} symbols "
          f"({u.n_active} active, {u.n_inactive} delisted = {u.inactive_pct:.1f}%)")
    t0 = time.time()
    bars = fetch_bars(u.symbols, cfg.data.start, cfg.data.end,
                      feed=cfg.data.feed, adjustment=cfg.data.adjustment, verbose=True)
    good = {s: d for s, d in bars.items() if len(d) > 250}
    print(f"done in {time.time()-t0:.0f}s: {len(bars)} symbols returned, "
          f"{len(good)} with >250 bars")
