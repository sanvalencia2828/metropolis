from __future__ import annotations


class KillSwitch:
    """Emergency switch that blocks new trades when risk limits are breached."""

    def __init__(self) -> None:
        self._active = False
        self.reason = ""

    @property
    def active(self) -> bool:
        return self._active

    def trigger(self, reason: str = "Risk limit breached") -> None:
        self._active = True
        self.reason = reason

    def reset(self) -> None:
        self._active = False
        self.reason = ""

    def __bool__(self) -> bool:
        return self.active
