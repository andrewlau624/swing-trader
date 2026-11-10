"""QP-RUNUP-FWD (N 1203): log-only forward shadow of the IPO quiet-period run-up (round1_prose.md "QP-RUNUP-FWD"; research
QP-RUNUP N 1201 / QP-RUNUP-CRSP N 1202, research/sim/qp_init.py runup_returns). Never places orders.

Rule (frozen; do not change it here): F = the first SIP daily bar of a new listing; x = the first regular session with date
>= F + 25 calendar days (qp_init.runup_returns: d.date >= F + K days); buy the official 16:00 closing cross of session x-3, sell
the closing cross of session x-1. Excess vs the EW cross-to-cross return of the other universe IPOs aged 60-250 sessions at x-3
(qp_init.cohort_control), also vs SPY and IWM; cost 5bp/side ($10+ and median $vol >= $10M) else 10bp, as qp_init.cost.

Source: Nasdaq's IPO calendar JSON (api.nasdaq.com/api/ipo/calendar?date=YYYY-MM, "priced" rows) via cef_nav._get (same
generic headers). The calendar is cached in state/qp-runup-ipos.json, seeded 14 months back on the first run (the cohort needs
deals up to ~250 sessions old); the current and previous months are re-fetched every run. Universe filters and the forward
amendments (decide on data through x-4) are in the prose; the code below is the only implementation.

Status flow per deal in state/qp-runup.jsonl (append-only; the last row per id wins): scheduled (F confirmed, x dates fixed)
-> signal (x-3 morning: filters pass on data through x-4; a SIGNAL line names the buy) or skipped -> entered (x-3 close cross
and the 15:45-15:50 SIP NBBO logged) -> scored (x-1 close cross, NBBO, cohort/SPY/IWM excess, costs) or void.
Deals that fail a universe filter at F get one `excluded` row. Only deals with x-3 >= START enter the forward sample.

Regular hours: sessions come from the exchange calendar (brokers.regular_sessions, validated by signals.regular_clock through
cef_rights_shadow.session_days), bars are labelled by marketdata.trade_date (sip_daily), prices are the official crosses
(pref_ex_shadow.crosses via marketdata.official_crosses). A session counts as closed 16 minutes after its 16:00/13:00 close.
"""
from __future__ import annotations

import datetime as dt
import json
import statistics as st
from pathlib import Path

import pandas as pd

LOG_NAME = "qp-runup.jsonl"
CAL_NAME = "qp-runup-ipos.json"
START = "2026-11-11"                 # first x-3 in the forward sample (pre-registered 2026-11-10)
K = 25                               # post-JOBS 25-day quiet period (qp_init.K_of outside 2002-08..2012-04)
SEED_MONTHS = 14
AGE_LO, AGE_HI = 60, 250             # cohort age window in sessions at x-3
GATE_N, KILL_N, END_N = 40, 80, 120
SIP_DELAY = dt.timedelta(minutes=16)
QUOTE_HM = "15:45"                   # last valid NBBO in 15:45-15:50 ET = the MOC cutoff
RULE = dict(rule="QP-RUNUP N 1201", K=K, entry="close cross x-3", exit="close cross x-1",
            x="first session >= F+25 cal days", cohort=f"universe IPOs aged {AGE_LO}-{AGE_HI} sessions at x-3",
            cost="5bp/side if px>=10 and adv>=10M else 10bp", filters="px(x-4)>=3, median $vol 2..x-4 >= 2M")


def _read(path: Path) -> list[dict]:
    from .ovn_mom_shadow import _read as r
    return r(path)


def fold(rows: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for r in rows:
        out[r["id"]] = {**out.get(r["id"], {}), **r}
    return out


# ------------------------------------------------------------------ calendar (pure)

def parse_calendar(raw: list[dict]) -> list[dict]:
    """Nasdaq 'priced' rows -> [{id, ticker, name, exchange, priced (ISO), offer, shares}]."""
    out = []
    for r in raw or []:
        t = (r.get("proposedTickerSymbol") or "").strip().upper()
        try:
            p = dt.datetime.strptime((r.get("pricedDate") or "").strip(), "%m/%d/%Y").date().isoformat()
        except ValueError:
            continue
        if not t:
            continue
        try:
            offer = float(str(r.get("proposedSharePrice")).replace("$", "").replace(",", ""))
        except (TypeError, ValueError):
            offer = None
        try:
            shares = float(str(r.get("sharesOffered")).replace(",", ""))
        except (TypeError, ValueError):
            shares = None
        out.append(dict(id=f"{t}:{p}", ticker=t, name=(r.get("companyName") or "").strip(),
                        exchange=r.get("proposedExchange"), priced=p, offer=offer, shares=shares))
    return out


def name_reason(ipo: dict) -> str | None:
    """Non-common / SPAC exclusions available from the calendar alone (stands in for Sharadar category + SIC 6770)."""
    n, t = ipo["name"].upper(), ipo["ticker"]
    if "ACQUISITION" in n or "SPAC" in n:
        return "spac name"
    if ipo.get("offer") == 10.0 and len(t) == 5 and t.endswith("U"):
        return "spac unit"
    if "FUND" in n.split() or n.endswith(" FUND"):
        return "fund"
    if not t.isalpha():
        return "not a plain ticker"
    return None


def classify(ipo: dict, bars: pd.DataFrame | None, cutoff: str) -> tuple[str | None, str | None]:
    """(F, None) if the deal is in the universe on raw bars dated <= cutoff, else (F or None, reason).
    Same checks as qp_init.load/build_events: first price within 3 days of the listing, day-1 close >= $5 and $vol >= $5M,
    first-20-close CV >= 1% (only the closes up to `cutoff` are used: amendment a)."""
    r = name_reason(ipo)
    if r:
        return None, r
    if bars is None or bars.empty:
        return None, "no bars"
    idx = pd.to_datetime(bars.index)
    p = pd.Timestamp(ipo["priced"])
    if ((idx < p) & (idx >= p - dt.timedelta(days=30))).any():
        return None, "bars before pricing (uplist / reused ticker)"
    b = bars[(idx >= p) & (idx <= pd.Timestamp(cutoff))]
    if b.empty:
        return None, "no bars"
    F = pd.Timestamp(b.index[0])
    if (F - p).days > 3:
        return None, "first bar > 3 days after pricing"
    Fs = str(F.date())
    c1, v1 = float(b.close.iloc[0]), float(b.volume.iloc[0])
    if c1 < 5 or c1 * v1 < 5e6:
        return Fs, "day-1 close < $5 or $vol < $5M"
    c20 = b.close.iloc[:20].astype(float)
    if len(c20) >= 2 and c20.std() / c20.mean() < 0.01:
        return Fs, "pinned closes (CV < 1%)"
    return Fs, None


def x_dates(F: str, days: list[str]) -> dict | None:
    """x = first session >= F + K calendar days; e = x-3, s = x-1 (sessions of the exchange calendar)."""
    lim = str((pd.Timestamp(F) + dt.timedelta(days=K)).date())
    i = next((j for j, d in enumerate(days) if d >= lim), None)
    if i is None or i < 3:
        return None
    return dict(x=days[i], e=days[i - 3], s=days[i - 1])


def entry_check(bars: pd.DataFrame, F: str, upto: str) -> dict:
    """Entry filters on raw bars from F through `upto` (inclusive): close(upto) >= $3, median close x volume over sessions
    2..upto >= $2M (qp_init.runup_returns, iloc[1:e+1]); returns px, adv, ok, reason, cost tier."""
    idx = pd.to_datetime(bars.index)
    b = bars[(idx >= pd.Timestamp(F)) & (idx <= pd.Timestamp(upto))]
    if b.empty or str(pd.Timestamp(b.index[-1]).date()) != upto:
        return dict(ok=False, reason=f"no bar for {upto}", px=None, adv=None)
    px = float(b.close.iloc[-1])
    dv = (b.close.astype(float) * b.volume.astype(float)).iloc[1:]
    adv = float(dv.median()) if len(dv) else float("nan")
    ok = px >= 3 and adv >= 2e6
    reason = None if ok else ("close < $3" if px < 3 else "median $vol < $2M")
    side = 0.0005 if (px >= 10 and adv >= 1e7) else 0.0010
    return dict(ok=ok, reason=reason, px=round(px, 4), adv=round(adv, 0) if adv == adv else None, side=side)


def cohort_members(univ: dict[str, str], days: list[str], e: str, self_t: str) -> list[str]:
    """Tickers of universe IPOs (ticker -> F) aged AGE_LO..AGE_HI sessions at e (qp_init.cohort_control: pos(e) - pos(F))."""
    pos = {d: i for i, d in enumerate(days)}
    if e not in pos:
        return []
    out = []
    for t, F in univ.items():
        if t == self_t or F not in pos:
            continue
        a = pos[e] - pos[F]
        if AGE_LO <= a <= AGE_HI:
            out.append(t)
    return sorted(out)


def two_session_ret(t: str, e: str, s: str, cross: dict, raw: dict, adj: dict) -> tuple[float | None, str | None]:
    """Cross(s) / cross(e) - 1, scaled by the split/dividend adjustment between e and s; daily-bar close if a cross is missing."""
    def px(d):
        c = (cross.get((t, d)) or (None, None))[1]
        if c:
            return float(c), "cross"
        b = raw.get(t)
        if b is not None and pd.Timestamp(d) in pd.to_datetime(b.index):
            return float(b.close[pd.to_datetime(b.index) == pd.Timestamp(d)].iloc[0]), "bar"
        return None, None
    (pe, se_), (px_, sx) = px(e), px(s)
    if not pe or not px_:
        return None, None
    f = 1.0
    a, b = adj.get(t), raw.get(t)
    if a is not None and b is not None:
        ai, bi = pd.to_datetime(a.index), pd.to_datetime(b.index)
        try:
            ae, as_ = float(a.close[ai == pd.Timestamp(e)].iloc[0]), float(a.close[ai == pd.Timestamp(s)].iloc[0])
            be, bs = float(b.close[bi == pd.Timestamp(e)].iloc[0]), float(b.close[bi == pd.Timestamp(s)].iloc[0])
            f = (as_ / bs) / (ae / be)
        except (IndexError, ZeroDivisionError):
            f = 1.0
    return px_ / pe * f - 1, ("cross" if se_ == sx == "cross" else "bar")


def half_spread(q: tuple | None) -> float | None:
    if not q or not q[0] or not q[1] or q[1] <= q[0]:
        return None
    m = (q[0] + q[1]) / 2
    return (q[1] - q[0]) / 2 / m


# ------------------------------------------------------------------ stats / reader

def stats(rows: list[dict]) -> dict:
    from .exec_bandit_shadow import _clustered
    sc = [r for r in fold(rows).values() if r.get("status") == "scored" and r.get("xc") is not None]
    by: dict[str, list[float]] = {}
    for r in sc:
        by.setdefault(r["e"], []).append(r["xc"])
    m, se, n = _clustered(by)
    t = m / se if n and se and se != float("inf") else 0.0
    med = st.median([r["xc"] for r in sc]) if sc else 0.0
    sp = [r["xc_spread"] for r in sc if r.get("xc_spread") is not None]
    msp = sum(sp) / len(sp) if sp else None
    passed = n >= GATE_N and m > 0 and t >= 2 and med > 0 and (msp is not None and msp > 0)
    state = ("PASS -> propose a small live test (user decision)" if passed else
             "KILL (mean <= 0 at 80)" if n >= KILL_N and m <= 0 else
             "KILL (no pass by 120)" if n >= END_N else f"collecting ({n}/{GATE_N})")
    return dict(n=n, mean=m, t=t, median=med, spread_net=msp, state=state)


def line(rows: list[dict]) -> str:
    f = fold(rows)
    s = stats(rows)
    up = sorted((r["e"], r["ticker"]) for r in f.values() if r.get("status") in ("scheduled", "signal", "entered"))
    nxt = ", ".join(f"{t} buy {e}" for e, t in up[:4])
    body = (f"{s['n']} scored, net excess vs IPO cohort {s['mean']*1e4:+.1f}bp (t {s['t']:.2f}, median {s['median']*1e4:+.1f}"
            + (f", net of 15:50 spread {s['spread_net']*1e4:+.1f}" if s["spread_net"] is not None else "") + ")") if s["n"] else "0 scored"
    return f"QP-RUNUP-FWD: {body}; {len(up)} open" + (f" (next: {nxt})" if nxt else "") + f"; {s['state']}"


# ------------------------------------------------------------------ run

def _months(today: dt.date, n: int) -> list[str]:
    y, m, out = today.year, today.month, []
    for _ in range(n + 1):
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y, m - 1) if m > 1 else (y - 1, 12)
    return sorted(out)


def refresh_calendar(state_dir: Path, today: dt.date, cal_fn, log=print) -> list[dict]:
    p = state_dir / CAL_NAME
    c = json.loads(p.read_text()) if p.exists() else {"months": {}, "ipos": {}}
    ms = _months(today, SEED_MONTHS)
    for m in ms:
        if m in c["months"] and m not in ms[-2:]:
            continue
        raw = cal_fn(m)
        if raw is None:
            log(f"[qp-runup] IPO calendar {m} unavailable; using the cached rows")
            continue
        for ipo in parse_calendar(raw):
            c["ipos"].setdefault(ipo["id"], ipo)
        c["months"][m] = str(today)
    state_dir.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(c, indent=0, sort_keys=True))
    return sorted(c["ipos"].values(), key=lambda r: r["priced"])


def _nasdaq_month(m: str):
    from .cef_nav import _get
    d = _get("ipo/calendar", {"date": m})
    if d is None:
        return None
    return (d.get("priced") or {}).get("rows") or []


def run(state_dir: Path, log=print, now: dt.datetime | None = None, cal_fn=None, bars_fn=None, sessions_fn=None,
        crosses_fn=None, quotes_fn=None, adj_fn=None) -> list[dict]:
    from zoneinfo import ZoneInfo
    from . import marketdata as md
    from .cef_rights_shadow import session_days
    state_dir = Path(state_dir)
    now = now or dt.datetime.now(dt.timezone.utc)
    today = now.astimezone(ZoneInfo(md.ET)).date()
    path = state_dir / LOG_NAME
    rows = _read(path)
    cal_fn = cal_fn or _nasdaq_month
    if sessions_fn is None:
        from .brokers import regular_sessions as sessions_fn
    if bars_fn is None:
        bars_fn = lambda syms, start: md.sip_daily(syms, start, adjustment="raw")  # noqa: E731
    if adj_fn is None:
        adj_fn = lambda syms, a, b: md.sip_daily(syms, a, pd.Timestamp(b) + dt.timedelta(days=1), adjustment="all")  # noqa: E731
    if crosses_fn is None:
        crosses_fn = md.official_crosses
    if quotes_fn is None:
        from .exdate_open_shadow import _headers
        from .pref_ex_shadow import close_quotes
        quotes_fn = lambda syms, day: close_quotes(syms, day, _headers(), hm=QUOTE_HM)  # noqa: E731

    ipos = refresh_calendar(state_dir, today, cal_fn, log)
    start = today - dt.timedelta(days=31 * SEED_MONTHS + 60)
    ss = sorted(sessions_fn(start, today + dt.timedelta(days=75)))
    days = session_days(ss)
    close_at = {d: c for d, (o, c) in zip(days, ss)}
    closed = lambda d: d in close_at and close_at[d] + SIP_DELAY <= now  # noqa: E731
    done = [d for d in days if closed(d)]
    last_done = done[-1] if done else None
    prev = {d: days[i - 1] for i, d in enumerate(days) if i}
    if not ipos or last_done is None:
        log("[qp-runup] no calendar rows or sessions; nothing logged")
        return rows
    syms = sorted({i["ticker"] for i in ipos if not name_reason(i)})
    bstart = min(i["priced"] for i in ipos)
    raw = bars_fn(syms, str((pd.Timestamp(bstart) - dt.timedelta(days=35)).date())) or {}
    # nothing after the last closed session is ever used (no partial bar)
    raw = {t: b[pd.to_datetime(b.index) <= pd.Timestamp(last_done)] for t, b in raw.items()}
    f = fold(rows)
    new: list[dict] = []

    def emit(r: dict, **kw):
        base = {k: v for k, v in r.items() if k not in ("ts",)}
        x = {**base, **kw, "ts": now.isoformat(timespec="seconds")}
        new.append(x)
        f[x["id"]] = x
        return x

    # 1) new deals: confirm F, fix x, write scheduled / excluded
    for ipo in ipos:
        if ipo["id"] in f or name_reason(ipo):
            continue
        b = raw.get(ipo["ticker"])
        F, why = classify(ipo, b, last_done)
        if F is None:
            continue                                        # not trading yet (or never): retried next run
        xd = x_dates(F, days)
        if xd is None or xd["e"] < START:
            continue                                        # history / cohort only, never scored
        base = dict(ipo, F=F, **xd, params=RULE)
        if why and "CV" not in why:
            emit(base, status="excluded", reason=why)
        else:
            emit(base, status="scheduled")
            log(f"[qp-runup] scheduled {ipo['ticker']} (F {F}): buy the {xd['e']} close cross, sell the {xd['s']} close (x {xd['x']})")

    # 2) advance open deals
    univ = {}
    for ipo in ipos:
        Fu, why = classify(ipo, raw.get(ipo["ticker"]), last_done)
        if Fu and not why:
            univ[ipo["ticker"]] = Fu
    for r in sorted(f.values(), key=lambda r: r["e"]):
        st_ = r.get("status")
        if st_ not in ("scheduled", "signal", "entered"):
            continue
        e, s, t = r["e"], r["s"], r["ticker"]
        b = raw.get(t)
        if st_ == "scheduled" and str(today) >= e:
            upto = prev[e]
            if b is None or not closed(upto):
                continue
            ipo = {k: r[k] for k in ("id", "ticker", "name", "exchange", "priced", "offer", "shares")}
            _, why = classify(ipo, b, upto)
            ec = entry_check(b, r["F"], upto)
            late = str(today) > e or closed(e)
            if why or not ec["ok"]:
                if not ec["ok"] and ec["reason"].startswith("no bar") and not closed(e):
                    continue                                # x-4 bar not published yet: retry
                r = emit(r, status="skipped", reason=why or ec["reason"], entry=ec, late=late)
                continue
            r = emit(r, status="signal", entry=ec, late=late)
            st_ = "signal"
            log(f"[qp-runup] SIGNAL buy {t} at the {e} 16:00 closing cross, sell at the {s} close (x-1; x {r['x']}); "
                f"px(x-4) {ec['px']} median $vol {ec['adv']/1e6:.1f}M, cost {ec['side']*1e4:.0f}bp/side"
                + (" [late]" if late else "") + " (log-only, no order placed)")
        if st_ == "signal" and closed(e):
            c = crosses_fn([t], e, e)
            q = quotes_fn([t], e)
            pe = (c.get((t, e)) or (None, None))[1]
            r = emit(r, status="entered", entry_px=pe, entry_src="cross" if pe else "bar", entry_nbbo=q.get(t),
                     entry_hs=half_spread(q.get(t)))
            st_ = "entered"
        if st_ == "entered" and closed(s):
            mem = cohort_members(univ, days, e, t)
            allsym = sorted(set(mem) | {t, "SPY", "IWM"})
            cr = crosses_fn(allsym, e, s)
            adj = adj_fn(allsym, e, s) or {}
            rawb = {**raw, **(bars_fn(["SPY", "IWM"], e) or {})}
            ret, src = two_session_ret(t, e, s, cr, rawb, adj)
            if ret is None:
                if len(done) - 1 - done.index(s) >= 5:
                    emit(r, status="void", reason="no price at x-3 or x-1, 5 sessions after x-1")
                continue
            cv = [v for m in mem if (v := two_session_ret(m, e, s, cr, rawb, adj)[0]) is not None]
            ctl = sum(cv) / len(cv) if len(cv) >= 5 else None
            spy = two_session_ret("SPY", e, s, cr, rawb, adj)[0]
            iwm = two_session_ret("IWM", e, s, cr, rawb, adj)[0]
            q = quotes_fn([t], s)
            side = r["entry"]["side"]
            hs_x = half_spread(q.get(t))
            hs_e = r.get("entry_hs")
            c1 = 2 * side
            st_ok = entry_check(b, r["F"], e) if b is not None else {"ok": None}
            rd = lambda v: None if v is None else round(v, 6)  # noqa: E731
            emit(r, status="scored", exit_px=(cr.get((t, s)) or (None, None))[1], px_src=src, exit_nbbo=q.get(t),
                 exit_hs=hs_x, ret=rd(ret), ctl=rd(ctl), n_ctl=len(cv), spy=rd(spy), iwm=rd(iwm), cost=c1,
                 xc=rd(ret - ctl - c1) if ctl is not None else None,
                 xc_2x=rd(ret - ctl - 2 * c1) if ctl is not None else None,
                 xc_3x=rd(ret - ctl - 3 * c1) if ctl is not None else None,
                 xc_spread=rd(ret - ctl - hs_e - hs_x) if (ctl is not None and hs_e is not None and hs_x is not None) else None,
                 xs_spy=rd(ret - spy - c1) if spy is not None else None, xs_iwm=rd(ret - iwm - c1) if iwm is not None else None,
                 raw_net=rd(ret - c1), study_entry_ok=st_ok.get("ok"))
            log(f"[qp-runup] scored {t} {e}->{s}: raw {ret*1e4:+.0f}bp, cohort "
                + (f"{ctl*1e4:+.0f}bp (n {len(cv)})" if ctl is not None else f"n/a (n {len(cv)} < 5)")
                + (f", net excess {(ret - ctl - c1)*1e4:+.0f}bp" if ctl is not None else ""))
    if new:
        state_dir.mkdir(parents=True, exist_ok=True)
        with path.open("a") as fh:
            fh.writelines(json.dumps(x, default=str) + "\n" for x in new)
        rows = rows + new
    up = sorted((r["e"], r["ticker"], r["s"]) for r in fold(rows).values() if r.get("status") in ("scheduled", "signal", "entered"))
    for e, t, s in up:
        log(f"[qp-runup] open: {t} buy {e} close, sell {s} close")
    log(f"[qp-runup] {len(univ)} universe IPOs in the {len(ipos)}-row calendar; {len(new)} new rows. {line(rows)}")
    return rows


if __name__ == "__main__":
    import sys
    from ..config import Config
    cfg = Config.load()
    if getattr(cfg.daily, "qp_runup_fwd", "shadow") == "off":
        print("[qp-runup] daily.qp_runup_fwd is off")
        sys.exit(0)
    root = Path(__file__).resolve().parents[2]
    st_dir = Path(sys.argv[sys.argv.index("--state") + 1]) if "--state" in sys.argv else root / "state"
    run(st_dir)
