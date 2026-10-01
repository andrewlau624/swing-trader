# Studies Lab-CB / Lab-CC — Cboe sentiment as a 20-day market predictor (Lab Round 50; program N 742 -> 744)

Script `daytrade/research/cb_replay.py`. Forward 20-day market return (French daily, t+1..t+20) on signal days
(z >= +1 vs the trailing 252 days) minus other days; Newey-West t (20 lags).

| study | signal days | diff, half 1 | diff, half 2 | all | NW t | verdict |
|---|---|---|---|---|---|---|
| Lab-CB equity put/call, 10-day mean high (fear) -> higher | 555 of 2,993 (2006-11..2019-10) | +49bp (2006-12) | +58bp (2013-19) | +54bp | **0.9** | **DEAD** |
| **Lab-CC SKEW high -> lower** | 1,886 of 8,946 (1990..2026-08) | **−30bp** (1990-2007) | **−110bp** (2008-26) | −75bp | **−2.34** | **PASS** |

## Reading
- **Put/call:** the contrarian sign is right in both halves but noisy (t 0.9).
- **SKEW:** when Cboe's SKEW is a standard deviation above its trailing year (option prices imply more crash risk),
  the next 20 days averaged 75bp less than other days. It held in both halves and was stronger since 2008.
- **Caveats:**
  - t −2.34 is marginal at program N 744 (a deflated Sharpe would be low).
  - Signal days cluster (z >= 1 regimes last weeks), so the effective sample is far smaller than 1,886.
  - It is a 20-day MARKET effect, not a cross-sectional edge.
- **Use: a sizing input for the main program's legs** (e.g. less overnight/intraday beta when SKEW is high), not a
  standalone book: timing the index already loses on return. Handed to the main session; nothing built in the lab.
  A forward log is cheap: Cboe publishes SKEW daily.
