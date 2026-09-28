from __future__ import annotations

from typing import Any

from backend.decision.types import GateResult, num


class HolderGate:
    name = "holder"

    def __init__(self, min_holders: float = 100.0) -> None:
        self.min_holders = min_holders

    def evaluate(self, record: dict[str, Any]) -> GateResult:
        value = num(record, "holder_count", "holders")
        if value is None:
            return GateResult(
                name=self.name,
                passed=False,
                reason="missing holder_count",
                threshold=self.min_holders,
            )
        passed = value >= self.min_holders
        return GateResult(
            name=self.name,
            passed=passed,
            reason="ok" if passed else f"holders {value} < {self.min_holders}",
            value=value,
            threshold=self.min_holders,
        )
