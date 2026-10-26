# Research memory — session "WRDS entitlement unlock + Tor null" (2026-10-16)

- **The binding constraint was mis-stated.** The program's DATA-LIMITED/BLOCKED rows were a *source* assumption, not a WRDS
  entitlement check. Reconciliation (`research/drafts/wrds_recon_2026-10-16.md`, `data/research/wrds_recon/`, `Make`-free):
  already licensed at $0 -> `optionm.borrate{1996..2025}` (borrow/HTB fee history), `optionm.opprcd{1996..2025}`
  (per-contract open_interest + gamma + delta; ETFs incl. SPY=109820), `optionm.vsurfd{1996..2025}` (per-delta vol surface /
  skew / term), `crsp_q_mutualfunds.daily_nav` + `monthly_tna` + `fund_hdr_hist` (et_flag). STILL blocked: borrow/recall
  *fee* history in the custodial sense (borrate is option-implied), PIT ratings (`ciqsamp_ratings` = 1,322-row sample),
  margin-rate history, CBOE (`cboe.*` = schema `cboe_eod` permission denied). Data facts: `borrate` year tables, sentinel
  exactly -99.99 (not NULL), %/yr, grain (securityid,date,expirationdate) -> pick nearest-30d tenor; `opprcd` is
  OptionMetrics-filtered EOD, NOT raw NBBO, and SPY/QQQ option coverage starts 2005-01 (1996-2004 empty); CRSP MF has
  **no CEFs** (`et_flag` F=ETF/N=ETN/blank=open-end) and CRSP prices end 2024-12-31; links `wrdsapps_link_crsp_optionm.opcrsphist`
  (secid->permno, score=1) and `crsp.dsenames` (`shrcd`).
- **Tor: null, permanently.** Tor installed + reachable; `research/tor_intelligence/` documents the survey. The `.onion`
  financial space is darknet markets + stolen-data/CVV/account shops + templated SEO spam; the only legitimate artifacts
  (Rauzy, delvingbitcoin) are dead v2 mirrors with clearnet duplicates. No legitimate PIT dataset, technology, or mechanism.
  Do not re-run Tor as a data source.
- **BORROW-XS / BORROW-XS2 (N 1006-1007): real signal, no deployable edge.** The option-implied borrow-rate cross-section,
  1996-2025, is monotone (D1 119 -> D10 13 bp/mo) and the LS D1-D10 is +106bp/mo gross (t 6.43); net of 20bp + actual borrow
  +84bp. But the payoff is the SHORT leg (the account cannot short a cash Roth; the same "profitable side is unharvestable"
  pattern as SSR-LIFT / threshold-flow), and the deployable long-only D1 tilt is a size/vol beta (survives only in the small
  + high-vol terciles; nothing clears t>=2 in 2016-25). Closed: no re-tuning of tenor/deciles/lag.
- **GAMMA-MKT (N 1008) + SKEW-MKT (N 1009): KILL.** Index dealer-gamma state: |next-day ret| ~ dealer-gamma z is significant
  but *positive* (a vol-regime proxy, not dealer hedging) and the directional arm ~0; index option skew (RR30) and term slope
  (TS) fail both halves (wrong sign post-2011, t<2 pre-2011). Index gamma/pinning + skew/term families closed.
- **Rule reinforced:** "blocked by data" must be verified against actual entitlements before it is written down; and a
  statistically-passing cross-section whose payoff is the unshortable side is not a candidate. Program N = 1009.
