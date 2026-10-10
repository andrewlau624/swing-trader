import datetime as dt
import json

import pandas as pd

from swingtrader.daily import gamma_state_shadow as W

CSV = "date,price,dix,gex\n" + "\n".join(f"2026-09-{d:02d},6000,0.45,{g}" for d, g in
                                        [(1, 5e9), (2, 4e9), (3, 6e9), (4, 5e9), (8, 5e9), (9, 4e9), (10, 6e9), (11, 5e9),
                                         (14, 5e9), (15, 4e9), (16, 6e9), (17, 5e9), (18, -2e9), (21, -1e9)]) + "\n"


def test_state_uses_the_prior_published_session_and_signs_it():
    gex = W.fetch_gex(CSV)
    s = W.state("2026-09-21", gex)
    assert s["gex_date"] == "2026-09-18" and s["short_gamma"] and s["z"] is not None and s["z"] < -3
    assert not W.state("2026-09-18", gex)["short_gamma"]
    assert W.state("2026-09-01", gex) is None


def test_score_is_signed_continuation_from_1530_to_the_close():
    s = dict(gex_date="x", gex=-1.0, dix=0.4, short_gamma=True, z=None)
    r = W.score("2026-09-21", s, 600.0, 606.0, 609.03)        # up day, continues +50bp
    assert r["status"] == "scored" and abs(r["cont"] - (609.03 / 606 - 1)) < 1e-6 and r["long_only"] is not None
    r = W.score("2026-09-22", s, 600.0, 594.0, 591.03)        # down day, continues -> positive cont
    assert r["cont"] > 0 and r["long_only"] is None
    assert W.score("2026-09-23", s, 600.0, None, 601.0)["status"] == "pending"


def test_line_gates_on_short_gamma_days_only():
    rows = [dict(date=f"2027-01-{i % 28 + 1:02d}", status="scored", short_gamma=True, net=0.0008 + (0.0002 if i % 2 else -0.0002),
                 long_only=0.0008) for i in range(W.NEED)]
    rows += [dict(date="2027-02-01", status="scored", short_gamma=False, net=-0.0005)]
    out = W.line(rows)
    assert "short-gamma 120/120" in out and "-> PASS" in out and "long-gamma control 1 days" in out
    assert "-> KILL" in W.line([dict(r, net=-r["net"]) for r in rows])


def test_run_logs_each_session_once(tmp_path):
    gex = W.fetch_gex(CSV)
    X = {"SPY": {"2026-09-21": (600.0, 1, 609.03, 1), "2026-09-22": (610.0, 1, 605.0, 1)}}
    calls = []

    def minutes_fn(syms, day, until):
        calls.append(str(day.date()))
        return pd.DataFrame({"open": [600.0], "close": [606.0]}, index=pd.Index(["SPY"], name="symbol"))
    W.run(tmp_path, tmp_path, log=lambda *_: None, today=dt.date(2026, 9, 23), H={}, gex=gex, minutes_fn=minutes_fn,
          crosses_fn=lambda s, a, b, H: X)
    rows = [json.loads(x) for x in (tmp_path / W.LOG_NAME).read_text().splitlines()]
    assert [r["date"] for r in rows] == ["2026-09-21", "2026-09-22"] and all(r["status"] == "scored" for r in rows)
    assert rows[0]["short_gamma"] and rows[1]["gex_date"] == "2026-09-21"
    W.run(tmp_path, tmp_path, log=lambda *_: None, today=dt.date(2026, 9, 23), H={}, gex=gex, minutes_fn=minutes_fn,
          crosses_fn=lambda s, a, b, H: X)
    assert len(calls) == 2
