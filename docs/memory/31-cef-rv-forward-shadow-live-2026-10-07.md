# CEF-RV forward shadow LIVE (2026-10-07)

- `swingtrader/daily/cef_rv_shadow.py` runs in research-shadows (08:20 ET), REGISTRY "CEF-RV: CEF discount reversion vs
  the CEF universe"; gate in round1_prose.md "CEF-RV-FWD" (60 closed forward trades, >= 10 entry weeks, excess vs EW CEF
  >= +60bp t >= 2). First forward signal week 2026-10-09; Sept/10-02 signals are backfill.
- **CEFConnect blocks the server's IP** (Akamai "request blocked"). Since 2026-10-19 the server extends the weekly panel itself from
  the Nasdaq Fund Network NAV symbols (`cef_nav.py`: X{sym}X or a name lookup, api.nasdaq.com `quote/{navsym}/historical?assetclass=
  mutualfunds` + the fund's own close; 624/624 regenerated rows identical to CEFConnect's; 314/354 funds mapped, the 40 unmapped
  (Sprott trusts, CLO funds, ASA, TY ...) keep their stored rows and cannot produce new signals; map state/cef-rv-navmap.json). `make cef-rv-panel` from the Mac is now only the seed / new-fund
  path (the universe list still comes from CEFConnect); a Mac launchd job (com.swingtrader.cef-rv-panel, Sun 20:00 / Mon 05:00 PT) still
  pushes it weekly as a fallback. Yahoo returns 429 from the server; Stooq needs JS; Sharadar has no CEF NAV.
- Live execution test (`research/sim/cef_open_test.py`, 1 share, Roth, pre-open opg order) is USER-RUN: the auto-mode
  classifier blocks Claude from placing real orders.
