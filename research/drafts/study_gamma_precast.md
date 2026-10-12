# Study GAMMA-STAT — OPRA signed dealer-gamma pre-registration (DRAFT SPEC; NO purchase made
# pending the data-buy rule; third-robot session 2026-10-06)

## Why this and not OI-pinning (which is killed)
OPEX OI-pinning (Study in research/sim/opex_pin.py) tested per-STRIKE concentration at monthly
expiries (K1/K2): net -8.4bp/+19.5bp — rejected as a tradable strike-level effect. The gamma STATE
is a different level of the same data: an aggregate dealer-positioning (hedging flow) variable that
conditions the WHOLE market, not one strike. It is the only mechanism on the frontier ledger whose
free proxy (strike-level concentration) failed while the aggregate state was never testable —
and it is now the ONLY remaining "options-induced underlying flow" (the program's top paid test).

## What OPRA (Databento OPRA.PILLAR) uniquely provides
- Daily per-strike/per-expiry OPEN INTEREST (`statistics` tables, 2013->) — the free data
  (Yahoo/CBOE quotes) does NOT expose history by strike; this is not reconstructible free.
- Contract definitions (`definition`) — strike/expiry/type/conract id.
- 1-minute NBBO (`cbbo-1m`), option-priced — needed only if the experiment judges per-strike fills.

## Free data cannot reconstruct
- Historical OI by strike/expiry (the essential input).
- Dealer gamma sign inference only by convention (below).

## Assumption pre-school
- **Sign convention (declared in advance, one arm only):** dealers are short customer-bought CALLS
  and long customer-sold WINNING puts — the standard approximation GEX = Σ_ strikes
  [OI_call(k) − OI_put(k)] × Γ_BS(k, S_t, T) × 100. The convention problem is known; it is what the
  aggregate tests must survive.
- Black-Scholes gamma with the realized rate/dividend assumptions; expires filtered to the SPY's
  listed expiries within 1 year.

## Hypothesis (primary, frozen)
 dealer net gamma G_t (SPY or QQQ, index-weighted) is a STATE: (a) when G_t flips from positive
 to negative (dealers under-hedged), realized next-2-session vol of the INDEX RISES and the S&P
 drift turns; when |G_t| is HIGH, the index is pinned/stabilized. Judged quantity: the 2021-2026
 daily SPY close-to-open and the 1-5-session realized-vol conditional on the |G|-state's
 standardized (t vs its '21d rolling MAD') bands. Wind-arms: IBS-night and the noise legs'
 per-trade returns conditional on the gamma state.

## Judge design (frozen)
- Symbols: SPY + QQQ (the only two worth pulling; SPY+QQQ OI ≈ $180/yr observed — recompute at
  purchase time); period: 2013-08..2026-06 FIRST PULL = ~$30 windowed (OPEX weeks + gamma-flip
  weeks); full-buy = ~$360 = 10yr for BOTH symbols: **the decisive test = ~$360 max, per year NOT a
  subscription** (cancel after the one run).
- Entry/exit: close of the flip-day (or -vhedged 'day +1') through +5 sessions close (a 1-shot); both
  directions; no shorts; either OK (the SPY-hedged book overlay for the account gamma-neutral).
- Minimum economically meaningful effect (frozen): a +25bp/flip-day net abnormal sustained both
  halves (2021-23 / 2024-26) — anything thinner = "regime-museum" (rejected like every calendar
  effect at below ~3%/yr on the account).
- Costs: entry+exit 25bp/leg on SPY/QQQ (real liquid), 50bp total; plus the edge's 100% = the
  account's own SPY-position exiting in RealSpreads; shock 2x shown.
- Expected information value assert: if the state effect (a positive response) with honest capture
  ~(≤50%) gives ≥ +2pp/yr to the book's realized return via better gating alone — and the "the flip
  is a VOL-spike warning" arms can guard the book's (e.p) drawdowns. This is a CONDITIONING value —
  the honest ceiling remains below the +8pp discovery gate as a STANDALONE edge (per the memory:
  state-level/protective effects are ~+1-2pp/yr class: VENM's own lesson).

## RECOMMENDATION (data-buy decision, user)
**DO NOT PURCHASE YET.** Cost = ~$360; expected information = the gamma-state as a protective gate
at ~+1-2pp/yr honest ceiling — neither obviously larger than existing protective edges/tier
controls nor decisive to the pending night-leg size-up decision. Revisit ONLY IF the BOROW-SNAP /
CEF-replication collectors don't dominate the budget and the user wants the last free-data gap in
regime-conditioning closed. The spec stands pre-registered; DO NOT RUN without approval.
