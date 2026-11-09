# GUIDANCE (management full-year guidance as a signal): DATA-LIMITED, 2026-11-09

Probe only; no N used, nothing tested. This WRDS account has no USAGE on schema `tr_ibes_guidance` (ibes.det_guidance,
det_guidance_ext, id_guidance*), nor `tr_ibes_corporate`, `tr_ibeskpi`, `tr_ibes_iga*`, `tr_ibes_old`. Readable:
`ibes.det_epsus` (detail estimates with activation dates -> PIT consensus), `ibes.idsum`, `crsp.dsf` (openprc),
`crsp.dsedelist`, link table `wrdsapps_link_crsp_ibes.ibcrsphist` (listed, not selected).

Branches registered in conversation, all untested: B1 implied-Q4 gap (FY guide midpoint - Q1..Q3 actuals vs consensus
Q4, day-2 open -> pre-Q4-report), B2 guidance-revision drift (day-2 open, 20/60d), B3 low first guide for the new FY.
Unblock: WRDS "IBES Guidance" product (subscription request, user's call). Text reconstruction from 8-K/press releases is
OUT (user closed text signals 2026-10-19). No free live guidance feed exists for a forward shadow.
Probe scripts were scratch-only; connect with `uv run --with psycopg2-binary` (no repo .venv locally).
