from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ChainConfig:
    name: str
    slug: str
    symbol: str
    native_token: str
    chain_id: Optional[int]
    explorer_url: str
    is_evm: bool = True


SUPPORTED_CHAINS: Dict[str, ChainConfig] = {
    "sol": ChainConfig(
        name="Solana",
        slug="sol",
        symbol="SOL",
        native_token="SOL",
        chain_id=None,
        explorer_url="https://solscan.io",
        is_evm=False,
    ),
    "eth": ChainConfig(
        name="Ethereum",
        slug="eth",
        symbol="ETH",
        native_token="ETH",
        chain_id=1,
        explorer_url="https://etherscan.io",
        is_evm=True,
    ),
    "base": ChainConfig(
        name="Base",
        slug="base",
        symbol="ETH",
        native_token="ETH",
        chain_id=8453,
        explorer_url="https://basescan.org",
        is_evm=True,
    ),
    "bsc": ChainConfig(
        name="BNB Smart Chain",
        slug="bsc",
        symbol="BNB",
        native_token="BNB",
        chain_id=56,
        explorer_url="https://bscscan.com",
        is_evm=True,
    ),
    "arb": ChainConfig(
        name="Arbitrum One",
        slug="arb",
        symbol="ETH",
        native_token="ETH",
        chain_id=42161,
        explorer_url="https://arbiscan.io",
        is_evm=True,
    ),
}


def get_chain(slug: str) -> ChainConfig:
    """Retrieve chain configuration by slug (e.g., 'sol', 'eth')."""
    normalized = slug.lower().strip()
    if normalized not in SUPPORTED_CHAINS:
        raise ValueError(
            f"Unsupported chain '{slug}'. Supported chains: {list_supported_chains()}"
        )
    return SUPPORTED_CHAINS[normalized]


def list_supported_chains() -> List[str]:
    """Return list of supported chain slugs."""
    return list(SUPPORTED_CHAINS.keys())
