"""Trade journal: every round trip (entry/exit reason, the replay fill beside the real one, the plan
it belongs to, a free-text note) and every rule event, as JSON lines per mode."""
from __future__ import annotations

import json
from pathlib import Path

from .settings import STATE


class Journal:
    def __init__(self, mode: str, root: Path = STATE):
        self.mode = mode
        self.dir = Path(root)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.trades_path = self.dir / f"journal-{mode}.jsonl"
        self.events_path = self.dir / f"events-{mode}.jsonl"

    def _append(self, path: Path, row: dict) -> None:
        with path.open("a") as f:
            f.write(json.dumps({**row, "mode": self.mode}, default=str) + "\n")

    def trade(self, row: dict) -> None:
        row = dict(row)
        row.setdefault("plan", f"daytrade/plans/{row.get('strategy', '')}.md")
        for side in ("entry", "exit"):
            real, rep = row.get(f"{side}_px"), row.get(f"replay_{side}_px")
            if real and rep:
                # positive = the real fill was worse than the replay model's
                worse = (real - rep) if (side == "entry") == (row.get("side") == "long") else (rep - real)
                row[f"{side}_drift_bp"] = round(worse / rep * 1e4, 2)
        self._append(self.trades_path, row)

    def event(self, row: dict) -> None:
        self._append(self.events_path, row)

    def note(self, day: str, sym: str, text: str) -> bool:
        """Attach a free-text note to that day's trade in `sym` (rewrites the file)."""
        if not self.trades_path.exists():
            return False
        rows = [json.loads(x) for x in self.trades_path.read_text().splitlines() if x.strip()]
        hit = False
        for r in rows:
            if r.get("day") == day and r.get("sym") == sym:
                r["note"] = (r.get("note", "") + " " + text).strip()
                hit = True
        self.trades_path.write_text("".join(json.dumps(r, default=str) + "\n" for r in rows))
        return hit


def load(path: Path) -> list[dict]:
    p = Path(path)
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []
