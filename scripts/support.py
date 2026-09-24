"""Everything needed to debug the bot, in one paste-safe block.

  python scripts/support.py        (make support)

Secrets are never printed: no .env values except the on/off switches, and any
long token-like string in logs is masked. Account numbers show last 4 only.
"""
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TOKENISH = re.compile(r"[A-Za-z0-9_\-]{28,}")
ACCT = re.compile(r"\b\d{8,}\b")
SAFE_ENV = ("DAILY_LIVE", "DAILY_LIVE_CAPITAL", "DAILY_ROTH", "DAILY_ROTH_CAPITAL", "ROTH_LIMITED_MARGIN", "SCHWAB_CALLBACK_URL")
HAVE_ENV = ("ALPACA_API_KEY", "ALPACA_SECRET_KEY", "SCHWAB_APP_KEY", "SCHWAB_APP_SECRET",
            "SCHWAB_ACCOUNT_NUMBER", "RESEND_API_KEY", "NOTIFY_EMAIL")


def scrub(s: str) -> str:
    s = TOKENISH.sub(lambda m: m.group(0)[:4] + "…[masked]", s)
    return ACCT.sub(lambda m: "…" + m.group(0)[-4:], s)


def sh(cmd: str, n: int = 60) -> str:
    try:
        out = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60, cwd=ROOT)
        txt = (out.stdout + out.stderr).strip()
    except Exception as exc:
        txt = f"({exc})"
    lines = [l for l in txt.splitlines() if "Deprecat" not in l and "httpx2" not in l]
    return "\n".join(lines[-n:]) or "(nothing)"


def section(title: str, body: str) -> None:
    print(f"\n===== {title} =====")
    print(scrub(body))


def main():
    print(f"swing-trader support bundle  {dt.datetime.now().astimezone():%Y-%m-%d %H:%M %Z}  "
          f"(ET {dt.datetime.now(dt.timezone.utc).astimezone(__import__('zoneinfo').ZoneInfo('America/New_York')):%H:%M})")
    section("code version", sh("git log --oneline -3"))

    env = {}
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip("'\"")
    body = [f"{k}={env.get(k, '(unset)')}" for k in SAFE_ENV]
    body += [f"{k}: {'set' if env.get(k) else 'MISSING'}" for k in HAVE_ENV]
    section(".env (switches only; secrets shown as set/MISSING)", "\n".join(body))

    section("timers", sh("./scripts/sysd.sh list-timers swing-trader.timer daily-trader.timer "
                         "schwab-reminder.timer --no-pager 2>/dev/null || crontab -l 2>/dev/null | grep -E 'run-|reminder'"))
    for unit in ("daily-trader", "swing-trader", "schwab-reminder"):
        section(f"{unit}: last result",
                sh(f"./scripts/sysd.sh show {unit}.service -p Result -p ExecMainExitTimestamp -p ExecMainStatus 2>/dev/null"))
    section("schwab login", sh("./.venv/bin/python scripts/schwab_reminder.py", 5))
    section("daily book status (paper + live)", sh("./.venv/bin/python scripts/daily.py --status", 40))

    logs = sorted(ROOT.glob("logs/daily*-20*.log"))[-6:]
    errs = []
    for f in logs:
        for line in f.read_text(errors="replace").splitlines():
            if re.search(r"WARN|ERROR|Traceback|FAILED|REJECTED|rejected|failed|Exception", line):
                errs.append(f"{f.name}: {line}")
    section("warnings/errors in the last daily logs", "\n".join(errs[-40:]) or "(none)")
    if logs:
        section(f"tail of {logs[-1].name}", "\n".join(logs[-1].read_text(errors="replace").splitlines()[-40:]))
    section("journal: daily-trader (last 40)",
            sh("journalctl --user -u daily-trader -n 40 --no-pager 2>/dev/null || tail -n 40 logs/cron-daily.log 2>/dev/null"))
    section("journal: schwab-reminder (last 10)",
            sh("journalctl --user -u schwab-reminder -n 10 --no-pager 2>/dev/null || tail -n 10 logs/cron-reminder.log 2>/dev/null"))
    print("\n===== end: paste everything above =====")


if __name__ == "__main__":
    main()
