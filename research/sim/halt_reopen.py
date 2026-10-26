"""Study HALT-REOPEN (round1_prose.md "## Amendment - Studies HALT-REOPEN", N 1046): buy the LULD reopening cross after a DOWN
halt in $5+/$10M+ names, sell the closing cross. Events: NYSE halt-history API (data/research/halts/luld_events.parquet, built by the
registration-time filter); bars: Alpaca SIP raw 1-min per symbol-day.
usage: PYTHONPATH=. .venv/bin/python -m research.sim.halt_reopen fetch | run
"""
from __future__ import annotations

import os
import re
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from .auction_fetch import _env

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "data/research/halts"
BD = D / "bars"
OUT = ROOT / "data/research/program" / os.environ.get("HALT_OUT", "halt_reopen_out.txt")
SH = Path.home() / "data/sharadar"
EVENTS = D / os.environ.get("HALT_EVENTS", "luld_events.parquet")
DIR_MODE = os.environ.get("HALT_DIR", "trigger")   # trigger (5-min move into the halt) | reopen (reopen print vs pre-halt)
ET = "America/New_York"


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    with OUT.open("a") as f:
        f.write(s + "\n")


def events() -> pd.DataFrame:
    e = pd.read_parquet(EVENTS)
    e["date"] = pd.to_datetime(e.date)
    return e.reset_index(drop=True)


def fetch() -> None:
    BD.mkdir(parents=True, exist_ok=True)
    H = _env()
    e = events()
    todo = [(s, d) for s, d in zip(e.Symbol, e.date) if not (BD / f"{s}_{d.date()}.parquet").exists()]
    print(f"{len(e)} events, {len(todo)} to fetch", flush=True)
    for i, (sym, d) in enumerate(todo):
        day = d.date()
        p = dict(symbols=sym, timeframe="1Min", start=f"{day}T13:00:00Z", end=f"{day + pd.Timedelta(days=1)}T01:00:00Z",
                 feed="sip", adjustment="raw", limit=10000)
        bars, tok = [], None
        ok = True
        while True:
            if tok:
                p["page_token"] = tok
            r = None
            for k in range(5):
                try:
                    r = requests.get("https://data.alpaca.markets/v2/stocks/bars", headers=H, params=p, timeout=60)
                except requests.RequestException as exc:   # transient SSL / connection errors: back off and retry
                    print(f"  {sym} {day}: {type(exc).__name__}, retry {k + 1}", flush=True)
                    time.sleep(5 * (k + 1))
                    r = None
                    continue
                if r.status_code == 429:
                    time.sleep(3 * (k + 1))
                    continue
                break
            if r is None or r.status_code != 200:
                print(f"  {sym} {day}: status {getattr(r, 'status_code', None)} {getattr(r, 'text', '')[:80]}", flush=True)
                ok = False
                break
            j = r.json()
            bars += (j.get("bars") or {}).get(sym, []) or []
            tok = j.get("next_page_token")
            if not tok:
                break
        if not ok:
            continue
        x = pd.DataFrame(bars)
        if x.empty:
            x = pd.DataFrame(columns=["t", "o", "h", "l", "c", "v"])
        x.to_parquet(BD / f"{sym}_{day}.parquet")
        if i % 100 == 0:
            print(f"  {i}/{len(todo)}", flush=True)
        time.sleep(0.25)


def _spy() -> dict:
    out = {}
    for f in sorted((ROOT / "data/research/night/m1").glob("SPY_*.parquet")):
        x = pd.read_parquet(f, columns=["timestamp", "close"])
        t = pd.to_datetime(x.timestamp, utc=True).dt.tz_convert(ET)
        x["date"] = t.dt.normalize().dt.tz_localize(None)
        x["mos"] = (t.dt.hour * 60 + t.dt.minute) - 570
        x = x[(x.mos >= 0) & (x.mos < 390)]
        for d, g in x.groupby("date"):
            v = np.full(390, np.nan)
            v[g.mos.to_numpy()] = g.close.to_numpy(float)
            out[d] = pd.Series(v).ffill().bfill().to_numpy()
    return out


def _nxt(e: pd.DataFrame) -> pd.Series:
    """Sharadar open(d+1)/close(d) per event (split-adjusted series, same basis)."""
    st = pd.read_parquet(SH / "stocks.parquet", columns=["ticker", "date", "open", "close"],
                         filters=[("ticker", "in", sorted(set(e.ticker.dropna())))])
    st["date"] = pd.to_datetime(st.date)
    st = st.sort_values(["ticker", "date"])
    st["nxt"] = st.groupby("ticker").open.shift(-1) / st.close
    m = e[["ticker", "date"]].merge(st[["ticker", "date", "nxt"]], on=["ticker", "date"], how="left")
    return m.nxt


def _to_mos(td: pd.Timedelta) -> int:
    return int(td.total_seconds() // 60) - 570


def build_rows() -> pd.DataFrame:
    e = events()
    e["nxt"] = _nxt(e).to_numpy()
    spy = _spy()
    rows = []
    for r in e.itertuples():
        f = BD / f"{r.Symbol}_{r.date.date()}.parquet"
        if not f.exists():
            continue
        x = pd.read_parquet(f)
        if x.empty:
            continue
        t = pd.to_datetime(x.t, utc=True).dt.tz_convert(ET)
        x["mos"] = (t.dt.hour * 60 + t.dt.minute) - 570
        x = x[(x.mos >= 0) & (x.mos < 390)].sort_values("mos")
        if len(x) < 60:
            continue
        kh = _to_mos(r.ht)                       # halt minute
        kr = _to_mos(r.rt)                       # resume minute
        pre = x[x.mos < kh]
        post = x[x.mos >= kr]
        if post.empty or (pre.empty and kh >= 0):
            continue
        p_halt = float(pre.c.iloc[-1]) if not pre.empty else float(r.pc)   # pre-open halt: prior close
        p5 = pre[pre.mos <= kh - 5]
        p_m5 = float(p5.c.iloc[-1]) if not p5.empty else np.nan
        reopen = float(post.o.iloc[0])
        k_re = int(post.mos.iloc[0])
        gap_re = k_re - kr                       # bars missing after the official resume time
        c5 = post[post.mos <= k_re + 5].c.iloc[-1]
        c30 = post[post.mos <= k_re + 30].c.iloc[-1]
        last = float(x.c.iloc[-1])
        S = spy.get(r.date)
        spy_re = (S[389] / S[min(k_re, 389)] - 1) if S is not None else np.nan
        later = x[(x.mos > k_re) & (x.mos <= k_re + 30)]
        # a re-halt shows as a >= 5-minute hole in the 30 minutes after reopen
        rehalt = bool((np.diff(later.mos.to_numpy()) >= 5).any()) if len(later) > 1 else False
        rows.append(dict(sym=r.Symbol, date=r.date, year=r.date.year, adv=r.adv, pc=r.pc, k_halt=kh, k_resume=kr, k_reopen=k_re,
                         gap_re=gap_re, down=(reopen < p_halt) if DIR_MODE == "reopen" else (p_halt < p_m5 if np.isfinite(p_m5) else (p_halt < r.pc)),
                         pre_ret=(p_halt / r.pc - 1) * 1e4, trig5=(p_halt / p_m5 - 1) * 1e4 if np.isfinite(p_m5) else np.nan,
                         re_vs_halt=(reopen / p_halt - 1) * 1e4, r5=(c5 / reopen - 1) * 1e4, r30=(c30 / reopen - 1) * 1e4,
                         r_close=(last / reopen - 1) * 1e4, r_next=((last / reopen) * r.nxt - 1) * 1e4 if np.isfinite(r.nxt) else np.nan,
                         spy_close=spy_re * 1e4, re_vol_usd=float(post.v.iloc[0]) * reopen, rehalt=rehalt))
    return pd.DataFrame(rows)


def clus_t(y, d):
    y = np.asarray(y, float)
    e = y - y.mean()
    s = pd.Series(e).groupby(np.asarray(d)).sum().to_numpy()
    se = np.sqrt((s * s).sum()) / len(y)
    return y.mean() / se if se > 0 else float("nan")


def stats(y, d) -> str:
    y = np.asarray(y, float)
    y = y[np.isfinite(y)]
    if len(y) < 3:
        return f"n {len(y)}"
    top = np.sort(y)[-5:].sum() if len(y) > 5 else 0.0
    return (f"n {len(y)} mean {y.mean():+.1f} med {np.median(y):+.1f} hit {np.mean(y > 0):.2f} t {clus_t(y, np.asarray(d)[:len(y)] if len(d) == len(y) else d):.2f} "
            f"ex-top5 {(y.sum() - top) / max(len(y) - 5, 1):+.1f}")


def run() -> None:
    if OUT.exists():
        OUT.unlink()
    x = build_rows()
    x.to_parquet(D / OUT.name.replace("_out.txt", "_rows.parquet"))
    log(f"{OUT.stem.upper()} ({EVENTS.name}, dir={DIR_MODE}): {len(x)} scored events of {len(events())} registered; {x.sym.nunique()} symbols; "
        f"{x.date.min().date()}..{x.date.max().date()}; down halts {int(x.down.sum())}, up {int((~x.down).sum())}; "
        f"reopen bar >= 1 min after resume time: {np.mean(x.gap_re >= 1):.2f} (median gap {x.gap_re.median():.0f} min)")
    log(f"trigger move (5 min before the halt): down median {x[x.down].trig5.median():+.0f}bp, up {x[~x.down].trig5.median():+.0f}bp; "
        f"pre-halt vs prev close: down {x[x.down].pre_ret.median():+.0f}, up {x[~x.down].pre_ret.median():+.0f}")
    log(f"reopen print vs pre-halt price: down {x[x.down].re_vs_halt.median():+.0f} (mean {x[x.down].re_vs_halt.mean():+.0f}), "
        f"up {x[~x.down].re_vs_halt.median():+.0f}; re-halt within 30 min: down {x[x.down].rehalt.mean():.2f}, up {x[~x.down].rehalt.mean():.2f}")
    log(f"reopen-bar $volume median: down ${x[x.down].re_vol_usd.median():,.0f}, up ${x[~x.down].re_vol_usd.median():,.0f}")
    for nm, m in (("D: DOWN halt, buy reopen", x.down), ("U: UP halt, (short) reopen", ~x.down)):
        s = x[m]
        sign = 1 if nm.startswith("D") else -1
        log(f"\n=== {nm}: n {len(s)}")
        for lab, col in (("-> +5m", "r5"), ("-> +30m", "r30"), ("-> close", "r_close"), ("-> next open", "r_next")):
            log(f"  {lab:13s} gross {stats(sign * s[col], s.date)}")
        y = sign * s.r_close.to_numpy(float)
        d = s.date.to_numpy()
        log(f"  -> close net 10bp: {stats(y - 10, d)} | net 25bp mean {y.mean() - 25:+.1f} | SPY-adj mean {(y - sign * s.spy_close).mean():+.1f}")
        for nm2, mm in (("2019-20", s.year <= 2020), ("2021-26", s.year >= 2021), ("ex-2020", s.year != 2020),
                        ("ADV>=50M", s.adv >= 5e7), ("no re-halt", ~s.rehalt), ("re-halt", s.rehalt)):
            log(f"    {nm2:10s} net10 {stats(sign * s[mm].r_close - 10, s[mm].date)}")
        log("    by year net10: " + ", ".join(f"{yy} {sign * g.r_close.mean() - 10:+.0f}/{len(g)}" for yy, g in s.groupby('year')))
        if nm.startswith("D"):
            net = y - 10
            ok = dict(mean=net.mean() >= 30, t=clus_t(net, d) >= 2, median=np.median(net) > 0, hit=np.mean(net > 0) >= 0.5,
                      h1=net[(s.year <= 2020).to_numpy()].mean() > 0, h2=net[(s.year >= 2021).to_numpy()].mean() > 0,
                      extop5=(net.sum() - np.sort(net)[-5:].sum()) / max(len(net) - 5, 1) > 0,
                      spyadj=(y - s.spy_close.to_numpy(float)).mean() >= 20, not_2020_only=net[(s.year != 2020).to_numpy()].mean() > 0)
            log(f"  GATES {ok} -> {'PASS' if all(ok.values()) else 'KILL'}")
    log("\nDisclosed: reopen = open of the first SIP minute bar at/after the resume time (not the cross print itself); "
        "direction from the 5-minute move into the halt; events = first LULD halt of the symbol-day only.")


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    {"fetch": fetch, "run": run}[cmd]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
