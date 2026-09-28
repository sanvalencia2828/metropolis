from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import numpy as np

from backend.backtest.fetcher import Candle
from backend.config.settings import settings
from backend.rl.env.trading_env import TradingEnv
from backend.rl.replay_buffer import ReplayBuffer


class DQNAgent:
    def __init__(self, obs_size: int, n_actions: int = 3, lr: float = 0.05, gamma: float = 0.99, rng: Optional[np.random.Generator] = None) -> None:
        self.obs_size = obs_size
        self.n_actions = n_actions
        self.lr = lr
        self.gamma = gamma
        self.rng = rng or np.random.default_rng(0)
        self.weights = self.rng.normal(0, 0.05, size=(obs_size, n_actions))
        self.bias = np.zeros(n_actions, dtype=float)

    def q(self, states: np.ndarray) -> np.ndarray:
        return np.atleast_2d(states) @ self.weights + self.bias

    def act(self, state: np.ndarray, epsilon: float = 0.0) -> int:
        if self.rng.random() < epsilon:
            return int(self.rng.integers(0, self.n_actions))
        return int(np.argmax(self.q(state)[0]))

    def update(self, states, actions, rewards, next_states, dones) -> float:
        q = self.q(states)
        next_q = self.q(next_states)
        targets = q.copy()
        best = np.max(next_q, axis=1)
        for i, action in enumerate(actions):
            targets[i, action] = rewards[i] + self.gamma * best[i] * (1.0 - dones[i])
        error = q - targets
        self.weights -= self.lr * (states.T @ error) / max(len(states), 1)
        self.bias -= self.lr * error.mean(axis=0)
        return float(np.mean(error ** 2))

    def save(self, path: Path, fill: np.ndarray) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(path, weights=self.weights, bias=self.bias, fill=fill)
        return path


def train_dqn(
    record: dict[str, Any],
    candles: list[Candle],
    episodes: int = 8,
    path: Optional[Path] = None,
) -> DQNAgent:
    env = TradingEnv(record, candles)
    agent = DQNAgent(env.obs_size)
    buffer = ReplayBuffer(capacity=2048, rng=agent.rng)
    state = env.reset()
    for _ in range(episodes):
        state = env.reset()
        done = False
        while not done:
            action = agent.act(state, epsilon=0.2)
            next_state, reward, done, _ = env.step(action)
            buffer.add(state, action, reward, next_state, done)
            state = next_state
            if len(buffer) >= 16:
                batch = buffer.sample(16)
                agent.update(*batch)
    target = path or (settings.BASE_PATH / "rl" / "models" / "dqn.npz")
    agent.save(target, env.fill)
    return agent
