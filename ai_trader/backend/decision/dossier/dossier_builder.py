from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Optional, Protocol

from backend.decision.gates import default_gates
from backend.decision.scoring.scoring_engine import ScoringEngine
from backend.decision.types import GateResult, ScoreResult
from backend.features.feature_registry import registry


class Gate(Protocol):
    name: str

    def evaluate(self, record: dict[str, Any]) -> GateResult: ...


BUY = "BUY"
WATCH = "WATCH"
REJECT = "REJECT"


@dataclass(frozen=True)
class Dossier:
    chain: Optional[str]
    address: Optional[str]
    symbol: Optional[str]
    features: dict[str, Optional[float]]
    gates: list[GateResult]
    passed: bool
    score: float
    components: dict[str, float]
    recommendation: str
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["gates"] = [asdict(gate) for gate in self.gates]
        return payload


class DossierBuilder:
    def __init__(
        self,
        gates: Optional[list[Gate]] = None,
        engine: Optional[ScoringEngine] = None,
        buy_score: float = 70.0,
        watch_score: float = 40.0,
    ) -> None:
        self.gates = gates or default_gates()
        self.engine = engine or ScoringEngine()
        self.buy_score = buy_score
        self.watch_score = watch_score

    def build(self, record: dict[str, Any]) -> Dossier:
        gate_results = [gate.evaluate(record) for gate in self.gates]
        scored: ScoreResult = self.engine.score(record)
        passed = all(result.passed for result in gate_results)
        reasons = [result.reason for result in gate_results if not result.passed]
        recommendation = self._recommend(passed, scored.score)
        if recommendation == REJECT and not reasons:
            reasons = [f"score {scored.score} below {self.watch_score}"]
        return Dossier(
            chain=record.get("chain"),
            address=record.get("address") or record.get("token_address") or record.get("mint"),
            symbol=record.get("symbol"),
            features=registry.extract(record),
            gates=gate_results,
            passed=passed,
            score=scored.score,
            components=scored.components,
            recommendation=recommendation,
            reasons=reasons,
        )

    def _recommend(self, passed: bool, score: float) -> str:
        if not passed:
            return REJECT
        if score >= self.buy_score:
            return BUY
        if score >= self.watch_score:
            return WATCH
        return REJECT


def build_dossier(record: dict[str, Any]) -> Dossier:
    return DossierBuilder().build(record)
