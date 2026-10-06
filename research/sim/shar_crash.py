"""Study SHAR-CRASH: whole-book crash/stress replay, daily-bar form.

Pre-registration: the "Study SHAR-CRASH" amendment in research/drafts/round1_prose.md
(N unchanged, diagnostic; no pass/fail, no tuning). Delisted-complete Sharadar bars let the
two daily-bar legs be replayed through 2000-02, 2008-09, 2011 and 2015-16.

Legs (weights 0.5 / 0.5, live night_w / ibs_w):
  IBS  - exactly the live rule (book.ibs_days): EQ18 ETFs, top-3 12-1 momentum monthly,
         IBS(day close) < 0.2, buy the next open, sell the open after that.
  NIGHT - the daily-bar form of the live night leg. The register's wording is the live
         `loser_picks` at the CLOSE (close(d)/close(d-1)-1 <= -8%, IBS(d) < 0.10, raw
         price 5..2000, ADV$ >= 1e7, vol20 >= .60, corr dedupe .7,
         `night_sizing(crowd_n=30, max_name_pct=0.10)`), buy the close(d), sell
         open(d+1). This runner builds it through nx.collect_trades, which applies the
         same filters plus the live night_tilt(0.25), the weekend gap_scale(0.5),
         delisting prices and back dividends, so the replay is the delisted-complete,
         tradable-outcome form of the live leg. The daily close stands in for the live
         15:40 decision (no pre-2021 minute data): stated.

The noise leg is excluded (no minute data). Combined curve: 0.5*ibs + 0.5*night, rebalanced
daily, no leverage, no margin, gross of costs. One ref, no variants.

Run: PYTHONPATH=. .venv/bin/python research/sim/shar_crash.py
"""
from __future__ import annotations

import pathlib
import time

import numpy as np
import pandas as pd

from research.sim import book, nx
from sharadar import prices as sh_prices
from swingtrader.daily import signals as sg

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "sim" / "shar_crash_out.txt"

WINDOWS = (
    ("2000-01..2002-12", pd.Timestamp("2000-01-01"), pd.Timestamp("2002-12-31")),
    ("2008-01..2009-12", pd.Timestamp("2008-01-01"), pd.Timestamp("2009-12-31")),
    ("2011-01..2011-12", pd.Timestamp("2011-01-01"), pd.Timestamp("2011-12-31")),
    ("2015-08..2016-02", pd.Timestamp("2015-08-01"), pd.Timestamp("2016-02-29")),
)
PAD = pd.Timedelta(days=45)          # bars kept either side of a window (vol20 / next-session)
EQ18 = book.EQ18


# ------------------------------------------------------------------ IBS leg
def etf_frames():
    """(open, high, low, close) frames, session-date index, one column per EQ18 ETF."""
    df = sh_prices(EQ18, "1998-06-01", "2016-04-30", adjust="split", source="funds")
    df = df[df["ticker"].isin(EQ18)]
    df = df.assign(date=pd.to_datetime(df["date"]))
    out = {}
    for name, col in (("open", "open"), ("high", "high"), ("low", "low"), ("close", "close")):
        out[name] = df.pivot(index="date", columns="ticker", values=col).sort_index()
    return out["open"], out["high"], out["low"], out["close"]


def ibs_daily(O, H, L, C) -> pd.Series:
    """Equal-weight daily return of the live IBS leg, dated by the SIGNAL day d:
    IBS(close d) < 0.2, buy open(d+1), sell open(d+2). Same logic as book.ibs_days;
    copied here because book.ibs_days is hard-wired to the 2021-26 research cache."""
    closes = C[EQ18]
    days = closes.index
    out, mom_cache = {}, {}
    for j in range(260, len(days) - 2):
        d, today = days[j], days[j + 1]
        m = today.to_period("M")
        if m not in mom_cache:
            mom_cache[m] = sg.momentum_top(closes[closes.index < today], today, 3)
        uni = mom_cache[m]
        last = {s: {"high": H.at[d, s], "low": L.at[d, s], "close": C.at[d, s]} for s in uni}
        tg = sg.ibs_targets(last, 0.2)
        legs = [O.at[days[j + 2], s] / O.at[days[j + 1], s] - 1 for s in tg
                if np.isfinite(O.at[days[j + 1], s]) and np.isfinite(O.at[days[j + 2], s])]
        if legs:
            out[d] = float(np.mean(legs))
    return pd.Series(out).sort_index()


def etf_universe_report(O) -> pd.DataFrame:
    """First session each EQ18 ETF has a bar (which sessions can signal at all)."""
    return O[EQ18].apply(lambda c: c.first_valid_index()).sort_values()


# ------------------------------------------------------------------ night leg
def night_daily(lo, hi, sep, sfp, master, act):
    """Per-signal-day night-leg return = sum(per*ret) from the delisted-complete panel.

    Uses nx.collect_trades (the registered night-rule engine) over [lo, hi]; bars are
    loaded with a 45-day pad so vol20 / the next session exist at the edges."""
    parts = [t[(t["date"] >= lo - PAD) & (t["date"] <= hi + PAD)] for t in (sep, sfp)]
    bars = pd.concat(parts, ignore_index=True).sort_values(["ticker", "date"], kind="mergesort")
    bars = bars.reset_index(drop=True)
    pn = nx.build_panel(bars)
    tr = nx.collect_trades(pn, master, act, "primary", lo, hi)["trades"]
    if tr is None or tr.empty:
        return pd.Series(dtype=float), tr, len(bars)
    # Keep EVERY outcome kind. nx.collect_trades scores delist_nopx and nobar_halt at
    # -100% (nx.py:623/625), exactly as nx.leg_series (nx.py:670-675) does; dropping them
    # would silently remove the worst overnight outcomes (the SHAR-CRASH selection bug).
    r = tr.groupby("date").apply(lambda g: float((g["per"] * g["ret"]).sum()))
    return r.sort_index(), tr, len(bars)


# ------------------------------------------------------------- drawdown stats
def curve_stats(r: pd.Series) -> dict:
    r = r.fillna(0.0)
    if r.empty:
        return dict(n=0)
    eq = (1 + r).cumprod()
    peak = eq.cummax()
    dd = eq / peak - 1.0
    mdd = float(dd.min())
    trough = dd.idxmin()
    prior_peak = float(peak.loc[trough])
    after = eq.loc[trough:]
    rec = after[after >= prior_peak]
    rec_sessions = int((after.index.get_loc(rec.index[0]))) if len(rec) else None
    lr = np.log1p(r)
    w5 = float(np.expm1(lr.rolling(5).sum()).min()) if len(r) >= 5 else np.nan
    w20 = float(np.expm1(lr.rolling(20).sum()).min()) if len(r) >= 20 else np.nan
    return dict(n=len(r), cum=float(eq.iloc[-1] - 1.0), mdd=mdd, w5=w5, w20=w20,
                rec=rec_sessions, trough=str(trough.date()),
                halt=mdd <= -sg.HALT_DRAWDOWN, lever=mdd <= -sg.LEVER_MAX_DD)


def main() -> int:
    t0 = time.time()
    lines: list[str] = []

    def p(s=""):
        lines.append(s)

    p("Study SHAR-CRASH - whole-book crash/stress replay, daily-bar form")
    p("pre-reg: research/drafts/round1_prose.md (N unchanged; diagnostic, one ref, no variants)")
    p("legs 0.5 IBS (EQ18, top-3 12-1 mom, IBS<0.2, open d+1 -> open d+2) +")
    p("     0.5 NIGHT (loser_picks at the close, buy close d -> open d+1; daily close as the")
    p("     15:40 proxy; delisted-complete Sharadar panel, live tilt/weekend-scale/delist px)")
    p("combined: 0.5/0.5 rebalanced daily, no leverage, no margin, GROSS of costs")
    p(f"generated: {pd.Timestamp.now():%Y-%m-%d %H:%M}  python {time.strftime('%H:%M:%S')}")
    p()

    O, H, L, C = etf_frames()
    first = etf_universe_report(O)
    p("EQ18 first session with a bar (window universe cue):")
    p("  " + ", ".join(f"{s}:{str(d)[:10]}" for s, d in first.items()))
    p()

    ibs_all = ibs_daily(O, H, L, C)
    p(f"IBS daily-return series: {len(ibs_all)} signal days "
      f"[{ibs_all.index.min().date()}..{ibs_all.index.max().date()}]")
    p()

    P = nx.Paths()
    master = nx.load_master(P)
    act = nx.read_table(P, "ACTIONS")
    sep = nx.read_table(P, "SEP")
    sfp = nx.read_table(P, "SFP")
    p(f"Sharadar: SEP {len(sep):,} rows, SFP {len(sfp):,} rows, "
      f"master {len(master):,}, ACTIONS {len(act):,}")

    rows = []
    for label, lo, hi in WINDOWS:
        idx = C.index[(C.index >= lo) & (C.index <= hi)]
        ibs_sig = ibs_all.reindex(idx)
        ibs = ibs_sig.fillna(0.0)
        night, tr, nbars = night_daily(lo, hi, sep, sfp, master, act)
        night_r = night.reindex(idx).fillna(0.0)
        r = 0.5 * ibs + 0.5 * night_r
        st = curve_stats(r)
        n_ibs = int(ibs_sig.notna().sum())
        n_night = int(len(night))
        n_picks = 0 if tr is None or tr.empty else len(tr)
        kinds = "" if tr is None or tr.empty else \
            " ".join(f"{k}:{v}" for k, v in tr["kind"].value_counts().sort_index().items())
        ibs_cum = float((1 + ibs).prod() - 1)
        ngt_cum = float((1 + night_r).prod() - 1)
        rows.append((label, st, n_ibs, n_night, n_picks, nbars, ibs_cum, ngt_cum, kinds))

    p()
    p("Per window (combined daily equal-weight book, gross):")
    hdr = (f"{'window':20s} {'cum':>9s} {'maxDD':>8s} {'worst5d':>9s} {'worst20d':>9s} "
           f"{'recov':>6s} {'halt':>5s} {'lever':>6s} {'ibs_cum':>9s} {'ngt_cum':>9s} "
           f"{'n':>5s} {'ibs_d':>6s} {'ngt_d':>6s} {'picks':>6s}")
    p(hdr)
    p("-" * len(hdr))
    for label, st, n_ibs, n_night, n_picks, nbars, ibs_cum, ngt_cum, kinds in rows:
        rec = "-" if st["rec"] is None else str(st["rec"])
        p(f"{label:20s} {st['cum']*100:8.2f}% {st['mdd']*100:7.2f}% "
          f"{st['w5']*100:8.2f}% {st['w20']*100:8.2f}% {rec:>6s} "
          f"{'YES' if st['halt'] else 'no':>5s} {'YES' if st['lever'] else 'no':>6s} "
          f"{ibs_cum*100:8.2f}% {ngt_cum*100:8.2f}% "
          f"{st['n']:>5d} {n_ibs:>6d} {n_night:>6d} {n_picks:>6d}")
    p()
    p("Night outcome kinds per window (all kept; delist_nopx / nobar_halt score -100%):")
    for label, st, n_ibs, n_night, n_picks, nbars, ibs_cum, ngt_cum, kinds in rows:
        p(f"  {label:20s} {kinds or '-'}")
    p()
    p("maxDD is the peak-to-trough of the compounded curve; worst5d/20d are the worst")
    p("compounded 5- and 20-session returns in the window; recov = sessions from the")
    p(f"trough back to the prior peak ('-' = never in the window). halt/lever = maxDD would")
    p(f"breach signals.HALT_DRAWDOWN ({sg.HALT_DRAWDOWN:.2f}) / signals.LEVER_MAX_DD "
      f"({sg.LEVER_MAX_DD:.2f}).")
    p("ibs_cum / ngt_cum = each leg's own compounded return over the window (gross);")
    p("ibs_d = sessions with an IBS signal; ngt_d = sessions with a night pick;")
    p("picks = night trades; n = combined sessions in the window.")
    p()
    p("Caveats: daily-close proxy for the live 15:40 night decision (optimistic on the")
    p("entry); EQ18 universe grows during 2000-02 (IWM 2000-05, SMH 2000-06, EEM 2003,")
    p("XBI 2006), so early-window IBS uses fewer names; night outcomes keep EVERY kind,")
    p("with delist_nopx / nobar_halt scored at -100% exactly as nx.collect_trades does")
    p("(delisting prices / back dividends from Sharadar; fully-removed tickers retained).")
    p("No costs, no leverage, no margin, no deposits; weights are the live leg weights.")
    p(f"\nelapsed {time.time()-t0:.1f}s")

    text = "\n".join(lines)
    OUT.write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
