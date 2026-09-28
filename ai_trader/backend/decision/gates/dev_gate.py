from __future__ import annotations

from typing import Any, Optional

from backend.decision.types import GateResult, num


class DevGate:
    name = "dev"

    def __init__(
        self,
        max_creator_percent: float = 5.0,
        max_top10_percent: float = 40.0,
        max_sniper_percent: float = 20.0,
    ) -> None:
        self.max_creator_percent = max_creator_percent
        self.max_top10_percent = max_top10_percent
        self.max_sniper_percent = max_sniper_percent

    def evaluate(self, record: dict[str, Any]) -> GateResult:
        creator = num(record, "creator_percent", "dev_hold_percent", "dev_percent")
        top10 = num(record, "top10_percent", "top10_holder_percent")
        sniper = num(record, "sniper_percent", "sniper_hold_percent")
        if creator is None and top10 is None and sniper is None:
            return GateResult(name=self.name, passed=False, reason="unknown dev concentration")
        failed = self._breach(creator, self.max_creator_percent, "creator")
        if failed:
            return failed
        failed = self._breach(top10, self.max_top10_percent, "top10")
        if failed:
            return failed
        failed = self._breach(sniper, self.max_sniper_percent, "sniper")
        if failed:
            return failed
        value = max(v for v in (creator, top10, sniper) if v is not None)
        return GateResult(name=self.name, passed=True, reason="ok", value=value)

    def _breach(self, value: Optional[float], limit: float, label: str) -> Optional[GateResult]:
        if value is None or value <= limit:
            return None
        return GateResult(
            name=self.name,
            passed=False,
            reason=f"{label} {value} > {limit}",
            value=value,
            threshold=limit,
        )
