"""LLM-EARN scorer (runs on the server, where OPENCODE_API_KEY lives). Reads prompts.jsonl, writes one JSON line per
prompt with the model's parsed reply. Resumable; touches nothing but its own output file.

    cd ~/llm-trader && .venv/bin/python /tmp/llm_earn_score.py /tmp/llm_earn_prompts.jsonl /tmp/llm_earn_scores.jsonl
"""
from __future__ import annotations

import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.getcwd())
from swingtrader.daily.news_judge import OpenCodeClient  # noqa: E402

MODEL = "deepseek-v4-flash"


def _env(name):
    for line in open(".env"):
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get(name)


def main(src, dst):
    c = OpenCodeClient(_env("OPENCODE_API_KEY"))
    done = set()
    if os.path.exists(dst):
        done = {(j["key"], j["arm"]) for j in map(json.loads, open(dst))}
    todo = [j for j in map(json.loads, open(src)) if (j["key"], j["arm"]) not in done]
    out = open(dst, "a")

    def one(j):
        rec = {"key": j["key"], "arm": j["arm"]}
        try:
            # non-thinking mode: in thinking mode the hidden reasoning ate any max_tokens cap and returned empty replies
            r = c.chat({"model": MODEL, "temperature": 0, "max_tokens": 400, "thinking": {"type": "disabled"},
                        "messages": [{"role": "user", "content": j["prompt"]}]})
            txt = r["choices"][0]["message"]["content"] or ""
            mm = re.search(r"\{.*\}", txt, re.S)
            rec.update(json.loads(mm.group(0)) if mm else {"error": "noparse", "raw": txt[:200]})
            rec["usage"] = r.get("usage")
        except Exception as ex:  # noqa: BLE001
            rec["error"] = str(ex)[:200]
        return rec

    with ThreadPoolExecutor(8) as ex:
        for i, rec in enumerate(ex.map(one, todo)):
            out.write(json.dumps(rec) + "\n")
            out.flush()
            if i % 200 == 0:
                print(i, len(todo), flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
