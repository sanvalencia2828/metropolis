from __future__ import annotations

from typing import Any, Optional

from backend.decision.types import ScoreResult
from backend.features.feature_registry import registry


class ScoringEngine:
    def __init__(
        self,
        liquidity_ref: float = 100_000.0,
        holders_ref: float = 1_000.0,
        volume_ref: float = 50_000.0,
    ) -> None:
        self.liquidity_ref = liquidity_ref
        self.holders_ref = holders_ref
        self.volume_ref = volume_ref

    def score(self, record: dict[str, Any]) -> ScoreResult:
        features = registry.extract(record)
        components = {
            "liquidity": self._scaled(features.get("liquidity"), self.liquidity_ref, 25.0),
            "holders": self._scaled(features.get("holder_count"), self.holders_ref, 15.0),
            "volume": self._scaled(features.get("volume"), self.volume_ref, 15.0),
            "buy_sell_ratio": self._scaled(features.get("buy_sell_ratio"), 2.0, 15.0),
            "price_change": self._clipped_change(features.get("price_change_percent"), 10.0),
            "renounced": 10.0 if features.get("renounced") == 1.0 else 0.0,
            "not_honeypot": 10.0 if features.get("is_honeypot") == 0.0 else 0.0,
        }
        total = round(sum(components.values()), 4)
        return ScoreResult(score=min(100.0, max(0.0, total)), components=components)

    @staticmethod
    def _scaled(value: Optional[float], reference: float, weight: float) -> float:
        if value is None or reference <= 0 or value < 0:
            return 0.0
        return round(min(1.0, value / reference) * weight, 4)

    @staticmethod
    def _clipped_change(value: Optional[float], weight: float) -> float:
        if value is None or value <= 0:
            return 0.0
        return round(min(weight, value / 5.0), 4)
