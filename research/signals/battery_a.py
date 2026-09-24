"""Battery A: entry-quality gates on HOW the dip formed (no engine change).

Reference points (published, top8 / -10% stop / cash BIL):
  baseline            15.1% CAGR, Sharpe 0.95, DD -14.4, avg +2.46, n=207
  overnight >= 0.3    17.2% / 1.34 / -11.1 / +5.00 / n=111, risk-matched 22.3
"""
import numpy as np
from h import bars, run, reset_gate, set_gate, vol_z, ibs, close_loc_5, dist_52w_high, overnight_share

b = bars()


def neg(fn):
    return lambda hist, w: -fn(hist, w)


def rnd_gate(p, seed=0):
    rng = np.random.default_rng(seed)

    def g(hist, w):
        return 1.0 if rng.random() < p else 0.0
    return g


def test(label, fn, thr):
    set_gate(fn)
    s, _ = run(b, label, min_overnight_share=thr)
    print(s, flush=True)
    reset_gate()


print("=== reference ===", flush=True)
s, _ = run(b, "baseline top8")
print(s, flush=True)
test("overnight >= 0.3 (ref)", overnight_share, 0.3)

print("=== volume of the dip ===", flush=True)
test("volz >= 1.0 (heavy-volume dip)", vol_z, 1.0)
test("volz >= 2.0", vol_z, 2.0)
test("volz >= 3.0", vol_z, 3.0)
test("volz <= 0.0 (quiet dip)", neg(vol_z), 0.0)
test("volz <= -0.5", neg(vol_z), 0.5)

print("=== close location (IBS) ===", flush=True)
test("ibs <= 0.30 (closed near low)", neg(ibs), -0.30)
test("ibs <= 0.10", neg(ibs), -0.10)
test("ibs >= 0.70 (closed off low)", ibs, 0.70)

print("=== 5-day close location ===", flush=True)
test("closeloc5 <= 0.30", neg(close_loc_5), -0.30)
test("closeloc5 >= 0.70", close_loc_5, 0.70)

print("=== distance from 52w high ===", flush=True)
test("dist52w >= -0.30 (near highs)", dist_52w_high, -0.30)
test("dist52w <= -0.50 (broken)", neg(dist_52w_high), 0.50)

print("=== random-gate controls (trade-count matched) ===", flush=True)
for p in (0.55, 0.30, 0.15):
    set_gate(rnd_gate(p, seed=1))
    s, _ = run(b, f"random gate p={p}", min_overnight_share=1.0)
    print(s, flush=True)
    reset_gate()
print("DONE", flush=True)
