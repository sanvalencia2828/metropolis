"""Solana data collection via the system-installed gmgn-cli (Node.js) tool.

Every public method shells out to ``gmgn-cli`` and parses its JSON stdout.
Nothing executes at import time and the module never installs packages;
commands only run when a collector method is called explicitly.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Any, Optional

import pandas as pd

from backend.config.settings import settings
from backend.data_collectors.gmgn_client import normalize_klines
from backend.monitoring.logger import get_logger

# get_logger() is a monitoring stub returning None until the real monitoring
# stack lands, so every call site must guard before using the logger.
logger = get_logger(__name__)

GMGN_CLI_BINARY = "gmgn-cli"
GMGN_SIGNUP_URL = "https://gmgn.ai/ai"
SUBPROCESS_TIMEOUT_SECONDS = 60

# Resolutions accepted by `gmgn-cli market kline` (1s is Pro-plan only).
TIMEFRAME_SECONDS = {
    "1s": 1,
    "30s": 30,
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3_600,
    "4h": 14_400,
    "1d": 86_400,
}

KLINE_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]

_COLUMN_ALIASES = {
    "timestamp": ("open_time", "time", "t"),
    "open": ("open", "o"),
    "high": ("high", "h"),
    "low": ("low", "l"),
    "close": ("close", "c"),
    "volume": ("volume", "v"),
}


class SolanaClient:
    """Collects Solana token data by shelling out to gmgn-cli."""

    def __init__(
        self,
        rpc_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = SUBPROCESS_TIMEOUT_SECONDS,
    ) -> None:
        self.rpc_url = rpc_url
        self.timeout = timeout
        # os.environ first per convention; fall back to the project .env so a
        # key configured there still works (gmgn-cli reads the env, not .env).
        self.api_key = api_key or os.environ.get("GMGN_API_KEY") or settings.GMGN_API_KEY
        if not self.api_key:
            raise ValueError(
                "GMGN_API_KEY is not set. Register at "
                f"{GMGN_SIGNUP_URL} to get an API key, then export it as "
                "GMGN_API_KEY (or add it to ai_trader/.env)."
            )

    # ------------------------------------------------------------------
    # subprocess plumbing
    # ------------------------------------------------------------------

    def _run_gmgn_command(self, command: list[str]) -> Optional[Any]:
        """Run ``gmgn-cli <command> --raw`` and return its parsed JSON stdout.

        Returns None (and logs through the monitoring logger) when the binary
        is missing, the process fails or times out, or the output is not JSON.
        """
        binary = shutil.which(GMGN_CLI_BINARY)
        if binary is None:
            if logger:
                logger.error("'%s' executable not found on PATH", GMGN_CLI_BINARY)
            return None
        env = os.environ.copy()
        # A key resolved from .env must still reach the child process.
        env.setdefault("GMGN_API_KEY", self.api_key)
        try:
            # --raw forces JSON stdout; without it gmgn-cli prints tables.
            result = subprocess.run(
                [binary, *command, "--raw"],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=env,
            )
        except subprocess.TimeoutExpired:
            if logger:
                logger.error(
                    "gmgn-cli timed out after %ss: gmgn-cli %s",
                    self.timeout,
                    " ".join(command),
                )
            return None
        except OSError as exc:
            if logger:
                logger.error("failed to start gmgn-cli: %s", exc)
            return None
        if result.returncode != 0:
            if logger:
                detail = (result.stderr or result.stdout or "").strip()[:500]
                logger.error("gmgn-cli exited with %s: %s", result.returncode, detail)
            return None
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            if logger:
                logger.error("gmgn-cli printed non-JSON output: %s", exc)
            return None
        return _unwrap_envelope(payload)

    def _dict_payload(self, command: list[str]) -> Optional[dict[str, Any]]:
        payload = self._run_gmgn_command(command)
        if payload is None:
            return None
        if not isinstance(payload, dict):
            if logger:
                logger.error(
                    "expected a JSON object from gmgn-cli %s, got %s",
                    command[1] if len(command) > 1 else command,
                    type(payload).__name__,
                )
            return None
        return payload

    # ------------------------------------------------------------------
    # Skill 1: Token Kline Data
    # ------------------------------------------------------------------

    def get_historical_klines(
        self,
        token_address: str,
        resolution: str = "1m",
        from_ts: Optional[int] = None,
        to_ts: Optional[int] = None,
    ) -> Optional[pd.DataFrame]:
        """OHLCV candles as a DataFrame (timestamp/open/high/low/close/volume,
        oldest first), or None on failure or empty result."""
        command = [
            "market",
            "kline",
            "--chain",
            "sol",
            "--address",
            token_address,
            "--resolution",
            resolution,
        ]
        if from_ts is not None:
            command += ["--from", str(int(from_ts))]
        if to_ts is not None:
            command += ["--to", str(int(to_ts))]
        payload = self._run_gmgn_command(command)
        if payload is None:
            return None
        frame = _klines_to_frame(payload)
        if frame.empty:
            if logger:
                logger.warning(
                    "gmgn-cli returned no klines for %s (%s)", token_address, resolution
                )
            return None
        return frame

    # ------------------------------------------------------------------
    # Skill 2: Token Security Check
    # ------------------------------------------------------------------

    def get_token_security(self, token_address: str) -> Optional[dict[str, Any]]:
        return self._dict_payload(
            ["token", "security", "--chain", "sol", "--address", token_address]
        )

    # ------------------------------------------------------------------
    # Skill 3: Token Basic Info
    # ------------------------------------------------------------------

    def get_token_info(self, token_address: str) -> Optional[dict[str, Any]]:
        return self._dict_payload(["token", "info", "--chain", "sol", "--address", token_address])

    # ------------------------------------------------------------------
    # Skill 4: Liquidity Pool Analysis
    # ------------------------------------------------------------------

    def get_liquidity_pool(self, token_address: str) -> Optional[dict[str, Any]]:
        return self._dict_payload(["token", "pool", "--chain", "sol", "--address", token_address])

    # ------------------------------------------------------------------
    # Skill 5: Wallet Trade History
    # ------------------------------------------------------------------

    def get_wallet_activity(
        self,
        wallet_address: str,
        tx_type: Optional[str] = None,
    ) -> Optional[pd.DataFrame]:
        """Wallet trade history as a DataFrame, or None on failure.

        tx_type accepts the CLI's values: buy / sell / transferIn /
        transferOut / add / remove.
        """
        command = ["portfolio", "activity", "--chain", "sol", "--wallet", wallet_address]
        if tx_type is not None:
            command += ["--type", tx_type]
        payload = self._run_gmgn_command(command)
        if payload is None:
            return None
        return pd.DataFrame(_records(payload, "activity", "trades"))

    # ------------------------------------------------------------------
    # Skill 6: Top100 Traders Analysis
    # ------------------------------------------------------------------

    def get_top_traders(
        self,
        token_address: str,
        order_by: str = "profit",
        direction: str = "desc",
        limit: int = 100,
    ) -> Optional[pd.DataFrame]:
        """Top traders as a DataFrame, or None on failure.

        order_by accepts: amount_percentage / profit / unrealized_profit /
        buy_volume_cur / sell_volume_cur (CLI caps --limit at 100).
        """
        command = [
            "token",
            "traders",
            "--chain",
            "sol",
            "--address",
            token_address,
            "--order-by",
            order_by,
            "--direction",
            direction,
            "--limit",
            str(limit),
        ]
        payload = self._run_gmgn_command(command)
        if payload is None:
            return None
        return pd.DataFrame(_records(payload, "traders", "top_traders", "rank"))


def _unwrap_envelope(payload: Any) -> Any:
    """Strip a {"code": 0, "data": ...} envelope; None on error envelopes."""
    if not isinstance(payload, dict):
        return payload
    code = payload.get("code")
    if code is not None and str(code) != "0":
        if logger:
            message = payload.get("msg") or payload.get("error") or "gmgn-cli reported an error"
            logger.error("gmgn-cli error envelope: %s", message)
        return None
    for key in ("data", "result"):
        if key in payload:
            return payload[key]
    return payload


def _klines_to_frame(payload: Any) -> pd.DataFrame:
    rows = normalize_klines(payload)
    records = [
        {column: _first_present(row, aliases) for column, aliases in _COLUMN_ALIASES.items()}
        for row in rows
    ]
    frame = pd.DataFrame(records, columns=KLINE_COLUMNS)
    if frame.empty:
        return frame
    frame = frame.apply(pd.to_numeric, errors="coerce")
    # GMGN timestamps arrive as seconds or milliseconds depending on payload; keep seconds.
    milliseconds = frame["timestamp"] > 10_000_000_000
    frame.loc[milliseconds, "timestamp"] = frame.loc[milliseconds, "timestamp"] // 1000
    frame["volume"] = frame["volume"].fillna(0.0)
    return frame.dropna(subset=["timestamp", "close"]).sort_values("timestamp").reset_index(drop=True)


def _records(payload: Any, *keys: str) -> list[dict[str, Any]]:
    """Pull a list of row dicts out of common gmgn-cli response shapes."""
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in (*keys, "items", "list", "data", "result"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _first_present(row: dict[str, Any], aliases: tuple[str, ...]) -> Any:
    for alias in aliases:
        if alias in row:
            return row[alias]
    return None
