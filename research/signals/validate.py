"""Harness validation: must reproduce addendum-4 numbers exactly."""
import time
from h import bars, run, reset_gate

b = bars()
print(f"loaded {len(b)} symbols", flush=True)

t = time.time()
s, _ = run(b, "baseline top8 (expect 15.1/0.95/-14.4)")
print(s, f"[{time.time()-t:.0f}s]", flush=True)

t = time.time()
s, _ = run(b, "overnight>=0.3 (expect rm 22.3, Sh 1.34)",
           min_overnight_share=0.3, overnight_window=5)
print(s, f"[{time.time()-t:.0f}s]", flush=True)
reset_gate()
