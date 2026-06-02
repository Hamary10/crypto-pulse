import importlib.util
import sys
import types
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BROADCASTER_DIR = PROJECT_ROOT / "broadcaster"
sys.path.insert(0, str(BROADCASTER_DIR))


class BroadcasterFormatterTests(unittest.TestCase):
    def setUp(self):
        sys.modules.setdefault(
            "pytz",
            types.SimpleNamespace(timezone=lambda _name: None),
        )
        spec = importlib.util.spec_from_file_location(
            "broadcaster_formatters",
            BROADCASTER_DIR / "formatters.py",
        )
        self.formatters = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.formatters)

        self.main_coins = [
            {"id": "bitcoin", "symbol": "BTC"},
            {"id": "ethereum", "symbol": "ETH"},
            {"id": "tether", "symbol": "USDT"},
            {"id": "binancecoin", "symbol": "BNB"},
            {"id": "solana", "symbol": "SOL"},
            {"id": "ripple", "symbol": "XRP"},
            {"id": "dogecoin", "symbol": "DOGE"},
            {"id": "cardano", "symbol": "ADA"},
            {"id": "polkadot", "symbol": "DOT"},
            {"id": "polygon-ecosystem-token", "symbol": "POL", "display_symbol": "POL（原 MATIC）"},
        ]

    def test_usdt_and_pol_are_in_main_coin_list(self):
        coin_ids = [coin["id"] for coin in self.main_coins]
        symbols = [coin["symbol"] for coin in self.main_coins]

        self.assertIn("tether", coin_ids)
        self.assertIn("USDT", symbols)
        self.assertIn("polygon-ecosystem-token", coin_ids)
        self.assertIn("POL", symbols)
        self.assertNotIn("matic-network", coin_ids)
        self.assertNotIn("MATIC", symbols)

    def test_usdt_rate_only_formats_cny(self):
        text = self.formatters.format_price_broadcast(
            [{"id": "tether", "symbol": "USDT"}, {"id": "polygon-ecosystem-token", "symbol": "POL", "display_symbol": "POL（原 MATIC）"}],
            {"tether": {"cny": 7.12, "usd": 1.0, "mmk": 3500}},
        )

        self.assertIn("💱 USDT/CNY 参考价：¥7.12", text)
        self.assertNotIn("USDT/USD", text)
        self.assertNotIn("USDT/MMK", text)

    def test_pol_display_name_mentions_original_matic(self):
        text = self.formatters.format_price_broadcast(
            [{"id": "polygon-ecosystem-token", "symbol": "POL", "display_symbol": "POL（原 MATIC）"}],
            {"tether": {"cny": 7.12}, "polygon-ecosystem-token": {"cny": 2.1}},
        )

        self.assertIn("POL（原 MATIC）: ¥2.10", text)

    def test_missing_usdt_rate_does_not_break_broadcast(self):
        buffer = StringIO()
        with patch("sys.stdout", buffer):
            text = self.formatters.format_price_broadcast(
                [{"id": "tether", "symbol": "USDT"}],
                {"tether": {"usd": 1.0}},
            )

        self.assertNotIn("USDT/CNY 参考价", text)
        self.assertIn("Missing USDT rate: cny", buffer.getvalue())

    def test_missing_coin_data_is_logged(self):
        buffer = StringIO()
        with patch("sys.stdout", buffer):
            text = self.formatters.format_price_broadcast(
                [{"id": "bitcoin", "symbol": "BTC"}],
                {},
            )

        self.assertIn("📊 加密货币行情更新", text)
        self.assertIn("Missing coin data: bitcoin", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
