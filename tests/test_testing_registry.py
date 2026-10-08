"""Standing rule: everything tested forward is in swingtrader/daily/testing.py REGISTRY (so it is on the weekly digest)."""
import json
import re
from pathlib import Path

import yaml

from swingtrader.daily import digest, testing

ROOT = Path(__file__).resolve().parents[1]


def _covered() -> set[str]:
    return {c for t in testing.REGISTRY for c in t.covers}


def test_every_module_with_a_state_log_is_registered():
    mods = [p.stem for p in (ROOT / "swingtrader/daily").glob("*.py")
            if re.search(r"^LOG_NAME\s*=", p.read_text(), re.M)]
    assert mods, "expected shadow modules with LOG_NAME"
    missing = sorted(set(mods) - _covered())
    assert not missing, f"add these to swingtrader/daily/testing.py REGISTRY (weekly digest): {missing}"


def test_every_shadow_config_key_is_registered():
    daily = yaml.safe_load((ROOT / "config.yaml").read_text())["daily"]
    keys = [k for k, v in daily.items() if v == "shadow"]
    assert keys
    missing = sorted(set(keys) - _covered())
    assert not missing, f"add these config keys to a REGISTRY entry's covers: {missing}"


def test_status_reads_logs_and_never_raises(tmp_path):
    (tmp_path / "insider-day.jsonl").write_text(
        json.dumps(dict(date="2026-10-05", sym="A", status="scored", ret_net=0.002, silence_days=None, usd=6e5)) + "\n"
        + json.dumps(dict(date="2026-10-05", sym="B", status="scored", ret_net=0.0, silence_days=5, usd=1e4)) + "\n")
    (tmp_path / "tender-watch.jsonl").write_text("not json\n" + json.dumps(dict(alert=True, date="2026-10-05")) + "\n")
    (tmp_path / "daily-2026-10-05.log").write_text("[fomc] SHADOW: would buy\n[oversold] x\n")
    st = {r["name"]: r for r in testing.status(tmp_path, tmp_path)}
    assert len(st) == len(testing.REGISTRY)
    assert st["Insider-day (ID3)"]["n"] == 2
    assert st["EV2: first insider buy in 2+ years"]["n"] == 1
    assert st["EV2 x buy >= $500k"]["n"] == 1
    assert st["Odd-lot tenders"]["n"] == 1
    assert st["FOMC-eve QQQ filler (F3)"]["n"] == 1
    assert st["M1 ID1: every insider buy, ADV >= $1M"]["n"] == 0          # pre-M1 rows are not ID1's forward base
    assert st["M1 N2: night leg on CPI/NFP mornings"]["n"] == 0
    assert all("line" in r for r in st.values())


def test_digest_shows_the_being_tested_section(tmp_path):
    d = dict(accounts={}, gates=[], whatif={}, proj={}, testing=testing.status(tmp_path, tmp_path))
    subj, html, text, _ = digest.render(d, charts=False)
    assert "Being tested" in text and "Being tested" in html
    assert all(t.name.split(" (")[0][:20] in text for t in testing.REGISTRY)


def test_au3_counts_only_tow_lines_and_f3_names_the_next_decision(tmp_path):
    (tmp_path / "daily-2026-10-05.log").write_text(
        "[night] scanned 3500 live names\n[night] tow shadow: A tow 3 w 0.10\n[night] data check\n")
    st = {r["name"]: r for r in testing.status(tmp_path, tmp_path)}
    assert st["Tug-of-war night tilt (AU3)"]["n"] == 1
    assert "next decision" in st["FOMC-eve QQQ filler (F3)"]["line"]
