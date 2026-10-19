# Tor Intelligence — Verified Source Catalog

Discovery date: 2026-10-16
Method: Tor client (`brew install tor torsocks`), SOCKS5 proxy on `127.0.0.1:9050`,
reached via `curl --socks5-hostname 127.0.0.1:9050` (`torsocks` is blocked by macOS SIP).
Circuit verified: `https://check.torproject.org/api/ip` -> `{"IsTor":true,"IP":"185.220.101.169"}`.

## Indexes / search layer

| source | reachable | notes | evidence quality |
|---|---|---|---|
| Ahmia clearnet `ahmia.fi/search/?q=` | yes (HTTP 200) | Search **requires the hidden form field** `cdc0eb=3be8a1`; without it the endpoint 302-redirects to `/`. Filtered ("clean") index — it removes known CSAM but keeps markets/scams. | verified by direct fetch |
| Ahmia `.onion` mirror `juhanurmihxlp77nkq76byazcldy2hlmovfu2epvl5ankdibsot4csyd.onion` | yes (HTTP 200 on `/`), but `/search/` -> 302 | Index-host onion, not a search endpoint from here. | verified |
| Ahmia full known-onion list `ahmia.fi/onions/` | yes | 15,529 unique `.onion` addresses returned (1.24 MB). Bulk corpus, mostly dead/illegal. | verified by fetch |
| `tor.taxi` (clearnet directory) | yes | 54 `.onion` addresses; directory of markets/forums/services. | verified by fetch |

## Search terms executed (unsuccessful — do NOT repeat)

`quantitative finance`, `quantitative research`, `algorithmic trading`, `machine learning finance`,
`market data`, `financial data`, `stock market data`, `stock data`, `order book`, `trading`,
`backtest trading`, `portfolio optimization`, `economic data`, `statistics finance`, `hedge fund`,
`sec filings`, `stock exchange`, `arxiv research`, `open dataset`, `university research`,
`cryptography research`, `bitcoin research archive`, `time series database`, `trading algorithm`.

All returned: darknet markets (drugs/weapons/IDs), stolen-data shops (CVV/fullz/"hacked BTC keys"/
verified exchange accounts), no-KYC crypto swaps, SEO-spam doorway pages, scams, and porn.
**No legitimate market/financial data source was found under any term.**

## Legitimate artifacts encountered (all unusable)

| artifact | address | status | assessment |
|---|---|---|---|
| "Research — Pablo Rauzy" (crypto/CS researcher blog) | `pablo2httpff4vogufavlmbxw4jkgb3amnywex2x.onion` | **dead** (connect fails in <1 ms) | 39-char address = Tor v2 onion; v2 support removed Oct 2021. Clearnet equivalent `pablo.rauzy.name`. |
| "Archive of delvingbitcoin.org" | `e3y5vky4v7snefqyhbn6kcmyl5fo4cnk3a2irh2t.onion` | **dead** (v2) | Bitcoin research archive; clearnet equivalent exists. |
| Monerica / Hidden Wiki / Monero community pages | various | live but out of scope | Directories of the above; no market data. |

## Verdict on the Tor source layer

The Tor `.onion` space contains **no legally usable market/financial dataset** relevant to this
program. Its financial content is entirely (a) illegal data/marketplaces, which the mission
explicitly forbids, or (b) scam/SEO spam. Every legitimate technical artifact indexed is either a
dead v2 mirror of clearnet content or a cryptocurrency community page — neither is a new data source.
