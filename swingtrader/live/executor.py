"""Daily autonomous loop for the paper account.

Two books run side by side:

  reversion  - LIVE. Places real (paper) orders. This is the sleeve that
               survived the falsification controls, the parameter sweeps and
               three rounds of bug fixes, so it is the only one risking fills.
  momentum   - SHADOW. Computes the same decisions and marks them against real
               opens, but places no orders. Its backtest parameters were chosen
               after seeing results, so it earns out-of-sample evidence before
               it earns order flow.

Timing mirrors the backtest exactly: decide on the last COMPLETE daily bar,
execute at the next open via a market-on-open order. Any run that cannot submit
for the next open still reconciles and re-arms protective stops.
"""
from __future__ import annotations

import json
import datetime as dt
from dataclasses import dataclass, asdict, field
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import Config, ROOT
from ..data import fetch_bars, refresh_bars
from ..metrics import zscore
from ..scan import scan_window
from ..universe import all_assets
from .broker import PaperBroker
from .lock import AccountLock, account_fingerprint
from .notify import Notifier

ET = "America/New_York"


@dataclass
class LivePosition:
    symbol: str
    qty: float
    entry_px: float
    entry_date: str
    stop_px: float
    peak: float
    bars_held: int = 0


@dataclass
class BookState:
    name: str
    live: bool
    positions: dict = field(default_factory=dict)      # symbol -> LivePosition dict
    pending: dict = field(default_factory=dict)        # symbol -> submitted-not-filled
    order_refs: dict = field(default_factory=dict)     # client_order_id -> {ref_px,...}
    equity: float = 100_000.0                          # shadow books track their own
    closed: list = field(default_factory=list)
    last_run: str = ""

    @classmethod
    def load(cls, path: Path, name: str, live: bool, equity: float) -> "BookState":
        if path.exists():
            try:
                return cls(**json.loads(path.read_text()))
            except Exception:
                pass
        return cls(name=name, live=live, equity=equity)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self), indent=2, default=str))
        tmp.replace(path)


class Executor:
    def __init__(self, cfg: Config, broker: PaperBroker | None = None,
                 state_dir: Path | None = None, log_dir: Path | None = None,
                 dry_run: bool = False, always_notify: bool = False):
        self.cfg = cfg
        self.dry_run = dry_run
        self.broker = broker or PaperBroker()
        self.state_dir = state_dir or ROOT / "state"
        self.log_dir = log_dir or ROOT / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.lines: list[str] = []
        self.actions: list[str] = []      # orders placed this run
        self.warnings: list[str] = []     # anything a human must see
        self.always_notify = always_notify
        self.notifier = Notifier(self.state_dir)

    # ------------------------------------------------------------------ util
    def log(self, msg: str) -> None:
        stamp = dt.datetime.now(dt.timezone.utc).astimezone().strftime("%H:%M:%S")
        line = f"[{stamp}] {msg}"
        self.lines.append(line)
        print(line, flush=True)

    def act(self, msg: str) -> None:
        self.actions.append(msg)
        self.log(f"  {msg}")

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)
        self.log(f"  WARN: {msg}")

    def _slippage_summary(self) -> dict | None:
        path = self.log_dir / "slippage.jsonl"
        if not path.exists():
            return None
        try:
            rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
        except Exception:
            return None
        if not rows:
            return None
        v = np.array([r["slippage_bps"] for r in rows], dtype=float)
        return {"n": len(v), "mean": float(v.mean()),
                "median": float(np.median(v)), "p90": float(np.percentile(v, 90))}

    def _flush_log(self) -> None:
        day = dt.date.today().isoformat()
        with open(self.log_dir / f"live-{day}.log", "a") as fh:
            fh.write("\n".join(self.lines) + "\n")

    # ----------------------------------------------------------------- data
    def load_market(self, refresh: bool = True) -> tuple[dict, pd.Timestamp]:
        """Universe bars, refreshed at the tail only.

        `refresh` is skipped while the market is open. Those runs cannot submit
        market-on-open orders anyway -- they reconcile fills, arm stops and
        measure slippage, all of which read broker state, not bars. And the
        last COMPLETE daily bar does not change intraday, so refreshing would
        buy nothing for 1-3 minutes of API calls against 14,760 symbols.
        """
        u = all_assets()
        today = dt.date.today()
        if refresh:
            self.log(f"refreshing recent bars for {len(u.symbols)} symbols "
                     f"(1-3 min; only the decision run pays this)...")
            refresh_bars(u.symbols + ["SPY", "SGOV"], today,
                         lookback_days=15, feed=self.cfg.data.feed,
                         adjustment=self.cfg.data.adjustment, verbose=True)
        else:
            self.log("market is open - using cached bars "
                     "(the last complete bar does not change intraday)")
        bars = fetch_bars(u.symbols + ["SPY", "SGOV"], self.cfg.data.start, today,
                          feed=self.cfg.data.feed,
                          adjustment=self.cfg.data.adjustment, verbose=False)
        bars = {s: d for s, d in bars.items() if len(d) > 150}
        asof = max(d.index.max() for d in bars.values())
        self.log(f"loaded {len(bars)} symbols; last complete bar {asof.date()}")
        return bars, asof

    # ------------------------------------------------------------- decisions
    def decide(self, bars: dict, asof: pd.Timestamp, mode: str,
               z_entry: float, state: BookState) -> tuple[list, list]:
        """Returns (entries, exits) for the NEXT open, using bars <= asof only."""
        sel, strat = self.cfg.selection, self.cfg.strategy
        form_start = asof - pd.Timedelta(days=int(self.cfg.walkforward.formation_days * 1.5))
        form = {s: d.loc[(d.index >= form_start) & (d.index <= asof)]
                for s, d in bars.items()}
        form = {s: d for s, d in form.items()
                if len(d) >= self.cfg.walkforward.formation_days * 0.8}
        picked = scan_window(form, self.cfg.cohort("highvol"), sel, mode=mode)
        watch = list(picked.index)

        exits, entries = [], []
        for sym, p in state.positions.items():
            pos = LivePosition(**p) if isinstance(p, dict) else p
            if sym not in bars or asof not in bars[sym].index:
                continue
            if pos.bars_held >= strat.time_stop_days and mode == "reversion":
                exits.append((sym, "time_stop"))
                continue
            z = zscore(bars[sym]["close"].loc[bars[sym].index <= asof], strat.z_window)
            if asof in z.index and np.isfinite(z.loc[asof]):
                if mode == "reversion" and float(z.loc[asof]) >= strat.z_exit:
                    exits.append((sym, "reversion"))

        exiting = {s for s, _ in exits}
        busy = set(state.positions) | set(state.pending)
        room = self.cfg.portfolio.max_positions - (len(busy) - len(exiting))
        for sym in watch:
            if room <= 0:
                break
            if sym in busy or sym not in bars:
                continue
            z = zscore(bars[sym]["close"].loc[bars[sym].index <= asof], strat.z_window)
            if asof not in z.index or not np.isfinite(z.loc[asof]):
                continue
            if float(z.loc[asof]) <= z_entry:
                entries.append((sym, float(bars[sym].loc[asof, "close"]),
                                float(z.loc[asof])))
                room -= 1
        return entries, exits

    # ------------------------------------------------------------------- run
    def run(self) -> int:
        fp = account_fingerprint(self.broker.key, self.broker.secret)
        with AccountLock(fp, self.state_dir):
            return self._run_locked()

    def _run_locked(self) -> int:
        clock = self.broker.clock()
        acct = self.broker.account()
        equity = float(acct.equity)
        self.log(f"=== swing-trader live run | equity ${equity:,.2f} | "
                 f"market {'OPEN' if clock.is_open else 'closed'} ===")

        # the decision run happens while the market is shut; the other two
        # only manage what is already open, so they skip the slow refresh
        bars, asof = self.load_market(refresh=not clock.is_open)
        today = dt.date.today().isoformat()

        rev_path = self.state_dir / "book-reversion.json"
        mom_path = self.state_dir / "book-momentum.json"
        rev = BookState.load(rev_path, "reversion", True, equity)
        mom = BookState.load(mom_path, "momentum", False, self.cfg.portfolio.equity)

        # ---- 1. reconcile the live book against the broker -----------------
        # Broker positions are the only source of truth for what we HOLD.
        # Submitted-but-unfilled orders live in `pending` and must NOT be
        # reconciled away: an OPG order sits unfilled for hours, and treating
        # that as "position gone" would re-submit it under the next day's id
        # and open the position twice.
        held = self.broker.positions()
        live_coids = {o.client_order_id for o in self.broker.open_orders()
                      if o.client_order_id}

        for sym, pend in list(rev.pending.items()):
            if sym in held:
                self.log(f"  reconcile: pending {sym} filled")
                rev.pending.pop(sym)
            elif pend.get("coid") in live_coids:
                self.log(f"  reconcile: {sym} order still working, leaving pending")
            else:
                self.log(f"  reconcile: {sym} order gone unfilled -> dropping")
                rev.pending.pop(sym)

        for sym in list(rev.positions):
            if sym not in held:
                p = rev.positions[sym]
                self.log(f"  reconcile: {sym} no longer held -> closing book entry")
                rev.closed.append({**p, "exit_date": today, "exit_reason": "broker"})
                rev.positions.pop(sym)
        for sym, p in held.items():
            px = float(p.avg_entry_price)
            if sym not in rev.positions:
                self.log(f"  reconcile: adopting position {sym} @ {px:.2f}")
                rev.positions[sym] = asdict(LivePosition(
                    symbol=sym, qty=float(p.qty), entry_px=px, entry_date=today,
                    stop_px=px * (1 - 10.0 / 100.0), peak=px))
            else:
                # trust the broker's fill price over our pre-fill estimate
                rev.positions[sym]["entry_px"] = px
                rev.positions[sym]["qty"] = float(p.qty)
                rev.positions[sym]["stop_px"] = max(
                    float(rev.positions[sym].get("stop_px", 0.0)), px * 0.90)

        # ---- 2. measure slippage on anything that filled --------------------
        fills = self.broker.measure_fills(rev.order_refs)
        if fills:
            for f in fills:
                self.log(f"  FILL {f.side} {f.qty:.0f} {f.symbol} @ {f.fill_px:.4f} "
                         f"(ref {f.ref_px:.4f}) slippage {f.slippage_bps:+.1f} bps")
            with open(self.log_dir / "slippage.jsonl", "a") as fh:
                for f in fills:
                    fh.write(json.dumps(asdict(f)) + "\n")
            avg = np.mean([f.slippage_bps for f in fills])
            self.log(f"  measured slippage this run: {avg:+.1f} bps "
                     f"(backtest assumed +20.0)")

        # ---- 3. advance holding clocks and peaks ---------------------------
        for sym, p in rev.positions.items():
            if sym in bars and asof in bars[sym].index:
                if p.get("last_bar") != str(asof.date()):
                    p["bars_held"] = int(p.get("bars_held", 0)) + 1
                    p["last_bar"] = str(asof.date())
                p["peak"] = max(float(p.get("peak", p["entry_px"])),
                                float(bars[sym].loc[asof, "high"]))

        # ---- 4. never hold unprotected overnight ---------------------------
        expected = {s: float(p["stop_px"]) for s, p in rev.positions.items()}
        missing = self.broker.unprotected(expected)
        for sym in missing:
            qty = float(held[sym].qty) if sym in held else 0
            if self.dry_run:
                self.log(f"  [dry] would arm stop {sym} @ {expected[sym]:.2f}")
                continue
            ok, note = self.broker.ensure_protection(sym, expected[sym], qty)
            if ok:
                self.act(note)
            elif note:
                self.warn(note)
        if not missing and rev.positions:
            self.log(f"  all {len(rev.positions)} positions carry a working stop")

        # ---- 5. decide for the next open -----------------------------------
        can_submit = not clock.is_open
        rev_entries, rev_exits = self.decide(bars, asof, "reversion",
                                             self.cfg.strategy.z_entry, rev)
        self.log(f"[reversion] holding {len(rev.positions)}; "
                 f"{len(rev_entries)} entry signal(s), {len(rev_exits)} exit signal(s)")

        if not can_submit:
            self.log("  market is open - OPG orders are not eligible; "
                     "reconcile-only this run")
        else:
            for sym, reason in rev_exits:
                qty = float(held[sym].qty) if sym in held else 0
                if self.dry_run:
                    self.log(f"  [dry] would SELL {qty:.0f} {sym} ({reason})"); continue
                o, note = self.broker.submit_exit("rev", sym, qty, today, reason)
                (self.act if o is not None else self.warn)(note)
                if o is not None:
                    rev.order_refs[o.client_order_id] = {
                        "ref_px": float(bars[sym].loc[asof, "close"]),
                        "symbol": sym, "kind": "exit", "day": today}
                    rev.closed.append({**rev.positions.get(sym, {}),
                                       "exit_date": today, "exit_reason": reason})
                    rev.positions.pop(sym, None)

            budget = equity * (self.cfg.portfolio.position_pct
                               or 1.0 / self.cfg.portfolio.max_positions)
            for sym, ref_px, z in rev_entries:
                qty = budget / ref_px
                if self.dry_run:
                    self.log(f"  [dry] would BUY {int(qty)} {sym} @ open "
                             f"(z={z:.2f}, ref {ref_px:.2f})"); continue
                o, note = self.broker.submit_entry("rev", sym, qty, today, ref_px)
                (self.act if o is not None else self.warn)(f"{note} z={z:.2f}")
                if o is not None:
                    rev.order_refs[o.client_order_id] = {
                        "ref_px": ref_px, "symbol": sym, "kind": "entry", "day": today}
                    # PENDING, not a position: it becomes a position only when
                    # the broker reports a fill.
                    rev.pending[sym] = {"coid": o.client_order_id, "day": today,
                                        "ref_px": ref_px, "qty": int(qty)}

        # ---- 6. shadow book: decide and mark, never order -------------------
        mom_entries, mom_exits = self.decide(bars, asof, "momentum", -1.0, mom)
        self.log(f"[momentum:SHADOW] holding {len(mom.positions)}; "
                 f"{len(mom_entries)} entry, {len(mom_exits)} exit signal(s)")
        for sym, p in list(mom.positions.items()):
            if sym in bars and asof in bars[sym].index:
                hi = float(bars[sym].loc[asof, "high"])
                p["peak"] = max(float(p.get("peak", p["entry_px"])), hi)
                trail = float(p["peak"]) * 0.75          # 25% trail
                p["stop_px"] = max(float(p["stop_px"]), trail)
                lo = float(bars[sym].loc[asof, "low"])
                if lo <= float(p["stop_px"]):
                    mom.closed.append({**p, "exit_date": str(asof.date()),
                                       "exit_reason": "trail"})
                    mom.positions.pop(sym)
        for sym, ref_px, z in mom_entries:
            if len(mom.positions) >= self.cfg.portfolio.max_positions:
                break
            mom.positions[sym] = asdict(LivePosition(
                symbol=sym, qty=int(mom.equity * 0.125 / ref_px), entry_px=ref_px,
                entry_date=today, stop_px=ref_px * 0.88, peak=ref_px))
            self.log(f"  [shadow] would BUY {sym} @ open (z={z:.2f})")

        # ---- 7. tell the human, but only when something actually happened ---
        if fills or self.actions or self.warnings or self.always_notify:
            status = self.notifier.activity(
                equity=equity, actions=self.actions, fills=fills,
                positions=rev.positions, pending=rev.pending,
                slippage=self._slippage_summary(), warnings=self.warnings,
                log_tail=self.lines,
                shadow={"holding": len(mom.positions), "closed": len(mom.closed)},
                dedupe_key=f"{today}:{len(self.actions)}:{len(fills)}:"
                           f"{len(self.warnings)}:{int(self.always_notify)}")
            self.log(status)
        else:
            self.log("nothing happened - no email sent")

        rev.last_run = dt.datetime.now().isoformat(timespec="seconds")
        mom.last_run = rev.last_run
        rev.save(rev_path)
        mom.save(mom_path)
        self.log(f"state saved; reversion holds {len(rev.positions)} "
                 f"(+{len(rev.pending)} pending), shadow holds {len(mom.positions)}")
        self._flush_log()
        return 0
