"""One look for every email (the weekly digest's): a navy header band, a white 600px card, an action box with the exact
command, then facts, steps and fine print. Inline styles only (email clients drop <style>).

    html = page("Odd-lot tender", "Buy up to 99 UTMD, then tender", "guaranteed $75.00 · +1.2% · expires Oct 7",
                [action("ACT TODAY", "Buy the odd lot", "make tender-buy ID=UTMD-2026-10-01", tone="act"),
                 facts([("Last close", "$74.10"), ("Expected gain", "~$89")]),
                 steps(["...", "..."]), fine("What can go wrong: ...")])

Every block takes plain text and escapes it; `html=True` on para() passes trusted markup through.
"""
from __future__ import annotations

import datetime as dt

INK, MUTE, LINE, ACC, UP, DOWN, WARN = "#1f2328", "#6e7781", "#d8dee4", "#0b5cad", "#1a7f37", "#cf222e", "#9a6700"
BAND, BAND_MUTE = "#0f2a44", "#a8bccf"
SANS = "-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif"   # unquoted: inside style='...'
SERIF = "Georgia,Times New Roman,serif"
MONO = "ui-monospace,Menlo,Consolas,monospace"
TONES = {"act": (UP, "#eef8f1"), "info": (ACC, "#eef4fb"), "warn": (DOWN, "#fff1f0"), "wait": (WARN, "#fff8e5")}


def esc(s) -> str:
    """HTML-escape, and send every non-ASCII character as an entity (·, −, ≥ survive any charset guess)."""
    t = str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return t.encode("ascii", "xmlcharrefreplace").decode()


def page(kicker: str, title: str, sub: str = "", blocks: list[str] = (), when: dt.datetime | None = None) -> str:
    when = when or dt.datetime.now()
    head = (f"<div style='background:{BAND};padding:22px 26px 20px'>"
            f"<div style='font-family:{SANS};font-size:13px;color:{BAND_MUTE};letter-spacing:.04em'>"
            f"{esc(kicker.upper())} &middot; {when:%a %b %-d, %Y}</div>"
            f"<div style='font-family:{SERIF};font-size:30px;line-height:1.2;color:#ffffff;margin-top:6px'>{esc(title)}</div>"
            + (f"<div style='font-family:{SANS};font-size:15px;color:{BAND_MUTE};margin-top:6px'>{esc(sub)}</div>" if sub else "")
            + "</div>")
    return (f"<div style='background:#eaeef2;padding:24px 10px'><div style='max-width:600px;margin:0 auto;"
            f"background:#ffffff;border:1px solid {LINE}'>{head}<div style='padding:4px 26px 28px'>"
            + "".join(blocks) + "</div></div></div>")


def action(lead: str, headline: str, command: str | None = None, lines: list[str] = (), tone: str = "act") -> str:
    """The box at the top: what to do, and the exact command to paste."""
    col, bg = TONES[tone]
    return (f"<div style='background:{bg};border-left:5px solid {col};padding:16px 20px;margin-top:24px'>"
            f"<div style='font-family:{SANS};font-size:12px;font-weight:700;letter-spacing:.06em;color:{col}'>{esc(lead.upper())}</div>"
            f"<div style='font-family:{SANS};font-size:20px;font-weight:700;color:{INK};margin:4px 0 6px'>{esc(headline)}</div>"
            + "".join(f"<div style='font-family:{SANS};font-size:15px;line-height:1.5;color:{INK}'>{esc(x)}</div>" for x in lines)
            + (f"<div style='font-family:{MONO};font-size:14px;background:#ffffff;border:1px solid {LINE};padding:8px 10px;"
               f"margin-top:10px;word-break:break-all;color:{INK}'>{esc(command)}</div>" if command else "")
            + "</div>")


def section(title: str, sub: str = "") -> str:
    return (f"<p style='margin:28px 0 10px;font-family:{SANS};font-size:17px;font-weight:700;color:{INK}'>{esc(title)}"
            + (f"<span style='display:block;font-size:14px;font-weight:400;color:{MUTE};margin-top:2px'>{esc(sub)}</span>" if sub else "")
            + "</p>")


def facts(rows: list[tuple[str, str]], title: str = "") -> str:
    """Label / value rows (values right-aligned, tabular figures)."""
    cell = f"font-family:{SANS};font-size:15px;color:{INK};padding:9px 0;border-bottom:1px solid {LINE};"
    body = "".join(f"<tr><td style='{cell}color:{MUTE}'>{esc(k)}</td>"
                   f"<td style='{cell}text-align:right;font-weight:600;font-variant-numeric:tabular-nums'>{esc(v)}</td></tr>"
                   for k, v in rows)
    return ((section(title) if title else "<div style='height:14px'></div>")
            + f"<table role='presentation' width='100%' cellspacing='0' cellpadding='0'>{body}</table>")


def steps(items: list[str], title: str = "How to do it") -> str:
    li = "".join(f"<tr><td style='font-family:{SANS};font-size:15px;font-weight:700;color:{ACC};vertical-align:top;"
                 f"padding:6px 10px 6px 0;width:18px'>{i}</td><td style='font-family:{SANS};font-size:15px;line-height:1.5;"
                 f"color:{INK};padding:6px 0'>{esc(x)}</td></tr>" for i, x in enumerate(items, 1))
    return section(title) + f"<table role='presentation' width='100%' cellspacing='0' cellpadding='0'>{li}</table>"


def para(text: str, muted: bool = False, html: bool = False) -> str:
    return (f"<p style='margin:12px 0 0;font-family:{SANS};font-size:{14 if muted else 15}px;line-height:1.5;"
            f"color:{MUTE if muted else INK}'>{text if html else esc(text)}</p>")


def bullets(items: list[str], title: str = "") -> str:
    return ((section(title) if title else "")
            + "".join(f"<div style='font-family:{SANS};font-size:15px;line-height:1.5;color:{INK};padding:3px 0 3px 14px;"
                      f"text-indent:-14px'>&bull;&nbsp;{esc(x)}</div>" for x in items))


def fine(text: str) -> str:
    """Muted fine print below a rule (what can go wrong, where the numbers come from)."""
    return (f"<p style='margin:26px 0 0;padding-top:14px;border-top:1px solid {LINE};font-family:{SANS};font-size:13px;"
            f"line-height:1.5;color:{MUTE}'>{esc(text)}</p>")


def link(url: str, label: str) -> str:
    return (f"<p style='margin:14px 0 0;font-family:{SANS};font-size:14px'>"
            f"<a href='{esc(url)}' style='color:{ACC}'>{esc(label)}</a></p>")


def code(text: str, title: str = "") -> str:
    """A log or raw output, monospace."""
    return ((section(title) if title else "")
            + f"<div style='font-family:{MONO};font-size:12px;white-space:pre-wrap;background:#f6f8fa;border:1px solid {LINE};"
              f"padding:10px;color:{INK}'>{esc(text)}</div>")
