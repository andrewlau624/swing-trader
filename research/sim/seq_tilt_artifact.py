"""Freeze the SEQ-NIGHT Ridge (N 1038) for the log-only tilt shadow SEQ-TILT-FWD (N 1196).

No new tuning: this is phase_a's Ridge line verbatim (seq_night.night_frame features, fit 1999-2015 rows, label = pick r minus
the night mean clipped +-0.5, X standardised by the TRAIN mean / std with np.mean / np.std -- NOT nan-aware, so any feature
with a NaN anywhere in the training rows standardises to NaN and nan_to_num zeroes it: such features are inert in the research
Ridge and are kept inert here -- then Ridge(alpha=10)). The research never refit on later data (phase_a's only Ridge is the
1999-2015 fit judged on 2016-26), so that fit IS the final fit.

Inputs are rebuilt with the research's own code (outputs of 2026-10-19 were not kept):
  sel_night.py --which primary  -> data/research/program/sel_night_names_primary.parquet
  seq_night.py --phase build    -> seq_feats/, seq_feats_night.parquet, seq_market.parquet
Run:  PYTHONPATH=. uv run --with scikit-learn --with python-dateutil python research/sim/seq_tilt_artifact.py
Out:  swingtrader/daily/seq_tilt_ridge.json (committed) + data/research/program/seq_tilt_artifact_out.txt (repro check)
"""
from __future__ import annotations

import json
import pathlib

import numpy as np

from research.sim import seq_night as sq

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "swingtrader" / "daily" / "seq_tilt_ridge.json"
SECT = ROOT / "swingtrader" / "daily" / "seq_tilt_sectors.json"
TRAIN_END = "2015-12-31"
ALPHA = 10.0
# identical on every pick of a night -> a constant shift of every score that night: no effect on rank, z or tilt
NIGHT_CONST = set(sq.MKT) | {"n_picks"}


def main() -> int:
    from sklearn.linear_model import Ridge
    d, feats = sq.night_frame()
    train, test = d[d.date <= TRAIN_END], d[d.date >= "2016-01-01"]
    X_tr = train[feats].to_numpy(np.float32)
    mu, sd = X_tr.mean(0), X_tr.std(0) + 1e-9          # exactly phase_a (NaN-propagating)
    rg = Ridge(alpha=ALPHA).fit(np.nan_to_num((X_tr - mu) / sd), train.label.to_numpy())
    pred = rg.predict(np.nan_to_num((test[feats].to_numpy(np.float32) - mu) / sd))
    lines, tmb = sq.judge_night(test, pred, "Ridge judge 2016-26 (repro of seq_night_out: +31.6bp t 2.1)")
    lines += sq.night_replays(test, pred)
    active = [bool(np.isfinite(m) and np.isfinite(s)) for m, s in zip(mu, sd)]
    art = dict(
        study="SEQ-TILT-FWD (N 1196) frozen from SEQ-NIGHT (N 1038) Ridge line",
        model="sklearn Ridge(alpha=10) on nan_to_num((x - mu) / sd); score = intercept + sum(coef * z)",
        train_window=[str(train.date.min().date()), str(train.date.max().date())],
        train_rows=int(len(train)), train_nights=int(train.date.nunique()),
        label="pick close->next-open return minus the night mean, clipped +-0.5",
        data="Sharadar SEP split-adjusted OHLCV (closeunadj for log_px), SEL-NIGHT primary universe current-rule kept picks",
        alpha=ALPHA, intercept=float(rg.intercept_),
        features=[dict(name=f, mu=float(m) if a else None, sd=float(s) if a else None, coef=float(c),
                       active=a, night_const=f in NIGHT_CONST)
                  for f, m, s, c, a in zip(feats, mu, sd, rg.coef_, active)],
        repro=dict(judge_2016_26_tmb_bp=round(float(tmb), 2), line=lines[0].strip()),
    )
    OUT.write_text(json.dumps(art, indent=1) + "\n")
    # live sector map: night_frame's source (SEP, latest row per ticker), listed tickers only (a delisted symbol may be reused)
    import pandas as pd
    t = pd.read_parquet(sq.S / "tickers.parquet", columns=["table", "ticker", "sector", "lastupdated", "isdelisted"])
    t = t[t.table == "SEP"].sort_values("lastupdated").drop_duplicates("ticker", keep="last")
    t = t[(t.isdelisted == "N") & t.sector.isin(sq.SECTORS)]
    SECT.write_text(json.dumps({s_: sorted(g.ticker) for s_, g in t.groupby("sector")}, separators=(",", ":")) + "\n")
    txt = "\n".join(lines + [f"features {len(feats)}, active {sum(active)}, active & per-pick "
                              f"{sum(a and f not in NIGHT_CONST for f, a in zip(feats, active))}",
                              "inert (NaN in training): " + ", ".join(f for f, a in zip(feats, active) if not a)]) + "\n"
    (sq.PROG / "seq_tilt_artifact_out.txt").write_text(txt)
    print(txt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
