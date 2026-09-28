from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PositionSizingConfig:
    account_equity: float
    risk_per_trade: float = 0.01
    max_position_value: float | None = None


class PositionSizer:
    """Calculates the number of units to buy based on a fixed risk budget."""

    def __init__(self, risk_per_trade: float = 0.01, max_position_value: float | None = None) -> None:
        self.risk_per_trade = risk_per_trade
        self.max_position_value = max_position_value

    def size(
        self,
        account_equity: float,
        entry_price: float,
        stop_loss_price: float,
        risk_per_trade: float | None = None,
        max_position_value: float | None = None,
    ) -> float:
        if account_equity <= 0:
            raise ValueError("account_equity must be positive")
        if entry_price <= 0:
            raise ValueError("entry_price must be positive")
        if stop_loss_price <= 0:
            raise ValueError("stop_loss_price must be positive")

        risk_budget = account_equity * (self.risk_per_trade if risk_per_trade is None else risk_per_trade)
        risk_per_unit = abs(entry_price - stop_loss_price)
        if risk_per_unit == 0:
            raise ValueError("entry_price and stop_loss_price must differ")

        quantity = risk_budget / risk_per_unit
        limit = self.max_position_value if max_position_value is None else max_position_value
        if limit is not None:
            quantity = min(quantity, limit / entry_price)
        return max(0.0, quantity)
