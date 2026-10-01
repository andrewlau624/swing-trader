"""Strategy plug-ins: one file each, one interface (strategies/base.py), one plan each (plans/)."""
from .gap_vwap_reclaim import GapVwapReclaim
from .open_imbalance import OpenImbalance
from .orb_in_play import OrbInPlay
from .vwap_trend import VwapTrend

REGISTRY = {s.name: s for s in (GapVwapReclaim, OpenImbalance, OrbInPlay, VwapTrend)}
