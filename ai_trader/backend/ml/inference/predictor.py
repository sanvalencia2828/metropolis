from __future__ import annotations

from typing import Any, Optional

from backend.ml.models.registry.model_registry import ModelRegistry
from backend.ml.models.srm.srm_model import SRMModel
from backend.ml.training.feature_builder import FeatureBuilder, impute


class Predictor:
    def __init__(
        self,
        model: Optional[SRMModel] = None,
        builder: Optional[FeatureBuilder] = None,
        registry: Optional[ModelRegistry] = None,
        buy_threshold: float = 0.65,
        watch_threshold: float = 0.45,
    ) -> None:
        self.builder = builder or FeatureBuilder()
        self.registry = registry or ModelRegistry()
        self.buy_threshold = buy_threshold
        self.watch_threshold = watch_threshold
        self.model = model or self._load()

    def _load(self) -> Optional[SRMModel]:
        try:
            payload = self.registry.load()
        except FileNotFoundError:
            return None
        return SRMModel(weights=payload["weights"], bias=payload["bias"], fill=payload["fill"])

    def probability(self, record: dict[str, Any]) -> Optional[float]:
        if self.model is None:
            return None
        vector, _ = impute(self.builder.matrix([record]), self.model.fill)
        return float(self.model.predict_proba(vector)[0])

    def recommend(self, record: dict[str, Any]) -> str:
        proba = self.probability(record)
        if proba is None:
            return "WATCH"
        if proba >= self.buy_threshold:
            return "BUY"
        if proba >= self.watch_threshold:
            return "WATCH"
        return "REJECT"
