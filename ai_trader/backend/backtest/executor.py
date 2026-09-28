from __future__ import annotations

from typing import Any, Optional

from backend.backtest.config import BacktestConfig
from backend.backtest.fetcher import Candle
from backend.paper_trading.paper_executor import PaperExecutor
from backend.paper_trading.paper_logger import PaperLogger
from backend.paper_trading.position_manager import PositionManager


class BacktestExecutor:
    def __init__(
        self,
        config: Optional[BacktestConfig] = None,
        executor: Optional[PaperExecutor] = None,
    ) -> None:
        self.config = config or BacktestConfig()
        self.executor = executor or PaperExecutor(
            manager=PositionManager(
                cash=self.config.cash,
                max_positions=self.config.max_positions,
                position_pct=self.config.position_pct,
            ),
            logger=PaperLogger(persist=False),
        )

    def apply_signal(self, dossier: Any, price: float, now=None) -> dict[str, Any]:
        fill = self._buy_fill(price)
        result = self.executor.on_signal(dossier, fill, now=now)
        position = result.get("position")
        if result.get("action") == "open" and position is not None:
            position.stop_loss_pct = self.config.stop_loss_pct
            position.take_profit_pct = self.config.take_profit_pct
        return result

    def apply_bar(self, chain: str, address: str, bar: Candle) -> Optional[dict[str, Any]]:
        position = self.executor.manager.get(chain, address)
        if position is None:
            return None
        stop = position.entry_price * (1.0 - position.stop_loss_pct)
        take = position.entry_price * (1.0 + position.take_profit_pct)
        if bar.low <= stop:
            return self.executor.on_price(chain, address, self._sell_fill(stop), now=bar.open_time)
        if bar.high >= take:
            return self.executor.on_price(chain, address, self._sell_fill(take), now=bar.open_time)
        return None

    def close_open(self, chain: str, address: str, price: float, now=None) -> Optional[dict[str, Any]]:
        closed = self.executor.manager.close_position(
            chain,
            address,
            self._sell_fill(price),
            "eod",
            now,
        )
        if closed is None:
            return None
        return self.executor._closed(closed)

    def _buy_fill(self, price: float) -> float:
        return price * (1.0 + self.config.fee_bps / 10_000.0)

    def _sell_fill(self, price: float) -> float:
        return price * (1.0 - self.config.fee_bps / 10_000.0)
