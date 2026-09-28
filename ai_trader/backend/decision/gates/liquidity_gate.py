from __future__ import annotations

from typing import Any

from backend.decision.types import GateResult, num


class LiquidityGate:
    name = "liquidity"

    def __init__(self, min_liquidity: float = 10_000.0) -> None:
        self.min_liquidity = min_liquidity

    def evaluate(self, record: dict[str, Any]) -> GateResult:
        value = num(record, "liquidity", "liquidity_usd")
        if value is None:
            return GateResult(
                name=self.name,
                passed=False,
                reason="missing liquidity",
                threshold=self.min_liquidity,
            )
        passed = value >= self.min_liquidity
        return GateResult(
            name=self.name,
            passed=passed,
            reason="ok" if passed else f"liquidity {value} < {self.min_liquidity}",
            value=value,
            threshold=self.min_liquidity,
        )
