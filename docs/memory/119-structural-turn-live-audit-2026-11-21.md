# Structural turn + live audit (2026-11-21)
- U9 RSPLIT-LONG (N 1258) KILL: reverse-split ex-date night long, 1998-2012 median -72bp t -2.37. Data rule: drop reverse splits paired with a same-day spin-off.
- U7 ARK-COPY (N 1259) KILL: +15bp gross t 3.3, -4bp net, the move is in the gap. Data: arkfunds.io API (free), copy in data/research/ark/.
- Tier C: ETF creation/redemption data was never blocked (SSGA navhist, Study EF); ceiling-killed 3.8pp. Newly free: CME margin PDFs 2003+, SEC 17g-7(b) rating histories 2015+.
- Round-ups at Schwab: 2 of 17 account-deals rounded up, 15 cash in lieu, net -$0.05. The family is ~$0 at this broker. GTC adds nothing. Scanner false-negative bugs fixed.
- Live audit: night +25.6bp/trip vs +26 expected (t 0.93), cost ~0. `_check_exit_cost` 403 bug 11-10..11-20 fixed in `official_crosses` (end capped at now-16min). CEF-RV held value starves the Roth night cash (executor.py:1137-1141). The PREF-EX gate needs a scoring decision before trip 30. Decisions are in NEXT.md "LIVE-AUDIT 2026-11-21".
