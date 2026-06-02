import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from generate_report import generate_report


class GenerateReportTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.reports_dir = self.root / "reports"
        self.now = datetime(2026, 6, 2, 12, 0, 0)

    def tearDown(self):
        self.temp_dir.cleanup()

    def read_report(self, path):
        return Path(path).read_text(encoding="utf-8")

    def test_missing_database_generates_friendly_report(self):
        missing_db = self.root / "missing.db"

        report_path = generate_report(str(missing_db), str(self.reports_dir), self.now)
        text = self.read_report(report_path)

        self.assertTrue(report_path.exists())
        self.assertIn("未找到数据库文件", text)
        self.assertIn("请确认 `DATABASE_PATH` 环境变量或默认 `crypto_pulse.db` 是否存在", text)

    def test_missing_tables_generate_report_without_crashing(self):
        db_path = self.root / "empty.db"
        sqlite3.connect(db_path).close()

        report_path = generate_report(str(db_path), str(self.reports_dir), self.now)
        text = self.read_report(report_path)

        self.assertIn("表 `users` 不存在，暂无法统计。", text)
        self.assertIn("表 `command_logs` 不存在，暂无法统计。", text)
        self.assertIn("表 `coin_query_stats` 不存在，暂无法统计。", text)
        self.assertIn("当前暂无错误日志表，暂无法统计。", text)

    def test_report_counts_users_commands_and_coin_queries(self):
        db_path = self.root / "crypto_pulse.db"
        today = self.now.replace(hour=8)
        yesterday = self.now - timedelta(days=1)
        conn = sqlite3.connect(db_path)
        try:
            conn.executescript(
                """
                CREATE TABLE users (
                    telegram_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL
                );
                CREATE TABLE command_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER,
                    command TEXT NOT NULL,
                    args TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE coin_query_stats (
                    coin_id TEXT PRIMARY KEY,
                    symbol TEXT,
                    query_count INTEGER NOT NULL DEFAULT 0,
                    last_queried_at TEXT NOT NULL
                );
                """
            )
            conn.executemany(
                """
                INSERT INTO users (
                    telegram_id, username, first_name, last_name,
                    first_seen_at, last_seen_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (123456, "secret_user", "Alice", "Hidden", today.isoformat(timespec="seconds"), today.isoformat(timespec="seconds")),
                    (987654, "another_secret", "Bob", "Hidden", yesterday.isoformat(timespec="seconds"), today.isoformat(timespec="seconds")),
                ],
            )
            conn.executemany(
                "INSERT INTO command_logs (telegram_id, command, args, created_at) VALUES (?, ?, ?, ?)",
                [
                    (123456, "/price", "btc", today.isoformat(timespec="seconds")),
                    (987654, "/price", "eth", today.isoformat(timespec="seconds")),
                    (987654, "/top", "", yesterday.isoformat(timespec="seconds")),
                ],
            )
            conn.executemany(
                "INSERT INTO coin_query_stats (coin_id, symbol, query_count, last_queried_at) VALUES (?, ?, ?, ?)",
                [
                    ("bitcoin", "BTC", 5, today.isoformat(timespec="seconds")),
                    ("ethereum", "ETH", 3, today.isoformat(timespec="seconds")),
                ],
            )
            conn.commit()
        finally:
            conn.close()

        report_path = generate_report(str(db_path), str(self.reports_dir), self.now)
        text = self.read_report(report_path)

        self.assertIn("- 总用户数：2", text)
        self.assertIn("- 今日新增用户数：1", text)
        self.assertIn("- 今日活跃用户数：2", text)
        self.assertIn("- 今日命令调用总数：2", text)
        self.assertIn("| 1 | /price | 2 |", text)
        self.assertIn("| 1 | bitcoin | BTC | 5 |", text)
        self.assertIn("| 2 | ethereum | ETH | 3 |", text)

    def test_report_does_not_include_private_user_fields(self):
        db_path = self.root / "privacy.db"
        conn = sqlite3.connect(db_path)
        try:
            conn.executescript(
                """
                CREATE TABLE users (
                    telegram_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL
                );
                CREATE TABLE command_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER,
                    command TEXT NOT NULL,
                    args TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE coin_query_stats (
                    coin_id TEXT PRIMARY KEY,
                    symbol TEXT,
                    query_count INTEGER NOT NULL DEFAULT 0,
                    last_queried_at TEXT NOT NULL
                );
                """
            )
            conn.execute(
                """
                INSERT INTO users (
                    telegram_id, username, first_name, last_name,
                    first_seen_at, last_seen_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (1122334455, "private_username", "PrivateFirst", "PrivateLast", self.now.isoformat(timespec="seconds"), self.now.isoformat(timespec="seconds")),
            )
            conn.execute(
                "INSERT INTO command_logs (telegram_id, command, args, created_at) VALUES (?, ?, ?, ?)",
                (1122334455, "/help", "", self.now.isoformat(timespec="seconds")),
            )
            conn.commit()
        finally:
            conn.close()

        report_path = generate_report(str(db_path), str(self.reports_dir), self.now)
        text = self.read_report(report_path)

        self.assertNotIn("1122334455", text)
        self.assertNotIn("private_username", text)
        self.assertNotIn("PrivateFirst", text)
        self.assertNotIn("PrivateLast", text)


if __name__ == "__main__":
    unittest.main()
