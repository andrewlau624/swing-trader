"""Forced-flow discovery: an EDGAR form-type scanner for per-holder-capped, guaranteed-floor events.

The four known contractual families already have watchers (odd-lot tenders `tender_watch.py`, split-off
exchange offers `splitoff_watch.py`, reverse-split round-ups `roundup_watch.py`, thrift/DRIP in
`research/sim/cpc.py`). This module covers the OTHER form types that can carry a per-holder cap plus a
guaranteed floor: SC 14D-9, DEFM14C, 425, 8-K items 2.01/5.01, 25-NSE, S-4 and SC 13E3.

Run once a weekday (`make forced-flow-discovery`): pulls the trailing sessions' EDGAR daily form index
(Archives/edgar/daily-index/.../form.YYYYMMDD.idx), filters to those forms, resolves the primary document
(using per-CIK data.sec.gov/submissions for the 8-K item filter and for 25-NSE), runs the cap/floor
regexes reused from the existing watchers, and appends deduped candidates (by accession) to
`state/forced-flow-discovery.jsonl`. Discovery only: no book, no order, no alert, no live-state mutation.
The `alert` field is just the candidate flag the weekly digest reads; nothing acts on it.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

import numpy as np

from .insider_shadow import _read, _sec_get
from .roundup_watch import round_up_sentence
from .splitoff_watch import CAP, PER100
from .tender_watch import clean, terms

LOG_NAME = "forced-flow-discovery.jsonl"

FORMS = ("SC 14D-9", "SC 14D9", "DEFM14C", "425", "8-K", "25-NSE", "S-4", "SC 13E3")
EIGHTK_ITEMS = ("2.01", "5.01")
MAX_TEXT = 2_000_000        # cap the regex pass on a large S-4/425 full submission

_IDX_ROW = re.compile(r"^(.+?)\s{2,}(.+?)\s{2,}(\d+)\s+(\d{8})\s+(edgar/\S+)")
# A per-holder share cap ("each holder may tender up to 5,000 shares") -- new wording the existing
# split-off CAP ("upper limit of N.NNNN") does not cover.
_PER_HOLDER = re.compile(
    r"(?:per (?:holder|person|account|stockholder|shareholder)|each (?:holder|person|account|stockholder|"
    r"shareholder))[^.]{0,80}?(?:up to|not (?:more|greater) than|no more than|maximum of|max(?:imum)? of|"
    r"capped at|limited to)\s+(\d[\d,]*)\s+shares"
    r"|(?:up to|not (?:more|greater) than|no more than|maximum of|max(?:imum)? of)\s+(\d[\d,]*)\s+shares"
    r"[^.]{0,80}?per (?:holder|person|account|stockholder|shareholder)", re.I)


def _base_form(form: str) -> str:
    return form.strip().split("/", 1)[0].strip()


def parse_idx(text: str, forms: tuple[str, ...] = FORMS) -> list[dict]:
    """Rows (form, company, cik, date, path) of the wanted form types from one EDGAR daily form.idx.

    Includes /A amendments (their base form is wanted) but not siblings such as 8-K12B. Generalizes the
    single-form `tender_watch.idx_paths`.
    """
    want = {_base_form(f) for f in forms}
    out = []
    for line in text.splitlines():
        m = _IDX_ROW.match(line)
        if not m:
            continue
        form = m.group(1).strip()
        if _base_form(form) in want:
            out.append(dict(form=form, company=m.group(2).strip(), cik=m.group(3),
                            date=m.group(4), path=m.group(5)))
    return out


def accession_of(path: str) -> str | None:
    """The accession number inside an index file name (edgar/data/CIK/ACC.txt -> ACC)."""
    m = re.search(r"/([0-9]{10}-[0-9]{2}-[0-9]{6})\.txt$", path)
    return m.group(1) if m else None


def submission_index(sub: dict) -> dict[str, dict]:
    """accession -> (form, items, primary document, filing date) from a submissions JSON `recent` block."""
    r = (sub or {}).get("filings", {}).get("recent", {}) or {}
    n = len(r.get("accessionNumber", []))
    out = {}
    for i, acc in enumerate(r.get("accessionNumber", [])):
        out[acc] = dict(form=(r.get("form") or [""] * n)[i],
                        items=(r.get("items") or [""] * n)[i] or "",
                        primary=(r.get("primaryDocument") or [""] * n)[i] or "",
                        date=(r.get("filingDate") or [""] * n)[i])
    return out


def primary_url(cik: str, accession: str, primary: str) -> str:
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/{primary}"


def per_holder_cap(text: str) -> float | None:
    m = _PER_HOLDER.search(text)
    if not m:
        return None
    return float((m.group(1) or m.group(2)).replace(",", ""))


def flag(text: str) -> dict:
    """Cap + guaranteed-floor read of a primary document (plain text). Pure; no network.

    A candidate is a guaranteed floor (fixed price or Dutch low end) together with at least one
    per-holder cap/priority mechanism (numeric cap, odd-lot priority, or a fractional round-up).
    """
    t = clean(text[:MAX_TEXT])
    tt = terms(text[:MAX_TEXT])
    floor = float(tt["floor"]) if np.isfinite(tt["floor"]) else None
    m = CAP.search(t)
    cap = float(m.group(1)) if m else per_holder_cap(t)
    p100 = PER100.search(t)
    ru = round_up_sentence(text[:MAX_TEXT])
    capped = []
    if cap is not None:
        capped.append("per_holder_cap")
    if tt["odd_lot"] == "Y":
        capped.append("odd_lot")
    if ru:
        capped.append("round_up")
    return dict(floor=floor, floor_kind=tt["kind"], odd_lot=tt["odd_lot"], cap=cap,
                per100=float(p100.group(1)) if p100 else None, nav=bool(tt["nav"]),
                round_up=bool(ru), round_up_sentence=ru, capped=capped,
                candidate=bool(floor is not None and capped and not tt["nav"]))


def _sessions_before(today: dt.date, days: int) -> list[dt.date]:
    from ..data import trading_days
    cal = [d.date() for d in trading_days(today - dt.timedelta(days=20), today)]
    return [d for d in cal if d < today][-days:]


def run(state_dir: Path, today: dt.date | None = None, days: int = 3, limit: int | None = None,
        sessions: list[dt.date] | None = None, write: bool = True, log=print) -> dict:
    """Scan the trailing sessions' daily indexes; append deduped candidates (unless `write=False`).

    `limit` bounds the rows resolved in one pass (submissions + primary-doc fetches). Never sends mail,
    never trades; `write=False` is the dry run.
    """
    path = Path(state_dir) / LOG_NAME
    seen = {r.get("accession") for r in _read(path) if r.get("accession")}
    today = today or dt.date.today()
    sessions = sessions if sessions is not None else _sessions_before(today, days)
    sub_cache: dict[str, dict] = {}
    got: set[str] = set()
    rows: list[dict] = []
    n_rows = n_8k = n_doc = 0

    def subs(cik: str) -> dict:
        if cik not in sub_cache:
            t = _sec_get(f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json")
            sub_cache[cik] = json.loads(t) if t else {}
        return sub_cache[cik]

    stop = False
    for day in sessions:
        if stop:
            break
        q = (day.month - 1) // 3 + 1
        idx = _sec_get(f"https://www.sec.gov/Archives/edgar/daily-index/{day.year}/QTR{q}/form.{day:%Y%m%d}.idx") or ""
        for r in parse_idx(idx):
            acc = accession_of(r["path"])
            if not acc or acc in seen or acc in got:
                continue
            if limit and n_rows >= limit:
                stop = True
                break
            n_rows += 1
            form, cik = r["form"], r["cik"]
            url = f"https://www.sec.gov/Archives/{r['path']}"
            if _base_form(form) in ("8-K", "25-NSE"):
                meta = submission_index(subs(cik)).get(acc, {})
                if form == "8-K":
                    items = [x.strip() for x in meta.get("items", "").replace(";", ",").split(",") if x.strip()]
                    if not any(it.startswith(EIGHTK_ITEMS) for it in items):
                        continue
                    n_8k += 1
                if meta.get("primary"):
                    url = primary_url(cik, acc, meta["primary"])
            text = _sec_get(url)
            n_doc += 1
            if text is None:
                text = _sec_get(f"https://www.sec.gov/Archives/{r['path']}") or ""
            f = flag(text)
            got.add(acc)
            rec = dict(date=str(day), form=form, company=r["company"], cik=cik, accession=acc,
                       path=r["path"], primary=url, **f)
            rec["alert"] = rec["candidate"]
            rows.append(rec)
            log(f"[forced-flow] {day} {form} {r['company'][:40]}: floor {rec['floor']} cap {rec['cap']} "
                f"{rec['capped']}{'  ** candidate **' if rec['candidate'] else ''}")

    if write and rows:
        with path.open("a") as fh:
            for rec in rows:
                fh.write(json.dumps(rec) + "\n")
    hits = [r for r in rows if r["candidate"]]
    log(f"[forced-flow] sessions {[str(s) for s in sessions]}: {n_rows} rows, {n_8k} 8-K item 2.01/5.01, "
        f"{n_doc} docs, {len(hits)} candidates, {len(rows) if write else 0} appended"
        f"{'' if write else ' (dry run)'}")
    return dict(sessions=[str(s) for s in sessions], rows=n_rows, eightk=n_8k, docs=n_doc,
                candidates=len(hits), parsed=len(rows), written=bool(write))


if __name__ == "__main__":
    import sys
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    day = dt.date.fromisoformat(args[0]) if args else None
    lim = next((int(a.split("=", 1)[1]) for a in sys.argv[1:] if a.startswith("--limit=")), None)
    ndays = next((int(a.split("=", 1)[1]) for a in sys.argv[1:] if a.startswith("--days=")), 3)
    run(Path(__file__).resolve().parents[2] / "state", day, days=ndays, limit=lim,
        write="--dry-run" not in sys.argv)
