from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from backend.config.settings import settings
from backend.rl.dqn.train_dqn import DQNAgent
from backend.rl.env.trading_env import ACTION_NAMES


class DQNPolicy:
    def __init__(self, agent: DQNAgent, fill: Optional[np.ndarray] = None) -> None:
        self.agent = agent
        self.fill = fill

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "DQNPolicy":
        target = path or (settings.BASE_PATH / "rl" / "models" / "dqn.npz")
        payload = np.load(target)
        agent = DQNAgent(obs_size=payload["weights"].shape[0], n_actions=payload["weights"].shape[1])
        agent.weights = payload["weights"]
        agent.bias = payload["bias"]
        return cls(agent, payload["fill"] if "fill" in payload.files else None)

    def act(self, state: np.ndarray) -> int:
        return self.agent.act(state, epsilon=0.0)

    def recommend(self, state: np.ndarray) -> str:
        return ACTION_NAMES[self.act(state)]
