# Broker facts from Reddit (r/Schwab, r/alpacamarkets, r/pennystocks, r/quant), 2026-10-02

Sweep: r/Schwab 18,924 posts (1,122 read), r/alpacamarkets 515 (415), r/quant 28,790 (1,570), r/quantfinance 17,228
(257), r/pennystocks 65,505 (766 on splits/offerings/compliance). No new edge. Facts below are user reports, not
documentation; counts = independent users.

## Round-up trade (B1)
- Schwab follows the issuer's fractional terms. Cash in lieu is what most reports show (~6 users, 2021-26), as the
  issuer's terms said cash. One report of Schwab rounding 3 shares of GWAV (1-for-150) up to 1 (2024-06, n=1). No report
  either way for a 1-share holder on a "rounded up" deal. VIVK (ex 2026-10-05) is still the first real test.
- The post-split position can lag 2-5 business days, with wrong cost basis or value meanwhile (~15 users).
  roundup_orders.py waits >= 2 days and calls "cash" at 21 days: consistent.
- Cash in lieu is booked as a sale (small realised loss, feeds wash-sale tracking).
- Thin/volatile names can be restricted: "Opening transactions for this security must be placed with a broker"
  (~4 users, 2026). An API buy may be rejected: treat it as a skip.
- Split dates slip and broker feeds can announce wrong dates (IBKR, PSTV 2025): use the 8-K / press release.

## Schwab
- thinkorswim help (quoted, 1 report, 2022): MOC orders "at least 20 minutes before the close"; later entries are
  "best efforts". The close run fires at 15:40. Verify with `make review` (night buy_cost_bps vs the official close)
  and the order entered times.
- Directed routing: venue choice only on StreetSmart Edge historically; no IEX routing (4 threads). Matches 46/46 AUTO.
- Refresh token 7 days (many). It can also die early after Schwab updates, and editing the developer app resets approval.
- Wash sales are tracked per account only; the cross-account (taxable/Roth) rule is the bot's job (many).
- Limited-margin Roth: trades unsettled funds, never borrows; a same-day sell + rebuy of the SAME name on unsettled
  funds can still be a GFV (2 users). The night leg (buy close, sell open) is clean.
- "Available quantity" ignores resting sell orders (1 user, 2026).
- Fills from 8pm-3am ET (EXTO / Blue Ocean) don't show until after 03:00 ET (2 users): relevant to 23/5 reconciliation.
- Market-order price improvement reportedly worse since 2026-03 (3 users); auction orders unaffected (unverified).

## Alpaca (paper control)
- Paper processes NO corporate actions: no splits, no reverse splits, no dividends (Alpaca staff, 2x). The paper P&L on
  any split name is wrong, and IBS ETF dividends are not credited (paper understates the IBS leg).
- Paper fills at the touch (ask/bid), not the auction cross; paper says nothing about auction slippage.
- Nightly paper processing ~03:30 ET has altered a position once (restored by staff).
- 1Day bars use a different trade filter than minute bars and include extended-hours prints (volume ~30% high):
  use rth_minutes for anything regular-hours (already the CLAUDE.md rule).
