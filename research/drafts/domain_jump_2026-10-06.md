# Domain-jump memo (2026-10-06 evening): the vocabulary escape

Mandate: mechanisms that do NOT look like "event -> next return". Each row answers the five questions
(family / participant / constraint / observable consequence / why arbitrage leaves it).

## The category the program systematically never modeled
Two whole classes were absent from ~850 registered studies:
1. **Cross-instrument relationships priced off the same issuer** (liability stack: preferred/common,
   dual-class, warrant/underlying, holding-company stubs). Every prior test was one ticker
   against a calendar or its own history. Only share-class TWINS at the close auction were tried (dead).
2. **Regulatory-mandated positioning** (1940-Act caps / 13F schedules). Never loaded 13F at all: F13C v1+v2
   this session = the first assault; both arms KILLED (see round1_prose).

## Mechanism table (new-frontier candidates, five questions + ceiling at $10k)
| family | participant | constraint | consequence | why not instantly arbitraged | status |
|---|---|---|---|---|---|
| **F13C regulatory trim (1940-Act 10%-of-issuer)** | diversified RICs (rule-bound) | 10%/issuer cap when share count shrinks | gradual forced trimming between filings | per-fund small caps, expensive shorts, thousands of small orders | **KILLED v1+v2 this session** (no footprint in daily bars) |
| **Dilution drag (kept)** | small-cap issuers expanding shares | — | -4.7..-5.7%/q vs SPY, both halves, t ~ -2.5 | shorts expensive/illiquid; long-only book uses it as AVOID screen | **defensive screen candidate, forward-watch** |
| Preferred/common liability stack | no convergence force (call dates unknowable free) | — | — | convert-pricing vets own it; retail spread costs dominate | **pre-killed (no convergence/no cost edge)** |
| Fund-accounting NAV (CEF/ETF premium) | APs/income funds | creation fees | premium drift | AP inventory, but SPY/SPDR arms killed (ETC/EF/BSPD) | CLOSED (family-level kills) |
| Funding/settlement (box finance, T+1 float) | retail broker | box-call rates | financing carry | Schwab/IBKR mechanics; no free history | DATA-LIMITED; ranked behind borrow/HTB |
| 13F as a quarterly STATE gate (not alpha) | existing legs | — | gates the IBS/night legs | no analysis exists | OPEN, unspecified (spec only) |

## Ceilings (priority gate) for tonight's survivors
- F13C: ~+2-4pp/yr ceiling IF alive; measured ~0 -> moot.
- Dilution screen: defensive; adds protection, not return: keep as an avoid-list, not a leg.

## What to try next session (ranked, all cheap)
1. **13F quarterly STATE gate** on the existing legs (the only data-supported use of this family).
2. **Intraday permit-free data** (the m1 matrices already cached) to attack pricing TIMING deaths that
   daily bars cannot re-test (BE/BD-class) — different observability, not new costs.
3. The named paid-data decisions stay unchanged (signed gamma $180, borrow fees, PIT ratings).
