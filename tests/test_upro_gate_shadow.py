import datetime as dt
import json
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from research.sim.upro_gate import dec_200
from swingtrader.daily import testing
from swingtrader.daily import upro_gate_shadow as W

ET = ZoneInfo("America/New_York")


def _sessions(dates):
    return lambda a, b: [(dt.datetime(d.year, d.month, d.day, 9, 30, tzinfo=ET),
                          dt.datetime(d.year, d.month, d.day, 16, 0, tzinfo=ET))
                         for d in dates if a <= d <= b]


def _px(n, seed=0):
    r = np.random.default_rng(seed).normal(0, 0.012, n)
    return 400 * np.exp(np.cumsum(r))


def test_step_band_hysteresis():
    m = 100.0
    assert W.step(None, 101.5, m) == 1.0 and W.step(0.0, 101.5, m) == 1.0          # above upper edge -> ON
    assert W.step(None, 98.5, m) == 0.0 and W.step(1.0, 98.5, m) == 0.0            # below lower edge -> OFF
    assert W.step(1.0, 99.5, m) == 1.0 and W.step(0.0, 100.5, m) == 0.0            # inside band: keep state
    assert W.step(None, 100.5, m) == 1.0 and W.step(None, 99.5, m) == 0.0          # no state inside band: close vs sma
    assert W.step(0.0, 101.0, m) == 0.0 and W.step(1.0, 99.0, m) == 1.0            # edges are strict


def test_replay_matches_study_dec_200():
    px = pd.Series(_px(900, 3), index=pd.bdate_range("2020-01-01", periods=900))
    ours = W.replay(px)["state"].astype(float)
    study = dec_200(pd.DataFrame({"px": px}))
    pd.testing.assert_series_equal(ours, study, check_names=False)
    assert ours.iloc[:199].isna().all() and ours.iloc[199:].notna().all()


def _setup(n=320, seed=1):
    dates = [d.date() for d in pd.bdate_range("2025-06-02", periods=n)]
    bars = pd.DataFrame({"close": _px(n, seed)}, index=pd.to_datetime(dates))
    return dates, bars


def _now(d, h=8, m=20):
    return dt.datetime(d.year, d.month, d.day, h, m, tzinfo=ET)


def test_seed_then_catch_up_persists_state_and_is_idempotent(tmp_path):
    dates, bars = _setup()
    out = []
    # first run on the morning of dates[300]: logs only dates[299], seeded by replay
    W.run(tmp_path, log=out.append, now=_now(dates[300]), bars_fn=lambda s: bars[bars.index < str(dates[300])],
          sessions_fn=_sessions(dates))
    rows = [json.loads(x) for x in (tmp_path / W.LOG_NAME).read_text().splitlines()]
    assert [r["date"] for r in rows] == [str(dates[299])] and "seed" in rows[0]
    rp = W.replay(bars["close"].iloc[:300].set_axis([str(d) for d in dates[:300]]))
    assert rows[0]["state"] == ("ON" if rp.state.iloc[-1] == 1.0 else "OFF")
    assert rows[0]["days_in_state"] == rp.days.iloc[-1]
    assert rows[0]["act_on"] == str(dates[300])
    assert rows[0]["band_lo"] == round(0.99 * rp.sma.iloc[-1], 4) and rows[0]["band_hi"] == round(1.01 * rp.sma.iloc[-1], 4)
    # four sessions later: catches up 300..303, each step from the previous logged state
    W.run(tmp_path, log=out.append, now=_now(dates[304]), bars_fn=lambda s: bars[bars.index < str(dates[304])],
          sessions_fn=_sessions(dates))
    rows = [json.loads(x) for x in (tmp_path / W.LOG_NAME).read_text().splitlines()]
    assert [r["date"] for r in rows] == [str(d) for d in dates[299:304]]
    full = W.replay(bars["close"].iloc[:304].set_axis([str(d) for d in dates[:304]]))
    assert [r["state"] for r in rows] == ["ON" if s == 1.0 else "OFF" for s in full.state.iloc[299:304]]
    # same morning again: nothing appended
    W.run(tmp_path, log=out.append, now=_now(dates[304]), bars_fn=lambda s: bars[bars.index < str(dates[304])],
          sessions_fn=_sessions(dates))
    assert len((tmp_path / W.LOG_NAME).read_text().splitlines()) == 5
    assert any("already logged" in x for x in out)
    assert all(x.startswith("[upro-gate]") for x in out)


def test_switch_line_and_in_session_bar_ignored(tmp_path):
    dates = [d.date() for d in pd.bdate_range("2026-01-02", periods=205)]
    c = [100.0] * 203 + [80.0, 80.0]              # flat at the SMA (seed: inside band, close == sma -> OFF) then...
    c[202] = 103.0                                  # ...a jump above the upper edge on dates[202] -> ON
    bars = pd.DataFrame({"close": c}, index=pd.to_datetime(dates))
    out = []
    W.run(tmp_path, log=out.append, now=_now(dates[202], 16, 30), bars_fn=lambda s: bars.iloc[:202],
          sessions_fn=_sessions(dates))
    assert json.loads((tmp_path / W.LOG_NAME).read_text())["state"] == "OFF"
    # 15:00 on dates[203]: the partial dates[203] bar must not be used; dates[202] is logged with a SWITCH line
    W.run(tmp_path, log=out.append, now=_now(dates[203], 15, 0), bars_fn=lambda s: bars.iloc[:204],
          sessions_fn=_sessions(dates))
    rows = [json.loads(x) for x in (tmp_path / W.LOG_NAME).read_text().splitlines()]
    assert rows[-1]["date"] == str(dates[202]) and rows[-1]["state"] == "ON" and rows[-1]["switched"]
    assert rows[-1]["hold"] == "UPRO" and rows[-1]["days_in_state"] == 1 and rows[-1]["act_on"] == str(dates[203])
    sw = [x for x in out if "SWITCH" in x]
    assert len(sw) == 1 and "SGOV -> UPRO" in sw[0] and f"{dates[203]} 16:00 closing cross" in sw[0]


def test_missing_bar_stops_catch_up(tmp_path):
    dates, bars = _setup(260)
    W.run(tmp_path, log=lambda s: None, now=_now(dates[250]), bars_fn=lambda s: bars.iloc[:250],
          sessions_fn=_sessions(dates))
    holed = bars.iloc[:256].drop(bars.index[252])
    out = []
    W.run(tmp_path, log=out.append, now=_now(dates[256]), bars_fn=lambda s: holed, sessions_fn=_sessions(dates))
    rows = [json.loads(x) for x in (tmp_path / W.LOG_NAME).read_text().splitlines()]
    assert [r["date"] for r in rows] == [str(dates[249]), str(dates[250]), str(dates[251])]
    assert any("missing" in x for x in out)


def test_registry_covers_and_reads(tmp_path):
    t = next(t for t in testing.REGISTRY if t.name.startswith("UPRO-GATE-FWD"))
    assert {"upro_gate_shadow", "upro_gate_fwd"} <= set(t.covers) and t.started == "2026-11-09"
    assert t.read(tmp_path, tmp_path)["n"] == 0
    (tmp_path / W.LOG_NAME).write_text(json.dumps(W.row("2026-11-09", 600.0, 580.0, None, "2026-11-10", 1.0, 40)) + "\n")
    r = t.read(tmp_path, tmp_path)
    assert r["n"] == 1 and "ON (hold UPRO) for 40 sessions" in r["line"] and "0 switches" in r["line"]
