from __future__ import annotations

from typing import Any, Optional

import numpy as np
import pandas as pd

from backend.features.feature_registry import registry, to_frame

FEATURE_COLUMNS = registry.names()


class FeatureBuilder:
    columns = FEATURE_COLUMNS

    def frame(self, records: list[dict[str, Any]]) -> pd.DataFrame:
        frame = to_frame(records)
        for column in self.columns:
            if column not in frame.columns:
                frame[column] = np.nan
        return frame[self.columns].apply(pd.to_numeric, errors="coerce")

    def matrix(self, records: list[dict[str, Any]]) -> np.ndarray:
        return self.frame(records).to_numpy(dtype=float)

    def vector(self, record: dict[str, Any]) -> np.ndarray:
        return self.matrix([record])[0]


def impute(matrix: np.ndarray, fill: Optional[np.ndarray] = None) -> tuple[np.ndarray, np.ndarray]:
    values = np.array(matrix, dtype=float, copy=True)
    if fill is None:
        fill = np.zeros(values.shape[1], dtype=float)
        for index in range(values.shape[1]):
            column = values[:, index]
            if not np.isnan(column).all():
                fill[index] = float(np.nanmedian(column))
    mask = np.isnan(values)
    values[mask] = np.take(fill, np.where(mask)[1])
    return values, fill
