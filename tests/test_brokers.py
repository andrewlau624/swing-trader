from swingtrader.daily.brokers import SchwabAdapter


class Resp:
    def __init__(self, d):
        self.d = d

    def json(self):
        return self.d

    def raise_for_status(self):
        pass


class FakeClient:
    def __init__(self, positions):
        self.positions = positions

    def get_account(self, h, fields=None):
        return Resp({"securitiesAccount": {"type": "MARGIN", "positions": self.positions}})


def pos(sym, uniform, qty, px):
    return {"instrument": {"assetType": "EQUITY", "symbol": sym, "uniformSymbol": uniform, "cusip": "C"},
            "longQuantity": qty, "shortQuantity": 0, "marketValue": qty * px}


def adapter(positions):
    return SchwabAdapter(client=FakeClient(positions), account_hash="H")


def test_sell_finds_the_holding_under_schwabs_hyphen_symbol():
    a = adapter([pos("GS-D", "GS/PRD", 47, 18.13)])
    assert a._instructions("GS/PRD", "sell", 47) == [("SELL", 47)]


def test_sell_splits_long_and_short_when_the_order_exceeds_the_holding():
    a = adapter([pos("GS-D", "GS/PRD", 10, 18.13)])
    assert a._instructions("GS/PRD", "sell", 15) == [("SELL", 10), ("SELL_SHORT", 5)]


def test_buy_against_a_short_covers_first():
    a = adapter([{"instrument": {"assetType": "EQUITY", "symbol": "XYZ", "uniformSymbol": "XYZ", "cusip": "C"},
                  "longQuantity": 0, "shortQuantity": 5, "marketValue": -500}])
    assert a._instructions("XYZ", "buy", 8) == [("BUY_TO_COVER", 5), ("BUY", 3)]
