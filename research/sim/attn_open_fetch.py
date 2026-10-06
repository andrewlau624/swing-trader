"""ATTN-OPEN data: official SIP crosses around 2021-2026 de-SPAC and ticker-change dates (new symbol E-10d..E+7d,
old symbol E-10d..E).

    PYTHONPATH=. .venv/bin/python -m research.sim.attn_open_fetch      # resumable

Cached as data/research/exdiv/attn/<arm>_<newticker>_<date>.json = {"new": rows, "old": rows, "old_sym": str}.
"""
from __future__ import annotations

import json
import pathlib
import time

import pandas as pd

from .auction_fetch import _env, fetch

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/exdiv/attn"
STORE = pathlib.Path.home() / "data" / "sharadar"
RX = r"[A-Z]{1,5}"


def events() -> pd.DataFrame:
    a = pd.read_parquet(STORE / "actions.parquet", columns=["date", "action", "ticker", "contraticker"])
    a["date"] = pd.to_datetime(a["date"])
    a = a[a.date >= "2021-01-01"]
    frm = a[a.action == "tickerchangefrom"][["date", "ticker", "contraticker"]].rename(columns={"contraticker": "old"})
    sp = a[a.action == "spacmerger"][["date", "ticker"]].merge(frm, on=["date", "ticker"], how="left").assign(arm="D")
    tc = a[a.action == "tickerchangeto"][["date", "ticker"]].merge(frm, on=["date", "ticker"], how="left").assign(arm="T")
    tc = tc.merge(sp[["date", "ticker"]], on=["date", "ticker"], how="left", indicator=True)
    tc = tc[tc._merge == "left_only"].drop(columns="_merge")
    ev = pd.concat([sp, tc])
    ev = ev[ev.ticker.str.fullmatch(RX) & (ev.old.isna() | ev.old.fillna("").str.fullmatch(RX))]
    return ev.drop_duplicates(["arm", "ticker", "date"])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    H = _env(); ev = events(); t0 = time.time()
    for i, r in enumerate(ev.itertuples()):
        f = OUT / f"{r.arm}_{r.ticker}_{r.date.date()}.json"
        if f.exists():
            continue
        s0, s1 = str((r.date - pd.Timedelta(days=10)).date()), str((r.date + pd.Timedelta(days=7)).date())
        out = {"old_sym": r.old if isinstance(r.old, str) else None}
        for key, sym, end in (("new", r.ticker, s1), ("old", out["old_sym"], str(r.date.date()))):
            if not sym:
                continue
            try:
                out[key] = fetch([sym], s0, end, H).get(sym, [])
            except Exception as e:  # noqa: BLE001
                out[key + "_error"] = str(e)[:200]
        json.dump(out, open(f, "w"))
        if i % 100 == 0:
            print(f"{i}/{len(ev)} {time.time()-t0:.0f}s", flush=True)
    print("done", len(ev), f"{time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
