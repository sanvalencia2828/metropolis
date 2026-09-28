from __future__ import annotations

from typing import Any, Optional

from backend.decision.types import GateResult, flag, num


class RugGate:
    name = "rug"

    def __init__(self, max_tax_percent: float = 10.0) -> None:
        self.max_tax_percent = max_tax_percent

    def evaluate(self, record: dict[str, Any]) -> GateResult:
        if flag(record, "is_rug", "rug_pull", "rugged") is True:
            return self._fail("token flagged as rug", 1.0)
        if flag(record, "freeze_authority", "freezeable", "is_freezable") is True:
            return self._fail("freeze authority enabled", 1.0)
        if flag(record, "mintable", "mint_authority") is True:
            return self._fail("mint authority enabled", 1.0)
        if flag(record, "renounced", "renounced_mint") is False:
            return self._fail("mint not renounced", 0.0)
        if flag(record, "lp_locked", "liquidity_locked") is False:
            return self._fail("lp not locked", 0.0)
        tax = self._max_tax(record)
        if tax is not None and tax > self.max_tax_percent:
            return self._fail(f"tax {tax} > {self.max_tax_percent}", tax)
        if not self._has_signal(record):
            return GateResult(name=self.name, passed=False, reason="unknown rug status")
        return GateResult(name=self.name, passed=True, reason="ok", value=0.0)

    def _max_tax(self, record: dict[str, Any]) -> Optional[float]:
        taxes = [
            num(record, "buy_tax", "buy_tax_percent"),
            num(record, "sell_tax", "sell_tax_percent"),
        ]
        present = [tax for tax in taxes if tax is not None]
        return max(present) if present else None

    def _has_signal(self, record: dict[str, Any]) -> bool:
        keys = (
            "is_rug",
            "rug_pull",
            "rugged",
            "freeze_authority",
            "freezeable",
            "is_freezable",
            "mintable",
            "mint_authority",
            "renounced",
            "renounced_mint",
            "lp_locked",
            "liquidity_locked",
            "buy_tax",
            "buy_tax_percent",
            "sell_tax",
            "sell_tax_percent",
        )
        return any(record.get(key) is not None for key in keys)

    def _fail(self, reason: str, value: float) -> GateResult:
        return GateResult(
            name=self.name,
            passed=False,
            reason=reason,
            value=value,
            threshold=self.max_tax_percent,
        )
