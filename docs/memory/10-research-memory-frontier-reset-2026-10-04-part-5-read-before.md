# Research memory — FRONTIER RESET (2026-10-04, part 5) — read before proposing anything

- **Permanent: T5/T5L DEAD; generic options strategy search CLOSED** (part 4 has the numbers). Do not search for another
  T5 variation or any calls/puts/condor/fly/straddle strategy. Options reopen only for options-INDUCED underlying flows.
- **Execution cost ~0bp is established.** The digest's `slippage_bps` drift-as-cost display is a separate CLEANUP item;
  do not change live code for it inside a research cycle.
- Program N = 809 (T5L 806 + NX 807-809). N measures how hard the local neighbourhood was searched, not the space.
- Ledger with the 11-question standard and verified data: `research/drafts/frontier_reset_2026-10-04.md`.
  Classes: nothing VALIDATED; PROMISING = Reg SHO threshold forced buy (timing now observable: daily Nasdaq lists 2007+,
  NYSE JSON 2012+, free) and Treasury auction concession (small); DATA-LIMITED = fallen angels (no free PIT ratings;
  bonds not retail-executable), ETF premium/discount + rebalance (SSGA navhist works, $0), borrow/HTB/recalls (no free
  fee history), margin-cascade triggers (CME notices 403, FINRA margin monthly), signed dealer gamma (OPRA OI ~$180/yr,
  the one untouched source; add. 35 only tested the OPEX calendar); TESTED-AND-REJECTED = LETF flow, vol-target/LETF
  deleveraging proxies, 0DTE hedging timing, VIX roll, window dressing, FINRA short volume, IPO/SPAC, intl ETF overnight.
- Resolves the part-3/part-4 conflict: fallen angels and ETF creation/redemption are DATA-LIMITED (acquirable for ETFs
  via SSGA), NOT rejected.
- **CEF discounts = separate secondary track** (~2-5%/yr literature). CEFConnect `/api/v3/pricinghistory/{T}/All` gives
  weekly NAV/discount from 1996, live funds only: survivorship unhandled. Must not displace the main search.
- Honest read: no candidate found promises an order-of-magnitude larger opportunity at $2-25k. Bigger mechanisms
  likely need new market access (futures, international, institutional-size bonds) or paid data (borrow fees, PIT
  ratings): user decisions. Test order: threshold forced buy -> dealer gamma (needs ~$180 OK) -> SPDR ETF discounts.
- Keep Trader research separate from the Polymarket project (same server, different repo; never mix data or code).
