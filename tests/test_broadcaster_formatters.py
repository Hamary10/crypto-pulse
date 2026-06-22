import importlib.util
import sys
import types
import unittest
from datetime import datetime
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

    def test_new_content_formatters_have_independent_titles_and_disclaimers(self):
        prices = {
            "bitcoin": {"cny": 720000, "usd_24h_change": 2.5},
            "ethereum": {"cny": 26000, "usd_24h_change": -1.2},
            "solana": {"cny": 1100, "usd_24h_change": 4.1},
            "tether": {"cny": 7.18},
        }
        markets = [
            {
                "id": "bitcoin",
                "name": "Bitcoin",
                "symbol": "btc",
                "price_change_percentage_24h": 2.5,
                "price_change_percentage_7d_in_currency": 8.2,
            },
            {
                "id": "ethereum",
                "name": "Ethereum",
                "symbol": "eth",
                "price_change_percentage_24h": -1.2,
                "price_change_percentage_7d_in_currency": -4.0,
            },
            {
                "id": "solana",
                "name": "Solana",
                "symbol": "sol",
                "price_change_percentage_24h": 4.1,
                "price_change_percentage_7d_in_currency": 12.0,
            },
        ]
        trending = [{"name": "Solana", "symbol": "sol", "market_cap_rank": 5}]
        global_data = {
            "total_market_cap": {"usd": 2_500_000_000_000},
            "market_cap_change_percentage_24h_usd": 1.8,
            "market_cap_percentage": {"btc": 54.2},
        }
        now = datetime(2026, 6, 22, 8, 17)

        morning = self.formatters.format_morning_brief(
            prices, markets, trending, global_data, now
        )
        evening = self.formatters.format_evening_watch(prices, markets, global_data, now)
        weekly = self.formatters.format_weekly_review(prices, markets, now)

        self.assertIn("🌅 早间市场简报", morning)
        self.assertIn("🔥 热门关注", morning)
        self.assertIn("总市值：$2.50T", morning)
        self.assertIn("BTC市场占有率：54.20%", morning)
        self.assertIn("市值前100涨跌分布", morning)
        self.assertIn("市场状态：", morning)
        self.assertIn("🌙 晚间重点观察", evening)
        self.assertIn("当前市场整体强弱", evening)
        self.assertIn("晚间总结：", evening)
        self.assertIn("观察口径", evening)
        self.assertIn("🗓 每周市场复盘", weekly)
        self.assertIn("BTC: ¥720,000.00（7d +8.20%）", weekly)
        self.assertIn("周度总结：", weekly)
        self.assertIn("近7日", weekly)
        for text in (morning, evening, weekly):
            self.assertIn("北京时间: 2026-06-22 08:17", text)
            self.assertIn("数据源：CoinGecko", text)
            self.assertIn("仅供信息参考，非投资建议。", text)

    def test_rule_sentences_never_guess_market_causes(self):
        breadth = {"up": 70, "down": 25, "flat": 5, "total": 100}
        sentence = self.formatters._morning_state_sentence(2.0, breadth)
        summary = self.formatters._evening_summary_sentence(2.0, breadth)
        combined = sentence + summary
        for forbidden in ("因为", "由于", "消息", "新闻", "资金推动"):
            self.assertNotIn(forbidden, combined)

    def test_anomaly_alert_contains_only_required_factual_fields(self):
        text = self.formatters.format_anomaly_alert(
            {
                "symbol": "btc",
                "current_price": 720000,
                "price_change_percentage_1h_in_currency": 2.5,
                "last_updated": "2026-06-22T08:16:40Z",
            }
        )
        self.assertIn("币种：BTC", text)
        self.assertIn("当前价格：¥720,000.00", text)
        self.assertIn("1小时涨跌：+2.50%", text)
        self.assertIn("数据时间（北京时间）：2026-06-22 16:16:40", text)
        self.assertNotIn("建议", text.replace("非投资建议", ""))

    def test_anomaly_alert_converts_offset_timestamp_to_beijing_time(self):
        text = self.formatters.format_anomaly_alert(
            {
                "symbol": "eth",
                "current_price": 26000,
                "price_change_percentage_1h_in_currency": -2.5,
                "last_updated": "2026-06-22T10:16:40+02:00",
            }
        )
        self.assertIn("数据时间（北京时间）：2026-06-22 16:16:40", text)
        self.assertNotIn("UTC", text)


if __name__ == "__main__":
    unittest.main()
