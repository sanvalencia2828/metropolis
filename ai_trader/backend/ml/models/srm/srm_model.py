from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def sigmoid(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(values, -500, 500)
    return 1.0 / (1.0 + np.exp(-clipped))


@dataclass
class SRMModel:
    weights: np.ndarray
    bias: float = 0.0
    fill: np.ndarray | None = None

    def logits(self, features: np.ndarray) -> np.ndarray:
        matrix = np.atleast_2d(features)
        return matrix @ self.weights + self.bias

    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        return sigmoid(self.logits(features))

    def predict(self, features: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        return (self.predict_proba(features) >= threshold).astype(int)
