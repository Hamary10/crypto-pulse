import asyncio
import importlib
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSISTANT_DIR = PROJECT_ROOT / "assistant"


class FakeHTTPException(Exception):
    def __init__(self, status_code, detail):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class FakeFastAPI:
    def post(self, _path):
        return lambda func: func

    def get(self, _path):
        return lambda func: func


class FakeRequest:
    def __init__(self, headers=None, payload=None):
        self.headers = headers or {}
        self.payload = payload or {}

    async def json(self):
        return self.payload


class InternalBroadcastTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False)
        self.tmp.close()
        os.environ["DATABASE_PATH"] = self.tmp.name
        os.environ["INTERNAL_BROADCAST_SECRET"] = "test-secret"
        os.environ.pop("ALLOW_REAL_BROADCAST", None)
        self.original_sys_path = list(sys.path)
        sys.path.insert(0, str(ASSISTANT_DIR))
        sys.path.insert(0, str(PROJECT_ROOT))

        self.module_names = [
            "assistant_bot",
            "database",
            "coingecko_client",
            "formatters",
            "broadcaster",
            "broadcaster.broadcaster_bot",
            "broadcaster.coingecko_client",
            "broadcaster.database",
            "broadcaster.formatters",
            "fastapi",
            "httpx",
            "pytz",
            "requests",
        ]
        self.original_modules = {name: sys.modules.get(name) for name in self.module_names}
        for name in self.module_names:
            sys.modules.pop(name, None)

        fake_fastapi = types.SimpleNamespace(
            FastAPI=lambda: FakeFastAPI(),
            HTTPException=FakeHTTPException,
            Request=object,
        )
        fake_httpx = types.SimpleNamespace(AsyncClient=object, get=lambda *args, **kwargs: None)
        fake_pytz = types.SimpleNamespace(timezone=lambda name: name)
        fake_requests = types.SimpleNamespace(get=lambda *args, **kwargs: None, post=lambda *args, **kwargs: None)
        sys.modules["fastapi"] = fake_fastapi
        sys.modules["httpx"] = fake_httpx
        sys.modules["pytz"] = fake_pytz
        sys.modules["requests"] = fake_requests

        self.assistant_bot = importlib.import_module("assistant_bot")
        self.broadcaster_bot = sys.modules["broadcaster.broadcaster_bot"]

    def tearDown(self):
        sys.path = self.original_sys_path
        for name in self.module_names:
            original = self.original_modules[name]
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original
        os.environ.pop("INTERNAL_BROADCAST_SECRET", None)
        os.environ.pop("ALLOW_REAL_BROADCAST", None)
        os.environ.pop("ALLOWED_TELEGRAM_GROUP_IDS", None)
        os.environ.pop("TELEGRAM_BOT_USERNAME_2", None)
        try:
            os.unlink(self.tmp.name)
        except OSError:
            pass

    def run_endpoint(self, request, dry_run=True):
        return asyncio.run(self.assistant_bot.internal_broadcast_run(request, dry_run=dry_run))

    def test_missing_secret_is_rejected(self):
        with self.assertRaises(FakeHTTPException) as context:
            self.run_endpoint(FakeRequest())
        self.assertEqual(401, context.exception.status_code)

    def test_wrong_secret_is_rejected(self):
        request = FakeRequest({"X-Internal-Broadcast-Secret": "wrong"})
        with self.assertRaises(FakeHTTPException) as context:
            self.run_endpoint(request)
        self.assertEqual(401, context.exception.status_code)

    def test_correct_secret_dry_run_returns_result_without_sending(self):
        expected = {"success": True, "dry_run": True, "message_labels": ["price_broadcast"]}
        request = FakeRequest({"X-Internal-Broadcast-Secret": "test-secret"})
        with patch.object(self.assistant_bot, "run_broadcast", return_value=expected) as mocked:
            result = self.run_endpoint(request)

        self.assertEqual(expected, result)
        mocked.assert_called_once_with(
            send_messages=False,
            dry_run=True,
            trigger_source="render_http",
        )

    def test_send_mode_is_rejected_when_real_broadcast_is_disabled(self):
        request = FakeRequest({"X-Internal-Broadcast-Secret": "test-secret"})
        with self.assertRaises(FakeHTTPException) as context:
            self.run_endpoint(request, dry_run=False)
        self.assertEqual(403, context.exception.status_code)

    def test_real_send_path_requires_explicit_environment_gate(self):
        prices = {coin["id"]: {"usd": 1, "cny": 1} for coin in self.broadcaster_bot.COINS}
        markets = [{"id": "bitcoin", "symbol": "btc"}]
        trending = [{"name": "Bitcoin", "symbol": "btc"}]
        request = FakeRequest({"X-Internal-Broadcast-Secret": "test-secret"})
        context = {
            "now": types.SimpleNamespace(hour=8),
            "current_time_local": "2026-06-10T08:17:00+08:00",
            "allowed_window": "even hours, minute 10-45 Asia/Shanghai",
            "within_allowed_window": True,
            "slots": {
                "price_broadcast": "price:2026-06-10:08",
                "daily_gainers": "daily_gainers:2026-06-10",
                "daily_losers": "daily_losers:2026-06-10",
                "daily_trending": "daily_trending:2026-06-10",
            },
        }

        with patch.dict(os.environ, {"ALLOW_REAL_BROADCAST": "true"}), patch.object(
            self.broadcaster_bot, "get_broadcast_context", return_value=context
        ), patch.object(
            self.broadcaster_bot, "should_send_daily_rankings", return_value=True
        ), patch.object(self.broadcaster_bot, "init_database"), patch.object(
            self.broadcaster_bot, "record_price_snapshots"
        ), patch.object(self.broadcaster_bot, "get_prices", return_value=prices), patch.object(
            self.broadcaster_bot, "get_gainers", return_value=markets
        ), patch.object(self.broadcaster_bot, "get_losers", return_value=markets), patch.object(
            self.broadcaster_bot, "get_trending", return_value=trending
        ), patch.object(self.broadcaster_bot, "format_price_broadcast", return_value="price"), patch.object(
            self.broadcaster_bot, "format_movers", return_value="movers"
        ), patch.object(self.broadcaster_bot, "format_trending", return_value="trending"), patch.object(
            self.broadcaster_bot, "send_to_telegram", return_value=True
        ) as send_mock, patch.object(self.broadcaster_bot, "ping_assistant_bot"):
            result = self.run_endpoint(request, dry_run=False)

        self.assertTrue(result["success"])
        self.assertFalse(result["dry_run"])
        self.assertEqual(4, result["planned_count"])
        self.assertEqual(4, result["sent_count"])
        self.assertEqual(4, send_mock.call_count)

    def test_omitted_dry_run_defaults_to_safe_mode(self):
        expected = {"success": True, "dry_run": True, "sent_count": 0}
        request = FakeRequest({"X-Internal-Broadcast-Secret": "test-secret"})

        with patch.dict(os.environ, {"ALLOW_REAL_BROADCAST": "true"}), patch.object(
            self.assistant_bot,
            "run_broadcast",
            return_value=expected,
        ) as mocked:
            result = self.run_endpoint(request)

        self.assertEqual(expected, result)
        mocked.assert_called_once_with(
            send_messages=False,
            dry_run=True,
            trigger_source="render_http",
        )

    def test_busy_lock_returns_conflict(self):
        request = FakeRequest({"X-Internal-Broadcast-Secret": "test-secret"})

        async def call_while_locked():
            async with self.assistant_bot._broadcast_lock:
                return await self.assistant_bot.internal_broadcast_run(request, dry_run=True)

        with self.assertRaises(FakeHTTPException) as context:
            asyncio.run(call_while_locked())
        self.assertEqual(409, context.exception.status_code)

    def test_webhook_empty_update_is_unchanged_and_does_not_send(self):
        with patch.object(self.assistant_bot, "send_telegram_message") as send_mock:
            result = asyncio.run(self.assistant_bot.webhook(FakeRequest(payload={})))
        self.assertEqual({"status": "ok"}, result)
        send_mock.assert_not_called()

    def test_allowed_group_command_is_processed(self):
        payload = {
            "message": {
                "chat": {"id": -100123, "type": "supergroup"},
                "text": "/help",
                "from": {"id": 123},
            }
        }
        with patch.dict(
            os.environ,
            {"ALLOWED_TELEGRAM_GROUP_IDS": "-100123"},
        ), patch.object(self.assistant_bot, "upsert_user") as user_mock, patch.object(
            self.assistant_bot, "log_command"
        ) as log_mock, patch.object(
            self.assistant_bot, "handle_command", return_value="help"
        ) as command_mock, patch.object(
            self.assistant_bot,
            "send_telegram_message",
            return_value={"ok": True},
        ) as send_mock:
            result = asyncio.run(self.assistant_bot.webhook(FakeRequest(payload=payload)))

        self.assertEqual({"status": "ok"}, result)
        user_mock.assert_called_once()
        log_mock.assert_called_once()
        command_mock.assert_called_once()
        send_mock.assert_called_once_with(-100123, "help")

    def test_unauthorized_group_command_is_silently_ignored(self):
        payload = {
            "message": {
                "chat": {"id": -100999, "type": "supergroup"},
                "text": "/price btc",
                "from": {"id": 123},
            }
        }
        with patch.dict(
            os.environ,
            {"ALLOWED_TELEGRAM_GROUP_IDS": "-100123"},
        ), patch.object(self.assistant_bot, "upsert_user") as user_mock, patch.object(
            self.assistant_bot, "log_command"
        ) as log_mock, patch.object(
            self.assistant_bot, "handle_command"
        ) as command_mock, patch.object(
            self.assistant_bot, "send_telegram_message"
        ) as send_mock:
            result = asyncio.run(self.assistant_bot.webhook(FakeRequest(payload=payload)))

        self.assertEqual({"status": "ok"}, result)
        user_mock.assert_not_called()
        log_mock.assert_not_called()
        command_mock.assert_not_called()
        send_mock.assert_not_called()

    def test_private_command_keeps_existing_behavior(self):
        payload = {
            "message": {
                "chat": {"id": 123, "type": "private"},
                "text": "/help",
                "from": {"id": 123},
            }
        }
        with patch.dict(
            os.environ,
            {"ALLOWED_TELEGRAM_GROUP_IDS": "-100999"},
        ), patch.object(
            self.assistant_bot, "handle_command", return_value="help"
        ) as command_mock, patch.object(
            self.assistant_bot,
            "send_telegram_message",
            return_value={"ok": True},
        ):
            result = asyncio.run(self.assistant_bot.webhook(FakeRequest(payload=payload)))

        self.assertEqual({"status": "ok"}, result)
        command_mock.assert_called_once()

    def test_supported_commands_are_routed_normally(self):
        cases = [
            ("/price BTC", "/price", ["BTC"]),
            ("/top", "/top", []),
            ("/help", "/help", []),
        ]

        for text, expected_command, expected_args in cases:
            with self.subTest(text=text):
                payload = {
                    "message": {
                        "chat": {"id": -100123, "type": "supergroup"},
                        "text": text,
                        "from": {"id": 123},
                    }
                }
                with patch.dict(
                    os.environ,
                    {"ALLOWED_TELEGRAM_GROUP_IDS": "-100123"},
                ), patch.object(
                    self.assistant_bot,
                    "handle_command",
                    return_value="response",
                ) as command_mock, patch.object(
                    self.assistant_bot,
                    "send_telegram_message",
                    return_value={"ok": True},
                ):
                    result = asyncio.run(
                        self.assistant_bot.webhook(FakeRequest(payload=payload))
                    )

                self.assertEqual({"status": "ok"}, result)
                command_mock.assert_called_once_with(
                    expected_command,
                    expected_args,
                    -100123,
                    {"id": 123},
                )

    def test_commands_for_other_bot_are_silently_ignored(self):
        commands = [
            "/id@CryptoPulseGuardBot",
            "/status@CryptoPulseGuardBot",
            "/guard_status@CryptoPulseGuardBot",
            "/rules@CryptoPulseGuardBot",
            "/abc@CryptoPulseGuardBot",
        ]

        for text in commands:
            with self.subTest(text=text):
                payload = {
                    "message": {
                        "chat": {"id": -100123, "type": "supergroup"},
                        "text": text,
                        "from": {"id": 123},
                    }
                }
                with patch.dict(
                    os.environ,
                    {
                        "ALLOWED_TELEGRAM_GROUP_IDS": "-100123",
                        "TELEGRAM_BOT_USERNAME_2": "CryptoService2_bot",
                    },
                ), patch.object(self.assistant_bot, "upsert_user") as user_mock, patch.object(
                    self.assistant_bot, "log_command"
                ) as log_mock, patch.object(
                    self.assistant_bot, "handle_command"
                ) as command_mock, patch.object(
                    self.assistant_bot, "send_telegram_message"
                ) as send_mock:
                    result = asyncio.run(
                        self.assistant_bot.webhook(FakeRequest(payload=payload))
                    )

                self.assertEqual({"status": "ok"}, result)
                user_mock.assert_not_called()
                log_mock.assert_not_called()
                command_mock.assert_not_called()
                send_mock.assert_not_called()

    def test_groupguard_short_commands_are_silently_ignored(self):
        commands = [
            "/gid",
            "/gst",
            "/grules",
            "/gabout",
            "/gdisc",
            "/ghelp",
            "/grep",
        ]

        for text in commands:
            with self.subTest(text=text):
                payload = {
                    "message": {
                        "chat": {"id": -100123, "type": "supergroup"},
                        "text": text,
                        "from": {"id": 123},
                    }
                }
                with patch.dict(
                    os.environ,
                    {"ALLOWED_TELEGRAM_GROUP_IDS": "-100123"},
                ), patch.object(self.assistant_bot, "upsert_user") as user_mock, patch.object(
                    self.assistant_bot, "log_command"
                ) as log_mock, patch.object(
                    self.assistant_bot, "handle_command"
                ) as command_mock, patch.object(
                    self.assistant_bot, "send_telegram_message"
                ) as send_mock:
                    result = asyncio.run(
                        self.assistant_bot.webhook(FakeRequest(payload=payload))
                    )

                self.assertEqual({"status": "ok"}, result)
                user_mock.assert_not_called()
                log_mock.assert_not_called()
                command_mock.assert_not_called()
                send_mock.assert_not_called()

    def test_unknown_command_without_target_returns_unknown_message(self):
        payload = {
            "message": {
                "chat": {"id": -100123, "type": "supergroup"},
                "text": "/abc",
                "from": {"id": 123},
            }
        }
        with patch.dict(
            os.environ,
            {"ALLOWED_TELEGRAM_GROUP_IDS": "-100123"},
        ), patch.object(
            self.assistant_bot,
            "send_telegram_message",
            return_value={"ok": True},
        ) as send_mock:
            result = asyncio.run(self.assistant_bot.webhook(FakeRequest(payload=payload)))

        self.assertEqual({"status": "ok"}, result)
        send_mock.assert_called_once_with(
            -100123,
            "❌ 未知命令，使用 /help 查看可用指令。",
        )

    def test_unknown_command_targeted_to_this_bot_returns_unknown_message(self):
        payload = {
            "message": {
                "chat": {"id": -100123, "type": "supergroup"},
                "text": "/abc@Bot2Username",
                "from": {"id": 123},
            }
        }
        with patch.dict(
            os.environ,
            {
                "ALLOWED_TELEGRAM_GROUP_IDS": "-100123",
                "TELEGRAM_BOT_USERNAME_2": "Bot2Username",
            },
        ), patch.object(
            self.assistant_bot,
            "send_telegram_message",
            return_value={"ok": True},
        ) as send_mock:
            result = asyncio.run(self.assistant_bot.webhook(FakeRequest(payload=payload)))

        self.assertEqual({"status": "ok"}, result)
        send_mock.assert_called_once_with(
            -100123,
            "❌ 未知命令，使用 /help 查看可用指令。",
        )


if __name__ == "__main__":
    unittest.main()
