# DL-G27: mutual savings bank conversions bought at $10 as an eligible depositor: PAYS on its history, but it can't be automated

Goal hunt, session llm-trader-ec, idea G27. Deal rule registered in `round1_prose.md` (DL-G27, no N) before any post-IPO
price was looked at. Runner `research/sim/goal_dl27.py`; deals in `data/research/program/goal_dl27_deals.csv`.

**Events.** S-1s with "plan of conversion" + "subscription offering" + "eligible account holders" (EDGAR FTS, 2016-26):
roughly 7-12 issuers a year. 18 of them have a current ticker with Alpaca bars and first traded after their S-1.
- Excluded on purpose: second steps whose old minority shares were already trading (the first run wrongly counted those
  bars; fixed before writing this up).
- Missing: 2016-18 issuers that have since been acquired or delisted. That is survivorship, but acquired thrifts usually
  did well.

**Payoff (buy at $10, tier cost on the sale):**
| exit | n | mean | median | hit | worst | best |
|---|---|---|---|---|---|---|
| first day's close | 18 | +19.0% | **+21.2%** | **83%** | −9.2% (CPBI 2023) | +50.7% |
| 20th session's close | 18 | +19.9% | +26.1% | 78% | −19.0% (SRBK 2023) | +54.0% |

By year (day 1, median): 2019 +36% (1 deal), 2020 +21% (1), **2021 +29% (7)**, 2022 +33% (2), **2023 −2.5% (4)**,
2024 +10% (2), 2025 −0.7% (1). The payoff comes from the conservative regulated appraisal, but it was weak in 2023-25.

**Verdict: PAYS as registered** (median > 0, hit >= 60%, worst > −30%), **but it fails ">= 5 deals a year" on the deals with
data (~2.6/yr), and it is not a strategy the server can run:**
- Eligibility needs a deposit account at THAT mutual before its eligibility record date, typically 1-2 years before the
  offering. You can't know far ahead which of ~400 mutuals will convert.
- Many mutuals open accounts, or run the community offering, only for residents of their state or county.
- Hot deals are oversubscribed and prorated above a minimum. A $2,000 order from a small depositor is often filled, but
  that isn't guaranteed.
- If eligible: $2,000 x ~+20% = ~$400 a deal. Two eligible deals a year would be ~$800 (~+35% at $2.3k, +8% at $10k).

**What to do with it (the user's call, a human project, not a bot feature):** open small savings accounts ($50-100 each)
at mutual savings banks that accept online, out-of-state applicants, then wait. This hunt doesn't build anything for it.
If wanted, the screen is: EDGAR Form AC / S-1 "plan of conversion" filings, plus the FDIC list of mutual institutions.
