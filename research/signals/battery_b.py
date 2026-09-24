"""Battery B: market/regime context gates on the entry (no engine change)."""
import numpy as np
import pandas as pd
from h import bars, run, reset_gate, set_gate, make_market_gate
from swingtrader.metrics import zscore

b = bars()
spy = b["SPY"]["close"]
vixy = b["VIXY"]["close"]
spy_r5 = spy.pct_change(5)
spy_r20 = spy.pct_change(20)
vixy_r5 = vixy.pct_change(5)
vixy_z = zscore(vixy, 20)


def neg(fn):
    return lambda hist, w: -fn(hist, w)


def test(label, fn, thr):
    set_gate(fn)
    s, _ = run(b, label, min_overnight_share=thr)
    print(s, flush=True)
    reset_gate()


print("=== reference ===", flush=True)
s, _ = run(b, "baseline top8")
print(s, flush=True)
s, _ = run(b, "SPY>200dma (engine regime_filter)", regime_filter=True)
print(s, flush=True)

print("=== SPY short-term return at entry ===", flush=True)
test("spy_r5 >= -0.03 (not a crash)", make_market_gate(spy_r5), -0.03)
test("spy_r5 <= -0.03 (only crash days)", neg(make_market_gate(spy_r5)), 0.03)
test("spy_r5 >= 0.00 (up week)", make_market_gate(spy_r5), 0.0)
test("spy_r20 >= -0.05 (not a downtrend)", make_market_gate(spy_r20), -0.05)
test("spy_r20 <= -0.05 (only downtrend)", neg(make_market_gate(spy_r20)), 0.05)

print("=== VIXY (fear proxy) ===", flush=True)
test("vixy_r5 >= 0 (fear rising)", make_market_gate(vixy_r5), 0.0)
test("vixy_r5 <= 0 (fear falling)", neg(make_market_gate(vixy_r5)), 0.0)
test("vixy_z >= 1.0 (elevated)", make_market_gate(vixy_z), 1.0)
test("vixy_z <= 0.0 (calm)", neg(make_market_gate(vixy_z)), 0.0)
print("DONE", flush=True)
