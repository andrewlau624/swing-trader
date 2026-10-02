# Round 31 #11: odd-lot priority in issuer tender offers (a report, no N)

Script: `research/sim/tender_report.py` (`snippets`, `report`), fetch `research/sim/tender_fetch.py`. Output:
`data/research/program/tender_oddlot_out.txt`; per-deal table `data/research/night/tender/oddlot_trades_rule.csv`.
No statistical test: the payoff is contractual. The question is how often it pays and how much.

**Forced trader.** In an issuer tender offer that is oversubscribed, every holder of 100 shares or more is
prorated. Final factors here ran 4.7-27%, so big holders sell only a slice at the tender price and keep the rest at
the post-offer price. Holders of 99 shares or fewer who tender all of them are bought first, in full, when the
offer grants odd-lot priority. A small account can buy up to 99 shares below the guaranteed price and tender.
Schwab charges $0 for voluntary reorganizations (April 2026 pricing guide; it was $39 until ~2022).

## Data
- EDGAR full-text search for "odd lot" in SC TO-I / TO-I/A, 2016-01 .. 2026-09: 193 issuers with an exchange
  ticker, 352 offers. Terms were read by four subagents from the offers' own sentences (`terms_*.csv`), and odd-lot
  priority was re-checked by regex on each offer's text: an explicit grant, and not "odd lots are still subject to
  proration".
- Prices: Alpaca raw daily closes. Entry A = close of the first session after the SC TO-I. Entry B = close 5
  sessions before the last filing (a few sessions before expiry). Cash ~2 sessions after the last filing. A 12%/yr
  financing charge is shown, which is conservative.

## Results

| subset | deals (per yr) | gain mean / median | worst | > 0 | hold | $ per deal (<= 99 sh) |
|---|---|---|---|---|---|---|
| **cash (fixed or Dutch), odd-lot priority, guaranteed floor >= +1% over the entry close, entry B** | 14 (1.3) | **+12.1% / +5.5%** | +1.3% | **100%** | 10 days | **$149** (median capital $936) |
| same, entry A | 15 (1.4) | +8.7% / +6.3% | +1.2% | 100% | 36 days | $93 |
| cash Dutch with priority, any floor, entry B | 47 (4.4) | +0.7% / +0.5% | −21% | 64% | 10 days | −$89 |
| closed-end-fund NAV tenders | 55 | +6% median **but 54 of 55 give odd lots no priority** (BlackRock's 2024-25 98%-NAV series; Calamos says odd lots are prorated) | — | — | — | not an odd-lot edge |

The floor is the fixed price, or the bottom of a Dutch range: an odd lot tendered "at the purchase price" gets the
clearing price, which is at least the low end. With that rule, every deal made money. Without it, Dutch offers are
a coin flip.

## What it is worth (per person: the 99-share limit counts all of an owner's accounts together)

| | $2.3k | $10k | $25k | $100k / $500k |
|---|---|---|---|---|
| deals/yr x $/deal | ~1.3 x ~$120-150 = **~$150-200/yr** | same dollars | same dollars | same dollars: capped by 99 shares |
| %/yr | **~+6-9%** | ~+1.5-2% | ~+0.6-0.8% | ~0 |

Capital is ~$900 for ~10 days per deal (entry B), so it barely competes with the book. In the taxable account it
can sit on margin. In the Roth it displaces ~10 days of night/IBS money on ~$900 (about $10 of book return).

## Caveats
- ~1-2 qualifying deals a year, and lumpy: 2020 +38% and 2026 +57% are single deals.
- Tendering is a manual Schwab election (an online voluntary-action form or a call) with an odd-lot certification.
  The bot cannot do it through the API.
- An offer can be terminated or amended. None in the qualifying set were, but then the shares are simply held and
  sold at market.
- Terms come from agent-read sentences plus a regex check, not from every full document. A wrong final price
  shifts one deal, not the sign.
- Not a test, so no N. It is contractual arbitrage, not a forecast.

**Verdict: worth doing at the current balance, by hand, with an alert.** `make tender-watch` (Round 31) scans each
day's new SC TO-I filings for an odd-lot-priority cash offer whose floor is above the market, and logs it.
