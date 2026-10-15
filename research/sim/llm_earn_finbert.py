"""LLM-EARN FINBERT arm (N 887): ProsusAI/finbert sentiment on the same pre-open news text as the LLM prompts.

Runs in a separate env with torch + transformers (not the project venv):
    <hfenv>/bin/python research/sim/llm_earn_finbert.py     # -> data/research/llm_earn/finbert.jsonl

Writes one line per news prompt: key, p_pos, p_neg, p_neu (news text truncated to the model's 512 tokens, from the start).
"""
from __future__ import annotations

import glob
import json
import pathlib

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

D = pathlib.Path(__file__).resolve().parents[2] / "data/research/llm_earn"
NAME = "ProsusAI/finbert"


def main():
    tok = AutoTokenizer.from_pretrained(NAME)
    mod = AutoModelForSequenceClassification.from_pretrained(NAME).eval()
    lab = {i: v.lower() for i, v in mod.config.id2label.items()}
    rows = []
    for f in sorted(glob.glob(str(D / "prompts_*.jsonl"))):
        for j in map(json.loads, open(f)):
            if j["arm"] != "news":
                continue
            txt = j["prompt"].split("News published before the open:", 1)[-1].rsplit("Predict (1)", 1)[0].strip()
            rows.append((j["key"], txt))
    out = open(D / "finbert.jsonl", "w")
    with torch.no_grad():
        for i in range(0, len(rows), 32):
            b = rows[i:i + 32]
            enc = tok([t for _, t in b], truncation=True, max_length=512, padding=True, return_tensors="pt")
            p = torch.softmax(mod(**enc).logits, dim=-1).numpy()
            for (k, _), q in zip(b, p):
                d = {lab[n]: float(q[n]) for n in range(len(q))}
                out.write(json.dumps({"key": k, "p_pos": d["positive"], "p_neg": d["negative"], "p_neu": d["neutral"]}) + "\n")
            if i % 640 == 0:
                print(i, len(rows), flush=True)
    print("DONE", len(rows), flush=True)


if __name__ == "__main__":
    main()
