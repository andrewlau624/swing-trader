# Research memory — session "domain jump: regulatory positioning" (2026-10-06, cont.)

- Answer to "what category has the program never modeled": (1) cross-instrument same-issuer relationships
  (preferred/dual-class/holdco vs common: NO convergence force / costs); (2) regulatory-mandated positioning.
  Built the first 13F-state panel ever (`f13f_agg.py` -> `data/research/f13f/agg.parquet`, 432k name-quarters,
  common-only, mxp/opp/fxp vs marketcap-implied shares, fund-name regex flag).
- **F13C-CAP (N 854->856): KILL both judged arms.** Trim (short, press = mxp>=9.5% & dsh<=-5%): +1.31%/window
  t 0.80, ex-top-5-names ~0; FREED (long after unwind prints done): -12.2%/window t -3.2 both halves.
  Reverse-split contamination only ~3%; the null is real. Participant-typed v2 (N->857): TRIM2 +0.15% t 0.08, FREED2 n 36 noise — family FINAL: no tradable footprint in daily 13F-state data.
- **Kept diagnostic:** implied shares down >=5%/q => -4.7..-5.7%/q vs SPY both halves (t -2.3..-2.8):
  dilution/death-spiral drag as a defensive avoid-screen (forward-watch), not alpha.
- 13F economics: quarterly lag + heavy overlap; a present-13F family can work only as a STATE gate on an
  existing edge, which no session has specified cleanly yet. No deployment.
