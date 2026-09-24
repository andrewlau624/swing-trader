"""Battery E: portfolio-level hooks via engine.run2 (corr cap, vol sizing, target)."""
import numpy as np
from h import bars, summ, uncapped
from swingtrader.config import Config
import engine

b = bars()


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
go("baseline top8")
go("uncapped 0.10", cfgmod=uncapped)

print("=== correlation cap (duplicate-bet filter) ===", flush=True)
for mc in (0.9, 0.8, 0.7):
    go(f"top8 max_corr {mc}", max_corr=mc)
for mc in (0.9, 0.8, 0.7):
    go(f"uncapped max_corr {mc}", cfgmod=uncapped, max_corr=mc)

print("=== inverse-vol position sizing ===", flush=True)
go("top8 inv-vol sizing", size_fn=make_size_fn())
go("uncapped inv-vol sizing", cfgmod=uncapped, size_fn=make_size_fn())

print("=== fixed take-profit exit ===", flush=True)
for tp in (5, 8, 10, 15):
    go(f"top8 target +{tp}%", target_pct=tp)
print("DONE", flush=True)
