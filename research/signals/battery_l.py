"""Battery L: final validation of the correlation cap (the one robust finding).

Checks: window robustness, falsification controls, other cohort, bootstrap,
cost shock, and the candidate-correlation it is supposed to reduce.
"""
import numpy as np
from h import bars, summ, uncapped, overnight_share, pin, z_of
from swingtrader.config import Config
from swingtrader.report import bootstrap_edge, cost_shock, concurrent_correlation, curve_stats
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


print("=== reference ===", flush=True)
go("uncapped 0.10")
go("top8 baseline")

print("=== correlation window robustness ===", flush=True)
for cw in (10, 30, 40):
    go(f"uncapped max_corr 0.7 win{cw}", cfgmod=uncapped, max_corr=0.7, corr_window=cw)
for cw in (10, 30, 40):
    go(f"uncapped max_corr 0.6 win{cw}", cfgmod=uncapped, max_corr=0.6, corr_window=cw)

print("=== falsification controls ===", flush=True)
go("uncapped max_corr 0.7 FLIP", cfgmod=uncapped, max_corr=0.7, control="flip")
go("uncapped max_corr 0.6 FLIP", cfgmod=uncapped, max_corr=0.6, control="flip")
go("uncapped max_corr 0.7 SHUFFLE", cfgmod=uncapped, max_corr=0.7, control="shuffle")

print("=== other cohort (broad) ===", flush=True)
go("broad baseline", cohort="broad")
go("broad max_corr 0.7", cohort="broad", max_corr=0.7)

print("=== detail on uncapped max_corr 0.6 ===", flush=True)
res = go("uncapped max_corr 0.6", cfgmod=uncapped, max_corr=0.6)
print("  bootstrap:", bootstrap_edge(res.trades), flush=True)
print("  cost shock:\n", cost_shock(res.trades).round(3).to_string(), flush=True)
print("  candidate corr:", concurrent_correlation(b, res), flush=True)
res0 = engine.run2(b, Config.load(), "highvol", stop_pct=10.0, cash_symbol="BIL",
                   max_corr=None, verbose=False)
cfg0 = Config.load(); cfg0.portfolio.equity = 100_000.0; uncapped(cfg0)
res0 = engine.run2(b, cfg0, "highvol", stop_pct=10.0, cash_symbol="BIL", max_corr=None)
print("  baseline candidate corr:", concurrent_correlation(b, res0), flush=True)
print("DONE", flush=True)
