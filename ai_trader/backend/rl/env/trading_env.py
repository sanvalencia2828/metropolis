from __future__ import annotations

from typing import Any, Optional

import numpy as np

from backend.backtest.config import BacktestConfig
from backend.backtest.executor import BacktestExecutor
from backend.backtest.fetcher import Candle
from backend.decision.dossier import BUY, REJECT, WATCH, Dossier
from backend.decision.gates import default_gates
from backend.ml.training.feature_builder import FeatureBuilder, impute
from backend.paper_trading.paper_executor import PaperExecutor
from backend.paper_trading.paper_logger import PaperLogger
from backend.paper_trading.position_manager import PositionManager

HOLD, BUY_ACT, SELL = 0, 1, 2
ACTION_NAMES = ("HOLD", "BUY", "SELL")


class TradingEnv:
    def __init__(
        self,
        record: dict[str, Any],
        candles: list[Candle],
        config: Optional[BacktestConfig] = None,
        builder: Optional[FeatureBuilder] = None,
    ) -> None:
        if not candles:
            raise ValueError("candles required")
        self.record = dict(record)
        self.candles = candles
        self.config = config or BacktestConfig()
        self.builder = builder or FeatureBuilder()
        self.chain = str(record.get("chain") or self.config.chain)
        self.address = str(record.get("address") or record.get("token_address") or record.get("mint") or "")
        self.n_actions = 3
        self.obs_size = len(self.builder.columns) + 3
        self.fill = np.zeros(len(self.builder.columns), dtype=float)
        self._executor: Optional[BacktestExecutor] = None
        self._index = 0
        self._equity = self.config.cash

    def reset(self) -> np.ndarray:
        self._executor = BacktestExecutor(
            self.config,
            executor=PaperExecutor(
                manager=PositionManager(
                    cash=self.config.cash,
                    max_positions=self.config.max_positions,
                    position_pct=self.config.position_pct,
                ),
                logger=PaperLogger(persist=False),
            ),
        )
        self._index = 0
        self._equity = self.config.cash
        raw = self.builder.matrix([self._snapshot()])
        _, self.fill = impute(raw)
        return self._obs()

    def step(self, action: int) -> tuple[np.ndarray, float, bool, dict[str, Any]]:
        if self._executor is None:
            self.reset()
        assert self._executor is not None
        bar = self.candles[self._index]
        before = self._mark_equity(bar.close)
        risk = self._executor.apply_bar(self.chain, self.address, bar)
        chosen = int(action)
        penalty = 0.0
        if chosen == BUY_ACT and not self._gates_ok():
            chosen = HOLD
            penalty = -0.01
        result = self._executor.apply_signal(self._dossier(chosen), bar.close, now=bar.open_time)
        done = self._index >= len(self.candles) - 1
        if done and self._executor.executor.manager.get(self.chain, self.address):
            closed = self._executor.close_open(self.chain, self.address, bar.close, now=bar.open_time)
            if closed:
                result = closed
        after = self._mark_equity(bar.close)
        reward = (after - before) / max(self.config.cash, 1.0) + penalty
        if result and result.get("action") == "close":
            reward += float(result.get("reward") or 0.0)
        self._equity = after
        if not done:
            self._index += 1
        return self._obs(), float(reward), done, {"action": ACTION_NAMES[chosen], "result": result}

    def _obs(self) -> np.ndarray:
        features, _ = impute(self.builder.matrix([self._snapshot()]), self.fill)
        position = self._executor.executor.manager.get(self.chain, self.address) if self._executor else None
        price = self.candles[self._index].close
        in_pos = 1.0 if position else 0.0
        unrealized = position.unrealized_pct(price) if position else 0.0
        cash = self._executor.executor.manager.cash if self._executor else self.config.cash
        extras = np.array([in_pos, unrealized, cash / max(self.config.cash, 1.0)], dtype=float)
        return np.concatenate([features[0], extras])

    def _snapshot(self) -> dict[str, Any]:
        bar = self.candles[self._index]
        snapshot = dict(self.record)
        snapshot["chain"] = self.chain
        snapshot["address"] = self.address
        snapshot["price"] = bar.close
        snapshot.setdefault("volume", bar.volume)
        return snapshot

    def _gates_ok(self) -> bool:
        return all(gate.evaluate(self._snapshot()).passed for gate in default_gates())

    def _dossier(self, action: int) -> Dossier:
        recommendation = {HOLD: WATCH, BUY_ACT: BUY, SELL: REJECT}[action]
        return Dossier(
            chain=self.chain,
            address=self.address,
            symbol=self.record.get("symbol"),
            features={},
            gates=[],
            passed=action != SELL,
            score=70.0 if action == BUY_ACT else 50.0,
            components={},
            recommendation=recommendation,
            reasons=[],
        )

    def _mark_equity(self, price: float) -> float:
        if self._executor is None:
            return self.config.cash
        return self._executor.executor.manager.equity({f"{self.chain}:{self.address}": price})
