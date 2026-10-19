# WRDS Entitlement Reconciliation — 2026-10-16

**Objective.** Before any data purchase, check the program's DATA-LIMITED / BLOCKED rows against
what WRDS *actually* licenses for this account. Method: enumerate all 346 libraries, then probe each
candidate table with `count(*)` (access = a number, deny = Postgres error).

**Result: 4 of the top "blocked/paid" rows are already licensed at $0.** The prior memory
("borrow fees stay DATA-LIMITED", "signed gamma needs ~$180 Databento", "no free per-fund NAV")
was a source assumption, not a WRDS coverage check. It was wrong on all three.

## Access matrix

| program need | prior status in CLAUDE.md | WRDS entitlement (verified) | table(s) | coverage |
|---|---|---|---|---|
| Borrow / HTB / recall history | **BLOCKED** ("no Markit lending") | **AVAILABLE** | `optionm.borrate{1996..2025}`, `optionm.fwdprbr{1996..2025}` | 1996-2025; ~6.0M rows (2020) |
| Signed dealer gamma / open interest | **DATA-TARGET** (~$180 Databento OPRA) | **AVAILABLE** | `optionm.opprcd{1996..2025}` (`open_interest`,`delta`,`gamma`,`best_bid/offer`) | 1996-2025; 291M rows (2020), 183M (2014) |
| Volatility surface (skew / term structure) | **UNEXPLORED** (needs options data) | **AVAILABLE** | `optionm.vsurfd{1996..2025}` | 1996-2025; 403M rows (2020), 4,677 secids |
| Per-fund daily NAV + shares outstanding | **DATA-LIMITED** | **AVAILABLE** | `crsp_q_mutualfunds.daily_nav`, `.monthly_tna`, `.fund_hdr_hist` (`et_flag`) | 1998-09 .. 2026-06; 72,258 funds; 185M nav rows |
| Corporate bond returns | (BOND-LEAD only) | AVAILABLE | `wrdsapps_bondret.bondret` | 4.59M rows |
| European short selling | — | AVAILABLE | `wrdsapps_eushort.eushort` | 441k rows |
| Short interest | known available | AVAILABLE | `comp.sec_shortint` | 5.37M rows |
| PIT issuer ratings (fallen angels) | **DATA-LIMITED** (no free PIT) | **SAMPLE ONLY** | `ciqsamp_ratings.wrds_irating` | 1,322 rows (irating) / 70,115 (srating) — sample, not full |
| Margin-rate history (CME) | **BLOCKED** | still not in WRDS | — | — |
| CBOE option prices / IV borrow rate | — | **DENIED** | `cboe.optprice`, `cboe.ivborrowrate` | listed but `cboe_eod` permission denied |

## Verified schemas / samples

- `optionm.opprcd2020`: `secid, date, symbol, symbol_flag, exdate, last_date, cp_flag, strike_price,
  best_bid, best_offer, volume, open_interest, impl_volatility, delta, gamma, vega, theta, optionid,
  cfadj, am_settlement, contract_size, ss_flag, forward_price, expiry_indicator, root, suffix`
  → per-contract daily OI + greeks; the signed-gamma input.
- `optionm.borrate2020`: `securityid, date, expirationdate, days, borrowrate`; sample row
  `5139, 2020-01-02, 2020-01-17, 15, -99.99`. **`-99.99` is the missing sentinel** — must be filtered.
- `optionm.fwdprbr2020`: `securityid, date, expiration, amsettlement, forwardprice`.
- `optionm.vsurfd2020`: `secid, date, days, delta, impl_volatility, impl_strike, impl_premium, dispersion, cp_flag`.
- `optionm.secnmd`: `secid, effect_date, cusip, ticker, class, issuer, issue, sic` → CRSP/permaticker join key.
- `crsp_q_mutualfunds.fund_hdr_hist`: has `et_flag`, `index_fund_flag`, `fund_name`, `ticker`, `first_offer_dt`,
  `crsp_portno` → identifies ETFs and CEFs and links to `daily_nav` / `monthly_tna`.

## Caveats before any study (do not skip)

1. **`borrowrate` is option-implied, not the actual stock-loan fee.** It is derived via put-call parity
   (same construction as the denied CBOE `ivborrowrate`). It is a proxy for the hard-to-borrow state,
   not a custodial fee feed; per-name coverage is periodic (monthly expirations) and sparse for names
   without listed options. Filter `-99.99`; validate coverage breadth before trusting it.
2. **`opprcd` is filtered** by OptionMetrics (wide spreads / stale quotes dropped); it is not raw OPRA.
   Fine for OI/gamma aggregates; not a substitute for NBBO microstructure.
3. **PIT ratings remain blocked**: `ciqsamp_ratings` is a sample (1,322 issuer rows), so fallen angels
   is unchanged.
4. These are **new data, not new evidence** — nothing is validated until a pre-registered study runs.

## Highest-value next step

The single biggest genuine gap (named counterparty = short sellers, no data) is now partially
addressable. Pre-register ONE study, e.g. **BORROW-RATE-STATE**: does a high OptionMetrics-implied
borrow rate (vs its own 21d median) forecast the same-direction move in the underlying / predict the
IBS-night loser-bounce asymmetry? Free, licensed, untouched period available. Register before reading
outcomes; then judge on a window the rule was not chosen on.

Raw probe evidence: `data/research/wrds_recon/`.
