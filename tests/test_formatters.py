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
sys.path.insert(0, str(ASSISTANT_DIR))


class FormatterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False)
        self.tmp.close()
        os.environ["DATABASE_PATH"] = self.tmp.name

        for name in ["database", "coingecko_client", "formatters", "assistant_bot"]:
            if name in sys.modules:
                del sys.modules[name]

        fake_httpx = types.SimpleNamespace(AsyncClient=object)

        class FakeFastAPI:
            def post(self, _path):
                return lambda func: func

            def get(self, _path):
                return lambda func: func

        fake_fastapi = types.SimpleNamespace(FastAPI=lambda: FakeFastAPI(), Request=object)
        sys.modules.setdefault("httpx", fake_httpx)
        sys.modules.setdefault("fastapi", fake_fastapi)

        self.formatters = importlib.import_module("formatters")
        self.assistant_bot = importlib.import_module("assistant_bot")

    def tearDown(self):
        try:
            os.unlink(self.tmp.name)
        except OSError:
            pass

    def test_ranking_formatters_include_titles_and_disclaimer(self):
        markets = [
            {
                "name": "Bitcoin",
                "symbol": "btc",
                "current_price": 69000,
                "market_cap": 1000000,
                "price_change_percentage_24h": 5.2,
            }
        ]
        trending = [{"name": "Ethereum", "symbol": "eth", "market_cap_rank": 2}]

        top_text = self.formatters.format_market_cap(markets)
        gainers_text = self.formatters.format_movers(markets, "📈 24小时涨幅榜 TOP10")
        trending_text = self.formatters.format_trending(trending)

        self.assertIn("市值排行", top_text)
        self.assertIn("24小时涨幅榜", gainers_text)
        self.assertIn("热门币榜", trending_text)
        self.assertIn("非投资建议", top_text)
        self.assertIn("非投资建议", gainers_text)
        self.assertIn("非投资建议", trending_text)

    def test_price_command_logic_uses_friendly_response(self):
        data = {
            "coin_id": "bitcoin",
            "symbol": "BTC",
            "price_usd": 69000,
            "price_cny": 500000,
            "market_cap": 100,
            "volume_24h": 10,
            "price_change_percentage_24h": 1.5,
        }

        with patch.object(self.assistant_bot, "get_price", return_value=data):
            text = asyncio.run(
                self.assistant_bot.handle_command(
                    "/price", ["btc"], 1, {"id": 123}
                )
            )

        self.assertIn("BTC 价格", text)
        self.assertIn("CoinGecko", text)

    def test_compare_command_logic_uses_single_price_batch(self):
        prices = {
            "bitcoin": {
                "coin_id": "bitcoin",
                "symbol": "BTC",
                "price_usd": 69000,
                "price_cny": 500000,
                "price_change_percentage_24h": 1.5,
            },
            "ethereum": {
                "coin_id": "ethereum",
                "symbol": "ETH",
                "price_usd": 3500,
                "price_cny": 25000,
                "price_change_percentage_24h": -0.5,
            },
        }

        with patch.object(self.assistant_bot, "get_prices", return_value=prices) as mocked:
            text = asyncio.run(
                self.assistant_bot.handle_command(
                    "/compare", ["btc", "eth"], 1, {"id": 123}
                )
            )

        mocked.assert_called_once()
        self.assertIn("BTC vs ETH", text)
        self.assertIn("非投资建议", text)

    def test_rate_limit_message_is_not_coin_symbol_error(self):
        with patch.object(
            self.assistant_bot,
            "get_price",
            return_value={"_status": "rate_limited"},
        ):
            text = asyncio.run(
                self.assistant_bot.handle_command(
                    "/price", ["btc"], 1, {"id": 123}
                )
            )

        self.assertIn("请求过于频繁", text)
        self.assertNotIn("检查币种符号", text)


if __name__ == "__main__":
    unittest.main()
