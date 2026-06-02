import os
import time
from typing import Any, Dict, List, Optional

import httpx


BASE_URL = "https://api.coingecko.com/api/v3"
CACHE_TTL = 600
CG_DEMO_API_KEY = os.getenv("CG_DEMO_API_KEY")

_cache: Dict[str, Dict[str, Any]] = {}


def _get_cached(key: str) -> Optional[Any]:
    cached = _cache.get(key)
    if cached and time.time() - cached["timestamp"] < CACHE_TTL:
        print(f"Using CoinGecko cache: {key}")
        return cached["data"]
    return None


def _get_any_cached(key: str) -> Optional[Any]:
    cached = _cache.get(key)
    if cached:
        print(f"Using stale CoinGecko cache: {key}")
        return cached["data"]
    return None


def _set_cached(key: str, data: Any) -> Any:
    _cache[key] = {"data": data, "timestamp": time.time()}
    return data


def _headers() -> Dict[str, str]:
    if not CG_DEMO_API_KEY:
        return {}
    return {"x-cg-demo-api-key": CG_DEMO_API_KEY}


def _rate_limited() -> Dict[str, str]:
    return {"_status": "rate_limited"}


def _error() -> Dict[str, str]:
    return {"_status": "error"}


def is_rate_limited(data: Any) -> bool:
    return isinstance(data, dict) and data.get("_status") == "rate_limited"


def is_error(data: Any) -> bool:
    return isinstance(data, dict) and data.get("_status") == "error"


def _get(path: str, params: Dict[str, Any], cache_key: str) -> Optional[Any]:
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        response = httpx.get(
            f"{BASE_URL}{path}",
            params=params,
            headers=_headers(),
            timeout=12,
        )
        if response.status_code == 429:
            stale = _get_any_cached(cache_key)
            if stale is not None:
                print(f"CoinGecko rate limited; stale cache returned: {cache_key}")
                return stale
            print(f"CoinGecko rate limited; no cache available: {cache_key}")
            return _rate_limited()

        response.raise_for_status()
        data = response.json()
        print(f"CoinGecko request succeeded: {path} cache_key={cache_key}")
        return _set_cached(cache_key, data)
    except Exception as exc:
        stale = _get_any_cached(cache_key)
        if stale is not None:
            print(f"CoinGecko request failed; stale cache returned: {cache_key}")
            return stale
        print(f"CoinGecko request failed: {path} {exc}")
        return _error()


def get_prices(coin_ids: List[str]) -> Dict[str, Any]:
    unique_ids = sorted(set(coin_ids))
    result: Dict[str, Any] = {}
    missing_ids = []
    for coin_id in unique_ids:
        cached = _get_cached(f"price:{coin_id}")
        if cached is not None:
            result[coin_id] = cached
        else:
            missing_ids.append(coin_id)

    if not missing_ids:
        return result

    data = _get(
        "/simple/price",
        {
            "ids": ",".join(missing_ids),
            "vs_currencies": "usd,cny",
            "include_market_cap": "true",
            "include_24hr_vol": "true",
            "include_24hr_change": "true",
        },
        f"prices:{','.join(missing_ids)}",
    )
    if is_rate_limited(data):
        return {"_status": "rate_limited"}
    if is_error(data):
        return {"_status": "error"}
    if not isinstance(data, dict):
        return result

    _set_cached(f"prices:{','.join(missing_ids)}", data)
    for coin_id in missing_ids:
        item = data.get(coin_id)
        if not item:
            continue
        result[coin_id] = item
        _set_cached(f"price:{coin_id}", item)
    return result


def get_markets(limit: int = 100) -> List[Dict[str, Any]]:
    data = _get(
        "/coins/markets",
        {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": limit,
            "page": 1,
            "sparkline": "false",
            "price_change_percentage": "24h",
        },
        f"markets:{limit}",
    )
    if is_rate_limited(data):
        return [{"_status": "rate_limited"}]
    if is_error(data):
        return [{"_status": "error"}]
    return data if isinstance(data, list) else []


def get_gainers(limit: int = 10) -> List[Dict[str, Any]]:
    markets = get_markets(100)
    if markets and (is_rate_limited(markets[0]) or is_error(markets[0])):
        return markets
    markets = [m for m in markets if m.get("price_change_percentage_24h") is not None]
    return sorted(markets, key=lambda m: m.get("price_change_percentage_24h", 0), reverse=True)[:limit]


def get_losers(limit: int = 10) -> List[Dict[str, Any]]:
    markets = get_markets(100)
    if markets and (is_rate_limited(markets[0]) or is_error(markets[0])):
        return markets
    markets = [m for m in markets if m.get("price_change_percentage_24h") is not None]
    return sorted(markets, key=lambda m: m.get("price_change_percentage_24h", 0))[:limit]


def get_trending(limit: int = 10) -> List[Dict[str, Any]]:
    data = _get("/search/trending", {}, "trending")
    if is_rate_limited(data):
        return [{"_status": "rate_limited"}]
    if is_error(data):
        return [{"_status": "error"}]
    coins = data.get("coins", []) if isinstance(data, dict) else []
    return [coin.get("item", {}) for coin in coins[:limit]]


def simple_price_to_snapshot(coin_id: str, symbol: str, data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "coin_id": coin_id,
        "symbol": symbol,
        "price_usd": data.get("usd"),
        "price_cny": data.get("cny"),
        "market_cap": data.get("usd_market_cap"),
        "volume_24h": data.get("usd_24h_vol"),
        "price_change_percentage_24h": data.get("usd_24h_change"),
    }


def market_to_snapshot(market: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "coin_id": market.get("id"),
        "symbol": market.get("symbol"),
        "price_usd": market.get("current_price"),
        "price_cny": None,
        "market_cap": market.get("market_cap"),
        "volume_24h": market.get("total_volume"),
        "price_change_percentage_24h": market.get("price_change_percentage_24h"),
    }
