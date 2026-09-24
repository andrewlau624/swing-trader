"""Battery F: corrected gates (windows pinned) + combos + controls.

Windows are pinned because the engine passes overnight_window (5) to the gate.
vol_z(5) = recent 5-day volume z; vol_z(20) = 20-day.
"""
import numpy as np
from h import (bars, run, reset_gate, set_gate, vol_z, ibs, close_loc_5,
               dist_52w_high, overnight_share, z_of, z_turn_up, z_two_days,
               combo, pin, shock_share, down_days)

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
test("overnight >= 0.3 (ref)", pin(overnight_share, 5), 0.3)

print("=== volume z, both windows ===", flush=True)
test("volz5 >= 1.0", pin(vol_z, 5), 1.0)
test("volz5 >= 2.0", pin(vol_z, 5), 2.0)
test("volz20 >= 1.0", pin(vol_z, 20), 1.0)
test("volz20 >= 2.0", pin(vol_z, 20), 2.0)

print("=== 52w distance (pinned 252) ===", flush=True)
test("dist52w >= -0.30 (near highs)", pin(dist_52w_high, 252), -0.30)
test("dist52w <= -0.50 (broken)", neg(pin(dist_52w_high, 252)), 0.50)

print("=== z depth (pinned 20) ===", flush=True)
test("z20 >= -2.5 (not too deep)", pin(z_of, 20), -2.5)
test("z20 >= -3.0", pin(z_of, 20), -3.0)
test("z20 >= -4.0", pin(z_of, 20), -4.0)

print("=== z shape (pinned 20) ===", flush=True)
test("z20 rising (turn up)", pin(z_turn_up, 20), 0.5)
test("z20 falling", neg(pin(z_turn_up, 20)), -0.5)
test("z20 <= -2 two days", pin(z_two_days, 20), 0.5)

print("=== dip shape ===", flush=True)
test("shock_share >= 0.5 (one-day shock)", pin(shock_share, 5), 0.5)
test("shock_share <= 0.3 (grind)", neg(pin(shock_share, 5)), -0.3)
test("down_days <= 0.6", neg(pin(down_days, 5)), -0.6)
test("down_days >= 0.8", pin(down_days, 5), 0.8)

print("=== combos of winners ===", flush=True)
test("ovn0.3 AND volz5>=1", combo(pin(overnight_share, 5), 0.3, pin(vol_z, 5), 1.0), 0.5)
test("ovn0.3 AND volz20>=1", combo(pin(overnight_share, 5), 0.3, pin(vol_z, 20), 1.0), 0.5)
test("ovn0.2 AND volz5>=1", combo(pin(overnight_share, 5), 0.2, pin(vol_z, 5), 1.0), 0.5)

print("=== random-gate controls ===", flush=True)
for p in (0.55, 0.40, 0.25):
    set_gate(rnd_gate(p, seed=1))
    s, _ = run(b, f"random gate p={p}", min_overnight_share=1.0)
    print(s, flush=True)
    reset_gate()
print("DONE", flush=True)
