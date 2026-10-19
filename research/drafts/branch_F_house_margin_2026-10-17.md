# Branch F - single-stock broker house-margin increases as a forced-selling trigger (2026-10-17)

Verdict: ZERO surviving cards. DATA-LIMITED at the observation step (no archivable, timestamped per-symbol list exists in public), and the ceiling is under the gate even on generous assumptions. No N consumed, no backtest.

Repo grep (NEXT.md, research/drafts/*.md): only aggregate margin debt is covered (MFLW, dead). One line in round1_prose.md notes Schwab house margin can be 100% on volatile names (a buying-power risk, not a signal). Single-name house margin has no prior study. MISTAKES.md does not exist.

## 1. Is there an archivable per-symbol list? No (as far as I could reach).
- IBKR: policy says house maintenance can be raised "at any time without advance written notice" (IB disclosure, via search snippets). Per-symbol changes go out as client emails, occasionally a press release. interactivebrokers.com margin-stocks pages return HTTP 403 to WebFetch and 404 on the guessed notice URL. Wayback CDX was "Temporarily Offline" this session; one earlier CDX call showed the margin-stocks.php page has only ~10 monthly snapshots 2021-2023, and it holds general rates, not a per-symbol change log. Not verified deeper.
- Webull help pages (webull.com/help/faq/559): default tiers by price and 2x/3x LETF only; "requirements for specific stocks may change without prior notice"; shown only on the order ticket. No list.
- Schwab/Robinhood: searches found only generic explainers; no per-symbol list. Schwab page not fetched (earlier note in repo: blocks automated fetch).
- DTC chills: SEC fast-answer (sec.gov/fast-answers/answersdtc-freezeshtm.html) and DTC Rule 22(A) describe deposit chills/global locks; notices go to the issuer and participants, not a public dated feed. Chills hit unregistered-share/penny/shell names, are a transfer-eligibility restriction (not forced liquidation), and the names are mostly unborrowable microcaps. Not a levered-retail margin trigger. Dropped.
- OCC: margin/clearing changes on single names are not published as a retail-readable archive that I found.

## 2. Dated sample: n = 3 public episodes, 7 symbols (needs >= 20; NOT achievable)
Only press-covered events are discoverable, and those are selected by being extreme (survivorship of newsworthiness).
| event | broker | symbols | announcement | rule | source |
|---|---|---|---|---|---|
| Meme squeeze | IBKR | GME AMC BB EXPR KOSS | 2021-01-28 | long 100%, short 300%, options liquidation-only | businesswire.com/news/home/20210128005689 (search result; page not opened) |
| MSTR | IBKR | MSTR | after NY close 2025-01-08, phased to 2025-01-13 | maintenance >= 50% | investing.com article (search result; not opened) |
| Pre-election 2020 | IBKR | all accounts | n/a | market-wide, not single-name | yahoo finance (not a single-name event; excluded) |
Robinhood raised GME margins Jan 2021 (sharecast.com result). Nothing found for 2022-2026 single names, which is itself informative: the events are rare and not documented.

## 3. DESCRIPTIVE path look (Sharadar closeadj, touched: Jan 2021 and Jan 2025 windows; bp, close-to-close; NOT a test)
| sym | ann-1 -> ann | ann -> eff | eff -> +5 (SPY same) |
|---|---|---|---|
| MSTR (ann 01-08, eff 01-13) | -285 | -99 (SPY -137) | +1848 (SPY +373) |
| GME (ann 01-27 close ref, eff 01-28) | +13483 | -4429 | -7237 (+227) |
| AMC | +30121 | -5663 | -1784 |
| BB | +3266 | -4163 | -1706 |
| EXPR | +21414 | -5079 | -3021 |
| KOSS | +48000 | -2766 | -5520 |
Read: MSTR is the only clean case (small concession, large rebound, n=1, coincident with a crypto rally). The Jan 2021 names fell sharply into the effective day and kept falling after (the "rebound" never came): the restriction came after a +1000s bp spike, was bundled with buying restrictions at other brokers, and the spike was the bubble itself. Mixed sign, n=1 and n=5 from one episode. Nothing to pre-register on this.

## 4. Ceiling and spec
Ceiling = events/yr x net edge x share x 50% capture. Observable public events: ~0.5-1/yr (MSTR-type, press-covered). Even if each paid 15% on 25% of a $10k account at 50% capture: 1 x 15% x 25% x 50% = ~1.9pp/yr at $10k (about the same at $2.3k/$25k; whole shares fine). Far below +8pp. Events that are not press-covered cannot be observed at all (no list), so the real-time trade is not executable either; the effective date is often "immediately/phased", so the concession is gone before a retail client could know. Capital lock 5 days; Roth ok (long-only), downside on a levered-retail name is large (GME-type -70%).

Pre-registrable spec only if a PIT list ever appears (e.g. a broker publishes a change log, or 20+ IBKR client emails are supplied by the user, who holds the account notices): long at the close of the announcement session, exit +5 sessions, vs SPY and vs a volatility-matched placebo; judge on events after the sample used to choose; kill if median excess < +300bp or t < 2 day-clustered. Untouched window: all events other than 2021-01 and 2025-01 (those two are now looked at).

## Dropped
- Aggregate FINRA margin debt: dead (MFLW N 866).
- DTC deposit chill / global lock: unborrowable shells, no forced liquidation by levered holders, no dated public feed.
- Robinhood/Webull/Schwab lists: not published.
- Jan-2021 style position-closing-only: episodic crisis, not recurring.
- Only potential user-side action: IBKR account holders receive these emails; if the user has an IBKR account, saving them would build a forward log. Schwab account has no equivalent known.
