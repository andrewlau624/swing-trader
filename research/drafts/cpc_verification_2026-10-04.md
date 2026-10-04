# CPC: is the mechanism alive today? (verification 2026-10-04, primary sources)

## UMH Dividend Reinvestment and Stock Purchase Plan — ALIVE
Sources: plan prospectus supplement 424B3 filed 2021-02-01 (accession 0001493152-21-002238; base prospectus 2019-06-17,
Reg. 333-232162); UMH 10-Q for Q2 2026 (0001493152-26-036177), Q3 2025 (0001493152-25-020593), Q3 2024
(0001493152-24-043831). No later plan amendment found in the EDGAR filing index (checked 2026-10-04).
- **Discount: 5%.** Price = the HIGHER of 95% of the average daily (high+low)/2 over the 4 trading days including and
  preceding the Investment Date, or 95% of the Investment Date's (high+low)/2 (Q16).
- **Optional cash payments: min $500, max $1,000 per month per owner of shares** (cut from $5,000 effective
  2021-02-11), above that only by UMH's discretionary Request for Waiver (Q11-12).
- **Investment Date:** the dividend payment date in dividend months (~Mar/Jun/Sep/Dec 15), else the 15th; next NYSE day
  if a holiday. Cash is invested monthly "generally on the Investment Date"; no interest on cash held by the Agent.
- **Eligibility:** holders of record; street-name (e.g. Schwab) holders may make optional cash payments by sending an
  Authorization Card certifying they are UMH shareholders (Q4). Payment by check/money order to the Agent
  (American Stock Transfer, now Equiniti). Shares are held at the Agent, not at Schwab.
- **Discount actually granted (implied = DRIP $ / shares issued vs the period's average close):** 9M-2024 4.3%,
  9M-2025 5.3%, H1-2026 4.8%. H1-2026: $4.6M for 314,000 shares; $909k of the June 2026 dividend was reinvested.
- **Not verified:** the Agent's receipt cutoff before each Investment Date; whether Equiniti accepts online payments;
  the time and cost to sell plan shares (Agent sale vs DRS transfer to Schwab). Price risk while shares sit at the Agent
  (UMH ~1.6%/day; ~5% sd over two weeks) is the same size as the discount unless hedged by a short in the taxable account.
- **Scale:** $1,000/month x 5% = ~$600/yr gross per owner at most (~$390 after 35% tax); not multiplied by extra accounts
  (the cap is per owner of shares). MNR, the other historical DRIP issuer in the census, no longer exists (acquired 2022).
**Kill condition (discount < 1% or unavailable to a small holder): NOT met.**

## Other families
- Reverse-split round-ups (B1): mechanism alive in filings (`roundup_watch`, automatic 1-share buys); whether Schwab
  passes the round-up to a 1-share holder is settled by VIVK (~2026-10-07).
- Split-off exchange offers with odd-lot priority (B2): alive as a corporate practice, ~1.3/yr; `splitoff_watch` alerts.
- Odd-lot tenders: alive; `tender_watch` alerts.
- Other issuer discount purchase plans: none verified beyond UMH; not searched (no rescue search).
