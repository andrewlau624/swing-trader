"""CEF-TXT (N 888-889) FinBERT scoring of N-CSR / N-CSRS text.

Runs in an env with torch + transformers (system python3, not the project venv):
    python3 research/sim/cef_txt_score.py      # -> data/research/cef_txt/scores.parquet

Per document: sentences of 8-80 words from the stripped text (first 60k chars), the first 64 are scored with
ProsusAI/finbert; tone = mean(P(neg) - P(pos)). Also writes n_chars and the distribution-cut keyword flag (control C2).
"""
from __future__ import annotations

import gzip
import pathlib
import re

import pandas as pd
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

D = pathlib.Path(__file__).resolve().parents[2] / "data/research/cef_txt"
NAME = "ProsusAI/finbert"
NSENT = 64
_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'(])")
DIST_CUT = re.compile(r"(?is)(?:reduc|decreas|\bcut\b|lower)\w*[^.]{0,60}?distribution"
                      r"|distribution[^.]{0,60}?(?:reduc|decreas|\bcut\b|lower)\w*")


ANCHOR = re.compile(r"(?i)dear (?:fellow )?shareholder|letter to (?:the )?shareholders|shareholder letter|"
                    r"manager.s discussion|portfolio manager|market review|commentary")
BOILER = re.compile(r"(?i)electronic|paper cop|intermediary|form n-csr|commission|fdic|registrant|prospectus|"
                    r"conclusions about|distribution plan|managed distribution|the plan\b|not (?:bank )?guarantee")


def sentences(text: str) -> list[str]:
    """First NSENT non-boilerplate sentences of 8-80 words, starting at the shareholder letter if one is found."""
    text = re.sub(r"\s+", " ", text)
    m = ANCHOR.search(text)
    out = []
    for s in _SPLIT.split(text[m.start():] if m else text):
        if 8 <= len(s.split()) <= 80 and not BOILER.search(s):
            out.append(s)
            if len(out) == NSENT:
                break
    return out


def main():
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(NAME)
    mod = AutoModelForSequenceClassification.from_pretrained(NAME).eval().to(dev)
    lab = {v.lower(): i for i, v in mod.config.id2label.items()}
    fp = D / "scores.parquet"
    rows = pd.read_parquet(fp).to_dict("records") if fp.exists() else []
    done = {r["accession"] for r in rows}
    files = sorted((D / "text").glob("*.txt.gz"))
    for k, f in enumerate(files):
        acc = f.name[:-7]
        if acc in done:
            continue
        txt = gzip.open(f, "rt").read()
        ss = sentences(txt)
        tone, npos, nneg = float("nan"), 0, 0
        if ss:
            with torch.no_grad():
                enc = tok(ss, truncation=True, max_length=128, padding=True, return_tensors="pt").to(dev)
                p = torch.softmax(mod(**enc).logits, dim=-1).cpu()
            d = p[:, lab["negative"]] - p[:, lab["positive"]]
            tone = float(d.mean())
            npos = int((p.argmax(1) == lab["positive"]).sum())
            nneg = int((p.argmax(1) == lab["negative"]).sum())
        rows.append(dict(accession=acc, tone=tone, n_sent=len(ss), n_pos=npos, n_neg=nneg, n_chars=len(txt),
                         dist_cut=bool(DIST_CUT.search(txt))))
        if k % 250 == 0:
            pd.DataFrame(rows).to_parquet(fp)
            print(k, len(files), flush=True)
    pd.DataFrame(rows).to_parquet(fp)
    print("DONE", len(rows), flush=True)


if __name__ == "__main__":
    main()
