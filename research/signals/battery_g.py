"""Battery G: robustness of the shock_share finding + combos + controls."""
import numpy as np
from h import (bars, run, reset_gate, set_gate, shock_share, overnight_share,
               vol_z, pin, combo, uncapped)

b = bars()


def test(label, fn, thr, cohort="highvol", cfgmod=None, **kw):
    set_gate(fn)
    s, _ = run(b, label, cohort=cohort, cfgmod=cfgmod, min_overnight_share=thr, **kw)
    print(s, flush=True)
    reset_gate()


print("=== reference ===", flush=True)
s, _ = run(b, "baseline top8")
print(s, flush=True)
s, _ = run(b, "uncapped 0.10", cfgmod=uncapped)
print(s, flush=True)

print("=== shock_share threshold plateau (window 5) ===", flush=True)
for th in (0.30, 0.40, 0.50, 0.60, 0.70):
    test(f"shock5 >= {th:.2f}", pin(shock_share, 5), th)

print("=== shock_share window (threshold 0.5) ===", flush=True)
for w in (3, 10):
    test(f"shock{w} >= 0.50", pin(shock_share, w), 0.50)

print("=== shock on the deployable (uncapped) config ===", flush=True)
for th in (0.4, 0.5, 0.6):
    test(f"uncapped shock5 >= {th:.2f}", pin(shock_share, 5), th, cfgmod=uncapped)

print("=== combos ===", flush=True)
test("shock5>=0.5 AND ovn>=0.3", combo(pin(shock_share, 5), 0.5, pin(overnight_share, 5), 0.3), 0.5)
test("shock5>=0.4 AND ovn>=0.3", combo(pin(shock_share, 5), 0.4, pin(overnight_share, 5), 0.3), 0.5)
test("shock5>=0.5 AND volz20>=1", combo(pin(shock_share, 5), 0.5, pin(vol_z, 20), 1.0), 0.5)

print("=== falsification controls on shock5>=0.5 ===", flush=True)
test("shock5>=0.5 FLIP", pin(shock_share, 5), 0.5, control="flip")
test("shock5>=0.5 SHUFFLE", pin(shock_share, 5), 0.5, control="shuffle")

print("=== other cohort (broad) ===", flush=True)
s, _ = run(b, "broad baseline", cohort="broad")
print(s, flush=True)
test("broad shock5 >= 0.5", pin(shock_share, 5), 0.50, cohort="broad")
print("DONE", flush=True)
