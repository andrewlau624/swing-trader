# Tor Intelligence — Ranked Recommendations

Discovery date: 2026-10-16

## Scored discoveries

Scoring per mission weights (0-100). No discovery cleared the bar; scores are recorded to close the
direction, not to rank anything actionable.

| candidate | enabling new hypotheses (25) | novelty vs repo (20) | accessibility (15) | econ plausibility (15) | impl. feasibility (10) | verifiability (10) | cost (5) | **total** | verdict |
|---|---|---|---|---|---|---|---|---|---|
| Tor `.onion` financial datasets | 0 | 0 | n/a | 0 | 0 | 0 | 0 | **0** | REJECT (unlawful/nonexistent) |
| Tor "AI trading bot" tech pages | 0 | 0 | 0 | 0 | 0 | 0 | 0 | **0** | REJECT (scam/spam) |
| Dead v2 crypto-research mirrors | 0 | 0 | 0 | 0 | 0 | 0 | 0 | **0** | REJECT (dead, clearnet duplicate) |
| Ahmia bulk onion corpus (15,529) | 0 | 5 | 15 | 0 | 5 | 5 | 5 | **35** | not pursued — no financial content on inspection |

## Recommendation: DO NOT pursue the Tor direction further.

The Tor route is closed. It delivers no data, no technology, and no mechanism, and its financial
content violates the mission's own legality filter. Recorded here so future sessions do not repeat it.

## Where the effort should actually go (unchanged from the existing frontier)

The binding constraint is **data access**, not idea generation (CLAUDE.md, NEXT.md). The highest-value
next moves, all $0 or already-funded:

1. **Reconcile the DATA-LIMITED rows against WRDS before buying anything.** ✅ **DONE 2026-10-16**
   (`research/drafts/wrds_recon_2026-10-16.md`, `data/research/wrds_recon/`). Result: borrow-rate
   (`optionm.borrate`), signed-gamma OI (`optionm.opprcd`), vol surface (`optionm.vsurfd`), and
   per-fund daily NAV/shares (`crsp_q_mutualfunds.daily_nav`/`monthly_tna`) are **already licensed at
   $0** — the prior "blocked/paid" status was a source assumption, not a WRDS check. PIT ratings and
   margin-rate history remain blocked (sample only / absent). Next: pre-register one study on the
   borrow-rate state.
2. **Borrow / HTB / recall history** — the one named counterparty (short sellers) with no data; not in
   WRDS (no Markit lending). Still the top genuine gap.
3. **Clearnet obscurity hunt** (the lawful substitute for this mission): government open data
   (shipping/AIS, energy inventories, procurement), academic mirrors, and any free PIT-capable source —
   scored against the +8pp ceiling gate before any code is written.
4. Keep the four forward-validation candidates (OVN-MOM, CEF-RV, PREF/ETD-EX, CPC) running; nothing
   from Tor touches them.

## Cleanup note

The Tor client is now installed and running as a background service (`brew services`). It was needed
only for this one-time survey. Stop/remove if unwanted:
```
brew services stop tor
brew uninstall tor torsocks
```
