# Study ETC: ETF creation/redemption flow proxy via daily shares-outstanding (pre-reg 2026-10-04)

Free data (State Street navhist xlsx: daily NAV, shares outstanding, total net assets). Mechanism probe.

## Mechanism
Authorized participants create/redeem ETF shares in creation units only against the underlying
basket at NAV. **Daily shares outstanding is the observable net creation/redemption.** Large
creations = APs absorbing end-investor demand (a demand proxy); large redemptions = selling
pressure. The question is whether the flow *predicts* the ETF price/NAV over the next few days,
or whether the price pressure from flow is a contrarian opportunity. Counterparty: the AP (arb)
and the end investor whose flow forces the AP to trade the basket.

## Data
- SSGA navhist xlsx per fund: SPY (S&P500), IWM (Russell 2000 via iShares — not SSGA; use SSGA's
  own funds), plus SPDR sector/intl/bond funds that have xlsx. Start SPY + a few SPDR funds with
  long history (JNK, GLD, XLF, XLE, EEM is iShares).
- Price: `etf_daily` (open/close) for SPY and the same funds.

## Rule (frozen)
1. flow_t = shares_t / shares_{t-1} - 1 (net creation/redemption rate).
2. Signal at t (known after close): sign(flow_t) x forward return t+1 (close->close), and the
   3-day version. Prediction: positive flow -> non-negative next return (demand continues) OR
   negative (flow is contrarian). Test both.
3. Discount: (close_t - NAV_t)/NAV_t; test its next-day reversion, and flow-conditioned.
4. Execution: SPY ~1bp round trip; report net.
5. Report by flow-decile, ex-best-5, by year, both sub-periods.

## Kill / economics
Kill unless a decile shows a next-day (or 3-day) net return materially above the ~1-2bp SPY round
trip AND the effect is not a single year. The point is *scalability*: SPY/IWM are bottomless, so a
real 1-day flow signal would be a capacity win. Bar: >= ~3bp/day net and stable = promising;
otherwise rejected.
