# Studies Lab-AZ / Lab-BB / Lab-BC — Nasdaq closing imbalance (Databento NOII), intraday: real signal, not tradable

Data: Databento XNAS.ITCH `imbalance`, closing-cross messages 15:50-15:55 ET, the top 100 Nasdaq-listed common stocks by
Nov-Dec 2021 dollar volume plus QQQ/TQQQ, 1,190 sessions 2022-01 .. 2026-09. **Cost $64.88** of the user's $125 free
credit. Entry: Alpaca SIP NBBO at 15:54:31. Exit: market-on-close = the official close.

## Lab-AZ (Lab Round 24): UNTESTABLE as registered
The rule needed Nasdaq's near indicative price at 15:54:30. Nasdaq publishes near/far prices only from 15:55 (the early
15:50-15:55 messages carry size, side, paired shares and the reference price), so: 0 trades. A registration error
(MISTAKES.md). After 15:55 a retail account can no longer send market-on-close (Nasdaq's cutoff), so the near
price is unusable for this exit anyway.

## Lab-BB (Lab Round 26): DEAD — the side is informative, the spread is bigger
r = signed imbalance / paired shares at 15:54:30; long the top 5 with r > 0, short the bottom 5 with r < 0.

| variant | n | gross (mid -> close) | 1x net (t) | H1 / H2 1x | 2x | without top 20 | placebo |
|---|---|---|---|---|---|---|---|
| Lab-BB1 long+short | 10,878 | **+3.4bp** | −1.3 (t −4.0) | −1.4 / −1.1 | −6.0 | −1.6 | 100 |
| Lab-BB2 long only | 5,456 | +4.1bp | −0.7 (t −1.1) | −0.1 / −1.4 | −5.4 | −1.2 | 100 |

The mean entry spread at 15:54 is 7.5bp (median 5.1; p90 15.2).

## Lab-BC (Lab Round 27): DEAD on the holdout — the dose-response replicates, the margin does not
Designed on H1 only: the gross rises monotonically with |r| (quartiles −1.9 / +2.6 / +3.6 / +7.0bp). Rule: Lab-BB1 with
|r| >= 1.6742 (H1's 75th percentile). Judged on H2 only.

| | n | gross | 1x net (t) | 2x | without top 20 | placebo | by year (1x) |
|---|---|---|---|---|---|---|---|
| **H2 holdout (judged)** | 1,130 | **+6.3bp** | +0.3 (t 0.26) | −5.7 | −1.7 | 100 | 2024 +0.7, 2025 +0.9, 2026 −1.1 |
| H1 (in-sample) | 1,428 | +7.0bp | +2.1 (t 2.1) | −2.8 | +0.5 | 100 | 2022 +5.5, 2023 −0.3 |

## Reading
- **A real, stable signal: a big early closing imbalance predicts ~6-7bp of the move from 15:54 to the close, out of
  sample.** Market-taking entry at 15:54 pays about all of it.
- Ways it could still pay (none tested; each would be a new registration):
  1. **Use it where the trade is already paid for.** The night leg buys in the closing cross anyway, so a buy
     imbalance means a worse entry print. This is main Study BD's question; the finding was sent to that session.
  2. **Passive entry** (a limit at the touch). That needs queue modelling on tick data and has adverse selection.
  3. **Cheaper instruments only** (QQQ: H1 +2.1bp gross, n 62; too few).
- Nothing to build.
