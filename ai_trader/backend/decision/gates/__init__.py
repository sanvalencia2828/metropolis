from .dev_gate import DevGate
from .holder_gate import HolderGate
from .honeypot_gate import HoneypotGate
from .liquidity_gate import LiquidityGate
from .rug_gate import RugGate

__all__ = [
    "DevGate",
    "HolderGate",
    "HoneypotGate",
    "LiquidityGate",
    "RugGate",
    "default_gates",
]


def default_gates() -> list[object]:
    return [
        LiquidityGate(),
        HolderGate(),
        HoneypotGate(),
        RugGate(),
        DevGate(),
    ]
