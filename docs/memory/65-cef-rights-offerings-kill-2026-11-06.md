# CEF-RIGHTS (N 1084, 2026-11-06): KILL on the long side, wrong sign; the pressure is real and does not reverse

- First data test of CEF rights offerings (before: "payoff ~0" by prior). Events built from EDGAR without efts (efts.sec.gov
  returns 403 from this host; www.sec.gov / data.sec.gov work with a generic UA): Sharadar SFP CEF -> CIK -> submissions JSON ->
  497/424B* filed >= 365d after first price whose text has "rights offering|subscription rights" + "subscription price"; expiry =
  earliest "Month D, YYYY" within 200/300 chars of "expir" in [filed, filed+120d]. 163 offerings 2001-26, 6.4/yr, 90 funds.
  `research/sim/cef_rights_fetch.py` (reusable per-fund EDGAR text census), `research/sim/cef_rights.py`.
- Long close(E+5)->close(E+25) vs EW CEF (delisted incl.), 20bp/side: -229bp t -4.96, median -242, hit 24%, halves both < 0,
  22/26 yrs < 0, gates 0/7. Placebo E-126 +88bp (funds offer after strong runs).
- Mechanism windows: E-10->E -352bp t -9.45 (formula pricing: subscription price set off the last days' market price);
  E->E+5 -68; E+5->E+25 -189 gross. Non-transferable worse than transferable.
- Use: a CEF holder should exit before the pricing window; never buy the post-expiry "dip" within 25 sessions. Short E-10->E+25
  ~+6.1% gross is post-hoc, taxable-only, borrow-DATA-LIMITED (CEFs mid-offering likely HTB), all data touched -> forward only.
- CEF-RV overlap: 53/5,502 entries 2008-26 in a rights window; exclusion is hygiene (< 0.5pp), not tested.
- Not tested: holds > E+25, borrow, BDC/REIT/operating-company rights, NAV-relative statistic, announcement day, 41 unparsed docs.
