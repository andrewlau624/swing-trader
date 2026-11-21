"""FT round: Kronos-small on the night leg's within-night ranking. FT-ZS (N 1232, zero-shot) and FT-NIGHT (N 1233, fine-tuned).

Pre-registration: research/drafts/round1_prose.md, "## Amendment - FT round: fine-tune an existing open model on the night
leg" (N 1231 -> 1233). Frozen before any outcome was read; program N 1233.

Frame (as registered)
  picks   data/research/program/sel_night_names_primary.parquet rule=='current' (date t, ticker, r = close->open).
  input   the last 64 daily bars through t's close (Sharadar ~/data/sharadar/stocks.parquet, split-adjusted OHLCV; the live
          version would use t's 15:40 bar: the ~20-minute look-ahead on t's last bar is stated, not fixed).
  output  KronosPredictor.predict_batch, pred_len 1, sample_count 10, the repo defaults T 1.0 / top_k 0 / top_p 0.9,
          max_context 512, clip 5; y timestamp = next business day (the repo's daily example, pd.bdate_range).
          f = forecast open / t close - 1.
  tilt    w = clip(1 + 0.5 z(f), 0.5, 1.5), z within the night (numpy std, z = 0 if std 0 or no forecast), w / mean(w);
          increment = sum (w - 1) r / n per night; nights with one pick contribute 0.
  judge   picks dated 2025-09-01..2026-09-30; halves 2025-09..2026-02 / 2026-03..2026-09. Gate (Study BA): both halves > 0,
          NW t (lags 5, news_judge_eval.nw_t) >= 2, sign-flip and within-night shuffle (1000 each, seed 23) >= 95th pct.
          Also: 2023-01..2024-12 (FT-NIGHT's stopping set; FT-ZS possibly contaminated: pretraining data to 2024-06).
  FT      the repo's finetune/train_predictor.py recipe on Kronos-small, tokenizer frozen: AdamW lr 4e-5 betas (.9,.95) wd .1,
          OneCycleLR pct_start .03 div_factor 10, grad clip 3.0, batch 50, epoch = 2000 batches drawn with replacement, val =
          400 x 50 fixed windows, next-token CE over the whole window ((s1+s2)/2, no teacher forcing, as the repo), window
          normalised on its lookback only; best-val checkpoint kept. Windows: 64 bars ending at an event day + the next bar
          (the target), events = day return <= -5% (split-adjusted close), unadjusted close >= $5, 20d mean dollar volume
          (through t) >= $10M, nx.is_common on SEP tickers; train 2003-01..2022-12 (subsampled), stop 2023-01..2024-12;
          the target bar of the last train window is <= 2023-01 and no window touches 2025+.

Run (phases cache under data/research/exp_kronos/cache):
    PYTHONPATH=. python3 research/sim/exp_kronos.py build|zs|train|ft|report|all
    PYTHONPATH=. python3 research/sim/exp_kronos.py timing
"""
from __future__ import annotations

import importlib.util
import json
import math
import pathlib
import sys
import time
import types

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import torch

from research.sim.news_judge_eval import nw_t
from research.sim.nx import is_common

ROOT = pathlib.Path(__file__).resolve().parents[2]
KD = ROOT / "data/research/exp_kronos"
REPO, HF, CACHE = KD / "repo", KD / "hf", KD / "cache"
SH = pathlib.Path.home() / "data/sharadar"
PICKS = ROOT / "data/research/program/sel_night_names_primary.parquet"
OUT = ROOT / "research/sim/exp_kronos_out.txt"

LOOK, CLIP, SAMPLES, TEMP, TOP_K, TOP_P, MAXCTX = 64, 5.0, 10, 1.0, 0, 0.9, 512
FIT = ("2003-01-01", "2022-12-31")
VAL = ("2023-01-01", "2024-12-31")
JUDGE = ("2025-09-01", "2026-09-30")
H1, H2 = ("2025-09-01", "2026-02-28"), ("2026-03-01", "2026-09-30")
MAX_TRAIN, N_VAL = 150_000, 20_000
BS, LR, BETAS, WD, GCLIP, STEPS_PER_EPOCH = 50, 4e-5, (0.9, 0.95), 0.1, 3.0, 2000
EPOCHS = 5             # repo default 30; cut to 5 so the OneCycle schedule completes inside the ~3h budget (MPS 0.47 s/step)
TRAIN_BUDGET_S = 95 * 60
PATIENCE = 2           # early stop: no val improvement in 2 consecutive epochs
import os
DEV = os.environ.get("KRONOS_DEV") or ("mps" if torch.backends.mps.is_available() else "cpu")
FEATS = ["open", "high", "low", "close", "volume", "amount"]


# ----------------------------------------------------------------------------- untrusted repo: import by path
def kronos_mod():
    if "model.kronos" in sys.modules:
        return sys.modules["model.kronos"]
    pkg = types.ModuleType("model"); pkg.__path__ = []; sys.modules["model"] = pkg
    for name in ("module", "kronos"):
        spec = importlib.util.spec_from_file_location(f"model.{name}", REPO / "model" / f"{name}.py")
        m = importlib.util.module_from_spec(spec); sys.modules[f"model.{name}"] = m; spec.loader.exec_module(m)
        setattr(pkg, name, m)
    return sys.modules["model.kronos"]


def load_models(predictor_state: pathlib.Path | None = None):
    from safetensors.torch import load_file
    K = kronos_mod()
    tok = K.KronosTokenizer(**json.loads((HF / "Kronos-Tokenizer-base/config.json").read_text()))
    tok.load_state_dict(load_file(str(HF / "Kronos-Tokenizer-base/model.safetensors")))
    mdl = K.Kronos(**json.loads((HF / "Kronos-small/config.json").read_text()))
    mdl.load_state_dict(load_file(str(HF / "Kronos-small/model.safetensors")))
    if predictor_state is not None:
        mdl.load_state_dict(torch.load(predictor_state, map_location="cpu", weights_only=True))
    return K, tok.eval(), mdl.eval()


# ----------------------------------------------------------------------------- bars
def load_bars() -> pd.DataFrame:
    t = pd.read_parquet(SH / "tickers.parquet", columns=["table", "ticker", "category"])
    t = t[(t.table == "SEP") & is_common(t.category.fillna(""))]
    cols = ["ticker", "date", "open", "high", "low", "close", "volume", "closeunadj"]
    tab = pq.read_table(SH / "stocks.parquet", columns=cols,
                        filters=[("ticker", "in", sorted(t.ticker.unique())), ("date", ">=", pd.Timestamp("2002-06-01").date())])
    df = tab.to_pandas()
    df["date"] = pd.to_datetime(df.date)
    df = df.drop_duplicates(["ticker", "date"]).sort_values(["ticker", "date"], kind="stable").reset_index(drop=True)
    df["amount"] = df.volume * df[["open", "high", "low", "close"]].mean(axis=1)   # predictor's amount rule
    return df


def bar_frame(df: pd.DataFrame):
    tk = df.ticker.to_numpy()
    start = np.r_[True, tk[1:] != tk[:-1]]
    gid = np.cumsum(start) - 1
    first = np.flatnonzero(start)
    pos = np.arange(len(df)) - first[gid]
    glen = np.diff(np.r_[first, len(df)])[gid]
    X = df[FEATS].to_numpy(np.float64)
    bad = ~np.isfinite(X).all(1)
    # windows containing a bad row: prefix count
    cb = np.r_[0, np.cumsum(bad)]
    return dict(gid=gid, pos=pos, glen=glen, X=X, cb=cb, dates=df.date.to_numpy())


def stamps(d: np.ndarray) -> np.ndarray:
    d = pd.DatetimeIndex(d)
    return np.stack([d.minute, d.hour, d.weekday, d.day, d.month], -1).astype(np.float32)


def windows(B: dict, idx: np.ndarray, with_target: bool):
    """idx = row of day t. Returns normalised x (n, 64[+1], 6), stamps, and the raw close at t, mean/std."""
    L = LOOK + (1 if with_target else 0)
    rows = idx[:, None] + np.arange(-LOOK + 1, -LOOK + 1 + L)[None, :]
    x = B["X"][rows]
    mu = x[:, :LOOK].mean(1, keepdims=True); sd = x[:, :LOOK].std(1, keepdims=True)
    xn = np.clip((x - mu) / (sd + 1e-5), -CLIP, CLIP).astype(np.float32)
    return xn, stamps(B["dates"][rows].ravel()).reshape(len(idx), L, 5)


# ----------------------------------------------------------------------------- phase: build
def build() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    df = load_bars()
    B = bar_frame(df)
    c, cu = df.close.to_numpy(), df.closeunadj.to_numpy()
    ret = np.full(len(df), np.nan); ok = B["pos"] >= 1
    ret[ok] = c[ok] / c[np.flatnonzero(ok) - 1] - 1
    dv = pd.Series(df.close.to_numpy() * df.volume.to_numpy())
    adv = dv.groupby(B["gid"]).transform(lambda s: s.rolling(20, min_periods=20).mean()).to_numpy()
    i = np.arange(len(df))
    have = (B["pos"] >= LOOK - 1) & (B["pos"] + 1 < B["glen"])
    have &= (B["cb"][np.minimum(i + 2, len(df))] - B["cb"][np.maximum(i - LOOK + 1, 0)]) == 0
    ev = have & (ret <= -0.05) & (cu >= 5) & (adv >= 1e7)
    d = B["dates"]
    nxt = d[np.minimum(i + 1, len(df) - 1)]
    tr = ev & (d >= np.datetime64(FIT[0])) & (d <= np.datetime64(FIT[1]))
    va = ev & (d >= np.datetime64(VAL[0])) & (d <= np.datetime64(VAL[1])) & (nxt <= np.datetime64(VAL[1]))
    tr_all, va_all = np.flatnonzero(tr), np.flatnonzero(va)
    rng = np.random.default_rng(1233)
    tr_idx = np.sort(rng.choice(tr_all, min(MAX_TRAIN, len(tr_all)), replace=False))
    va_idx = np.sort(rng.choice(va_all, min(N_VAL, len(va_all)), replace=False))
    meta = dict(train_events=int(len(tr_all)), train_used=int(len(tr_idx)), val_events=int(len(va_all)),
                val_used=int(len(va_idx)), last_train_target=str(pd.Timestamp(nxt[tr_idx].max()).date()),
                bars=int(len(df)))
    # tokenise once with the frozen tokenizer (identical to the repo's on-the-fly no_grad encode)
    _, tok, _ = load_models(); tok = tok.to(DEV)
    for name, idx in (("train", tr_idx), ("val", va_idx)):
        s0, s1, st = [], [], []
        for a in range(0, len(idx), 2000):
            xn, xs = windows(B, idx[a:a + 2000], True)
            with torch.no_grad():
                z0, z1 = tok.encode(torch.from_numpy(xn).to(DEV), half=True)
            s0.append(z0.cpu().numpy().astype(np.int16)); s1.append(z1.cpu().numpy().astype(np.int16)); st.append(xs.astype(np.int8))
        np.savez(CACHE / f"tok_{name}.npz", s0=np.concatenate(s0), s1=np.concatenate(s1), st=np.concatenate(st))
    # picks: index of day t's row
    pk = pd.read_parquet(PICKS)
    pk = pk[pk.rule == "current"][["date", "ticker", "r"]].copy()
    pk["date"] = pd.to_datetime(pk.date)
    pk = pk[((pk.date >= VAL[0]) & (pk.date <= VAL[1])) | ((pk.date >= JUDGE[0]) & (pk.date <= JUDGE[1]))].reset_index(drop=True)
    key = pd.DataFrame({"ticker": df.ticker.to_numpy(), "date": d, "row": i})
    pk = pk.merge(key, on=["ticker", "date"], how="left")
    rw = pk.row.fillna(-1).astype(int).to_numpy()
    okp = (rw >= 0)
    okp[okp] &= (B["pos"][rw[okp]] >= LOOK - 1)
    okp[okp] &= (B["cb"][rw[okp] + 1] - B["cb"][rw[okp] - LOOK + 1]) == 0
    pk["row"] = np.where(okp, rw, -1)
    pk.to_parquet(CACHE / "picks.parquet")
    meta.update(picks=int(len(pk)), picks_no_window=int((~okp).sum()))
    (CACHE / "meta.json").write_text(json.dumps(meta, indent=1))
    print(meta, f"{time.time()-t0:.0f}s")


# ----------------------------------------------------------------------------- phase: forecast
def forecast(tag: str, state: pathlib.Path | None) -> None:
    K, tok, mdl = load_models(state)
    pred = K.KronosPredictor(mdl, tok, device=DEV, max_context=MAXCTX, clip=CLIP)
    pk = pd.read_parquet(CACHE / "picks.parquet")
    df = load_bars()
    X, dates = df[["open", "high", "low", "close", "volume"]], df.date
    f = np.full(len(pk), np.nan)
    rows = pk.row.to_numpy()
    todo = np.flatnonzero(rows >= 0)
    torch.manual_seed(1232); np.random.seed(1232)
    t0 = time.time()
    for a in range(0, len(todo), 128):
        ii = todo[a:a + 128]
        dfs, xts, yts = [], [], []
        for j in ii:
            r = rows[j]
            dfs.append(X.iloc[r - LOOK + 1:r + 1].reset_index(drop=True))
            xts.append(dates.iloc[r - LOOK + 1:r + 1].reset_index(drop=True))
            yts.append(pd.Series(pd.bdate_range(start=dates.iloc[r] + pd.Timedelta(days=1), periods=1)))
        out = pred.predict_batch(dfs, xts, yts, pred_len=1, T=TEMP, top_k=TOP_K, top_p=TOP_P, sample_count=SAMPLES, verbose=False)
        for j, o, d_ in zip(ii, out, dfs):
            f[j] = o["open"].iloc[0] / d_["close"].iloc[-1] - 1
    pk[f"f_{tag}"] = f
    pk[["date", "ticker", f"f_{tag}"]].to_parquet(CACHE / f"f_{tag}.parquet")
    print(tag, f"{len(todo)} forecasts {time.time()-t0:.0f}s")


# ----------------------------------------------------------------------------- phase: fine-tune
def train(max_epochs: int = EPOCHS, budget_s: float = TRAIN_BUDGET_S, steps_per_epoch: int = STEPS_PER_EPOCH) -> dict:
    torch.manual_seed(100); np.random.seed(100)   # repo seed
    _, _, mdl = load_models()
    mdl = mdl.to(DEV)
    T = {k: np.load(CACHE / f"tok_{k}.npz") for k in ("train", "val")}
    tr = [torch.from_numpy(T["train"][k].astype(np.int64)) for k in ("s0", "s1", "st")]
    va = [torch.from_numpy(T["val"][k].astype(np.int64)) for k in ("s0", "s1", "st")]
    opt = torch.optim.AdamW(mdl.parameters(), lr=LR, betas=BETAS, weight_decay=WD)
    sch = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=LR, steps_per_epoch=steps_per_epoch, epochs=max_epochs,
                                              pct_start=0.03, div_factor=10)

    def step_loss(b0, b1, bs):
        b0, b1, bs = b0.to(DEV), b1.to(DEV), bs.to(DEV).float()
        lg = mdl(b0[:, :-1], b1[:, :-1], bs[:, :-1, :])
        return mdl.head.compute_loss(lg[0], lg[1], b0[:, 1:], b1[:, 1:])[0]

    def val_loss():
        mdl.eval(); torch.manual_seed(0); tot = 0.0; n = 0
        with torch.no_grad():
            for a in range(0, len(va[0]), BS):
                tot += step_loss(*(v[a:a + BS] for v in va)).item(); n += 1
        return tot / n

    rng = np.random.default_rng(100)
    hist = {"epoch0_val": val_loss(), "epochs": []}
    print(f"epoch 0 val {hist['epoch0_val']:.4f}", flush=True)
    best, bad, t0 = math.inf, 0, time.time()
    for ep in range(max_epochs):
        mdl.train(); te = time.time(); tl = []
        for s in range(steps_per_epoch):
            j = torch.from_numpy(rng.integers(0, len(tr[0]), BS))
            loss = step_loss(tr[0][j], tr[1][j], tr[2][j])
            opt.zero_grad(); loss.backward()
            torch.nn.utils.clip_grad_norm_(mdl.parameters(), max_norm=GCLIP)
            opt.step(); sch.step(); tl.append(loss.item())
        v = val_loss()
        hist["epochs"].append(dict(epoch=ep + 1, train=float(np.mean(tl)), val=v, sec=time.time() - te))
        print(f"epoch {ep+1} train {np.mean(tl):.4f} val {v:.4f} {time.time()-te:.0f}s", flush=True)
        if v < best:
            best, bad = v, 0
            torch.save(mdl.state_dict(), CACHE / "ft_best.pt"); hist["best_epoch"] = ep + 1
        else:
            bad += 1
        el = time.time() - t0
        if bad >= PATIENCE:
            hist["stop"] = f"early stop (val no better for {PATIENCE} epochs)"; break
        if el + el / (ep + 1) > budget_s:
            hist["stop"] = f"time budget ({budget_s/60:.0f} min) after epoch {ep+1} of {max_epochs}"; break
    else:
        hist["stop"] = "max epochs"
    hist["best_val"] = best
    (CACHE / "ft_hist.json").write_text(json.dumps(hist, indent=1))
    return hist


def timing() -> None:
    _, _, mdl = load_models(); mdl = mdl.to(DEV).train()
    opt = torch.optim.AdamW(mdl.parameters(), lr=LR)
    b0 = torch.randint(0, 1024, (BS, LOOK + 1)); b1 = torch.randint(0, 1024, (BS, LOOK + 1))
    st = torch.tensor(stamps(pd.bdate_range("2020-01-01", periods=LOOK + 1).to_numpy())).unsqueeze(0).repeat(BS, 1, 1)
    for k in range(25):
        if k == 5:
            if DEV == "mps": torch.mps.synchronize()
            t0 = time.time()
        lg = mdl(b0[:, :-1].to(DEV), b1[:, :-1].to(DEV), st[:, :-1].to(DEV))
        loss = mdl.head.compute_loss(lg[0], lg[1], b0[:, 1:].to(DEV), b1[:, 1:].to(DEV))[0]
        opt.zero_grad(); loss.backward(); opt.step()
    if DEV == "mps": torch.mps.synchronize()
    print(f"{DEV}: {(time.time()-t0)/20*1000:.0f} ms/step -> epoch of {STEPS_PER_EPOCH} = {(time.time()-t0)/20*STEPS_PER_EPOCH/60:.1f} min")


# ----------------------------------------------------------------------------- phase: report
def tilt_inc(f: np.ndarray, r: np.ndarray, g: np.ndarray, G: int) -> np.ndarray:
    v = np.isfinite(f); fv = np.where(v, f, 0.0)
    cnt = np.bincount(g, v, G); n = np.bincount(g, minlength=G).astype(float)
    m = np.bincount(g, fv, G) / np.maximum(cnt, 1)
    var = np.bincount(g, np.where(v, (fv - m[g]) ** 2, 0.0), G) / np.maximum(cnt, 1)
    sd = np.sqrt(var)
    z = np.where(v & (sd[g] > 0), (fv - m[g]) / np.where(sd[g] > 0, sd[g], 1), 0.0)
    w = np.clip(1 + 0.5 * z, 0.5, 1.5)
    w = w / (np.bincount(g, w, G) / n)[g]
    return np.bincount(g, (w - 1) * r, G) / n


def block(P: pd.DataFrame, fcol: str, lo: str, hi: str, h1, h2, label: str) -> tuple[list[str], bool]:
    d = P[(P.date >= lo) & (P.date <= hi)].sort_values("date").reset_index(drop=True)
    nights = d.date.unique(); g = pd.factorize(d.date)[0]; G = len(nights)
    f, r = d[fcol].to_numpy(), d.r.to_numpy()
    inc = tilt_inc(f, r, g, G) * 1e4
    nd = pd.DatetimeIndex(nights)
    a = inc[(nd >= h1[0]) & (nd <= h1[1])]; b = inc[(nd >= h2[0]) & (nd <= h2[1])]
    t = nw_t(inc)
    rng = np.random.default_rng(23)
    flip = np.array([(inc * rng.choice([-1, 1], G)).mean() for _ in range(1000)])
    order = np.argsort(g, kind="stable"); bounds = np.r_[0, np.cumsum(np.bincount(g, minlength=G))]
    shuf = []
    for _ in range(1000):
        fs = f.copy()
        for k in range(G):
            sl = order[bounds[k]:bounds[k + 1]]
            if len(sl) > 1:
                fs[sl] = f[rng.permutation(sl)]
        shuf.append(tilt_inc(fs, r, g, G).mean() * 1e4)
    p1 = (flip < inc.mean()).mean() * 100; p2 = (np.array(shuf) < inc.mean()).mean() * 100
    ics = []
    for k in range(G):
        sl = order[bounds[k]:bounds[k + 1]]
        x, y = f[sl], r[sl]; m = np.isfinite(x)
        if m.sum() >= 3 and np.unique(x[m]).size > 1:
            ics.append(pd.Series(x[m]).rank().corr(pd.Series(y[m]).rank()))
    ics = np.array(ics)
    vm = np.isfinite(f) & (r != 0) & (f != 0)
    hit = (np.sign(f[vm]) == np.sign(r[vm])).mean() * 100
    ok = a.mean() > 0 and b.mean() > 0 and t >= 2 and p1 >= 95 and p2 >= 95
    L = [f"  {label}: picks {len(d)} (forecast {np.isfinite(f).sum()}), nights {G} (>=2 picks {(np.bincount(g) >= 2).sum()})",
         f"    increment {inc.mean():+.2f} bp/night, NW t {t:+.2f}; halves {a.mean():+.2f} ({len(a)} nights) / {b.mean():+.2f} ({len(b)} nights)",
         f"    sign-flip {p1:.0f}th pct, within-night shuffle {p2:.0f}th pct (shuffle mean {np.mean(shuf):+.2f}, 95th {np.percentile(shuf, 95):+.2f})",
         f"    rank IC f vs r (nights with >=3 forecasts, n {len(ics)}): mean {ics.mean():+.4f}, t {ics.mean()/(ics.std(ddof=1)/np.sqrt(len(ics))):+.2f}",
         f"    direction hit {hit:.1f}% on {vm.sum()} picks (share r>0 {(r[vm] > 0).mean()*100:.1f}%, share f>0 {(f[vm] > 0).mean()*100:.1f}%); "
         f"f mean {np.nanmean(f)*1e4:+.1f}bp sd {np.nanstd(f)*1e4:.1f}bp",
         f"    gate (halves > 0, NW t >= 2, both placebos >= 95th): {'PASS' if ok else 'FAIL'}"]
    return L, ok


def report() -> None:
    meta = json.loads((CACHE / "meta.json").read_text())
    hist = json.loads((CACHE / "ft_hist.json").read_text())
    P = pd.read_parquet(CACHE / "picks.parquet")
    for tag in ("zs", "ft"):
        P = P.merge(pd.read_parquet(CACHE / f"f_{tag}.parquet"), on=["date", "ticker"], how="left")
    vh1, vh2 = ("2023-01-01", "2023-12-31"), ("2024-01-01", "2024-12-31")
    L = ["FT round: Kronos-small on the night picks (N 1232 FT-ZS, N 1233 FT-NIGHT; pre-reg round1_prose.md 'FT round').",
         "Model: NeoQuasar/Kronos-small + Kronos-Tokenizer-base, weights committed to HF 2025-06-30 (unchanged since; sha256",
         "  b082dfcb / 59d85f6a); paper arXiv 2508.02739 (2025-08-02): 'pre-training data extends up to June 2024'. Data end is",
         "  before the release, so the registered judge start 2025-09-01 stands. 2023-24 is inside/next to FT-ZS's pretraining.",
         f"Fine-tune windows: {meta['train_events']} events 2003-22, {meta['train_used']} used (random subsample); stopping set "
         f"{meta['val_events']} events 2023-24, {meta['val_used']} used; last train target bar {meta['last_train_target']}.",
         f"Picks in 2023-24 + judge: {meta['picks']}, without a full clean 64-bar window {meta['picks_no_window']} (w = 1).",
         f"Fine-tune: epoch-0 (pretrained) val loss {hist['epoch0_val']:.4f}; " + "; ".join(
             f"ep{e['epoch']} train {e['train']:.4f} val {e['val']:.4f}" for e in hist["epochs"]),
         f"  best epoch {hist.get('best_epoch')} val {hist['best_val']:.4f}; stop: {hist['stop']}.", ""]
    verdict = {}
    for tag, name in (("zs", "FT-ZS (N 1232)"), ("ft", "FT-NIGHT (N 1233)")):
        L.append(name)
        lv, _ = block(P, f"f_{tag}", *VAL, vh1, vh2, "2023-24 (report only" + (", possibly contaminated)" if tag == "zs" else ", stopping set)"))
        lj, ok = block(P, f"f_{tag}", *JUDGE, H1, H2, "JUDGE 2025-09..2026-09")
        L += lv + lj
        verdict[name] = ok
        L.append(f"  VERDICT {name}: {'PASS -> tilt candidate (forward shadow)' if ok else 'DEAD'}")
        L.append("")
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))


def main() -> int:
    ph = sys.argv[1] if len(sys.argv) > 1 else "all"
    if ph == "timing":
        timing(); return 0
    if ph in ("build", "all"):
        build()
    if ph in ("zs", "all"):
        forecast("zs", None)
    if ph in ("train", "all"):
        train()
    if ph in ("ft", "all"):
        forecast("ft", CACHE / "ft_best.pt")
    if ph in ("report", "all"):
        report()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
