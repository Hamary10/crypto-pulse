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

    def tearDown(self):
        sys.path = self.original_sys_path
        for name in self.module_names:
            original = self.original_modules[name]
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original
        os.environ.pop("INTERNAL_BROADCAST_SECRET", None)
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

    def test_send_mode_is_rejected_in_phase_one(self):
        request = FakeRequest({"X-Internal-Broadcast-Secret": "test-secret"})
        with self.assertRaises(FakeHTTPException) as context:
            self.run_endpoint(request, dry_run=False)
        self.assertEqual(403, context.exception.status_code)

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


if __name__ == "__main__":
    unittest.main()
