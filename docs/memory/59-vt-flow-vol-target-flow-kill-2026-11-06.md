# VT-FLOW (N 1072-1075, 2026-11-06): vol-target fund flow signal KILL; VT-SPIKE ceiling-kill

- Modeled generic vol-target book on ^GSPC: E = min(1.5, 0.10 / max(RV21, RV63)). A1 = daily dE (funds execute next close), A2 = dE from
  the 21d/63d drop-outs only (deterministic; ~always >= 0, so long-only). Signal = |dE| above trailing-252 q80/q90, hold close->close.
- Choice on SPY 2010-19: all 4 variants |t| < 0.35. Judged A2 q.90: SPY 2020-26 net -3.3bp t -0.44; STOXX50E 2010-26 +8.7bp gross t 0.5;
  pre-vol-target placebo ^GSPC 1970-99 +4.8bp t 1.5, larger than the modern era: the predicted flow does not move next-day index returns
  at daily close-to-close tier. A1 (incl. short side) desc 2020-26 t < 0.6. Gates 0/6.
- VT-SPIKE (buy after -4% days gated on vol falling): ceiling ~+1.2pp/yr, same shape as PANIC-IDX; no N.
- Not tested: same-day last-hour flow (minute data), exact S&P Risk Control EWMA + lag, AUM-scaled flow, risk-parity cross-asset, LETF rebalance.
- Runner `research/sim/vt_flow.py` (free Yahoo, cache `data/research/vtflow/`), out `data/research/program/vt_flow_out.txt`. Program N = 1075.
- 2026-11-05 state (descriptive): modeled exposure 0.79 -> 0.51x after the -4.4% day; no large return leaves the 21d window in the next 10 sessions.
