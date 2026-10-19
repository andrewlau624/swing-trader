"""Score REV-TONE reviews: roberta sentiment (tone = p(pos) - p(neg)) + keyword reason tags.

Run with system python3 (torch/transformers live there). Output data/research/reviews/scored.parquet.
Cap 1,000 random reviews per firm-month (seed 0), frozen in round1_prose.md.
"""
import re, sys, time
sys.modules["torchvision"] = None  # mismatched torchvision breaks transformers import
from pathlib import Path
import numpy as np, pandas as pd, torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

ROOT = Path(__file__).resolve().parents[3] / "data/research/reviews"
MODEL = "cardiffnlp/twitter-roberta-base-sentiment-latest"
CAP = 1000

TAGS = {
    "fit_size": r"\b(fit|fits|fitting|size|sizing|too (small|big|large|tight|loose)|runs (small|big|large)|narrow|wide)\b",
    "quality": r"\b(quality|cheap(ly)?|flimsy|poorly made|well made|durab\w*|fell apart|falling apart|wore out|thin material)\b",
    "defect": r"\b(broke|broken|defect\w*|stopped working|doesn'?t work|not working|dead on arrival|doa|crack(ed)?|leak\w*|ripped|tore|died)\b",
    "comfort": r"\b(comfort\w*|uncomfortable|blister\w*|hurt(s)?|pain(ful)?|support(ive)?)\b",
    "price_value": r"\b(price|overpriced|expensive|worth|value|money|refund)\b",
    "shipping_pkg": r"\b(shipping|shipped|arrived|delivery|delivered|package|packaging|box)\b",
    "fake": r"\b(fake|counterfeit|knock ?off|not authentic|not genuine|replica)\b",
    "service": r"\b(customer service|warranty|support team|return(ed)? it|replacement)\b",
    "tech": r"\b(battery|charge|charging|bluetooth|wifi|wi-fi|app|connect\w*|firmware|update|pair(ing)?)\b",
}
TAG_RE = {k: re.compile(v, re.I) for k, v in TAGS.items()}


def main():
    df = pd.concat([pd.read_parquet(p) for p in sorted((ROOT / "raw").glob("*.parquet")) if not p.name.endswith("_meta.parquet")])
    df = df.drop_duplicates(["parent_asin", "ts", "title", "text"])
    df["dt"] = pd.to_datetime(df.ts, unit="ms")
    df["ym"] = df.dt.dt.to_period("M")
    n_all = df.groupby(["tk", "ym"]).size().rename("n_all")
    df = (df.sample(frac=1, random_state=0).groupby(["tk", "ym"], group_keys=False).head(CAP)
          .sort_values(["tk", "ts"]).reset_index(drop=True))
    df = df.join(n_all, on=["tk", "ym"])
    print("to score", len(df), flush=True)
    txt = (df.title.fillna("") + ". " + df.text.fillna("")).str.slice(0, 1200).tolist()
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(MODEL)
    mdl = AutoModelForSequenceClassification.from_pretrained(MODEL).to(dev).eval()
    # labels: 0 neg, 1 neu, 2 pos; sort by length so batches pad little
    order = np.argsort([len(t) for t in txt])
    probs = np.zeros((len(txt), 3), np.float32)
    t0, B = time.time(), 128
    with torch.inference_mode():
        for i in range(0, len(order), B):
            idx = order[i:i + B]
            enc = tok([txt[j] for j in idx], truncation=True, max_length=256, padding=True, return_tensors="pt").to(dev)
            probs[idx] = torch.softmax(mdl(**enc).logits.float(), -1).cpu().numpy()
            if i % (B * 200) == 0:
                print(i, round(time.time() - t0), "s", flush=True)
    df["p_neg"], df["p_neu"], df["p_pos"] = probs[:, 0], probs[:, 1], probs[:, 2]
    df["tone"] = df.p_pos - df.p_neg
    low = pd.Series(txt).str.lower()
    for k, rx in TAG_RE.items():
        df["tag_" + k] = low.str.contains(rx).values
    df["ym"] = df.ym.astype(str)
    df.drop(columns=["text"]).to_parquet(ROOT / "scored.parquet")
    print("done", len(df), round(time.time() - t0), "s")


if __name__ == "__main__":
    main()
