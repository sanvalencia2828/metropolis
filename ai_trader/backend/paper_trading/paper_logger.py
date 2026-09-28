from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from backend.config.settings import settings


class PaperLogger:
    def __init__(self, path: Optional[Path] = None, persist: bool = True) -> None:
        self.path = path or (settings.STORAGE_PATH / "paper_trades.jsonl")
        self.persist = persist
        self.events: list[dict[str, Any]] = []

    def log(self, event_type: str, payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        event = {
            "ts": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            "type": event_type,
            **(payload or {}),
        }
        self.events.append(event)
        if self.persist:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, default=str) + "\n")
        return event
