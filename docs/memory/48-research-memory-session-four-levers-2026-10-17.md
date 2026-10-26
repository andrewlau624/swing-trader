# Research memory — session "four levers" (2026-10-17)

- **TAX-STACK (N 1017): PASS-SMALL, tax- and cost-fragile.** PREF-EX/ETDX + CEF-RV + BIL on the taxable book's idle cash
  (live nx_s2), 2021-26 (touched: economics, not OOS). Added after-tax %/yr, cash-only / margin-to-2x: +8.1/+15.9 at $2.3k,
  +4.4/+7.5 at $10k, +2.6/+3.6 at $25k, ~+0.9 at $100k; halves both positive. Holds ONLY if the ex-date price drop is a
  short-term loss that offsets the book's ST gains (view A); if not (wash-sale deferral on monthly payers re-bought <30d,
  view B) it is ~-18pp at $10k. 3x cost leaves +0.6pp at $10k. Unverified: Schwab marginability of preferreds/baby bonds,
  the 12.5% margin rate, wash-sale treatment. `research/sim/tax_stack.py`, `tax_stack_out.txt`. Not deployed: a tax-advice
  check and the PREF-EX live 30-trip cost gate come first.
- **PROVOL (no N): CEILING-KILL.** Night-leg size-up on high-vol days: NDISC already scanned rv20 / vix_pct252 (signs flip
  between halves); ceiling ~+1.2pp at honest capture. Sizing conditioning on the night leg is closed.
- **Tax placement memo** (`research/drafts/tax_placement_2026-10-17.md`, no N): the current split is near-optimal; the only
  gain is letting the Roth run IBS (wash_guard roth_first + SGOV parking keep it tiny): +1.4 / +2.1 / +2.5pp after tax at
  now / $10k / $25k combined (model; cause of the suppression inferred, not read from executor code). User decision.
- Shadow status 10-17: OVN-MOM 2/120, CEF-RV-FWD 0/60 (12 open), PREF-EX shadow 4/60, PREF-EX live 0/30 (orders from 10-21),
  split 1/40. events.py CPI/NFP calendar extended through 2027-12 (BLS pages, fetched 10-17). Program N = 1017
  (the 10-16 burst reused 1011-1015; numbering continues from PMX 1016).
- **SSR-LIFT-FWD shadow LIVE on him (2026-10-17, log-only, no N):** `swingtrader/daily/ssr_lift_shadow.py` in research-shadows
  (frozen rule: RTH low <= -10% on T, $10+, ADV20 >= $20M, no T+1 re-trigger; short T+2 open cross -> cover T+2 close cross,
  +1.5x SPY hedge; net = 5bp/side + 2bp borrow; Alpaca ETB flag at detection). Gate 60 forward event-days, net > 0, day-t >= 2.
  Local 20-session backfill +115bp net/event (raw short +214bp, median +233): a look-alike, NOT evidence. The research-shadows
  unit on him was re-rendered with absolute paths (was `~/llm-trader/`). Any live pilot = user decision.
