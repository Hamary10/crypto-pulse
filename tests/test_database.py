import importlib
import os
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSISTANT_DIR = PROJECT_ROOT / "assistant"
sys.path.insert(0, str(ASSISTANT_DIR))


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False)
        self.tmp.close()
        os.environ["DATABASE_PATH"] = self.tmp.name

        if "database" in sys.modules:
            del sys.modules["database"]
        self.database = importlib.import_module("database")
        self.database.init_database()

    def tearDown(self):
        try:
            os.unlink(self.tmp.name)
        except OSError:
            pass

    def test_init_creates_p0_tables(self):
        with closing(sqlite3.connect(self.tmp.name)) as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()

        table_names = {row[0] for row in rows}
        self.assertIn("users", table_names)
        self.assertIn("command_logs", table_names)
        self.assertIn("coin_query_stats", table_names)
        self.assertIn("price_snapshots", table_names)

    def test_records_user_command_coin_and_snapshot(self):
        self.database.upsert_user(
            {
                "id": 123,
                "username": "alice",
                "first_name": "Alice",
                "last_name": "Lee",
            }
        )
        self.database.log_command(123, "/price", ["btc"])
        self.database.increment_coin_query("bitcoin", "BTC")
        self.database.record_price_snapshot(
            {
                "coin_id": "bitcoin",
                "symbol": "BTC",
                "price_cny": 500000,
                "price_usd": 69000,
                "market_cap": 100,
                "volume_24h": 10,
                "price_change_percentage_24h": 1.5,
            }
        )

        with closing(sqlite3.connect(self.tmp.name)) as conn:
            users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            logs = conn.execute("SELECT COUNT(*) FROM command_logs").fetchone()[0]
            stats = conn.execute("SELECT query_count FROM coin_query_stats").fetchone()[0]
            snapshots = conn.execute("SELECT COUNT(*) FROM price_snapshots").fetchone()[0]

        self.assertEqual(users, 1)
        self.assertEqual(logs, 1)
        self.assertEqual(stats, 1)
        self.assertEqual(snapshots, 1)


if __name__ == "__main__":
    unittest.main()
