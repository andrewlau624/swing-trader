"""Weekly digest email: balances, gates, what each shadow idea would have made, and 1/3/5-year
projections with vs without the levers (swingtrader/daily/digest.py).

  python scripts/weekly_digest.py           # print only     (make weekly)
  python scripts/weekly_digest.py --send    # print + email to NOTIFY_EMAIL (Resend)   (make weekly-send)

Optional .env: DIGEST_TAXABLE_MONTHLY=<$ you add to the taxable account each month> (default 0).
"""
import argparse
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from swingtrader.config import ROOT, Config, get_env  # noqa: E402
from swingtrader.daily import digest  # noqa: E402
from swingtrader.live.notify import Notifier  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--send", action="store_true", help="also email it")
    ap.add_argument("--scheduled", action="store_true",
                    help="the Saturday timer: send at most once per ISO week (a manual --send always sends)")
    a = ap.parse_args(argv)
    d = Config.load().daily
    data = digest.build(ROOT / "state", ROOT / "logs", d.start_equity, d.conviction_weight,
                        float(get_env("DIGEST_TAXABLE_MONTHLY") or 0))
    subj, html, text = digest.render(data)
    print(subj); print(); print(text)
    if a.send:
        week = dt.date.today().isocalendar()
        key = f"digest-{week[0]}-{week[1]}" if a.scheduled else f"digest-manual-{dt.datetime.now():%Y%m%d%H%M%S}"
        print("\n" + Notifier(ROOT / "state").send(subj, html, dedupe_key=key))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
