"""Battery K: size positions by signal quality instead of gating them.

overnight_share is the one monotone, per-trade-significant feature (audit:
rho +0.158, buckets -0.11 / +0.16 / +3.60 / +7.21). Gating discards trades and
worsens utilisation; sizing keeps them all and tilts capital to the better ones.
"""
import numpy as np
from h import bars, summ, uncapped, overnight_share, pin, vol_z
from swingtrader.config import Config
import engine

b = bars()
engine.overnight_share = pin(overnight_share, 5)


def go(label, cfgmod=None, **kw):
    cfg = Config.load()
    cfg.portfolio.equity = 100_000.0
    if cfgmod:
        cfgmod(cfg)
    res = engine.run2(b, cfg, "highvol", stop_pct=10.0, cash_symbol="BIL", **kw)
    print(summ(res, label), flush=True)
    return res


def ovn_size(center=0.30, tilt=1.0, lo=0.4, hi=1.6):
    def f(sym, bb, t):
        hist = bb[sym].loc[bb[sym].index <= t]
        v = overnight_share(hist, 5)
        if not np.isfinite(v):
            return 1.0
        return float(np.clip(1.0 + tilt * (v - center), lo, hi))
    return f


def invvol_size(vol_ref=0.70, lo=0.4, hi=1.6, window=20):
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
go("top8 baseline")
go("uncapped 0.10", cfgmod=uncapped)

print("=== size by overnight share ===", flush=True)
go("top8 ovn-size tilt1", size_fn=ovn_size(tilt=1.0))
go("top8 ovn-size tilt2", size_fn=ovn_size(tilt=2.0))
go("top8 ovn-size tilt3", size_fn=ovn_size(tilt=3.0))
go("top8 ovn-size tilt4", size_fn=ovn_size(tilt=4.0))
go("top8 ovn-size tilt2 lo0.5 hi1.5", size_fn=ovn_size(tilt=2.0, lo=0.5, hi=1.5))
go("uncapped ovn-size tilt1", cfgmod=uncapped, size_fn=ovn_size(tilt=1.0))
go("uncapped ovn-size tilt2", cfgmod=uncapped, size_fn=ovn_size(tilt=2.0))

print("=== combine sizing with the ovn gate ===", flush=True)
go("top8 ovn>=0.3 + ovn-size", min_overnight_share=0.3, size_fn=ovn_size(tilt=1.0))
go("uncapped ovn>=0.3 + ovn-size", cfgmod=uncapped, min_overnight_share=0.3,
   size_fn=ovn_size(tilt=1.0))

print("=== inv-vol reference ===", flush=True)
go("top8 inv-vol", size_fn=invvol_size())
go("uncapped inv-vol", cfgmod=uncapped, size_fn=invvol_size())
print("DONE", flush=True)
