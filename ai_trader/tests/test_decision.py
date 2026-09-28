from backend.decision.dossier import BUY, REJECT, WATCH, build_dossier
from backend.decision.gates import DevGate, HolderGate, HoneypotGate, LiquidityGate, RugGate
from backend.decision.scoring import ScoringEngine


SAFE = {
    "chain": "sol",
    "address": "mint1",
    "symbol": "AAA",
    "liquidity": 80_000,
    "holder_count": 400,
    "volume": 40_000,
    "buys": 80,
    "sells": 40,
    "price_change_percent": 20,
    "is_honeypot": False,
    "renounced": True,
    "lp_locked": True,
    "buy_tax": 2,
    "sell_tax": 2,
    "creator_percent": 2,
    "top10_percent": 18,
    "sniper_percent": 5,
}


def test_liquidity_and_holder_gates():
    assert LiquidityGate(min_liquidity=10_000).evaluate(SAFE).passed
    assert not LiquidityGate(min_liquidity=10_000).evaluate({"price": 1}).passed
    assert HolderGate(min_holders=100).evaluate(SAFE).passed
    assert not HolderGate().evaluate({"holder_count": 10}).passed


def test_honeypot_rug_dev_fail_closed():
    assert not HoneypotGate().evaluate({}).passed
    assert not HoneypotGate().evaluate({"is_honeypot": True}).passed
    assert HoneypotGate().evaluate({"is_honeypot": False}).passed
    assert not RugGate().evaluate({"renounced": False}).passed
    assert RugGate().evaluate({"renounced": True, "lp_locked": True, "buy_tax": 1}).passed
    assert not DevGate().evaluate({"creator_percent": 40}).passed
    assert DevGate().evaluate({"creator_percent": 1, "top10_percent": 10}).passed


def test_scoring_bounds():
    score = ScoringEngine().score(SAFE)
    assert 0 <= score.score <= 100
    assert score.components["not_honeypot"] == 10.0
    empty = ScoringEngine().score({})
    assert empty.score == 0.0


def test_dossier_recommendations():
    dossier = build_dossier(SAFE)
    assert dossier.passed
    assert dossier.recommendation in {BUY, WATCH}
    assert dossier.address == "mint1"
    rejected = build_dossier({**SAFE, "is_honeypot": True})
    assert rejected.recommendation == REJECT
    assert rejected.passed is False
