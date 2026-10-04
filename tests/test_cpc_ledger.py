import datetime as dt
import json
from zoneinfo import ZoneInfo

import pytest

from swingtrader.daily import cpc_ledger as L

ET = ZoneInfo("America/New_York")


def at(y, m, d, h=9):
    return dt.datetime(y, m, d, h, 0, tzinfo=ET)


@pytest.fixture
def path(tmp_path):
    return tmp_path / L.LOG_NAME


def ev(**kw):
    base = dict(family="SPLIT_OFF", issuer="MDT", security="MDT->MMED", event_date="2026-10-02",
                deadline=L.close_et(dt.date(2026, 10, 9)), status="KNOWN_AVAILABLE", eligibility="odd lot",
                maximum_position=8000, estimated_gross_payoff=300.0, estimated_net_payoff=195.0,
                required_action="x", source="s", source_date="2026-10-02", notes="")
    base.update(kw)
    return base


# ---- UMH generation
def test_umh_regular_month_deadline_is_10th_and_investment_the_15th():
    e = L.umh_event(2026, 11, at(2026, 10, 4))
    assert e["event_date"] == "2026-11-16"          # Sun 15th -> next session
    assert e["deadline"] == L.close_et(dt.date(2026, 11, 10))
    assert e["maximum_position"] == 1000.0 and e["estimated_gross_payoff"] == 50.0
    assert e["estimated_net_payoff"] == 32.5
    assert "NOT guaranteed profit" in e["notes"] and "Roth cannot" in e["notes"] and "UNKNOWN" in e["notes"]


def test_umh_dividend_month_and_holiday_15th():
    assert L.umh_event(2026, 9, at(2026, 8, 1))["event_date"] == "2026-09-15"
    assert L.umh_event(2026, 12, at(2026, 11, 1))["event_date"] == "2026-12-15"
    # 15th is a holiday: 2027-02-15 is Presidents Day -> Tuesday the 16th
    assert L.umh_event(2027, 2, at(2027, 1, 1))["event_date"] == "2027-02-16"
    # Good Friday 2027-03-26 and July 4 2026 observed Fri July 3
    assert not L.is_session(dt.date(2027, 3, 26)) and not L.is_session(dt.date(2026, 7, 3))
    assert L.is_session(dt.date(2026, 10, 12))      # Columbus Day: NYSE open


def test_umh_deadline_weekend_and_bank_holiday_roll_back():
    assert L.umh_deadline(dt.date(2026, 11, 16)) == dt.date(2026, 11, 10)        # Tue
    assert L.umh_deadline(dt.date(2026, 10, 15)) == dt.date(2026, 10, 9)         # 10th is Sat -> Fri
    assert L.umh_deadline(dt.date(2027, 1, 15)) == dt.date(2027, 1, 8)           # 10th Sun -> Fri


def test_umh_events_horizon_skips_past_deadline():
    es = L.umh_events(at(2026, 10, 11), horizon=2)    # Oct deadline (Oct 9) has passed
    assert [e["event_date"] for e in es] == ["2026-11-16", "2026-12-15"]
    es = L.umh_events(at(2026, 10, 4), horizon=2)
    assert es[0]["event_date"] == "2026-10-15"


# ---- ids, duplicates, deadlines, prospective enforcement
def test_stable_event_id():
    assert L.event_id("UMH_OCP", "UMH", "2026-10-15") == "UMH-OCP:UMH:2026-10-15"
    assert L.event_id("split off", "m d t", "2026-10-02") == "SPLIT-OFF:M-D-T:2026-10-02"


def test_refuse_after_deadline_and_missing_deadline(path):
    with pytest.raises(L.Refused):
        L.add_event(path, ev(deadline=L.close_et(dt.date(2026, 10, 9))), now=at(2026, 10, 9, 16))
    with pytest.raises(L.Refused):
        L.add_event(path, ev(deadline=None), now=at(2026, 10, 4))          # not provably prospective
    assert not path.exists()
    k, r = L.add_event(path, ev(deadline=None, status="UNKNOWN"), now=at(2026, 10, 4))
    assert k == "new"


def test_duplicate_prevention_and_timestamp(path):
    k1, r = L.add_event(path, ev(), now=at(2026, 10, 4))
    k2, _ = L.add_event(path, ev(), now=at(2026, 10, 5))
    assert (k1, k2) == ("new", "unchanged")
    assert len(L.read(path)) == 1 and r["timestamp_known"].startswith("2026-10-04T09:00")


def test_material_change_appends_change_and_bumps_version(path):
    L.add_event(path, ev(), now=at(2026, 10, 4))
    k, rec = L.add_event(path, ev(deadline=L.close_et(dt.date(2026, 10, 8))), now=at(2026, 10, 5))
    assert k == "changed" and rec["version"] == 2 and rec["old"]["deadline"].startswith("2026-10-09")
    s = L.fold(L.read(path))["SPLIT-OFF:MDT:2026-10-02"]
    assert s["deadline"].startswith("2026-10-08") and s["version"] == 2
    assert len(L.read(path)) == 2                    # earlier line untouched


# ---- transitions
def test_allowed_and_forbidden_transitions(path):
    L.add_event(path, ev(), now=at(2026, 10, 4))
    eid = "SPLIT-OFF:MDT:2026-10-02"
    with pytest.raises(L.Refused):
        L.transition(path, eid, "POTENTIAL")                 # backwards
    L.transition(path, eid, "ACTION_REQUIRED", now=at(2026, 10, 5), material=True)
    L.transition(path, eid, "COMPLETED", now=at(2026, 10, 12))
    for to in ("MISSED", "ACTION_REQUIRED", "COMPLETED"):
        with pytest.raises(L.Refused):
            L.transition(path, eid, to)                      # terminal
    with pytest.raises(L.Refused):
        L.transition(path, "nope", "MISSED")
    assert set(L.ALLOWED) == set(L.STATUSES)


def test_potential_cannot_complete_directly(path):
    L.add_event(path, ev(status="POTENTIAL"), now=at(2026, 10, 4))
    with pytest.raises(L.Refused):
        L.transition(path, "SPLIT-OFF:MDT:2026-10-02", "COMPLETED")


def test_sweep_misses_unacted_but_not_action_required(path):
    L.add_event(path, ev(), now=at(2026, 10, 4))
    L.add_event(path, ev(issuer="X", security="X", status="ACTION_REQUIRED"), now=at(2026, 10, 4))
    assert L.sweep(path, at(2026, 10, 10)) == ["SPLIT-OFF:MDT:2026-10-02"]
    s = L.fold(L.read(path))
    assert s["SPLIT-OFF:X:2026-10-02"]["status"] == "ACTION_REQUIRED"


def test_promote_umh_within_window(path):
    e = L.umh_events(at(2026, 10, 1), horizon=1)[0]
    L.add_event(path, e, now=at(2026, 10, 1))
    assert L.promote(path, at(2026, 10, 1)) == ["UMH-OCP:UMH-PROPERTIES:2026-10-15"]   # 8d to the Oct 9 deadline
    assert L.promote(path, at(2026, 10, 2)) == []                                       # already ACTION_REQUIRED
    assert L.fold(L.read(path))["UMH-OCP:UMH-PROPERTIES:2026-10-15"]["version"] == 2


# ---- alerts
def test_alert_dedup_and_change_alert(path, tmp_path):
    L.add_event(path, ev(), now=at(2026, 10, 4))
    a = L.send_alerts(path, tmp_path, email=False, now=at(2026, 10, 4), log=lambda *_: None)
    b = L.send_alerts(path, tmp_path, email=False, now=at(2026, 10, 4), log=lambda *_: None)
    assert a == [("SPLIT-OFF:MDT:2026-10-02", 1)] and b == []
    L.add_event(path, ev(maximum_position=5000), now=at(2026, 10, 5))
    c = L.send_alerts(path, tmp_path, email=False, now=at(2026, 10, 5), log=lambda *_: None)
    d = L.send_alerts(path, tmp_path, email=False, now=at(2026, 10, 5), log=lambda *_: None)
    assert c == [("SPLIT-OFF:MDT:2026-10-02", 2)] and d == []


def test_alert_email_has_the_nine_items():
    e = L.umh_event(2026, 11, at(2026, 10, 4))
    e.update(event_id="UMH_OCP:UMH:2026-11-16", version=1)
    subj, html = L.alert_email(e, "new")
    for needle in ("What happened", "Why it qualifies", "Deadline", "Maximum position", "Estimated payoff",
                   "Required action", "Hedge", "Source", "Status", "NOT guaranteed profit"):
        assert needle in html, needle


def test_run_sends_via_notifier_once(path, tmp_path, monkeypatch):
    sent = []
    from swingtrader.live import notify
    monkeypatch.setattr(notify.Notifier, "mail", lambda self, subj, html, dedupe_key=None: sent.append(dedupe_key) or "ok")
    monkeypatch.setattr(L, "UMH_ENABLED", True)   # dedup mechanics only; UMH itself is hold-only in production
    r1 = L.run(tmp_path, at(2026, 10, 4), email=True, log=lambda *_: None)
    n1 = len(sent)
    L.run(tmp_path, at(2026, 10, 4), email=True, log=lambda *_: None)
    assert n1 == len(r1["alerts"]) >= 2 and len(sent) == n1


# ---- serialization
def test_round_trip(path):
    L.add_event(path, L.umh_event(2026, 11, at(2026, 10, 4)), now=at(2026, 10, 4))
    rows = L.read(path)
    again = json.loads(json.dumps(rows))
    assert again == rows and set(L.EVENT_FIELDS) <= set(rows[0])
    assert L.fold(rows) .keys() == L.fold(again).keys()


# ---- ingest from fixtures shaped like the real watcher output
def test_ingest_tender_splitoff_roundup(tmp_path):
    (tmp_path / "tender-watch.jsonl").write_text(json.dumps(dict(
        date="2026-10-05", path="edgar/data/1/x.txt", cik="1", name="ACME INC", ticker="ACME", last_close=10.0,
        floor=10.5, kind="fixed", expires="2026-11-02", odd_lot="Y", nav=False, floor_gain=0.05, alert=True)) + "\n"
        + json.dumps(dict(date="2026-10-05", ticker="NOPE", alert=False)) + "\n")
    (tmp_path / "splitoff-watch.jsonl").write_text(
        json.dumps(dict(date="2026-10-02", parent="MDT", recv="MMED", expires="2026-10-09", per100=107.53, cap=4.5939,
                        url="u", odd_lot="Y", source="manual")) + "\n"
        + json.dumps(dict(entry="2026-10-02", parent="MDT", recv_px=19.6, parent_px=86.44, gain=0.0417, alert=True)) + "\n")
    (tmp_path / "roundup-watch.jsonl").write_text(
        json.dumps(dict(date="2026-10-02", ticker="VIVK", trade_date="2026-10-05", buy_by="2026-10-02", ratio=15.0,
                        last_close=0.3085, alert=True, sentence="rounded up", url="u", form="10-Q", filed="2026-08-19")) + "\n"
        + json.dumps(dict(checked="2026-10-02", ticker="ZCMD", ex_date="2026-10-02", ratio=2.0)) + "\n")
    (tmp_path / "roundup-orders.json").write_text(json.dumps({"VIVK-2026-10-05": {"acct": {"status": "ordered"}}}))
    evs = {e["family"]: e for e in L.ingest(tmp_path)}
    assert set(evs) == {"ODD_LOT_TENDER", "SPLIT_OFF", "REVERSE_SPLIT_ROUNDUP"}
    t = evs["ODD_LOT_TENDER"]
    assert t["maximum_position"] == 99 and t["estimated_gross_payoff"] == 49.5 and t["deadline"].startswith("2026-11-02T16")
    s = evs["SPLIT_OFF"]
    assert s["status"] == "ACTION_REQUIRED" and s["maximum_position"] == round(99 * 86.44, 2)
    r = evs["REVERSE_SPLIT_ROUNDUP"]
    assert r["security"] == "VIVK" and "ordered" in r["notes"] and r["deadline"].startswith("2026-10-02T16")
    # prospective rule applies to ingested items: VIVK's buy_by has passed on 2026-10-04, the others are open
    res = L.run(tmp_path, at(2026, 10, 4), email=False, log=lambda *_: None)
    assert any("VIVK" in x for x in res["refused"])
    folded = L.fold(L.read(tmp_path / L.LOG_NAME))
    assert any(k.startswith("ODD-LOT-TENDER") for k in folded) and any(k.startswith("SPLIT-OFF") for k in folded)


# ---- outcomes and report
def test_cpc_done_and_failed(path):
    L.add_event(path, ev(), now=at(2026, 10, 4))
    L.add_event(path, ev(issuer="B", security="B", status="ACTION_REQUIRED"), now=at(2026, 10, 4))
    L.done(path, "SPLIT-OFF:MDT:2026-10-02", pnl=250.0, costs=10.0, note="ok", now=at(2026, 10, 12))
    L.failed(path, "SPLIT-OFF:B:2026-10-02", "MISSED", note="forgot", now=at(2026, 10, 12))
    s = L.fold(L.read(path))
    a, b = s["SPLIT-OFF:MDT:2026-10-02"], s["SPLIT-OFF:B:2026-10-02"]
    assert a["status"] == "COMPLETED" and a["realized_pnl"] == 250.0 and a["realized_costs"] == 10.0
    assert a["realized_return"] == pytest.approx(0.024) and a["completion_date"] == "2026-10-12"
    assert b["status"] == "MISSED" and b["history"][-1]["note"] == "forgot"
    with pytest.raises(L.Refused):
        L.failed(path, "SPLIT-OFF:B:2026-10-02", "COMPLETED")


def test_report_too_early_then_annualized(path):
    L.add_event(path, ev(), now=at(2026, 10, 4))
    L.done(path, "SPLIT-OFF:MDT:2026-10-02", 250.0, 10.0, now=at(2026, 10, 12))
    r = L.report(L.read(path), at(2026, 10, 20))
    assert r["annualized_at_10k"] is None and r["annualized_note"] == "too early"
    assert r["classification"] == "PERSONAL-SCALE ECONOMICS (not scalable alpha)"
    assert r["total_pnl_after_tax"] == pytest.approx(156.0)
    L.add_event(path, ev(family="ODD_LOT_TENDER", issuer="ACME", security="ACME"), now=at(2026, 10, 5))
    L.done(path, "ODD-LOT-TENDER:ACME:2026-10-02", 100.0, 0.0, now=at(2026, 10, 13))
    r = L.report(L.read(path), at(2027, 1, 20))
    assert r["independent_completed"] == 2 and r["annualized_at_10k"] is not None
    assert r["best_event_share"] == pytest.approx(156 / 221, abs=1e-3)
    assert r["annualized_ex_best"] < r["annualized_at_10k"]
    assert r["correlation_note"] == "n/a"
    assert "Frozen gate" in L.format_report(r)


def test_digest_read_and_registry(tmp_path):
    from swingtrader.daily import testing
    assert L.digest_read(tmp_path, tmp_path)["n"] == 0
    assert any("cpc_ledger" in t.covers for t in testing.REGISTRY)


def test_umh_hold_only_no_events_and_excluded_from_report(tmp_path):
    """User decision 2026-10-04: UMH is hold-only, generates nothing, and never counts toward validation."""
    import datetime as _dt
    from swingtrader.daily import cpc_ledger as c
    assert c.UMH_ENABLED is False
    now = _dt.datetime(2026, 10, 1, 9, 0, tzinfo=c.ET)
    res = c.run(tmp_path, now=now, email=False, log=lambda *a: None)
    assert not any(str(e).startswith("UMH") for e in res["new"])
    ev = c.umh_event(2026, 11, now)                      # an old-style UMH record, e.g. written before the decision
    _, rec = c.add_event(tmp_path / c.LOG_NAME, ev, now)
    c.done(tmp_path / c.LOG_NAME, rec["event_id"], 50.0, 0.0, now=now)
    r = c.report(c.read(tmp_path / c.LOG_NAME), now=now)
    assert r["events"] == 0 and r["completed"] == 0
