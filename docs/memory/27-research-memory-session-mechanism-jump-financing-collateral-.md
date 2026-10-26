# Research memory — session "mechanism jump: financing/collateral/margin" (2026-10-06, cont.)

- **Pre-test ceiling table** (round1_prose.md): CL/NG monthly GSCI roll (~1-4%/yr), buyback 10b-18
  blackout flow (~1-2%/yr), SG-CTA crowding (~1-2%/yr), DXJ/EWJ forward-point wedge (2-4%/yr minus
  borrow), dividend-fail pre-ex-div front-run — ALL CEILING-KILLED before any backtest. No reruns.
- **PLUM (N 865): KILL.** Daily repo-stress states (SOFR-DTB3 >= 25bp n 171, SOFR-IORB n 3, FRED
  free): 1d ~0 both directions; 3d mean crash-carried (median -18bp). Post-2021 flags benign —
  SRF absorbed the mechanism. The daily financing state is NOT a usable risk gate. Runners
  research/sim/{plum,mflw}.py; outputs data/research/program/{plum,mflw}_out.txt.
- **MFLW (N 866): KILL.** FINRA margin-debt monthly 1997-2026 (one free XLSX,
  data/research/finra/margin.xlsx): cascade-bounce +16bp/mo t 0.11 with 52% hit (2008/09.next-months
  -8..-11%) — no reliable bounce; euphoria-short wrong sign. Margin debt coincident. Family closed.
- **Region status:** the financing/collateral/margin/clearing members of the mechanism map are now
  MEASURED at free data and empty at retail tier. The one remaining free-data region = FINRA ATS
  venue-mix (off-exchange share per symbol, weekly): needs a FREE FINRA API token (user action at
  api.finra.org; otcMarket weeklySummary already key-less) — then a conditioning study on the
  IBS/night legs becomes testable. Everything else standing is paid-tier (OPRA gamma, margin-rate
  archive, borrow fees, PIT ratings, TBA, per-fund NAV, Milliman LDI) — user decisions, not automatic.
- Program N = 866.
