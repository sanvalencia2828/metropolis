from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from backend.config.settings import settings
from backend.paper_trading.position_manager import Position


@dataclass
class BacktestReport:
    chain: str
    address: str
    symbol: Optional[str]
    metrics: dict[str, float]
    equity_curve: list[float]
    actions: list[dict[str, Any]]
    trades: list[Position]

    def to_dict(self) -> dict[str, Any]:
        return {
            "chain": self.chain,
            "address": self.address,
            "symbol": self.symbol,
            "metrics": self.metrics,
            "equity_curve": self.equity_curve,
            "trades": [
                {
                    "id": trade.id,
                    "entry_price": trade.entry_price,
                    "exit_price": trade.exit_price,
                    "pnl": trade.pnl,
                    "pnl_pct": trade.pnl_pct,
                    "reason": trade.close_reason,
                }
                for trade in self.trades
            ],
            "actions": [
                {
                    "action": item.get("action"),
                    "reason": item.get("reason") or getattr(item.get("position"), "close_reason", None),
                    "reward": item.get("reward"),
                }
                for item in self.actions
            ],
        }

    def summary(self) -> str:
        metrics = self.metrics
        return (
            f"{self.chain}:{self.address} trades={int(metrics.get('closed_trades', 0))} "
            f"return={metrics.get('return_pct', 0.0):.2%} "
            f"win={metrics.get('win_rate', 0.0):.2%} "
            f"dd={metrics.get('max_drawdown', 0.0):.2%}"
        )

    def write(self, path: Optional[Path] = None) -> Path:
        target = path or (settings.STORAGE_PATH / "backtests" / f"{self.chain}_{self.address}.json")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), default=str, indent=2), encoding="utf-8")
        return target
