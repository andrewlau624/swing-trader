# Research memory — session "FinBERT / open NLP discovery" (2026-10-06)

- Ledger + gate math: `research/drafts/nlp_ledger_2026-10-06.md`. Only CEF-TXT (FinBERT tone of N-CSR shareholder
  reports as a filter on CEF-RV, N 887->889) cleared the gate; **KILL both arms** (level -58bp t -1.86 wrong sign; change
  -31bp t -0.79; 0/7 checks). Lazy prices, PREF-EX/Form 4/FOMC/night-leg text filters, CEF proxy text, classifier
  forced-flow discovery: killed at the gate (regex on full text beats a classifier for contractual clauses).
- **Verdict: open-source financial NLP adds no edge beyond price data at this account's reach**; fast text is priced at
  the open, slow text (CEF letters) is commentary. Do not re-open NLP as a signal source.
- Unregistered lead (price-only): CEF-RV entries after a trailing-26w NAV fall are its best trades (dropping them costs
  -705bp t -5.1, both halves); needs its own pre-registration on data CEF-RV was not judged on.
- System `python3` has torch+transformers but a mismatched torchvision: block it (`sys.modules["torchvision"]=None`)
  before importing transformers.
- **CEF-OOS / NAVFALL (N 890-891), same session.** CEF-RV PASSES on untouched 1999-2014 (+333bp t 5.3, alpha +237 t 5.2
  after 0.53*SPY). **But its 2016-26 alpha after 0.76*SPY over the hold is +46bp t 0.74**: the recent "+409..486bp" is
  mostly levered equity beta bought after selloffs. NAV-fall filter passes as registered (+376bp t 3.45 OOS) but ~half is
  SPY rebound. `cef_rv.next_close` fixed (pre-window signals took the window's first close).
- **CEF-ALPHA (N 892-893, 2026-10-07) SUPERSEDES the "+46bp t 0.74" line above** (that used an in-window fitted beta; the
  intercept is beta-sensitive because entries precede big rebounds). Pre-registered beta-matched comparators: CEF-RV minus
  the EW CEF universe incl. delisted = **+125bp/trade t 5.6 (2016-26), +187 t 9.4 (1999-2014)**; minus out-of-window
  beta x SPY = +159 t 3.5. CEF-RV has real alpha in both eras; raw is ~2/3 market. ~+4.8pp/yr excess on deployed capital
  (below the +8pp stand-alone gate; a Roth upgrade over holding beta). Open: same-category peer comparator.
- **CEF-SURV99 (N 895-896): 1999-2014 survivorship is MATERIAL.** Dead CEFs are 71% of 1999-2014 proxy entries; on a
  price-only proxy live funds beat dead funds by +186bp/trade (both halves, ex-2008-09 +104). Bound on the OOS alpha:
  ~+105bp central, ~0 at the conservative end (`cef_surv99_out.txt:22-28`). Pre-2010 dead CEFs often died badly (16%
  lost >10% in the final 6m vs 6% in 2015-26). => The 1999-2014 "OOS pass" is NOT established; 2016-26 (+125bp vs EW CEF,
  benign-death era, ~2pp/yr gap) remains the evidence. History cannot settle it (no dead-fund NAV): the decisive test is
  forward (open-cross execution + log-only shadow). Program N = 896.
