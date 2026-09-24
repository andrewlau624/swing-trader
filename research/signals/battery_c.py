"""Battery C: remaining dip-quality gates + z-shape gates + combos + controls."""
import numpy as np
from h import (bars, run, reset_gate, set_gate, vol_z, ibs, close_loc_5,
               dist_52w_high, overnight_share, z_of, z_turn_up, z_two_days, combo)

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
test("volz >= 1.0 (ref)", vol_z, 1.0)

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

print("=== z-shape (reversal confirmation) ===", flush=True)
test("z rising (turn up)", z_turn_up, 0.5)
test("z falling (still going down)", neg(z_turn_up), -0.5)
test("z <= -2 two days running", z_two_days, 0.5)
test("z >= -3 (not a falling knife)", z_of, -3.0)
test("z >= -4", z_of, -4.0)

print("=== combos of the two winners ===", flush=True)
test("overnight>=0.3 AND volz>=1", combo(overnight_share, 0.3, vol_z, 1.0), 0.5)
test("overnight>=0.3 AND volz>=0", combo(overnight_share, 0.3, vol_z, 0.0), 0.5)

print("=== random-gate controls ===", flush=True)
for p in (0.55, 0.40, 0.25):
    set_gate(rnd_gate(p, seed=1))
    s, _ = run(b, f"random gate p={p}", min_overnight_share=1.0)
    print(s, flush=True)
    reset_gate()
print("DONE", flush=True)
