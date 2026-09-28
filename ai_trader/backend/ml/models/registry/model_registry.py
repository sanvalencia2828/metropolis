from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import numpy as np

from backend.config.settings import settings


class ModelRegistry:
    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = root or (settings.BASE_PATH / "ml" / "models" / "srm")
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, name: str, weights: np.ndarray, bias: float, fill: np.ndarray, metrics: dict[str, Any]) -> Path:
        target = self.root / f"{name}.npz"
        np.savez(
            target,
            weights=np.asarray(weights, dtype=float),
            bias=np.array([bias], dtype=float),
            fill=np.asarray(fill, dtype=float),
        )
        meta = {
            "name": name,
            "path": str(target),
            "saved_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            "metrics": metrics,
        }
        (self.root / f"{name}.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        latest = self.root / "latest.json"
        latest.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return target

    def load(self, name: str = "latest") -> dict[str, Any]:
        if name == "latest":
            meta_path = self.root / "latest.json"
            if not meta_path.exists():
                raise FileNotFoundError("no trained SRM model")
            name = json.loads(meta_path.read_text(encoding="utf-8"))["name"]
        payload = np.load(self.root / f"{name}.npz")
        return {
            "name": name,
            "weights": payload["weights"],
            "bias": float(payload["bias"][0]),
            "fill": payload["fill"],
        }

    def latest_meta(self) -> Optional[dict[str, Any]]:
        path = self.root / "latest.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
