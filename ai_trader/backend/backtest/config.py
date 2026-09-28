from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class BacktestConfig:
    chain: str = "sol"
    cash: float = 10_000.0
    position_pct: float = 0.1
    max_positions: int = 5
    resolution: str = "1m"
    fee_bps: float = 10.0
    stop_loss_pct: float = 0.15
    take_profit_pct: float = 0.30
    from_ts: Optional[int] = None
    to_ts: Optional[int] = None
