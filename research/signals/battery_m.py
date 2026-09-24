"""Battery M: remaining validation for the correlation cap."""
import numpy as np
from h import bars, summ, uncapped, overnight_share, pin
from swingtrader.config import Config
from swingtrader.report import bootstrap_edge, cost_shock, concurrent_correlation
import engine

b = bars()
engine.overnight_share = pin(overnight_share, 5)


def go(label, cohort="highvol", cfgmod=None, **kw):
    cfg = Config.load()
    cfg.portfolio.equity = 100_000.0
    if cfgmod:
        cfgmod(cfg)
    res = engine.run2(b, cfg, cohort, stop_pct=10.0, cash_symbol="BIL", **kw)
    print(summ(res, label), flush=True)
    return res


print("=== candidate-correlation: what the cap actually removes ===", flush=True)
r0 = go("uncapped baseline", cfgmod=uncapped)
print("  corr:", concurrent_correlation(b, r0), flush=True)
r1 = go("uncapped max_corr 0.7", cfgmod=uncapped, max_corr=0.7)
print("  corr:", concurrent_correlation(b, r1), flush=True)

print("=== broad cohort replication ===", flush=True)
go("broad baseline", cohort="broad")
go("broad max_corr 0.7", cohort="broad", max_corr=0.7)

print("=== bootstrap + cost shock on uncapped max_corr 0.7 ===", flush=True)
r = go("uncapped max_corr 0.7", cfgmod=uncapped, max_corr=0.7)
print("  bootstrap:", bootstrap_edge(r.trades), flush=True)
print("  cost shock:\n", cost_shock(r.trades).round(3).to_string(), flush=True)

print("=== live top8 + max_corr ===", flush=True)
go("top8 max_corr 0.7", max_corr=0.7)
go("top8 max_corr 0.8", max_corr=0.8)
print("DONE", flush=True)
