from datetime import datetime

import pytest

from backend.decision.dossier import BUY, REJECT, WATCH, Dossier
from backend.paper_trading import PaperExecutor, PaperLogger, PositionManager, RewardEngine, compute_metrics


def _dossier(recommendation: str, address: str = "mint1") -> Dossier:
    return Dossier(
        chain="sol",
        address=address,
        symbol="AAA",
        features={},
        gates=[],
        passed=recommendation != REJECT,
        score=80.0 if recommendation == BUY else 50.0,
        components={},
        recommendation=recommendation,
        reasons=[],
    )


def test_open_close_and_pnl():
    manager = PositionManager(cash=1000, position_pct=0.1)
    opened = manager.open_position("sol", "mint1", 10, now=datetime(2026, 1, 1))
    assert opened is not None
    assert manager.cash == 900
    closed = manager.close_position("sol", "mint1", 12, "manual")
    assert closed is not None
    assert closed.pnl == 20
    assert closed.pnl_pct == 0.2
    assert manager.cash == 1020


def test_executor_buy_then_take_profit():
    executor = PaperExecutor(
        manager=PositionManager(cash=1000, position_pct=0.5),
        logger=PaperLogger(persist=False),
    )
    opened = executor.on_signal(_dossier(BUY), price=10)
    assert opened["action"] == "open"
    result = executor.on_price("sol", "mint1", 14)
    assert result is not None
    assert result["position"].close_reason == "take_profit"
    assert result["reward"] > 0


def test_stop_loss_and_reject_skip():
    executor = PaperExecutor(
        manager=PositionManager(cash=1000, position_pct=0.5),
        logger=PaperLogger(persist=False),
        rewards=RewardEngine(),
    )
    executor.on_signal(_dossier(BUY), price=10)
    stopped = executor.on_price("sol", "mint1", 8)
    assert stopped is not None
    assert stopped["position"].close_reason == "stop_loss"
    assert stopped["reward"] < 0
    skipped = executor.on_signal(_dossier(REJECT, "mint2"), price=3)
    assert skipped["action"] == "skip"
    assert skipped["reward"] == 0.01
    assert executor.on_signal(_dossier(WATCH, "mint3"), price=3)["action"] == "skip"


def test_metrics_win_rate():
    manager = PositionManager(cash=1000, position_pct=0.1)
    manager.open_position("sol", "a", 10)
    manager.close_position("sol", "a", 12, "tp")
    manager.open_position("sol", "b", 10)
    manager.close_position("sol", "b", 9, "sl")
    metrics = compute_metrics(manager)
    assert metrics["closed_trades"] == 2
    assert metrics["win_rate"] == 0.5
    assert metrics["realized_pnl"] == pytest.approx(9.8)
