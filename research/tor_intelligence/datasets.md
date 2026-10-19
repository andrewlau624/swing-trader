# Tor Intelligence — Datasets

Discovery date: 2026-10-16

## Finding: NO legitimate dataset discovered.

Across 24 search terms and one bulk index (15,529 onions), the only financial/quantitative-adjacent
material on Tor was one of the two columns below. Nothing met the mission's provenance bar
("legitimately published, legally usable, point-in-time timestamped").

### Prohibited material (explicitly rejected — do not acquire or use)

| category | examples seen | why rejected |
|---|---|---|
| Stolen credentials / accounts | "Crypto Accounts — Binance/Coinbase/Kraken Verified" shops | Unlawful provenance; mission forbids stolen/breached data. |
| Payment-card data | "CRDSTORE CVV SHOP", fullz, fake-ID shops | Unlawful. |
| "Hacked" crypto keys | "Fancy Bear APT28 — hacked private BTC keys" | Unlawful; near-certainly scams. |
| Marketplaces | guns, drugs, faux-credentials ("DarkMall", "BoomMarket") | Unlawful. |
| Hacking-for-hire | "hire crypto hacker / exchange security" | Unlawful / fraud. |

None of this is usable and none of it is market-predictive even if it were lawful.

### Non-financial / out-of-scope (legitimate but useless here)

| source | why not useful |
|---|---|
| No-KYC crypto swap services (GhostSwap, VeilSwap, Haveno reviews) | Execution venues for privacy, not datasets. |
| Monero/Monerica community pages, Hidden Wiki | Directories, no numeric data, no PIT. |
| Dead v2 crypto-research mirrors (Rauzy, delvingbitcoin) | Unreachable; clearnet duplicates exist and are not market data. |

## Requirement check against the program's own data needs

CLAUDE.md's data map lists the genuinely open needs as: borrow/HTB fee history, point-in-time issuer
ratings, per-fund daily NAV/shares-outstanding, signed dealer gamma (OPRA), margin-rate history.
**None of these exist on Tor** in any legitimate form. Paid/vendor sources (WRDS Markit lending,
Databento OPRA, TRACE, PIT ratings) remain the only route, exactly as the existing ledger records.

## Access / cost

- Cost of the Tor route: $0 (client only). Information value delivered: ~0.
- No registration, payment, or operator contact was performed (permission to install the client was
  granted; nothing else was authorized or needed).
