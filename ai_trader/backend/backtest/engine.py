from __future__ import annotations

from typing import Any, Optional

from backend.backtest.config import BacktestConfig
from backend.backtest.executor import BacktestExecutor
from backend.backtest.fetcher import Candle, CandleFetcher
from backend.backtest.metrics import backtest_metrics
from backend.backtest.report import BacktestReport
from backend.config.chains import get_chain
from backend.decision.dossier import DossierBuilder


class BacktestEngine:
    def __init__(
        self,
        config: Optional[BacktestConfig] = None,
        builder: Optional[DossierBuilder] = None,
        fetcher: Optional[CandleFetcher] = None,
        executor: Optional[BacktestExecutor] = None,
    ) -> None:
        self.config = config or BacktestConfig()
        self.builder = builder or DossierBuilder()
        self.fetcher = fetcher or CandleFetcher()
        self.executor = executor or BacktestExecutor(self.config)

    def run(
        self,
        record: dict[str, Any],
        candles: Optional[list[Candle]] = None,
    ) -> BacktestReport:
        chain = get_chain(record.get("chain") or self.config.chain).slug
        address = str(record.get("address") or record.get("token_address") or record.get("mint") or "")
        if not address:
            raise ValueError("token address required")
        bars = candles if candles is not None else self.fetcher.fetch(
            address,
            chain,
            resolution=self.config.resolution,
            from_ts=self.config.from_ts,
            to_ts=self.config.to_ts,
        )
        curve = [self.executor.executor.manager.starting_cash]
        actions: list[dict[str, Any]] = []
        snapshot = dict(record)
        snapshot["chain"] = chain
        snapshot["address"] = address
        for bar in bars:
            snapshot["price"] = bar.close
            if snapshot.get("volume") is None:
                snapshot["volume"] = bar.volume
            risk = self.executor.apply_bar(chain, address, bar)
            if risk:
                actions.append(risk)
            dossier = self.builder.build(snapshot)
            signal = self.executor.apply_signal(dossier, bar.close, now=bar.open_time)
            if signal.get("action") != "skip":
                actions.append(signal)
            marks = {f"{chain}:{address}": bar.close}
            curve.append(self.executor.executor.manager.equity(marks))
        if self.executor.executor.manager.get(chain, address) and bars:
            last = bars[-1]
            closed = self.executor.close_open(chain, address, last.close, now=last.open_time)
            if closed:
                actions.append(closed)
            curve.append(self.executor.executor.manager.equity())
        stats = backtest_metrics(self.executor.executor.manager, curve)
        return BacktestReport(
            chain=chain,
            address=address,
            symbol=record.get("symbol"),
            metrics=stats,
            equity_curve=curve,
            actions=actions,
            trades=list(self.executor.executor.manager.closed),
        )
