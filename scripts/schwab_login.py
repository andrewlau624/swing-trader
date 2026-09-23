"""Create or renew the Schwab API login (the refresh token lasts 7 days).

  python scripts/schwab_login.py          # prints a URL; log in; paste the URL you land on

Works over SSH: nothing needs a browser on the server. After Schwab's login
page, your browser goes to https://127.0.0.1/?code=... and shows a
"can't connect" error. That's expected. Copy the WHOLE address bar and paste it here.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from swingtrader.daily.brokers import schwab_credentials, schwab_token_path


def main():
    from schwab.auth import client_from_manual_flow
    k, s, cb = schwab_credentials()
    path = schwab_token_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()           # a manual flow always starts a fresh 7-day token
    c = client_from_manual_flow(k, s, cb, str(path))
    r = c.get_account_numbers(); r.raise_for_status()
    rows = r.json()
    print(f"\nlogged in. token saved to {path} (valid 7 days - renew with: make schwab-login)")
    for x in rows:
        print(f"  linked account ...{x['accountNumber'][-4:]}")
    if len(rows) > 1:
        print("  more than one account: add SCHWAB_ACCOUNT_NUMBER=<the full number> to .env")
    path.chmod(0o600)


if __name__ == "__main__":
    main()
