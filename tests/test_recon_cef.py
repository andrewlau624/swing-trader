import json

from swingtrader.daily import recon


def _w(p, rows):
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))


def test_cef_misses_keep_the_session_day_reason_over_a_later_missed_row(tmp_path):
    """A budget skip on the entry session followed by the next day's "missed" row is a budget miss, not a late signal."""
    _w(tmp_path / "cef-rv.jsonl", [dict(sym="A", signal="2026-10-23"), dict(sym="B", signal="2026-10-23")])
    _w(tmp_path / "cef-rv-live.jsonl", [
        dict(ts="2026-10-26T09:05:56-04:00", mode="live", cmd="buy", sym="A", signal="2026-10-23", order_id="1"),
        dict(ts="2026-10-26T09:05:56-04:00", mode="live", cmd="buy-skip", sym="B", signal="2026-10-23", reason="no budget"),
        dict(ts="2026-10-27T09:05:56-04:00", mode="live", cmd="missed", sym="B", signal="2026-10-23", session="2026-10-26",
             reason="entry session already passed; not chased")])
    out = recon.cef_section(tmp_path, tmp_path, ["2026-10-26", "2026-10-27"])
    assert (out["rule"], out["live"], out["both"]) == (2, 1, 1) and out["miss"] == {"buy-skip": 1}
