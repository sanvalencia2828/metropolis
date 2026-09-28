from __future__ import annotations

import time
from typing import Any, Callable, Optional

import httpx

from backend.config.chains import get_chain
from backend.config.settings import settings

PERIODS = ("1m", "5m", "1h", "6h", "24h")


class GMGNError(Exception):
    """Raised when a GMGN request fails."""


class GMGNClient:
    """HTTP client for the public GMGN quotation API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[int] = None,
        retry_count: Optional[int] = None,
        client: Optional[httpx.Client] = None,
        backoff: float = 0.4,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.base_url = (base_url or settings.GMGN_BASE_URL).rstrip("/")
        self.api_key = api_key if api_key is not None else settings.GMGN_API_KEY
        self.timeout = timeout if timeout is not None else settings.COLLECTOR_TIMEOUT
        self.retry_count = retry_count if retry_count is not None else settings.COLLECTOR_RETRY_COUNT
        self.backoff = backoff
        self._sleep = sleep
        self._owns_client = client is None
        self._client = client or httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            headers=self._headers(),
        )

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "ai-trader/0.1",
            "Referer": f"{self.base_url}/",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "GMGNClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _chain(self, chain: Optional[str]) -> str:
        return get_chain(chain or settings.DEFAULT_CHAIN).slug

    def _get(self, path: str, params: Optional[dict[str, Any]] = None) -> Any:
        last_error: Optional[Exception] = None
        for attempt in range(self.retry_count):
            retryable = True
            try:
                response = self._client.get(path, params=params)
                retryable = response.status_code == 429 or response.status_code >= 500
                response.raise_for_status()
                return self._unwrap(response)
            except GMGNError:
                raise
            except httpx.HTTPError as exc:
                last_error = exc
                if not retryable or attempt + 1 >= self.retry_count:
                    break
                self._sleep(self.backoff * (attempt + 1))
        raise GMGNError(
            f"GMGN request failed after {self.retry_count} attempts: {last_error}"
        ) from last_error

    def _unwrap(self, response: httpx.Response) -> Any:
        try:
            payload = response.json()
        except ValueError as exc:
            raise GMGNError("GMGN returned a non-JSON response") from exc
        if isinstance(payload, dict) and "code" in payload and payload["code"] not in (0, "0"):
            message = payload.get("msg") or payload.get("message") or "GMGN request failed"
            raise GMGNError(str(message))
        if isinstance(payload, dict) and "data" in payload and "code" in payload:
            return payload["data"]
        return payload

    def get_trending(
        self,
        chain: Optional[str] = None,
        period: str = "1h",
        limit: int = 50,
    ) -> Any:
        self._validate_period(period)
        slug = self._chain(chain)
        return self._get(
            f"/defi/quotation/v1/rank/{slug}/swaps/{period}",
            {"limit": limit, "orderby": "volume", "direction": "desc"},
        )

    def get_token(self, address: str, chain: Optional[str] = None) -> Any:
        slug = self._chain(chain)
        return self._get(f"/defi/quotation/v1/tokens/{slug}/{address}")

    def get_token_security(self, address: str, chain: Optional[str] = None) -> Any:
        slug = self._chain(chain)
        return self._get(f"/defi/quotation/v1/tokens/security/{slug}/{address}")

    def get_trades(
        self,
        address: str,
        chain: Optional[str] = None,
        limit: int = 100,
    ) -> Any:
        slug = self._chain(chain)
        return self._get(f"/defi/quotation/v1/trades/{slug}/{address}", {"limit": limit})

    def get_klines(
        self,
        address: str,
        chain: Optional[str] = None,
        resolution: str = "1m",
        from_ts: Optional[int] = None,
        to_ts: Optional[int] = None,
    ) -> Any:
        slug = self._chain(chain)
        params: dict[str, Any] = {"resolution": resolution}
        if from_ts is not None:
            params["from"] = from_ts
        if to_ts is not None:
            params["to"] = to_ts
        return self._get(f"/defi/quotation/v1/tokens/kline/{slug}/{address}", params)

    def get_top_traders(
        self,
        address: str,
        chain: Optional[str] = None,
        limit: int = 50,
    ) -> Any:
        slug = self._chain(chain)
        return self._get(
            f"/defi/quotation/v1/tokens/top_traders/{slug}/{address}",
            {"limit": limit, "orderby": "profit", "direction": "desc"},
        )

    def get_new_pairs(self, chain: Optional[str] = None, limit: int = 50) -> Any:
        slug = self._chain(chain)
        return self._get(f"/defi/quotation/v1/pairs/{slug}/new_pairs", {"limit": limit})

    @staticmethod
    def _validate_period(period: str) -> None:
        if period not in PERIODS:
            raise ValueError(f"Unsupported period '{period}'. Expected one of {PERIODS}")


def extract_items(payload: Any) -> list[dict[str, Any]]:
    """Pull a list of records out of common GMGN response shapes."""
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("rank", "list", "tokens", "pairs", "trades", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def normalize_klines(payload: Any) -> list[dict[str, Any]]:
    """Normalize GMGN kline payloads into open/high/low/close rows."""
    items = extract_items(payload)
    if items and any(key in items[0] for key in ("open", "o", "close", "c")):
        return items
    if not isinstance(payload, dict):
        return []
    times = payload.get("t") or payload.get("time") or []
    if not isinstance(times, list):
        return []
    opens = payload.get("o") or payload.get("open") or []
    highs = payload.get("h") or payload.get("high") or []
    lows = payload.get("l") or payload.get("low") or []
    closes = payload.get("c") or payload.get("close") or []
    volumes = payload.get("v") or payload.get("volume") or []
    rows: list[dict[str, Any]] = []
    for index, open_time in enumerate(times):
        rows.append(
            {
                "open_time": open_time,
                "open": _series_value(opens, index),
                "high": _series_value(highs, index),
                "low": _series_value(lows, index),
                "close": _series_value(closes, index),
                "volume": _series_value(volumes, index),
            }
        )
    return rows


def _series_value(series: Any, index: int) -> Any:
    if isinstance(series, list) and index < len(series):
        return series[index]
    return None
