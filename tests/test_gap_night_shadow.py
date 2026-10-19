import datetime as dt

import numpy as np
import pandas as pd

from swingtrader.daily import gap_night_shadow as W

N = 40
DATES = [str(d.date()) for d in pd.bdate_range("2026-08-03", periods=N)]
T = DATES[-2]            # gap day; DATES[-1] is T+1 (its open is in the frame)


def _bars(gap_on_T=0.0, close=20.0, volume=5_000_000, day_ret=0.0, ibs=0.5, on=0.0):
    """Flat at `close`; on T the open gaps by `gap_on_T`, the close moves by `day_ret`; T+1 opens `on` above T's close."""
    idx = pd.DatetimeIndex(DATES)
    c = np.full(N, close)
    o = c.copy()
    h, lo = c.copy(), c.copy()
    i = DATES.index(T)
    o[i] = close * (1 + gap_on_T)
    c[i] = close * (1 + day_ret)
    h[i], lo[i] = max(o[i], c[i]) * 1.02, min(o[i], c[i]) * 0.98
    c[i] = lo[i] + ibs * (h[i] - lo[i])
    o[i + 1] = c[i] * (1 + on)
    return pd.DataFrame({"open": o, "high": h, "low": lo, "close": c, "volume": [volume] * N}, index=idx)


def _universe():
    bars = {f"S{i:02d}": _bars(on=0.001 * i) for i in range(10)}         # eligible, no gap: univ = mean of 0..0.9%
    bars["UPG"] = _bars(gap_on_T=0.05, on=0.02)                             # up gap, +2% overnight
    bars["DNG"] = _bars(gap_on_T=-0.04, on=-0.01)                           # down gap
    bars["SMALL"] = _bars(gap_on_T=0.02)                                    # gap < 3%
    bars["CHEAP"] = _bars(gap_on_T=0.05, close=3.0)                         # prev close < $5
    bars["THIN"] = _bars(gap_on_T=0.05, volume=1000)                        # ADV < $50M
    bars["FUNDX"] = _bars(gap_on_T=0.05)                                    # fund
    bars["NIGHT"] = _bars(day_ret=-0.10, ibs=0.05, on=0.03)                 # night-leg pick: out of univ_x only
    return bars


def test_gaps_and_night_bench():
    F = W.wide(_universe())
    fund = lambda s: s == "FUNDX"  # noqa: E731
    g = {r["sym"]: r for r in W.gaps(T, F, fund)}
    assert set(g) == {"UPG", "DNG"}
    assert g["UPG"]["cls"] == "up" and g["DNG"]["cls"] == "down" and abs(g["UPG"]["gap"] - 0.05) < 1e-6
    nb = W.night_bench(T, F, fund)
    assert nb["n_univ"] == 14 and nb["n_night"] == 1                        # 10 flat + UPG + DNG + SMALL + NIGHT
    # univ_x drops the night pick, so it is below univ
    assert nb["univ_x"] < nb["univ"]
    # no T+1 bar for the last session -> None
    assert W.night_bench(DATES[-1], F, fund) is None


def test_eligible_counts_small_gap_names_in_the_bench():
    F = W.wide(_universe())
    el = W.eligible(T, F, lambda s: s == "FUNDX")
    assert el["SMALL"] and not el["CHEAP"] and not el["THIN"] and not el["FUNDX"]
    nb = W.night_bench(T, F, lambda s: s == "FUNDX")
    assert nb["n_univ"] == 14


def test_score_waits_for_the_next_open_cross():
    X = {"UPG": {"2026-10-20": (21.0, 1, 20.0, 100), "2026-10-21": (20.4, 500, 20.5, 100)},
         "SPY": {"2026-10-20": (500.0, 1, 500.0, 1), "2026-10-21": (501.0, 1, 502.0, 1)}}
    r = W.score(dict(T="2026-10-20", sym="UPG", cls="up", status="pending"), X)
    assert r["status"] == "scored" and r["d1"] == "2026-10-21" and abs(r["r"] - 0.02) < 1e-9
    assert abs(r["spy"] - 0.002) < 1e-9 and abs(r["net5"] - (0.02 - 0.0005)) < 1e-9 and r["open_usd"] == 10200
    assert W.score(dict(T="2026-10-21", sym="UPG", cls="up", status="pending"), X) is None


def _night(Tn, univ, backfill=False):
    return dict(T=Tn, status="night", backfill=backfill, n_gap=2, univ=univ, univ_x=univ - 0.0005, n_univ=100)


def test_summary_is_per_night_excess_and_ignores_backfill_and_unbenched():
    rows = []
    for i in range(3):
        Tn = f"2026-11-0{i + 2}"
        rows.append(_night(Tn, 0.001))
        rows.append(dict(T=Tn, sym="A", cls="up", status="scored", r=0.004, spy=0.0, backfill=False))
        rows.append(dict(T=Tn, sym="B", cls="down", status="scored", r=0.002, spy=0.0, backfill=False))
    rows.append(_night("2026-11-09", 0.0, backfill=True))
    rows.append(dict(T="2026-11-09", sym="Z", cls="up", status="scored", r=0.5, spy=0.0, backfill=True))
    rows.append(dict(T="2026-11-10", sym="Q", cls="up", status="scored", r=0.5, spy=0.0, backfill=False))   # no night row yet
    s = W.summary(rows)
    assert s["nights"] == 3 and s["names"] == 6 and s["unbenched"] == 1
    assert abs(s["raw_bp"] - 30.0) < 1e-6 and abs(s["excess_bp"] - 20.0) < 1e-6 and abs(s["excess_x_bp"] - 25.0) < 1e-6
    assert abs(s["up_excess_bp"] - 30.0) < 1e-6 and abs(s["down_excess_bp"] - 10.0) < 1e-6 and s["up_nights"] == 3
    assert abs(s["net5_bp"] - 15.0) < 1e-6
    assert W.summary(rows, True)["nights"] == 1
    assert "3/60 gap nights" in W.line(rows)


def test_run_scans_and_scores_with_fakes(tmp_path):
    import json
    state = tmp_path / "state"
    state.mkdir()
    (state / "daily-universe-2026-10-19.json").write_text(json.dumps(
        [{"symbol": s, "adv20": 1e8} for s in _universe()] + [{"symbol": "IGNORED", "adv20": 1e6}]))
    bars = _universe()
    bars["SPY"] = _bars()
    today = dt.date.fromisoformat(DATES[-1]) + dt.timedelta(days=1)
    pulled = []

    def bars_fn(syms, start, end=None):
        pulled.extend(syms)
        return {s: bars[s] for s in syms if s in bars}

    def crosses_fn(syms, d0, end, H):
        out = {}
        for s in syms:
            b = bars[s]
            out[s] = {str(d.date()): (float(r.open), 1000, float(r.close), 1000) for d, r in b.iterrows() if str(d.date()) >= d0}
        return out

    s = W.run(state, tmp_path, log=lambda *_: None, today=today, H={}, bars_fn=bars_fn, crosses_fn=crosses_fn,
              fund_fn=lambda s: s == "FUNDX", backfill=3)
    rows = [json.loads(x) for x in (state / W.LOG_NAME).read_text().splitlines()]
    assert "IGNORED" not in pulled
    nights = [r for r in rows if r["status"] == "night"]
    assert {r["T"] for r in nights} == set(DATES[-4:-1]) and all(r["backfill"] for r in nights)
    scored = {(r["T"], r["sym"]): r for r in rows if r["status"] == "scored"}
    assert set(scored) == {(T, "UPG"), (T, "DNG")}
    assert abs(scored[(T, "UPG")]["r"] - 0.02) < 1e-6
    b = W.summary(rows, True)
    assert b["nights"] == 1 and s["nights"] == 0
    assert "0 forward gap nights" in W.line(rows)
    # second run is idempotent
    W.run(state, tmp_path, log=lambda *_: None, today=today, H={}, bars_fn=bars_fn, crosses_fn=crosses_fn,
          fund_fn=lambda s: s == "FUNDX", backfill=3)
    rows2 = [json.loads(x) for x in (state / W.LOG_NAME).read_text().splitlines()]
    assert len(rows2) == len(rows)
