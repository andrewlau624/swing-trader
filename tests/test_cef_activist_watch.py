from swingtrader.daily import cef_activist_watch as c


def _hit(form, names):
    return {"_source": {"form": form, "display_names": names, "file_date": "2026-09-01", "adsh": "x"}}


def test_events_from_hits_picks_the_fund_subject():
    h = [_hit("SC 13D", ["Saba Capital Management, L.P.  (CIK 0001510281)", "Adams Diversified Equity Fund  (ADX)  (CIK 0000002230)"]),
         _hit("SC 13D/A", ["Saba Capital Management, L.P.  (CIK 0001510281)", "Some Trust  (STT)  (CIK 0000000001)"]),
         _hit("SC 13D", ["Karpus Investment  (CIK 1)", "Acme Widgets Inc  (ACME)  (CIK 2)"])]
    e = c.events_from_hits(h)
    assert [(x["sym"], x["act"]) for x in e] == [("ADX", "saba")]


def test_gate_counts_scored_only():
    rows = [dict(status="open"), dict(status="scored", excess=0.03), dict(status="scored", excess=0.01)]
    g = c.gate(rows)
    assert g["n"] == 2 and abs(g["mean_excess"] - 0.02) < 1e-12 and g["verdict"].startswith("shadowing")
