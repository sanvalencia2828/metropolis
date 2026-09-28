from datetime import datetime, timedelta

from backend.backtest.config import BacktestConfig
from backend.backtest.engine import BacktestEngine
from backend.backtest.fetcher import Candle, CandleFetcher
from backend.backtest.metrics import max_drawdown, sharpe


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


def _bars(prices: list[float]) -> list[Candle]:
    start = datetime(2026, 1, 1)
    candles = []
    previous = prices[0]
    for index, price in enumerate(prices):
        low = min(previous, price)
        high = max(previous, price)
        candles.append(
            Candle(
                open_time=start + timedelta(minutes=index),
                open=previous,
                high=high,
                low=low,
                close=price,
                volume=1000,
            )
        )
        previous = price
    return candles


def test_fetcher_from_rows():
    candles = CandleFetcher().from_rows(
        [{"t": 1700000000, "o": 1, "h": 2, "l": 0.5, "c": 1.5, "v": 10}]
    )
    assert len(candles) == 1
    assert candles[0].close == 1.5
    assert candles[0].high == 2


def test_engine_take_profit(tmp_path):
    config = BacktestConfig(cash=1000, position_pct=0.5, fee_bps=0, take_profit_pct=0.2, stop_loss_pct=0.5)
    engine = BacktestEngine(config=config)
    report = engine.run(SAFE, _bars([10, 10.5, 13, 12]))
    assert report.metrics["closed_trades"] >= 1
    assert report.trades[0].close_reason in {"take_profit", "eod"}
    path = report.write(tmp_path / "bt.json")
    assert path.exists()
    assert "mint1" in report.summary()


def test_engine_stop_loss():
    config = BacktestConfig(cash=1000, position_pct=0.5, fee_bps=0, take_profit_pct=5.0, stop_loss_pct=0.15)
    report = BacktestEngine(config=config).run(SAFE, _bars([10, 9.5, 8, 8.2]))
    assert report.trades
    assert report.trades[0].close_reason == "stop_loss"
    assert report.metrics["max_drawdown"] >= 0


def test_drawdown_and_sharpe():
    assert max_drawdown([100, 120, 90, 110]) == 0.25
    assert sharpe([100]) == 0.0
