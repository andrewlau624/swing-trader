# Research memory — session "frontier reset: margin data + CEF-TL2" (2026-10-06, evening 3)

- CME margin-rate history probed four ways (web+ftp+wayback): NOT free-reachable; margin-hike
  forced-deleveraging stays DATA-LIMITED. Do not re-probe without new credentials/clean IP.
- **CEF-TL2 (N 863->864): REJECTED (net)** — 1,156 delisted-complete CEFs 1999-2025: Jan Q1-u gross
  +2.72% t 3.28 (22/27 yrs+, ex-best +2.31), net +0.13 t 0.27 at 30bp; Dec leg wrong sign.
- **CLASS-verdict: December-loser January bounce = real GROSS seasonal, cost-bound at retail
  (panels: stocks t 1.91, CEFs t 3.28). Closed at prices-only data forever.**
- **PREF-EX execution attack (2026-10-06): size claim halved, edge intact.** At 5% of auction $ and 10bp round trip: CO
  $232/yr at $1k, $456 at $3k, $585 at $5k, $789 at $10k, $919 at $25k (dollars plateau: capacity binds above ~$5k).
  CO dies if the open leg misses the auction (half-spread 44bp); Schwab has no MOO (directed routes refused; AUTO pre-open
  sells hit the official open for liquid names only so far); CC (MOC both legs) is the Schwab-safe form (~60-70% of CO).
  Shadow live on him (`pref_ex_shadow.py`, REGISTRY, 60 ex-nights). Next: one tiny live Roth test order (user decision).
- **ETDX (2026-10-06, N 869): PASS** — PREF-EX rule on baby bonds (SFP ETD) + CEF preferreds: official 2021-26 ETD CO
  +44bp / CC +39bp, 28/29 yrs. Mechanism = dividend-proportional under-adjustment surviving only in $25-par income paper (THN: thin commons had it pre-2021 regardless of tax status, ~0 since; tax is contributing, not proven). Lifts the Roth plateau ~1.5x ($1.1k/yr at $10k, $1.4k at $25k
  CO). Logged in the same shadow (cls "etd"). **FXD KILL** (CEF/ETF ex-nights decayed to <10bp since 2020). SFP dividends
  can be split-adjusted vs raw prices: guard against y(closeadj).
