from __future__ import annotations

from backend.decision.dossier import REJECT
from backend.paper_trading.position_manager import Position


class RewardEngine:
    def reward_close(self, position: Position) -> float:
        reward = position.pnl_pct
        if position.close_reason == "stop_loss":
            reward -= 0.01
        return round(reward, 6)

    def reward_skip(self, recommendation: str) -> float:
        if recommendation == REJECT:
            return 0.01
        return 0.0
