"""Turn real-money trading of the daily book on or off.

  python scripts/daily_switch.py on     # DAILY_LIVE=on in .env (asks to confirm)
  python scripts/daily_switch.py off    # remove it (warns if the live book holds anything)
  python scripts/daily_switch.py check  # connect to the live account, change nothing
  python scripts/daily_switch.py on roth     # same three for the Roth IRA book
                                             # (DAILY_ROTH, SCHWAB_ROTH_ACCOUNT_NUMBER)

The paper book keeps running either way, so paper vs real fills stay comparable.
"""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from swingtrader.config import Config, ROOT, get_env
from swingtrader.daily.book import DailyBook, book_file

ENV = ROOT / ".env"
# account -> (.env switch, .env capital cap, .env Schwab account number)
ACCTS = {"live": ("DAILY_LIVE", "DAILY_LIVE_CAPITAL", "SCHWAB_ACCOUNT_NUMBER"),
         "roth": ("DAILY_ROTH", "DAILY_ROTH_CAPITAL", "SCHWAB_ROTH_ACCOUNT_NUMBER")}


def set_live(on: bool, acct: str = "live") -> None:
    """The switch lives in .env: gitignored, so `make pull` (git reset --hard)
    can never flip real money on or off behind your back."""
    var = ACCTS[acct][0]
    val = f"{var}={'on' if on else 'off'}"
    line = re.compile(rf'^{var}=.*$', re.M)
    s = ENV.read_text() if ENV.exists() else ""
    s = line.sub(val, s) if line.search(s) else s.rstrip("\n") + ("\n" if s else "") + val + "\n"
    ENV.write_text(s)
    import os
    os.environ[var] = "on" if on else "off"


def _cap(acct: str):
    env_cap = (get_env(ACCTS[acct][1]) or "").strip()
    return float(env_cap) if env_cap and env_cap.lower() not in ("none", "null", "off") \
        else Config.load().daily.live_capital


def check(acct: str = "live") -> bool:
    cfg = Config.load()
    if acct == "roth" or cfg.daily.live_broker == "schwab":
        return check_schwab(acct)
    return check_alpaca_live()


def check_schwab(acct: str = "live") -> bool:
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
        b = SchwabAdapter(account_env=ACCTS[acct][2]); a = b.account(); pos = b.positions()
    except Exception as exc:
        print(f"cannot reach the Schwab account: {exc}"); return False
    print(f"{acct.upper()} (Schwab) account ...{str(a.account_number)[-4:]}  type {a.account_type}")
    print(f"  equity ${a.equity:,.2f}   cash ${a.cash:,.2f}   buying power ${a.buying_power:,.2f}"
          f"   est. intraday multiplier {a.multiplier:g}")
    print(f"  open positions {len(pos)}")
    from swingtrader.daily.book import DailyBook, book_file
    from swingtrader.config import ROOT
    own = set(DailyBook.load(ROOT / "state", 0.0, book_file(acct)).positions)
    foreign = sum(abs(float(p.qty) * float(p.current_price or 0)) for s, p in pos.items() if s not in own)
    free = a.equity - foreign
    cap = _cap(acct)
    use = min(free, cap) if cap else free
    print(f"  your other holdings ${foreign:,.2f}  ->  FREE for the bot ${free:,.2f}"
          + (f" (capped at ${cap:,.0f})" if cap else "") + f"  ->  bot sizes from ${max(use,0):,.2f}")
    ok = True
    if use < Config.load().daily.live_min_capital:
        print(f"  PROBLEM: under ${Config.load().daily.live_min_capital:,.0f} free. The bot never borrows against")
        print("  your holdings, so it would place nothing. Sell some positions or deposit cash.")
        ok = False
    if acct == "roth":
        lm = (get_env("ROTH_LIMITED_MARGIN") or "").strip().lower() in ("yes", "on", "true", "1")
        if not lm:
            print("  PROBLEM: the Roth book needs Schwab LIMITED MARGIN on the IRA (no borrowing;")
            print("  it lets same-day sale proceeds buy without good-faith violations). Apply at")
            print("  Schwab, then set ROTH_LIMITED_MARGIN=yes in .env.")
            ok = False
        print("  Roth mode: IBS + overnight legs at 1.0x (never borrows), intraday leg long-only")
        print("  in 3x ETFs (TQQQ/SQQQ, SOXL/SOXS) with the cash the open sells free up.")
        if foreign > 0:
            print("  NOTE: the ETFs you hold here are 'your holdings': the bot will not sell them.")
            print("  To give the bot that money, sell them yourself (no tax inside a Roth).")
    elif a.account_type != "MARGIN":
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
    acct = sys.argv[2] if len(sys.argv) > 2 else "live"
    if acct not in ACCTS:
        sys.exit(__doc__)
    cfg = Config.load()
    accts = cfg.daily.resolved_accounts()
    if cmd == "check":
        check(acct); print(f"\naccounts trading: {accts}"); return
    if cmd == "on":
        if acct in accts:
            print(f"real money ({acct}) is already ON:", accts); return
        if not check(acct):
            sys.exit("\nnot switching on.")
        broker = "SCHWAB (Roth IRA)" if acct == "roth" else cfg.daily.live_broker.upper()
        print(f"\nThis places REAL orders with REAL money via {broker} from the next scheduled run:")
        cap = _cap(acct)
        cap_txt = f"${cap:,.0f} cap" if cap else "all FREE capital"
        print(f"  IBS leg {cfg.daily.ibs_weight:.0%} + overnight leg {cfg.daily.night_weight:.0%} of the bot's capital ({cap_txt}),")
        floor = cfg.daily.daytrade_min_equity
        if acct == "roth":
            print("  intraday legs OFF (cash account).")
        elif cfg.daily.daytrade_mode != "auto":
            print("  intraday QQQ leg OFF.")
        else:
            print(f"  intraday QQQ/SMH leg live while the ACCOUNT holds >= ${floor:,.0f} (Reg T).")
        if input('Type REAL MONEY to confirm: ').strip() != "REAL MONEY":
            sys.exit("not confirmed; nothing changed.")
        set_live(True, acct)
        print(f"done: {ACCTS[acct][0]}=on in .env. accounts trading: {Config.load().daily.resolved_accounts()}")
        print("check it tomorrow with: make daily-status")
        return
    if cmd == "off":
        if acct not in accts:
            print(f"real money ({acct}) is already OFF:", accts); return
        b = DailyBook.load(ROOT / "state", 0.0, book_file(acct))
        if b.positions or b.open_orders():
            print(f"WARNING: the live book still holds {sorted(b.positions)} "
                  f"with {len(b.open_orders())} open order(s).")
            print("Switching off stops managing them: overnight names will NOT be sold at")
            print("the open. Safest: switch off after the 09:50 ET run, when the overnight leg")
            print("is flat, and sell any IBS ETFs by hand in the Alpaca app.")
            if input("Type OFF ANYWAY to continue: ").strip() != "OFF ANYWAY":
                sys.exit("nothing changed.")
        set_live(False, acct)
        print(f"done: {ACCTS[acct][0]}=off in .env. accounts trading: {Config.load().daily.resolved_accounts()}")
        return
    sys.exit(__doc__)


if __name__ == "__main__":
    main()
