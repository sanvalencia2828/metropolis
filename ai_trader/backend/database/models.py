from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

from sqlalchemy import DateTime, Float, Integer, String, Text, UniqueConstraint, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from backend.config.settings import settings


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class TokenSnapshot(Base):
    __tablename__ = "token_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chain: Mapped[str] = mapped_column(String(16), index=True)
    address: Mapped[str] = mapped_column(String(128), index=True)
    symbol: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    liquidity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    volume_24h: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    market_cap: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    holder_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    raw_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)


class TradeRecord(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chain: Mapped[str] = mapped_column(String(16), index=True)
    token_address: Mapped[str] = mapped_column(String(128), index=True)
    tx_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    side: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    raw_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)


class Candle(Base):
    __tablename__ = "candles"
    __table_args__ = (
        UniqueConstraint("token_address", "timestamp", "timeframe", name="uix_token_tf_ts"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chain: Mapped[str] = mapped_column(String(16), index=True)
    token_address: Mapped[str] = mapped_column(String(128), index=True)
    timeframe: Mapped[str] = mapped_column(String(16), default="1m")
    timestamp: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    open: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    high: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    low: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    close: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    volume: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)


def resolve_database_url(url: Optional[str] = None) -> str:
    """Normalize sqlite URLs so Windows paths and relative .env values work."""
    raw = url or settings.DATABASE_URL
    if not raw.startswith("sqlite:///"):
        return raw
    path = raw[len("sqlite:///") :]
    if path in (":memory:", ""):
        return raw
    if path.startswith("./") or path.startswith(".\\"):
        path = str((settings.BASE_PATH / path[2:]).resolve())
    return "sqlite:///" + path.replace("\\", "/")


def get_engine(url: Optional[str] = None) -> Engine:
    resolved = resolve_database_url(url)
    connect_args = {"check_same_thread": False} if resolved.startswith("sqlite") else {}
    if resolved.startswith("sqlite:///") and not resolved.endswith(":memory:"):
        Path(resolved[len("sqlite:///") :]).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(resolved, connect_args=connect_args)


def init_db(url: Optional[str] = None) -> Engine:
    settings.ensure_directories()
    engine = get_engine(url)
    Base.metadata.create_all(engine)
    return engine


@contextmanager
def session_scope(url: Optional[str] = None) -> Iterator[Session]:
    engine = init_db(url)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def save_token_snapshots(
    items: list[dict[str, Any]],
    chain: str,
    url: Optional[str] = None,
) -> int:
    rows = []
    for item in items:
        address = _address(item)
        if not address:
            continue
        rows.append(
            TokenSnapshot(
                chain=chain,
                address=address,
                symbol=_opt_str(item, "symbol"),
                name=_opt_str(item, "name"),
                price=_opt_float(item, "price", "price_usd"),
                liquidity=_opt_float(item, "liquidity", "liquidity_usd"),
                volume_24h=_opt_float(item, "volume", "volume_24h", "volume_usd"),
                market_cap=_opt_float(item, "market_cap", "marketcap"),
                holder_count=_opt_int(item, "holder_count", "holders"),
                raw_json=json.dumps(item, default=str),
            )
        )
    return _save_rows(rows, url)


def save_trades(
    items: list[dict[str, Any]],
    chain: str,
    token_address: str,
    url: Optional[str] = None,
) -> int:
    rows = [
        TradeRecord(
            chain=chain,
            token_address=token_address,
            tx_hash=_opt_str(item, "tx_hash", "transaction_hash", "hash"),
            side=_opt_str(item, "side", "type", "event"),
            price=_opt_float(item, "price", "price_usd"),
            amount=_opt_float(item, "amount", "base_amount", "quote_amount"),
            raw_json=json.dumps(item, default=str),
        )
        for item in items
        if isinstance(item, dict)
    ]
    return _save_rows(rows, url)


def save_candles(
    items: list[dict[str, Any]],
    chain: str,
    token_address: str,
    timeframe: str = "1m",
    url: Optional[str] = None,
) -> int:
    """Blind-insert candle dicts; overlapping (token, timestamp, timeframe)
    rows hit uix_token_tf_ts — use backend.database.crud.save_klines_to_db
    for the upsert path."""
    rows = []
    for item in items:
        if not isinstance(item, dict):
            continue
        rows.append(
            Candle(
                chain=chain,
                token_address=token_address,
                timeframe=timeframe,
                timestamp=_opt_int(item, "timestamp", "open_time", "time", "t"),
                open=_opt_float(item, "open", "o"),
                high=_opt_float(item, "high", "h"),
                low=_opt_float(item, "low", "l"),
                close=_opt_float(item, "close", "c"),
                volume=_opt_float(item, "volume", "v"),
            )
        )
    return _save_rows(rows, url)


def list_snapshots(chain: str, url: Optional[str] = None, limit: int = 50) -> list[TokenSnapshot]:
    with session_scope(url) as session:
        stmt = (
            select(TokenSnapshot)
            .where(TokenSnapshot.chain == chain)
            .order_by(TokenSnapshot.collected_at.desc())
            .limit(limit)
        )
        return list(session.scalars(stmt))


def _save_rows(rows: list[Any], url: Optional[str]) -> int:
    if not rows:
        return 0
    with session_scope(url) as session:
        session.add_all(rows)
    return len(rows)


def _address(item: dict[str, Any]) -> str:
    if not isinstance(item, dict):
        return ""
    return str(item.get("address") or item.get("token_address") or item.get("mint") or "").strip()


def _opt_str(item: dict[str, Any], *keys: str) -> Optional[str]:
    for key in keys:
        value = item.get(key)
        if value is not None and str(value).strip():
            return str(value)
    return None


def _opt_float(item: dict[str, Any], *keys: str) -> Optional[float]:
    for key in keys:
        value = item.get(key)
        if value is None or value == "":
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _opt_int(item: dict[str, Any], *keys: str) -> Optional[int]:
    value = _opt_float(item, *keys)
    if value is None:
        return None
    return int(value)
