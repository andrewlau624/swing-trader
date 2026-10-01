"""Study Lab-BF: Lab-BE's opening-cross reversal with the decision at 09:28:30 (near prices exist from 09:28:00),
on 30 names (round1_prose.md Lab Round 30). Reuses be_replay's pricing and trade arithmetic.

  python -m daytrade.research.bf_replay fetch      # probe gate, then pull (guard $9)
  python -m daytrade.research.bf_replay run
"""
from __future__ import annotations

import datetime as dt
import json
import pickle
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor


from ..settings import DATA
from . import as_replay as A
from . import az_replay as Z
from . import be_replay as B

OUT = DATA / "research" / "bf"
BUDGET = 9.0
TOP = 2


def universe():
    u = Z.universe()
    return u[:28] + ["QQQ", "TQQQ"]


def window(o):
    return (o - dt.timedelta(minutes=2)).astimezone(dt.timezone.utc), (o - dt.timedelta(seconds=89)).astimezone(dt.timezone.utc)


def probe(cli, syms, cal):
    """The checklist gate: >= 50% of messages in [09:28:00, 09:28:30] carry a near price, on 5 sample days."""
    for o, _ in [cal[i] for i in (10, 300, 600, 900, 1150)]:
        s, e = window(o)
        df = cli.timeseries.get_range(dataset="XNAS.ITCH", schema="imbalance", symbols=syms[:3], start=s, end=e).to_df()
        df = df[df.auction_type == "O"]
        share = float((df.cont_book_clr_price > 0).mean()) if len(df) else 0.0
        A.log(f"probe {o.date()}: {len(df)} messages, near>0 {share:.0%}")
        assert share >= 0.5, f"probe failed on {o.date()}: near price missing in the decision window"


def fetch():
    import databento as db
    from swingtrader.config import get_env
    syms = universe()
    cal = pickle.loads((Z.OUT / "sessions.pkl").read_bytes())
    cli0 = db.Historical(get_env("DATABENTO_API_KEY"))
    probe(cli0, syms, cal)
    d = OUT / "imbalance"; d.mkdir(parents=True, exist_ok=True)
    sp = OUT / "spent.json"
    lock = threading.Lock()
    st = {"spent": json.loads(sp.read_text())["usd"] if sp.exists() else 0.0, "stop": False}
    todo = [(o, c) for o, c in cal if o.date() <= Z.END and not (d / f"{o.date()}.parquet").exists()]

    def one(oc):
        o, _ = oc
        if st["stop"]:
            return
        s, e = window(o)
        cli = db.Historical(get_env("DATABENTO_API_KEY"))
        for attempt in range(6):
            try:
                cost = cli.metadata.get_cost(dataset="XNAS.ITCH", schema="imbalance", symbols=syms, start=s, end=e)
                with lock:
                    if st["spent"] + cost > BUDGET:
                        st["stop"] = True; A.log(f"STOP at {o.date()}: ${st['spent'] + cost:.2f}"); return
                    st["spent"] += cost
                df = cli.timeseries.get_range(dataset="XNAS.ITCH", schema="imbalance", symbols=syms, start=s, end=e).to_df()
                break
            except Exception as exc:
                A.log(f"{o.date()} retry {attempt}: {type(exc).__name__}"); time.sleep(10 * (attempt + 1))
        else:
            A.log(f"{o.date()} skipped"); return
        if len(df):
            df = df.reset_index()[["ts_event", "symbol", "ref_price", "cont_book_clr_price", "paired_qty",
                                   "total_imbalance_qty", "side", "auction_type"]]
            df = df[(df.auction_type == "O") & (df.cont_book_clr_price > 0)]
        df.to_parquet(d / f"{o.date()}.parquet")
        with lock:
            sp.write_text(json.dumps({"usd": round(st["spent"], 4)}))

    with ThreadPoolExecutor(6) as ex:
        list(ex.map(one, todo))
    A.log(f"imbalance done, spent ${st['spent']:.2f}")


def run():
    # same signal and arithmetic as Lab-BE, at 09:28:30 and top 2
    B.TOP = TOP
    B.OUT = OUT
    orig = B.signals_for
    B.signals_for = lambda df, o: orig(df, o + dt.timedelta(seconds=30))   # B uses o - 2 min -> at or before 09:28:30
    cal = pickle.loads((Z.OUT / "sessions.pkl").read_bytes())
    if not (OUT / "signals.parquet").exists():
        B.prices(cal)
    res_path = OUT / "results.json"
    B.run()
    r = json.loads(res_path.read_text())
    for k in ("Lab-BE1", "Lab-BE2"):
        r[k.replace("BE", "BF")] = r.pop(k)
    res_path.write_text(json.dumps(r, indent=1, default=str))
    print(json.dumps({k: (v.get("verdict"), v.get("gross_bp"), v.get("without_top20"), v.get("placebo_pct"))
                      for k, v in r.items() if isinstance(v, dict) and "verdict" in v}, default=str))


if __name__ == "__main__":
    {"fetch": fetch, "run": run}[sys.argv[1]]()
