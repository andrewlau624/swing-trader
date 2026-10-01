"""What each strategy earns per day, from its MEASURED net bp per trade and trades per day.

    $/day = notional per trade x net bp x trades/day

Notional per trade is capped by buying power, modelled honestly:
- cash account (any account under $2k): settled cash only, and a sale settles T+1, so the money
  turns over at most once a day: total notional per day <= equity.
- margin >= $2k: Schwab intraday buying power, up to 4x equity (add. 40), per trade.
Each row's `lev` is the notional per trade as a multiple of equity, capped by the account. The rows
use lev 4 = every trade at the full intraday buying power: an UPPER bound (the live legs actually
run at ~0.5-1x). The last column is the account size needed for $1,000/day at that edge, on margin.
The brief's illustration ($12/day at $2.3k with no margin) turns the cash over 5 times a day; T+1
settlement allows once, so the honest cash figure is ~$2.30/day.

Every lab strategy adds a row once it has replay numbers (`ROWS` below; `make daytrade-table`).
"""
from __future__ import annotations

from dataclasses import dataclass

SIZES = (2_300, 10_000, 25_000)
MARGIN_MULT = 4.0


@dataclass(frozen=True)
class Row:
    name: str
    net_bp: float           # measured net bp per trade on the notional traded
    trades_per_day: float
    lev: float              # notional per trade / equity as measured (capped by the account)
    source: str
    measured: bool = True


ROWS = [
    Row("noise leg, QQQ (live book)", 2.0, 1.0, 4.0,
        "RESULTS add. 35: plan on ~+2bp/day per unit of equity, 2016-26 (0DTE era +2.2)"),
    Row("conviction trade, TQQQ (live book, shadow)", 15.3, 0.29, 4.0,
        "Study AK: +15.3bp/trade at 3bp/side 2016-26 (0s delay; 1-min delay +12.9); ~73 trades/yr"),
    Row("gap_vwap_reclaim (lab, Study Lab-AS: DEAD)", -18.9, 2.78, 0.139,
        "Study Lab-AS 2022-26 replay at 1x (10bp/side), 1s; lev 0.14 = the risk layer's measured average "
        "(0.5% risk per trade). Gross -1.7bp: no edge. At 2x costs -36.1bp"),
    Row("orb_in_play (lab, Study Lab-AU1: DEAD)", -23.5, 2.37, 0.15,
        "Study Lab-AU 2022-26 at 5bp/side: 19,016 trades; even the optimistic fill bound is ~0 at 5bp and "
        "-9bp at 10bp/side. 2.4 trades/day and lev 0.15 as measured under the lab limits (3 slots, 0.5% risk)"),
    Row("vwap_trend QQQ (lab, Study Lab-AW1: DEAD)", -9.3, 1.0, 1.0,
        "Study Lab-AW 2022-26, per DAY at 0.5bp/side, whole equity: gross +6.7bp/day eaten by 16 switches"),
    Row("illustration only: 10bp x 5 trades", 10.0, 5.0, 4.0,
        "the brief's illustration, NOT a measured edge", measured=False),
]


def per_day(row: Row, equity: float, kind: str) -> float:
    if kind == "cash" or equity < 2_000:
        # settled cash only: one turn of the account per day across all trades
        return min(min(row.lev, 1.0) * row.trades_per_day, 1.0) * equity * row.net_bp / 1e4
    return min(row.lev, MARGIN_MULT) * equity * row.trades_per_day * row.net_bp / 1e4


def needed_for(row: Row, target: float = 1_000.0) -> float:
    per_dollar = min(row.lev, MARGIN_MULT) * row.trades_per_day * row.net_bp / 1e4
    return target / per_dollar if per_dollar > 0 else float("inf")


def markdown(rows=ROWS) -> str:
    head = ("| strategy | net bp/trade | trades/day | $2.3k cash | $2.3k margin | $10k | $25k "
            "| size for $1k/day | source |\n|---|---|---|---|---|---|---|---|---|\n")
    out = []
    for r in rows:
        need = needed_for(r)
        money = lambda x: f"{'-' if x < 0 else ''}${abs(x):,.2f}"  # noqa: E731
        cells = [money(per_day(r, 2_300, 'cash')), money(per_day(r, 2_300, 'margin')),
                 money(per_day(r, 10_000, 'margin')), money(per_day(r, 25_000, 'margin'))]
        need_s = "never (edge <= 0)" if need == float("inf") else f"${need:,.0f}"
        name = r.name if r.measured else f"*{r.name}*"
        out.append(f"| {name} | {r.net_bp:+.1f} | {r.trades_per_day:.2f} | " + " | ".join(cells)
                   + f" | {need_s} | {r.source} |")
    return head + "\n".join(out) + "\n"


if __name__ == "__main__":
    print(markdown())
