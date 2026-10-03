"""Pick-quality lead (research/drafts/pick_quality_log.md, 2026-10-02): live night-leg auction cost and bounce by price bucket.

Backtests charge $5-10 night names ~15bp/side (the tier spread model), which erases their gross edge (+40bp/night vs ~0bp for
$50+ names, 2021-23). The night leg trades only in the official auctions, where live costs looked ~0bp (add. 29). This watch
measures it on the live fills, per price bucket, and never orders:
  buy cost  = fill / official closing cross - 1   (bp, + = paid more)
  sell cost = 1 - fill / official opening cross   (bp, + = received less)
  bounce    = official open / official close - 1  (the backtest's night return for the same trip)
Fills: logs/daily-fills-{live,roth}.jsonl, `leg == "night"`, a buy paired with the next sell of the same symbol. Official
crosses = regular-session daily bars (`marketdata.sip_daily`, labelled by trade date: open/close are the auction prints).
Read at NEED trips in the $5-10 bucket: if its median all-in cost is <= READ_BPS per side, a cheap-name tilt is worth a
pre-registered test; also logs whether $50+ trips keep bouncing least (the PQ7b watch).
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

LOG_NAME = "pick-cost.jsonl"
FILLS = ("daily-fills-live.jsonl", "daily-fills-roth.jsonl")
BUCKETS = ((5, 10, "$5-10"), (10, 20, "$10-20"), (20, 50, "$20-50"), (50, 1e12, "$50+"))
NEED, READ_BPS = 100, 5.0


def bucket(price: float) -> str:
    for lo, hi, lab in BUCKETS:
        if lo <= price < hi:
            return lab
    return "<$5"


def _jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def trips(fills: list[dict], account: str) -> list[dict]:
    """Night buys paired with the next night sell of the same symbol (by fill time)."""
    n = sorted((f for f in fills if f.get("leg") == "night" and f.get("fill_px")), key=lambda f: f.get("filled_at", ""))
    out, used = [], set()
    for i, b in enumerate(n):
        if b.get("side") != "buy":
            continue
        for j in range(i + 1, len(n)):
            s = n[j]
            if j not in used and s.get("side") == "sell" and s.get("sym") == b.get("sym"):
                used.add(j)
                out.append(dict(account=account, sym=b["sym"], buy_at=b["filled_at"][:10], sell_at=s["filled_at"][:10],
                                buy_px=float(b["fill_px"]), sell_px=float(s["fill_px"]), qty=float(b.get("qty") or 0)))
                break
    return out


def score(t: dict, buy_close: float | None, sell_open: float | None) -> dict:
    r = dict(t, bucket=bucket(t["buy_px"]))
    if buy_close and sell_open:
        r.update(official_close=buy_close, official_open=sell_open,
                 buy_cost_bp=(t["buy_px"] / buy_close - 1) * 1e4, sell_cost_bp=(1 - t["sell_px"] / sell_open) * 1e4,
                 bounce_bp=(sell_open / buy_close - 1) * 1e4, net_bp=(t["sell_px"] / t["buy_px"] - 1) * 1e4)
    return r


def summary(rows: list[dict]) -> dict:
    import statistics as st
    out = {}
    for _, _, lab in BUCKETS:
        x = [r for r in rows if r["bucket"] == lab and "buy_cost_bp" in r]
        if x:
            cost = [(r["buy_cost_bp"] + r["sell_cost_bp"]) / 2 for r in x]
            out[lab] = dict(n=len(x), cost_side_med=st.median(cost), bounce_mean=st.mean(r["bounce_bp"] for r in x),
                            net_mean=st.mean(r["net_bp"] for r in x))
        else:
            out[lab] = dict(n=0)
    return out


def line(rows: list[dict]) -> str:
    s = summary(rows)
    parts = [f"{k} n {v['n']}" + (f", cost {v['cost_side_med']:+.1f}bp/side, bounce {v['bounce_mean']:+.0f}bp" if v["n"] else "")
             for k, v in s.items()]
    cheap = s["$5-10"]
    verdict = ""
    if cheap["n"] >= NEED:
        verdict = (" -> READ: $5-10 live cost <= %.0fbp/side, register a cheap-name tilt test" % READ_BPS
                   if cheap["cost_side_med"] <= READ_BPS else " -> READ: $5-10 live cost too high, the tier model stands")
    return "; ".join(parts) + verdict


def run(state_dir: Path, logs_dir: Path, log=print, bars=None) -> dict:
    state_dir, logs_dir = Path(state_dir), Path(logs_dir)
    path = state_dir / LOG_NAME
    rows = _jsonl(path)
    have = {(r["account"], r["sym"], r["buy_at"]) for r in rows if "buy_cost_bp" in r}
    new = []
    for f in FILLS:
        acct = "roth" if "roth" in f else "taxable"
        for t in trips(_jsonl(logs_dir / f), acct):
            if (t["account"], t["sym"], t["buy_at"]) not in have:
                new.append(t)
    if new:
        if bars is None:
            import pandas as pd
            from . import marketdata as md
            bars = md.sip_daily(sorted({t["sym"] for t in new}), pd.Timestamp(min(t["buy_at"] for t in new)) - pd.Timedelta(days=3))
        import pandas as pd
        keep = [r for r in rows if "buy_cost_bp" in r]
        for t in new:
            g = bars.get(t["sym"])
            bc = so = None
            if g is not None and len(g):
                d0, d1 = pd.Timestamp(t["buy_at"]), pd.Timestamp(t["sell_at"])
                bc = float(g.at[d0, "close"]) if d0 in g.index else None
                so = float(g.at[d1, "open"]) if d1 in g.index else None
            keep.append(score(t, bc, so))
        rows = sorted(keep, key=lambda r: (r["buy_at"], r["account"], r["sym"]))
        path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    log(f"[pick-cost] {line(rows)}")
    return summary(rows)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    run(root / "state", root / "logs")
