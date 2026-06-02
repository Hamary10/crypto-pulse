import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Iterable


DATABASE_PATH = os.getenv("DATABASE_PATH", "crypto_pulse.db")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db_connection():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_database() -> None:
    try:
        with db_connection() as conn:
            conn.executescript(
                """
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS command_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                command TEXT NOT NULL,
                args TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS coin_query_stats (
                coin_id TEXT PRIMARY KEY,
                symbol TEXT,
                query_count INTEGER NOT NULL DEFAULT 0,
                last_queried_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS price_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                coin_id TEXT NOT NULL,
                symbol TEXT,
                price_cny REAL,
                price_usd REAL,
                market_cap REAL,
                volume_24h REAL,
                price_change_percentage_24h REAL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_price_snapshots_coin_id
                ON price_snapshots (coin_id);
            CREATE INDEX IF NOT EXISTS idx_price_snapshots_created_at
                ON price_snapshots (created_at);
                """
            )
        print(f"SQLite initialized: {DATABASE_PATH}")
    except Exception as exc:
        print(f"SQLite initialization failed: {exc}")


def record_price_snapshot(snapshot: Dict[str, Any]) -> None:
    try:
        with db_connection() as conn:
            conn.execute(
                """
            INSERT INTO price_snapshots (
                coin_id, symbol, price_cny, price_usd, market_cap, volume_24h,
                price_change_percentage_24h, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    snapshot.get("coin_id"),
                    (snapshot.get("symbol") or "").upper(),
                    snapshot.get("price_cny"),
                    snapshot.get("price_usd"),
                    snapshot.get("market_cap"),
                    snapshot.get("volume_24h"),
                    snapshot.get("price_change_percentage_24h"),
                    utc_now(),
                ),
            )
        print(f"SQLite price snapshot recorded: coin_id={snapshot.get('coin_id')}")
    except Exception as exc:
        print(f"SQLite price snapshot failed: {exc}")


def record_price_snapshots(snapshots: Iterable[Dict[str, Any]]) -> None:
    for snapshot in snapshots:
        record_price_snapshot(snapshot)
