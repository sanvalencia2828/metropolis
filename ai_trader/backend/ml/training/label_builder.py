from __future__ import annotations

from typing import Any, Optional

import numpy as np

from backend.paper_trading.position_manager import Position

WIN = 1
LOSS = 0


class LabelBuilder:
    def __init__(self, horizon_return: float = 0.10) -> None:
        self.horizon_return = horizon_return

    def from_forward_return(self, start_price: float, end_price: float) -> int:
        if start_price <= 0:
            return LOSS
        return WIN if (end_price / start_price) - 1.0 >= self.horizon_return else LOSS

    def from_position(self, position: Position) -> int:
        return WIN if position.pnl > 0 else LOSS

    def from_records(self, records: list[dict[str, Any]]) -> np.ndarray:
        labels = []
        for record in records:
            if "label" in record:
                labels.append(int(record["label"]))
                continue
            start = _price(record, "price", "entry_price")
            end = _price(record, "exit_price", "future_price")
            if start is None or end is None:
                labels.append(LOSS)
                continue
            labels.append(self.from_forward_return(start, end))
        return np.array(labels, dtype=int)


def _price(record: dict[str, Any], *keys: str) -> Optional[float]:
    for key in keys:
        value = record.get(key)
        if value is None or value == "":
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None
