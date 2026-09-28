from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DrawdownGuard:
    """Tracks portfolio drawdown and raises a flag once the threshold is exceeded."""

    max_drawdown: float = 0.20
    peak_equity: float = 0.0
    current_equity: float = 0.0
    triggered: bool = False
    reason: str = ""

    def update(self, equity: float) -> float:
        if equity <= 0:
            raise ValueError("equity must be positive")

        if self.peak_equity == 0 or equity > self.peak_equity:
            self.peak_equity = equity

        self.current_equity = equity
        drawdown = 0.0 if self.peak_equity <= 0 else max(0.0, (self.peak_equity - equity) / self.peak_equity)

        self.triggered = drawdown >= self.max_drawdown
        self.reason = (
            f"Drawdown reached {drawdown:.2%} which exceeds the limit of {self.max_drawdown:.2%}."
            if self.triggered
            else ""
        )
        return drawdown
