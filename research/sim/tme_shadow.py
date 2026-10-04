"""Study TME-L: leveraged month-end Treasury sleeve, FORWARD SHADOW (pre-registered round1_prose.md, N 814 -> 816,
commit e68391a). No orders. The base window is TME1, frozen: close(T-3) -> close(T), T = the month's last session.

    PYTHONPATH=. .venv/bin/python -m research.sim.tme_shadow forward   # log every completed forward window (idempotent)
    PYTHONPATH=. .venv/bin/python -m research.sim.tme_shadow history   # one-time instrument measurement 2009-26 (report only)

Rules (per unit of sleeve capital C): L1 TLT 1.0x C; L2 TLT 2.0x C on Reg T margin, debit 1.0x C at 12.5%/yr act/360 on
calendar days; L3 TMF 1.0x C (3x exposure). Roth report-only: UBT 1.0x C (2x). Costs/side: TLT 2bp, TMF 5bp, UBT 15bp.
Forward prices = official closing-auction prints (largest-size closing cross, the repo's max-by-size rule) + cash
distributions with ex-date inside the window. Log: state/tme-shadow.jsonl (testing.py REGISTRY "TME-L").
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import subprocess
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
LOG_NAME = "tme-shadow.jsonl"
LOG = ROOT / "state" / LOG_NAME
HIST_OUT = ROOT / "data/research/program/tme_l_hist_out.txt"
FWD_START = pd.Timestamp("2026-10-01")
SYMS = ["TLT", "TMF", "UBT"]
COST = {"TLT": 2.0, "TMF": 5.0, "UBT": 15.0}         # bp per side
RATE = 0.125                                          # margin, per year, act/360
MAINT = 0.25                                          # Reg T maintenance on a long ETF (assumed; Schwab house may be higher)


def windows(cal: pd.DatetimeIndex) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """(T-3, T) for every month with >= 8 sessions; T = the month's last session."""
    s = pd.Series(cal, index=cal)
    out = []
    for _, g in s.groupby(s.index.to_period("M")):
        if len(g) >= 8:
            out.append((g.index[-4], g.index[-1]))
    return out


def sleeve(r: dict[str, float], days: int) -> dict[str, float]:
    """Per-unit-C window P&L of each rule, net of costs and financing. r = instrument window total returns."""
    c = {k: 2 * COST[k] / 1e4 for k in COST}
    fin = RATE * days / 360
    out = {"L1": r["TLT"] - c["TLT"],
           "L2": 2 * r["TLT"] - 2 * c["TLT"] - fin,
           "L3": r["TMF"] - c["TMF"]}
    if "UBT" in r:
        out["L2r"] = r["UBT"] - c["UBT"]
    return out


def l2_headroom(path: np.ndarray) -> float:
    """Min over the window's closes of (equity - maintenance) / starting equity for 2x TLT on margin.
    Start: equity E = 1 (C = 0.5 E), position 2C = E, debit C = 0.5 E. path = TLT closes / entry close."""
    pos = 1.0 * path
    eq = pos - 0.5
    return float(np.min(eq - MAINT * pos))


# ------------------------------------------------------------------ forward
def _closing_prints(syms, d0, d1) -> dict:
    from .auction_fetch import _env, fetch
    rows = fetch(syms, str(d0.date()), str((d1 + pd.Timedelta(days=1)).date()), _env())
    out = {}
    for s, v in rows.items():
        for x in v:
            if x.get("c"):
                out[(s, pd.Timestamp(x["d"]).normalize())] = float(max(x["c"], key=lambda q: q.get("s", 0))["p"])
    return out


def forward() -> list[dict]:
    from swingtrader.daily import marketdata as md
    bars = md.sip_daily(SYMS, FWD_START - pd.Timedelta(days=10))
    if "TLT" not in bars:
        raise SystemExit("no TLT bars")
    cal = bars["TLT"].index[bars["TLT"].index >= FWD_START]
    done = set()
    if LOG.exists():
        done = {json.loads(l)["T"] for l in LOG.read_text().splitlines() if l.strip()}
    new = []
    for t3, t in windows(cal):
        if str(t.date()) in done or t > cal[-1]:
            continue
        if t == cal[-1] and t.month == (cal[-1] + pd.offsets.BDay(1)).month:
            continue                                              # month not finished yet
        pr = _closing_prints(SYMS, t3, t)
        divs = md.cash_dividends(SYMS, t3.date() + dt.timedelta(days=1), t.date())
        r, miss = {}, []
        for s in SYMS:
            a, b = pr.get((s, t3)), pr.get((s, t))
            if a is None or b is None:
                miss.append(s); continue
            dv = sum(x["rate"] for x in divs if x["sym"] == s)
            r[s] = (b + dv) / a - 1
        if "TLT" not in r or "TMF" not in r:
            new.append({"T": str(t.date()), "status": "missing_prints", "missing": miss}); continue
        days = (t - t3).days
        p = sleeve(r, days)
        seg = bars["TLT"].loc[t3:t]
        on = (bars["TLT"]["open"] / bars["TLT"]["close"].shift(1) - 1).loc[t3:t].iloc[1:]
        on3 = (bars["TMF"]["open"] / bars["TMF"]["close"].shift(1) - 1).loc[t3:t].iloc[1:] if "TMF" in bars else on * np.nan
        row = {"T": str(t.date()), "T3": str(t3.date()), "status": "scored", "days": days,
               "r": {k: round(v, 6) for k, v in r.items()}, "pnl": {k: round(v, 6) for k, v in p.items()},
               "te_TMF_vs_3xTLT_bp": round((r["TMF"] - 3 * r["TLT"]) * 1e4, 1),
               "te_UBT_vs_2xTLT_bp": round((r["UBT"] - 2 * r["TLT"]) * 1e4, 1) if "UBT" in r else None,
               "fin_L2": round(RATE * days / 360, 6),
               "l2_min_headroom": round(l2_headroom((seg["close"] / seg["close"].iloc[0]).to_numpy()), 4),
               "worst_overnight_TLT": round(float(on.min()), 5), "worst_overnight_TMF": round(float(on3.min()), 5),
               "logged": dt.datetime.now().isoformat(timespec="seconds")}
        new.append(row)
    if new:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a") as f:
            for row in new:
                f.write(json.dumps(row) + "\n")
    print(f"forward windows logged: {len(new)} ({LOG})")
    return new


def summary(rows: list[dict]) -> str:
    """Running stats + kill checks for the digest (per unit of C)."""
    s = [r for r in rows if r.get("status") == "scored"]
    if not s:
        return "no forward window scored yet (first: Oct-2026 month-end)"
    out = []
    for k in ("L1", "L2", "L3"):
        x = np.array([r["pnl"][k] for r in s])
        eq = np.cumprod(1 + x)
        dd = float((eq / np.maximum.accumulate(eq) - 1).min())
        kill = dd < -0.30 or x.min() < -0.15
        out.append(f"{k} n {len(x)} mean {x.mean() * 1e4:+.0f}bp worst {x.min() * 100:+.1f}% DD {dd * 100:.1f}%"
                   + (" KILL" if kill else ""))
    te = [r["te_TMF_vs_3xTLT_bp"] for r in s]
    hr = min(r["l2_min_headroom"] for r in s)
    out.append(f"TMF-3xTLT median {np.median(te):+.0f}bp" + (" KILL" if len(te) >= 12 and abs(np.median(te)) > 50 else ""))
    out.append(f"L2 min headroom {hr * 100:.0f}%" + (" KILL" if hr < 0.10 else ""))
    return "; ".join(out)


# ------------------------------------------------------------------ history (report only)
def _yahoo(t: str, start="2009-04-01") -> pd.DataFrame:
    p1 = int(pd.Timestamp(start).timestamp()); p2 = int(pd.Timestamp.now().timestamp())
    u = (f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?period1={p1}&period2={p2}"
         f"&interval=1d&events=div,split")
    j = json.loads(subprocess.run(["curl", "-s", "-A", "Mozilla/5.0", u], capture_output=True, text=True,
                                  check=True).stdout)["chart"]["result"][0]
    q = j["indicators"]["quote"][0]
    df = pd.DataFrame({"open": q["open"], "close": q["close"], "adj": j["indicators"]["adjclose"][0]["adjclose"]},
                      index=pd.to_datetime(j["timestamp"], unit="s", utc=True)
                      .tz_convert("America/New_York").tz_localize(None).normalize())
    return df.dropna(subset=["close"])


def history() -> str:
    px = {s: _yahoo(s) for s in SYMS}
    cal = px["TLT"].index[px["TLT"].index >= "2009-05-01"]
    cal = cal[cal <= "2026-09-30"]
    rows = []
    for t3, t in windows(cal):
        r = {}
        for s in SYMS:
            a = px[s]["adj"]
            if t3 in a.index and t in a.index and a.index[0] <= t3:
                r[s] = a.loc[t] / a.loc[t3] - 1
        if "TLT" not in r or "TMF" not in r:
            continue
        p = sleeve(r, (t - t3).days)
        seg = px["TLT"]["adj"].loc[t3:t]
        on = {s: (px[s]["open"] / px[s]["close"].shift(1) - 1).loc[t3:t].iloc[1:].min() for s in ("TLT", "TMF")}
        rows.append({"T": t, **{f"r_{k}": v for k, v in r.items()}, **p,
                     "te3": r["TMF"] - 3 * r["TLT"], "te2": (r["UBT"] - 2 * r["TLT"]) if "UBT" in r else np.nan,
                     "hr": l2_headroom((seg / seg.iloc[0]).to_numpy()), "on_TLT": on["TLT"], "on_TMF": on["TMF"]})
    H = pd.DataFrame(rows).set_index("T")
    L = [f"TME-L history (REPORT ONLY, instrument measurement; overlaps the TME judge and probe) "
         f"{H.index[0].date()}..{H.index[-1].date()}, {len(H)} windows"]

    def st(x, lab):
        x = x.dropna()
        dn = np.sqrt(np.mean(np.minimum(x, 0) ** 2))
        eq = np.cumprod(1 + x)
        dd = (eq / np.maximum.accumulate(eq) - 1).min()
        return (f"{lab:24s} n {len(x):3d} mean {x.mean() * 1e4:+6.1f}bp  sd {x.std() * 1e4:6.0f}bp  "
                f"downside dev {dn * 1e4:5.0f}bp  worst {x.min() * 100:+6.2f}%  best {x.max() * 100:+6.2f}%  "
                f"maxDD {dd * 100:6.1f}%  mean/downside {x.mean() / dn if dn else np.nan:+.2f}")
    for k, lab in (("L1", "L1 TLT 1x"), ("L2", "L2 TLT 2x margin"), ("L3", "L3 TMF"), ("L2r", "L2r UBT (Roth)")):
        if k in H:
            L.append(st(H[k], lab))
    L.append(f"L2 / L1 mean ratio {H.L2.mean() / H.L1.mean():.2f} (theory ~2 less financing); "
             f"L3 / L1 {H.L3.mean() / H.L1.mean():.2f} (theory ~3)")
    L.append(f"tracking TMF - 3xTLT per window: mean {H.te3.mean() * 1e4:+.1f}bp median {H.te3.median() * 1e4:+.1f}bp "
             f"|median| {H.te3.abs().median() * 1e4:.1f}bp p95 |.| {H.te3.abs().quantile(.95) * 1e4:.0f}bp")
    L.append(f"tracking UBT - 2xTLT per window: mean {H.te2.mean() * 1e4:+.1f}bp |median| {H.te2.abs().median() * 1e4:.1f}bp")
    L.append(f"financing L2 per window: mean {RATE * 4.2 / 360 * 1e4:.1f}bp (~4.2 calendar days)")
    L.append(f"L2 min maintenance headroom over all windows {H.hr.min() * 100:.1f}% of equity (kill < 10%)")
    L.append(f"worst overnight inside a window: TLT {H.on_TLT.min() * 100:+.2f}%  TMF {H.on_TMF.min() * 100:+.2f}%")
    for a, b, lab in (("2013-05", "2013-09", "2013 taper"), ("2020-02", "2020-04", "2020-03"), ("2022-01", "2022-12", "2022")):
        x = H.loc[a:b]
        L.append(f"  {lab:10s} windows {len(x)}: L1 {x.L1.sum() * 100:+.2f}%  L2 {x.L2.sum() * 100:+.2f}%  "
                 f"L3 {x.L3.sum() * 100:+.2f}%  worst L3 window {x.L3.min() * 100:+.2f}%")
    L.append(f"forward kill thresholds vs history: windows with L3 loss > 15% of C: {(H.L3 < -0.15).sum()}, "
             f"L2: {(H.L2 < -0.15).sum()}")
    text = "\n".join(L)
    HIST_OUT.write_text(text + "\n")
    return text


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "forward":
        forward()
    elif cmd == "history":
        print(history())
    else:
        raise SystemExit(__doc__)
