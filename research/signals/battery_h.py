"""Battery H: correlation cap robustness + stacking with the shock filter.

Uses the validated research engine (engine.run2). Gates are injected by
patching engine.overnight_share (the engine calls that module global).
"""
import numpy as np
from h import bars, summ, uncapped, shock_share, pin
from swingtrader.config import Config
import engine

b = bars()
engine.overnight_share = pin(shock_share, 5)


def go(label, cfgmod=None, **kw):
    cfg = Config.load()
    cfg.portfolio.equity = 100_000.0
    if cfgmod:
        cfgmod(cfg)
    res = engine.run2(b, cfg, "highvol", stop_pct=10.0, cash_symbol="BIL", **kw)
    print(summ(res, label), flush=True)
    return res


def make_size_fn(vol_ref=0.70, lo=0.4, hi=1.6, window=20):
    def f(sym, bb, t):
        c = bb[sym]["close"].loc[:t]
        if len(c) < window + 2:
            return 1.0
        r = np.log(c.astype(float)).diff().iloc[-window:]
        vol = float(r.std(ddof=1) * np.sqrt(252))
        if not np.isfinite(vol) or vol <= 0:
            return 1.0
        return float(np.clip(vol_ref / vol, lo, hi))
    return f


print("=== reference ===", flush=True)
go("uncapped 0.10")
go("uncapped shock5>=0.5", cfgmod=uncapped, min_overnight_share=0.5)

print("=== max_corr plateau on uncapped ===", flush=True)
for mc in (0.95, 0.85, 0.75, 0.65, 0.50):
    go(f"uncapped max_corr {mc}", cfgmod=uncapped, max_corr=mc)

print("=== max_corr x shock ===", flush=True)
for mc in (0.8, 0.7):
    go(f"uncapped shock5>=0.5 max_corr {mc}", cfgmod=uncapped,
       min_overnight_share=0.5, max_corr=mc)

print("=== top8 stacking ===", flush=True)
go("top8 shock5>=0.5 max_corr 0.7", min_overnight_share=0.5, max_corr=0.7)
print("DONE", flush=True)
