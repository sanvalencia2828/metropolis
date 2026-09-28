from __future__ import annotations

from dataclasses import dataclass

from .drawdown_guard import DrawdownGuard
from .exposure_manager import ExposureManager
from .kill_switch import KillSwitch


@dataclass(frozen=True)
class RiskAssessment:
    allowed: bool
    reason: str
    drawdown: float
    exposure: float


class RiskManager:
    """Coordinates the drawdown, exposure, and kill-switch checks for a trading strategy."""

    def __init__(
        self,
        *,
        max_daily_drawdown: float = 0.20,
        max_portfolio_exposure: float = 0.50,
    ) -> None:
        self.drawdown_guard = DrawdownGuard(max_drawdown=max_daily_drawdown)
        self.exposure_manager = ExposureManager(max_total_exposure=max_portfolio_exposure)
        self.kill_switch = KillSwitch()

    def evaluate(self, equity: float, new_exposure: float = 0.0) -> RiskAssessment:
        drawdown = self.drawdown_guard.update(equity)
        total_exposure = self.exposure_manager.total_exposure() + new_exposure

        if self.kill_switch.active:
            return RiskAssessment(False, self.kill_switch.reason, drawdown, total_exposure)

        if drawdown >= self.drawdown_guard.max_drawdown:
            self.kill_switch.trigger(self.drawdown_guard.reason)
            return RiskAssessment(False, self.drawdown_guard.reason, drawdown, total_exposure)

        if total_exposure > self.exposure_manager.max_total_exposure:
            reason = (
                f"Exposure {total_exposure:.2%} exceeds the max portfolio exposure "
                f"of {self.exposure_manager.max_total_exposure:.2%}."
            )
            return RiskAssessment(False, reason, drawdown, total_exposure)

        return RiskAssessment(True, "Within risk limits", drawdown, total_exposure)

    def add_exposure(self, additional_exposure: float) -> bool:
        if self.kill_switch.active:
            return False
        if not self.exposure_manager.can_add(additional_exposure):
            return False
        self.exposure_manager.add_exposure(additional_exposure)
        return True
