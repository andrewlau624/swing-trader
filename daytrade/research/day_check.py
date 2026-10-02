"""Post-close check of one recorded session through every lab strategy and the risk layer (plumbing, not P&L):
flat by close, no rule breaks, journal fields complete. Usage: python -m daytrade.research.day_check DIR YYYY-MM-DD
where DIR holds l1/trade_date=<day>/ and meta/<day>.json (a read-only copy of the server's recording)."""
from __future__ import annotations

import datetime as dt
import glob
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import pyarrow as pa
import pyarrow.parquet as pq

from ..engine import Engine
from ..events import DayInfo
from ..feeds import rows_to_events
from ..fills import SimBroker
from ..journal import Journal
from ..session import calendar, session_times
from ..strategies import REGISTRY

BREAKS = ("held at end of data", "order after halt/flat", "late fill after cancel")


def check(root: Path, day: dt.date) -> dict:
    meta = json.loads((root / "meta" / f"{day}.json").read_text())
    st = session_times(day, calendar(day, day))
    rows = pa.concat_tables([pq.read_table(f) for f in sorted(glob.glob(str(root / "l1" / f"trade_date={day}" / "*.parquet")))]).sort_by("ts").to_pylist()
    info = {g["sym"]: DayInfo(g["sym"], float(g["prev_close"]), 50e6, float(g["premarket_volume"]), atr14=1.0,
                              avg_volume14=2e6, or_volume_avg14=1e5) for g in meta.get("gappers", [])}
    out = {"day": str(day), "rows": len(rows), "meta": {k: meta.get(k) for k in ("rows", "flagged", "complete")},
           "gaps": len(meta.get("gaps", [])), "reconnects": len(meta.get("reconnects", [])),
           "last_row_et": str(rows[-1]["ts"].astimezone(ZoneInfo("America/New_York"))) if rows else None, "runs": []}
    for name, cls in REGISTRY.items():
        for eq, kind in ((2300, "cash"), (25000, "margin")):
            jroot = root / "journal" / f"{name}-{kind}"
            jroot.mkdir(parents=True, exist_ok=True)
            for f in jroot.glob("*.jsonl"):
                f.unlink()
            eng = Engine([cls()], SimBroker(latency_s=1, extra_bp=0.5, cost_bp=10), equity=eq, session=st,
                         account_kind=kind, day_info=info, journal=Journal("replay", jroot), halt_path=root / "HALT-never")
            eng.run(rows_to_events(rows, st, clock_every_s=1))
            late = [t for t in eng.trades if dt.datetime.fromisoformat(t["exit_ts"]) > st.flat_by + dt.timedelta(minutes=2)]
            out["runs"].append({"strategy": name, "equity": eq, "kind": kind, "trades": len(eng.trades),
                                "breaks": [e["detail"] for e in eng.events if e["kind"] in BREAKS],
                                "exits_after_flat": len(late), "open_at_end": len(eng.positions),
                                "limits": [e["kind"] for e in eng.events if e["kind"] in ("daily loss limit", "halt")]})
    out["ok"] = all(not r["breaks"] and not r["exits_after_flat"] and not r["open_at_end"] for r in out["runs"])
    return out


if __name__ == "__main__":
    print(json.dumps(check(Path(sys.argv[1]), dt.date.fromisoformat(sys.argv[2])), indent=1, default=str))
