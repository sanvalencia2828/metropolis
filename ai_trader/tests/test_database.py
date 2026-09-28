import pandas as pd
from sqlalchemy import select

from backend.database.crud import save_klines_to_db
from backend.database.models import (
    Candle,
    init_db,
    list_snapshots,
    resolve_database_url,
    save_candles,
    save_token_snapshots,
    save_trades,
)
from backend.database.session import get_session


def test_resolve_relative_sqlite_url():
    resolved = resolve_database_url("sqlite:///./data/storage/ai_trader.db")
    assert "\\" not in resolved
    assert resolved.endswith("data/storage/ai_trader.db")


def test_save_and_list_snapshots(tmp_path):
    url = f"sqlite:///{(tmp_path / 't.db').as_posix()}"
    init_db(url)
    saved = save_token_snapshots(
        [
            {"address": "mint1", "symbol": "AAA", "price": "1.5", "liquidity": 10, "holder_count": "3"},
            {"symbol": "skip"},
        ],
        "sol",
        url=url,
    )
    assert saved == 1
    rows = list_snapshots("sol", url=url)
    assert rows[0].symbol == "AAA"
    assert rows[0].price == 1.5
    assert rows[0].holder_count == 3


def test_save_trades_and_candles(tmp_path):
    url = f"sqlite:///{(tmp_path / 't.db').as_posix()}"
    init_db(url)
    assert save_trades([{"tx_hash": "0x1", "side": "buy", "price": 2}], "eth", "token", url=url) == 1
    assert save_candles([{"timestamp": 10, "open": 1, "close": 2}], "eth", "token", url=url) == 1


def test_save_klines_to_db_upserts_overlapping_rows(tmp_path):
    url = f"sqlite:///{(tmp_path / 'k.db').as_posix()}"
    init_db(url)
    frame = pd.DataFrame(
        {
            "timestamp": [100, 200],
            "open": [1.0, 2.0],
            "high": [1.5, 2.5],
            "low": [0.5, 1.5],
            "close": [1.2, 2.2],
            "volume": [10.0, 20.0],
        }
    )
    assert save_klines_to_db(frame, "token", "1m", url=url) == 2

    # overlapping download: ts 100 already exists (updated), 300 is new (inserted)
    overlap = pd.DataFrame(
        {
            "timestamp": [100, 300],
            "open": [9.0, 3.0],
            "high": [9.5, 3.5],
            "low": [8.5, 2.5],
            "close": [9.9, 3.3],
            "volume": [11.0, 30.0],
        }
    )
    assert save_klines_to_db(overlap, "token", "1m", url=url) == 2

    with get_session(url) as session:
        candles = {c.timestamp: c for c in session.scalars(select(Candle))}
    assert set(candles) == {100, 200, 300}  # no duplicates despite the overlap
    assert candles[100].close == 9.9  # existing row was updated
    assert candles[300].close == 3.3


def test_save_klines_to_db_empty_frame(tmp_path):
    url = f"sqlite:///{(tmp_path / 'e.db').as_posix()}"
    assert save_klines_to_db(pd.DataFrame(), "token", "1m", url=url) == 0
