"""Jump hunt stop table (prompt section 8): idea | track | method | death dodged | signals/yr | best select cell | judged?
| verdict | confirm. Rows from jump_ideas.md (all rounds); outcomes from data/research/jump/out/<idea>_explore.txt and the
judge files; "best select cell" = the cell with the highest mean net (its line, shortened).

    PYTHONPATH=. .venv/bin/python -m research.sim.jump_final_table > /tmp/table.md
"""
import re

from .jump_common import ROOT

JUDGED = {"d6": ("J1", "RIDE hold60", "DEAD (+5.5%, ex-top3 -1.8%, P 0.21)"),
          "r2_5": ("J2", "JUMP tp205", "DEAD (x1.3, P 0.18)"),
          "r4_5": ("J3", "RIDE hold20", "DEAD (-1.7%, P 0.71)"),
          "r4_6": ("J4", "JUMP hold20", "DEAD (7 trades)"),
          "r2_25": ("J5", "JUMP tp205", "DEAD (x4.8, +0.8%, ex-top3 -0.1%, P 0.23)"),
          "s5": ("J6", "JUMP trail20", "DEAD (+2.6%, ex-top3 -1.1%, P 0.16)"),
          "r2_19": ("J7", "JUMP tp205", "DEAD (+1.0%, ex-top3 -1.5%, P 0.34)"),
          "r3_15": ("J8", "RIDE hold60", "DEAD (0 trades)")}
CONTROL_FAILED = {"h16", "r3_17", "h9", "v2", "c2"}


def ideas() -> list[tuple[str, list[str]]]:
    out = []
    for line in (ROOT / "research/drafts/jump_ideas.md").read_text().splitlines():
        m = re.match(r"^\| (H\d+|D\d+|C\d+|V\d+|S\d+|W\d+|R\d-\d+) \|", line)
        if m:
            line = line.replace("|return|", "abs return").replace("|5d return|", "abs 5d return")
            out.append((m.group(1), [c.strip() for c in line.strip().strip("|").split("|")]))
    return out


def best(key: str) -> str:
    f = ROOT / f"data/research/jump/out/{key}_explore.txt"
    if not f.exists():
        return ""
    best_line, best_mean = "too few trades", -9.0
    for ln in f.read_text().splitlines():
        m = re.match(r"^(\w+)\s+n\s+(\d+).*?mean net\s+([+-][\d.]+)%\s+ex-top3\s+([+-][\d.]+)%\s+median\s+([+-][\d.]+)%.*?P\(mean<=0\) ([\d.]+)(.*)$", ln)
        if m and float(m.group(3)) > best_mean:
            best_mean = float(m.group(3))
            tag = " MEETS" if "MEETS" in m.group(7) else ""
            best_line = f"{m.group(1)} n{m.group(2)} {m.group(3)}%/{m.group(4)}%/{m.group(5)}% P{m.group(6)}{tag}"
    return best_line


def main():
    print("| idea | track | method | death dodged | signals/yr | best select cell (mean/ex-top3/median) | judged? | verdict | confirm |")
    print("|---|---|---|---|---|---|---|---|---|")
    for iid, c in ideas():
        key = iid.lower().replace("-", "_")
        name = re.sub(r"\*\*", "", c[1])[:70]
        track, tag, death, sig = c[2], c[3], c[5][:60], c[7]
        b = best(key)
        if key in JUDGED:
            j, cell, v = JUDGED[key]
            judged, verdict = f"yes ({j}, {cell})", v
        elif not b:
            judged, verdict = "no", "not explored (data / rarity: see log)"
        elif key in CONTROL_FAILED:
            judged, verdict = "no", "MEETS; failed the same-day control"
        else:
            judged, verdict = "no", "explored-dead"
        print(f"| {iid} {name} | {track} | {tag} | {death} | {sig} | {b} | {judged} | {verdict} | {'not run' if key in JUDGED else ''} |")


if __name__ == "__main__":
    main()
