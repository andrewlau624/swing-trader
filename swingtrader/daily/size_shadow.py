"""Capacity shadow (2026-10-05): the live book's real decisions, sized for accounts it does not have yet — SHADOW, never orders.

Paper cannot answer the high-capital questions: paper fills never move the auction, and no broker the bot uses trades
futures. So each completed session, this module takes what the LIVE account actually decided and re-sizes it at
SIZES ($30k / $100k / $250k), next to the live account's own equity:

  night leg   picks = that day's live decisions (logs/daily-decisions-live.jsonl); per name
              target = V x night_weight x min(1/n, night_max_name_pct) x gap_scale (no tilt, no crowd cut: approx.),
              whole shares at the official close (SIP daily close of the trade date). Impact under the square-root
              law the live impact cap uses (signals.night_impact_cap, Study X): cost/side = Y sigma sqrt(q / ADV20),
              Y = IMPACT_Y (NEXT.md: "turn on (4 ...) once the account passes ~$25k"). Gross = next open / close - 1.
              Logged: deployed $, max % of ADV, names the impact cap would trim, gross and net-of-impact P&L.
              Read: at which size does net-of-impact fall well below gross (where the leg stops scaling)?
  noise / MNQ the live QQQ noise trades (logs/daily-fills-live.jsonl, leg "noise"), as a return per $ of position, sized
              at the live leverage (signals.noise_leverage on prior closes, x 1/2 for the QQQ half) two ways:
              fractional QQQ (the ideal) and whole MNQ contracts (leap.signals.futures_contracts; index = QQQ x
              NDX_PER_QQQ, ~1% approx.; basis and roll ignored). Read: how far whole contracts drift from the ideal
              at each size, and below which size one contract is already over the leverage cap (0 contracts).

Rows are keyed by trade date and appended once (idempotent). Live equity = state/book-daily-live.json equity_log.
"""
from __future__ import annotations

import datetime as dt
import json
import math
from pathlib import Path

import numpy as np

LOG_NAME = "size-shadow.jsonl"
SIZES = (30_000, 100_000, 250_000)
IMPACT_Y = 4.0
NDX_PER_QQQ = 41.0          # Nasdaq-100 level per QQQ share (drifts ~0.2%/yr with the expense ratio)
NOISE_SHARE = 0.5           # the QQQ half of the QQQ/SMH noise leg
NEED = 60


def _read(p: Path) -> list[dict]:
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def night_at(picks: list[dict], bars: dict, equity: float, *, weight: float, max_name_pct: float,
             gap: float, impact_y: float = IMPACT_Y, edge_bps: float = 22.0) -> dict:
    """One session's night picks at `equity`. bars: sym -> (close of the trade date, next open)."""
    from . import signals as sg
    usable = [p for p in picks if p["sym"] in bars]
    if not usable:
        return dict(n=0, deployed=0.0, gross=0.0, net=0.0, max_pct_adv=0.0, capped=0)
    per = equity * weight * min(1.0 / len(usable), max_name_pct) * gap
    dep = gross = cost = mx = 0.0
    capped = 0
    for p in usable:
        close, nxt = bars[p["sym"]]
        qty = math.floor(per / close)
        q = qty * close
        adv, v20 = float(p.get("adv20") or np.nan), float(p.get("vol20") or np.nan)
        cap = float(sg.night_impact_cap(np.array([adv]), np.array([v20]), edge_bps, impact_y)[0])
        capped += int(per > cap)
        side = impact_y * v20 / math.sqrt(252) * math.sqrt(q / adv) if adv > 0 and v20 > 0 and q > 0 else 0.0
        dep += q
        gross += q * (nxt / close - 1)
        cost += q * 2 * side
        mx = max(mx, q / adv if adv > 0 else 0.0)
    return dict(n=len(usable), deployed=round(dep, 2), gross=round(gross, 2), net=round(gross - cost, 2),
                max_pct_adv=round(mx * 100, 4), capped=capped)


def noise_day(fills: list[dict]) -> tuple[float, float] | None:
    """(return per $ of peak position, price of the first fill) for one session's QQQ noise fills; None unless flat."""
    pos = peak = pnl = 0.0
    first = None
    for f in fills:
        q = float(f["qty"]) * (1 if f["side"] == "buy" else -1)
        px = float(f["fill_px"])
        first = first or px
        pos += q
        pnl -= q * px
        peak = max(peak, abs(pos))
    if abs(pos) > 1e-9 or not peak:
        return None
    return pnl / (peak * first), first


def noise_at(r: float, px: float, lev: float, equity: float, max_lev: float) -> dict:
    from ..leap.signals import FUTURES, futures_contracts
    ndx = px * NDX_PER_QQQ
    k = futures_contracts(equity, ndx, "MNQ", lev, max_lev)
    mnq_lev = k * FUTURES["MNQ"]["mult"] * ndx / equity
    return dict(ideal=round(lev * equity * r, 2), mnq=round(mnq_lev * equity * r, 2), contracts=k,
                lev=round(lev, 3), mnq_lev=round(mnq_lev, 3))


def summary(rows: list[dict]) -> dict:
    out = {"n": len(rows)}
    for v in ("live",) + tuple(str(s) for s in SIZES):
        nr = [r["night"][v] for r in rows if v in r.get("night", {})]
        dep = sum(x["deployed"] for x in nr)
        out[f"night_{v}"] = dict(trips=sum(x["n"] for x in nr),
                                 gross_bp=1e4 * sum(x["gross"] for x in nr) / dep if dep else None,
                                 net_bp=1e4 * sum(x["net"] for x in nr) / dep if dep else None,
                                 max_pct_adv=max((x["max_pct_adv"] for x in nr), default=0.0),
                                 capped=sum(x["capped"] for x in nr))
        mr = [r["noise"][v] for r in rows if v in r.get("noise", {})]
        if mr:
            out[f"mnq_{v}"] = dict(days=len(mr), ideal=sum(x["ideal"] for x in mr), mnq=sum(x["mnq"] for x in mr),
                                   zero=sum(1 for x in mr if x["contracts"] == 0))
    return out


def line(rows: list[dict]) -> str:
    s = summary(rows)
    bp = lambda x: "n/a" if x is None else f"{x:+.0f}bp"
    night = "; ".join(f"{k[6:]} gross {bp(v['gross_bp'])} net {bp(v['net_bp'])} (max {v['max_pct_adv']:.2f}% ADV)"
                      for k, v in s.items() if k.startswith("night_") and k != "night_live")
    mnq = "; ".join(f"{k[4:]} MNQ ${v['mnq']:+,.0f} vs ideal ${v['ideal']:+,.0f}" + (f" ({v['zero']} days 0 contracts)" if v["zero"] else "")
                    for k, v in s.items() if k.startswith("mnq_") and k != "mnq_live")
    return f"{s['n']} sessions | night {night or 'no picks yet'} | noise {mnq or 'no QQQ trades yet'}"


def run(state_dir: Path, log_dir: Path, today: dt.date | None = None, log=print, bars=None, cfg=None) -> dict:
    """Append every complete session not yet logged. `bars` = {sym: DataFrame(index=trade date, open, close)} for tests."""
    import pandas as pd
    from . import marketdata as md
    from . import signals as sg
    state_dir, log_dir = Path(state_dir), Path(log_dir)
    path = state_dir / LOG_NAME
    rows = _read(path)
    done = {r["date"] for r in rows}
    if cfg is None:
        from ..config import Config
        cfg = Config.load().daily.for_account("live")[0]
    book = state_dir / "book-daily-live.json"
    eq = {r["date"]: float(r["equity"]) for r in (json.loads(book.read_text()).get("equity_log", []) if book.exists() else [])}
    picks: dict[str, list[dict]] = {}
    for p in _read(log_dir / "daily-decisions-live.jsonl"):
        picks.setdefault(p["date"], []).append(p)
    fills: dict[str, list[dict]] = {}
    for f in _read(log_dir / "daily-fills-live.jsonl"):
        if f.get("leg") == "noise" and f.get("sym") == "QQQ" and f.get("filled_at"):
            fills.setdefault(str(md.trade_date(f["filled_at"]).date()), []).append(f)
    dates = sorted(d for d in (set(picks) | set(fills)) if d not in done and d in eq and (today is None or d < str(today)))
    if dates:
        if bars is None:
            syms = sorted({p["sym"] for d in dates for p in picks.get(d, [])} | {"QQQ"})
            bars = md.sip_daily(syms, pd.Timestamp(min(dates)) - pd.Timedelta(days=40))
        qqq = bars.get("QQQ")
        for d in dates:
            t = pd.Timestamp(d)
            row = dict(date=d, live_equity=eq[d], night={}, noise={})
            px, nxt_day = {}, None
            for p in picks.get(d, []):
                b = bars.get(p["sym"])
                if b is None or t not in b.index:
                    continue
                after = b.index[b.index > t]
                if len(after):
                    px[p["sym"]] = (float(b.at[t, "close"]), float(b.at[after[0], "open"]))
                    nxt_day = after[0]
            if picks.get(d) and nxt_day is None:
                continue                                    # next open not printed yet: try again tomorrow
            if px:
                gap = sg.gap_scale(t, nxt_day, cfg.night_weekend_scale)
                for v, e in [("live", eq[d])] + [(str(s), float(s)) for s in SIZES]:
                    row["night"][v] = night_at(picks[d], px, e, weight=cfg.night_weight, max_name_pct=cfg.night_max_name_pct,
                                               gap=gap, edge_bps=cfg.night_impact_edge_bps)
            nd = noise_day(sorted(fills.get(d, []), key=lambda f: f["filled_at"]))
            if nd and qqq is not None:
                lev = sg.noise_leverage(qqq["close"][qqq.index < t], cfg.noise_target_vol, cfg.noise_max_lev) * NOISE_SHARE
                for v, e in [("live", eq[d])] + [(str(s), float(s)) for s in SIZES]:
                    row["noise"][v] = noise_at(nd[0], nd[1], lev, e, cfg.noise_max_lev)
            row["noise_r_bp"] = round(nd[0] * 1e4, 2) if nd else None
            rows.append(row)
        rows.sort(key=lambda r: r["date"])
        path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    log(f"[size] {line(rows)}")
    return summary(rows)


if __name__ == "__main__":
    import sys
    from ..config import ROOT
    day = dt.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else None
    run(ROOT / "state", ROOT / "logs", day)
