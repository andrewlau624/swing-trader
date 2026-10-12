# Roth book equity drop 10-05: not a bug (manual trade)

Verdict: no accounting bug. Schwab transactions (read-only API) show a non-bot BUY of $857.30 in the Roth at 2026-10-05 09:40:40 ET
(13:40:40 UTC), between the 09:16 open run and the 09:50 reconcile, and a non-bot SELL of $716.21 on 10-06 10:35 ET (14:35 UTC).
Account total stayed flat because cash became a position.

Mechanism: `executor.free_equity` (executor.py:1600-1611) = liquidationValue - market value of broker positions the book does not own.
`_sync_live_cash` (executor.py:1418-1427) sets book.cash = min(free, cap) - own positions. Free was ~1,385 (capped to 1,000) before;
the $857 foreign buy took it to ~528 (equity 470.8, cash 69). The bot's cash really was spent by the manual buy.
The 10-06 10:35 sale (+716) lifted free back above the $1,000 cap (log: 15:01 UTC 472 -> 1,000.00). The 10-06 account drop (-$895) was a
bank-sweep journal, unrelated.

Hypotheses ruled out: fills were credited (7 night sells + SGOV 4 @100.45 in daily-fills-roth.jsonl, state cash 598 after recovery = 804+195-402);
no double debit; no dropped positions.

Other occurrences: scan of all daily-roth/daily-live logs for >20% book-equity jumps: only 10-05 and 10-06 Roth (this event) and the live
book 10-06 15:01 (+$1,000 deposit, genuine).

Impact: 10-05 15:40 skips SPCG (2 sh), SECZ (1 sh) by the <$500 free floor, ACMR (cash exhausted); roth-cash funded $35 of $71;
day-trade leg shadow on 10-06 morning (equity 472 < min) until 10-06 ~11:01 ET. All small (<$100 of buys).

Fix: none written. Optional design change: free_equity treats manual Roth buys as reducing bot cash by design; log the foreign total
in the book line so this is visible. No branch created.
