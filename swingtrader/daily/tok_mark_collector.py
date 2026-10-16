"""TOK-GAP forward mark collector (TOK-GAP DATA-BLOCKED 2026-10-16; LOG-ONLY, no orders).

Appends the last ~3 days of Gate 5m candles for the four tokenized US-stock certificates
(MSTRX/NVDAX/AAPLX/TSLAX_USDT) to data/research/tok/{pair}_5m.parquet, once per run, and logs a
coverage row to state/tok-mark.jsonl. Purpose: build a forward token-mark sample (registered in
research/sim/tok_gap.py + round1_prose.md Study TOK-GAP) because no free API serves history back
to 2025-06. Judge (the one look) only when the minimum-n guard passes (>= 60 qualified days per
half per judged token, judge tokens NVDAX/AAPLX/MSTRX, placebo TSLAX).

No prices, no orders, no signals: free public venue candles only.
"""
from __future__ import annotations

import datetime as dt
import json
import urllib.request
from pathlib import Path

PAIRS = ("MSTRX_USDT", "NVDAX_USDT", "AAPLX_USDT", "TSLAX_USDT")
LOG_NAME = "tok-mark.jsonl"
STEP = 86400 * 3               # 864 candles of 5m per call, under the 1000-point cap
SLEEP = 0.15
ROOT = Path(__file__).resolve().parents[2]


def _fetch(pair: str, frm: int, to: int) -> list:
    u = (f"https://api.gateio.ws/api/v4/spot/candlesticks"
         f"?currency_pair={pair}&interval=5m&from={frm}&to={to}")
    for i in range(3):
        try:
            with urllib.request.urlopen(u, timeout=25) as r:
                return json.load(r)
        except Exception:
            import time
            time.sleep(2 + 2 * i)
    return []


def _collect(pair: str, now: int) -> dict:
    import pandas as pd
    out = Path(ROOT, "data", "research", "tok")
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{pair}_5m.parquet"
    rows: list = []
    t = now - STEP + 300
    while t < now:
        rows.extend(_fetch(pair, t, min(t + STEP, now)))
        t += STEP
        import time
        time.sleep(SLEEP)
    if not rows:
        have = pd.read_parquet(path) if path.exists() else pd.DataFrame()
        return dict(pairs={pair: int(len(have))})
    df = pd.DataFrame(rows, columns=["ts", "qv", "open", "high", "low", "close", "vol", "done"])
    for c in df.columns:
        df[c] = df[c].astype(str).eq("true") if c == "done" else pd.to_numeric(df[c])
    df = df.drop_duplicates("ts").sort_values("ts")
    df["dt"] = pd.to_datetime(df["ts"], unit="s", utc=True)
    if path.exists():
        old = pd.read_parquet(path)
        df = (pd.concat([old, df[old.columns]], ignore_index=True)
              .drop_duplicates("ts").sort_values("ts"))
    df.to_parquet(path)
    return dict(pairs={pair: int(len(df))})


def run(state_dir: Path, logs_dir: Path) -> dict:
    import pandas as pd
    now = int(dt.datetime.now(dt.timezone.utc).timestamp())
    pairs = {}
    for p in PAIRS:
        try:
            pairs.update(_collect(p, now)["pairs"])
        except Exception as e:
            pairs.update({p: -1})
            print(f"[tok-mark] {p} failed: {e!r}", flush=True)
    first = None
    path = Path(ROOT, "data", "research", "tok", "TSLAX_USDT_5m.parquet")
    if path.exists():
        first = str(pd.read_parquet(path, columns=["dt"])["dt"].min())
    row = dict(date=dt.date.today().isoformat(), rows_cached=pairs, sample_since=first, utc=now)
    state_dir.mkdir(parents=True, exist_ok=True)
    with (state_dir / LOG_NAME).open("a") as f:
        f.write(json.dumps(row) + "\n")
    print("[tok-mark] " + line(), flush=True)
    return row


def qualified_dates(pair: str) -> int:
    """Distinct ET dates with >= 8 zero-volume-excluded candles anywhere in the day (printed marks)."""
    import pandas as pd
    path = Path(ROOT, "data", "research", "tok", f"{pair}_5m.parquet")
    if not path.exists():
        return 0
    df = pd.read_parquet(path)
    df["et"] = pd.to_datetime(df["dt"], utc=True).dt.tz_convert("America/New_York")
    df = df[df["vol"] > 0]
    cnt = df.groupby(df["et"].dt.date).size()
    return int((cnt >= 8).sum())


def line() -> str:
    m = {p: qualified_dates(p) for p in PAIRS}
    return ("days with >=8 printed candles: "
            + " ".join(f"{p.split('_')[0]}={m[p]}" for p in PAIRS)
            + "; judge needs >= 60 qualified days per half (prose TOK-GAP guard)")


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    run(root / "state", root / "logs")
