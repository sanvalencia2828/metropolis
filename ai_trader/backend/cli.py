from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rich.console import Console
from rich.table import Table

from backend.config.chains import get_chain, list_supported_chains
from backend.config.settings import settings
from backend.data_collectors.gmgn_client import GMGNClient, GMGNError, extract_items
from backend.data_collectors.solana_client import TIMEFRAME_SECONDS, SolanaClient
from backend.features.feature_registry import registry
from backend.database.crud import save_klines_to_db
from backend.database.models import init_db, save_token_snapshots

console = Console()


def cmd_chains() -> int:
    table = Table(title="Supported chains")
    table.add_column("slug")
    table.add_column("name")
    table.add_column("symbol")
    for slug in list_supported_chains():
        chain = get_chain(slug)
        table.add_row(chain.slug, chain.name, chain.symbol)
    console.print(table)
    return 0


def cmd_init_db() -> int:
    init_db()
    console.print(f"database ready: {settings.DATABASE_URL}")
    return 0


def cmd_features() -> int:
    for spec in registry.specs():
        console.print(f"{spec.name}: {spec.description}")
    return 0


def collect_trending(
    chain: Optional[str] = None,
    limit: int = 20,
    period: str = "1h",
    db_url: Optional[str] = None,
    client: Optional[GMGNClient] = None,
) -> int:
    slug = get_chain(chain or settings.DEFAULT_CHAIN).slug
    owns_client = client is None
    active = client or GMGNClient()
    try:
        payload = active.get_trending(chain=slug, period=period, limit=limit)
    finally:
        if owns_client:
            active.close()
    items = extract_items(payload)
    saved = save_token_snapshots(items, slug, url=db_url)
    console.print(f"saved {saved} snapshots on {slug}")
    return saved


def download_klines(
    token: str,
    timeframe: str = "1m",
    limit: int = 1000,
    db_url: Optional[str] = None,
    client: Optional[SolanaClient] = None,
) -> int:
    """Download klines via gmgn-cli and upsert them into the local database."""
    active = client or SolanaClient()
    to_ts = int(time.time())
    from_ts = to_ts - limit * TIMEFRAME_SECONDS[timeframe]
    frame = active.get_historical_klines(token, resolution=timeframe, from_ts=from_ts, to_ts=to_ts)
    if frame is None or frame.empty:
        console.print(f"no klines returned for {token} ({timeframe})")
        return 0
    console.print(_klines_table(token, timeframe, frame))
    saved = save_klines_to_db(frame, token_address=token, timeframe=timeframe, url=db_url)
    if saved is None:
        console.print(f"database error while saving klines for {token} (see logs)")
        return 0
    console.print(f"Saved {saved} candles for {token}")
    return saved


def _klines_table(token: str, timeframe: str, frame) -> Table:
    tail = frame.tail(10)
    table = Table(title=f"{token} {timeframe} candles (showing {len(tail)} of {len(frame)})")
    for column in ("time (UTC)", "open", "high", "low", "close", "volume"):
        table.add_column(column, justify="right")
    for row in tail.itertuples(index=False):
        stamp = datetime.fromtimestamp(row.timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        table.add_row(stamp, *[_fmt(value) for value in (row.open, row.high, row.low, row.close, row.volume)])
    return table


def _fmt(value: float) -> str:
    return f"{value:,.8f}".rstrip("0").rstrip(".")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-trader")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("chains")
    sub.add_parser("init-db")
    sub.add_parser("features")
    collect = sub.add_parser("collect")
    collect.add_argument("--chain", default=None)
    collect.add_argument("--limit", type=int, default=20)
    collect.add_argument("--period", default="1h", choices=["1m", "5m", "1h", "6h", "24h"])
    klines = sub.add_parser("download-klines")
    klines.add_argument("--token", required=True)
    klines.add_argument("--timeframe", default="1m", choices=sorted(TIMEFRAME_SECONDS))
    klines.add_argument("--limit", type=int, default=1000)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "chains":
        return cmd_chains()
    if args.command == "init-db":
        return cmd_init_db()
    if args.command == "features":
        return cmd_features()
    if args.command == "collect":
        try:
            collect_trending(chain=args.chain, limit=args.limit, period=args.period)
        except (GMGNError, ValueError) as exc:
            console.print(f"collect failed: {exc}")
            return 1
        return 0
    if args.command == "download-klines":
        try:
            saved = download_klines(token=args.token, timeframe=args.timeframe, limit=args.limit)
        except ValueError as exc:  # missing GMGN_API_KEY and friends
            console.print(f"download-klines failed: {exc}")
            return 1
        return 0 if saved > 0 else 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
