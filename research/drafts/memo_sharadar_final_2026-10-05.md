# Sharadar session — FINAL MEMO (2026-10-05)

Scope: run every pre-registered, decision-relevant study the Sharadar full bundle newly enabled, before the
subscription is cancelled. Results are recorded in `research/drafts/round1_prose.md` (pre-registrations + dated
corrections), `NEXT.md` (do-not-redo rows + the session section) and `CLAUDE.md` (research memory).
Program **N 838 -> 839** (SHAR-IBS is the only new judged rule). No live code changed; no deployment.

## Studies run (all one look, adversarially checked)

| study | window / data | verdict | headline |
|---|---|---|---|
| SHAR-IBS (`research/sim/shar_ibs.py`) | live IBS leg, 2003-01..2015-12 ETFs (never used for IBS) | **WEAK, not PASS** | tier net +4.99bp t 1.03 (gross +16.15bp t 3.34); halves +11.84 / -4.69; beta-adj SPY resid -8.58bp t -2.89; 2/5 checks |
| H-POOL on Sharadar (`research/sim/hpool_sharadar.py`) | pooled insider-buy open->close, 2008-01..2015-12 (SF2 start) | **PASS at tier, NOT ROBUST** | +21.1bp t 2.71, n 29,285; tier_hi +11.4bp t 1.46; ex-top-1% +5.4bp; DSR 0.842; decays to ~0 by 2013-15 |
| SHAR-SURV (`research/sim/shar_surv.py`) | night leg 2021-02..2026-09, delisted-complete vs survivor-only | **diagnostic** | survivorship flattered ~+4.1bp/trade at tier (+18.86 -> +14.75); delisted names 24.1% of eligible, 16.0% of picks |
| SHAR-CRASH (`research/sim/shar_crash.py`) | 0.5 IBS + 0.5 night daily-bar book, 2000-02/2008-09/2011/2015-16 | **diagnostic** | 2000-02 maxDD -24.07% (trips -10% lever gate, not the -25% halt); 2008-09 -9.86%; 2011 -8.35%; 2015-16 -8.25% |
| SHAR-EVENT (structural events) | — | **not run (gate + gap)** | S&P flow in the announcement gap; spin-off effect in the distribution gap; round-ups ~$370/yr; all < +8pp/yr at $10k |

Two real bugs were found by the independent adversarial checks and fixed in the same look (not re-looks):
a raw-open split return on 2 SHAR-IBS leg-days (moved the verdict FAIL -> WEAK), and a dropped -100% delisting
outcome filter in SHAR-CRASH (2000-02 maxDD -20.07% -> -24.07%). Both fixes verified by reproduction.

## What changed in the book's evidence

1. **IBS is weaker than believed in the oldest regime.** On the first genuinely untouched pre-2016 window the leg
   is WEAK: the gross premium (+16bp) is real but is fully eaten by `tier` costs, and the beta-adjusted residual is
   **negative** pre-2016 (-8.58bp t -2.89), against the +6.7bp/day 2017-20 residual. The durable-IBS claim now rests
   on 2016-20 (+29.8bp) and 2021-26 live; it does **not** extend to 2003-15. Only the live ~0bp auction cost keeps
   this regime net-positive. 2003-15 is now TOUCHED — no IBS variants or tuning on it.
2. **The night leg is ~4bp/trade less good once delisting is included.** SHAR-SURV puts the survivorship flattering
   of the 2021-26 stock panel at +4.1bp/trade at tier (~22% of the mean), concentrated 2021-23. Quote night-leg
   panels as delisted-complete. This reinforces the NX result (VALIDATED-SMALL, cost-bound).
3. **The insider-buy family survives out of sample only as a crisis tilt.** H-POOL — the program's registered pooled
   rule, never run — passes at `tier` on 2008-15 but fails the cost shock (tier_hi t 1.46), is carried by 2008-10,
   and decays to ~0 by 2013-15. It is the first insider evidence on a window the program never saw, but it is
   conditional, not a standalone engine. Keep the ID3 shadow forward; do not size up.
4. **Crash behaviour is better than the halt implies.** Across 2000-02, 2008-09, 2011 and 2015-16 the daily-bar book
   never breached the -25% halt; the -10% leverage gate would have fired in 2000-02 (maxDD -24.07%). The daily-close
   proxy is optimistic (~1.7x vs the exact 15:40 rule, per NX), so treat these as upper bounds.
5. **No new edge.** The bundle did not add a tradable edge; it qualified two live legs and ran the insider family
   on its registered untouched decade. The data-buy gate is vindicated (expected information > cost) and the open
   pre-2016 questions are now answered — the subscription can be cancelled without losing a decision-relevant test.

## Recommendations (recommendations only: no live changes, no deployment)

- **IBS leg:** do not size up on the strength of the leg; the pre-2016 evidence is weaker than assumed. If more
  IBS confidence is wanted, the next test is a forward, delisted-complete panel — not another re-split of 2021-26
  and not a 2003-15 variant.
- **Night leg:** no new S1/S2 size-ups beyond the NX decision; discount any 2021-26 night expectation by ~4bp/trade
  for survivorship.
- **Insiders:** keep the ID3/EV2 shadow forward; H-POOL's 2008-15 PASS is a crisis-tilt validation, not grounds to
  deploy or size. Gate remains ~60 live fills / live auction cost.
- **Risk plan:** keep the -25% halt; treat the -10% leverage gate as the binding constraint in a 2000-02-style
  regime.
- **Structural events:** do not open a study; the class fails the research-priority gate (gap + small).

## Every path holding Sharadar data or derived caches

Vendor data (never committed; `.gitignore` blocks `data/`, `*.parquet`, `*.zip`, `*.csv`, `.env`):
- `~/data/sharadar/` — the primary store, 3.2GB: `actions, daily, descriptions, events, fundamentals, funds,
  holdings, holdings_investor, holdings_ticker, insiders, manifest.json, metrics, sp500, stocks, tickers`.
- `~/Downloads/sharadar-backup/` — the requested navigable backup copy (3.2GB, 15 entries).
- `~/Documents/Code/Projects/sharadar-data/` — loader code only (no data in-repo); its `.env` holds
  `SHARADAR_API_KEY` (secret, gitignored). `.venv` and `.pytest_cache` hold no data.

Derived caches (gitignored under `data/research/`):
- `data/research/nx/cache_SEP.parquet` (~640MB), `cache_SFP.parquet` (~160MB), `cache_ACTIONS.parquet`,
  `cache_TICKERS.parquet` — the NX study's ingest-window caches (pre-existing NX infrastructure, not created by
  this session's studies); sentinels `run_done.json`, `validate_passed.json`.
- `data/research/nx_run.log`, `data/research/nx_validate.log`; `data/research/program/nx_out.txt`.
- No `data/research/sharadar_derived/` was needed: the four studies read the store directly with date/column
  filters and wrote no new caches. If the nx caches are to be relocated per the standing rule, they should move to
  `data/research/sharadar_derived/` and `nx.py`'s cache path updated (not done here — it would force a rebuild).

Result text only (no raw data): `research/sim/{shar_ibs,shar_crash,hpool_sharadar,shar_surv,beta_alpha_iso}_out.txt`.
