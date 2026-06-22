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


class FakeTimeout(Exception):
    pass


class FakeResponse:
    ok = True
    status_code = 200
    text = "ok"

    def raise_for_status(self):
        return None


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

        sys.modules["pytz"] = types.SimpleNamespace(timezone=lambda name: name)
        sys.modules["requests"] = types.SimpleNamespace(
            Timeout=FakeTimeout,
            get=lambda *args, **kwargs: None,
            post=lambda *args, **kwargs: FakeResponse(),
        )
        sys.modules["httpx"] = types.SimpleNamespace(get=lambda *args, **kwargs: None)
        self.bot = importlib.import_module("broadcaster_bot")
        self.bot._delivery_states.clear()
        self.bot._radar_cooldowns.clear()
        self.bot._radar_hour_counts.clear()

        self.prices = {
            coin["id"]: {
                "usd": 100,
                "cny": 700,
                "usd_24h_change": 1.25,
            }
            for coin in self.bot.COINS
        }
        self.markets = [
            {
                "id": "bitcoin",
                "name": "Bitcoin",
                "symbol": "btc",
                "price_change_percentage_24h": 3.2,
                "price_change_percentage_7d_in_currency": 8.4,
            },
            {
                "id": "ethereum",
                "name": "Ethereum",
                "symbol": "eth",
                "price_change_percentage_24h": -2.1,
                "price_change_percentage_7d_in_currency": -5.3,
            },
        ]
        self.trending = [{"name": "Solana", "symbol": "sol", "market_cap_rank": 5}]
        self.global_data = {
            "total_market_cap": {"usd": 2_500_000_000_000},
            "market_cap_change_percentage_24h_usd": 1.8,
            "market_cap_percentage": {"btc": 54.2},
        }

    def tearDown(self):
        sys.path = self.original_sys_path
        for name in self.module_names:
            original = self.original_modules[name]
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original

    def _run(self, current, dry_run=True, send_effect=True, prices=None):
        send_kwargs = (
            {"side_effect": send_effect}
            if isinstance(send_effect, list) or callable(send_effect)
            else {"return_value": send_effect}
        )
        with patch.object(self.bot, "init_database"), patch.object(
            self.bot, "record_price_snapshots"
        ), patch.object(self.bot, "get_prices", return_value=self.prices if prices is None else prices), patch.object(
            self.bot, "get_gainers", return_value=self.markets
        ), patch.object(self.bot, "get_losers", return_value=list(reversed(self.markets))), patch.object(
            self.bot, "get_trending", return_value=self.trending
        ), patch.object(self.bot, "get_markets", return_value=self.markets), patch.object(
            self.bot, "get_global_market_data", return_value=self.global_data
        ), patch.object(self.bot, "send_to_telegram", **send_kwargs) as send_mock, patch.object(
            self.bot, "ping_assistant_bot"
        ):
            result = self.bot.run_broadcast(
                send_messages=not dry_run,
                dry_run=dry_run,
                trigger_source="test",
                current_time=current,
            )
        return result, send_mock

    def test_github_automatic_schedule_stays_disabled_and_documents_new_cron(self):
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        active_crons = [line for line in workflow.splitlines() if line.strip().startswith("- cron:")]
        self.assertEqual([], active_crons)
        self.assertIn("cron: '17 */4 * * *'", workflow)

    def test_each_slot_routes_exactly_one_content_type(self):
        monday = 22  # 2026-06-22 is Monday
        cases = [
            (datetime(2026, 6, monday, 0, 17), "price_broadcast", True),
            (datetime(2026, 6, monday, 4, 17), "price_broadcast", True),
            (datetime(2026, 6, monday, 8, 17), "morning_market_brief", False),
            (datetime(2026, 6, monday, 12, 17), "price_broadcast", False),
            (datetime(2026, 6, monday, 16, 17), "price_broadcast", False),
            (datetime(2026, 6, monday, 20, 17), "evening_market_watch", False),
        ]
        for current, label, silent in cases:
            with self.subTest(current=current):
                result, send_mock = self._run(current)
                self.assertEqual([label], result["message_labels"])
                self.assertEqual(1, result["planned_count"])
                self.assertEqual(silent, result["silent"])
                self.assertEqual(silent, result["messages"][0]["silent"])
                send_mock.assert_not_called()

    def test_sunday_2017_routes_only_weekly_review(self):
        result, _ = self._run(datetime(2026, 6, 21, 20, 17))
        self.assertEqual(["weekly_market_review"], result["message_labels"])
        self.assertNotIn("evening_market_watch", result["message_labels"])
        self.assertNotIn("price_broadcast", result["message_labels"])

    def test_morning_and_evening_replace_regular_price_message(self):
        morning, _ = self._run(datetime(2026, 6, 22, 8, 17))
        evening, _ = self._run(datetime(2026, 6, 22, 20, 17))
        self.assertEqual(["morning_market_brief"], morning["message_labels"])
        self.assertEqual(["evening_market_watch"], evening["message_labels"])

    def test_overnight_real_sends_pass_silent_flag(self):
        for hour in (0, 4):
            with self.subTest(hour=hour):
                self.bot._delivery_states.clear()
                result, send_mock = self._run(datetime(2026, 6, 22, hour, 17), dry_run=False)
                self.assertEqual(1, result["sent_count"])
                self.assertTrue(send_mock.call_args.kwargs["silent"])

    def test_legacy_ranking_generation_is_retained_but_not_scheduled(self):
        with patch.object(self.bot, "get_gainers", return_value=self.markets), patch.object(
            self.bot, "get_losers", return_value=self.markets
        ), patch.object(self.bot, "get_trending", return_value=self.trending):
            messages = self.bot.generate_legacy_daily_ranking_messages()

        self.assertEqual(
            ["daily_gainers", "daily_losers", "daily_trending"],
            [message["label"] for message in messages],
        )

    def test_real_send_window_boundaries(self):
        for minute, should_send in ((9, False), (10, True), (45, True), (46, False)):
            with self.subTest(minute=minute):
                self.bot._delivery_states.clear()
                result, send_mock = self._run(datetime(2026, 6, 22, 12, minute), dry_run=False)
                self.assertEqual(1 if should_send else 0, result["sent_count"])
                self.assertEqual(1 if should_send else 0, send_mock.call_count)
                if not should_send:
                    self.assertIn("outside_allowed_window", result["skipped"])

    def test_unscheduled_hour_generates_nothing_even_in_dry_run(self):
        result, send_mock = self._run(datetime(2026, 6, 22, 3, 17))
        self.assertEqual([], result["message_labels"])
        self.assertEqual(["no_scheduled_content"], result["skipped"])
        send_mock.assert_not_called()

    def test_dry_run_outside_minute_window_returns_real_format_without_side_effects(self):
        result, send_mock = self._run(datetime(2026, 6, 22, 8, 46))
        self.assertEqual(["morning_market_brief"], result["message_labels"])
        self.assertIn("🌅 早间市场简报", result["messages"][0]["text"])
        self.assertNotIn("outside_allowed_window", result["skipped"])
        send_mock.assert_not_called()

    def test_same_slot_consecutive_real_requests_send_once(self):
        current = datetime(2026, 6, 22, 20, 17)
        first, first_send = self._run(current, dry_run=False)
        second, second_send = self._run(current, dry_run=False)
        self.assertEqual(1, first["sent_count"])
        self.assertEqual(0, second["sent_count"])
        self.assertEqual(1, len(second["duplicate_skipped"]))
        self.assertEqual(1, first_send.call_count)
        second_send.assert_not_called()

    def test_dry_run_does_not_claim_slot(self):
        current = datetime(2026, 6, 22, 12, 17)
        dry_result, _ = self._run(current)
        real_result, real_send = self._run(current, dry_run=False)
        self.assertEqual(0, dry_result["sent_count"])
        self.assertEqual(1, real_result["sent_count"])
        self.assertEqual(1, real_send.call_count)

    def test_failure_does_not_claim_slot_and_uncertain_blocks_retry(self):
        current = datetime(2026, 6, 22, 12, 17)
        failed, _ = self._run(current, dry_run=False, send_effect=False)
        recovered, recovered_send = self._run(current, dry_run=False)
        self.assertTrue(failed["errors"])
        self.assertEqual(1, recovered["sent_count"])
        self.assertEqual(1, recovered_send.call_count)

        self.bot._delivery_states.clear()
        uncertain, _ = self._run(current, dry_run=False, send_effect="uncertain")
        retry, retry_send = self._run(current, dry_run=False)
        self.assertEqual(1, len(uncertain["uncertain"]))
        self.assertEqual(1, len(retry["uncertain"]))
        retry_send.assert_not_called()

    def test_coingecko_failure_generates_no_message_and_claims_no_slot(self):
        current = datetime(2026, 6, 22, 12, 17)
        failed, failed_send = self._run(current, dry_run=False, prices={"_status": "error"})
        recovered, recovered_send = self._run(current, dry_run=False)
        self.assertEqual(0, failed["sent_count"])
        failed_send.assert_not_called()
        self.assertEqual(1, recovered["sent_count"])
        self.assertEqual(1, recovered_send.call_count)

    def test_telegram_payload_marks_only_overnight_slots_silent(self):
        captured = []

        def fake_post(_url, json=None, timeout=None):
            captured.append(json)
            return FakeResponse()

        with patch.object(self.bot, "BOT_TOKEN", "fake"), patch.object(
            self.bot, "CHANNEL_ID", "fake-channel"
        ), patch.object(self.bot.requests, "post", side_effect=fake_post):
            self.assertTrue(self.bot.send_to_telegram("night", "price_broadcast", silent=True))
            self.assertTrue(self.bot.send_to_telegram("day", "price_broadcast", silent=False))

        self.assertTrue(captured[0]["disable_notification"])
        self.assertFalse(captured[1]["disable_notification"])

    def test_weekly_movers_use_seven_day_field(self):
        client = sys.modules["coingecko_client"]
        markets = [
            {"symbol": "a", "price_change_percentage_7d_in_currency": -4.0},
            {"symbol": "b", "price_change_percentage_7d_in_currency": 9.0},
            {"symbol": "c", "price_change_percentage_7d_in_currency": 2.0},
        ]
        with patch.object(client, "get_markets", return_value=markets) as get_markets:
            gainers, losers = client.get_weekly_movers(2)

        get_markets.assert_called_once_with(100, "7d")
        self.assertEqual(["b", "c"], [item["symbol"] for item in gainers])
        self.assertEqual(["a", "c"], [item["symbol"] for item in losers])

    def test_weekly_reference_filter_removes_stable_and_wrapped_assets(self):
        markets = [
            {"id": "bitcoin", "symbol": "btc", "price_change_percentage_7d_in_currency": 5},
            {"id": "tether", "symbol": "usdt", "price_change_percentage_7d_in_currency": 0},
            {"id": "wrapped-bitcoin", "symbol": "wbtc", "price_change_percentage_7d_in_currency": 5},
        ]
        filtered = self.bot._filter_weekly_reference_markets(markets)
        self.assertEqual(["bitcoin"], [market["id"] for market in filtered])

    def test_global_market_data_unwraps_coingecko_data_object(self):
        client = sys.modules["coingecko_client"]
        expected = {"market_cap_percentage": {"btc": 54.2}}
        with patch.object(client, "_get", return_value={"data": expected}) as get_mock:
            result = client.get_global_market_data()

        self.assertEqual(expected, result)
        get_mock.assert_called_once_with("/global", {}, "global_market")

    def test_hourly_markets_request_cny_and_one_hour_change(self):
        client = sys.modules["coingecko_client"]
        response = [{"id": "bitcoin", "price_change_percentage_1h_in_currency": 2.5}]
        with patch.object(client, "_get", return_value=response) as get_mock:
            result = client.get_hourly_markets(["ethereum", "bitcoin", "bitcoin"])

        self.assertEqual(response, result)
        _, params, cache_key = get_mock.call_args.args
        self.assertEqual("cny", params["vs_currency"])
        self.assertEqual("bitcoin,ethereum", params["ids"])
        self.assertEqual("1h", params["price_change_percentage"])
        self.assertEqual("hourly_markets:bitcoin,ethereum", cache_key)


if __name__ == "__main__":
    unittest.main()
