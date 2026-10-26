# Research memory — deep loop (2026-10-12, `research/drafts/deep_loop_ledger.md`)

- Crypto access (date-versioned 2026-10-12): Schwab spot BTC/ETH since 2026-05 (~75bp/trade, taxable only); Coinbase US
  perp-style nano BTC/ETH (hourly funding); Roth = spot ETFs only. Funding carry, CME basis, unlocks, listings, depegs:
  CEILING/ACCESS-KILL; DAT mNAV discount DATA-LIMITED (`crypto_access_2026-10-12.md`).
- Box-spread financing: ACCESS-KILL below $125k (Reg-T short box costs ~its width in buying power; PM needs $125k).
- **LEG-HEALTH (N 938): KILL.** Own trailing-63-session P&L switch costs 2-14pp/yr, no maxDD gain vs random masks; leg
  P&L does not persist. Do not build a leg kill switch on trailing P&L.
- **OVN-MOM (N 939): PASS historical, SMALL now.** LPS overnight momentum (top decile of 252-night mean overnight return, close->
  open): 1998-2015 +15.4bp/night net 2bp/side; decayed to ~+3bp net 2016-26 (official prints 2021-26 +7.2 gross). Overnight
  clientele, not bounce; close-to-close ~0. Forward shadow `ovn_mom_shadow.py` + REGISTRY (OVN-MOM-FWD, 120 nights) runs in
  research-shadows (log-only; OOM-killed until 2026-10-14, now a wide panel, ~200MB peak; first scored night 10-13).
  Live trading needs the user's OK.
- **LUCK-B1/B2/B3 (N 935/940/941): all LUCK.** Random rules on stocks (price), 8-K/actions, crypto alts never beat their nulls; B2's
  passes were firm type (date placebo 34 > real 5). Always include a same-ticker date placebo in a random-search null.
- Crypto alt panel: `data/research/crypto_spot/` (Binance USDT spot 2017-08..2026-09, 249 delisted; build `research/sim/crypto_spot_build/`).
- **WIKI-ATTN (N 936-937): KILL.** Wikipedia pageview spikes -> no overnight or 5d effect (gross -1bp/night, n 5,854, 2016-26).
  Pageview cache `data/research/wiki/` (1,898 articles, 2015-07+) stays for reuse; do not re-run attention spikes on it.
- **WRDS (user's Wharton access, 2026-10-13):** CRSP, Compustat (sec_shortint 1973+), OptionMetrics 1996-2025, TAQ ms 2003-26,
  TRACE/FISD, IBES, TR 13F/insiders, CBOE, Datastream. NO Markit lending (borrow fees stay DATA-LIMITED). `wrds` in .venv, ~/.pgpass.
- **CRSP-EARLY (N 942-943): night leg NOT CONFIRMED on 1992-97** (gross t 2.5 is bid-ask bounce: from the closing mid t 1.33);
  **OVN-MOM mechanism CONFIRMED** (+16.6bp t 8.4, survives midquote/NYSE-only/stale scores) but pre-decimal spreads make the
  net untestable; forward shadow decides. 1992-97 is now TOUCHED for both rules.
- **LUCK-B4 (N 944): LUCK.** 1000 random long-only rules on OptionMetrics IV/skew/PC-volume + Compustat short interest (2001-10): 0 passes, nulls 0. Per-stock option state adds nothing beyond known families (high-IV overnight premium, reversal).
- **LUCK-B5 (N 947): LUCK.** 1000 random long-only rules on IBES consensus/dispersion/revision/LTG features (2001-10): 0 passes, nulls 0, placebo 0; best t 2.00 = revision drift / reversal x value. IBES summary features add nothing.
- **BOND-LEAD (N 948): KILL.** TRACE 2006-15, top-decile issuer bond return -> stock next day: gross -0.5bp/day, within-return-tercile t 0.03. No bond->stock lead. TRACE `cmsn_trd` is NULL from 2012-02 (filter with IS DISTINCT FROM 'Y').
- **LUCK-B6 (N 949): LUCK.** 800 random rules on all CRSP ETFs/ETNs with flow/premium/age/size features (2004-12): 0 passes, nulls 0. Six luck batches across six data families: stop random search until a genuinely new asset panel exists.
- **MODERN-XS (N 977, user request): KILL.** Monthly top-decile sorts on 14 untested traits (value/quality/size/investment/issuance/turnover/$vol), discover 2021-23 -> judge 2024-26: kept sales-yield+ / low-issuance both -13%/yr vs QQQ. With momentum/52w/low-vol/sector/theme already dead, monthly characteristic stock-picking in the modern regime is closed: holding QQQ is the modern "winner" trait.
- **LATE-FLOW (N 945, TAQ 2010-15): KILL.** Late-day signed flow -> overnight: real (+0.9bp gross, monotone deciles) but ~1bp; net -3.1bp. Closing-pressure family closed.
- **Odd-lot tender watch RETIRED (user, 2026-10-13):** tender proceeds take weeks to arrive, locking capital. Not run, not on the digest; `tender_watch.py` keeps a `RETIRED` marker (the registry test skips RETIRED modules) because other modules import its parsers. Do not re-propose odd-lot tenders.
