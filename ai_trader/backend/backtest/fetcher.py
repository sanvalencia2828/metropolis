from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from backend.data_collectors.gmgn_client import GMGNClient, normalize_klines


@dataclass(frozen=True)
class Candle:
    open_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


class CandleFetcher:
    def __init__(self, client: Optional[GMGNClient] = None) -> None:
        self.client = client

    def fetch(
        self,
        address: str,
        chain: str,
        resolution: str = "1m",
        from_ts: Optional[int] = None,
        to_ts: Optional[int] = None,
    ) -> list[Candle]:
        if self.client is None:
            raise ValueError("GMGN client required to fetch candles")
        payload = self.client.get_klines(
            address,
            chain=chain,
            resolution=resolution,
            from_ts=from_ts,
            to_ts=to_ts,
        )
        return self.from_payload(payload)

    def from_payload(self, payload: Any) -> list[Candle]:
        return self.from_rows(normalize_klines(payload))

    def from_rows(self, rows: list[dict[str, Any]]) -> list[Candle]:
        candles = [row_to_candle(row) for row in rows]
        return [candle for candle in candles if candle is not None]


def row_to_candle(row: dict[str, Any]) -> Optional[Candle]:
    close = _float(row.get("close") if "close" in row else row.get("c"))
    if close is None or close <= 0:
        return None
    high = _float(row.get("high") if "high" in row else row.get("h")) or close
    low = _float(row.get("low") if "low" in row else row.get("l")) or close
    open_ = _float(row.get("open") if "open" in row else row.get("o")) or close
    volume = _float(row.get("volume") if "volume" in row else row.get("v")) or 0.0
    stamp = row.get("open_time", row.get("time", row.get("t", 0)))
    return Candle(
        open_time=_to_dt(stamp),
        open=open_,
        high=max(high, open_, close, low),
        low=min(low, open_, close, high),
        close=close,
        volume=volume,
    )


def _to_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    try:
        stamp = int(float(value))
    except (TypeError, ValueError):
        return datetime.now(timezone.utc).replace(tzinfo=None)
    if stamp > 10_000_000_000:
        stamp //= 1000
    return datetime.fromtimestamp(stamp, tz=timezone.utc).replace(tzinfo=None)


def _float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
