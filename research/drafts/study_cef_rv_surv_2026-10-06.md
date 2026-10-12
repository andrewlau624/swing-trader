# Study CEF-RV survivorship attack — free angles only (2026-10-06, follow-up to N 860)

No new pre-registration increment: this is the registered follow-up the N 860 study promised
("a PASS is recorded PROMISING-SURV-LIMITED and requires a delisted-complete replication"). Runner
`research/sim/cef_rv_surv.py` -> `cef_rv_surv_out.txt`. No tuning of the frozen rule.

## What the panel is missing (the concern, quantified)
`tickers.parquet` (`category=CEF`, deduped by permaticker) = **1,074 CEFs** 1996-2026: 370 live /
**704 delisted**. CEFConnect's `funds` list = **355 tickers**. So the judged panel can never see
**66% of the CEF universe** (every fund that died by 2026), plus 20 currently-live funds.

## Free probes run
1. **Births / backfill (a).** Panel first date vs Sharadar `firstpricedate`: median gap **1 day**;
   109/351 funds have panel history starting before Sharadar's price series — but a trade is
   impossible there (entry needs an SFP close). No fabricated pre-listing history. Restricting to
   funds whose panel history starts **2005+** (post data-floor, full life present) gives **+594bp** vs
   +474bp full — the effect is *stronger* in the youngest, least survivor-selected cohort.
2. **Entry-year cohorts (b).** 11/12 entry years positive; ex-2020 **+340bp**; the one negative year
   is 2021 (-21bp); 2020 is +1203bp on 584 trades. Mean hold 14.0 weeks. A survivorship gradient
   (strong early, weak late) is absent — this is a regime pattern, not attrition.
3. **Delisted NAV source (c).** No free daily/weekly source exists. CEFConnect returns
   `{"Data":null}` for dead tickers (verified live: FHY null; DPG/GAB return NAVData). EDGAR gives
   N-Q/N-CSR at quarterly/semi-annual frequency only; N-PORT has **monthly** NAV/returns for
   delisted funds from 2019 (e.g. MHN: 26 NPORT-P), i.e. a viable but heavy scrape target
   (~26 filings x ~700 funds) that is still too coarse for a weekly rule. **Not buildable free in-session.**
4. **Bias direction (d).** Delisted CEF final-window **total** returns are positive, not crashes:
   final 6m +4.96% (68% > 0), 12m +7.98%. Equal-weight CEF universe 2000+ : delisted-complete
   **5.2%/yr** vs survivors-only **7.2%/yr** -> survivorship gap **~2.0pp/yr**. CEFs die benignly
   (liquidation/conversion near NAV), unlike delisted equities. A ~2pp/yr average gap cannot create a
   +340bp/trade (≈12%/yr) effect.

## New diagnostic (e): is the edge real discount convergence, or a thin-close bounce?
The +474bp is 50x the CEF literature (2-5%/yr), so the program's PRV lesson (thin-security daily-close
reversal = bid-ask bounce until proven otherwise) must be checked. On the 2016+ judge window:
- **NAV decomposition:** long trade price return **+303bp**, of which NAV return **+22bp** and the
  price-vs-NAV (discount) component **+281bp**. The edge is ~all *discount convergence*, not NAV drift.
- **Mirror:** short-at-premium-extreme price return **-219bp** — symmetric (expected for a two-sided
  discount mechanism, so not damning by itself).
- **Permuted-NAV placebo:** shuffling each fund's NAV series (anchor becomes decorative) collapses the
  effect to **+34bp** (n 10,745). The NAV anchor does real work — the result is not generic
  weekly price mean-reversion.
Residual risk: the return lives **entirely in the price leg**; if a CEF's weekly close is a thin/stale
last trade rather than the official closing print, part of +281bp could be close noise. **An
official-cross execution test (entry/exit at the SIP closing cross) is the one remaining decisive
attack and is the gate before any upgrade.** Do not size on the current panel.

## Retail feasibility (f) — executable at $250-1k
Median CEF daily $vol **$962k** (p5 $152k). $250 and $1k are <= 10% of ADV for **100%** of the panel;
87% of judged trades are in >= $250k-ADV funds, 49% in >= $1M. Live SIP NBBO (345 CEFs, 2026-10-05
15:00 ET): relative spread p25/50/75/90 = **16/26/45/73bp** (median ~26bp round trip). A +340bp
14-week edge clears the spread; **capacity, not cost, is the constraint.** $/$/DD to be tabulated in
the shadow spec at $2.3k / $10k / $25k.

**Executable subset flagged:** joining the judged trades to today's ADV + NBBO, **64% of the 3,765
trades (217 funds) sit in names with ADV >= $250k and NBBO spread <= 40bp**; 42% also clear $1M ADV.
Only 1.2% of trades are in names with no live quote (liquidated since). The tradable core is the
high-ADV, tight-spread CEFs.

## Verdict
**CEF-RV survives every free survivors-free / robustness variant and is NOT killed.** Verdict stays
**PROMISING-SURV-LIMITED**, now with a stronger free bound: the missing 66% die benignly (~2pp/yr
average gap), the youngest cohort is strongest, and the anchor is non-decorative. It cannot be
upgraded on free data (no weekly delisted NAV) and it carries one untested artifact risk (thin-close
execution). Family remains **alive** for a log-only forward shadow; do not size.

## Reviewer notes (2026-10-06): 0/7 false-pass calibration background
Per PCAL, the PASS machinery's background false-pass rate is ~0/7; the CEF-RV PASS is therefore
informative, but this attack's job was to bound the two known inflators (survivorship, thin-close
execution), not to re-litigate the gate.

## Prepared (not deployed): shadow + Roth pilot
- **Shadow spec (log-only, no orders):** each Friday, on the panel, emit the CEF-RV signal for the
  next week (fund, disc percentile, last close/NAV); score the forward path vs the frozen rule at the
  next two Friday closes + the official closing cross. Registry entry in `swingtrader/daily/testing.py`
  required **in the same commit as the code** when built. Not built here.
- **Roth pilot (one line):** a single ~$250 Roth position (no shorting needed, dividend untaxed) in
  the widest-discount liquid CEF at the signal, held to the median-discount exit, with the shadow
  logging whether the SFP close and the official closing cross print together.
