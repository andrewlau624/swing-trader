"""Live-vs-backtest review for the daily book. Read-only; places nothing.

  python scripts/review.py --since 2026-09-24          # paper (Alpaca) + live (Schwab)
  python scripts/review.py --since 2026-09-24 --no-live

Rebuilt entirely from the brokers and market data, so it runs anywhere with
the keys (no server logs needed) and never writes results into git -- the
repo is public. Output: printed, plus out/review-<today>.md (gitignored).

It answers four questions, in the order that isolates problems:
  1. SIGNAL   did it trade what the honest backtest signal picks that day?
  2. FILLS    did fills match the official auction prices the backtest used?
  3. PAPER vs LIVE   same days, same decisions: does Schwab execution differ?
  4. P&L      what did the backtest make on exactly those days vs actual?
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from swingtrader.config import Config, ROOT
from swingtrader.daily import marketdata as md
from swingtrader.daily import signals as sg

ET = ZoneInfo("America/New_York")
NIGHT_COST_BPS = 7.5          # per side, what the research assumed


# ------------------------------------------------------------------ fills
def paper_fills(since: dt.date) -> pd.DataFrame:
    """Daily-book fills from the Alpaca paper account (client ids 'dly.')."""
    from alpaca.trading.enums import QueryOrderStatus
    from alpaca.trading.requests import GetOrdersRequest
    from swingtrader.live.broker import PaperBroker
    b = PaperBroker()
    rows = []
    after = dt.datetime.combine(since, dt.time(0), tzinfo=ET) - dt.timedelta(days=1)
    while True:
        batch = b.client.get_orders(GetOrdersRequest(status=QueryOrderStatus.ALL, after=after,
                                                     limit=500, direction="asc"))
        if not batch:
            break
        for o in batch:
            coid = o.client_order_id or ""
            if coid.startswith("dly.") and o.filled_at and float(o.filled_qty or 0) > 0:
                parts = coid.split(".")
                leg = parts[3].split("-")[0] if len(parts) > 3 else "?"
                rows.append(dict(book="paper", sym=o.symbol, leg=leg,
                                 side=str(o.side).split(".")[-1].lower(),
                                 qty=float(o.filled_qty), px=float(o.filled_avg_price),
                                 when=pd.Timestamp(o.filled_at).tz_convert(ET),
                                 tif=str(o.time_in_force).split(".")[-1].lower()))
        if len(batch) < 500:
            break
        after = batch[-1].submitted_at
    return pd.DataFrame(rows)


def live_fills(since: dt.date, cfg) -> pd.DataFrame:
    """Bot fills from Schwab. Schwab orders carry no client id, so bot orders
    are recognised by shape: the bot only sends MARKET / MARKET_ON_CLOSE at its
    own run times; your manual trades (LIMIT, or other times) are excluded."""
    from swingtrader.daily.brokers import SchwabAdapter, schwab_client
    c = schwab_client(); a = SchwabAdapter(client=c)
    now = dt.datetime.now(ET)
    r = c.get_orders_for_account(a.hash, from_entered_datetime=dt.datetime.combine(since, dt.time(0), tzinfo=ET),
                                 to_entered_datetime=now); r.raise_for_status()
    ibs_syms = set(cfg.daily.ibs_symbols) | {cfg.daily.ibs_cash_symbol}
    rows = []
    for o in r.json() or []:
        if o.get("orderType") not in ("MARKET", "MARKET_ON_CLOSE"):
            continue
        entered = pd.Timestamp(o["enteredTime"]).tz_convert(ET)
        hm = entered.hour * 60 + entered.minute
        # 09:14-09:59: the open run can wait on the account lock, and unfilled
        # open sells are resent at the 09:50 reconcile
        bot_time = (9 * 60 + 14 <= hm <= 9 * 60 + 59 or 15 * 60 + 39 <= hm <= 15 * 60 + 49
                    or (10 * 60 <= hm <= 15 * 60 + 35 and entered.minute in (1, 2, 3, 31, 32, 33)))
        if not bot_time:
            continue
        sym, ins, _ = a._leg(o)
        fq, notional, when = 0.0, 0.0, None
        for act in o.get("orderActivityCollection", []) or []:
            for leg in act.get("executionLegs", []) or []:
                q = float(leg.get("quantity") or 0); fq += q
                notional += q * float(leg.get("price") or 0)
                when = pd.Timestamp(leg.get("time")).tz_convert(ET)
        if fq <= 0:
            continue
        leg = ("noise" if sym in (cfg.daily.noise_symbol, cfg.daily.noise_alt_symbol) and 10 * 60 <= hm < 15 * 60 + 39
               else "tbill" if sym == cfg.daily.ibs_cash_symbol
               else "ibs" if sym in ibs_syms else "night")
        rows.append(dict(book="live", sym=sym, leg=leg,
                         side="buy" if ins in ("BUY", "BUY_TO_COVER") else "sell",
                         qty=fq, px=notional / fq, when=when,
                         tif="cls" if o["orderType"] == "MARKET_ON_CLOSE" else "day"))
    return pd.DataFrame(rows)


# ------------------------------------------------------------ benchmarks
def auction_prices(fills: pd.DataFrame) -> pd.DataFrame:
    """Official session open/close (SIP daily bars) for every fill's day."""
    if fills.empty:
        return fills
    f = fills.copy()
    f["day"] = f.when.dt.tz_localize(None).dt.normalize()
    bars = md.sip_daily(sorted(f.sym.unique()), f.day.min() - pd.Timedelta(days=3),
                        f.day.max() + pd.Timedelta(days=1))
    def px(sym, day, col):
        b = bars.get(sym)
        return float(b.loc[day, col]) if b is not None and day in b.index else np.nan
    f["open_auction"] = [px(s, d, "open") for s, d in zip(f.sym, f.day)]
    f["close_auction"] = [px(s, d, "close") for s, d in zip(f.sym, f.day)]
    # benchmark: close auction for MOC fills, open auction for pre-open fills
    pre_open = f.when.dt.hour * 60 + f.when.dt.minute <= 9 * 60 + 35
    bench = np.where(f.tif == "cls", f.close_auction, np.where(pre_open, f.open_auction, np.nan))
    sign = np.where(f.side == "buy", 1, -1)
    f["bench"] = bench
    f["cost_bps"] = sign * (f.px / f.bench - 1) * 1e4          # + = worse than the auction
    return f


def round_trips(f: pd.DataFrame) -> pd.DataFrame:
    """Night leg: buy at close day d, sell at the next session. Also the
    backtest's version of the same trade: close auction -> open auction."""
    out = []
    for (book, sym), g in f[f.leg == "night"].sort_values("when").groupby(["book", "sym"]):
        buys, sells = g[g.side == "buy"], g[g.side == "sell"]
        for _, b in buys.iterrows():
            s = sells[sells.when > b.when].head(1)
            if s.empty:
                continue
            s = s.iloc[0]
            out.append(dict(book=book, sym=sym, day=b.day, qty=min(b.qty, s.qty),
                            ret=s.px / b.px - 1, pnl=min(b.qty, s.qty) * (s.px - b.px),
                            bt_ret=(s.open_auction / b.close_auction - 1) - 2 * NIGHT_COST_BPS / 1e4,
                            buy_cost_bps=b.cost_bps, sell_cost_bps=s.cost_bps))
    return pd.DataFrame(out)


# ------------------------------------------------------------ signal replay
def replay_night_signal(day: pd.Timestamp, cfg) -> set[str]:
    """What the honest research signal picks at 15:40 that day, from SIP
    minute bars (available 15 minutes later). Same rules as live."""
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from swingtrader.data import _clients
    from swingtrader.universe import all_assets, valid_symbol
    d = cfg.daily
    elig = md.eligibility([s for s in all_assets().symbols if valid_symbol(s)], day.date(),
                          price_min=d.night_price_min, adv_min=d.night_adv_min,
                          cache_dir=ROOT / "out" / "review-cache")
    data, _ = _clients()
    start = pd.Timestamp(day.date()).tz_localize(ET) + pd.Timedelta(hours=9, minutes=30)
    end = pd.Timestamp(day.date()).tz_localize(ET) + pd.Timedelta(hours=15, minutes=40)
    rows = {}
    syms = list(elig.index)
    for i in range(0, len(syms), 400):
        df = data.get_stock_bars(StockBarsRequest(symbol_or_symbols=syms[i:i + 400],
                                                  timeframe=TimeFrame.Minute, start=start.tz_convert("UTC"),
                                                  end=end.tz_convert("UTC"), feed="sip")).df
        if df.empty:
            continue
        for sym, g in df.reset_index().groupby("symbol"):
            rows[sym] = {"price": float(g.close.iloc[-1]), "high": float(g.high.max()),
                         "low": float(g.low.min())}
    live = pd.DataFrame.from_dict(rows, orient="index").join(elig[["prev_close", "vol20"]], how="inner")
    picks = sg.loser_picks(live, day_ret_max=d.night_day_ret_max, ibs_max=d.night_ibs_max,
                           price_min=d.night_price_min, price_max=d.night_price_max)
    kept, _ = sg.night_sizing(picks, vol_min=d.night_vol_min, crowd_n=d.night_crowd_n,
                              max_name_pct=d.night_max_name_pct)
    return set(kept.index)


# ------------------------------------------------------------------ report
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", required=True, help="first trading day to review, YYYY-MM-DD")
    ap.add_argument("--no-live", action="store_true", help="skip Schwab")
    ap.add_argument("--no-replay", action="store_true", help="skip the (slower) signal replay")
    a = ap.parse_args(argv)
    cfg = Config.load(); since = dt.date.fromisoformat(a.since)
    L = []
    say = lambda s="": (print(s), L.append(s))

    frames = [paper_fills(since)]
    if not a.no_live:
        try:
            frames.append(live_fills(since, cfg))
        except Exception as exc:
            say(f"(live/Schwab skipped: {exc})")
    f = pd.concat([x for x in frames if not x.empty], ignore_index=True) if any(
        not x.empty for x in frames) else pd.DataFrame()
    say(f"# Daily-book review since {since} (generated {dt.datetime.now(ET):%Y-%m-%d %H:%M} ET)")
    if f.empty:
        say("\nNo daily-book fills yet."); return _write(L)
    f = auction_prices(f)

    say("\n## 2. Fills vs the official auction price (what the backtest assumed)")
    say(f"Research assumed {NIGHT_COST_BPS}bp per side on the night leg. + = worse than the auction.\n")
    for (book, leg, side), g in f.dropna(subset=["cost_bps"]).groupby(["book", "leg", "side"]):
        say(f"- {book:5s} {leg:6s} {side:4s}: n={len(g):3d}  mean {g.cost_bps.mean():+6.1f}bp  "
            f"median {g.cost_bps.median():+6.1f}bp  worst {g.cost_bps.max():+6.1f}bp")

    rt = round_trips(f)
    say("\n## 4. Night-leg round trips: actual vs backtest on the same trades")
    if rt.empty:
        say("No completed round trips yet (buys at 15:40 close out the next morning).")
    else:
        for book, g in rt.groupby("book"):
            say(f"- {book:5s}: {len(g)} trades, win {100*(g.ret>0).mean():.0f}%, avg {g.ret.mean()*100:+.2f}% "
                f"(backtest same trades {g.bt_ret.mean()*100:+.2f}%), P&L ${g.pnl.sum():+,.2f}. "
                f"Gap {(g.ret.mean()-g.bt_ret.mean())*1e4:+.0f}bp/trade = buy cost {g.buy_cost_bps.mean():+.0f}bp "
                f"+ sell cost {g.sell_cost_bps.mean():+.0f}bp vs the {2*NIGHT_COST_BPS:.0f}bp assumed")

    say("\n## 5. Pre-registered kill rules (signals.KILL_*, fixed 2026-09-24)")
    say(f"Night leg dies at >= {sg.KILL_MIN_TRADES['night']} round trips with a losing mean and "
        f"t < {sg.KILL_T}, or open sells > {sg.KILL_EXIT_COST_BPS:g}bp/side over "
        f"{sg.KILL_EXIT_COST_MIN_N}. The bot applies these itself every run.")
    if not rt.empty:
        for book, g in rt.groupby("book"):
            r = g.ret.to_numpy()
            t = r.mean() / (r.std(ddof=1) / np.sqrt(len(r))) if len(r) > 1 and r.std() > 0 else float("nan")
            v = sg.kill_check([{"leg": "night", "ret": x} for x in r])
            need = sg.KILL_MIN_TRADES["night"] - len(r)
            say(f"- {book:5s} night: n {len(r)}, mean {r.mean()*1e4:+.1f}bp, t {t:+.2f} -> "
                + ("KILL" if v else (f"no verdict yet ({need} more round trips)" if need > 0 else "keep")))

    say("\n## 3. Paper vs live on the same days")
    if {"paper", "live"} <= set(f.book):
        for leg in ("night", "ibs", "noise"):
            p = f[(f.book == "paper") & (f.leg == leg)]; l = f[(f.book == "live") & (f.leg == leg)]
            if len(p) and len(l):
                say(f"- {leg}: paper cost {p.cost_bps.mean():+.1f}bp over {len(p)} fills, "
                    f"live {l.cost_bps.mean():+.1f}bp over {len(l)}")
        pd_ = f[(f.leg == "night") & (f.side == "buy")].groupby(["day", "book"]).sym.apply(set).unstack()
        for day, r in pd_.iterrows():
            ps, ls = r.get("paper") or set(), r.get("live") or set()
            if isinstance(ps, set) and isinstance(ls, set):
                say(f"  {day.date()}: paper {len(ps)} names, live {len(ls)}, both {len(ps & ls)}"
                    + (f", live-only {sorted(ls-ps)}" if ls - ps else "")
                    + (f", paper-only {sorted(ps-ls)}" if ps - ls else ""))
    else:
        say("Only one book has fills so far.")

    if not a.no_replay:
        say("\n## 1. Signal: live picks vs the honest backtest signal (SIP data)")
        buys = f[(f.leg == "night") & (f.side == "buy")]
        for day, g in buys.groupby("day"):
            try:
                ref = replay_night_signal(day, cfg)
            except Exception as exc:
                say(f"- {day.date()}: replay failed ({str(exc)[:80]})"); continue
            for book, h in g.groupby("book"):
                got = set(h.sym)
                say(f"- {day.date()} {book}: traded {len(got)}, backtest signal {len(ref)}, agree {len(got & ref)}"
                    + (f"; missed {sorted(ref-got)[:10]}" if ref - got else "")
                    + (f"; extra {sorted(got-ref)[:10]}" if got - ref else ""))
        say("\n(Missed names are usually whole-share rounding at small size, or a stale quote.")
        say("Extra names mean the live quotes disagreed with SIP: check `make schwab-quote-check`.)")
    return _write(L)


def _write(lines):
    out = ROOT / "out"; out.mkdir(exist_ok=True)
    p = out / f"review-{dt.date.today().isoformat()}.md"
    p.write_text("\n".join(lines) + "\n")
    print(f"\nwritten to {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
