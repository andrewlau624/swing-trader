# Research memory — mechanism loop (2026-10-17/18), `research/drafts/mech_loop_2026-10-17.md`

- KILLS: PCP-HTB (N 1019; conversion earns r - b, registration sign error disclosed; HTB chains far-side -78%/yr), BK-EMERGE-GV (N 1020;
  median -6.5%/120d, lottery), INCOME-SHOCK (N 1021; $25-par panic rule with PIT quality screen loses in 2008-07), TME via futures (access:
  commissions; Schwab IRA futures need $25k). Branches B-F (contracts, cross-asset, disclosures, obscure info, house margin): 0 cards.
- **INTL-PREF (N 1022): PASS** — PREF-EX on TSX $25-par prefs (WRDS Datastream tr_ds_equities, 2005-25, 999/1,166 delisted): CO net +32bp,
  issuer-clustered t 12, 21/21 yrs, 2023-25 +33.5; Yahoo matches Datastream 28/28. The ex-date under-adjustment is a property of retail $25-par
  paper, not US tax. Additive to US PREF-EX. Unverified: IBKR MOO fills at the TSX open, Roth Canadian withholding (0% vs 15% = ~6-9 vs ~2-3%/yr
  at $10k). Prototype `research/sim/intl_pref_shadow.py` (`make intl-pref`, log-only, local, not deployed).
- Data: WRDS FISD fisd_ratings/fisd_rating_hist = PIT issue-level ratings (the "no free PIT ratings" line was wrong at issue level).
  Datastream on WRDS has international raw prices + ds2div ex-dates: untouched markets for any mechanism.
- Arrears catch-up ex-nights (G2): 9/9 positive, +4.8%/event, ~1/yr, thin: log-only candidate (PREF-EX y<=4% filter excludes them).
- Round 3 (10-18), branches J-N + INTL-PREF diligence (ledger mech_loop_2026-10-17.md): J intl income paper = ex-date under-adjustment
  corroborated in JSE (+169bp, drop 0.61) and Stockholm prefs (+62bp) but ceilings ~1.5pp each; ASX hybrids dead (0.91, franking).
  KILLS: K delisted $25 paper (2 events/11y, move in the gap), L special-event pref calls (exercises were on above-par paper),
  M Japan yutai (over-drop real, no recovery), N CEF-pref 200% coverage floor (never bound; 2020 = beta). INTL-PREF at IBKR:
  ~+5.6pp/yr at $10k if Roth gets 0% WHT (Article XXI, IBKR handling unknown), ~+1.9pp at 15%; small tickets cost 10-20bp RT.
  TSX no-open-trade prints = prior close (3.4% of ex events; bias ~1.4bp); shadow scores them at the close.
  The $25-par/income-paper neighbourhood is now saturated: next branches must leave it.
- **USER RULING 2026-10-18: Schwab only.** No new brokerage accounts; international markets are out (INTL-PREF, JSE/SE prefs, TSX,
  IBKR unlocks all ACCESS-KILLED). Research only US-listed instruments tradable at Schwab (taxable margin + Roth). Do not re-propose IBKR.
