from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class ReplayBuffer:
    capacity: int = 4096
    rng: np.random.Generator | None = None

    def __post_init__(self) -> None:
        self.rng = self.rng or np.random.default_rng(0)
        self.states: list[np.ndarray] = []
        self.actions: list[int] = []
        self.rewards: list[float] = []
        self.next_states: list[np.ndarray] = []
        self.dones: list[bool] = []

    def __len__(self) -> int:
        return len(self.states)

    def add(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool,
    ) -> None:
        if len(self.states) >= self.capacity:
            self.states.pop(0)
            self.actions.pop(0)
            self.rewards.pop(0)
            self.next_states.pop(0)
            self.dones.pop(0)
        self.states.append(np.asarray(state, dtype=float))
        self.actions.append(int(action))
        self.rewards.append(float(reward))
        self.next_states.append(np.asarray(next_state, dtype=float))
        self.dones.append(bool(done))

    def sample(self, batch_size: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        size = min(batch_size, len(self.states))
        idx = self.rng.choice(len(self.states), size=size, replace=False)
        return (
            np.stack([self.states[i] for i in idx]),
            np.array([self.actions[i] for i in idx], dtype=int),
            np.array([self.rewards[i] for i in idx], dtype=float),
            np.stack([self.next_states[i] for i in idx]),
            np.array([self.dones[i] for i in idx], dtype=float),
        )
