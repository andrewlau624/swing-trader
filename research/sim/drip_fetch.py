"""Study DRIP-PAY: fetch Alpaca cash-dividend corporate actions (ex/record/payable dates) 2021-01..2026-10. Outcome-free.
  PYTHONPATH=. .venv/bin/python -m research.sim.drip_fetch"""
import json, time, urllib.request, urllib.parse, pandas as pd
from swingtrader.config import get_env
H = {"APCA-API-KEY-ID": get_env("ALPACA_API_KEY") or get_env("APCA_API_KEY_ID"), "APCA-API-SECRET-KEY": get_env("ALPACA_SECRET_KEY") or get_env("APCA_API_SECRET_KEY")}
rows = []
for m in pd.period_range("2020-12", "2026-10", freq="M"):
    tok = None
    while True:
        p = {"types": "cash_dividend", "start": str(m.start_time.date()), "end": str(m.end_time.date()), "limit": 1000}
        if tok: p["page_token"] = tok
        for k in range(4):
            try:
                d = json.loads(urllib.request.urlopen(urllib.request.Request("https://data.alpaca.markets/v1/corporate-actions?" + urllib.parse.urlencode(p), headers=H), timeout=40).read()); break
            except Exception as e:
                time.sleep(2 + 2 * k); d = {}
        rows += d.get("corporate_actions", {}).get("cash_dividends", []); tok = d.get("next_page_token")
        if not tok: break
    print(m, len(rows), flush=True)
df = pd.DataFrame(rows); df.to_parquet("data/research/events/alpaca_cash_divs.parquet", index=False)
print("saved", len(df), "payable_date present:", df.payable_date.notna().mean() if "payable_date" in df else 0)
