"""Odd-lot tender watch (Round 31, research/drafts/study_oddlot_tenders.md) — ALERT ONLY, never trades.

An oversubscribed issuer tender prorates every holder of >= 100 shares, but when the offer grants odd-lot
priority a holder of <= 99 shares who tenders all of them is bought in full. 2016-26: cash offers with odd-lot
priority whose guaranteed price (fixed, or the low end of a Dutch range) was >= 1% above the market made money
every time (14-15 deals, median +5.5-6.3%, ~$90-150 per deal on <= 99 shares).

Run once a weekday (`make tender-watch`): reads the previous session-days' new SC TO-I filings from EDGAR's daily
index, extracts the price terms and the odd-lot clause, compares the floor with the last close, and logs every
candidate to state/tender-watch.jsonl; candidates with floor >= +1% and explicit priority are emailed (Notifier).
Tendering is a manual Schwab election; the 99-share limit counts ALL of the owner's accounts together.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
from pathlib import Path

import numpy as np

from .insider_shadow import _read, _sec_get, filing_days

LOG_NAME = "tender-watch.jsonl"
MONEY = r"\$\s?(\d[\d,]*\.\d{2,4})"
MIN_FLOOR = 0.01
BAD = ("par value", "dividend", "exercise price", "conversion price", "warrant", "liquidation preference")
YES = re.compile(r"odd[ -]lots?\W{0,3} first\b|odd[ -]lot[^.]{0,300}?(priority|first (?:purchase|accept)|not be subject to (?:the )?pro ?ration|"
                 r"without pro ?ration|accepted in full|before (?:pro ?ration|purchasing))|"
                 r"(priority|first purchase|accept all)[^.]{0,200}?odd[ -]lot", re.I)
NO = re.compile(r"odd[ -]lot[^.]{0,200}?(still|also|will be|are) subject to pro ?ration|"
                r"no (?:priority|preference) (?:for|to) odd", re.I)


def _num(x: str) -> float:
    return float(x.replace(",", ""))


def clean(text: str) -> str:
    t = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(t))


def terms(text: str) -> dict:
    """Price terms and odd-lot clause of an offer to purchase (plain text)."""
    t = clean(text)
    rng = re.search(r"not (?:greater|more) than " + MONEY + r"[^$]{0,40}(?:nor|and not|or|and) (?:less|lower) than "
                    + MONEY, t, re.I)
    lo = hi = fixed = np.nan
    if rng:
        a, b = _num(rng.group(1)), _num(rng.group(2)); lo, hi = min(a, b), max(a, b)
    else:
        for m in re.finditer(r"(?:at|for) a (?:purchase |cash )?price of " + MONEY + r",? (?:per|a) [Ss]hare", t):
            if not any(w in t[max(0, m.start() - 25):m.end()].lower() for w in BAD):
                fixed = _num(m.group(1)); break
    nav = bool(re.search(r"(?:\d{2}(?:\.\d+)?%|percent) of (?:the )?(?:\w+ )?(?:net asset value|NAV)", t, re.I))
    odd = "N" if NO.search(t) else "Y" if YES.search(t) else "none"
    floor = fixed if np.isfinite(fixed) else lo
    exp = None
    m = re.search(r"expire[sd]? (?:at|on) [^;]{0,120}?(?:on|,) (?:\w+day, )?(January|February|March|April|May|June|July|August|"
                  r"September|October|November|December) (\d{1,2}), (\d{4})", t, re.I)
    if m:
        try:
            exp = dt.datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%B %d %Y").date().isoformat()
        except ValueError:
            exp = None
    return dict(lo=lo, hi=hi, fixed=fixed, nav=nav, odd_lot=odd, floor=floor, expires=exp,
                kind="dutch" if np.isfinite(lo) else "fixed" if np.isfinite(fixed) else "unknown")


def header_company(sub: str) -> tuple[str | None, str | None]:
    """(subject company CIK, conformed name) from an EDGAR full-submission header."""
    m = re.search(r"SUBJECT COMPANY:.*?COMPANY CONFORMED NAME:\s*(.+?)\n.*?CENTRAL INDEX KEY:\s*(\d+)", sub, re.S)
    return (m.group(2).lstrip("0"), m.group(1).strip()) if m else (None, None)


def idx_paths(idx_text: str, form: str = "SC TO-I") -> list[str]:
    out = []
    for line in idx_text.splitlines():
        if line.startswith(form + " ") and not line.startswith(form + "/A"):
            m = re.search(r"(edgar/data/\S+\.txt)", line)
            if m:
                out.append(m.group(1))
    return sorted(set(out))


def candidate(t: dict, last_close: float | None) -> dict:
    g = (t["floor"] / last_close - 1) if (last_close and np.isfinite(t["floor"])) else np.nan
    alert = bool(np.isfinite(g) and g >= MIN_FLOOR and t["odd_lot"] == "Y" and not t["nav"])
    return dict(floor_gain=None if not np.isfinite(g) else round(float(g), 4), alert=alert)


def instructions(r: dict) -> str:
    """The full how-to for one alert (plain text, goes in the email)."""
    tk, floor, close = r["ticker"], r["floor"], r["last_close"]
    exp = r.get("expires") or "see the offer document (link below)"
    price = (f"${floor:.2f} cash per share (fixed)" if r.get("kind") == "fixed" else
             f"at least ${floor:.2f} (Dutch auction ${r.get('lo'):.2f}-${r.get('hi'):.2f}; odd lots get the final price, "
             f"which is never below ${floor:.2f})")
    gain = 99 * (floor - close)
    oid = f"{tk}-{r.get('date', '')}"
    return f"""ODD-LOT TENDER: {tk} ({r['name']})
ONE-COMMAND BUY (you approve it): ssh in, cd ~/llm-trader, run   make tender-buy ID={oid}
  (it re-checks the deal, shows the plan, and buys only after you type {tk}; then do step 3 below.)
Offer: {price}. Last close ${close:.2f} -> guaranteed floor +{r['floor_gain']:.1%}, about ${gain:,.0f} on 99 shares.
Offer expires: {exp}.  Schwab's own deadline is usually 1 business day EARLIER - use that.

HOW TO DO IT (each step matters):
1. Check your TOTAL {tk} shares across Brokerage + Roth + anything else: you must own 99 or FEWER in total
   (an odd lot is counted per person). If you already own some, buy only enough to reach 99.
2. Buy up to 99 shares in ONE account - prefer the ROTH if it has the cash (the gain is tax-free there) - with a
   LIMIT order at or below ${floor * 0.99:.2f} (keeps >= 1% of room). Do not chase: at ${floor:.2f} or above, skip it.
   Buy at least 2 business days before Schwab's deadline: the shares must settle (T+1) before you can tender.
3. Tender ALL of them once they settle (the next business day):
   schwab.com > Accounts > Positions > {tk} > "Corporate actions"/"Voluntary reorganization" (or call Schwab
   1-800-435-4000 and say "I want to tender my odd lot in the {tk} issuer tender offer").
   - Tender ALL your shares (a partial tender loses odd-lot priority).
   - Tick / say "ODD LOT certification: I own fewer than 100 shares".
   - Dutch auction: choose "tender at the PURCHASE PRICE determined by the offer" (not a specific price).
   - Do NOT make it a conditional tender.
4. Write down Schwab's confirmation number. Fee should be $0 (voluntary reorganization).
5. Do not sell or move the shares until the offer closes. Cash usually arrives 2-5 business days after expiry.

What can go wrong: the company withdraws the offer (rare) -> you keep the shares at market price, so sell or hold;
you hold >= 100 shares in total -> you are prorated like everyone else; you miss Schwab's deadline -> you hold
the stock after the offer, which often drops. Taxable account: the gain is a short-term capital gain.

Offer document: https://www.sec.gov/Archives/{r['path']}
"""


def offer_email(r: dict, reminder: bool = False) -> tuple[str, str]:
    """(subject, html) for one alerted offer, in the shared email look."""
    from ..live import mail as M
    tk, floor, close = r["ticker"], float(r["floor"]), float(r["last_close"])
    exp = r.get("expires") or "see the offer document"
    oid = f"{tk}-{r.get('date', '')}"
    price = (f"${floor:.2f} cash (fixed)" if r.get("kind") == "fixed" else
             f"at least ${floor:.2f} (Dutch ${r.get('lo'):.2f}-${r.get('hi'):.2f})")
    blocks = [
        M.action("Deadline soon - if you already tendered, ignore this" if reminder else "Act today",
                 f"Buy up to 99 {tk}, then tender them",
                 "make tender-buy ID=" + oid,
                 [f"On the server (ssh in, cd ~/llm-trader) run the command below. It re-checks the deal, shows the plan "
                  f"and buys only after you type {tk}. Then tender (step 2)."], tone="wait" if reminder else "act"),
        M.facts([("Offer", price), ("Last close", f"${close:.2f}"), ("Guaranteed gain", f"+{r['floor_gain']:.1%}"),
                 ("On 99 shares", f"about ${99 * (floor - close):,.0f}"), ("Offer expires", exp),
                 ("Schwab's deadline", "usually 1 business day earlier")]),
        M.steps([f"Buy: the command above (99 or fewer {tk} shares IN TOTAL across all your accounts; Roth first).",
                 f"The next business day (shares settled) tender ALL of them: schwab.com > Accounts > Positions > {tk} > "
                 "Corporate actions / Voluntary reorganization, or call 1-800-435-4000.",
                 "Tick the odd-lot certification (fewer than 100 shares). Dutch auction: tender 'at the purchase price'. "
                 "Not a conditional tender.",
                 "Keep the confirmation number. Fee $0. Don't sell until the offer closes; cash arrives 2-5 business days "
                 "after expiry."], "Then"),
        M.fine("What can go wrong: the company withdraws the offer (you keep the shares at market); you hold 100+ shares "
               "in total (prorated like everyone); you miss Schwab's deadline (you hold the stock after the offer, which "
               "often drops). Taxable account: a short-term gain. History 2016-26: every qualifying offer made money."),
        M.link(f"https://www.sec.gov/Archives/{r['path']}", "Offer document (SEC)")]
    subj = (f"REMINDER {tk} odd-lot tender: deadline {exp}" if reminder else
            f"Odd-lot tender: buy up to 99 {tk} (+{r['floor_gain']:.1%}) - act today")
    return subj, M.page("Odd-lot tender", f"Buy up to 99 {tk}, then tender", f"{r['name']} · expires {exp}", blocks)


def reminders(rows: list[dict], today: dt.date) -> list[dict]:
    """Alerted offers whose expiry is 1-3 days away (a reminder each of those days)."""
    out = []
    for r in rows:
        if r.get("alert") and r.get("expires"):
            left = (dt.date.fromisoformat(r["expires"]) - today).days
            if 1 <= left <= 3:
                out.append(r)
    return out


def run(state_dir: Path, today: dt.date | None = None, email: bool = True, log=print) -> list[dict]:
    from . import marketdata as md
    from ..data import trading_days
    from ..live.notify import Notifier
    from .news_judge import _cik_map
    path = Path(state_dir) / LOG_NAME
    seen = {r["path"] for r in _read(path)}
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
            cik, name = header_company(sub)
            tk = cik2tk.get(cik or "")
            t = terms(sub)
            close = None
            if tk:
                b = md.sip_daily([tk.replace("-", ".")], today - dt.timedelta(days=10)).get(tk.replace("-", "."))
                close = float(b.close.iloc[-1]) if b is not None and len(b) else None
            r = dict(date=str(day), path=p, cik=cik, name=name, ticker=tk, last_close=close,
                     **{k: (None if isinstance(v, float) and not np.isfinite(v) else v) for k, v in t.items()},
                     **candidate(t, close))
            new.append(r)
            log(f"[tender] {day} {tk or '?'} {name}: floor {r['floor']} vs close {close} -> "
                f"{r['floor_gain']} odd-lot {r['odd_lot']}{'  ** ALERT **' if r['alert'] else ''}")
    with path.open("a") as f:
        for r in new:
            f.write(json.dumps(r) + "\n")
    hits = [r for r in new if r["alert"]]
    if hits and email:
        for r in hits:
            Notifier(Path(state_dir)).mail(*offer_email(r))
    try:                                   # bookkeeping for buys you approved (never places an order)
        from .tender_buy import track
        note = Notifier(Path(state_dir)) if email else None
        track(state_dir, today, notify=(lambda subj, html: note.mail(subj, html)) if note else None, log=log)
    except Exception as exc:
        log(f"[tender] tracking failed: {str(exc)[:120]}")
    due = reminders(_read(path), today)
    if due and email:
        for r in due:
            Notifier(Path(state_dir)).mail(*offer_email(r, reminder=True))
    log(f"[tender] {len(new)} new SC TO-I, {len(hits)} odd-lot alerts")
    return new


if __name__ == "__main__":
    import sys
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    day = dt.date.fromisoformat(args[0]) if args else None
    run(Path(__file__).resolve().parents[2] / "state", day, email="--no-email" not in sys.argv)
