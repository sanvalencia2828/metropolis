from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import numpy as np

from backend.backtest.fetcher import Candle
from backend.config.settings import settings
from backend.rl.env.trading_env import TradingEnv


def softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - np.max(logits, axis=-1, keepdims=True)
    exp = np.exp(shifted)
    return exp / np.sum(exp, axis=-1, keepdims=True)


class PPOAgent:
    def __init__(self, obs_size: int, n_actions: int = 3, lr: float = 0.05, gamma: float = 0.99, clip: float = 0.2, rng: Optional[np.random.Generator] = None) -> None:
        self.obs_size = obs_size
        self.n_actions = n_actions
        self.lr = lr
        self.gamma = gamma
        self.clip = clip
        self.rng = rng or np.random.default_rng(1)
        self.policy_w = self.rng.normal(0, 0.05, size=(obs_size, n_actions))
        self.policy_b = np.zeros(n_actions, dtype=float)
        self.value_w = self.rng.normal(0, 0.05, size=obs_size)
        self.value_b = 0.0

    def probs(self, states: np.ndarray) -> np.ndarray:
        return softmax(np.atleast_2d(states) @ self.policy_w + self.policy_b)

    def value(self, states: np.ndarray) -> np.ndarray:
        return np.atleast_2d(states) @ self.value_w + self.value_b

    def act(self, state: np.ndarray) -> tuple[int, float]:
        dist = self.probs(state)[0]
        action = int(self.rng.choice(self.n_actions, p=dist))
        return action, float(dist[action])

    def update(self, states, actions, rewards, old_probs) -> None:
        values = self.value(states)
        returns = np.zeros_like(rewards)
        acc = 0.0
        for i in range(len(rewards) - 1, -1, -1):
            acc = rewards[i] + self.gamma * acc
            returns[i] = acc
        advantages = returns - values
        dist = self.probs(states)
        taken = dist[np.arange(len(actions)), actions]
        ratio = taken / np.clip(old_probs, 1e-8, 1.0)
        clipped = np.clip(ratio, 1.0 - self.clip, 1.0 + self.clip)
        objective = np.minimum(ratio * advantages, clipped * advantages)
        grad_scale = (-objective).reshape(-1, 1)
        onehot = np.zeros_like(dist)
        onehot[np.arange(len(actions)), actions] = 1.0
        policy_error = (dist - onehot) * grad_scale
        self.policy_w -= self.lr * (states.T @ policy_error) / max(len(states), 1)
        self.policy_b -= self.lr * policy_error.mean(axis=0)
        value_error = values - returns
        self.value_w -= self.lr * (states.T @ value_error) / max(len(states), 1)
        self.value_b -= self.lr * float(value_error.mean())

    def save(self, path: Path, fill: np.ndarray) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(
            path,
            policy_w=self.policy_w,
            policy_b=self.policy_b,
            value_w=self.value_w,
            value_b=np.array([self.value_b]),
            fill=fill,
        )
        return path


def train_ppo(
    record: dict[str, Any],
    candles: list[Candle],
    episodes: int = 8,
    path: Optional[Path] = None,
) -> PPOAgent:
    env = TradingEnv(record, candles)
    agent = PPOAgent(env.obs_size)
    for _ in range(episodes):
        state = env.reset()
        done = False
        states, actions, rewards, probs = [], [], [], []
        while not done:
            action, prob = agent.act(state)
            next_state, reward, done, _ = env.step(action)
            states.append(state)
            actions.append(action)
            rewards.append(reward)
            probs.append(prob)
            state = next_state
        agent.update(np.stack(states), np.array(actions), np.array(rewards), np.array(probs))
    target = path or (settings.BASE_PATH / "rl" / "models" / "ppo.npz")
    agent.save(target, env.fill)
    return agent
