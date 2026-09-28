from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from backend.config.settings import settings
from backend.rl.env.trading_env import ACTION_NAMES
from backend.rl.ppo.train_ppo import PPOAgent


class PPOPolicy:
    def __init__(self, agent: PPOAgent, fill: Optional[np.ndarray] = None) -> None:
        self.agent = agent
        self.fill = fill

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "PPOPolicy":
        target = path or (settings.BASE_PATH / "rl" / "models" / "ppo.npz")
        payload = np.load(target)
        agent = PPOAgent(obs_size=payload["policy_w"].shape[0], n_actions=payload["policy_w"].shape[1])
        agent.policy_w = payload["policy_w"]
        agent.policy_b = payload["policy_b"]
        agent.value_w = payload["value_w"]
        agent.value_b = float(payload["value_b"][0])
        return cls(agent, payload["fill"] if "fill" in payload.files else None)

    def act(self, state: np.ndarray) -> int:
        dist = self.agent.probs(state)[0]
        return int(np.argmax(dist))

    def recommend(self, state: np.ndarray) -> str:
        return ACTION_NAMES[self.act(state)]
