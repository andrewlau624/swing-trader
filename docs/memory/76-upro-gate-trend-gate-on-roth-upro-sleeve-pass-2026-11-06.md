# UPRO-GATE (N 1106-1107, 2026-11-06): trend gate on the Roth's passive UPRO sleeve only — PASS, proposal only

Different from REGIME-10M (N 919-922, gates on the MR book, class closed): only the passive 1/3 UPRO core is gated (the Roth
book sizes from DAILY_ROTH_CAPITAL, executor.py ~1731; the UPRO core is a manual holding, plan NEXT.md "Index-beat hunt").

- Data: synthetic 3x = 3 x S&P TR (^GSPC + Shiller dividends to 1993-01, SPY adjclose after) - 2 x DTB3 - 0.91%/yr.
  vs real UPRO 2009-26: corr 0.998, TE 3%/yr, synthetic ~1.7pp/yr optimistic (swap spread; 2(rf+50bp) closes most of it).
- Judge 1955-2008, execution next session's 16:00 close cross, OFF = T-bills less SGOV fee, 2bp/side:
  B&H 3x 6.4% CAGR / -97% maxDD. 10M SMA (TR, month-end): 13.7% / -78% (1987). 200D 1% band: 13.2% / -80.5%. Both pass
  G1 MAR >= 1.5x, G2 CAGR >= 80%, G3 worst-12m better, in BOTH halves (1955-81, 1982-2008); 3x cost costs ~0.1-0.2pp/yr.
- Honest benchmark: static UPRO+bills at the same maxDD earns 4.4-4.9pp/yr LESS on the judge -> the gate beats "hold less".
- What it does: cuts slow bears (1973-74, 2000-02, 2007-09: 10M maxDD -42% vs -96%; 2020: -34% vs -77%). What it does not:
  1987 (-78%), 2018Q4 (10M worse than B&H), 2022 (10M -57% vs -63%; 200D -36%).
- 2009-26 real UPRO (bull, descriptive): 10M costs 12pp/yr (17.7% vs 30.1%) and LOSES to the maxDD-matched static mix;
  200D 24.9% / -47.8% vs B&H 30.1% / -76.8%. Whole Roth 2009-26: B&H 16.6%/-33%, 200D 14.0%/-22%, 1/6 static 10.8%/-20%.
- Selection: both rules were published on data containing the judge window -> not OOS for the rule family. DSR not computed.
- Proposal (not live): gate the UPRO core with the 200D band or 10M, switch at the next close cross into SGOV; forward shadow
  first (testing.py REGISTRY entry). User decision. Runner research/sim/upro_gate.py; out data/research/program/upro_gate_out.txt.
- Not tested: other lengths/bands (deliberately, no tuning), vol-target scaling of UPRO, 2x (SSO) instead of 3x, partial
  de-risking (e.g. 1/3 -> 1/6 when OFF), gating the taxable SPY 1.0x core, intraday/stop-based exits, pre-1955 (no DTB3).
