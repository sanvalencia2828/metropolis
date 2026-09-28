from __future__ import annotations

from typing import Any

from backend.decision.types import GateResult, flag


class HoneypotGate:
    name = "honeypot"

    def evaluate(self, record: dict[str, Any]) -> GateResult:
        value = flag(record, "is_honeypot", "honeypot")
        if value is None:
            return GateResult(
                name=self.name,
                passed=False,
                reason="unknown honeypot status",
            )
        if value:
            return GateResult(
                name=self.name,
                passed=False,
                reason="token flagged as honeypot",
                value=1.0,
            )
        return GateResult(name=self.name, passed=True, reason="ok", value=0.0)
