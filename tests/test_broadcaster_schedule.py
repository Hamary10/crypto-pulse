import importlib
import sys
import types
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BROADCASTER_DIR = PROJECT_ROOT / "broadcaster"
WORKFLOW_PATH = PROJECT_ROOT / ".github" / "workflows" / "broadcaster.yml"


class FakeDateTime:
    current = datetime(2026, 6, 4, 8, 17)

    @classmethod
    def now(cls, _tz=None):
        return cls.current


class BroadcasterScheduleTests(unittest.TestCase):
    def setUp(self):
        self.module_names = [
            "broadcaster_bot",
            "coingecko_client",
            "database",
            "formatters",
            "pytz",
            "requests",
            "httpx",
        ]
        self.original_modules = {name: sys.modules.get(name) for name in self.module_names}
        self.original_sys_path = list(sys.path)

        sys.path.insert(0, str(BROADCASTER_DIR))
        for name in self.module_names:
            sys.modules.pop(name, None)

        fake_pytz = types.SimpleNamespace(timezone=lambda name: name)
        fake_requests = types.SimpleNamespace(get=lambda *args, **kwargs: None, post=lambda *args, **kwargs: None)
        fake_httpx = types.SimpleNamespace(get=lambda *args, **kwargs: None)
        sys.modules["pytz"] = fake_pytz
        sys.modules["requests"] = fake_requests
        sys.modules["httpx"] = fake_httpx

        self.broadcaster_bot = importlib.import_module("broadcaster_bot")

    def tearDown(self):
        sys.path = self.original_sys_path
        for name in self.module_names:
            original = self.original_modules[name]
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original

    def test_workflow_cron_runs_every_two_hours_at_minute_17(self):
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

        self.assertIn("cron: '17 */2 * * *'", workflow)
        self.assertIn("每 2 小时在第 17 分运行一次", workflow)

    def test_daily_rankings_send_at_0817(self):
        FakeDateTime.current = datetime(2026, 6, 4, 8, 17)

        with patch.object(self.broadcaster_bot, "FORCE_DAILY_RANKINGS", False), patch.object(
            self.broadcaster_bot, "datetime", FakeDateTime
        ):
            self.assertTrue(self.broadcaster_bot.should_send_daily_rankings())

    def test_daily_rankings_send_at_0831(self):
        FakeDateTime.current = datetime(2026, 6, 4, 8, 31)

        with patch.object(self.broadcaster_bot, "FORCE_DAILY_RANKINGS", False), patch.object(
            self.broadcaster_bot, "datetime", FakeDateTime
        ):
            self.assertTrue(self.broadcaster_bot.should_send_daily_rankings())

    def test_daily_rankings_send_at_0959(self):
        FakeDateTime.current = datetime(2026, 6, 4, 9, 59)

        with patch.object(self.broadcaster_bot, "FORCE_DAILY_RANKINGS", False), patch.object(
            self.broadcaster_bot, "datetime", FakeDateTime
        ):
            self.assertTrue(self.broadcaster_bot.should_send_daily_rankings())

    def test_daily_rankings_do_not_send_at_1000(self):
        FakeDateTime.current = datetime(2026, 6, 4, 10, 0)

        with patch.object(self.broadcaster_bot, "FORCE_DAILY_RANKINGS", False), patch.object(
            self.broadcaster_bot, "datetime", FakeDateTime
        ):
            self.assertFalse(self.broadcaster_bot.should_send_daily_rankings())

    def test_force_daily_rankings_still_sends(self):
        FakeDateTime.current = datetime(2026, 6, 4, 12, 30)

        with patch.object(self.broadcaster_bot, "FORCE_DAILY_RANKINGS", True), patch.object(
            self.broadcaster_bot, "datetime", FakeDateTime
        ):
            self.assertTrue(self.broadcaster_bot.should_send_daily_rankings())

    def test_message_types_at_schedule_boundaries(self):
        prices = {coin["id"]: {"usd": 1, "cny": 1} for coin in self.broadcaster_bot.COINS}
        markets = [{"id": "bitcoin", "symbol": "btc"}]
        trending = [{"name": "Bitcoin", "symbol": "btc"}]
        daily_labels = ["price_broadcast", "daily_gainers", "daily_losers", "daily_trending"]

        cases = [
            (datetime(2026, 6, 4, 8, 17), daily_labels),
            (datetime(2026, 6, 4, 8, 31), daily_labels),
            (datetime(2026, 6, 4, 9, 59), daily_labels),
            (datetime(2026, 6, 4, 10, 0), ["price_broadcast"]),
        ]

        for current, expected in cases:
            with self.subTest(current=current):
                FakeDateTime.current = current
                labels = []
                with patch.object(self.broadcaster_bot, "FORCE_DAILY_RANKINGS", False), patch.object(
                    self.broadcaster_bot, "datetime", FakeDateTime
                ), patch.object(self.broadcaster_bot, "init_database"), patch.object(
                    self.broadcaster_bot, "record_price_snapshots"
                ), patch.object(self.broadcaster_bot, "get_prices", return_value=prices), patch.object(
                    self.broadcaster_bot, "get_gainers", return_value=markets
                ), patch.object(self.broadcaster_bot, "get_losers", return_value=markets), patch.object(
                    self.broadcaster_bot, "get_trending", return_value=trending
                ), patch.object(self.broadcaster_bot, "format_price_broadcast", return_value="price"), patch.object(
                    self.broadcaster_bot, "format_movers", return_value="movers"
                ), patch.object(self.broadcaster_bot, "format_trending", return_value="trending"), patch.object(
                    self.broadcaster_bot,
                    "send_to_telegram",
                    side_effect=lambda _message, label: labels.append(label) or True,
                ), patch.object(self.broadcaster_bot, "ping_assistant_bot"):
                    self.broadcaster_bot.main()

                self.assertEqual(expected, labels)

    def test_dry_run_returns_labels_without_sending_or_writing_database(self):
        prices = {coin["id"]: {"usd": 1, "cny": 1} for coin in self.broadcaster_bot.COINS}
        markets = [{"id": "bitcoin", "symbol": "btc"}]
        trending = [{"name": "Bitcoin", "symbol": "btc"}]

        with patch.object(self.broadcaster_bot, "FORCE_DAILY_RANKINGS", True), patch.object(
            self.broadcaster_bot, "datetime", FakeDateTime
        ), patch.object(
            self.broadcaster_bot, "get_prices", return_value=prices
        ), patch.object(self.broadcaster_bot, "get_gainers", return_value=markets), patch.object(
            self.broadcaster_bot, "get_losers", return_value=markets
        ), patch.object(self.broadcaster_bot, "get_trending", return_value=trending), patch.object(
            self.broadcaster_bot, "format_price_broadcast", return_value="price"
        ), patch.object(self.broadcaster_bot, "format_movers", return_value="movers"), patch.object(
            self.broadcaster_bot, "format_trending", return_value="trending"
        ), patch.object(self.broadcaster_bot, "send_to_telegram") as send_mock, patch.object(
            self.broadcaster_bot, "init_database"
        ) as init_database_mock, patch.object(
            self.broadcaster_bot, "record_price_snapshots"
        ) as record_mock, patch.object(
            self.broadcaster_bot, "ping_assistant_bot"
        ) as ping_mock:
            result = self.broadcaster_bot.run_broadcast(
                send_messages=False,
                dry_run=True,
                trigger_source="test",
            )

        self.assertTrue(result["success"])
        self.assertTrue(result["dry_run"])
        self.assertEqual("test", result["trigger_source"])
        self.assertEqual(
            ["price_broadcast", "daily_gainers", "daily_losers", "daily_trending"],
            result["message_labels"],
        )
        self.assertEqual(4, result["planned_count"])
        self.assertEqual(0, result["sent_count"])
        send_mock.assert_not_called()
        init_database_mock.assert_not_called()
        record_mock.assert_not_called()
        ping_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
