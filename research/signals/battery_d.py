"""Battery D: structural knobs that need no new signal (time stop, costs)."""
from h import bars, run, uncapped

b = bars()

print("=== reference ===", flush=True)
s, _ = run(b, "baseline top8 tstop20")
print(s, flush=True)
s, _ = run(b, "uncapped + pos 0.10 (deployable)", cfgmod=uncapped)
print(s, flush=True)

print("=== time-stop sweep (top8) ===", flush=True)
for ts in (5, 10, 15, 25, 30, 40, 60):
    s, _ = run(b, f"time_stop {ts}d", time_stop_days=ts)
    print(s, flush=True)

print("=== slippage sensitivity (value of earning vs paying the spread) ===", flush=True)
for bps in (0.0, 5.0, 10.0, 40.0):
    def setbps(c, bps=bps):
        c.portfolio.slippage_bps = bps
    s, _ = run(b, f"baseline slip {bps:.0f}bps", cfgmod=setbps)
    print(s, flush=True)
print("DONE", flush=True)
