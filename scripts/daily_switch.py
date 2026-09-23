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
    cfg = Config.load()
    if cfg.daily.live_broker == "schwab":
        return check_schwab()
    return check_alpaca_live()


def check_schwab() -> bool:
    from swingtrader.daily.brokers import SchwabAdapter, schwab_token_age_s
    if not (get_env("SCHWAB_APP_KEY") and get_env("SCHWAB_APP_SECRET")):
        print("SCHWAB_APP_KEY / SCHWAB_APP_SECRET are not in .env.")
        print("developer.schwab.com -> Dashboard -> your app -> App Key and Secret.")
        return False
    age = schwab_token_age_s()
    if age is None:
        print("no Schwab login yet - run: make schwab-login"); return False
    print(f"Schwab login age {age/86400:.1f} days (dies at 7; renew with make schwab-login)")
    try:
        b = SchwabAdapter(); a = b.account(); pos = b.positions()
    except Exception as exc:
        print(f"cannot reach the Schwab account: {exc}"); return False
    print(f"LIVE (Schwab) account ...{str(a.account_number)[-4:]}  type {a.account_type}")
    print(f"  equity ${a.equity:,.2f}   cash ${a.cash:,.2f}   buying power ${a.buying_power:,.2f}"
          f"   est. intraday multiplier {a.multiplier:g}")
    print(f"  open positions {len(pos)}")
    from swingtrader.daily.book import DailyBook, book_file
    from swingtrader.config import ROOT
    own = set(DailyBook.load(ROOT / "state", 0.0, book_file("live")).positions)
    foreign = sum(abs(float(p.qty) * float(p.current_price or 0)) for s, p in pos.items() if s not in own)
    free = a.equity - foreign
    env_cap = (get_env("DAILY_LIVE_CAPITAL") or "").strip()
    cap = float(env_cap) if env_cap and env_cap.lower() not in ("none", "null", "off") \
        else Config.load().daily.live_capital
    use = min(free, cap) if cap else free
    print(f"  your other holdings ${foreign:,.2f}  ->  FREE for the bot ${free:,.2f}"
          + (f" (capped at ${cap:,.0f})" if cap else "") + f"  ->  bot sizes from ${max(use,0):,.2f}")
    ok = True
    if use < Config.load().daily.live_min_capital:
        print(f"  PROBLEM: under ${Config.load().daily.live_min_capital:,.0f} free. The bot never borrows against")
        print("  your holdings, so it would place nothing. Sell some positions or deposit cash.")
        ok = False
    if a.account_type != "MARGIN":
        print("  PROBLEM: not a margin account. This book re-uses same-day sale proceeds;")
        print("  in a cash account that is a good-faith violation. Apply for margin at Schwab.")
        ok = False
    if a.trading_blocked:
        print("  PROBLEM: account is restricted to closing trades only."); ok = False
    if pos:
        print("  NOTE: existing positions are left alone (the book only trades what it owns).")
    return ok


def check_alpaca_live() -> bool:
    k, s = get_env("ALPACA_LIVE_API_KEY"), get_env("ALPACA_LIVE_SECRET_KEY")
    if not (k and s):
        print("ALPACA_LIVE_API_KEY / ALPACA_LIVE_SECRET_KEY are not in .env."); return False
    from swingtrader.live.broker import PaperBroker
    try:
        b = PaperBroker(paper=False, key=k, secret=s); a = b.account()
    except Exception as exc:
        print(f"cannot connect to the live account: {exc}"); return False
    mult = float(a.multiplier or 1)
    print(f"LIVE (Alpaca) account {str(a.account_number)[:3]}***  status {a.status}")
    print(f"  equity ${float(a.equity):,.2f}   cash ${float(a.cash):,.2f}   margin multiplier {mult:g}")
    ok = mult >= 2 and not (a.trading_blocked or a.account_blocked)
    if mult < 2:
        print("  PROBLEM: not a margin account (good-faith violations with this book).")
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
        print(f"\nThis places REAL orders with REAL money via {cfg.daily.live_broker.upper()} from the next scheduled run:")
        env_cap = (get_env("DAILY_LIVE_CAPITAL") or "").strip()
        cap = float(env_cap) if env_cap and env_cap.lower() not in ("none", "null", "off") else cfg.daily.live_capital
        cap_txt = f"${cap:,.0f} cap" if cap else "all FREE capital"
        print(f"  IBS leg {cfg.daily.ibs_weight:.0%} + overnight leg {cfg.daily.night_weight:.0%} of the bot's capital ({cap_txt}),")
        floor = cfg.daily.daytrade_min_equity
        if cfg.daily.daytrade_mode != "auto":
            print("  intraday QQQ leg OFF.")
        elif cap and cap < floor:
            print(f"  intraday QQQ leg stays SHADOW (bot capital ${cap:,.0f} < ${floor:,.0f} floor).")
        else:
            print(f"  intraday QQQ leg live once bot capital >= ${floor:,.0f}.")
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
