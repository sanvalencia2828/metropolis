from __future__ import annotations

from typing import Optional

from backend.paper_trading.position_manager import PositionManager


def compute_metrics(
    manager: PositionManager,
    marks: Optional[dict[str, float]] = None,
) -> dict[str, float]:
    closed = manager.closed
    wins = [pos for pos in closed if pos.pnl > 0]
    losses = [pos for pos in closed if pos.pnl < 0]
    realized = sum(pos.pnl for pos in closed)
    gross_win = sum(pos.pnl for pos in wins)
    gross_loss = abs(sum(pos.pnl for pos in losses))
    equity = manager.equity(marks)
    peak = max([manager.starting_cash] + _equity_curve(manager, marks))
    drawdown = 0.0 if peak <= 0 else (peak - equity) / peak
    return {
        "starting_cash": manager.starting_cash,
        "cash": manager.cash,
        "equity": equity,
        "open_positions": float(len(manager.positions)),
        "closed_trades": float(len(closed)),
        "realized_pnl": realized,
        "win_rate": 0.0 if not closed else len(wins) / len(closed),
        "avg_win": 0.0 if not wins else gross_win / len(wins),
        "avg_loss": 0.0 if not losses else -(gross_loss / len(losses)),
        "profit_factor": 0.0 if gross_loss == 0 else gross_win / gross_loss,
        "max_drawdown": max(0.0, drawdown),
        "return_pct": 0.0 if manager.starting_cash == 0 else (equity / manager.starting_cash) - 1.0,
    }


def _equity_curve(manager: PositionManager, marks: Optional[dict[str, float]]) -> list[float]:
    cash = manager.starting_cash
    curve = [cash]
    for position in manager.closed:
        cash += position.pnl
        curve.append(cash)
    curve.append(manager.equity(marks))
    return curve
