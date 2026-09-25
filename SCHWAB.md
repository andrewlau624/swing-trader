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
- Fund it. The bot sizes from the real balance; to trade only part of it, set
  `DAILY_LIVE_CAPITAL` (dollars) in `.env`. It is a hard cap.

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
DAILY_LIVE_CAPITAL=1000          # optional hard cap in dollars
```

Check it the next morning with `make daily-status` and, once night exits
exist, `make review SINCE=<first live day> ARGS=--no-replay`.

## 3b. The Roth IRA book (optional)

The same login can drive a Roth IRA as a third book: 1.0x overnight at most
(an IRA never borrows), the intraday leg through 3x ETFs instead of shorting,
and a 30-day wash-sale gap against the brokerage book (a loss disallowed
against an IRA is gone for good). Addendum 20.

1. Ask Schwab for **limited margin** on the Roth. Without it the book would
   reuse unsettled cash, which is a good-faith violation.
2. Set **both** account numbers in `.env` *before* linking the Roth
   (`SCHWAB_ACCOUNT_NUMBER` and `SCHWAB_ROTH_ACCOUNT_NUMBER`; the last 4
   digits are enough). With two accounts linked and no number set, the
   brokerage book stops rather than guess.
3. `make schwab-login` again, ticking both accounts.
4. `ROTH_LIMITED_MARGIN=yes`, optionally `DAILY_ROTH_CAPITAL=...`.
5. Sell the Roth's existing holdings yourself if you want the bot to use that
   cash. The bot never touches positions it did not open.
6. `make daily-roth-check`, then `make daily-roth-on`.

## 4. Every 7 days: `make schwab-login`

Schwab refresh tokens die after 7 days, and nothing can renew them
automatically. `schwab-reminder.timer` (installed by `make persist`, every 2
hours, weekends included) emails you **2 days before, 1 day before, and under 6
hours before** it expires, then once when it has expired. Each `make
schwab-login` emails a confirmation with the exact expiry time and restarts the
sequence. `make schwab-reminder` shows the current status. Log in during the
day, so the expiry and its last reminder land while you're awake.

**Only ONE machine can hold the login.** Schwab keeps one active login per app:
running `make schwab-login` anywhere else (a laptop) silently revokes the
server's. The reminder timer probes Schwab every 2 hours and emails you if
that happens. Always log in *on the server*.

If the token does expire, live runs fail loudly and place nothing, while paper
keeps running and the 15:40 scan falls back to Alpaca data.

## What is different from Alpaca

| | Alpaca (paper) | Schwab (live) |
|---|---|---|
| overnight buy at the close | MOC (`cls`) | `MARKET_ON_CLOSE` — same |
| overnight sell at the open | market-on-open auction (`opg`) | **no MOO type**: a market DAY order placed at 09:15 and **directed to the stock's listing exchange** (`requestedDestination`), so it joins that exchange's opening auction. If Schwab refuses the route, the bot resends it with Schwab's routing (a wholesaler "at the open") and pauses directed routing for 5 days. `daily.schwab_open_route: auto` turns directing off |
| IBS ETFs | fractional, by dollar amount | **whole shares** (QQQ at ~$750 = 2 shares of a $1,500 slot) |
| duplicate protection | client order id | the book is saved after every order; before placing, today's Schwab orders are checked for an identical one |
| shorts (intraday leg) | automatic | explicit SELL_SHORT / BUY_TO_COVER |
| market data | Alpaca (IEX + delayed SIP), both accounts | same — so the only paper/live difference is execution |

**Watch the open fills.** Research (addendum 10) found the overnight leg's
entire edge is in the opening auction: +20bp at the open, gone by 09:35.
`make daily-status` reports slippage per leg against the price at decision
time (15:50 for night buys). That includes the market's move into the
auction, so it reads worse than the execution cost. **The number that gates
leverage is in `make review`:** fills vs the official auction print. Every 15:40 run logs
each route's cost and **auction hit rate** (fills within half a cent of the
official open). A high hit rate on NASDAQ/NYSE/ECN_ARCA routes means the
emulated market-on-open works. The bot kills the night leg by itself if open
sells average > 25bp/side over 30 exits, and only turns overnight leverage
on after 50 exits at ≤ 10bp/side (RESULTS.md addendum 16).

Directed routing is standard on thinkorswim for equities, but whether the
Trader API honours `requestedDestination` for this account, and whether any
exchange fee is passed through, is unverified until the first live open.
Check the first morning's log for `-> NASDAQ` on the submits and for any
"directed ... ended rejected" warnings.
