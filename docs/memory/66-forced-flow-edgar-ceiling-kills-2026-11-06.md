# Forced-flow EDGAR families (2026-11-06, no N): ceiling-kills beside CEF-RIGHTS

- Already in ledgers, not re-run: CEF/BDC NAV tenders pro-rata (study_cpc 1.3pp, after-tax -0.2pp), odd-lot/Dutch odd-lot
  (ABANDONED), B3 cash tenders, B4 going-private, MERG-CASH, SPIN-CHILD (N 840).
- Dutch non-odd-lot tender arb ~3-4pp at $10k with cash locked weeks: CEILING-KILL. Mandatory-convertible conversion dates
  < 7.5pp, hedged arbs net zero, no deal table: CEILING-KILL/DATA-LIMITED. Spin-off orphan delayed entry needs >= +4%/event vs
  SPIN-CHILD -1.0%: CEILING-KILL. Appraisal: untradable.
- Server state/forced-flow-discovery.jsonl (1,002 rows) scans tender/round-up text in 8-K/S-4/SC TO; it has no rights family.
- Not tested with data: all four above (no backtest); spin child entry after the S&P deletion effective date.
- No family survived, so no generic EDGAR event scanner was built (cef_rights_fetch.py is the per-fund census pattern if needed).
