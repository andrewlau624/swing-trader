"""Entrypoint for the daily-cadence book (RESULTS.md addendum 6).

  python scripts/daily.py                 # run the phase for the current ET time
  python scripts/daily.py --dry-run       # decide and log, submit nothing, save nothing
  python scripts/daily.py --phase close   # force a phase (open|reconcile|intraday|close)
  python scripts/daily.py --status        # book equity, positions, legs, history
  python scripts/daily.py --account live  # only one account (default: all in config)
  python scripts/daily.py --unkill night --account live   # undo a kill rule, on purpose

Paper always runs. Real money runs too when .env has DAILY_LIVE=on; switch
with `make daily-live-on` / `make daily-live-off`.
"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from swingtrader.config import Config, ROOT
from swingtrader.daily.book import DailyBook, book_file


def status(account: str):
    cfg = Config.load()
    d, profile = cfg.daily.for_account(account)
    if not (ROOT / "state" / book_file(account)).exists() and account in ("live", "roth"):
        print(f"=== {account.upper()} (real money){' profile ' + profile if profile else ''}: not started yet ==="); return
    b = DailyBook.load(ROOT / "state", d.start_equity, book_file(account))
    eq = b.equity_log[-1]["equity"] if b.equity_log else b.cash
    print(f"=== {account.upper()}{' (real money)' if account in ('live', 'roth') else ' (virtual $' + format(b.start_equity, ',.0f') + ')'}"
          f"{' profile ' + profile if profile else ''} ===")
    print(f"daily book  equity ${eq:,.2f}  start ${b.start_equity:,.0f}  "
          f"({(eq/b.start_equity-1)*100:+.1f}%)  cash ${b.cash:,.2f}  last run {b.last_run or '-'}")
    print(f"day-trade leg {'LIVE' if b.daytrade_live else 'shadow'} "
          f"(mode {d.daytrade_mode}; on at ${d.daytrade_min_equity:,.0f}; "
          f"intraday leverage cap {b.noise_lev_cap:g}x)")
    for s, p in sorted(b.positions.items()):
        print(f"   {p['leg']:6} {s:6} {float(p['qty']):10.4f} @ {float(p['avg_px']):9.2f}  since {p['entry_date']}")
    op = b.open_orders()
    if op:
        print(f"open orders {len(op)}")
        for k, o in op.items():
            print(f"   {o['leg']:6} {o['side']:4} {o['sym']:6} {o.get('tif','')}  {k}")
    for leg in ("ibs", "night", "noise"):
        r = [c["ret"] for c in b.closed if c["leg"] == leg]
        pnl = sum(c["pnl"] for c in b.closed if c["leg"] == leg)
        if r:
            print(f"{leg:6} trades {len(r):4}  win {100*np.mean(np.array(r)>0):4.0f}%  "
                  f"avg {np.mean(r)*100:+.2f}%  P&L ${pnl:+,.2f}")
    for leg, k in b.killed.items():
        print(f"KILLED  {leg}: since {k['date']} - {k['reason']}")
    lw = d.lever_weight
    wi, wn = (max(w, lw) if (b.levered and lw) else w for w in (d.ibs_weight, d.night_weight))
    if account == "roth":       # an IRA never borrows (executor._cash_scale)
        k = min(1.0, 1.0 / (wi + wn)) if wi + wn > 0 else 1.0
        wi, wn = wi * k, wn * k
    gate = ("gate ON" if b.levered else "gate off") if lw else "no gate"
    print(f"overnight size {wi + wn:.2f}x (ibs {wi:.2f} + night {wn:.2f}; {gate})"
          f"  night name cap {d.night_max_name_pct:.0%}"
          + (f"; open-sell route {'Schwab default (directed refused ' + b.route_refused + ')' if b.route_refused else 'listing exchange'}"
             if account in ("live", "roth") else ""))
    for sig, n in [(d.noise_symbol, b.noise)] + sorted(b.noise_more.items()):
        if n.get("history"):
            h = [x["ret"] for x in n["history"]]
            print(f"noise {sig} (shadow) days {len(h)}  equity ${n.get('shadow_equity', 0):,.2f}  "
                  f"avg/day {np.mean(h)*100:+.3f}%  up-days {100*np.mean(np.array(h)>0):.0f}%")
    ch = b.conviction.get("history", [])
    if ch or b.conviction:
        r = [x["ret"] for x in ch]
        print(f"conviction TQQQ ({d.conviction_mode}) trades {len(r)}"
              + (f"  win {100*np.mean(np.array(r)>0):.0f}%  avg {np.mean(r)*100:+.2f}% on TQQQ" if r else "")
              + (f"  today: {'holding ' + format(b.conviction['pos'], '+d') if b.conviction.get('pos') else ('done' if b.conviction.get('done') else 'waiting')}"
                 if b.conviction.get("day") else ""))
    f = ROOT / "logs" / (f"daily-fills-{account}.jsonl" if account in ("live", "roth") else "daily-fills.jsonl")
    if f.exists():
        rows = [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
        for leg in ("ibs", "night"):
            v = [r["slippage_bps"] for r in rows if r["leg"] == leg]
            if v:
                print(f"slippage {leg:6} n={len(v)} mean {np.mean(v):+.1f} bps (vs ref price at decision)")
    if len(b.equity_log) > 1:
        print("equity by day: " + "  ".join(f"{e['date'][5:]} {e['equity']:,.0f}" for e in b.equity_log[-10:]))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--phase", choices=["open", "reconcile", "intraday", "close", "flatten"])
    ap.add_argument("--account", choices=["paper", "live", "roth"])
    ap.add_argument("--unkill", metavar="LEG", help="re-enable a leg a kill rule switched off "
                    "(night|ibs|noise|all); needs --account")
    a = ap.parse_args(argv)
    cfg = Config.load()
    if a.unkill:
        if not a.account:
            ap.error("--unkill needs --account paper|live|roth")
        b = DailyBook.load(ROOT / "state", cfg.daily.start_equity, book_file(a.account))
        k = b.killed.pop(a.unkill, None)
        if k is None:
            print(f"{a.unkill} is not killed on {a.account}"); return 1
        b.save(ROOT / "state", book_file(a.account))
        print(f"{a.account}: {a.unkill} re-enabled (was killed {k['date']}: {k['reason']}).\n"
              "The rule will kill it again on the next run if the numbers still say so.")
        return 0
    accounts = [a.account] if a.account else cfg.daily.resolved_accounts()
    if a.status:
        for acc in dict.fromkeys(accounts + [x for x in ("live", "roth") if x not in accounts]):
            status(acc); print()
        ra = cfg.daily.resolved_accounts()
        print(f"accounts trading: {ra}  (real money: brokerage {'ON' if 'live' in ra else 'OFF'} "
              f"[DAILY_LIVE], Roth {'ON' if 'roth' in ra else 'OFF'} [DAILY_ROTH] in .env)")
        return 0
    from swingtrader.daily.executor import DailyExecutor
    rc = 0
    for acc in accounts:
        # one account failing must not stop the other: they are independent books
        try:
            rc |= DailyExecutor(cfg, account=acc, dry_run=a.dry_run).run(phase=a.phase)
        except Exception as exc:
            print(f"[{acc}] run failed: {type(exc).__name__}: {exc}", flush=True)
            rc |= 1
            # a silent failure on the real-money book is the worst outcome
            try:
                import datetime as _dt
                from swingtrader.live.notify import Notifier
                print(Notifier(ROOT / "state").send(
                    f"[daily{(' ' + acc.upper() + ' $') if acc in ('live', 'roth') else ''}] run FAILED: {type(exc).__name__}",
                    f"<p>The {acc} daily book could not run.</p><pre>{exc}</pre>"
                    + ("<p>If this mentions invalid_grant or revoked: run "
                       "<code>make schwab-login</code> on the server.</p>" if acc in ("live", "roth") else ""),
                    dedupe_key=f"daily-fail:{acc}:{_dt.date.today()}:{type(exc).__name__}"))
            except Exception:
                pass
    if not a.dry_run:
        ping_healthcheck(rc)
    return rc


def ping_healthcheck(rc: int) -> None:
    """Dead-man switch for when the server itself is down: every run pings
    HEALTHCHECK_URL (e.g. a healthchecks.io check), `/fail` if any account
    failed. The service emails you when pings STOP, which nothing running on
    this box can do. Never raises."""
    from swingtrader.config import get_env
    url = (get_env("HEALTHCHECK_URL") or "").strip().rstrip("/")
    if not url:
        return
    try:
        import requests
        requests.get(url + ("/fail" if rc else ""), timeout=10)
    except Exception as exc:
        print(f"healthcheck ping failed: {type(exc).__name__}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
