"""Robinhood data collection stub.

Placeholder client mirroring the structure of ``solana_client.py`` so the
research/backtesting pipeline can be wired against a stable interface while
the real integration is pending. It performs no login, no credential
validation, and no network calls of any kind.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from backend.monitoring.logger import get_logger

if TYPE_CHECKING:  # zero runtime imports in this step (no pandas, no robin_stocks)
    import pandas as pd

# Interval/span values accepted by Robinhood's historical quotes endpoint;
# documented here so the future implementation has the API surface at hand.
HISTORICAL_INTERVALS = frozenset({"1minute", "5minute", "10minute"})
HISTORICAL_SPANS = frozenset({"day", "week", "month", "3month", "year", "5year", "all"})


class RobinhoodClient:
    """Stub client for Robinhood market and account data (no login)."""

    def __init__(self, config: Optional[dict[str, Any]] = None) -> None:
        self.config: dict[str, Any] = config or {}
        # get_logger() is a monitoring stub returning None until the real
        # monitoring stack lands; guard call sites before using it.
        self.logger = get_logger(__name__)

    # ------------------------------------------------------------------
    # Historical OHLCV
    # ------------------------------------------------------------------

    def get_historical_candles(
        self,
        ticker: str,
        interval: str = "5minute",
        span: str = "day",
    ) -> Optional["pd.DataFrame"]:
        """Would return OHLCV candles for a ticker as a DataFrame
        (timestamp/open/high/low/close/volume, oldest first).

        ``interval`` is the bar size (1minute/5minute/10minute) and ``span``
        the lookback window (day/week/month/...). Stub: logs a warning and
        returns None; no network call is made.
        """
        if self.logger:
            self.logger.warning(
                "RobinhoodClient.get_historical_candles is a stub; no data for %s (%s, %s)",
                ticker,
                interval,
                span,
            )
        return None

    # ------------------------------------------------------------------
    # Account positions
    # ------------------------------------------------------------------

    def get_current_positions(self) -> Optional["pd.DataFrame"]:
        """Would return the account's open positions as a DataFrame.

        Stub: logs a warning and returns None; no login is performed.
        """
        if self.logger:
            self.logger.warning("RobinhoodClient.get_current_positions is a stub; no data returned")
        return None

    # ------------------------------------------------------------------
    # Instrument lookup
    # ------------------------------------------------------------------

    def get_instruments(self, symbol: str) -> Optional[dict[str, Any]]:
        """Would return instrument metadata (id, tradability, tick sizes)
        for a ticker symbol.

        Stub: logs a warning and returns None.
        """
        if self.logger:
            self.logger.warning(
                "RobinhoodClient.get_instruments is a stub; no data for %s", symbol
            )
        return None
