from backend.features.feature_registry import registry, to_frame, write_training_csv


def test_extract_numeric_features():
    row = registry.extract(
        {
            "price": "1.25",
            "buys": 4,
            "sells": 2,
            "is_honeypot": False,
            "renounced": True,
        }
    )
    assert row["price"] == 1.25
    assert row["buy_sell_ratio"] == 2.0
    assert row["is_honeypot"] == 0.0
    assert row["renounced"] == 1.0
    assert "liquidity" in registry.names()


def test_write_training_csv(tmp_path):
    target = tmp_path / "features.csv"
    path = write_training_csv([{"address": "abc", "chain": "sol", "price": 3}], path=target)
    frame = to_frame([{"address": "abc", "price": 3}])
    assert path.exists()
    assert frame.loc[0, "address"] == "abc"
    assert "price" in path.read_text(encoding="utf-8")
