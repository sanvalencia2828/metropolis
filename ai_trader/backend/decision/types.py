from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class GateResult:
    name: str
    passed: bool
    reason: str
    value: Optional[float] = None
    threshold: Optional[float] = None


@dataclass(frozen=True)
class ScoreResult:
    score: float
    components: dict[str, float]


def num(record: dict[str, Any], *keys: str) -> Optional[float]:
    for key in keys:
        if key not in record or record[key] is None or record[key] == "":
            continue
        try:
            return float(record[key])
        except (TypeError, ValueError):
            continue
    return None


def flag(record: dict[str, Any], *keys: str) -> Optional[bool]:
    for key in keys:
        if key not in record or record[key] is None:
            continue
        value = record[key]
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)) and value in (0, 1):
            return bool(value)
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in ("1", "true", "yes"):
                return True
            if lowered in ("0", "false", "no"):
                return False
    return None
