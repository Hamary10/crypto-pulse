"""
Crypto Pulse - 1号Bot（广播员）
部署平台：GitHub Actions
功能：定时获取行情并推送 Telegram 频道，附带 P0 基础榜单内容
"""

import os
from datetime import datetime

import pytz
import requests

from coingecko_client import (
    get_gainers,
    get_losers,
    get_prices,
    get_trending,
    is_error,
    is_rate_limited,
    market_to_snapshot,
    simple_price_to_snapshot,
)
from database import init_database, record_price_snapshots
from formatters import format_movers, format_price_broadcast, format_trending


CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN_1")
ASSISTANT_WEBHOOK_URL = os.getenv("ASSISTANT_WEBHOOK_URL")
FORCE_DAILY_RANKINGS = os.getenv("FORCE_DAILY_RANKINGS", "0") == "1"
BEIJING_TZ = pytz.timezone("Asia/Shanghai")

COINS = [
    {"id": "bitcoin", "symbol": "BTC", "emoji": "₿"},
    {"id": "ethereum", "symbol": "ETH", "emoji": "Ξ"},
    {"id": "tether", "symbol": "USDT", "emoji": "💵"},
    {"id": "binancecoin", "symbol": "BNB", "emoji": "🔶"},
    {"id": "solana", "symbol": "SOL", "emoji": "◎"},
    {"id": "ripple", "symbol": "XRP", "emoji": "💧"},
    {"id": "dogecoin", "symbol": "DOGE", "emoji": "🐕"},
    {"id": "cardano", "symbol": "ADA", "emoji": "🎴"},
    {"id": "polkadot", "symbol": "DOT", "emoji": "🔴"},
    {"id": "polygon-ecosystem-token", "symbol": "POL", "display_symbol": "POL（原 MATIC）", "emoji": "🟣"},
]


def send_to_telegram(message: str, label: str) -> bool:
    if not BOT_TOKEN or not CHANNEL_ID:
        print("Telegram channel id or bot token is not configured")
        return False

    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHANNEL_ID,
            "text": message,
            "disable_web_page_preview": True,
        }
        response = requests.post(url, json=payload, timeout=10)
        if not response.ok:
            print(f"Telegram API error ({label}): {response.status_code} {response.text}")
        response.raise_for_status()
        print(f"Sent channel message: {label}")
        return True
    except Exception as exc:
        print(f"Failed to send channel message ({label}): {exc}")
        return False


def ping_assistant_bot() -> None:
    if not ASSISTANT_WEBHOOK_URL:
        print("ASSISTANT_WEBHOOK_URL not configured, skip ping")
        return

    try:
        response = requests.get(ASSISTANT_WEBHOOK_URL, timeout=5)
        print(f"Assistant bot ping status: {response.status_code}")
    except Exception as exc:
        print(f"Assistant bot ping failed: {exc}")


def should_send_daily_rankings() -> bool:
    now = datetime.now(BEIJING_TZ)
    return FORCE_DAILY_RANKINGS or (now.hour == 8 and now.minute < 30)


def main() -> None:
    print("Broadcaster started")
    init_database()

    coin_ids = [coin["id"] for coin in COINS]
    price_data = get_prices(coin_ids)
    if is_rate_limited(price_data):
        print("CoinGecko rate limited; price broadcast skipped")
    elif is_error(price_data):
        print("CoinGecko unavailable; price broadcast skipped")
    elif price_data:
        missing_coin_ids = [coin["id"] for coin in COINS if coin["id"] not in price_data]
        for coin_id in missing_coin_ids:
            print(f"Missing coin data: {coin_id}")

        snapshots = [
            simple_price_to_snapshot(coin["id"], coin["symbol"], price_data[coin["id"]])
            for coin in COINS
            if coin["id"] in price_data
        ]
        record_price_snapshots(snapshots)
        send_to_telegram(format_price_broadcast(COINS, price_data), "price_broadcast")
    else:
        print("No price data received")

    if should_send_daily_rankings():
        gainers = get_gainers(10)
        if gainers and is_rate_limited(gainers[0]):
            print("CoinGecko rate limited; daily gainers skipped")
        elif gainers and is_error(gainers[0]):
            print("CoinGecko unavailable; daily gainers skipped")
        elif gainers:
            record_price_snapshots(market_to_snapshot(market) for market in gainers)
            send_to_telegram(format_movers(gainers, "📈 今日涨幅榜 TOP10"), "daily_gainers")
        else:
            print("No gainers data received")

        losers = get_losers(10)
        if losers and is_rate_limited(losers[0]):
            print("CoinGecko rate limited; daily losers skipped")
        elif losers and is_error(losers[0]):
            print("CoinGecko unavailable; daily losers skipped")
        elif losers:
            record_price_snapshots(market_to_snapshot(market) for market in losers)
            send_to_telegram(format_movers(losers, "📉 今日跌幅榜 TOP10"), "daily_losers")
        else:
            print("No losers data received")

        trending = get_trending(10)
        if trending and is_rate_limited(trending[0]):
            print("CoinGecko rate limited; daily trending skipped")
        elif trending and is_error(trending[0]):
            print("CoinGecko unavailable; daily trending skipped")
        elif trending:
            send_to_telegram(format_trending(trending), "daily_trending")
        else:
            print("No trending data received")
    else:
        print("Daily rankings skipped; they are sent at Beijing 08:17")

    ping_assistant_bot()
    print("Broadcaster finished")


if __name__ == "__main__":
    main()
