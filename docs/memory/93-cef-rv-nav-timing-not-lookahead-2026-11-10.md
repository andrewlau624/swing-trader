# CEF-RV NAV timing: not lookahead, a logging artifact (2026-11-10)

Question: recon said 24 of 28 CEF-RV rule entries were `missed` ("entry session already passed"), mostly muni funds
(MMD, MMU, NEA, NZF, NVG, MYI, IQI). Hypothesis: those Friday NAVs publish after Monday 08:20, so the research's Monday-open
entry used an unknowable NAV. **Verdict: REFUTED.** No late-NAV class exists in the mapped universe.

Evidence (server, read-only):
- logs/cef-rv-live.jsonl: every Tuesday `missed` row for signals 10-23 (20) and 10-30 (4) has a Monday 09:05 `buy-skip`
  row for the same (sym, signal) ("no budget / position room or 0 shares"). The rows WERE in state/cef-rv.jsonl at Monday
  09:05 (file written 08:25 ET). `entries()` returned any unbought row with a passed session as missed, so each skip was
  re-logged the next day, and recon.cef_section keyed reasons by sym only, so the later `missed` won. Corrected recon on the
  same files: 28 rule entries, 2 bought, misses {'buy-skip': 26}.
- Why skipped: 10-26 settled cash $4; 11-02 equity cap $1,000 -> 1 slot, already held; 11-09 cap $2,500 -> 2 slots.
  Cash and position caps, not timing (live sizing untouched).
- Genuine misses: signals 10-09 (before the leg's first run 10-19) and 10-16 (19 names; 10-19 shadow ran on a stale panel:
  "CEFConnect unreachable ... latest week 2026-10-09"; Nasdaq refresh cef_nav.py was deployed that evening). Ops gap, closed.
- Publication timing: journal shows the Monday 08:21-08:25 ET Nasdaq refresh extended 312/314 mapped funds with Friday's
  row on 10-26, 11-02 and 11-09 (2 return nothing every week). Fetch at Tue 2026-11-10 03:28 ET: 314/314 mapped funds
  (all muni funds above incl.) already had Monday 11-09's NAV. Every mapped fund publishes daily NAV by the next pre-open;
  Friday NAV is knowable before Monday's open. One lag class; sponsor split not needed.

Changed (commit in this session): cef_rv_live.run no longer logs `missed` for a (sym, signal) already bought / skipped /
rejected on its session; recon.cef_section keys reasons by (sym, session), session-day reason wins. Tests added.

Not run: the pre-registered delayed-entry (Tuesday-open) re-test. Its premise (late NAV) is false, so no program N was
consumed. Not tested: exact first-publication time on Friday evening (only upper bounds: Mon 08:25, next-day 03:28); the
40 unmapped funds (cannot signal anyway); whether CEFConnect's historical NAVs were ever restated after first print
(the research panel's source; 624/624 overlap rows match Nasdaq but that is post-hoc data, not first-print).
Latent, not fixed: panel() skips refresh once >= half the funds have the due Friday, so a fund whose Friday NAV is
missing at Monday 08:20 would only get that row next Monday (a missed week). Moot at 312/314; a retry would fix it.
