"""Executor for the daily-cadence book. One phase per invocation.

  open       09:15 ET  book last night's fills; SELL the night leg at the open
                       auction; rebalance the IBS leg at the open; settle
                       yesterday's intraday (noise) leg; build today's
                       night-leg universe (~30s of SIP bars)
  reconcile  09:50 ET  book the opening fills
  intraday   HH:01 / HH:31, 10:01-15:31 ET   noise-leg decision (shadow
                       until the day-trading gate trips)
  close      15:40 ET  scan for beaten-down names trading at their lows and
                       BUY them at the close auction (cutoff 15:50); flatten a
                       live noise position at the close

The IBS leg holds open -> next open and the night leg close -> next open. The
noise leg is the only day trade; it places orders once equity reaches
`daytrade_min_equity` ($2,000, Reg T -- the PDT rule was retired 2026-06-04)
and never uses more intraday leverage than the broker grants.

The swing book shares the account. The two books never touch each other's
symbols: this book skips anything the swing book holds or has pending, and
the swing executor skips anything listed in state/book-daily.json.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import time
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from ..config import REAL_ACCOUNTS, Config, ROOT, get_env
from ..live.broker import PaperBroker
from .brokers import AlpacaAdapter, SchwabAdapter, make_adapter
from ..live.lock import AccountLock, account_fingerprint
from ..live.notify import Notifier
from ..universe import all_assets, valid_symbol
from . import marketdata as md
from . import signals as sg
from .book import TERMINAL, DailyBook, book_file

ET = "America/New_York"
NOISE_COST_BPS = 0.5          # per side, shadow accounting (research: noise.py)


def phase_for(now_et: dt.datetime) -> str:
    t = now_et.hour * 60 + now_et.minute
    if 7 * 60 <= t < 9 * 60 + 28:
        return "open"
    if 9 * 60 + 30 <= t < 10 * 60:
        return "reconcile"
    if 10 * 60 <= t < 15 * 60 + 38:
        return "intraday"
    if 15 * 60 + 38 <= t < 15 * 60 + 50:
        return "close"
    if 15 * 60 + 55 <= t < 16 * 60:
        return "flatten"
    return "reconcile"


def heartbeat_gaps(hb: dict) -> list[str]:
    """What today's runs are missing, from a heartbeat {session_close, runs}.
    The timer fires 09:15 open, 10:01-15:31 intraday (12), 15:40 close,
    15:57 flatten; on a half day only what falls before the bell counts."""
    close = hb.get("session_close") or "16:00"
    runs = hb.get("runs", [])
    phases = {p for p, _ in runs}
    out = [] if "open" in phases else ["no 09:15 open run"]
    slots = [f"{h}:{m:02d}" for h in range(10, 16) for m in (1, 31)]
    due = [t for t in slots if t.zfill(5) < close]
    got = sum(p == "intraday" for p, _ in runs)
    if got < len(due) - 2:        # a slow run can skip one slot on the lock
        out.append(f"{got}/{len(due)} intraday runs")
    if close >= "15:50":
        out += [f"no {t} {p} run" for p, t in (("close", "15:40"), ("flatten", "15:57"))
                if p not in phases]
    return out


class DailyExecutor:
    def __init__(self, cfg: Config, account: str = "paper",
                 broker: PaperBroker | None = None,
                 state_dir: Path | None = None, log_dir: Path | None = None,
                 dry_run: bool = False):
        self.cfg = cfg
        self.account = account
        self.d, self.profile = cfg.daily.for_account(account)
        self.live = account in REAL_ACCOUNTS      # real money
        # Roth IRA: a cash account. No margin (so no overnight leverage and no
        # intraday leg, which shorts), and every buy is paid for in full.
        self.cash_account = account == "roth"
        self.dry_run = dry_run
        b = broker or make_adapter(account, getattr(cfg.daily, "live_broker", "schwab"),
                                   getattr(cfg.daily, "schwab_open_route", "primary"))
        # a raw PaperBroker (or test double) gets the Alpaca adapter
        self.broker = b if hasattr(b, "submit") else AlpacaAdapter(b)
        self.fname = book_file(account)
        self.tag = f"-{account}" if self.live else ""
        self.state_dir = state_dir or ROOT / "state"
        self.log_dir = log_dir or ROOT / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.lines: list[str] = []
        self.actions: list[str] = []
        self.warnings: list[str] = []
        self.notifier = Notifier(self.state_dir)

    # ------------------------------------------------------------- logging
    def log(self, msg: str) -> None:
        line = f"[{dt.datetime.now().astimezone().strftime('%H:%M:%S')}] {msg}"
        self.lines.append(line)
        print(line, flush=True)

    def act(self, msg: str) -> None:
        self.actions.append(msg); self.log(f"  {msg}")

    def warn(self, msg: str) -> None:
        self.warnings.append(msg); self.log(f"  WARN: {msg}")

    # ----------------------------------------------------------------- run
    def run(self, phase: str | None = None, lock_wait_s: int = 600) -> int:
        if not self.d.enabled:
            print("daily book disabled in config.yaml"); return 0
        fp = account_fingerprint(self.broker.key, self.broker.secret)
        lock = AccountLock(fp, self.state_dir)
        # the swing book's 09:05 run can take several minutes; wait for it
        # rather than skip the open (OPG cutoff 09:28)
        deadline = time.time() + lock_wait_s
        while not lock.acquire():
            if time.time() > deadline:
                self.log("account lock busy past deadline - skipping this run")
                return 1
            time.sleep(5)
        try:
            return self._run(phase)
        finally:
            lock.release()

    def _run(self, phase: str | None) -> int:
        now = dt.datetime.now(ZoneInfo(ET))
        today = now.date().isoformat()
        phase = phase or phase_for(now)
        clock = self.broker.clock()
        acct = self.broker.account()
        # live: the book starts at the FREE equity (not your other holdings)
        start = self._live_start() if self.live else self.d.start_equity
        book = DailyBook.load(self.state_dir, start, self.fname)
        self.acct_equity = float(acct.equity)
        self.log(f"=== daily book [{self.account.upper()}{' profile ' + self.profile if self.profile else ''}] | phase {phase} | {now:%Y-%m-%d %H:%M} ET | "
                 f"market {'OPEN' if clock.is_open else 'closed'} ===")

        if self.live and isinstance(self.broker, SchwabAdapter):
            from .brokers import TOKEN_WARN_AGE_S, schwab_token_age_s
            age = schwab_token_age_s()
            if age is not None and age > TOKEN_WARN_AGE_S:
                self.warn(f"Schwab login is {age/86400:.1f} days old and dies at 7 - "
                          "run `make schwab-login` on the server TODAY")
        if self.live:
            if getattr(acct, "trading_blocked", False) or getattr(acct, "account_blocked", False):
                self.warn("LIVE account is blocked from trading - nothing submitted")
                return 1
            if self.cash_account:
                if not self.roth_limited_margin():
                    # a plain cash IRA must not reuse same-day sale proceeds (good-faith
                    # violations), and the settled-cash version trails SPY (addendum 20)
                    self.warn("Roth book needs Schwab LIMITED MARGIN on the IRA (Schwab form: "
                              "margin in IRA). Once approved set ROTH_LIMITED_MARGIN=yes in "
                              ".env. Nothing traded.")
                    return 1
            elif float(getattr(acct, "multiplier", 1) or 1) < 2:
                # cash account: selling at the open and re-buying at the close
                # with the same unsettled proceeds is a good-faith violation
                self.warn("LIVE account is not a margin account (multiplier < 2). This book "
                          "re-uses same-day sale proceeds; in a cash account that is a "
                          "good-faith violation. Enable margin at Alpaca before trading.")
                return 1
        trading_day = clock.is_open or (
            pd.Timestamp(clock.next_open).tz_convert(ET).date() == now.date())
        self.reconcile(book, today)
        if self.live:
            # AFTER reconcile: fresh fills must count as the bot's own, or they
            # are subtracted as "your holdings" and then again as spent cash
            self._sync_live_cash(book)

        if trading_day:
            self._apply_kills(book, today)
        if not trading_day:
            self.log("not a trading day - reconcile only")
        elif phase == "open":
            self.phase_open(book, today)
        elif phase == "intraday":
            self.phase_intraday(book, today, now, clock)
        elif phase == "close":
            self.phase_close(book, today, now, clock)
        elif phase == "flatten":
            self._flatten_noise(book, today, tif="day", kind="flat")

        if not self.dry_run:
            if trading_day:
                self._heartbeat(today, phase, now, clock)
            elif phase == "reconcile" and now.hour >= 16:
                self._watchdog(today)

        marks = self._marks(book)
        eq = book.equity(marks)
        book.log_equity(today, eq)
        book.last_run = now.isoformat(timespec="seconds")
        if not self.dry_run:
            book.save(self.state_dir, self.fname)
        self.log(f"book equity ${eq:,.2f} (start ${book.start_equity:,.0f}, "
                 f"{(eq / book.start_equity - 1) * 100:+.1f}%) | cash ${book.cash:,.2f} | "
                 f"{len(book.positions)} positions"
                 + (f" | account ${float(self.broker.account().equity):,.2f}" if self.live else "")
                 + " | day-trade leg "
                 f"{'LIVE' if book.daytrade_live else 'shadow'}")
        self._notify(book, eq, today)
        with open(self.log_dir / f"daily{self.tag}-{today}.log", "a") as fh:
            fh.write("\n".join(self.lines) + "\n")
        return 0

    # ------------------------------------------------------------ watchdog
    # Quiet runs send nothing, so silence cannot tell "nothing to do" from
    # "never ran". Every trading-day run stamps state/heartbeat*.json; the
    # 16:10 run checks today's stamps and emails if a phase is missing (a lock
    # timeout, a crash before the failure email, a timer that did not fire).
    # The server being down entirely is HEALTHCHECK_URL's job (scripts/daily.py).
    def _hb_path(self) -> Path:
        return self.state_dir / f"heartbeat{self.tag}.json"

    def _heartbeat(self, today: str, phase: str, now: dt.datetime, clock) -> None:
        try:
            hb = json.loads(self._hb_path().read_text())
        except Exception:
            hb = {}
        if hb.get("date") != today:
            hb = {"date": today, "runs": []}
        try:     # today's close (13:00 on a half day); clock.next_close is today's until the bell
            hb["session_close"] = pd.Timestamp(clock.next_close).tz_convert(ET).strftime("%H:%M")
        except Exception:
            pass
        hb["runs"].append([phase, now.strftime("%H:%M")])
        try:
            self._hb_path().write_text(json.dumps(hb))
        except Exception as exc:
            self.log(f"  heartbeat not saved ({exc})")

    def _watchdog(self, today: str) -> None:
        try:
            hb = json.loads(self._hb_path().read_text())
        except Exception:
            hb = {}
        if hb.get("date") != today:
            return          # holiday, or down all day: HEALTHCHECK_URL covers that
        missing = heartbeat_gaps(hb)
        if missing:
            self.warn("watchdog: today's schedule has gaps - " + "; ".join(missing)
                      + ". Check `make daily-logs` and `make persist-status`.")
        else:
            self.log(f"[watchdog] all phases ran today ({len(hb['runs'])} runs)")

    # ------------------------------------------------------------ reconcile
    def reconcile(self, book: DailyBook, today: str) -> None:
        """Book any fills since the last run. Broker is the source of truth."""
        for coid, o in list(book.open_orders().items()):
            try:
                status, fq, px, when = self.broker.order_status(coid, o)
            except Exception as exc:
                self.warn(f"cannot look up order {coid}: {str(exc)[:80]}")
                continue
            when = when or today
            new = book.apply_fill(coid, fq, px, status, when)
            if new:
                ref = float(o.get("ref_px") or px)
                bps = (px / ref - 1) * 1e4 * (1 if o["side"] == "buy" else -1) if ref else 0.0
                self.log(f"  FILL {o['leg']:5} {o['side']:4} {new:g} {o['sym']} @ {px:.4f} "
                         f"(ref {ref:.4f}, {bps:+.1f} bps)")
                with open(self.log_dir / f"daily-fills{self.tag}.jsonl", "a") as fh:
                    fh.write(json.dumps({"coid": coid, "sym": o["sym"], "leg": o["leg"],
                                         "side": o["side"], "qty": new, "fill_px": px,
                                         "ref_px": ref, "slippage_bps": bps,
                                         "route": o.get("route", ""),
                                         "filled_at": when}) + "\n")
            if status in ("canceled", "expired", "rejected"):
                if not new and float(o.get("filled_qty", 0) or 0) <= 0:
                    self.log(f"  order {coid} ended {status} unfilled")
                # an open sell that died with shares left must not carry the
                # night position into another day (Alpaca paper expired 9 of 10
                # OPG sells on 2026-09-24, several after partial fills)
                self._reroute_open_sell(book, today, coid, o, status)
        # anything the broker no longer holds cannot still be ours
        held = self.broker.positions()
        for sym in list(book.positions):
            if sym not in held and not any(o["sym"] == sym for o in book.open_orders().values()):
                p = book.positions.pop(sym)
                qty, avg = float(p["qty"]), float(p["avg_px"])
                # We do not know the real exit price (delisting, buy-in, manual
                # sale). Booking the ENTRY price invented cash and threw away the
                # P&L; use the last known market price and record the round trip.
                px = self._last_price(sym, fallback=avg)
                book.cash += qty * px
                book.closed.append({"sym": sym, "leg": p.get("leg"), "qty": qty,
                                    "entry_px": avg, "exit_px": px,
                                    "entry_date": p.get("entry_date"), "exit_date": today,
                                    "pnl": qty * (px - avg),
                                    "ret": (px / avg - 1.0) if avg else 0.0,
                                    "note": "broker no longer holds; exit price unknown"})
                self.warn(f"{sym}: in daily book but not held at broker - booked out at "
                          f"{px:.2f} (last known), not the {avg:.2f} entry price")

    def _last_price(self, sym: str, fallback: float) -> float:
        try:
            b = md.sip_daily([sym], pd.Timestamp.now(tz=ET) - pd.Timedelta(days=10), None)
            d = b.get(sym)
            if d is not None and len(d):
                return float(d["close"].iloc[-1])
        except Exception:
            pass
        return float(fallback)

    # ---------------------------------------------------------------- open
    def phase_open(self, book: DailyBook, today: str) -> None:
        marks = self._marks(book)
        equity = self._sizing_equity(book)
        left = {**book.leg_positions("noise"), **book.leg_positions("conv")}
        if left:
            self.warn(f"intraday-leg position left over from yesterday: {list(left)} "
                      "- closing it at the open")
            self._flatten_noise(book, today, tif="day", kind="leftover")
        self._settle_noise(book, today)
        self._gate(book, equity)

        # night leg: everything bought at yesterday's close goes at the open
        self._prepare_open_route(book, today)
        for sym, p in book.leg_positions("night").items():
            self._order(book, today, sym, "sell", "night", qty=float(p["qty"]),
                        tif="opg", ref_px=marks.get(sym, p["avg_px"]), kind="exit")
        self._confirm_open_routes(book, today)

        # IBS leg: rank the universe by 12-1 momentum (month-end, bars before
        # today), then IBS < ibs_max on the last complete SIP bar of the top-k
        self._ibs_open(book, today, equity)

        # night-leg universe for this afternoon (pays the ~30s SIP pull now)
        u = [s for s in all_assets().symbols if valid_symbol(s)]
        elig = md.eligibility(u, dt.date.fromisoformat(today), price_min=self.d.night_price_min,
                              adv_min=self.d.night_adv_min, cache_dir=self.state_dir)
        self.log(f"[night] {len(elig)} names eligible today "
                 f"(close >= ${self.d.night_price_min:.0f}, 20d SIP $vol >= ${self.d.night_adv_min/1e6:.0f}M)")

    # ------------------------------------------------------ kill rules
    def _kill(self, book: DailyBook, leg: str, today: str, reason: str) -> None:
        if leg in book.killed:
            return
        book.killed[leg] = {"date": today, "reason": reason}
        what = "ALL legs" if leg == "all" else f"the {leg} leg"
        self.warn(f"KILL RULE: {what} stops opening positions - {reason}. Exits continue. "
                  f"Undo only on purpose: python scripts/daily.py --unkill {leg} --account {self.account}")

    def _apply_kills(self, book: DailyBook, today: str) -> None:
        """Pre-registered kill rules (signals.KILL_*): a leg losing money with
        t < -1 over enough live round trips stops opening positions, and a
        realised drawdown past HALT_DRAWDOWN halts every leg."""
        for leg, why in sg.kill_check(book.closed).items():
            self._kill(book, leg, today, why)
        eq = book.equity(self._marks(book))
        dd = sg.realised_drawdown(book.closed, eq)
        if dd < -sg.HALT_DRAWDOWN:
            self._kill(book, "all", today, f"realised drawdown {dd:.0%} of equity "
                                            f"(limit -{sg.HALT_DRAWDOWN:.0%}; backtest worst ~-20%)")
        if book.killed:
            self.log("killed legs: " + ", ".join(f"{k} (since {v['date']})" for k, v in book.killed.items()))

    # ------------------------------------------------- overnight leverage
    def _cash_scale(self) -> float:
        """An IRA never borrows: scale both overnight legs to <= 1.0x in total."""
        tot = self.d.night_weight + self.d.ibs_weight
        return min(1.0, 1.0 / tot) if (self.cash_account and tot > 0) else 1.0

    def _w_night(self, book: DailyBook) -> float:
        lw = self.d.lever_weight
        w = max(self.d.night_weight, lw) if (book.levered and lw) else self.d.night_weight
        return w * self._cash_scale()

    def _w_ibs(self, book: DailyBook) -> float:
        lw = self.d.lever_weight
        w = max(self.d.ibs_weight, lw) if (book.levered and lw) else self.d.ibs_weight
        return w * self._cash_scale()

    def _lever_gate(self, book: DailyBook) -> None:
        """Open or close the overnight leverage gate from live evidence."""
        if not self.d.lever_weight or self.cash_account:
            book.levered = False; return
        n, bps = getattr(self, "_exit_stats", (0, float("nan")))
        try:
            mult = float(getattr(self.broker.account(), "multiplier", 1) or 1)
        except Exception:
            mult = 1.0
        dd = sg.realised_drawdown(book.closed, book.equity(self._marks(book)))
        ok, why = sg.lever_ok(n, bps, book.killed, dd, mult)
        if ok != book.levered:
            (self.act if ok else self.warn)(
                f"overnight leverage {'ON' if ok else 'OFF'}: legs at "
                f"{self.d.lever_weight if ok else self.d.night_weight:.2f} each - {why}")
        else:
            ucb = getattr(self, "_exit_ucb", float("nan"))
            self.log(f"[lever] {'on' if ok else 'off'} - {why}"
                     + (f" (95% upper bound on the mean {ucb:+.1f}bp)" if np.isfinite(ucb) else ""))
        book.levered = ok

    # ------------------------------------------------------ open routing
    ROUTE_RETRY_DAYS = 5

    def _prepare_open_route(self, book: DailyBook, today: str) -> None:
        """Schwab only: skip directed routing for a few days after a refusal,
        so a refused route costs one fallback, not one every morning."""
        if not hasattr(self.broker, "route_refused") or not book.route_refused:
            return
        age = (dt.date.fromisoformat(today) - dt.date.fromisoformat(book.route_refused)).days
        if age < self.ROUTE_RETRY_DAYS:
            self.broker.route_refused = True
            self.log(f"[night] open sells use Schwab routing (directed route refused {book.route_refused})")

    def _confirm_open_routes(self, book: DailyBook, today: str, wait_s: float = 8.0) -> None:
        """A directed order can be accepted by the API and rejected by Schwab a
        moment later. Check the directed open sells now, while there is still
        time before 09:30 to resend them with Schwab's own routing."""
        directed = {k: o for k, o in book.open_orders().items()
                    if o.get("tif") == "opg" and o.get("route") not in ("", "AUTO", None)}
        if self.dry_run or not directed:
            return
        time.sleep(wait_s)
        for coid, o in directed.items():
            try:
                status, fq, *_ = self.broker.order_status(coid, o)
            except Exception as exc:
                self.log(f"  cannot check route of {o['sym']}: {str(exc)[:80]}"); continue
            if status in ("canceled", "expired", "rejected") and fq <= 0:
                o["status"] = status
                self._reroute_open_sell(book, today, coid, o, status)

    def _reroute_open_sell(self, book: DailyBook, today: str, coid: str, o: dict, status: str) -> None:
        """An open sell that ended (expired / canceled / rejected) with shares
        still held: sell the rest now rather than carry the night position into
        another day. A DIRECTED Schwab sell refused outright is resent with
        Schwab's routing and pauses directed routing; anything else (a partial
        auction fill, an expired OPG) sells the remainder at market."""
        if o.get("side") != "sell" or o.get("tif") != "opg":
            return
        p = book.positions.get(o["sym"])
        if not p or o.get("rerouted") or float(p["qty"]) <= 0:
            return
        o["rerouted"] = True
        directed = o.get("route") not in ("", "AUTO", None)
        if not directed or float(o.get("filled_qty", 0) or 0) > 0:
            self.warn(f"{o['sym']}: open sell ended {status} with {float(p['qty']):g} sh still held - "
                      "selling the rest at market")
            self._order(book, today, o["sym"], "sell", o["leg"], qty=float(p["qty"]),
                        tif="day", ref_px=float(o.get("ref_px") or p["avg_px"]), kind="exit-rest")
            return
        book.route_refused = today
        if hasattr(self.broker, "route_refused"):
            self.broker.route_refused = True
        self.warn(f"{o['sym']}: open sell directed to {o['route']} ended {status}; "
                  "resending with Schwab routing (directed routing paused "
                  f"{self.ROUTE_RETRY_DAYS} days; set daily.schwab_open_route: auto to stop trying)")
        self._order(book, today, o["sym"], "sell", o["leg"], qty=float(p["qty"]),
                    tif="opg", ref_px=float(o.get("ref_px") or p["avg_px"]), kind="exit-auto")

    def _ibs_open(self, book: DailyBook, today: str, equity: float) -> None:
        t = pd.Timestamp(today)
        cash_sym = self.d.ibs_cash_symbol
        syms = list(self.d.ibs_symbols) + ([cash_sym] if cash_sym else [])
        bars = md.sip_daily(syms, t - pd.Timedelta(days=420), t)
        bars = {s: b[b.index < t] for s, b in bars.items() if len(b[b.index < t])}
        closes = pd.DataFrame({s: b["close"] for s, b in bars.items()
                               if s in self.d.ibs_symbols})
        if self.d.ibs_top_k:
            universe = sg.momentum_top(closes, t, self.d.ibs_top_k)
            self.log(f"[ibs] top-{self.d.ibs_top_k} by 12-1 momentum this month: {universe or 'n/a'}")
        else:
            universe = list(closes.columns)
        last = {s: bars[s].iloc[-1].to_dict() for s in universe if s in bars}
        foreign = self._foreign_symbols(book)
        targets = [s for s in sg.ibs_targets(last, self.d.ibs_max) if s not in foreign]
        if book.is_killed("ibs") and targets:
            self.log(f"[ibs] leg killed - not buying {targets}")
            targets = []
        self.log("[ibs] IBS last bar: " + ", ".join(
            f"{s} {sg.ibs(b['high'], b['low'], b['close']):.2f}" for s, b in sorted(last.items()))
            + f" -> hold {targets or ('T-bills (' + cash_sym + ')' if cash_sym else 'cash')}")
        held = book.leg_positions("ibs")
        for sym, p in held.items():
            if sym not in targets:
                ref = bars.get(sym, pd.DataFrame({"close": [p["avg_px"]]}))["close"].iloc[-1]
                self._order(book, today, sym, "sell", "ibs", qty=float(p["qty"]),
                            tif="day", ref_px=float(ref), kind="exit")
        leg = self._w_ibs(book) * equity
        # T-bills hold the leg's money whenever it has nothing to own
        tb = book.leg_positions("tbill")
        if cash_sym:
            if targets:
                for sym, p in tb.items():
                    self._order(book, today, sym, "sell", "tbill", qty=float(p["qty"]),
                                tif="day", ref_px=float(bars[sym]["close"].iloc[-1]) if sym in bars else float(p["avg_px"]),
                                kind="exit")
            elif not tb and not held and cash_sym in bars and cash_sym not in foreign:
                if leg >= 50:
                    self._order(book, today, cash_sym, "buy", "tbill", notional=leg, tif="day",
                                ref_px=float(bars[cash_sym]["close"].iloc[-1]), kind="entry")
        if targets:
            per = leg / len(targets)
            for sym in targets:
                if sym in held:
                    continue
                self._order(book, today, sym, "buy", "ibs", notional=per, tif="day",
                            ref_px=float(last[sym]["close"]), kind="entry")

    # --------------------------------------------------------------- close
    EXIT_COST_WARN_BPS = 15.0     # night edge is gone near 28bp/side (RESULTS.md addendum 14)
    EXIT_COST_MIN_N = 10

    def _check_exit_cost(self, book: DailyBook | None = None, today: str = "") -> None:
        """This morning's open sells are booked by now; score the recent ones
        against the official open (SIP, >15 min old by 15:40)."""
        path = self.log_dir / f"daily-fills{self.tag}.jsonl"
        if not path.exists():
            return
        try:
            fills = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
            sells = [f for f in fills if f.get("leg") == "night" and f.get("side") == "sell"][-sg.LEVER_MIN_EXITS:]
            if not sells:
                return
            days = sorted({str(f.get("filled_at", ""))[:10] for f in sells})
            bars = md.sip_daily(sorted({f["sym"] for f in sells}),
                                pd.Timestamp(days[0]) - pd.Timedelta(days=3), None)
            opens = {(sym, str(d.date())): float(b.loc[d, "open"])
                     for sym, b in bars.items() for d in b.index}
            n, bps = sg.night_exit_cost(sells, opens)
            routes = sg.exit_cost_by_route(sells, opens)
            self._exit_stats = sg.night_exit_cost(sells, opens, window=sg.LEVER_MIN_EXITS)
            self._exit_ucb = sg.cost_upper_bound(sg.night_exit_costs(sells, opens, window=sg.LEVER_MIN_EXITS))
        except Exception as exc:
            self.log(f"[night] exit-cost check skipped ({type(exc).__name__}: {str(exc)[:80]})")
            return
        if not n:
            return
        self.log(f"[night] open-sell cost vs official open, last {n}: {bps:+.1f} bps/side")
        for r, (k, c, hit) in sorted(routes.items()):
            self.log(f"[night]   route {r or 'OPG'}: n {k}, {c:+.1f} bps/side, "
                     f"{hit:.0%} filled at the auction print")
        if book is not None and n >= sg.KILL_EXIT_COST_MIN_N and bps > sg.KILL_EXIT_COST_BPS:
            self._kill(book, "night", today, f"open sells average {bps:+.1f}bp/side worse than the "
                                             f"official open over {n} exits (kill at {sg.KILL_EXIT_COST_BPS:g})")
        elif n >= self.EXIT_COST_MIN_N and bps > self.EXIT_COST_WARN_BPS:
            self.warn(f"night-leg open sells average {bps:+.1f} bps/side worse than the official open "
                      f"over {n} exits (backtest assumes 7.5; the edge is gone near 28). "
                      "Consider a broker with real market-on-open orders.")

    def phase_close(self, book: DailyBook, today: str, now, clock) -> None:
        self._check_exit_cost(book, today)
        self._lever_gate(book)
        if book.is_killed("night"):
            self.log("[night] leg killed - no new buys"); return
        close_et = pd.Timestamp(clock.next_close).tz_convert(ET)
        if close_et.date() != now.date() or close_et.hour != 16:
            self.log("early close today - night leg skipped (research excludes half days)")
            return
        elig_path = self.state_dir / f"daily-universe-{today}.json"
        if not elig_path.exists():
            self.warn("no eligibility file for today (did the 09:15 run fail?) - building now")
        elig = md.eligibility([s for s in all_assets().symbols if valid_symbol(s)], dt.date.fromisoformat(today),
                              price_min=self.d.night_price_min, adv_min=self.d.night_adv_min,
                              cache_dir=self.state_dir)
        if elig.empty:
            self.warn("night universe empty - skipping"); return
        foreign = self._foreign_symbols(book) | set(self.d.ibs_symbols) | set(book.positions)
        syms = [s for s in elig.index if s not in foreign]
        rows, src = md.decision_rows(syms, self.d.quote_source, log=self.log)
        if rows.empty:
            self.warn("no live prices returned - skipping night leg"); return
        self.log(f"[night] prices from {src.upper()} ({len(rows)} fresh quotes)")
        cols = [c for c in ("prev_close", "vol20") if c in elig.columns]
        rows = rows.join(elig[cols], how="inner")
        bad = sg.prev_close_mismatch(rows)
        if bad.any():
            self.warn(f"[night] skipping {int(bad.sum())} name(s) whose previous close disagrees with "
                      f"the quote feed (split/corporate action?): {sorted(rows.index[bad])[:10]}")
            rows = rows[~bad]
        picks = sg.loser_picks(rows, day_ret_max=self.d.night_day_ret_max,
                               ibs_max=self.d.night_ibs_max, price_min=self.d.night_price_min,
                               price_max=self.d.night_price_max)
        self.log(f"[night] scanned {len(rows)} live names -> {len(picks)} signal(s)")
        if src == "schwab":
            self._log_alt_source(syms, elig, picks)
        if picks.empty:
            return
        if "rets" in elig.columns:
            picks, dropped = sg.dedupe_correlated(picks, elig["rets"].to_dict(), self.d.night_max_corr)
            if dropped:
                self.log(f"[night] {len(dropped)} duplicate bet(s) dropped (20d corr > {self.d.night_max_corr}): "
                         + ", ".join(f"{d} ~ {k}" for d, k in dropped[:12]))
        else:
            self.warn("eligibility cache has no return history - duplicate-bet check skipped today")
        n_raw = len(picks)
        picks, frac = sg.night_sizing(picks, vol_min=self.d.night_vol_min,
                                      crowd_n=self.d.night_crowd_n,
                                      max_name_pct=self.d.night_max_name_pct)
        self.log(f"[night] {len(picks)} after vol20 >= {self.d.night_vol_min:.0%}"
                 + (f"; crowded day ({n_raw} signals): exposure x {self.d.night_crowd_n / n_raw:.2f}"
                    if n_raw > self.d.night_crowd_n else ""))
        if picks.empty:
            return
        equity = self._sizing_equity(book)
        leg = self._w_night(book) * equity
        gs = sg.gap_scale(today, pd.Timestamp(clock.next_open).tz_convert(ET), self.d.night_weekend_scale)
        if gs != 1.0:
            self.log(f"[night] held over {pd.Timestamp(clock.next_open).tz_convert(ET):%a %m-%d}: "
                     f"exposure x {gs:g} (weekend/holiday gap)")
        per = leg * frac * gs
        # never let this book borrow beyond the gross its weights allow
        floor = -(max(1.0, self._w_ibs(book) + self._w_night(book)) - 1.0) * equity
        cash = book.cash
        v20 = picks["vol20"].values if "vol20" in picks else np.full(len(picks), np.nan)
        w = sg.night_tilt(v20, picks["day_ret"].values, self.d.night_tilt_k)
        prev = np.array([np.expm1(r[-1]) if isinstance(r, list) and r else np.nan
                         for r in (elig["rets"].reindex(picks.index) if "rets" in elig.columns
                                   else pd.Series([None] * len(picks), index=picks.index))])
        w2 = sg.night_tilt_v2(v20, picks["day_ret"].values, prev, self.d.night_tilt_k)
        if self.d.night_tilt_model == "v2":
            w, w_other, other = w2, w, "v1"
        else:
            w_other, other = w2, "v2"
        self.log(f"[night] tilt {self.d.night_tilt_model} (would be {other}: "
                 + ", ".join(f"{s} {a:.2f}" for s, a in zip(picks.index[:8], w_other)) + ")")
        probe_usd = self.d.night_probe_max_usd if self.live else None
        for (sym, r), wi in zip(picks.iterrows(), w):
            qty = math.floor(per * wi / r.price)   # auction orders are whole shares
            probe = False
            if qty < 1 and probe_usd and r.price <= probe_usd:
                # a small account rounds every name above ~$50 to zero shares, so
                # the open-sell cost sample would be cheap, wide-spread names
                # only. One share measures the auction fill just as well.
                qty, probe = 1, True
            if qty < 1:
                self.log(f"  skip {sym}: ${per * wi:.0f} buys 0 shares at {r.price:.2f}")
                continue
            if cash - qty * r.price < floor:
                self.log(f"  skip {sym}: book cash exhausted"); continue
            cash -= qty * r.price
            spread = (r.ask - r.bid) / ((r.ask + r.bid) / 2) * 1e4 if (
                "bid" in r and np.isfinite(r.get("bid", np.nan)) and np.isfinite(r.get("ask", np.nan))
                and r.ask >= r.bid > 0) else float("nan")
            self.log(f"  {sym}: day {r.day_ret*100:+.1f}%  ibs {r.ibs:.2f}  px {r.price:.2f}  w {wi:.2f}"
                     + (f"  spread {spread:.0f}bp" if np.isfinite(spread) else "")
                     + (f"  PROBE 1 sh (target ${per * wi:.0f})" if probe else ""))
            self._log_decision(today, sym, r, spread, qty)
            self._order(book, today, sym, "buy", "night", qty=qty, tif="cls",
                        ref_px=float(r.price), kind="entry")

    def _log_decision(self, today: str, sym: str, r, spread_bps: float, qty: int) -> None:
        """One line per night pick with what was known at 15:40, including the
        quoted spread. This is the dataset a per-name cost model will be fitted
        on once fills accumulate (research/sim uses a price/volume tier until then)."""
        if self.dry_run:
            return
        rec = {"date": today, "sym": sym, "price": float(r.price), "day_ret": float(r.day_ret),
               "ibs": float(r.ibs), "vol20": float(r.get("vol20", np.nan)),
               "spread_bps": None if not np.isfinite(spread_bps) else round(spread_bps, 1),
               "qty": int(qty)}
        with open(self.log_dir / f"daily-decisions{self.tag}.jsonl", "a") as fh:
            fh.write(json.dumps(rec) + "\n")

    # ------------------------------------------------------------ intraday
    def phase_intraday(self, book: DailyBook, today: str, now, clock) -> None:
        close_et = pd.Timestamp(clock.next_close).tz_convert(ET)
        if not clock.is_open or close_et.hour != 16:
            self.log("[noise] market shut or early close - no intraday decision"); return
        for sig in self._noise_signals():
            self._intraday_one(book, today, sig)
        self._conviction_one(book, today)

    # ------------------------------------------ conviction day trade (TQQQ)
    def _conviction_live(self, book: DailyBook) -> bool:
        return (bool(self.d.conviction_weight) and self.d.conviction_mode == "auto"
                and not self.cash_account
                and book.daytrade_live and not book.is_killed("conv"))

    def _conviction_one(self, book: DailyBook, today: str) -> None:
        """At most one trade a day, and most days none: the day's FIRST
        noise-area breakout in TQQQ, taken only if it is strong
        (sg.breakout_strength >= conviction_strength). Long = TQQQ, short =
        SQQQ bought (no shorting). Out when the price falls back inside the band
        or through VWAP, else at the 15:57 flatten. RESULTS.md addendum 19."""
        if not self.d.conviction_weight:
            return
        sym = self.d.conviction_symbol
        c = book.conviction
        if c.get("day") != today:
            hist_log = c.get("history", [])
            b = self._day_bands(sym, today)
            if b is None:
                book.conviction = {"day": today, "done": True, "history": hist_log}; return
            book.conviction = c = {"day": today, "pos": 0, "done": False, "entry": None, "last_m": -1,
                                   "ub": b["ub"].round(4).tolist(), "lb": b["lb"].round(4).tolist(),
                                   "sigma": np.round(b["sigma"], 6).tolist(), "history": hist_log}
        mins = md.minute_today(sym).get(pd.Timestamp(today))
        if not mins:
            return
        px_c, v = mins["close"], mins["volume"]
        last_done = mins["last_minute"] - 1
        vwap = np.cumsum(px_c * v) / np.maximum(np.cumsum(v), 1)
        ub, lb, sig = np.array(c["ub"]), np.array(c["lb"]), np.array(c["sigma"])
        for m in range(sg.NOISE_FIRST, 390, sg.NOISE_STEP):
            if m <= c.get("last_m", -1) or m > last_done:
                continue
            c["last_m"] = m
            if c["done"] and c["pos"] == 0:
                break
            p = float(px_c[m])
            hh, mm = divmod(570 + m, 60)
            if c["pos"] == 0:
                d, strength = sg.breakout_strength(p, float(ub[m]), float(lb[m]), float(sig[m]))
                if d == 0:
                    continue
                if strength < self.d.conviction_strength:
                    c["done"] = True
                    self.log(f"[conv] {hh:02d}:{mm:02d} first breakout {d:+d} too weak "
                             f"({strength:.2f} < {self.d.conviction_strength}) - no trade today")
                    continue
                c.update(pos=d, entry=p, strength=round(strength, 3), entry_m=m)
                self.log(f"[conv] {hh:02d}:{mm:02d} STRONG breakout {d:+d} (strength {strength:.2f}) "
                         f"@ {p:.2f} -> {'long TQQQ' if d > 0 else 'long SQQQ'}")
            elif (c["pos"] == 1 and p < max(ub[m], vwap[m])) or (c["pos"] == -1 and p > min(lb[m], vwap[m])):
                r = c["pos"] * (p / c["entry"] - 1)
                c["history"].append({"date": today, "dir": c["pos"], "ret": round(r, 5)})
                self.log(f"[conv] {hh:02d}:{mm:02d} back inside the band @ {p:.2f}: out, {r*100:+.2f}% on TQQQ")
                c.update(pos=0, done=True)
        if self._conviction_live(book):
            self._sync_conviction_live(book, today)
        elif c.get("pos"):
            self.log(f"[conv:SHADOW] holding {c['pos']:+d} (would be {self.d.conviction_weight:.0%} of equity)")

    def _sync_conviction_live(self, book: DailyBook, today: str) -> None:
        c = book.conviction
        want_sym = {1: self.d.conviction_symbol, -1: self.d.conviction_inverse}.get(int(c.get("pos", 0)))
        for sym, p in list(book.leg_positions("conv").items()):
            if sym != want_sym and not any(o["sym"] == sym for o in book.open_orders().values()):
                self._order(book, today, sym, "sell", "conv", qty=float(p["qty"]), tif="day",
                            ref_px=float(p["avg_px"]), kind=f"x{c.get('last_m')}")
        if want_sym is None or want_sym in book.leg_positions("conv"):
            return
        if want_sym in self._foreign_symbols(book) or want_sym in {
                s for s, p in book.positions.items() if p.get("leg") != "conv"}:
            self.log(f"[conv] {want_sym} is held by another leg - skipping today"); return
        if any(o["sym"] == want_sym for o in book.open_orders().values()):
            return
        rows = md.live_rows([want_sym], max_age_min=5)
        if rows.empty:
            self.warn(f"[conv] no live price for {want_sym} - skipping"); return
        px = float(rows.price.iloc[0])
        qty = math.floor(self.d.conviction_weight * self._sizing_equity(book) / px)
        if qty >= 1:
            self._order(book, today, want_sym, "buy", "conv", qty=qty, tif="day", ref_px=px,
                        kind=f"e{c.get('entry_m')}")

    # ------------------------------------------------ intraday instruments
    def _noise_signals(self) -> list[str]:
        """Signal symbols of the intraday leg. They split its leverage budget
        equally (RESULTS.md addendum 16: QQQ + SMH, same 1.5x budget)."""
        return [self.d.noise_symbol] + [s for s in (self.d.noise_extra or {}) if s != self.d.noise_symbol]

    def _noise_state(self, book: DailyBook, sig: str | None = None) -> dict:
        sig = sig or self.d.noise_symbol
        if sig == self.d.noise_symbol:
            return book.noise                    # primary: the original state (and its history)
        return book.noise_more.setdefault(sig, {})

    def _set_noise_state(self, book: DailyBook, sig: str, st: dict) -> None:
        if sig == self.d.noise_symbol:
            book.noise = st
        else:
            book.noise_more[sig] = st

    def _intraday_one(self, book: DailyBook, today: str, sig: str) -> None:
        n = self._noise_state(book, sig)
        if n.get("day") != today:
            self._settle_noise(book, today, sig)     # in case the 09:15 run was missed
            self._init_noise(book, today, sig)
            n = self._noise_state(book, sig)
            if not n:
                return
        mins = md.minute_today(sig).get(pd.Timestamp(today))
        if not mins:
            self.warn(f"[noise] no minute bars for {sig} today"); return
        c, v = mins["close"], mins["volume"]
        last_done = mins["last_minute"] - 1          # the current minute is still forming
        ub, lb = np.array(n["ub"]), np.array(n["lb"])
        cum_v = np.cumsum(v)
        vwap = np.cumsum(c * v) / np.maximum(cum_v, 1)
        pos = int(n.get("pos", 0))
        for m in range(sg.NOISE_FIRST, 390, sg.NOISE_STEP):
            if m <= n.get("last_m", -1) or m > last_done:
                continue
            px = float(c[m])
            new = sg.noise_decide(pos, px, float(ub[m]), float(lb[m]), float(vwap[m]))
            if new != pos:
                if pos != 0:          # exit leg
                    n["realized"] += pos * (px / n["entry"] - 1.0)
                    n["trades"] += 1
                if new != 0:
                    n["entry"] = px
                    n["trades"] += 1
                hh, mm = divmod(570 + m, 60)
                self.log(f"[noise {sig}] {hh:02d}:{mm:02d} "
                         f"px {px:.2f} ub {ub[m]:.2f} lb {lb[m]:.2f} vwap {vwap[m]:.2f}: "
                         f"{pos:+d} -> {new:+d}")
                pos = new
            n["last_m"] = m
        n["pos"] = pos
        if book.daytrade_live:
            self._sync_noise_live(book, today, float(c[max(0, last_done)]), sig)
        else:
            self.log(f"[noise:SHADOW {sig}] position {pos:+d}, lev {n['lev']:.2f}, "
                     f"trades today {n['trades']}")

    def _day_bands(self, sym: str, today: str) -> dict | None:
        """Today's noise-area band for `sym` (sigma from the last noise_lookback
        sessions, official open when Schwab is available). None = cannot trade it."""
        hist = md.minute_history(sym, self.d.noise_lookback + 3)
        days = sorted(d for d in hist if d < pd.Timestamp(today))[-self.d.noise_lookback:]
        if len(days) < self.d.noise_lookback:
            self.warn(f"[intraday] {sym}: only {len(days)} sessions of history - no trading today")
            return None
        moves = np.vstack([np.abs(hist[d]["close"] / hist[d]["open"] - 1) for d in days])
        sigma = sg.noise_sigma(moves)
        daily = md.sip_daily([sym], pd.Timestamp(today) - pd.Timedelta(days=40), pd.Timestamp(today))[sym]
        daily = daily[daily.index < pd.Timestamp(today)]
        prev_close = float(daily["close"].iloc[-1])
        today_m = md.minute_today(sym).get(pd.Timestamp(today))
        if not today_m:
            self.warn(f"[intraday] {sym}: no open print yet"); return None
        day_open = today_m["open"]
        # IEX's first-minute open is unreliable (research: wrong opens, ~5% of
        # volume). Prefer Schwab's official consolidated open when logged in.
        src = "iex"
        if self.d.quote_source in ("auto", "schwab"):
            try:
                q = md.schwab_rows([sym], max_age_min=10)
                if not q.empty and "open" in q.columns and np.isfinite(q["open"].iloc[0]):
                    day_open = float(q["open"].iloc[0])
                    src = "schwab"
            except Exception:
                pass
        if src == "iex":
            self.warn(f"[intraday] {sym}: using IEX open (Schwab not available) - the open "
                      "can be wrong on IEX; bounds may be off")
        ub, lb = sg.noise_bounds(day_open, prev_close, sigma)
        return {"sigma": sigma, "ub": ub, "lb": lb, "open": day_open, "prev_close": prev_close,
                "daily": daily, "src": src}

    def _init_noise(self, book: DailyBook, today: str, sig: str | None = None) -> None:
        sym = sig or self.d.noise_symbol
        prior = self._noise_state(book, sym)
        b = self._day_bands(sym, today)
        if b is None:
            self._set_noise_state(book, sym, {}); return
        sigma, ub, lb, daily = b["sigma"], b["ub"], b["lb"], b["daily"]
        day_open, prev_close, src = b["open"], b["prev_close"], b["src"]
        lev = sg.noise_leverage(daily["close"], self.d.noise_target_vol, self.d.noise_max_lev)
        shadow_eq = float(prior.get("shadow_equity", book.start_equity))
        hist_log = prior.get("history", [])
        self._set_noise_state(book, sym, {"day": today, "pos": 0, "entry": None, "realized": 0.0, "trades": 0,
                      "last_m": -1, "lev": lev, "open": day_open, "prev_close": prev_close,
                      "ub": ub.round(4).tolist(), "lb": lb.round(4).tolist(),
                      "shadow_equity": shadow_eq, "history": hist_log, "settled": False,
                      "src": src})
        self.log(f"[noise] {sym} open {day_open:.2f} (src {src}) prev close {prev_close:.2f} "
                 f"lev {lev:.2f}  band at 10:00 [{lb[30]:.2f}, {ub[30]:.2f}]")

    def _settle_noise(self, book: DailyBook, today: str, sig: str | None = None) -> None:
        """Close yesterday's shadow position at its SIP close and compound.
        With several instruments each books its share of the budget."""
        if sig is None:
            for s in self._noise_signals():
                self._settle_noise(book, today, s)
            return
        n = self._noise_state(book, sig)
        if not n or n.get("settled") or n.get("day") == today:
            return
        day = n["day"]
        if n.get("pos", 0) != 0:
            b = md.sip_daily([sig], pd.Timestamp(day), pd.Timestamp(day) + pd.Timedelta(days=1))
            px = float(b[sig]["close"].iloc[0])
            n["realized"] += n["pos"] * (px / n["entry"] - 1.0)
            n["trades"] += 1
        r = n["lev"] * self._noise_share() * (n["realized"] - n["trades"] * NOISE_COST_BPS / 1e4)
        n["shadow_equity"] = float(n.get("shadow_equity", book.start_equity)) * (1 + r)
        n.setdefault("history", []).append({"date": day, "ret": round(r, 6)})
        n["settled"] = True
        self.log(f"[noise:{'LIVE' if book.daytrade_live else 'SHADOW'} {sig}] {day} settled "
                 f"{r*100:+.2f}% ({n['trades']} fills) -> shadow equity ${n['shadow_equity']:,.2f}")

    def _gate(self, book: DailyBook, equity: float) -> None:
        """Latch the day-trading leg on for the day, or keep it in shadow."""
        a = self.broker.account()
        acct = float(a.equity)
        was = book.daytrade_live
        # Reg T's $2,000 is an ACCOUNT minimum. Live, the bot's cap
        # (DAILY_LIVE_CAPITAL) only sizes it: a $1,000 cap on a $5,000 account
        # must not keep the leg in shadow, or its fills never get measured.
        book_min = self.d.live_min_capital if self.live else self.d.daytrade_min_equity
        book.daytrade_live = (self.d.daytrade_mode == "auto"
                              and not book.is_killed("noise")
                              and equity >= book_min
                              and acct >= self.d.daytrade_min_equity)
        # intraday leverage the broker actually grants (4 = leverage-enabled
        # margin, 2 = standard, 1 = cash); the IBS half stays invested intraday
        mult = float(getattr(a, "multiplier", 1) or 1)
        conv = self.d.conviction_weight if self._conviction_live(book) else 0.0
        if self.cash_account:
            # no borrowing: only the cash the night leg's open sells free up, held
            # in 3x ETFs, so the cap in underlying terms is 3 x that cash
            mult = 1.0 + (1.0 - self._w_ibs(book)) * (self.d.roth_etf_lev - 1.0)
        # every dollar of standard stock uses 1/mult of equity; a 3x ETF uses
        # conviction_margin (75%) per dollar, so conviction eats more room
        room = mult * max(0.0, 1.0 - conv * self.d.conviction_margin) if conv else mult
        book.noise_lev_cap = max(0.0, min(self.d.noise_max_lev, room - self._w_ibs(book)))
        if book.daytrade_live and not was:
            self.act(f"DAY-TRADE LEG SWITCHED ON: book equity ${equity:,.0f} >= "
                     f"${self.d.daytrade_min_equity:,.0f}")
        elif was and not book.daytrade_live:
            self.warn(f"day-trade leg switched OFF: book equity ${equity:,.0f}")

    def _log_alt_source(self, syms, elig, picks) -> None:
        """Diagnostics only: what Alpaca's IEX data would have picked. Builds a
        daily record of how much the data source changes the trades."""
        try:
            alt = md.live_rows(syms)
            if alt.empty:
                return
            alt = alt.join(elig[[c for c in ("prev_close", "vol20") if c in elig.columns]], how="inner")
            ap = sg.loser_picks(alt, day_ret_max=self.d.night_day_ret_max, ibs_max=self.d.night_ibs_max,
                                price_min=self.d.night_price_min, price_max=self.d.night_price_max)
            a, b = set(ap.index), set(picks.index)
            self.log(f"[night] data check: Schwab {len(b)} picks, Alpaca would have {len(a)}; "
                     f"both {len(a & b)}, Schwab-only {sorted(b - a)[:8]}, Alpaca-only {sorted(a - b)[:8]}")
            with open(self.log_dir / "daily-source-diff.jsonl", "a") as fh:
                fh.write(json.dumps({"date": dt.date.today().isoformat(), "schwab": sorted(b),
                                     "alpaca": sorted(a)}) + "\n")
        except Exception as exc:
            self.log(f"[night] data check skipped: {str(exc)[:80]}")

    def _sync_live_cash(self, book: DailyBook) -> None:
        """Real money: the bot's cash is whatever the broker says is free for it
        right now (free equity, capped, minus its own positions), not a ledger
        started on day one. Otherwise selling your holdings after the book was
        created, or depositing, would never reach the bot, and it would skip
        every buy as 'cash exhausted'. Closed trades keep the P&L record."""
        cap_eq = self._sizing_equity(book)
        marks = self._marks(book)
        mv = sum(float(p["qty"]) * float(marks.get(s, p["avg_px"])) for s, p in book.positions.items())
        book.cash = cap_eq - mv
        if book.start_equity < self.d.live_min_capital <= cap_eq:
            book.start_equity = cap_eq          # first day it actually had money to trade

    def _live_start(self) -> float:
        free = self.free_equity()
        cap = self.live_cap()
        return max(0.0, min(free, cap) if cap else free)

    def _noise_share(self) -> float:
        return 1.0 / len(self._noise_signals())

    def _noise_instrument(self, book: DailyBook, sig: str | None = None) -> str:
        """The signal symbol, unless another leg holds it today -- then its
        stand-in: QQQ -> QQQM (same index), SMH -> SOXX (semis, rho ~0.98)."""
        sig = sig or self.d.noise_symbol
        n = self._noise_state(book, sig)
        if n.get("instrument"):
            return n["instrument"]
        sym = sig
        other = {s for s, p in book.positions.items() if p.get("leg") != "noise"}
        other |= {o["sym"] for o in book.open_orders().values() if o["leg"] != "noise"}
        if sym in other or sym in self._foreign_symbols(book):
            sym = (self.d.noise_alt_symbol if sig == self.d.noise_symbol
                   else (self.d.noise_extra or {}).get(sig) or sig)
        n["instrument"] = sym
        return sym

    def _sync_noise_live(self, book: DailyBook, today: str, px_signal: float,
                         sig: str | None = None) -> None:
        sig = sig or self.d.noise_symbol
        if self.cash_account:
            return self._sync_noise_roth(book, today, sig)
        n = self._noise_state(book, sig)
        sym = self._noise_instrument(book, sig)
        px = px_signal
        if sym != sig:
            rows = md.live_rows([sym], max_age_min=5)
            if rows.empty:
                self.warn(f"[noise:LIVE] no live price for {sym} - skipping"); return
            px = float(rows.price.iloc[0])
        equity = self._sizing_equity(book)
        lev = min(float(n["lev"]), float(getattr(book, "noise_lev_cap", n["lev"]) or 0)) * self._noise_share()
        want = int(n["pos"]) * math.floor(lev * equity / px)
        have = float(book.positions.get(sym, {}).get("qty", 0.0))
        pend = [o for o in book.open_orders().values() if o["sym"] == sym]
        if pend:
            self.log(f"[noise:LIVE] order still working on {sym} - not stacking another"); return
        if have * want < 0:
            # flipping long<->short in one order is fragile at both brokers:
            # flatten now, open the new side at the next decision point
            self.log(f"[noise:LIVE] flip {have:+g} -> {want:+d}: flattening first")
            want = 0
        delta = want - have
        if abs(delta) >= 1:
            self._order(book, today, sym, "buy" if delta > 0 else "sell", "noise",
                        qty=abs(delta), tif="day", ref_px=px,
                        kind=f"m{n['last_m']}")

    def _sync_noise_roth(self, book: DailyBook, today: str, sig: str) -> None:
        """Roth IRA: no shorting and no borrowing. The signal's position is held
        long-only in 3x ETFs, long = bull ETF, short = bear ETF, at 1/3 of the
        underlying leverage (RESULTS.md addendum 20, research/sim/roth.py b1)."""
        n = self._noise_state(book, sig)
        pair = (self.d.roth_etfs or {}).get(sig)
        if not pair:
            return
        pos = int(n.get("pos", 0))
        want_sym = {1: pair[0], -1: pair[1]}.get(pos)
        held = book.leg_positions("noise")
        pend = {o["sym"] for o in book.open_orders().values()}
        for sym, p in held.items():
            if sym in pair and sym != want_sym and sym not in pend:
                self._order(book, today, sym, "sell", "noise", qty=float(p["qty"]), tif="day",
                            ref_px=self._noise_ref(book, sym, p), kind=f"m{n['last_m']}")
        if want_sym is None or want_sym in pend:
            return
        if want_sym in self._foreign_symbols(book):
            self.log(f"[noise:ROTH] {want_sym} is held outside this book - skipping"); return
        rows = md.live_rows([want_sym], max_age_min=5)
        if rows.empty:
            self.warn(f"[noise:ROTH] no live price for {want_sym} - skipping"); return
        px = float(rows.price.iloc[0])
        lev = min(float(n["lev"]), float(getattr(book, "noise_lev_cap", n["lev"]) or 0)) * self._noise_share()
        want = math.floor(lev / self.d.roth_etf_lev * self._sizing_equity(book) / px)
        have = float(held.get(want_sym, {}).get("qty", 0.0))
        delta = want - have
        if abs(delta) >= 1:
            self._order(book, today, want_sym, "buy" if delta > 0 else "sell", "noise",
                        qty=abs(delta), tif="day", ref_px=px, kind=f"m{n['last_m']}")

    def _flatten_noise(self, book: DailyBook, today: str, tif: str = "day",
                       kind: str = "flat") -> None:
        """Close every intraday-leg position. 15:57 ET with a market order
        (Alpaca paper expires close-auction orders unpredictably -- on the first
        live day a CLS flatten of QQQ filled 0 of 7), and again at the next
        open as a safety net for anything left over."""
        for sym, p in list({**book.leg_positions("noise"), **book.leg_positions("conv")}.items()):
            leg = p.get("leg", "noise")
            have = float(p["qty"])
            if abs(have) < 1e-9:
                continue
            if any(o["sym"] == sym for o in book.open_orders().values()):
                self.log(f"[noise] {sym}: an order is still working - not stacking a flatten"); continue
            self.log(f"[noise] flattening {have:+g} {sym} ({kind})")
            self._order(book, today, sym, "sell" if have > 0 else "buy", leg,
                        qty=abs(have), tif=tif, ref_px=self._noise_ref(book, sym, p),
                        kind=kind)

    def _noise_ref(self, book: DailyBook, sym: str, p: dict) -> float:
        for sig in self._noise_signals():
            n = self._noise_state(book, sig)
            if n.get("instrument", sig) == sym and n.get("entry"):
                return float(n["entry"])
        return float(p["avg_px"])

    # --------------------------------------------------------------- orders
    def _order(self, book: DailyBook, today: str, sym: str, side: str, leg: str, *,
               tif: str, ref_px: float, kind: str, qty: float | None = None,
               notional: float | None = None) -> None:
        coid = PaperBroker.coid({"live": "dlv", "roth": "dlr"}.get(self.account, "dly"),
                                sym, today, f"{leg}-{side}-{kind}")
        if coid in book.orders:
            self.log(f"  {sym}: {leg} {side} already submitted today (idempotent skip)"); return
        desc = f"{leg} {side} {sym} " + (f"${notional:,.2f}" if notional else f"{qty:g} sh") + \
               f" [{tif.upper()}] ref {ref_px:.2f}"
        if self.live and side == "buy" and kind == "entry":
            cap = self._sizing_equity(book)
            if cap < self.d.live_min_capital:
                self.warn(f"{desc} skipped: only ${cap:,.2f} free for the bot "
                          f"(< ${self.d.live_min_capital:,.0f}). Sell holdings or deposit cash.")
                return
        if self.dry_run:
            self.log(f"  [dry] would {desc}"); return
        try:
            broker_id = self.broker.submit(sym, side, tif, coid, qty=qty,
                                           notional=notional, ref_px=ref_px)
        except Exception as exc:
            msg = str(exc)
            if "client_order_id" in msg or "duplicate" in msg.lower():
                self.log(f"  {sym}: already at broker (idempotent)")
                book.register(coid, sym=sym, side=side, leg=leg, ref_px=ref_px, tif=tif)
                return
            if tif == "opg" and side == "sell":
                # missed the OPG window: get out at the open anyway
                self.warn(f"{sym}: OPG sell rejected ({msg[:80]}); retrying as DAY market")
                self._order(book, today, sym, side, leg, tif="day", ref_px=ref_px,
                            kind=kind + "-day", qty=qty)
                return
            self.warn(f"{desc} REJECTED: {msg[:140]}"); return
        route = str(getattr(self.broker, "last_route", "") or "")
        book.register(coid, sym=sym, side=side, leg=leg, ref_px=ref_px, tif=tif,
                      broker_id=broker_id, route=route,
                      submitted=dt.datetime.now().isoformat(timespec="seconds"))
        if route and route != "AUTO":
            desc += f" -> {route}"
        # persist immediately: Schwab has no client order id, so the book is
        # the idempotency record -- a crash here must not lose the order
        book.save(self.state_dir, self.fname)
        self.act(f"submitted {desc}")

    # ---------------------------------------------------------------- utils
    def free_equity(self, book: DailyBook | None = None) -> float:
        """Account equity minus the market value of every position this book
        does not own. = cash + the book's own positions. Your other holdings
        (and their gains or losses) never size the bot, so it cannot borrow
        against them. Deposits count immediately."""
        b = book if book is not None else DailyBook.load(self.state_dir, 0.0, self.fname)
        book_syms = b.owned_symbols()          # positions AND symbols with pending bot orders
        eq = float(self.broker.account().equity)
        foreign = sum(abs(float(p.qty) * float(p.current_price or 0))
                      for s, p in self.broker.positions().items() if s not in book_syms)
        return eq - foreign

    def live_cap(self) -> float | None:
        """DAILY_LIVE_CAPITAL in .env wins over config.yaml: `make pull` resets
        tracked files, and a cap that silently vanished would size the bot up."""
        env = (get_env("DAILY_ROTH_CAPITAL" if self.cash_account else "DAILY_LIVE_CAPITAL") or "").strip()
        if env and env.lower() not in ("none", "null", "off"):
            return float(env)
        return float(self.d.live_capital) if self.d.live_capital else None

    def _sizing_equity(self, book: DailyBook) -> float:
        """Paper: the virtual book. Live: free equity, optionally capped."""
        if self.live:
            free = self.free_equity(book)
            cap = self.live_cap()
            return max(0.0, min(free, cap) if cap else free)
        return book.equity(self._marks(book))

    def _marks(self, book: DailyBook) -> dict[str, float]:
        held = self.broker.positions()
        return {s: float(held[s].current_price) for s in book.positions
                if s in held and held[s].current_price is not None}

    def roth_limited_margin(self) -> bool:
        return (get_env("ROTH_LIMITED_MARGIN") or "").strip().lower() in ("yes", "on", "true", "1")

    WASH_DAYS = 31

    def _wash_symbols(self, today: str | None = None) -> set[str]:
        """Symbols the OTHER real-money book has held or traded in the last 31
        days. A loss sold in the brokerage account and bought back in the IRA
        within 30 days is a wash sale, and against an IRA the loss is gone for
        good, not deferred. So the two books never share a name inside that
        window (the T-bill ETF excepted: its losses are pennies)."""
        if not self.live:
            return set()
        other = "roth" if self.account == "live" else "live"
        p = self.state_dir / book_file(other)
        if not p.exists():
            return set()
        try:
            b = json.loads(p.read_text())
        except Exception:
            return set()
        cut = (pd.Timestamp(today or dt.date.today()) - pd.Timedelta(days=self.WASH_DAYS)).date().isoformat()
        out = set(b.get("positions", {}))
        out |= {o.get("sym") for o in (b.get("orders") or {}).values()
                if o.get("sym") and o.get("status") not in TERMINAL}
        out |= {c["sym"] for c in b.get("closed", []) if str(c.get("exit_date", "")) >= cut}
        out.discard(self.d.ibs_cash_symbol)
        return out

    def _foreign_symbols(self, book: DailyBook) -> set[str]:
        """Held or pending by the swing book, or held at the broker by anyone
        but this book, or inside the other real-money book's wash-sale window.
        Never trade these -- Alpaca nets positions per symbol."""
        out = set(self.broker.positions()) - set(book.positions)
        out |= self._wash_symbols() - set(book.positions)
        p = self.state_dir / "book-reversion.json"
        if not self.live and p.exists():     # the swing book trades the paper account only
            try:
                d = json.loads(p.read_text())
                out |= set(d.get("positions", {})) | set(d.get("pending", {}))
            except Exception:
                pass
        return out

    def _notify(self, book: DailyBook, equity: float, today: str) -> None:
        if not (self.actions or self.warnings):
            return
        body = "<h3>daily book</h3>" + \
            f"<p>equity ${equity:,.2f} ({(equity/book.start_equity-1)*100:+.1f}% since start)</p>" + \
            ("<h4>actions</h4><ul>" + "".join(f"<li>{a}</li>" for a in self.actions) + "</ul>" if self.actions else "") + \
            ("<h4>warnings</h4><ul>" + "".join(f"<li>{w}</li>" for w in self.warnings) + "</ul>" if self.warnings else "") + \
            "<pre>" + "\n".join(self.lines[-40:]) + "</pre>"
        subj = f"[daily{(' ' + self.account.upper() + ' $') if self.live else ''}] {'WARN ' if self.warnings else ''}{len(self.actions)} action(s), equity ${equity:,.0f}"
        try:
            self.log(self.notifier.send(subj, body,
                                        dedupe_key=f"daily:{today}:{len(self.lines)}:{len(self.actions)}"))
        except Exception as exc:
            self.log(f"  notify failed: {exc}")
