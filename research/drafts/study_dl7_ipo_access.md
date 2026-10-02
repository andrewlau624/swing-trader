# Discovery DL7: IPO allocations through retail IPO-access platforms, a bound (deal rule, no N) — DEAD

Session llm-trader-c5, 2026-10-02. Registered in `round1_prose.md` ("deal rule DL7", 467d43e) before any price.
Script `research/sim/ipo_access.py`; deals `data/research/events/ipo_access_deals.csv`.

**Mechanism (F, queueing).** Retail platforms get a slice of IPOs at the offer price; allocations aren't public and
shrink in hot deals (winner's curse). 502 operating-company IPOs 2019-26 (424B4 "initial public offering price of
$X", X >= $4, no SPACs/units/ADSs/funds, bars from the debut).

| fill model | deals | 30-session return: mean | median | hit | 1st close: median | $/yr at $500/deal |
|---|---|---|---|---|---|---|
| optimistic: every deal filled | 502 (67/yr) | +26.5% | +14.6% | 63% | +14.8% | +$8,871 (not attainable) |
| **pessimistic: filled only when the open <= 1.10 x offer (registered verdict)** | 212 | **−4.1%** | **−7.4%** | **40%** | −4.8% | **−$573** |

Pessimistic median by year: 2019 +2%, 2020 −11%, 2021 −6%, 2022 −17%, 2023 −29%, 2024 −3%, 2025 −20%, 2026 −8%.
**Verdict (pessimistic median > 0, mean > 0, hit >= 55%): DEAD.** The deals retail can actually get filled in (cold
debuts) lose ~7% over the platforms' 30-day no-flip window. The +15% "IPO pop" sits in the hot deals that allocate
little. The truth is between the two lines, and without allocation data it can't be shown to be positive.
