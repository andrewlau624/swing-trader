"""Split-off exchange-offer watch (Round 32 B2, research/drafts/study_round32_events.md) — ALERT ONLY, never trades.

A parent that splits off a subsidiary offers ~$107 of subsidiary stock for every $100 of its own shares (a 6-10%
discount, capped by an upper limit on the exchange ratio). These offers are oversubscribed and prorated, but a holder
of <= 99 parent shares who tenders all of them is accepted in full (odd-lot priority). 2016-25: 14 offers, all
oversubscribed with odd-lot priority; buying the parent 5 sessions before expiry and valuing the received shares at
the first close after expiry made a median +7.4% (12 of 14 > 0; worst −8.8%, Neogen's post-merger flowback).

Run once a weekday (with tender_watch): new SC TO-I filings that look like split-off exchange offers are logged to
state/splitoff-watch.jsonl and emailed; terms (value per $100, upper limit, expiry) come from the parent's Form 425
press releases, and `add` sets them (and the received ticker) by hand. Every open offer with complete terms is valued
at the last closes: implied gain = min(per100/100 x P/R, cap) x R / P − 1. Inside the entry window (3-5 sessions
before expiry) an offer with implied gain >= +1% is emailed with the exact steps. Tendering is manual at Schwab.

    python -m swingtrader.daily.splitoff_watch [DATE] [--no-email]
    python -m swingtrader.daily.splitoff_watch add PARENT RECV YYYY-MM-DD PER100 CAP [URL]
"""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

from .insider_shadow import _read, _sec_get, filing_days
from .tender_watch import YES, clean, header_company, idx_paths

LOG_NAME = "splitoff-watch.jsonl"
MIN_GAIN = 0.01
CO = r"([A-Z][A-Za-z0-9.&' -]{1,50}?,? (?:Inc\.|Corporation|Corp\.|Company|Holdings?,? Inc\.|Group,? Inc\.|plc|N\.V\.|Ltd\.|LLC|Splitco|SpinCo))"
RECV = re.compile(r"exchange[^.]{0,250}?shares of (?:Class [A-Z] )?common stock(?:,? par value [^,]{0,40},)? of " + CO)
NOT_SPLIT = re.compile(r"\b(?:options?|warrants?|notes|debentures|preferred)\b to (?:purchase|exchange)|eligible options|"
                       r"option exchange", re.I)
KEYS = re.compile(r"split-off|splitco|spinco|upper limit|exchange ratio", re.I)
PER100 = re.compile(r"\$\s?(1\d\d\.\d\d) of [^$]{0,120}?for (?:each|every) \$\s?100", re.I)
CAP = re.compile(r"upper limit of (\d+\.\d+)", re.I)
MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
EXP = re.compile(rf"(?:expire|expiration)[^.]{{0,120}}?({MONTHS}) (\d{{1,2}}), (\d{{4}})", re.I)


def detect(text: str) -> tuple[str, str] | None:
    """(issuer, received company or '?') when an SC TO-I offers another company's stock for the issuer's own."""
    t = clean(text)[:40000]
    if "exchange offer" not in t.lower() or NOT_SPLIT.search(t):
        return None
    issuer = (re.search(r"COMPANY CONFORMED NAME:\s*([^\n]+)", text) or [None, ""])[1].strip()
    m = RECV.search(t)
    if not m:
        return (issuer, "?") if KEYS.search(t) else None
    recv = m.group(1).strip()
    if issuer and recv.split()[0].lower().strip(",.") == issuer.split()[0].lower().strip(",."):
        return None
    return issuer, recv


def parse_terms(text: str) -> dict:
    t = clean(text)
    out = {}
    if m := PER100.search(t):
        out["per100"] = float(m.group(1))
    if m := CAP.search(t):
        out["cap"] = float(m.group(1))
    if m := EXP.search(t):
        try:
            out["expires"] = dt.datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%B %d %Y").date().isoformat()
        except ValueError:
            pass
    if YES.search(t):
        out["odd_lot"] = "Y"
    return out


def implied_gain(r: dict, p_parent: float, p_recv: float) -> float:
    """Value received per parent share / parent price − 1 at the given prices, with the upper limit applied."""
    ratio = min(r["per100"] / 100 * p_parent / p_recv, r["cap"])
    return ratio * p_recv / p_parent - 1


def in_window(sessions_left: int) -> bool:
    """3-5 sessions to expiry: late enough to match the study's entry, early enough to settle (T+1) and tender
    before Schwab's own deadline (1-2 business days before expiry)."""
    return 3 <= sessions_left <= 5


def instructions(r: dict, gain: float, pp: float, pr: float) -> str:
    return f"""SPLIT-OFF EXCHANGE OFFER: {r['parent']} -> {r['recv']}
Terms: ${r['per100']:.2f} of {r['recv']} stock per $100 of {r['parent']}, upper limit {r['cap']} {r['recv']} per {r['parent']} share.
At the last closes ({r['parent']} ${pp:.2f}, {r['recv']} ${pr:.2f}) one {r['parent']} share is worth {1 + gain:.3f}x in {r['recv']}:
implied gain {gain:+.1%}, about ${99 * pp * gain:,.0f} on 99 shares (capital ${99 * pp:,.0f}). Expires {r['expires']}.
History (2016-25, 14 offers): median +7.4%, 12 of 14 > 0, worst -8.8% (the received stock fell after delivery).

ONE-COMMAND BUY (you approve it): ssh in, cd ~/llm-trader, run   make splitoff-buy PARENT={r['parent']}
  (it re-checks the offer live, shows the plan, and buys only after you type {r['parent']}; then tender, step 3.)

HOW TO DO IT:
1. Own 99 or FEWER {r['parent']} shares IN TOTAL across all accounts (odd lots are counted per person).
2. Buy up to 99 {r['parent']} shares in ONE account (Roth first if it has the cash) with a limit near the last price.
   Buy at least 2 business days before Schwab's deadline (usually 1-2 business days before expiry): shares settle T+1.
3. Tender ALL of them: schwab.com > Accounts > Positions > {r['parent']} > Corporate actions / Voluntary reorganization
   (or call 1-800-435-4000: "tender my odd lot in the {r['parent']} exchange offer"). Certify the odd lot. Fee $0.
4. {r['recv']} shares arrive a few days after expiry. From the final pricing on you hold {r['recv']} risk; sell or keep.

What can go wrong: {r['recv']} falls after the exchange (tenderers dump the new shares: Neogen 2022 -8.8%); when the
upper limit is in effect the offer is usually extended 2 trading days; >= 100 shares in total -> prorated like everyone.
Filing: {r.get('url', '')}
"""


def entry_email(r: dict, gain: float, pp: float, pr: float) -> tuple[str, str]:
    """(subject, html) for an open offer in its entry window, in the shared email look."""
    from ..live import mail as M
    par, rec = r["parent"], r["recv"]
    capped = r["per100"] / 100 * pp / pr > r["cap"]
    blocks = [
        M.action("Act now", f"Buy up to 99 {par}, then tender for {rec}", f"make splitoff-buy PARENT={par}",
                 [f"On the server (ssh in, cd ~/llm-trader) run the command below. It re-checks the offer live, shows the "
                  f"plan and buys only after you type {par}. Then tender (step 2)."]),
        M.facts([("Offer", f"${r['per100']:.2f} of {rec} per $100 of {par}"),
                 ("Upper limit", f"{r['cap']} {rec} per {par} share" + (" (binding now)" if capped else "")),
                 (f"Last close {par} / {rec}", f"${pp:.2f} / ${pr:.2f}"),
                 ("Value per share now", f"{1 + gain:.3f}x ({gain:+.1%})"),
                 ("On 99 shares", f"about ${99 * pp * gain:,.0f} on ${99 * pp:,.0f}"),
                 ("Offer expires", r["expires"]), ("Schwab's deadline", "usually 1-2 business days earlier")]),
        M.steps([f"Buy: the command above (99 or fewer {par} IN TOTAL across all your accounts).",
                 f"The next business day (shares settled) tender ALL of them: schwab.com > Accounts > Positions > {par} > "
                 "Corporate actions / Voluntary reorganization, or call 1-800-435-4000. Certify the odd lot. Fee $0.",
                 f"{rec} shares arrive a few days after expiry. Sell them or keep them - from then on it's {rec} risk."], "Then"),
        M.fine(f"History (2016-25, 14 offers): median +7.4%, 12 of 14 made money, worst -8.8% (the received stock fell "
               f"after delivery: Neogen 2022). When the upper limit binds the offer may be extended 2 trading days. "
               f"Holding 100+ {par} in total means you are prorated like everyone else.")]
    if r.get("url"):
        blocks.append(M.link(r["url"], "Offer filing (SEC)"))
    return (f"Split-off: buy up to 99 {par} for {rec} ({gain:+.1%}) - act now",
            M.page("Split-off exchange offer", f"Buy up to 99 {par}, then tender", f"for {rec} · expires {r['expires']}", blocks))


def new_offer_email(r: dict) -> tuple[str, str]:
    from ..live import mail as M
    args = (f"{r['parent'] or 'PARENT'} RECV {r.get('expires') or 'YYYY-MM-DD'} {r.get('per100') or 'PER100'} "
            f"{r.get('cap') or 'CAP'} {r['url']}")
    return (f"New split-off offer: {r['name']} - set its ticker",
            M.page("Split-off exchange offer", "New offer found", r["name"], [
                M.action("One step so the bot can watch it", "Add the received company's ticker",
                         f"make splitoff-add ARGS='{args}'",
                         ["Replace RECV with the ticker of the shares you would receive (and any value left as a "
                          "placeholder, from the offer's press release). The bot then values it daily and emails you "
                          "with the buy command 3-5 sessions before expiry."], tone="info"),
                M.facts([("Value per $100", f"${r['per100']:.2f}" if r.get("per100") else "not found"),
                         ("Upper limit", str(r.get("cap") or "not found")), ("Expires", r.get("expires") or "not found"),
                         ("Odd-lot priority", "yes" if r.get("odd_lot") == "Y" else "check the offer")]),
                M.link(r["url"], "Offer filing (SEC)")]))


def _closes(syms: list[str], today: dt.date) -> dict[str, float]:
    from . import marketdata as md
    b = md.sip_daily(syms, today - dt.timedelta(days=10))
    return {s: float(v.close.iloc[-1]) for s, v in b.items() if len(v)}


def _sessions_left(expires: str, today: dt.date) -> int:
    from ..data import trading_days
    e = dt.date.fromisoformat(expires)
    return len([d for d in trading_days(today, e) if today <= d.date() < e])


def _press_terms(cik: str, since: dt.date) -> dict:
    """Terms from the parent's Form 425 filings since the SC TO-I (the SC TO-I incorporates the prospectus)."""
    sub = _sec_get(f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json")
    out: dict = {}
    try:
        f = json.loads(sub)["filings"]["recent"]
    except (TypeError, ValueError, KeyError):
        return out
    for i in range(min(len(f["form"]), 80)):
        if f["form"][i] != "425" or f["filingDate"][i] < str(since):
            continue
        a = f["accessionNumber"][i]
        t = _sec_get(f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{a.replace('-', '')}/{f['primaryDocument'][i]}") or ""
        for k, v in parse_terms(t).items():
            out.setdefault(k, v)
        if {"per100", "cap", "expires"} <= set(out):
            break
    return out


def add(state_dir: Path, parent: str, recv: str, expires: str, per100: float, cap: float, url: str = "") -> dict:
    r = dict(date=str(dt.date.today()), parent=parent.upper(), recv=recv.upper(), expires=expires, per100=per100,
             cap=cap, url=url, odd_lot="Y", source="manual")
    with (Path(state_dir) / LOG_NAME).open("a") as f:
        f.write(json.dumps(r) + "\n")
    return r


def open_offers(rows: list[dict], today: dt.date) -> list[dict]:
    """Latest complete record per parent whose expiry has not passed."""
    live: dict = {}
    for r in rows:
        if all(r.get(k) for k in ("parent", "recv", "per100", "cap", "expires")):
            live[r["parent"]] = r
    return [r for r in live.values() if dt.date.fromisoformat(r["expires"]) >= today]


def run(state_dir: Path, today: dt.date | None = None, email: bool = True, log=print) -> list[dict]:
    from ..data import trading_days
    from ..live.notify import Notifier
    from .news_judge import _cik_map
    path = Path(state_dir) / LOG_NAME
    seen = {r.get("path") for r in _read(path)}
    today = today or dt.date.today()
    sess = [d.date() for d in trading_days(today - dt.timedelta(days=10), today)]
    prev = [d for d in sess if d < today][-1]
    cik2tk = {str(v): k for k, v in _cik_map(Path(state_dir)).items()}
    new = []
    for day in filing_days(prev, today):
        q = (day.month - 1) // 3 + 1
        idx = _sec_get(f"https://www.sec.gov/Archives/edgar/daily-index/{day.year}/QTR{q}/form.{day:%Y%m%d}.idx")
        for p in idx_paths(idx or ""):
            if p in seen:
                continue
            sub = _sec_get(f"https://www.sec.gov/Archives/{p}") or ""
            d = detect(sub)
            if not d:
                continue
            cik, _ = header_company(sub)
            r = dict(date=str(day), path=p, url=f"https://www.sec.gov/Archives/{p}", cik=cik, name=f"{d[0]} -> {d[1]}",
                     parent=cik2tk.get(cik or ""), recv=None, **parse_terms(sub))
            if cik:
                r.update({k: v for k, v in _press_terms(cik, day).items() if k not in r})
            new.append(r)
            log(f"[splitoff] {day} NEW {r['name']} ({r['parent']}): " + str({k: r.get(k) for k in ('per100', 'cap', 'expires')}))
    with path.open("a") as f:
        for r in new:
            f.write(json.dumps(r) + "\n")
    note = Notifier(Path(state_dir)) if email else None
    if new and note:
        for r in new:
            note.mail(*new_offer_email(r))
    try:                                   # bookkeeping for buys you approved (never places an order)
        from .splitoff_buy import track
        track(state_dir, today, notify=(lambda subj, html: note.mail(subj, html)) if note else None, log=log)
    except Exception as exc:
        log(f"[splitoff] tracking failed: {str(exc)[:120]}")
    for r in open_offers(_read(path), today):
        px = _closes([r["parent"], r["recv"]], today)
        if r["parent"] not in px or r["recv"] not in px:
            continue
        g = implied_gain(r, px[r["parent"]], px[r["recv"]])
        left = _sessions_left(r["expires"], today)
        log(f"[splitoff] {r['parent']}->{r['recv']} expires {r['expires']} ({left} sessions): implied {g:+.2%}")
        if in_window(left) and g >= MIN_GAIN and not any(x.get("entry") and x.get("parent") == r["parent"]
                                                        and x.get("expires") == r["expires"] for x in _read(path)):
            with path.open("a") as f:     # one alert of record per offer (digest what-if: 99 x parent x gain)
                f.write(json.dumps(dict(entry=str(today), parent=r["parent"], expires=r["expires"], recv_px=px[r["recv"]],
                                        parent_px=px[r["parent"]], gain=round(g, 4), alert=True)) + "\n")
        if note and in_window(left) and g >= MIN_GAIN:
            note.mail(*entry_email(r, g, px[r["parent"]], px[r["recv"]]))
    return new


if __name__ == "__main__":
    import sys
    st = Path(__file__).resolve().parents[2] / "state"
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    if a and a[0] == "add":
        print(add(st, a[1], a[2], a[3], float(a[4]), float(a[5]), a[6] if len(a) > 6 else ""))
    else:
        run(st, dt.date.fromisoformat(a[0]) if a else None, email="--no-email" not in sys.argv)
