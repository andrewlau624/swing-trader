# Index-beat A1 / deal rule DL-IB1: the reverse-split round-up in more accounts (no N) — PAYS on history, CONDITIONAL

Rule registered 7da5578 (round1_prose.md "DL-IB1") before these numbers. Data: B1's deal file
(`data/research/program/roundup_deals.csv`, built by `research/sim/roundup.py`); nothing new was fetched.

## Per account (1 share per qualifying split; 2026 annualized from the data's 2026-09-18 end)
| year | qualifying deals | mean / median $ if rounded | $ per account if rounded | $ if cash in lieu | worst |
|---|---|---|---|---|---|
| 2022 | 19 | 4.69 / 3.89 | $89 | −$1 | $0.00 |
| 2023 | 69 | 4.38 / 3.51 | $302 | −$1 | +$0.42 |
| 2024 | 91 | 4.18 / 3.18 | $380 | −$3 | +$0.63 |
| 2025 | 69 | 4.45 / 3.86 | $307 | −$0 | +$0.02 |
| 2026 (ann.) | 105 | 4.28 / 3.72 | $449 | −$3 | −$0.00 |

2024-26: **$371/yr per account** ($336 without the 5 best deals). Capital per deal: median $0.25, p90 $0.67, max $3.68.
Issuer adaptation (share of round-up filings saying "participant level", skipped): 2023 25%, 2024 21%, 2025 43%,
2026 37%. Qualifying deals did not fall (2024 91 -> 2026 ~105). The rule's PAYS test: mean > 0 if rounded (yes),
>= $150/yr per extra account 2024-26 (yes, $371), 2026 qualifying deals >= half of 2024's (yes). **PAYS (deal rule) —
CONDITIONAL on Schwab paying the round-up to a 1-share holder, which history cannot show.**

## Money (per extra account, if rounded)
| | $2.3k | $10k | $25k |
|---|---|---|---|
| +1 extra **Roth** IRA (tax-free; funded with ~$50 of the $7.5k limit) | +$371 (+16%) | +$371 (+3.7%) | +$371 (+1.5%) |
| +1 extra taxable account (35% ST) | +$241 (+10%) | +$241 (+2.4%) | +$241 (+1.0%) |
| +3 extra Roth IRAs | +$1,113 (+48%) | +$1,113 (+11%) | +$1,113 (+4.5%) |
$100k / $500k: the same flat $371 per account (0.4% / 0.07%): a pure small-account edge.

## Why it might be real / what would kill it
- Who pays: the issuer's other holders (a few $ of dilution per round-up); issuers round up to keep small holders and
  skip a cash-in-lieu process. It is a known retail practice (multi-broker "reverse split arbitrage"); the payoff per
  deal has not shrunk (mean $4.18-4.45 every year), but more issuers now round at the participant level.
- Kill: Schwab pays cash in lieu to 1-share holders (VIVK, ex 2026-10-05, check ~10-07, decides it; the live kill
  switch stops an account after 2 cash outcomes); issuers moving to participant-level rounding faster; an issuer
  excluding holders who bought after the announcement.
- Automatable: yes after a small live-code change (roundup_orders already loops `ROUNDUP_ACCOUNTS`; `make_adapter`
  needs to accept extra Schwab account numbers). One-time manual step: open the accounts (~10 min each) under the same
  Schwab login so the Trader API token covers them. **Not built (research-only rule); spec only.**

## Verdict
**Not FOUND yet** (DL-IB1 says so: 2 live rounded deals first). If VIVK comes back rounded in either account, this is
the single cheapest money in the program at $2.3k: each extra Roth IRA is ~+16%/yr of today's taxable balance, flat.
NEXT line: "DL-IB1 (index beat): B1 round-up in more accounts PAYS on history ($371/yr per account 2024-26, tax-free in
an extra Roth IRA); conditional on VIVK rounding (~10-07); then: extra Schwab Roth IRAs + ROUNDUP_ACCOUNTS."
