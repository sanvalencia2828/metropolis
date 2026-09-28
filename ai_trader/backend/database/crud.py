"""CRUD helpers for kline (OHLCV) persistence."""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from backend.database.models import Candle, init_db
from backend.database.session import get_session
from backend.monitoring.logger import get_logger

# get_logger() is a monitoring stub returning None until the real monitoring
# stack lands, so every call site must guard before using the logger.
logger = get_logger(__name__)


def save_klines_to_db(
    df: pd.DataFrame,
    token_address: str,
    timeframe: str,
    url: Optional[str] = None,
) -> Optional[int]:
    """Upsert OHLCV rows for a token/timeframe.

    Existing (token_address, timestamp, timeframe) rows are UPDATEd and new
    timestamps INSERTed, so overlapping downloads never duplicate data or
    trip the uix_token_tf_ts constraint. Returns the number of rows written,
    or None when the database fails (the error is logged, not raised).
    """
    if df is None or df.empty:
        return 0
    rows = df.drop_duplicates(subset="timestamp", keep="last")
    session = get_session(url)
    inserted = 0
    updated = 0
    try:
        init_db(url)
        stamps = [int(ts) for ts in rows["timestamp"].tolist()]
        existing = {
            candle.timestamp: candle
            for candle in session.scalars(
                select(Candle).where(
                    Candle.token_address == token_address,
                    Candle.timeframe == timeframe,
                    Candle.timestamp.in_(stamps),
                )
            )
        }
        for row in rows.itertuples(index=False):
            stamp = int(row.timestamp)
            candle = existing.get(stamp)
            if candle is None:
                session.add(
                    Candle(
                        chain="sol",
                        token_address=token_address,
                        timeframe=timeframe,
                        timestamp=stamp,
                        open=_num(row.open),
                        high=_num(row.high),
                        low=_num(row.low),
                        close=_num(row.close),
                        volume=_num(row.volume),
                    )
                )
                inserted += 1
            else:
                candle.open = _num(row.open)
                candle.high = _num(row.high)
                candle.low = _num(row.low)
                candle.close = _num(row.close)
                candle.volume = _num(row.volume)
                updated += 1
        session.commit()
        if logger:
            logger.info(
                "klines upsert %s (%s): %d inserted, %d updated",
                token_address,
                timeframe,
                inserted,
                updated,
            )
        return inserted + updated
    except SQLAlchemyError as exc:
        session.rollback()
        if logger:
            logger.error(
                "failed to save klines for %s (%s): %s", token_address, timeframe, exc
            )
        return None
    finally:
        session.close()


def _num(value: Any) -> Optional[float]:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return None if result != result else result  # NaN -> NULL
