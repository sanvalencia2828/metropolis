from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExposureManager:
    """Tracks aggregate portfolio exposure as a fraction of account equity."""

    max_total_exposure: float = 0.50
    exposures: list[float] = field(default_factory=list)

    def total_exposure(self) -> float:
        return sum(self.exposures)

    def available_capacity(self) -> float:
        return max(0.0, self.max_total_exposure - self.total_exposure())

    def can_add(self, additional_exposure: float) -> bool:
        if additional_exposure < 0:
            raise ValueError("additional_exposure cannot be negative")
        return self.total_exposure() + additional_exposure <= self.max_total_exposure

    def add_exposure(self, additional_exposure: float) -> bool:
        if not self.can_add(additional_exposure):
            return False
        self.exposures.append(additional_exposure)
        return True

    def reset(self) -> None:
        self.exposures.clear()
