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

from ..config import Config, ROOT, get_env
from ..live.broker import PaperBroker
from .brokers import AlpacaAdapter, SchwabAdapter, make_adapter
from ..live.lock import AccountLock, account_fingerprint
from ..live.notify import Notifier
from ..universe import all_assets, valid_symbol
from . import marketdata as md
from . import signals as sg
from .book import DailyBook, book_file

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
    return "reconcile"


class DailyExecutor:
    def __init__(self, cfg: Config, account: str = "paper",
                 broker: PaperBroker | None = None,
                 state_dir: Path | None = None, log_dir: Path | None = None,
                 dry_run: bool = False):
        self.cfg, self.d = cfg, cfg.daily
        self.account = account
        self.live = account == "live"
        self.dry_run = dry_run
        b = broker or make_adapter(account, getattr(cfg.daily, "live_broker", "schwab"))
        # a raw PaperBroker (or test double) gets the Alpaca adapter
        self.broker = b if hasattr(b, "submit") else AlpacaAdapter(b)
        self.fname = book_file(account)
        self.tag = "" if not self.live else "-live"
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
        self.log(f"=== daily book [{self.account.upper()}] | phase {phase} | {now:%Y-%m-%d %H:%M} ET | "
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
            if float(getattr(acct, "multiplier", 1) or 1) < 2:
                # cash account: selling at the open and re-buying at the close
                # with the same unsettled proceeds is a good-faith violation
                self.warn("LIVE account is not a margin account (multiplier < 2). This book "
                          "re-uses same-day sale proceeds; in a cash account that is a "
                          "good-faith violation. Enable margin at Alpaca before trading.")
                return 1
        trading_day = clock.is_open or (
            pd.Timestamp(clock.next_open).tz_convert(ET).date() == now.date())
        self.reconcile(book, today)

        if not trading_day:
            self.log("not a trading day - reconcile only")
        elif phase == "open":
            self.phase_open(book, today)
        elif phase == "intraday":
            self.phase_intraday(book, today, now, clock)
        elif phase == "close":
            self.phase_close(book, today, now, clock)

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
                                         "filled_at": when}) + "\n")
            elif status in ("canceled", "expired", "rejected"):
                self.log(f"  order {coid} ended {status} unfilled")
        # anything the broker no longer holds cannot still be ours
        held = self.broker.positions()
        for sym in list(book.positions):
            if sym not in held and not any(o["sym"] == sym for o in book.open_orders().values()):
                self.warn(f"{sym} in daily book but not held at broker - dropping at book price")
                p = book.positions.pop(sym)
                book.cash += float(p["qty"]) * float(p["avg_px"])

    # ---------------------------------------------------------------- open
    def phase_open(self, book: DailyBook, today: str) -> None:
        marks = self._marks(book)
        equity = self._sizing_equity(book)
        self._settle_noise(book, today)
        self._gate(book, equity)

        # night leg: everything bought at yesterday's close goes at the open
        for sym, p in book.leg_positions("night").items():
            self._order(book, today, sym, "sell", "night", qty=float(p["qty"]),
                        tif="opg", ref_px=marks.get(sym, p["avg_px"]), kind="exit")

        # IBS leg: rank the universe by 12-1 momentum (month-end, bars before
        # today), then IBS < ibs_max on the last complete SIP bar of the top-k
        self._ibs_open(book, today, equity)

        # night-leg universe for this afternoon (pays the ~30s SIP pull now)
        u = [s for s in all_assets().symbols if valid_symbol(s)]
        elig = md.eligibility(u, dt.date.fromisoformat(today), price_min=self.d.night_price_min,
                              adv_min=self.d.night_adv_min, cache_dir=self.state_dir)
        self.log(f"[night] {len(elig)} names eligible today "
                 f"(close >= ${self.d.night_price_min:.0f}, 20d SIP $vol >= ${self.d.night_adv_min/1e6:.0f}M)")

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
        self.log("[ibs] IBS last bar: " + ", ".join(
            f"{s} {sg.ibs(b['high'], b['low'], b['close']):.2f}" for s, b in sorted(last.items()))
            + f" -> hold {targets or ('T-bills (' + cash_sym + ')' if cash_sym else 'cash')}")
        held = book.leg_positions("ibs")
        for sym, p in held.items():
            if sym not in targets:
                ref = bars.get(sym, pd.DataFrame({"close": [p["avg_px"]]}))["close"].iloc[-1]
                self._order(book, today, sym, "sell", "ibs", qty=float(p["qty"]),
                            tif="day", ref_px=float(ref), kind="exit")
        leg = self.d.ibs_weight * equity
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
    def phase_close(self, book: DailyBook, today: str, now, clock) -> None:
        close_et = pd.Timestamp(clock.next_close).tz_convert(ET)
        if close_et.date() != now.date() or close_et.hour != 16:
            self.log("early close today - night leg skipped (research excludes half days)")
            return
        if book.daytrade_live and book.noise.get("pos", 0) != 0:
            self._flatten_noise(book, today)

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
        picks = sg.loser_picks(rows, day_ret_max=self.d.night_day_ret_max,
                               ibs_max=self.d.night_ibs_max, price_min=self.d.night_price_min,
                               price_max=self.d.night_price_max)
        self.log(f"[night] scanned {len(rows)} live names -> {len(picks)} signal(s)")
        if src == "schwab":
            self._log_alt_source(syms, elig, picks)
        if picks.empty:
            return
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
        leg = self.d.night_weight * equity
        per = leg * frac
        # never let this book borrow beyond the gross its weights allow
        floor = -(max(1.0, self.d.ibs_weight + self.d.night_weight) - 1.0) * equity
        cash = book.cash
        for sym, r in picks.iterrows():
            qty = math.floor(per / r.price)        # auction orders are whole shares
            if qty < 1:
                self.log(f"  skip {sym}: ${per:.0f} buys 0 shares at {r.price:.2f}")
                continue
            if cash - qty * r.price < floor:
                self.log(f"  skip {sym}: book cash exhausted"); continue
            cash -= qty * r.price
            self.log(f"  {sym}: day {r.day_ret*100:+.1f}%  ibs {r.ibs:.2f}  px {r.price:.2f}")
            self._order(book, today, sym, "buy", "night", qty=qty, tif="cls",
                        ref_px=float(r.price), kind="entry")

    # ------------------------------------------------------------ intraday
    def phase_intraday(self, book: DailyBook, today: str, now, clock) -> None:
        close_et = pd.Timestamp(clock.next_close).tz_convert(ET)
        if not clock.is_open or close_et.hour != 16:
            self.log("[noise] market shut or early close - no intraday decision"); return
        n = book.noise
        if n.get("day") != today:
            self._settle_noise(book, today)     # in case the 09:15 run was missed
            self._init_noise(book, today)
            n = book.noise
            if not n:
                return
        mins = md.minute_today(self.d.noise_symbol).get(pd.Timestamp(today))
        if not mins:
            self.warn("[noise] no minute bars for today"); return
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
                self.log(f"[noise] {hh:02d}:{mm:02d} "
                         f"px {px:.2f} ub {ub[m]:.2f} lb {lb[m]:.2f} vwap {vwap[m]:.2f}: "
                         f"{pos:+d} -> {new:+d}")
                pos = new
            n["last_m"] = m
        n["pos"] = pos
        if book.daytrade_live:
            self._sync_noise_live(book, today, float(c[max(0, last_done)]))
        else:
            self.log(f"[noise:SHADOW] position {pos:+d}, lev {n['lev']:.2f}, "
                     f"trades today {n['trades']}")

    def _init_noise(self, book: DailyBook, today: str) -> None:
        sym = self.d.noise_symbol
        hist = md.minute_history(sym, self.d.noise_lookback + 3)
        days = sorted(d for d in hist if d < pd.Timestamp(today))[-self.d.noise_lookback:]
        if len(days) < self.d.noise_lookback:
            self.warn(f"[noise] only {len(days)} sessions of history - no trading today")
            book.noise = {}; return
        moves = np.vstack([np.abs(hist[d]["close"] / hist[d]["open"] - 1) for d in days])
        sigma = sg.noise_sigma(moves)
        daily = md.sip_daily([sym], pd.Timestamp(today) - pd.Timedelta(days=40), pd.Timestamp(today))[sym]
        daily = daily[daily.index < pd.Timestamp(today)]
        prev_close = float(daily["close"].iloc[-1])
        today_m = md.minute_today(sym).get(pd.Timestamp(today))
        if not today_m:
            self.warn("[noise] no open print yet"); book.noise = {}; return
        day_open = today_m["open"]
        ub, lb = sg.noise_bounds(day_open, prev_close, sigma)
        lev = sg.noise_leverage(daily["close"], self.d.noise_target_vol, self.d.noise_max_lev)
        shadow_eq = float(book.noise.get("shadow_equity", book.start_equity))
        hist_log = book.noise.get("history", [])
        book.noise = {"day": today, "pos": 0, "entry": None, "realized": 0.0, "trades": 0,
                      "last_m": -1, "lev": lev, "open": day_open, "prev_close": prev_close,
                      "ub": ub.round(4).tolist(), "lb": lb.round(4).tolist(),
                      "shadow_equity": shadow_eq, "history": hist_log, "settled": False}
        self.log(f"[noise] {sym} open {day_open:.2f} prev close {prev_close:.2f} "
                 f"lev {lev:.2f}  band at 10:00 [{lb[30]:.2f}, {ub[30]:.2f}]")

    def _settle_noise(self, book: DailyBook, today: str) -> None:
        """Close yesterday's shadow position at its SIP close and compound."""
        n = book.noise
        if not n or n.get("settled") or n.get("day") == today:
            return
        day = n["day"]
        if n.get("pos", 0) != 0:
            b = md.sip_daily([self.d.noise_symbol], pd.Timestamp(day), pd.Timestamp(day) + pd.Timedelta(days=1))
            px = float(b[self.d.noise_symbol]["close"].iloc[0])
            n["realized"] += n["pos"] * (px / n["entry"] - 1.0)
            n["trades"] += 1
        r = n["lev"] * (n["realized"] - n["trades"] * NOISE_COST_BPS / 1e4)
        n["shadow_equity"] = float(n.get("shadow_equity", book.start_equity)) * (1 + r)
        n.setdefault("history", []).append({"date": day, "ret": round(r, 6)})
        n["settled"] = True
        self.log(f"[noise:{'LIVE' if book.daytrade_live else 'SHADOW'}] {day} settled "
                 f"{r*100:+.2f}% ({n['trades']} fills) -> shadow equity ${n['shadow_equity']:,.2f}")

    def _gate(self, book: DailyBook, equity: float) -> None:
        """Latch the day-trading leg on for the day, or keep it in shadow."""
        a = self.broker.account()
        acct = float(a.equity)
        was = book.daytrade_live
        book.daytrade_live = (self.d.daytrade_mode == "auto"
                              and equity >= self.d.daytrade_min_equity
                              and acct >= self.d.daytrade_min_equity)
        # intraday leverage the broker actually grants (4 = leverage-enabled
        # margin, 2 = standard, 1 = cash); the IBS half stays invested intraday
        mult = float(getattr(a, "multiplier", 1) or 1)
        book.noise_lev_cap = max(0.0, min(self.d.noise_max_lev, mult - self.d.ibs_weight))
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

    def _live_start(self) -> float:
        free = self.free_equity()
        cap = self.live_cap()
        return max(0.0, min(free, cap) if cap else free)

    def _noise_instrument(self, book: DailyBook) -> str:
        """QQQ, unless another leg holds it today -- then QQQM (same index)."""
        n = book.noise
        if n.get("instrument"):
            return n["instrument"]
        sym = self.d.noise_symbol
        other = {s for s, p in book.positions.items() if p.get("leg") != "noise"}
        other |= {o["sym"] for o in book.open_orders().values() if o["leg"] != "noise"}
        if sym in other or sym in self._foreign_symbols(book):
            sym = self.d.noise_alt_symbol
        n["instrument"] = sym
        return sym

    def _sync_noise_live(self, book: DailyBook, today: str, px_signal: float) -> None:
        n = book.noise
        sym = self._noise_instrument(book)
        px = px_signal
        if sym != self.d.noise_symbol:
            rows = md.live_rows([sym], max_age_min=5)
            if rows.empty:
                self.warn(f"[noise:LIVE] no live price for {sym} - skipping"); return
            px = float(rows.price.iloc[0])
        equity = self._sizing_equity(book)
        lev = min(float(n["lev"]), float(getattr(book, "noise_lev_cap", n["lev"]) or 0))
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

    def _flatten_noise(self, book: DailyBook, today: str) -> None:
        sym = book.noise.get("instrument") or self.d.noise_symbol
        have = float(book.positions.get(sym, {}).get("qty", 0.0))
        if abs(have) >= 1:
            self._order(book, today, sym, "sell" if have > 0 else "buy", "noise",
                        qty=abs(have), tif="cls", ref_px=float(book.noise.get("entry") or 0),
                        kind="flat")

    # --------------------------------------------------------------- orders
    def _order(self, book: DailyBook, today: str, sym: str, side: str, leg: str, *,
               tif: str, ref_px: float, kind: str, qty: float | None = None,
               notional: float | None = None) -> None:
        coid = PaperBroker.coid("dlv" if self.live else "dly", sym, today, f"{leg}-{side}-{kind}")
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
        book.register(coid, sym=sym, side=side, leg=leg, ref_px=ref_px, tif=tif,
                      broker_id=broker_id, submitted=dt.datetime.now().isoformat(timespec="seconds"))
        # persist immediately: Schwab has no client order id, so the book is
        # the idempotency record -- a crash here must not lose the order
        book.save(self.state_dir, self.fname)
        self.act(f"submitted {desc}")

    # ---------------------------------------------------------------- utils
    def free_equity(self) -> float:
        """Account equity minus the market value of every position this book
        does not own. = cash + the book's own positions. Your other holdings
        (and their gains or losses) never size the bot, so it cannot borrow
        against them. Deposits count immediately."""
        book_syms = set(DailyBook.load(self.state_dir, 0.0, self.fname).positions)
        eq = float(self.broker.account().equity)
        foreign = sum(abs(float(p.qty) * float(p.current_price or 0))
                      for s, p in self.broker.positions().items() if s not in book_syms)
        return eq - foreign

    def live_cap(self) -> float | None:
        """DAILY_LIVE_CAPITAL in .env wins over config.yaml: `make pull` resets
        tracked files, and a cap that silently vanished would size the bot up."""
        env = (get_env("DAILY_LIVE_CAPITAL") or "").strip()
        if env and env.lower() not in ("none", "null", "off"):
            return float(env)
        return float(self.d.live_capital) if self.d.live_capital else None

    def _sizing_equity(self, book: DailyBook) -> float:
        """Paper: the virtual book. Live: free equity, optionally capped."""
        if self.live:
            free = self.free_equity()
            cap = self.live_cap()
            return max(0.0, min(free, cap) if cap else free)
        return book.equity(self._marks(book))

    def _marks(self, book: DailyBook) -> dict[str, float]:
        held = self.broker.positions()
        return {s: float(held[s].current_price) for s in book.positions
                if s in held and held[s].current_price is not None}

    def _foreign_symbols(self, book: DailyBook) -> set[str]:
        """Held or pending by the swing book, or held at the broker by anyone
        but this book. Never trade these -- Alpaca nets positions per symbol."""
        out = set(self.broker.positions()) - set(book.positions)
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
        subj = f"[daily{' LIVE $' if self.live else ''}] {'WARN ' if self.warnings else ''}{len(self.actions)} action(s), equity ${equity:,.0f}"
        try:
            self.log(self.notifier.send(subj, body,
                                        dedupe_key=f"daily:{today}:{len(self.lines)}:{len(self.actions)}"))
        except Exception as exc:
            self.log(f"  notify failed: {exc}")
