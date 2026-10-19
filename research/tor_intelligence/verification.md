# Tor Intelligence — Verification & Red-Team Assessment

Discovery date: 2026-10-16
Reviewer stance: adversarial. Every claim below is checked against primary evidence (raw HTTP
responses), not against a source's self-description.

## A. Was the environment real?

| claim | evidence | verdict |
|---|---|---|
| Traffic actually routed through Tor | `check.torproject.org/api/ip` returned `{"IsTor":true,"IP":"185.220.101.169"}` | **verified** |
| `.onion` reachable | Ahmia onion `/` returned HTTP 200; searches returned 1-1.9 MB result pages | **verified** |
| Search endpoint works | `ahmia.fi/search/?q=...` returns 302 without the `cdc0eb=3be8a1` token, 200 with it | **verified** |

## B. Provenance assessment of discovered material

| finding | provenance | lawfulness | PIT-usable | disposition |
|---|---|---|---|---|
| Darknet markets (drugs/guns/IDs) | anonymous operators | unlawful | n/a | **REJECT** |
| Stolen accounts / CVV / "hacked keys" | explicitly criminal | unlawful | n/a | **REJECT** |
| No-KYC crypto swaps | legitimate-ish services | lawful to read | no numeric data | out of scope |
| "AI trading bot" / doorway spam | unknown, templated | likely scam | no | **REJECT** |
| Dead v2 research mirrors (Rauzy, delvingbitcoin) | legitimate academics (clearnet) | lawful | n/a (dead) | no value |

Red-team checks applied:
- **Is it too good to be true?** Yes, for everything advertised (lots, "verified", "best trusted") —
  these are SEO spam signatures, not products.
- **Can it be independently verified?** No artifact could: no code, no docs, no reproducible result.
- **Is the address even alive?** The two plausibly-legitimate onions were v2 addresses, dead since
  Tor removed v2 support (Oct 2021) — the index returns them but they cannot be reached.
- **Does obscurity imply value?** No. The mission's own caveat ("do not assume a discovery is
  valuable simply because it is obscure or hosted on Tor") is confirmed here.

## C. Threats to the *conclusion* (could the null be wrong?)

| threat | mitigation | residual risk |
|---|---|---|
| Ahmia's filtered index hides good content | Also probed the raw 15,529-onion list and `tor.taxi` directory; same profile. | Low. A niche private onion *could* exist, but it would still be unlawful or clearnet-duplicated. |
| Wrong search terms | 24 terms spanning quant, data, research, academic, exchanges. | Low. |
| Index staleness / coverage limits | Ahmia is the largest indexed aggregator; results were abundant (500-1250/term), just worthless. | Low. |
| Could a paid/private onion data broker exist? | Unverifiable and, by the mission's rules, disallowed if unlawfully sourced. | Not actionable. |

## D. Red-team verdict

The null is **robust**, not a search failure. The Tor financial space is a population of illegal
marketplaces and automated spam with no legitimate quantitative content. Conclusion stands: no
discovery meets any of the mission's five success criteria.

## E. Safety & scope compliance

- Installed software: `tor`, `torsocks` (user-authorized).
- No binaries downloaded or executed from Tor; no private system accessed; no vulnerability used.
- No accounts registered, no data purchased, no operators contacted.
- All fetched pages were read as text only.
