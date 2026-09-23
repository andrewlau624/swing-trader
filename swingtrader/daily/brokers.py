"""Broker adapters for the daily book: Alpaca (paper) and Schwab (live).

The executor talks to one small interface:

  key, secret                  -> account-lock fingerprint
  clock()                      -> .is_open, .next_open, .next_close
  account()                    -> .equity, .cash, .multiplier, .trading_blocked, .account_blocked
  positions()                  -> {symbol: obj(.qty, .current_price)}
  submit(sym, side, tif, coid, qty=None, notional=None, ref_px=None) -> broker order id
  order_status(coid, info)     -> (status, filled_qty, avg_px, when)

Differences the adapters absorb:

  Alpaca: client_order_id gives idempotency; OPG/CLS auction orders;
          fractional DAY orders by notional.
  Schwab: no client order id -- idempotency is "look for today's matching
          order before placing"; MARKET_ON_CLOSE exists but there is NO
          market-on-open type (a market DAY order placed pre-market fills at
          the open instead); no fractional shares via the API; shorting needs
          explicit SELL_SHORT / BUY_TO_COVER; tokens expire after 7 days.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import time
from pathlib import Path
from types import SimpleNamespace

from ..config import ROOT, get_env, require_alpaca_keys

ET = "America/New_York"
OPEN = "new"   # any non-terminal state; DailyBook only cares about TERMINAL


class AlpacaAdapter:
    """Thin pass-through over live.broker.PaperBroker (or a test double)."""

    fractional = True

    def __init__(self, broker):
        self.b = broker
        self.key, self.secret = broker.key, broker.secret
        self.client = broker.client       # tests inspect submitted requests here

    def clock(self):
        return self.b.clock()

    def account(self):
        return self.b.account()

    def positions(self) -> dict:
        return self.b.positions()

    def submit(self, sym, side, tif, coid, qty=None, notional=None, ref_px=None):
        from alpaca.trading.enums import OrderSide, TimeInForce
        from alpaca.trading.requests import MarketOrderRequest
        req = dict(symbol=sym, side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
                   time_in_force={"day": TimeInForce.DAY, "opg": TimeInForce.OPG,
                                  "cls": TimeInForce.CLS}[tif],
                   client_order_id=coid)
        if notional:
            req["notional"] = round(notional, 2)
        else:
            req["qty"] = qty if tif == "day" else int(qty)
        o = self.client.submit_order(MarketOrderRequest(**req))
        return str(o.id)

    def order_status(self, coid, info):
        bo = self.client.get_order_by_client_id(coid)
        status = str(bo.status).split(".")[-1].lower()
        return (status, float(bo.filled_qty or 0), float(bo.filled_avg_price or 0),
                str(bo.filled_at or bo.updated_at or ""))


# ------------------------------------------------------------------ Schwab
SCHWAB_STATUS = {"FILLED": "filled", "CANCELED": "canceled", "EXPIRED": "expired",
                 "REJECTED": "rejected", "REPLACED": "replaced"}
TOKEN_MAX_AGE_S = 7 * 24 * 3600          # Schwab refresh tokens die at ~7 days
TOKEN_WARN_AGE_S = 6 * 24 * 3600


def schwab_token_path() -> Path:
    return Path(get_env("SCHWAB_TOKEN_PATH") or (ROOT / "state" / "schwab-token.json"))


def schwab_token_age_s(path: Path | None = None) -> float | None:
    p = path or schwab_token_path()
    if not p.exists():
        return None
    try:
        return time.time() - float(json.loads(p.read_text())["creation_timestamp"])
    except Exception:
        return None


def schwab_credentials() -> tuple[str, str, str]:
    k, s = get_env("SCHWAB_APP_KEY"), get_env("SCHWAB_APP_SECRET")
    cb = get_env("SCHWAB_CALLBACK_URL") or "https://127.0.0.1"
    if not (k and s):
        raise RuntimeError("SCHWAB_APP_KEY / SCHWAB_APP_SECRET are not in .env "
                           "(developer.schwab.com -> Dashboard -> your app)")
    return k, s, cb


class SchwabAdapter:
    fractional = False

    def __init__(self, client=None, account_hash: str | None = None, clock_source=None):
        k, s, _ = schwab_credentials() if client is None else ("test", "test", "")
        if client is None:
            age = schwab_token_age_s()
            if age is None:
                raise RuntimeError("no Schwab token yet - run: make schwab-login")
            if age > TOKEN_MAX_AGE_S:
                raise RuntimeError(f"Schwab token is {age/86400:.1f} days old (limit 7) - "
                                   "run: make schwab-login")
            from schwab.auth import client_from_token_file
            client = client_from_token_file(str(schwab_token_path()), k, s)
        self.c = client
        self.hash = account_hash or self._pick_account()
        self.key, self.secret = f"schwab:{k}", self.hash
        self._clock = clock_source

    # ------------------------------------------------------------- state
    def _pick_account(self) -> str:
        r = self.c.get_account_numbers(); r.raise_for_status()
        rows = r.json()
        want = get_env("SCHWAB_ACCOUNT_NUMBER")
        if want:
            for x in rows:
                if x["accountNumber"] == want:
                    return x["hashValue"]
            raise RuntimeError(f"SCHWAB_ACCOUNT_NUMBER {want[-4:]} not linked to this app")
        if len(rows) != 1:
            raise RuntimeError(f"{len(rows)} Schwab accounts linked - set SCHWAB_ACCOUNT_NUMBER in .env")
        return rows[0]["hashValue"]

    def clock(self):
        # the exchange calendar is the same everywhere; Alpaca's clock is free
        # and already trusted by the rest of the code
        if self._clock is not None:
            return self._clock()
        from alpaca.trading.client import TradingClient
        k, s = require_alpaca_keys()
        return TradingClient(k, s, paper=True).get_clock()

    def _acct(self) -> dict:
        from schwab.client import Client
        r = self.c.get_account(self.hash, fields=[Client.Account.Fields.POSITIONS])
        r.raise_for_status()
        return r.json()["securitiesAccount"]

    def account(self):
        a = self._acct()
        bal = a.get("currentBalances", {})
        equity = float(bal.get("liquidationValue") or bal.get("equity") or 0)
        margin = a.get("type") == "MARGIN"
        bp = max(float(bal.get("dayTradingBuyingPower") or 0), float(bal.get("buyingPower") or 0))
        mult = 1.0 if not margin else max(2.0, min(4.0, bp / equity if equity else 2.0))
        return SimpleNamespace(equity=equity, cash=float(bal.get("cashBalance") or 0),
                               multiplier=mult, account_type=a.get("type"),
                               trading_blocked=bool(a.get("isClosingOnlyRestricted")),
                               account_blocked=False, buying_power=bp,
                               account_number=a.get("accountNumber", ""), status="ACTIVE")

    def positions(self) -> dict:
        out = {}
        for p in self._acct().get("positions", []) or []:
            ins = p.get("instrument", {})
            if ins.get("assetType") not in ("EQUITY", "ETF", "COLLECTIVE_INVESTMENT"):
                continue
            q = float(p.get("longQuantity") or 0) - float(p.get("shortQuantity") or 0)
            if abs(q) < 1e-9:
                continue
            mv = float(p.get("marketValue") or 0)
            out[ins["symbol"]] = SimpleNamespace(qty=q, current_price=abs(mv / q) if q else None)
        return out

    # ------------------------------------------------------------ orders
    def _today_orders(self) -> list:
        """Orders entered since midnight ET today (never yesterday's: an
        identical SGOV order from yesterday must not look like a duplicate)."""
        from zoneinfo import ZoneInfo
        now = dt.datetime.now(ZoneInfo(ET))
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        r = self.c.get_orders_for_account(self.hash, from_entered_datetime=start,
                                          to_entered_datetime=now + dt.timedelta(minutes=1))
        r.raise_for_status()
        return r.json() or []

    @staticmethod
    def _leg(o: dict) -> tuple[str, str, float]:
        leg = (o.get("orderLegCollection") or [{}])[0]
        return (leg.get("instrument", {}).get("symbol", ""), leg.get("instruction", ""),
                float(leg.get("quantity") or o.get("quantity") or 0))

    def _instructions(self, sym: str, side: str, qty: float) -> list[tuple[str, int]]:
        """Split an order into Schwab instructions. A sell larger than the long
        position becomes SELL + SELL_SHORT; a buy against a short becomes
        BUY_TO_COVER (+ BUY for any excess)."""
        have = float(getattr(self.positions().get(sym), "qty", 0.0) or 0.0)
        q = int(qty)
        if side == "sell":
            long_part = int(min(max(have, 0), q))
            parts = [("SELL", long_part), ("SELL_SHORT", q - long_part)]
        else:
            cover = int(min(max(-have, 0), q))
            parts = [("BUY_TO_COVER", cover), ("BUY", q - cover)]
        return [(ins, n) for ins, n in parts if n > 0]

    def submit(self, sym, side, tif, coid, qty=None, notional=None, ref_px=None):
        from schwab.orders.common import Duration, OrderType, Session
        from schwab.orders.equities import (equity_buy_market, equity_buy_to_cover_market,
                                            equity_sell_market, equity_sell_short_market)
        if notional:                        # no fractional shares via the Schwab API
            if not ref_px:
                raise ValueError(f"{sym}: notional order needs a reference price")
            qty = math.floor(notional / ref_px)
        if not qty or int(qty) < 1:
            raise ValueError(f"{sym}: rounds to 0 whole shares (Schwab has no fractional API)")
        parts = self._instructions(sym, side, qty)
        # idempotency without client order ids: a matching live/filled order
        # placed today means this decision was already sent
        todays = [o for o in self._today_orders()
                  if o.get("status") not in ("CANCELED", "REJECTED", "EXPIRED")]
        ids = []
        for ins, n in parts:
            dup = next((o for o in todays if self._leg(o)[:2] == (sym, ins)
                        and int(self._leg(o)[2]) == n), None)
            if dup is not None:
                ids.append(str(dup["orderId"])); continue
            make = {"BUY": equity_buy_market, "SELL": equity_sell_market,
                    "SELL_SHORT": equity_sell_short_market,
                    "BUY_TO_COVER": equity_buy_to_cover_market}[ins]
            b = make(sym, n).set_duration(Duration.DAY).set_session(Session.NORMAL)
            if tif == "cls":
                b = b.set_order_type(OrderType.MARKET_ON_CLOSE)
            # tif "opg": no market-on-open type at Schwab; a market DAY order
            # placed before 09:30 executes at the open
            r = self.c.place_order(self.hash, b.build())
            if r.status_code not in (200, 201):
                raise RuntimeError(f"Schwab rejected {ins} {n} {sym}: {r.status_code} {r.text[:160]}")
            loc = r.headers.get("Location", "")
            ids.append(loc.rstrip("/").split("/")[-1])
        return ",".join(ids)

    def order_status(self, coid, info):
        ids = [i for i in str(info.get("broker_id", "")).split(",") if i]
        if not ids:
            return (OPEN, 0.0, 0.0, "")
        statuses, fq, notional, when = [], 0.0, 0.0, ""
        for oid in ids:
            r = self.c.get_order(int(oid), self.hash); r.raise_for_status()
            o = r.json()
            statuses.append(SCHWAB_STATUS.get(o.get("status", ""), OPEN))
            for act in o.get("orderActivityCollection", []) or []:
                for leg in act.get("executionLegs", []) or []:
                    q = float(leg.get("quantity") or 0); fq += q
                    notional += q * float(leg.get("price") or 0)
                    when = max(when, str(leg.get("time", "")))
            when = when or str(o.get("closeTime", ""))
        avg = notional / fq if fq else 0.0
        if all(s == "filled" for s in statuses):
            status = "filled"
        elif any(s == OPEN for s in statuses):
            status = OPEN
        else:
            status = next(s for s in statuses if s != "filled")
        return (status, fq, avg, when)


def make_adapter(account: str, live_broker: str = "schwab"):
    """paper -> Alpaca paper; live -> Schwab (default) or Alpaca live."""
    from ..live.broker import PaperBroker
    if account == "paper":
        return AlpacaAdapter(PaperBroker())
    if account != "live":
        raise ValueError(f"unknown daily account {account!r} (paper|live)")
    if live_broker == "schwab":
        return SchwabAdapter()
    k, s = get_env("ALPACA_LIVE_API_KEY"), get_env("ALPACA_LIVE_SECRET_KEY")
    if not (k and s):
        raise RuntimeError("live_broker=alpaca but ALPACA_LIVE_API_KEY / _SECRET_KEY missing")
    return AlpacaAdapter(PaperBroker(paper=False, key=k, secret=s))
