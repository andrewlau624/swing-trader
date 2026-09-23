"""Send the Schwab-login expiry reminder if one is due. Run by
schwab-reminder.timer every 2 hours, 7 days a week (expiry can land on a weekend)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from swingtrader.config import ROOT
from swingtrader.daily.schwab_reminder import check
from swingtrader.live.notify import Notifier

if __name__ == "__main__":
    print(check(Notifier(ROOT / "state")))
