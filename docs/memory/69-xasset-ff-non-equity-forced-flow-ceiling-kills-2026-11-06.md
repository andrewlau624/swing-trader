# XASSET-FF (2026-11-06, no N): non-equity forced flows via ETFs are ceiling-killed by perfect-foresight bounds

- Ideas A/B of the brief were already in the program: Treasury month-end = TME (validated small, ~4%/yr; TME-L2/TMF measured),
  auction concession = TAC (killed). COMEX delivery = FND branch (user-closed). Not re-run.
- New screening tool: perfect-sign bound = windows/yr x E|log r over window| x 50% capture (`research/sim/xasset_ff_bound.py`).
  If it is < +8pp at $10k the idea dies with no outcome read. TME realised ~29% of its own bound: honest capture ~1/3 of bound.
- Bounds: FX month-end fix (FXE) 2.5pp 1d / 4.3pp 3d; quarter-end USD (UUP) 1.6; Jan BCOM reweight SLV 2.4 / GLD 1.3; muni
  reinvestment (MUB) 1.1; carry unwind AUDJPY 6.6pp (13.1 at 2x; ~4 honest), FXA (Roth) 2.9. All CEILING-KILL.
- Class reading: deep non-equity ETFs at 1x need a daily-cadence mechanism to clear the gate; calendar/episodic flows with <= 12
  short windows/yr cannot, even with perfect foresight. Daily x-asset IBS is already ~+1.7bp (bonds/commodities).
- Not tested: conditional outcomes; spot FX/futures (access); leveraged FX ETPs; intraday London-fix window; silver/natgas flows beyond
  roll/FND/GSCI; physical-trust / halted-creation premia; crypto trust conversions. Out `data/research/program/xasset_ff_out.txt`.
