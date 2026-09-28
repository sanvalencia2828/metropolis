from __future__ import annotations

from typing import Optional

from backend.paper_trading.metrics import compute_metrics
from backend.paper_trading.position_manager import PositionManager


def backtest_metrics(
    manager: PositionManager,
    equity_curve: list[float],
    marks: Optional[dict[str, float]] = None,
) -> dict[str, float]:
    stats = dict(compute_metrics(manager, marks))
    stats["bars"] = float(max(len(equity_curve) - 1, 0))
    stats["max_drawdown"] = max_drawdown(equity_curve or [manager.starting_cash])
    stats["sharpe"] = sharpe(equity_curve)
    return stats


def max_drawdown(curve: list[float]) -> float:
    peak = curve[0] if curve else 0.0
    worst = 0.0
    for value in curve:
        peak = max(peak, value)
        if peak > 0:
            worst = max(worst, (peak - value) / peak)
    return worst


def sharpe(curve: list[float]) -> float:
    if len(curve) < 2:
        return 0.0
    returns = []
    for previous, current in zip(curve, curve[1:]):
        if previous:
            returns.append((current / previous) - 1.0)
    if not returns:
        return 0.0
    mean = sum(returns) / len(returns)
    var = sum((item - mean) ** 2 for item in returns) / len(returns)
    if var <= 0:
        return 0.0
    return mean / (var ** 0.5)
