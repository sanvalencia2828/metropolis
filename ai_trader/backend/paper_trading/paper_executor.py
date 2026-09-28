from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from backend.decision.dossier import BUY, REJECT, Dossier
from backend.paper_trading.metrics import compute_metrics
from backend.paper_trading.paper_logger import PaperLogger
from backend.paper_trading.position_manager import Position, PositionManager, utcnow
from backend.paper_trading.reward_engine import RewardEngine


class PaperExecutor:
    def __init__(
        self,
        manager: Optional[PositionManager] = None,
        logger: Optional[PaperLogger] = None,
        rewards: Optional[RewardEngine] = None,
    ) -> None:
        self.manager = manager or PositionManager()
        self.logger = logger or PaperLogger()
        self.rewards = rewards or RewardEngine()

    def on_signal(
        self,
        dossier: Dossier,
        price: float,
        now: Optional[datetime] = None,
    ) -> dict[str, Any]:
        stamp = now or utcnow()
        chain = dossier.chain or "sol"
        address = dossier.address
        if not address or price <= 0:
            return self._skip("invalid signal", dossier, 0.0)
        if dossier.recommendation == BUY:
            opened = self.manager.open_position(
                chain=chain,
                address=address,
                price=price,
                symbol=dossier.symbol,
                now=stamp,
                dossier_score=dossier.score,
            )
            if opened is None:
                return self._skip("cannot open", dossier, 0.0)
            self.logger.log(
                "open",
                {
                    "id": opened.id,
                    "chain": chain,
                    "address": address,
                    "price": price,
                    "qty": opened.qty,
                    "score": dossier.score,
                },
            )
            return {"action": "open", "position": opened, "reward": 0.0}
        if dossier.recommendation == REJECT:
            closed = self.manager.close_position(chain, address, price, "reject", stamp)
            if closed is not None:
                return self._closed(closed)
            reward = self.rewards.reward_skip(REJECT)
            return self._skip("reject", dossier, reward)
        return self._skip("watch", dossier, 0.0)

    def on_price(
        self,
        chain: str,
        address: str,
        price: float,
        now: Optional[datetime] = None,
    ) -> Optional[dict[str, Any]]:
        position = self.manager.get(chain, address)
        if position is None or price <= 0:
            return None
        change = position.unrealized_pct(price)
        if change <= -position.stop_loss_pct:
            closed = self.manager.close_position(chain, address, price, "stop_loss", now)
            return self._closed(closed) if closed else None
        if change >= position.take_profit_pct:
            closed = self.manager.close_position(chain, address, price, "take_profit", now)
            return self._closed(closed) if closed else None
        return None

    def metrics(self, marks: Optional[dict[str, float]] = None) -> dict[str, float]:
        return compute_metrics(self.manager, marks)

    def _closed(self, position: Position) -> dict[str, Any]:
        reward = self.rewards.reward_close(position)
        self.logger.log(
            "close",
            {
                "id": position.id,
                "chain": position.chain,
                "address": position.address,
                "price": position.exit_price,
                "pnl": position.pnl,
                "pnl_pct": position.pnl_pct,
                "reason": position.close_reason,
                "reward": reward,
            },
        )
        return {"action": "close", "position": position, "reward": reward}

    def _skip(self, reason: str, dossier: Dossier, reward: float) -> dict[str, Any]:
        self.logger.log(
            "skip",
            {
                "reason": reason,
                "recommendation": dossier.recommendation,
                "address": dossier.address,
                "reward": reward,
            },
        )
        return {"action": "skip", "reason": reason, "reward": reward}
