from __future__ import annotations

from typing import Any, Optional

import numpy as np

from backend.ml.models.registry.model_registry import ModelRegistry
from backend.ml.models.srm.srm_model import SRMModel, sigmoid
from backend.ml.training.feature_builder import FeatureBuilder, impute
from backend.ml.training.label_builder import LabelBuilder


class SRMTrainer:
    def __init__(
        self,
        builder: Optional[FeatureBuilder] = None,
        labels: Optional[LabelBuilder] = None,
        registry: Optional[ModelRegistry] = None,
        lr: float = 0.1,
        epochs: int = 400,
        l2: float = 1e-3,
    ) -> None:
        self.builder = builder or FeatureBuilder()
        self.labels = labels or LabelBuilder()
        self.registry = registry or ModelRegistry()
        self.lr = lr
        self.epochs = epochs
        self.l2 = l2

    def fit(self, records: list[dict[str, Any]], name: str = "srm") -> SRMModel:
        raw = self.builder.matrix(records)
        features, fill = impute(raw)
        y = self.labels.from_records(records).astype(float)
        if len(features) == 0:
            raise ValueError("no training rows")
        weights = np.zeros(features.shape[1], dtype=float)
        bias = 0.0
        n = max(len(features), 1)
        for _ in range(self.epochs):
            preds = sigmoid(features @ weights + bias)
            error = preds - y
            weights -= self.lr * ((features.T @ error) / n + self.l2 * weights)
            bias -= self.lr * (error.mean())
        model = SRMModel(weights=weights, bias=float(bias), fill=fill)
        metrics = self.evaluate(model, features, y)
        self.registry.save(name, model.weights, model.bias, fill, metrics)
        return model

    def evaluate(self, model: SRMModel, features: np.ndarray, y: np.ndarray) -> dict[str, float]:
        preds = model.predict(features)
        acc = float((preds == y).mean()) if len(y) else 0.0
        return {"accuracy": acc, "rows": float(len(y)), "positive_rate": float(y.mean()) if len(y) else 0.0}
