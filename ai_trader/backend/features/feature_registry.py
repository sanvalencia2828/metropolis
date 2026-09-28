from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

import pandas as pd

from backend.config.settings import settings

FeatureFn = Callable[[dict[str, Any]], Optional[float]]


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    description: str
    extractor: FeatureFn


class FeatureRegistry:
    def __init__(self) -> None:
        self._features: dict[str, FeatureSpec] = {}

    def register(self, name: str, description: str) -> Callable[[FeatureFn], FeatureFn]:
        def decorator(fn: FeatureFn) -> FeatureFn:
            self._features[name] = FeatureSpec(name=name, description=description, extractor=fn)
            return fn

        return decorator

    def extract(self, record: dict[str, Any]) -> dict[str, Optional[float]]:
        return {name: spec.extractor(record) for name, spec in self._features.items()}

    def names(self) -> list[str]:
        return list(self._features.keys())

    def specs(self) -> list[FeatureSpec]:
        return list(self._features.values())


def _num(record: dict[str, Any], *keys: str) -> Optional[float]:
    for key in keys:
        if key not in record or record[key] is None or record[key] == "":
            continue
        try:
            return float(record[key])
        except (TypeError, ValueError):
            continue
    return None


def _flag(record: dict[str, Any], *keys: str) -> Optional[float]:
    for key in keys:
        if key not in record or record[key] is None:
            continue
        value = record[key]
        if isinstance(value, bool):
            return 1.0 if value else 0.0
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


registry = FeatureRegistry()


@registry.register("price", "Last traded price")
def price(record: dict[str, Any]) -> Optional[float]:
    return _num(record, "price", "price_usd")


@registry.register("liquidity", "Pool liquidity in USD")
def liquidity(record: dict[str, Any]) -> Optional[float]:
    return _num(record, "liquidity", "liquidity_usd")


@registry.register("volume", "Trading volume")
def volume(record: dict[str, Any]) -> Optional[float]:
    return _num(record, "volume", "volume_24h", "volume_usd")


@registry.register("market_cap", "Market cap")
def market_cap(record: dict[str, Any]) -> Optional[float]:
    return _num(record, "market_cap", "marketcap")


@registry.register("holder_count", "Holder count")
def holder_count(record: dict[str, Any]) -> Optional[float]:
    return _num(record, "holder_count", "holders")


@registry.register("buy_sell_ratio", "Buy count divided by sell count")
def buy_sell_ratio(record: dict[str, Any]) -> Optional[float]:
    buys = _num(record, "buys", "buy_count")
    sells = _num(record, "sells", "sell_count")
    if buys is None or sells is None or sells == 0:
        return None
    return buys / sells


@registry.register("price_change_percent", "Price change percent")
def price_change_percent(record: dict[str, Any]) -> Optional[float]:
    return _num(record, "price_change_percent", "price_change_percent1h", "change")


@registry.register("is_honeypot", "1 when the token is flagged as a honeypot")
def is_honeypot(record: dict[str, Any]) -> Optional[float]:
    return _flag(record, "is_honeypot", "honeypot")


@registry.register("renounced", "1 when mint authority is renounced")
def renounced(record: dict[str, Any]) -> Optional[float]:
    return _flag(record, "renounced", "renounced_mint")


def to_frame(records: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for record in records:
        row = registry.extract(record)
        row["chain"] = record.get("chain")
        row["address"] = record.get("address") or record.get("token_address") or record.get("mint")
        rows.append(row)
    return pd.DataFrame(rows)


def write_training_csv(
    records: list[dict[str, Any]],
    path: Optional[Path] = None,
) -> Path:
    target = path or (settings.TRAINING_DATA_PATH / "features.csv")
    target.parent.mkdir(parents=True, exist_ok=True)
    to_frame(records).to_csv(target, index=False)
    return target
