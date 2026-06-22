import importlib
import sys
import types
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BROADCASTER_DIR = PROJECT_ROOT / "broadcaster"


class FakeTimeout(Exception):
    pass


class AnomalyRadarTests(unittest.TestCase):
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
            post=lambda *args, **kwargs: None,
        )
        sys.modules["httpx"] = types.SimpleNamespace(get=lambda *args, **kwargs: None)
        self.bot = importlib.import_module("broadcaster_bot")
        self.bot._radar_cooldowns.clear()
        self.bot._radar_hour_counts.clear()

    def tearDown(self):
        sys.path = self.original_sys_path
        for name in self.module_names:
            original = self.original_modules[name]
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original

    @staticmethod
    def market(coin_id, symbol, change, price=100, updated="2026-06-22T08:16:40Z"):
        return {
            "id": coin_id,
            "symbol": symbol,
            "current_price": price,
            "price_change_percentage_1h_in_currency": change,
            "last_updated": updated,
        }

    def run_radar(
        self,
        markets,
        current=datetime(2026, 6, 22, 10, 17),
        dry_run=True,
        send_effect=True,
        production_enabled=False,
    ):
        with patch.object(self.bot, "get_hourly_markets", return_value=markets), patch.object(
            self.bot, "send_to_telegram", return_value=send_effect
        ) as send_mock, patch.object(
            self.bot, "RADAR_PRODUCTION_ENABLED", production_enabled
        ):
            result = self.bot.run_anomaly_radar(
                send_messages=not dry_run,
                dry_run=dry_run,
                trigger_source="test",
                current_time=current,
            )
        return result, send_mock

    def test_threshold_boundaries_trigger_and_values_below_do_not(self):
        markets = [
            self.market("bitcoin", "btc", 2.5),
            self.market("ethereum", "eth", -2.5),
            self.market("solana", "sol", 4.0),
            self.market("cardano", "ada", -4.0),
            self.market("dogecoin", "doge", 3.999),
            self.market("polkadot", "dot", -3.999),
        ]
        result, send_mock = self.run_radar(markets)

        self.assertEqual(4, result["candidate_count"])
        self.assertEqual(3, result["planned_count"])
        self.assertEqual(1, len(result["hourly_limit_skipped"]))
        send_mock.assert_not_called()

    def test_default_real_send_is_hard_blocked_before_data_fetch(self):
        with patch.object(self.bot, "get_hourly_markets") as fetch_mock, patch.object(
            self.bot, "send_to_telegram"
        ) as send_mock, patch.object(self.bot, "RADAR_PRODUCTION_ENABLED", False):
            result = self.bot.run_anomaly_radar(
                send_messages=True,
                dry_run=False,
                trigger_source="test",
                current_time=datetime(2026, 6, 22, 10, 17),
            )

        self.assertTrue(result["production_blocked"])
        self.assertEqual(["radar_real_send_disabled"], result["skipped"])
        fetch_mock.assert_not_called()
        send_mock.assert_not_called()

    def test_dry_run_never_sends_or_claims_cooldown(self):
        market = self.market("bitcoin", "btc", 3.0)
        result, send_mock = self.run_radar([market])

        self.assertEqual(1, result["planned_count"])
        self.assertEqual(0, result["sent_count"])
        self.assertEqual({}, self.bot._radar_cooldowns)
        self.assertEqual({}, self.bot._radar_hour_counts)
        send_mock.assert_not_called()

    def test_same_coin_same_direction_cools_down_for_two_hours(self):
        market = self.market("bitcoin", "btc", 3.0)
        first, _ = self.run_radar(
            [market],
            current=datetime(2026, 6, 22, 10, 0),
            dry_run=False,
            production_enabled=True,
        )
        second, second_send = self.run_radar(
            [market],
            current=datetime(2026, 6, 22, 11, 59),
            dry_run=False,
            production_enabled=True,
        )
        boundary, boundary_send = self.run_radar(
            [market],
            current=datetime(2026, 6, 22, 12, 0),
            dry_run=False,
            production_enabled=True,
        )

        self.assertEqual(1, first["sent_count"])
        self.assertEqual(1, len(second["cooldown_skipped"]))
        second_send.assert_not_called()
        self.assertEqual(1, boundary["sent_count"])
        self.assertEqual(1, boundary_send.call_count)

    def test_opposite_direction_has_independent_cooldown(self):
        up = self.market("ethereum", "eth", 3.0)
        down = self.market("ethereum", "eth", -3.0)
        self.run_radar(
            [up], dry_run=False, production_enabled=True
        )
        result, send_mock = self.run_radar(
            [down],
            current=datetime(2026, 6, 22, 10, 30),
            dry_run=False,
            production_enabled=True,
        )

        self.assertEqual(1, result["sent_count"])
        self.assertEqual(1, send_mock.call_count)

    def test_channel_hourly_limit_selects_only_three_strongest(self):
        markets = [
            self.market("bitcoin", "btc", 2.5),
            self.market("ethereum", "eth", 5.0),
            self.market("solana", "sol", -8.0),
            self.market("cardano", "ada", 6.0),
        ]
        result, _ = self.run_radar(markets)
        labels = [message["label"] for message in result["messages"]]

        self.assertEqual(3, result["planned_count"])
        self.assertEqual(
            ["anomaly_radar_sol_down", "anomaly_radar_ada_up", "anomaly_radar_eth_up"],
            labels,
        )
        self.assertEqual(["bitcoin"], [item["coin_id"] for item in result["hourly_limit_skipped"]])

    def test_existing_hour_count_reduces_remaining_quota(self):
        self.bot._radar_hour_counts["2026-06-22:10"] = 2
        markets = [
            self.market("bitcoin", "btc", 3.0),
            self.market("ethereum", "eth", 4.0),
        ]
        result, _ = self.run_radar(markets)
        self.assertEqual(1, result["planned_count"])
        self.assertEqual(1, len(result["hourly_limit_skipped"]))

    def test_duplicate_coin_rows_trigger_only_once(self):
        market = self.market("bitcoin", "btc", 3.0)
        result, _ = self.run_radar([market, dict(market)])
        self.assertEqual(1, result["candidate_count"])
        self.assertEqual(1, result["planned_count"])

    def test_missing_change_price_or_timestamp_is_skipped(self):
        markets = [
            self.market("bitcoin", "btc", None),
            self.market("ethereum", "eth", 3.0, price=None),
            self.market("solana", "sol", 5.0, updated=None),
        ]
        result, _ = self.run_radar(markets)
        self.assertEqual(0, result["planned_count"])
        self.assertEqual(3, len(result["data_skipped"]))

    def test_failed_send_does_not_claim_cooldown_or_hour_quota(self):
        market = self.market("bitcoin", "btc", 3.0)
        result, _ = self.run_radar(
            [market], dry_run=False, send_effect=False, production_enabled=True
        )
        self.assertTrue(result["errors"])
        self.assertEqual({}, self.bot._radar_cooldowns)
        self.assertEqual({}, self.bot._radar_hour_counts)

    def test_uncertain_send_claims_cooldown_to_prevent_duplicate(self):
        market = self.market("bitcoin", "btc", 3.0)
        first, _ = self.run_radar(
            [market], dry_run=False, send_effect="uncertain", production_enabled=True
        )
        retry, retry_send = self.run_radar(
            [market],
            current=datetime(2026, 6, 22, 10, 30),
            dry_run=False,
            production_enabled=True,
        )
        self.assertEqual(1, len(first["uncertain"]))
        self.assertEqual(1, len(retry["cooldown_skipped"]))
        retry_send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
