"""Where is everything, what is configured, and what is missing.

Answers the questions you actually have on a fresh box: where does .env live,
which keys are set, can we reach Alpaca, will email work, is it scheduled.
Masks every secret it prints.
"""
import os, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent.parent
OK, BAD, MEH = "  ok  ", " MISS ", " warn "


def mask(v: str) -> str:
    if not v:
        return "(empty)"
    return f"{v[:4]}{'*' * max(0, min(len(v) - 4, 12))} ({len(v)} chars)"


def main():
    print(f"project   {ROOT}")
    envp = ROOT / ".env"
    print(f".env      {envp}")
    if not envp.exists():
        print(f"[{BAD}] .env does NOT exist here. Create it with:  make env")
        print("         (it is gitignored, so it survives git reset --hard)")
    else:
        st = envp.stat()
        print(f"[{OK}] exists, {st.st_size} bytes, mode {oct(st.st_mode)[-3:]}")
        if oct(st.st_mode)[-3:] not in ("600", "400", "640"):
            print(f"[{MEH}] readable by others; tighten with:  chmod 600 .env")

    from swingtrader.config import load_dotenv
    load_dotenv()

    print("\n--- credentials ---")
    required = {
        "ALPACA_API_KEY": "trading + market data (must start with PK for paper)",
        "ALPACA_SECRET_KEY": "trading + market data",
    }
    optional = {
        "RESEND_API_KEY": "email alerts (https://resend.com/api-keys)",
        "NOTIFY_EMAIL": "where alerts are sent",
        "NOTIFY_FROM": "sender; needs a Resend-verified domain",
    }
    missing = []
    for k, why in required.items():
        v = os.environ.get(k, "")
        print(f"[{OK if v else BAD}] {k:18} {mask(v):28} {why}")
        if not v:
            missing.append(k)
    for k, why in optional.items():
        v = os.environ.get(k, "")
        show = v if k in ("NOTIFY_EMAIL", "NOTIFY_FROM") else mask(v)
        print(f"[{OK if v else MEH}] {k:18} {show if v else '(not set)':28} {why}")

    key = os.environ.get("ALPACA_API_KEY", "")
    if key and not key.startswith("PK"):
        print(f"\n[{BAD}] ALPACA_API_KEY does not start with 'PK'. This is not a paper key;")
        print("         the broker will refuse to start. That guard is deliberate.")

    print("\n--- connectivity ---")
    if missing:
        print(f"[{BAD}] skipping Alpaca check - {', '.join(missing)} not set")
    else:
        try:
            from swingtrader.live.broker import PaperBroker
            b = PaperBroker()
            a, c = b.account(), b.clock()
            print(f"[{OK}] Alpaca paper: equity ${float(a.equity):,.2f}, "
                  f"market {'OPEN' if c.is_open else 'closed'}, next open {c.next_open}")
            pos, stops = b.positions(), b.stops_by_symbol()
            unprot = [s for s in pos if s not in stops]
            print(f"[{OK if not unprot else BAD}] {len(pos)} position(s), "
                  f"{len(stops)} stop(s)" + (f"  UNPROTECTED: {unprot}" if unprot else ""))
        except Exception as exc:
            print(f"[{BAD}] Alpaca: {type(exc).__name__}: {str(exc)[:140]}")

    print("\n--- email ---")
    from swingtrader.live.notify import Notifier
    n = Notifier(ROOT / "state")
    if n.enabled:
        print(f"[{OK}] configured: {n.sender} -> {n.to}")
        if n.sender.endswith("@resend.dev"):
            print(f"[{MEH}] using Resend's shared test sender. It ONLY delivers to the")
            print("         address that owns the Resend account. If alerts should reach a")
            print("         different mailbox, verify a domain and set NOTIFY_FROM to it.")
            print("         Prove it either way with:  make notify-test")
    else:
        print(f"[{MEH}] disabled: {n.reason}")

    print("\n--- schedule ---")
    try:
        out = subprocess.run(["systemctl", "--user", "list-timers", "swing-trader.timer",
                              "--no-pager"], capture_output=True, text=True, timeout=10)
        if "swing-trader" in out.stdout:
            print(f"[{OK}] systemd timer installed")
            for line in out.stdout.splitlines()[:3]:
                print(f"         {line}")
        else:
            raise FileNotFoundError
    except Exception:
        try:
            cr = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=10)
            if "run-live.sh" in cr.stdout:
                print(f"[{OK}] cron entries installed")
                for line in cr.stdout.splitlines():
                    if "run-live.sh" in line:
                        print(f"         {line}")
            else:
                print(f"[{MEH}] not scheduled anywhere. Install with:  make persist")
        except Exception:
            print(f"[{MEH}] not scheduled anywhere. Install with:  make persist")

    print("\n--- state ---")
    for name in ("book-reversion.json", "book-momentum.json"):
        p = ROOT / "state" / name
        print(f"[{OK if p.exists() else MEH}] state/{name}"
              f"{'' if p.exists() else '  (created on first run)'}")
    sl = ROOT / "logs" / "slippage.jsonl"
    print(f"[{OK if sl.exists() else MEH}] logs/slippage.jsonl"
          f"{'' if sl.exists() else '  (created on first fill)'}")
    if missing:
        print(f"\nNEXT: add {', '.join(missing)} to {envp}")


if __name__ == "__main__":
    main()
