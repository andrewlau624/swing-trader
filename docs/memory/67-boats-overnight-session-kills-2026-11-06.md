# BOATS overnight session: Asian-demand premium and LETF dislocation both KILL (2026-11-06, N 1088-1089)

- BOATS-PREM (N 1088): Blue Ocean NBBO via Alpaca feed=boats (quotes, not only bars) 2024-09-16..2026-10-30, 531 live nights.
  Close cross -> BOATS bid at 23:00 ET (Korean midday) on 19 a-priori Korean-retail favourites: hedged -2.1bp/night (t -1.34),
  unhedged +2.1. Selling at the BOATS bid loses to the next open cross by 6.8bp (t -2.16). ASIA-minus-control looked positive
  at the bid (+11.2, t 2.36) but it is the spread gap (controls quote 6-34bp half-spreads overnight); at the mid it is -5.4.
  No price-insensitive Asian premium survives the spread. 03:45 ET same.
- BOATS-LETF (N 1089): LETFs track L x their underlying's BOATS move inside the spread (median -1.5..-5.5bp). Buying the
  cheap side (<= -15bp) and selling the open: -3.4bp/event. The rich-side +18bp (t 4) is entirely SOXL/SOXS on a thin SOXX
  quote (both read mispriced in opposite directions at once = underlying quote error); ex-SOX -2.8.
- Useful facts: BOATS is liquid only in mega-caps/LETFs (QQQ/SPY 0.7bp half-spread, TSLA 1.7, TQQQ 1.8 at 23:00); mega-cap
  non-favourites (JPM/PG/V/HD) quote 17-34bp. Cache data/research/boats_asia/ (quotes at 23:00 and 03:45, crosses, daily).
- Ceiling-kills same night (no N): intl ETF NAV gaps (ETF-PD class), EW/factor ETF rebalance days (<= 2pp), LETF up-side short.
- Not tested: exchange overnight sessions after 2026-12-06, in-session dynamics, event nights, index/futures fair value.
  Runners research/sim/boats_asia.py (+ _posthoc.py); out data/research/program/boats_asia_out.txt.
