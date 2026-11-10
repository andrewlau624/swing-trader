"""QP-RUNUP-FWD (N 1203) shadow: synthetic calendar + bars; no network."""
import datetime as dt
import json
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from swingtrader.daily import qp_runup_shadow as q
from swingtrader.daily.cpc_ledger import is_session

ET = ZoneInfo("America/New_York")
DAYS = [d for d in (dt.date(2025, 6, 1) + dt.timedelta(days=i) for i in range(600)) if is_session(d)]
SDAYS = [str(d) for d in DAYS]
E, S, X = "2026-11-19", "2026-11-23", "2026-11-24"      # NEWC: F 2026-10-30 -> F+25 = 11-24 (Tue) = x


def _sessions(a, b):
    return [(dt.datetime(d.year, d.month, d.day, 9, 30, tzinfo=ET), dt.datetime(d.year, d.month, d.day, 16, 0, tzinfo=ET))
            for d in DAYS if a <= d <= b]


def _bars(F, base, fixed=None, vol=1e6):
    idx = [pd.Timestamp(d) for d in SDAYS if d >= F]
    c = [base * (1.0 if i % 2 == 0 else 1.05) for i in range(len(idx))]
    df = pd.DataFrame({"close": c, "volume": vol}, index=pd.DatetimeIndex(idx, name="date"))
    for d, v in (fixed or {}).items():
        df.loc[pd.Timestamp(d), "close"] = v
    return df


def _cal_row(t, name, priced, offer="15.00"):
    p = dt.date.fromisoformat(priced)
    return {"proposedTickerSymbol": t, "companyName": name, "proposedExchange": "NASDAQ Global", "proposedSharePrice": offer,
            "sharesOffered": "1,000,000", "pricedDate": f"{p.month}/{p.day:02d}/{p.year}", "dealStatus": "Priced"}


def world(exit_px=22.0, entry_px=20.0):
    cal = [_cal_row("NEWC", "New Co Inc.", "2026-10-29")]
    bars = {"NEWC": _bars("2026-10-30", 20.0, {E: entry_px, S: exit_px})}
    for i, t in enumerate("ABCDEF"):
        cal.append(_cal_row(f"OLD{t}", f"Old {t} Corp", "2026-03-02"))
        bars[f"OLD{t}"] = _bars("2026-03-03", 50.0, {E: 50.0, S: 51.0})
    cal.append(_cal_row("YNG", "Young Inc", "2026-09-30"))                     # aged ~35 sessions at E: not in the cohort
    bars["YNG"] = _bars("2026-10-01", 30.0, {E: 30.0, S: 60.0})
    cal.append(_cal_row("ZZACU", "Zz Acquisition Corp", "2026-03-02", "10.00"))  # SPAC: never fetched, never in the cohort
    bars["SPY"] = _bars("2025-06-02", 700.0, {E: 700.0, S: 707.0}, 5e7)
    bars["IWM"] = _bars("2025-06-02", 250.0, {E: 250.0, S: 250.0}, 5e7)
    calls = {"bars": []}

    def cal_fn(m):
        return [r for r in cal if f"{r['pricedDate'].split('/')[2]}-{int(r['pricedDate'].split('/')[0]):02d}" == m]

    def bars_fn(syms, start):
        calls["bars"].append(list(syms))
        return {s: bars[s] for s in syms if s in bars}

    def crosses_fn(syms, a, b):
        return {(s, str(d.date())): (None, float(c)) for s in syms if s in bars
                for d, c in bars[s].close.items() if a <= str(d.date()) <= b}

    kw = dict(cal_fn=cal_fn, bars_fn=bars_fn, sessions_fn=_sessions, crosses_fn=crosses_fn,
              quotes_fn=lambda syms, day: {s: (19.9, 20.1) for s in syms},
              adj_fn=lambda syms, a, b: {s: bars[s] for s in syms if s in bars})
    return kw, bars, calls


def at(day, hm=(8, 20)):
    return dt.datetime.fromisoformat(day).replace(hour=hm[0], minute=hm[1], tzinfo=ET).astimezone(dt.timezone.utc)


# ------------------------------------------------------------------ pure pieces

@pytest.mark.parametrize("F,x,e,s", [
    ("2026-10-30", "2026-11-24", "2026-11-19", "2026-11-23"),   # weekday target
    ("2026-10-14", "2026-11-09", "2026-11-04", "2026-11-06"),   # F+25 = Sun 11-08 -> Monday
    ("2026-11-01", "2026-11-27", "2026-11-23", "2026-11-25"),   # F+25 = Thanksgiving 11-26 -> Fri; x-1 skips the holiday
    ("2026-12-01", "2026-12-28", "2026-12-22", "2026-12-24"),   # F+25 = Sat 12-26, Christmas 12-25 between x-1 and x
])
def test_x_dates_weekends_and_holidays(F, x, e, s):
    assert q.x_dates(F, SDAYS) == dict(x=x, e=e, s=s)


def test_name_filters():
    base = dict(ticker="ABCD", name="Abcd Therapeutics, Inc.", offer=15.0)
    assert q.name_reason(base) is None
    assert q.name_reason({**base, "name": "Abcd Acquisition Corp II"}) == "spac name"
    assert q.name_reason({**base, "ticker": "ABCDU", "offer": 10.0}) == "spac unit"
    assert q.name_reason({**base, "ticker": "ABCDU", "offer": 15.0}) is None       # a 5-letter U ticker at $15 is not a unit
    assert q.name_reason({**base, "name": "Abcd Income Fund"}) == "fund"
    assert q.name_reason({**base, "ticker": "AB.WS"}) == "not a plain ticker"


def test_classify_universe_checks():
    ipo = dict(id="N:2026-10-29", ticker="N", name="N Inc", priced="2026-10-29", offer=15.0)
    b = _bars("2026-10-30", 20.0)
    assert q.classify(ipo, b, "2026-11-18") == ("2026-10-30", None)
    assert q.classify(ipo, _bars("2026-10-30", 4.0), "2026-11-18")[1].startswith("day-1")
    assert q.classify(ipo, _bars("2026-10-30", 20.0, vol=1e5), "2026-11-18")[1].startswith("day-1")      # $2M day-1 $vol
    assert q.classify(ipo, _bars("2026-10-10", 20.0), "2026-11-18")[1].startswith("bars before")
    assert q.classify(ipo, _bars("2026-11-04", 20.0), "2026-11-18")[1].startswith("first bar > 3")
    flat = _bars("2026-10-30", 10.0)
    flat["close"] = 10.0
    assert q.classify(ipo, flat, "2026-11-18")[1].startswith("pinned")
    assert q.classify(ipo, None, "2026-11-18") == (None, "no bars")


def test_entry_check_uses_only_bars_through_upto():
    b = _bars("2026-10-30", 20.0, {E: 1.0})                 # x-3's own close would fail the $3 filter
    ec = q.entry_check(b, "2026-10-30", "2026-11-18")
    assert ec["ok"] and ec["px"] == b.close[pd.Timestamp("2026-11-18")]
    assert ec["side"] == 0.0005                              # px >= 10 and median $vol >= $10M
    assert not q.entry_check(b, "2026-10-30", E)["ok"]       # the study's x-3 version is reported separately


# ------------------------------------------------------------------ run: full flow

def test_flow_signal_enter_score_and_sign(tmp_path):
    kw, bars, _ = world()
    logs = []
    rows = q.run(tmp_path, log=logs.append, now=at(E), **kw)
    f = q.fold(rows)
    r = f["NEWC:2026-10-29"]
    assert r["status"] == "signal" and r["x"] == X and r["e"] == E and r["s"] == S and r["late"] is False
    assert r["entry"]["px"] == bars["NEWC"].close[pd.Timestamp("2026-11-18")]
    assert any("SIGNAL buy NEWC" in m and "no order placed" in m for m in logs)
    assert set(f) == {"NEWC:2026-10-29"}                    # seasoned deals (x-3 before START) are cohort only
    rows = q.run(tmp_path, log=logs.append, now=at("2026-11-20"), **kw)
    r = q.fold(rows)["NEWC:2026-10-29"]
    assert r["status"] == "entered" and r["entry_px"] == 20.0 and r["entry_hs"] == pytest.approx(0.005)
    rows = q.run(tmp_path, log=logs.append, now=at(X), **kw)
    r = q.fold(rows)["NEWC:2026-10-29"]
    assert r["status"] == "scored" and r["n_ctl"] == 6        # OLDA-F; YNG too young, the SPAC excluded, self excluded
    assert r["ret"] == pytest.approx(0.10) and r["ctl"] == pytest.approx(0.02)
    assert r["xc"] == pytest.approx(0.10 - 0.02 - 0.001) and r["xc"] > 0
    assert r["xc_3x"] == pytest.approx(0.10 - 0.02 - 0.003)
    assert r["xc_spread"] == pytest.approx(0.10 - 0.02 - 0.010)
    assert r["xs_spy"] == pytest.approx(0.10 - 0.01 - 0.001) and r["xs_iwm"] == pytest.approx(0.10 - 0.001)
    assert r["study_entry_ok"] is True
    s = q.stats(rows)
    assert s["n"] == 1 and s["mean"] == pytest.approx(0.079)
    assert "QP-RUNUP-FWD: 1 scored" in q.line(rows)


def test_losing_event_scores_negative(tmp_path):
    kw, _, _ = world(exit_px=18.0)
    rows = q.run(tmp_path, log=lambda *_: None, now=at(X), **kw)
    r = q.fold(rows)["NEWC:2026-10-29"]
    assert r["status"] == "scored" and r["late"] is True
    assert r["xc"] == pytest.approx(-0.10 - 0.02 - 0.001) and r["xc"] < 0


def test_no_lookahead_signal_ignores_x3_and_later_bars(tmp_path):
    a, _, _ = world(entry_px=20.0)
    b, _, _ = world(entry_px=1.0, exit_px=0.5)                # a collapse at/after x-3 must not change the x-3 morning decision
    ra = q.fold(q.run(tmp_path / "a", log=lambda *_: None, now=at(E), **a))["NEWC:2026-10-29"]
    rb = q.fold(q.run(tmp_path / "b", log=lambda *_: None, now=at(E), **b))["NEWC:2026-10-29"]
    assert ra["status"] == rb["status"] == "signal"
    assert ra["entry"] == rb["entry"]
    # before x-3's morning there is no signal at all
    rc = q.fold(q.run(tmp_path / "c", log=lambda *_: None, now=at("2026-11-18"), **a))["NEWC:2026-10-29"]
    assert rc["status"] == "scheduled"


def test_idempotent_reruns(tmp_path):
    kw, _, _ = world()
    q.run(tmp_path, log=lambda *_: None, now=at(E), **kw)
    n1 = (tmp_path / q.LOG_NAME).read_text().count("\n")
    q.run(tmp_path, log=lambda *_: None, now=at(E, (12, 0)), **kw)
    assert (tmp_path / q.LOG_NAME).read_text().count("\n") == n1
    q.run(tmp_path, log=lambda *_: None, now=at(X), **kw)
    n2 = (tmp_path / q.LOG_NAME).read_text().count("\n")
    q.run(tmp_path, log=lambda *_: None, now=at("2026-11-25"), **kw)
    assert (tmp_path / q.LOG_NAME).read_text().count("\n") == n2
    st = [json.loads(x)["status"] for x in (tmp_path / q.LOG_NAME).read_text().splitlines()]
    assert st == ["scheduled", "signal", "entered", "scored"]


def test_spac_never_fetched(tmp_path):
    kw, _, calls = world()
    q.run(tmp_path, log=lambda *_: None, now=at(E), **kw)
    assert all("ZZACU" not in c for c in calls["bars"])


def test_gate_states():
    def sc(i, x, sp):
        return dict(id=str(i), ticker="T", e=f"2027-01-{1 + i % 28:02d}", status="scored", xc=x, xc_spread=sp)
    good = [sc(i, 0.006 + 0.001 * (i % 3), 0.004) for i in range(40)]
    assert q.stats(good)["state"].startswith("PASS")
    assert not q.stats([dict(r, xc_spread=-0.001) for r in good])["state"].startswith("PASS")   # dies on the real spread
    bad = [sc(i, -0.002 + 0.001 * (i % 3), -0.004) for i in range(80)]
    assert q.stats(bad)["state"].startswith("KILL (mean <= 0")
    assert q.stats(good[:10])["state"] == "collecting (10/40)"
