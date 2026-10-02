"""Compact log lines from saved explore outputs (data/research/jump/out/<idea>_explore.txt): select size, the 1-day
jump lift, and mean / ex-top3 / median / P for tp205, hold20 and hold60, plus any MEETS.

    PYTHONPATH=. .venv/bin/python -m research.sim.jump_summary idea [idea ...]
"""
import re
import sys

from .jump_common import ROOT


def line(idea: str) -> str:
    t = (ROOT / f"data/research/jump/out/{idea}_explore.txt").read_text()
    sel = re.search(r"\((\d+) events -> (\d+) trades\)", t)
    out = [f"**{idea.upper().replace('_', '-')}** ({sel.group(1)} select -> {sel.group(2)} trades)" if sel else idea]
    for cell in ("hold1", "tp205", "hold20", "hold60", "tp2060"):
        m = re.search(rf"^{cell}\s+n.*?\(x([\d.inf]+)\)\s+mean net\s+([+-][\d.]+%)\s+ex-top3\s+([+-][\d.]+%)\s+median\s+([+-][\d.]+%).*?P\(mean<=0\) ([\d.]+)", t, re.M)
        if m:
            out.append(f"{cell} x{m.group(1)} {m.group(2)}/{m.group(3)}/{m.group(4)} P{m.group(5)}")
    meets = re.findall(r"^(\w+).*(jump MEETS|ride MEETS)", t, re.M)
    out.append("MEETS: " + ", ".join(f"{c} {k}" for c, k in meets) if meets else "all fail")
    return "; ".join(out)


if __name__ == "__main__":
    for i in sys.argv[1:]:
        print("  - " + line(i))
