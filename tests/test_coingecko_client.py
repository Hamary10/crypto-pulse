import importlib
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSISTANT_DIR = PROJECT_ROOT / "assistant"
sys.path.insert(0, str(ASSISTANT_DIR))


class FakeResponse:
    def __init__(self, status_code=200, data=None):
        self.status_code = status_code
        self._data = data or {}

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"{self.status_code} error")


class CoinGeckoClientTests(unittest.TestCase):
    def import_client(self, api_key=None):
        if api_key is None:
            os.environ.pop("CG_DEMO_API_KEY", None)
        else:
            os.environ["CG_DEMO_API_KEY"] = api_key

        if "coingecko_client" in sys.modules:
            del sys.modules["coingecko_client"]
        sys.modules.setdefault("httpx", types.SimpleNamespace(get=lambda *args, **kwargs: None))
        return importlib.import_module("coingecko_client")

    def test_demo_api_key_adds_header(self):
        client = self.import_client("demo-key")
        captured = {}

        def fake_get(url, params=None, headers=None, timeout=None):
            captured["headers"] = headers
            return FakeResponse(200, {"bitcoin": {"usd": 1}})

        with patch.object(client.httpx, "get", side_effect=fake_get):
            data = client._get("/simple/price", {"ids": "bitcoin"}, "x")

        self.assertEqual(captured["headers"], {"x-cg-demo-api-key": "demo-key"})
        self.assertEqual(data["bitcoin"]["usd"], 1)

    def test_no_demo_api_key_uses_empty_headers(self):
        client = self.import_client()
        captured = {}

        def fake_get(url, params=None, headers=None, timeout=None):
            captured["headers"] = headers
            return FakeResponse(200, {"bitcoin": {"usd": 1}})

        with patch.object(client.httpx, "get", side_effect=fake_get):
            client._get("/simple/price", {"ids": "bitcoin"}, "x")

        self.assertEqual(captured["headers"], {})

    def test_429_returns_stale_cache(self):
        client = self.import_client()
        client._cache["x"] = {"data": {"cached": True}, "timestamp": 0}

        with patch.object(client.httpx, "get", return_value=FakeResponse(429)):
            data = client._get("/simple/price", {"ids": "bitcoin"}, "x")

        self.assertEqual(data, {"cached": True})

    def test_429_without_cache_returns_rate_limited(self):
        client = self.import_client()

        with patch.object(client.httpx, "get", return_value=FakeResponse(429)):
            data = client._get("/simple/price", {"ids": "bitcoin"}, "x")

        self.assertTrue(client.is_rate_limited(data))

    def test_compare_then_price_reuses_single_coin_cache(self):
        client = self.import_client()
        calls = []

        def fake_get(url, params=None, headers=None, timeout=None):
            calls.append(params["ids"])
            return FakeResponse(
                200,
                {
                    "bitcoin": {"usd": 1, "cny": 7},
                    "ethereum": {"usd": 2, "cny": 14},
                },
            )

        with patch.object(client.httpx, "get", side_effect=fake_get):
            prices = client.get_prices(["bitcoin", "ethereum"])
            price = client.get_price("bitcoin")

        self.assertEqual(prices["bitcoin"]["price_usd"], 1)
        self.assertEqual(price["price_usd"], 1)
        self.assertEqual(calls, ["bitcoin,ethereum"])

    def test_pol_and_matic_aliases_use_polygon_ecosystem_token(self):
        client = self.import_client()

        for symbol in ["POL", "pol", "MATIC", "matic", "Polygon"]:
            with self.subTest(symbol=symbol):
                self.assertEqual(
                    client.symbol_to_coingecko(symbol),
                    "polygon-ecosystem-token",
                )

    def test_pol_alias_ignores_parenthetical_description(self):
        client = self.import_client()

        self.assertEqual(
            client.symbol_to_coingecko("POL（原 MATIC）"),
            "polygon-ecosystem-token",
        )


if __name__ == "__main__":
    unittest.main()
