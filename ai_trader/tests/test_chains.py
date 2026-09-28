import pytest

from backend.config.chains import get_chain, list_supported_chains


def test_supported_chains_include_solana():
    assert "sol" in list_supported_chains()
    chain = get_chain("SOL")
    assert chain.slug == "sol"
    assert chain.is_evm is False


def test_unknown_chain_raises():
    with pytest.raises(ValueError):
        get_chain("nope")
