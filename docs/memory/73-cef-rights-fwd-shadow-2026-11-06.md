# CEF-RIGHTS-FWD (N 1085) + CEF-RV rights hygiene (N 1086): forward log-only shadow, 2026-11-06

- Built `swingtrader/daily/cef_rights_shadow.py` (research-shadows, config `daily.cef_rights_fwd: shadow`, `make cef-rights`):
  scans the CEF-RV fund list (state/cef-rv-panel.json -> SEC company_tickers.json CIK) daily on data.sec.gov for 497/424B* final
  prospectuses AND 497AD press releases (N 1084 classifier, `cef_rights_fetch.classify`), logs the would-be SHORT close(E-10) ->
  close(E+25) vs EW CEF, net 2x20bp + borrow. Borrow is read-only: Alpaca asset shortable/easy_to_borrow + Schwab quote reference
  isShortable/isHardToBorrow/htbRate (fields unverified: no Schwab login was available when built). Gate 15 knowable events:
  mean > +200bp, median > 0, borrow available >= 70%; kill mean <= 0. Logs state/cef-rights.jsonl, state/cef-rights-rv.jsonl.
- KEY CAVEAT found while building: N 1084's first final prospectus is filed a median 2 business days before expiry; 78% of the 163
  offerings were filed < 10 sessions before E. The post-hoc E-10 short (+6.1%) is mostly NOT knowable from EDGAR at entry
  (knowable subset E-10->E -164bp, n 31, vs -396bp unknowable). 497AD helps a little (2026: 1 of 5 offerings announced before
  E-10). Expect the gate to fill slowly (~1-2 knowable events/yr) unless an earlier source (fund press releases off-EDGAR, N-2/A
  with dates) is added. Expiry parsing is noisy: 497AD and final prospectus dates disagree by 2-23 days on 4 of 5 2026 events.
- 2026 scan (local, CEF-RV list of 354): MUA, RIV, NMCO (scored late, not gated), BCAT (E 10-14, exit 11-18), NMZ (E 10-30, exit
  12-07) live late; 0 upcoming.
