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

    def test_daily_rankings_send_at_0829(self):
        FakeDateTime.current = datetime(2026, 6, 4, 8, 29)

        with patch.object(self.broadcaster_bot, "FORCE_DAILY_RANKINGS", False), patch.object(
            self.broadcaster_bot, "datetime", FakeDateTime
        ):
            self.assertTrue(self.broadcaster_bot.should_send_daily_rankings())

    def test_daily_rankings_do_not_send_at_0830(self):
        FakeDateTime.current = datetime(2026, 6, 4, 8, 30)

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


if __name__ == "__main__":
    unittest.main()
