"""Battery J: max_corr rigor (plateau + random-drop control + falsification),
and the shock middle-band question. Engine-based so gates and max_corr combine.
"""
import numpy as np
from h import (bars, summ, uncapped, shock_share, pin, band, overnight_share,
               down_days)
from swingtrader.config import Config
import engine

b = bars()
engine.overnight_share = pin(shock_share, 5)


def rnd_gate(p, seed=0):
    rng = np.random.default_rng(seed)

    def g(hist, w):
        return 1.0 if rng.random() < p else 0.0
    return g


def go(label, cfgmod=None, gate=None, **kw):
    engine.overnight_share = gate if gate is not None else pin(shock_share, 5)
    cfg = Config.load()
    cfg.portfolio.equity = 100_000.0
    if cfgmod:
        cfgmod(cfg)
    res = engine.run2(b, cfg, "highvol", stop_pct=10.0, cash_symbol="BIL", **kw)
    print(summ(res, label), flush=True)
    return res


print("=== reference + random-drop controls ===", flush=True)
go("uncapped 0.10")
for p in (0.67, 0.50):
    g = rnd_gate(p)
    go(f"uncapped random-keep {p}", cfgmod=uncapped, gate=g, min_overnight_share=1.0)

print("=== max_corr finer plateau on uncapped ===", flush=True)
for mc in (0.90, 0.80, 0.70, 0.60, 0.50):
    go(f"uncapped max_corr {mc}", cfgmod=uncapped, max_corr=mc)

print("=== max_corr correlation window ===", flush=True)
for cw in (10, 40):
    go(f"uncapped max_corr 0.7 win{cw}", cfgmod=uncapped, max_corr=0.7, corr_window=cw)

print("=== falsification on max_corr ===", flush=True)
go("uncapped max_corr 0.7 FLIP", cfgmod=uncapped, max_corr=0.7, control="flip")
go("uncapped max_corr 0.7 SHUFFLE", cfgmod=uncapped, max_corr=0.7, control="shuffle")

print("=== shock middle-band (honest post-hoc check) ===", flush=True)
for lo, hi in ((0.4, 0.7), (0.5, 0.7), (0.3, 0.6)):
    go(f"top8 shock band [{lo},{hi}]", gate=band(pin(shock_share, 5), lo, hi),
       min_overnight_share=0.5)

print("=== the proven filter + max_corr on the deployable config ===", flush=True)
go("uncapped ovn>=0.3", cfgmod=uncapped, gate=pin(overnight_share, 5), min_overnight_share=0.3)
go("uncapped ovn>=0.3 max_corr 0.7", cfgmod=uncapped, gate=pin(overnight_share, 5),
   min_overnight_share=0.3, max_corr=0.7)
print("DONE", flush=True)
