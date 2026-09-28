from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass
class Position:
    id: str
    chain: str
    address: str
    qty: float
    entry_price: float
    notional: float
    opened_at: datetime
    symbol: Optional[str] = None
    stop_loss_pct: float = 0.15
    take_profit_pct: float = 0.30
    status: str = "open"
    exit_price: Optional[float] = None
    closed_at: Optional[datetime] = None
    pnl: float = 0.0
    pnl_pct: float = 0.0
    close_reason: Optional[str] = None
    dossier_score: Optional[float] = None

    def mark(self, price: float) -> float:
        return (price - self.entry_price) * self.qty

    def unrealized_pct(self, price: float) -> float:
        if self.entry_price == 0:
            return 0.0
        return (price - self.entry_price) / self.entry_price


@dataclass
class PositionManager:
    cash: float = 10_000.0
    max_positions: int = 5
    position_pct: float = 0.1
    starting_cash: float = field(init=False)
    positions: dict[str, Position] = field(default_factory=dict)
    closed: list[Position] = field(default_factory=list)
    _seq: int = 0

    def __post_init__(self) -> None:
        self.starting_cash = self.cash

    @staticmethod
    def key(chain: str, address: str) -> str:
        return f"{chain}:{address}"

    def get(self, chain: str, address: str) -> Optional[Position]:
        return self.positions.get(self.key(chain, address))

    def open_position(
        self,
        chain: str,
        address: str,
        price: float,
        symbol: Optional[str] = None,
        now: Optional[datetime] = None,
        dossier_score: Optional[float] = None,
        stop_loss_pct: float = 0.15,
        take_profit_pct: float = 0.30,
    ) -> Optional[Position]:
        if price <= 0:
            return None
        token_key = self.key(chain, address)
        if token_key in self.positions:
            return None
        if len(self.positions) >= self.max_positions:
            return None
        notional = self.cash * self.position_pct
        if notional <= 0 or self.cash < notional:
            return None
        qty = notional / price
        self._seq += 1
        position = Position(
            id=f"p-{self._seq}",
            chain=chain,
            address=address,
            symbol=symbol,
            qty=qty,
            entry_price=price,
            notional=notional,
            opened_at=now or utcnow(),
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct,
            dossier_score=dossier_score,
        )
        self.cash -= notional
        self.positions[token_key] = position
        return position

    def close_position(
        self,
        chain: str,
        address: str,
        price: float,
        reason: str,
        now: Optional[datetime] = None,
    ) -> Optional[Position]:
        token_key = self.key(chain, address)
        position = self.positions.pop(token_key, None)
        if position is None:
            return None
        proceeds = position.qty * price
        position.exit_price = price
        position.closed_at = now or utcnow()
        position.pnl = proceeds - position.notional
        position.pnl_pct = 0.0 if position.notional == 0 else position.pnl / position.notional
        position.close_reason = reason
        position.status = "closed"
        self.cash += proceeds
        self.closed.append(position)
        return position

    def equity(self, marks: Optional[dict[str, float]] = None) -> float:
        total = self.cash
        for token_key, position in self.positions.items():
            price = (marks or {}).get(token_key, position.entry_price)
            total += position.qty * price
        return total
