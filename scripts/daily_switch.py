"""Turn real-money trading of the daily book on or off.

  python scripts/daily_switch.py on     # DAILY_LIVE=on in .env (asks to confirm)
  python scripts/daily_switch.py off    # remove it (warns if the live book holds anything)
  python scripts/daily_switch.py check  # connect to the live account, change nothing

The paper book keeps running either way, so paper vs real fills stay comparable.
"""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from swingtrader.config import Config, ROOT, get_env
from swingtrader.daily.book import DailyBook, book_file

ENV = ROOT / ".env"
LINE = re.compile(r'^DAILY_LIVE=.*$', re.M)


def set_live(on: bool) -> None:
    """The switch lives in .env: gitignored, so `make pull` (git reset --hard)
    can never flip real money on or off behind your back."""
    val = f"DAILY_LIVE={'on' if on else 'off'}"
    s = ENV.read_text() if ENV.exists() else ""
    s = LINE.sub(val, s) if LINE.search(s) else s.rstrip("\n") + ("\n" if s else "") + val + "\n"
    ENV.write_text(s)
    import os
    os.environ["DAILY_LIVE"] = "on" if on else "off"


def check() -> bool:
    k, s = get_env("ALPACA_LIVE_API_KEY"), get_env("ALPACA_LIVE_SECRET_KEY")
    if not (k and s):
        print("ALPACA_LIVE_API_KEY / ALPACA_LIVE_SECRET_KEY are not in .env.")
        print("Get them from app.alpaca.markets -> switch to the LIVE account -> API keys,")
        print("then add both lines to .env on the machine that runs the bot.")
        return False
    from swingtrader.live.broker import PaperBroker
    try:
        b = PaperBroker(paper=False, key=k, secret=s)
        a = b.account()
    except Exception as exc:
        print(f"cannot connect to the live account: {exc}"); return False
    mult = float(a.multiplier or 1)
    print(f"LIVE account {str(a.account_number)[:3]}***  status {a.status}")
    print(f"  equity ${float(a.equity):,.2f}   cash ${float(a.cash):,.2f}   "
          f"margin multiplier {mult:g} (4 = leverage-enabled: full intraday leg)")
    print(f"  open positions {len(b.positions())}")
    ok = True
    if mult < 2:
        print("  PROBLEM: not a margin account. This book sells at the open and re-buys at")
        print("  the close with the same unsettled cash; in a cash account that is a")
        print("  good-faith violation. Enable margin in the Alpaca dashboard (needs >= $2k).")
        ok = False
    if a.trading_blocked or a.account_blocked:
        print("  PROBLEM: account is blocked from trading."); ok = False
    if b.positions():
        print("  NOTE: positions already exist. The daily book never trades a symbol it")
        print("  does not own, so they are left alone, but they are not part of the experiment.")
    return ok


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    cfg = Config.load()
    accts = cfg.daily.resolved_accounts()
    if cmd == "check":
        check(); print(f"\naccounts trading: {accts}"); return
    if cmd == "on":
        if "live" in accts:
            print("real money is already ON:", accts); return
        if not check():
            sys.exit("\nnot switching on.")
        print("\nThis places REAL orders with REAL money from the next scheduled run:")
        print(f"  IBS leg {cfg.daily.ibs_weight:.0%} + overnight leg {cfg.daily.night_weight:.0%} of the account,")
        print(f"  intraday QQQ leg {'live (equity >= $' + format(cfg.daily.daytrade_min_equity, ',.0f') + ')' if cfg.daily.daytrade_mode == 'auto' else 'OFF'}.")
        if input('Type REAL MONEY to confirm: ').strip() != "REAL MONEY":
            sys.exit("not confirmed; nothing changed.")
        set_live(True)
        print(f"done: DAILY_LIVE=on in .env. accounts trading: {Config.load().daily.resolved_accounts()}")
        print("check it tomorrow with: make daily-status")
        return
    if cmd == "off":
        if "live" not in accts:
            print("real money is already OFF:", accts); return
        b = DailyBook.load(ROOT / "state", 0.0, book_file("live"))
        if b.positions or b.open_orders():
            print(f"WARNING: the live book still holds {sorted(b.positions)} "
                  f"with {len(b.open_orders())} open order(s).")
            print("Switching off stops managing them: overnight names will NOT be sold at")
            print("the open. Safest: switch off after the 09:50 ET run, when the overnight leg")
            print("is flat, and sell any IBS ETFs by hand in the Alpaca app.")
            if input("Type OFF ANYWAY to continue: ").strip() != "OFF ANYWAY":
                sys.exit("nothing changed.")
        set_live(False)
        print(f"done: DAILY_LIVE=off in .env. accounts trading: {Config.load().daily.resolved_accounts()}")
        return
    sys.exit(__doc__)


if __name__ == "__main__":
    main()
