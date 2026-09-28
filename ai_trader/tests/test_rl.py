from datetime import datetime, timedelta

from backend.backtest.config import BacktestConfig
from backend.backtest.fetcher import Candle
from backend.rl.dqn.inference import DQNPolicy
from backend.rl.dqn.train_dqn import train_dqn
from backend.rl.env.trading_env import HOLD, TradingEnv
from backend.rl.ppo.inference import PPOPolicy
from backend.rl.ppo.train_ppo import train_ppo
from backend.rl.replay_buffer import ReplayBuffer


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


def _candles() -> list[Candle]:
    start = datetime(2026, 1, 1)
    prices = [10, 10.2, 10.4, 10.1, 10.8]
    return [
        Candle(start + timedelta(minutes=i), price, price + 0.1, price - 0.1, price, 100)
        for i, price in enumerate(prices)
    ]


def test_env_step_and_buffer():
    env = TradingEnv(SAFE, _candles(), config=BacktestConfig(cash=1000, fee_bps=0, position_pct=0.5))
    state = env.reset()
    assert state.shape[0] == env.obs_size
    nxt, reward, done, info = env.step(HOLD)
    assert nxt.shape == state.shape
    assert info["action"] == "HOLD"
    assert isinstance(reward, float)
    assert done is False
    buffer = ReplayBuffer(capacity=8)
    buffer.add(state, HOLD, reward, nxt, done)
    sampled = buffer.sample(1)
    assert sampled[0].shape[0] == 1


def test_dqn_and_ppo_roundtrip(tmp_path):
    candles = _candles()
    dqn = train_dqn(SAFE, candles, episodes=2, path=tmp_path / "dqn.npz")
    ppo = train_ppo(SAFE, candles, episodes=2, path=tmp_path / "ppo.npz")
    env = TradingEnv(SAFE, candles)
    obs = env.reset()
    assert dqn.act(obs) in {0, 1, 2}
    assert ppo.act(obs)[0] in {0, 1, 2}
    assert DQNPolicy.load(tmp_path / "dqn.npz").recommend(obs) in {"HOLD", "BUY", "SELL"}
    assert PPOPolicy.load(tmp_path / "ppo.npz").recommend(obs) in {"HOLD", "BUY", "SELL"}
