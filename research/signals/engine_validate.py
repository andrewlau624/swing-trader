"""Validate the research engine (engine.run2) reproduces the package baseline."""
import time
from h import bars, summ, uncapped
from swingtrader.config import Config
import engine

b = bars()
cfg = Config.load()
cfg.portfolio.equity = 100_000.0

t = time.time()
res = engine.run2(b, cfg, "highvol", stop_pct=10.0, cash_symbol="BIL")
print(summ(res, "engine.py baseline (expect 15.1/0.95/-14.4)"), f"[{time.time()-t:.0f}s]", flush=True)

cfg2 = Config.load()
cfg2.portfolio.equity = 100_000.0
uncapped(cfg2)
res2 = engine.run2(b, cfg2, "highvol", stop_pct=10.0, cash_symbol="BIL")
print(summ(res2, "engine.py uncapped (expect 22.3/1.16)"), flush=True)

# hooks off must equal baseline exactly
res3 = engine.run2(b, cfg, "highvol", stop_pct=10.0, cash_symbol="BIL",
                   max_corr=None, size_fn=None, target_pct=None)
print("identical to package baseline:",
      res3.equity.round(6).equals(res.equity.round(6)), flush=True)
