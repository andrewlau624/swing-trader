import datetime as dt
import json

import numpy as np
import pandas as pd

from research.sim import seq_night as sq
from swingtrader.daily import seq_tilt_shadow as W


def _bars(n=320, seed=0, end="2026-11-09", base=50.0):
    """Synthetic split-adjusted daily bars ending the session BEFORE `end`, plus `end`'s full-day row."""
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(end=end, periods=n + 1)
    c = base * np.exp(np.cumsum(rng.normal(0, 0.06, n + 1)))
    o = c * np.exp(rng.normal(0, 0.01, n + 1))
    h = np.maximum(o, c) * (1 + rng.uniform(0, 0.03, n + 1))
    lo = np.minimum(o, c) * (1 - rng.uniform(0, 0.03, n + 1))
    v = rng.uniform(1e6, 3e6, n + 1)
    return pd.DataFrame(dict(open=o, high=h, low=lo, close=c, volume=v), index=idx)


def _today(b, T, drop=0.12):
    """15:40 row: a -drop day closing near the low (the night rule shape)."""
    pc = float(b[b.index < pd.Timestamp(T)]["close"].iloc[-1])
    p = pc * (1 - drop)
    return dict(open=pc * 0.99, high=pc, low=p * 0.995, close=p, volume=1.5e6)


def _model(feats=("day_ret", "rsi", "vol20", "repeat", "spy_ret1"), coefs=(-1.0, 0.5, 0.2, 0.3, 9.0)):
    return dict(intercept=0.001, features=[dict(name=f, mu=0.0, sd=1.0, coef=c, active=True, night_const=f in sq.MKT)
                                           for f, c in zip(feats, coefs)])


def test_features_match_research_function_and_use_no_bar_dated_T_or_later():
    T = "2026-11-09"
    b = _bars()
    row = _today(b, T)
    tr = pd.DataFrame([row], index=["AAA"])
    F = W.features_at(T, {"AAA": b}, tr)
    # tampering with any daily bar dated T or later must not move a feature (only today's 15:40 row counts)
    b2 = b.copy(); b2.loc[b2.index >= pd.Timestamp(T), :] *= 3.0
    b2 = pd.concat([b2, pd.DataFrame([b2.iloc[-1].to_numpy() * 2], index=[pd.Timestamp("2026-11-10")], columns=b2.columns)])
    F2 = W.features_at(T, {"AAA": b2}, tr)
    num = [c for c in F.columns if c != "rets"]
    pd.testing.assert_frame_equal(F[num].astype(float), F2[num].astype(float))
    # and equals seq_night.features() run on bars < T plus the 15:40 row
    hist = b[b.index < pd.Timestamp(T)]
    full = pd.concat([hist, pd.DataFrame([row], index=[pd.Timestamp(T)])])
    ref = sq.features(*(full[[k]].rename(columns={k: "AAA"}) for k in ("open", "high", "low", "close", "volume")),
                      full[["close"]].rename(columns={"close": "AAA"}))
    for k in ("rsi", "macd_pct", "sq_on_run", "hma_turn_age", "ret252", "lag_rsi", "atr_pct"):
        assert np.isclose(F.loc["AAA", k], ref[k].iloc[-1], equal_nan=True), k
    # SEL-NIGHT pool columns: prior-20 vol20 / ADV, raw 15:40 price
    lr = np.log(hist["close"] / hist["close"].shift(1)).iloc[-20:]
    assert np.isclose(F.loc["AAA", "vol20"], lr.std() * np.sqrt(252))
    assert np.isclose(F.loc["AAA", "log_adv"], np.log((hist["close"] * hist["volume"]).iloc[-20:].mean()))
    assert np.isclose(F.loc["AAA", "day_ret"], row["close"] / hist["close"].iloc[-1] - 1)
    assert np.isclose(F.loc["AAA", "log_px"], np.log(row["close"]))
    assert len(F.loc["AAA", "rets"]) == 20 and np.allclose(F.loc["AAA", "rets"], lr.to_numpy())


def test_score_ignores_inactive_and_night_constant_features_and_imputes_nan_at_mean():
    F = pd.DataFrame(dict(day_ret=[-0.1, -0.2], rsi=[np.nan, 1.0], vol20=[1.0, 1.0], repeat=[0.0, 1.0], spy_ret1=[5.0, 5.0]),
                     index=["A", "B"])
    m = _model()
    s = W.score(F, m)
    assert np.isclose(s["A"], 0.001 + 0.1 + 0 + 0.2) and np.isclose(s["B"], 0.001 + 0.2 + 0.5 + 0.2 + 0.3)
    m["features"][1]["active"] = False
    assert np.isclose(W.score(F, m)["B"], 0.001 + 0.2 + 0.2 + 0.3)


def test_tilt_matches_research_replay():
    p = np.array([0.3, -1.0, 0.1, 2.0])
    z = (p - p.mean()); z = z / z.std()
    m = np.clip(1 + 0.25 * z, 0.25, 2); m = m / m.mean()
    assert np.allclose(W.tilt(p), m) and np.isclose(W.tilt(p).mean(), 1.0)
    assert np.allclose(W.tilt([1.0, 1.0]), 1.0)


def _setup(tmp_path, T="2026-11-10"):
    syms = {"AAA": 1, "BBB": 2, "CCC": 3, "DDD": 4, "ETF": 5, "QUIET": 6}
    bars = {s: _bars(seed=k, end=T) for s, k in syms.items()}
    q = bars["QUIET"]; bars["QUIET"] = q.assign(close=50 + np.arange(len(q)) * 1e-3)       # vol20 ~ 0
    bars["DDD"] = bars["AAA"] * 1.0001                                                       # a twin of AAA
    drops = dict(AAA=0.15, BBB=0.10, CCC=0.09, DDD=0.12, ETF=0.20, QUIET=0.11)
    tr = pd.DataFrame([_today(bars[s], T, drops[s]) for s in syms], index=list(syms))
    with (tmp_path / W.CAND_LOG).open("w") as f:
        for s in syms:
            f.write(json.dumps(dict(date=T, sym=s, account="live", price=1.0, day_ret=-drops[s], ibs=0.02, status="pending")) + "\n")
    return T, bars, tr


def test_run_logs_picks_then_scores_and_never_rescans(tmp_path, monkeypatch):
    T, bars, tr = _setup(tmp_path)
    monkeypatch.setattr(W, "load_model", lambda: _model())
    monkeypatch.setattr(W, "load_sectors", lambda: {"AAA": "Technology"})
    seen = []
    kw = dict(bars_fn=lambda syms, start: (seen.append(start), {s: bars[s] for s in syms})[1],
              rth_fn=lambda syms, d, hm: (seen.append(hm), tr.loc[syms])[1], fund_fn=lambda s: s == "ETF")
    out = []
    # morning of T+1 before its open cross: picks logged, nothing scored yet
    W.run(tmp_path, log=out.append, today=dt.date(2026, 11, 11), crosses_fn=lambda s, a, b: {}, **kw)
    rows = [json.loads(x) for x in (tmp_path / W.LOG_NAME).read_text().splitlines()]
    picks = [r for r in rows if r.get("sym")]
    assert 1540 in seen
    assert {r["sym"] for r in picks} == {"AAA", "BBB", "CCC"}       # ETF (fund), QUIET (vol20), DDD (twin of AAA) out
    assert sorted(r["rank"] for r in picks) == [1, 2, 3] and all(r["status"] == "pending" and not r["backfill"] for r in picks)
    assert np.isclose(np.mean([r["m"] for r in picks]), 1.0, atol=1e-3)
    top = min(picks, key=lambda r: r["rank"])
    assert top["score"] == max(r["score"] for r in picks)
    # next run after T+1's open cross: scored; no second scan of T
    X = {s: {T: (None, None, 10.0, 100), "2026-11-11": (10.0 * (1 + 0.01 * k), 100, None, None)}
         for k, s in enumerate(["AAA", "BBB", "CCC"])}
    s = W.run(tmp_path, log=out.append, today=dt.date(2026, 11, 12), crosses_fn=lambda syms, a, b: X, **kw)
    rows = [json.loads(x) for x in (tmp_path / W.LOG_NAME).read_text().splitlines()]
    assert sum(1 for r in rows if r.get("status") == "scanned") == 1
    assert all(r["status"] == "scored" for r in rows if r.get("sym"))
    assert s["nights"] == 1 and s["names"] == 3 and "SEQ-TILT-FWD" in out[-1]


def test_repeat_flag_uses_the_previous_pick_nights(tmp_path, monkeypatch):
    T, bars, tr = _setup(tmp_path)
    (tmp_path / W.LOG_NAME).write_text(json.dumps(dict(T="2026-11-06", sym="BBB", status="no_cross", rank=1, score=0.0,
                                                       m=1.0, w_v1=1.0, backfill=True)) + "\n"
                                       + json.dumps(dict(T="2026-11-06", status="scanned")) + "\n")
    monkeypatch.setattr(W, "load_model", lambda: _model())
    monkeypatch.setattr(W, "load_sectors", lambda: {})
    W.run(tmp_path, log=lambda *_: None, today=dt.date(2026, 11, 11), crosses_fn=lambda s, a, b: {},
          bars_fn=lambda syms, start: {s: bars[s] for s in syms}, rth_fn=lambda syms, d, hm: tr.loc[syms],
          fund_fn=lambda s: s == "ETF")
    rows = {r["sym"]: r for r in map(json.loads, (tmp_path / W.LOG_NAME).read_text().splitlines()) if r.get("T") == T and r.get("sym")}
    assert rows["BBB"]["repeat"] and not rows["AAA"]["repeat"]


def _night(T, rs, scores, w=None, bf=False):
    w = w or [1.0] * len(rs)
    return [dict(T=T, sym=f"S{i}", status="scored", r=r, score=s, w_v1=wi, backfill=bf) for i, (r, s, wi) in enumerate(zip(rs, scores, w))]


def test_readout_delta_tmb_and_gate():
    rows = _night("2026-11-10", [0.02, 0.01, -0.01, -0.02], [4, 3, 2, 1])          # perfect ranking
    N = W.nights(rows)[0]
    m = W.tilt([4, 3, 2, 1]); r = np.array([0.02, 0.01, -0.01, -0.02])
    assert np.isclose(N["delta_ew_bp"], 1e4 * ((m * r).mean() - r.mean())) and N["delta_ew_bp"] > 0
    assert np.isclose(N["tmb_bp"], 1e4 * (0.015 - (-0.015)))
    # pending pick holds the whole night out; 1-pick nights do not count
    assert W.nights(rows + [dict(T="2026-11-10", sym="P", status="pending", score=0, w_v1=1)]) == []
    assert W.nights(_night("2026-11-11", [0.01], [1])) == []
    assert W.nights(_night("2026-11-12", [0.01, 0.0], [1, 2], bf=True)) == []
    many = []
    rng = np.random.default_rng(0)
    for i in range(60):
        r = rng.normal(0, 0.02, 4)
        many += _night(f"2026-{i:03d}", list(r), list(r + rng.normal(0, 0.005, 4)))   # informative scores
    s = W.summary(many)
    assert s["nights"] == 60 and s["t"] >= 2 and W.verdict(s).startswith("PASS")
    bad = []
    for i in range(60):
        r = rng.normal(0, 0.02, 4)
        bad += _night(f"2026-{i:03d}", list(r), list(-r))
    assert W.verdict(W.summary(bad)) == "KILL"
    assert W.verdict(W.summary(many[:40])) == "(10/60 nights)"


def test_frozen_artifact_is_well_formed():
    m = W.load_model()
    assert m["train_window"][1] <= "2015-12-31" and m["alpha"] == 10.0
    names = [f["name"] for f in m["features"]]
    assert len(names) == len(set(names)) and "day_ret" in names and "repeat" in names
    act = [f for f in m["features"] if f["active"] and not f["night_const"]]
    assert act and all(f["sd"] > 0 for f in act)
    assert W.load_sectors()  # committed sector map loads
