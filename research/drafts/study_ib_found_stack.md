# Index-beat FOUND (track C, structure): the book stacked on index beta in both accounts

Session llm-trader-ee, 2026-10-02, `prompt_index_beat.md`, bar 3 ("a change that needs no new edge, worth >= +2pp/yr after
tax on the combined plan, computed exactly with the repo's tax code, both halves"). Scripts `research/sim/ib_r65.py`,
`research/sim/ib_r82.py`; outputs `data/research/program/ib/r65_*.txt`, `r82_out.txt`, `r82_checks.txt`.

## What it is
- **Taxable:** hold SPY at 1.0x and run every live leg on top of it: noise intraday, night + IBS overnight on margin.
  The mean overnight debit is 0.40E, charged 12%/yr (−4.8%/yr). (R6-5)
- **Roth (no margin):** 1/3 of the cash in UPRO (3x daily S&P, ~1.0x index beta) and the Roth book on the other 2/3. The
  Roth IBS never buys QQQ/SMH, because the taxable noise leg's loss sales would otherwise be permanently disallowed. (R8-2)

The bot no longer replaces the index; it adds its edge on top. It has to beat its financing cost (~5%/yr on 0.4x in
taxable; UPRO's decay and fees in the Roth), not SPY.

## The bar (after tax, edge-halves, combined money-weighted %/yr vs plan P = live taxable book + proposed Roth, G4s)
| cost | deposits | 2021-23 | 2024-26 | full |
|---|---|---|---|---|
| tier | $1k/mo | **+3.50pp** | **+11.09pp** | +8.96pp |
| tier | $2k/mo | **+4.03pp** | **+11.44pp** | +9.49pp |
| tier_hi | $1k/mo | **+3.88pp** | **+11.59pp** | +9.43pp |
| tier_hi | $2k/mo | **+4.29pp** | **+11.78pp** | +9.81pp |

Every cell clears +2pp: both halves, both deposit plans, both cost levels. Taxable tax comes from `taxable_frontier.after_tax`
for P. For the stacked account it comes from `ib_c2.c2_account`: legs taxed short-term at 35% yearly with an April payment,
carry-forward and the $3k deduction; SPY taxed at 20% when sold at the end. With the legs off, `c2_account` reproduces
`index_after_tax` to the dollar. The Roth is untaxed.

## Against the index itself (SPY in both accounts, after tax, tier, $1k/mo)
2021-23 **+5.29pp** (14.8% vs 9.5%), 2024-26 **+6.56pp** (24.4% vs 17.8%), full **+4.74pp** (20.0% vs 15.3%). At $2k/mo
the gaps are +5.12 / +6.64 / +4.44pp.

How much of the backtested edge must be real for the stacked plan to beat SPY in both accounts:

| edge kept | 2021-23 | 2024-26 | full |
|---|---|---|---|
| 100% | +16.2pp | +16.0pp | +15.1pp |
| 50% (plan) | +5.3pp | +6.6pp | +4.7pp |
| 25% | +0.2pp | +2.2pp | −0.1pp |
| 0% | −5.0pp | −2.1pp | −5.2pp |

**Break-even is ~25% of the backtested edge.**

## Risk
| | taxable, pre-tax 2021-26 (EH) | max DD | 5y MC P(DD>30%) / P(DD>50%) |
|---|---|---|---|
| SPY | 15.3% | −24.5% | 6% / 0.0% (taxable MC) |
| live book | 12.2% | −13.9% | 1% / 0.0% |
| stacked taxable | 22.1% | −27.8% | 16% / 0.3% |
| Roth book (EH) | — | −14.3% | 5% / 0.0% |
| Roth all-SPY | — | −24.5% | 11% / 0.1% |
| Roth 1/3 UPRO + 2/3 book | — | −24.0% | 12% / 0.1% |

**COVID (2020-02-19..03-23):**
- SPY: −33.5%.
- Stacked taxable: −37.5% max DD.
- UPRO: −76.5%, so the Roth's 1/3 sleeve alone takes about −25.5% before the book's −4%.

**2020 as a whole:** stacked taxable +51.4% vs SPY +13.2%. The crash risk is about the index's plus 4-5pp; it is not the
tail of the 1.5x profiles.

## Honest caveats (read these before switching anything)
1. **It is index beta plus the bot, not a new edge.** In a long flat or bear market for stocks it loses to the bot alone, and
   with less than ~25% of the edge real it loses to the index.
2. **It was built after looking.** It combines two structure looks, each tried alone first: R6-5 missed the 2021-23 bar at
   $1k/mo (+1.5pp); R8-2 alone missed in 2021-23 at tier. That makes k = 10 structure looks in this hunt (C1, C2, C3, C4, C5,
   R3-3, R6-5, R8-1, R8-2, the combination) and 0 book ideas judged. Track C needs no pre-registration and no N, and the
   mechanism is not fitted: no parameter was tuned, 1.0x beta and 1/3 UPRO are the natural choices. Still, treat it as a
   design choice whose live behaviour has to be watched.
3. **Margin.** Schwab house requirements on volatile night names can exceed Reg-T, leaving less overnight buying power than
   modelled.
4. **Intraday buying power.** The taxable account would be ~1.4x overnight and up to ~2.2x intraday (SPY 1.0 + noise ≤ 0.75
   + IBS), which needs the 2026 intraday buying power or smaller noise sizing.
5. **UPRO in the IRA** needs Schwab's leveraged-ETF acknowledgment and decays in choppy markets: the decay is inside its
   price history, and 2022 is included.
6. **Wash sales.** The Roth IBS must skip QQQ/SMH, which costs the Roth ~4% of its end value (included above).

## Money at three sizes (taxable, after tax, EH, pre-tax gaps x 0.65 where taxed; per year)
| | $2.3k | $10k | $25k |
|---|---|---|---|
| Stacked taxable vs live book: legs unchanged + SPY − ~4.8% interest | ~+$160 (+7pp) | ~+$700 | ~+$1,750 |
| Stacked taxable vs SPY: the legs at EH, net of interest, after tax | ~+$100 (+4.5pp) | ~+$450 | ~+$1,100 |

$100k / $500k: margin interest falls with Schwab's tiered rates, but the night leg stops scaling (Study V). The SPY core
scales without limit.

**5-year medians for the plan** ($2.3k + $1k/mo taxable, $8.5k + $7.5k/yr Roth):
- Taxable MC: plan ~$75.5k, SPY ~$78.6k, stacked ~$88.8k.
- Roth MC: book ~$70.2k, SPY ~$69.9k, stacked ~$84.1k.

## Manual steps
- **None to watch it.** `make stack-shadow` logs it daily; the weekly digest shows it under "Being tested".
- **To switch it on** (user decision; live code would change):
  - buy SPY with the taxable cash and mark it as a core position the executor never trades or sizes on;
  - make the night/IBS sizing margin-aware;
  - put 1/3 of the Roth in UPRO and size the Roth book on the other 2/3;
  - turn off the Roth's QQQ/SMH IBS.

## Shadow
`swingtrader/daily/stack_shadow.py` (`make stack-shadow`, `state/stack-shadow.jsonl`, tests in `tests/test_stack_shadow.py`,
REGISTRY entry "Book stacked on index beta", gate 250 sessions). Each weekday it logs the live accounts' day, SPY and UPRO,
and the two stacked accounts' day. Never orders.
