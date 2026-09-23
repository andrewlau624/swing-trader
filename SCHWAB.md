# Schwab setup (real money)

Paper trading stays on Alpaca. Real money goes through Schwab. Both books run
side by side, so paper and real fills stay comparable.

## 1. Developer portal (one time)

1. Go to **developer.schwab.com** and register. The developer login is
   separate from your brokerage login.
2. **Dashboard → Apps → Create App**
   - API product: **Trader API – Individual** (it bundles *Accounts and
     Trading Production* and *Market Data Production*)
   - App name: anything, e.g. `swing-trader`
   - Callback URL: **`https://127.0.0.1`** — exactly this: https, no port,
     no trailing slash. It must match `SCHWAB_CALLBACK_URL` character for character.
   - Order limit: the default (120/min) is plenty
3. Wait for the status to read **"Ready For Use"**. It usually says *Approved –
   Pending* first; that takes from hours to a few business days. Nothing works
   until it changes.
4. Open the app and copy the **App Key** and **Secret**.

## 2. Brokerage account (one time)

- It must be a **margin** account. The bot sells at the open and re-buys at the
  close with the same day's money; in a cash account that is a good-faith
  violation. `make daily-live-check` refuses to go live on a cash account.
- Fund it with the $3,000.

## 3. On the server

```bash
make pull && make setup          # installs schwab-py
$EDITOR .env                     # add the lines below
make schwab-login                # prints a URL: open it, log in with your BROKERAGE login,
                                 # tick the account, then paste the https://127.0.0.1/?code=...
                                 # address you land on (the "can't connect" page is expected)
make daily-live-check            # shows balance, margin, token age. Changes nothing
make daily-live-on               # type REAL MONEY
```

```
SCHWAB_APP_KEY=...
SCHWAB_APP_SECRET=...
SCHWAB_CALLBACK_URL=https://127.0.0.1
# only if more than one account is linked:
# SCHWAB_ACCOUNT_NUMBER=12345678
```

## 4. Every 7 days: `make schwab-login`

Schwab refresh tokens die after 7 days, and nothing can renew them
automatically. `schwab-reminder.timer` (installed by `make persist`, every 2
hours, weekends included) emails you **2 days before, 1 day before, and under 6
hours before** it expires, then once when it has expired. Each `make
schwab-login` emails a confirmation with the exact expiry time and restarts the
sequence. `make schwab-reminder` shows the current status. Log in during the
day, so the expiry and its last reminder land while you're awake.

If the token does expire, live runs fail loudly and place nothing, while paper
keeps running and the 15:40 scan falls back to Alpaca data.

## What is different from Alpaca

| | Alpaca (paper) | Schwab (live) |
|---|---|---|
| overnight buy at the close | MOC (`cls`) | `MARKET_ON_CLOSE` — same |
| overnight sell at the open | market-on-open auction (`opg`) | **no MOO type**: a market DAY order placed at 09:15 fills at the open, but may not be the auction price |
| IBS ETFs | fractional, by dollar amount | **whole shares** (QQQ at ~$750 = 2 shares of a $1,500 slot) |
| duplicate protection | client order id | the book is saved after every order; before placing, today's Schwab orders are checked for an identical one |
| shorts (intraday leg) | automatic | explicit SELL_SHORT / BUY_TO_COVER |
| market data | Alpaca (IEX + delayed SIP), both accounts | same — so the only paper/live difference is execution |

**Watch the open fills.** Research (addendum 10) found the overnight leg's
entire edge is in the opening auction: +20bp at the open, gone by 09:35.
`make daily-status` reports live slippage per leg. If Schwab's open fills
run much worse than paper's, that leg's edge is at risk.
