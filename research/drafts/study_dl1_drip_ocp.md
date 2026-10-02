# Discovery DL1: DRIP optional cash purchases at a fixed 5% discount (deal rule, no N) — PAYS

Session llm-trader-c5, `prompt_discovery_loop.md`, 2026-10-02. Rule registered in `round1_prose.md` (amendment "deal
rule DL1", commit 2f57a54) before any number. Script `research/sim/drip_ocp.py`; deals
`data/research/events/drip_ocp_deals.csv`.

**Contract.** UMH Properties' Dividend Reinvestment and Stock Purchase Plan sells new shares to optional cash
purchasers at P = max(0.95 x 4-session mean of (high+low)/2, 0.95 x (high+low)/2 on the Investment Date), the 15th of
each month. $500 minimum, **$1,000/month cap** (was $5,000 until 2021-02-11); waivers above the cap are at UMH's
discretion. A street-name holder may use the OCP by certifying ownership (plan Q4). The issuer pays the discount to
raise ~$6M/yr cheaply; the cap is what keeps arbitrage funds out (Scholes & Wolfson 1989 documented funds farming these
discounts in the 1980s until plans added caps). **The cap only binds above $1,000/month, so this is a small-holder
edge.** Monmouth REIT (MNR) ran the same template until the ILPT merger (2022-02).

**Who else.** ~90 issuers mention an OCP discount, but almost all are "0-5% at our discretion, may change monthly"
(Chatham, Hannon Armstrong, ONEOK, NNN, INDB, Old National ...); those monthly rates are not filed, so they can't be
simulated. York Water's and TDS's 5% apply to reinvested dividends only.

## Result (registered rule: $1,000 each month at P, sell at the official close 5 sessions after the ID)

| | months | mean / month | median | hit | worst | best |
|---|---|---|---|---|---|---|
| **UMH + MNR, exit ID+5 (registered)** | 203 (2016-01 .. 2026-09) | **+$47.40** | +$52.28 | **93%** | −$202 | +$161 |
| exit ID+1 (info) | 203 | +$48.87 | +$49.75 | 99% | −$63 | +$130 |
| exit ID+10 (info) | 203 | +$56.75 | +$55.29 | 92% | −$84 | +$240 |
| UMH only, ID+5 | 129 | +$45.09 | | 91% | | |

By year (ID+5 sum): every one of 11 years > 0 (2016 +$1,637 with two plans … 2023 +$236, the low, 2025 +$640).
The effective discount to the ID close is 4.4% mean (the "higher of" clause gives back ~0.6pp). **Verdict by the
registered rule (mean > 0, hit >= 60%, >= 2/3 of years > 0): PAYS.**

## What it is worth (one person; the cap is per participant, so the dollars are the same at every balance)

| | $2.3k | $10k | $25k | $100k / $500k |
|---|---|---|---|---|
| UMH only: 12 x ~$45 = **~$540/yr** | **+23%** | +5.4% | +2.2% | +0.5% / 0.1% (capped) |

Capital: $1,000 for ~3 weeks a month (cash must reach the agent before the 15th; shares then move to Schwab). It
competes with the book for ~$1k at $2.3k; in the taxable account it can sit on margin. **Not the Roth**: plan accounts
at the transfer agent are personal (taxable) registrations. Taxes: short-term gains; the IRS ruling in the plan says
an OCP-only participant is not taxed on the discount as a distribution.

## Caveats
- **One issuer.** UMH can cut the discount or end the plan at any time ("UMH reserves the right to terminate the Plan").
  The 2021 cap cut from $5,000 to $1,000 shows it watches usage.
- Execution: the cash is committed before the price is known; the exit needs a DRS transfer from Equiniti/AST to
  Schwab (free at Schwab, ~3-7 business days) or a plan sale (fees would eat ~half the gain). The ID+10 line shows a
  slower transfer costs nothing on average; the worst month (−$202) was a 5-day drop of ~20% in 2020-03.
- Raw bars, no dividends added; UMH ex-dates sometimes fall inside the hold (conservative).
- ~15 min a month by hand (one ACH on the agent's site, one DRS transfer request). Under the 30-min rule.

## Spec for an alert (don't build here)
Monthly reminder on the 8th: "UMH OCP: send $1,000 to Equiniti by the 12th; on the 16th request DRS transfer of last
month's shares to Schwab; sell at the close when they land." Check UMH's 10-K/plan supplements each quarter for a
change to the 95% / $1,000 terms (an FTS on "UMH" + "optional cash payments" in 424B3/S-3D); kill if the discount
goes below 3% or the plan ends. Also: look at Chatham (CLDT), Hannon Armstrong (HASI), ONEOK (OKE), NNN, Old National
for a currently announced OCP discount on their plan pages (forward-only, the history isn't filed). Digest line:
month, shares, price, exit close, P&L.
