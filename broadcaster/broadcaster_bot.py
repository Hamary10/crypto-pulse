"""
Crypto Pulse - 1号Bot（广播员）
部署平台：GitHub Actions
功能：定时获取行情并推送 Telegram 频道，附带 P0 基础榜单内容
"""

import os
from datetime import datetime
from typing import Dict

import pytz
import requests

try:
    from .coingecko_client import (
        get_gainers,
        get_losers,
        get_prices,
        get_trending,
        is_error,
        is_rate_limited,
        market_to_snapshot,
        simple_price_to_snapshot,
    )
    from .database import init_database, record_price_snapshots
    from .formatters import format_movers, format_price_broadcast, format_trending
except ImportError:
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
ALLOWED_WINDOW = "even hours, minute 10-45 Asia/Shanghai"

# P0 protection only: this state is lost whenever the Render process restarts.
_delivery_states: Dict[str, str] = {}

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


def send_to_telegram(message: str, label: str):
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
    except requests.Timeout as exc:
        print(f"Telegram send uncertain ({label}): {exc}")
        return "uncertain"
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


def should_send_daily_rankings(now=None) -> bool:
    now = now or datetime.now(BEIJING_TZ)
    return FORCE_DAILY_RANKINGS or now.hour in (8, 9)


def get_broadcast_context(now=None) -> dict:
    now = now or datetime.now(BEIJING_TZ)
    price_hour = now.hour if now.hour % 2 == 0 else now.hour - 1
    date = now.strftime("%Y-%m-%d")
    return {
        "now": now,
        "current_time_local": now.isoformat(),
        "allowed_window": ALLOWED_WINDOW,
        "within_allowed_window": now.hour % 2 == 0 and 10 <= now.minute <= 45,
        "slots": {
            "price_broadcast": f"price:{date}:{price_hour:02d}",
            "daily_gainers": f"daily_gainers:{date}",
            "daily_losers": f"daily_losers:{date}",
            "daily_trending": f"daily_trending:{date}",
        },
    }


def _delivery_key(slot: str, label: str) -> str:
    return f"{slot}|{label}"


def _send_status(message: str, label: str) -> str:
    status = send_to_telegram(message, label)
    if status == "uncertain":
        return "uncertain"
    return "sent" if status else "failed"


def run_broadcast(
    send_messages: bool = True,
    dry_run: bool = False,
    trigger_source: str = "manual",
    current_time=None,
) -> dict:
    print("Broadcaster started")
    should_send = send_messages and not dry_run
    context = get_broadcast_context(current_time)
    result = {
        "success": True,
        "dry_run": dry_run,
        "trigger_source": trigger_source,
        "current_time_local": context["current_time_local"],
        "allowed_window": context["allowed_window"],
        "slot": context["slots"]["price_broadcast"],
        "slots": context["slots"],
        "message_labels": [],
        "planned_count": 0,
        "sent_count": 0,
        "duplicate_skipped": [],
        "skipped": [],
        "uncertain": [],
        "errors": [],
    }

    if should_send and not context["within_allowed_window"]:
        result["skipped"].append("outside_allowed_window")
        print("Real broadcast skipped; outside allowed window")
        return result

    if not dry_run:
        init_database()

    def plan_message(message: str, label: str) -> None:
        result["message_labels"].append(label)
        result["planned_count"] += 1
        if should_send:
            slot = context["slots"][label]
            key = _delivery_key(slot, label)
            state = _delivery_states.get(key)
            if state == "sent":
                result["duplicate_skipped"].append({"slot": slot, "message_label": label})
                return
            if state == "uncertain":
                result["uncertain"].append({"slot": slot, "message_label": label})
                return

            status = _send_status(message, label)
            if status == "sent":
                _delivery_states[key] = "sent"
                result["sent_count"] += 1
            elif status == "uncertain":
                _delivery_states[key] = "uncertain"
                result["uncertain"].append({"slot": slot, "message_label": label})
            else:
                result["errors"].append(f"Failed to send {label}")

    coin_ids = [coin["id"] for coin in COINS]
    price_data = get_prices(coin_ids)
    if is_rate_limited(price_data):
        print("CoinGecko rate limited; price broadcast skipped")
        result["skipped"].append("price_broadcast: rate_limited")
    elif is_error(price_data):
        print("CoinGecko unavailable; price broadcast skipped")
        result["skipped"].append("price_broadcast: unavailable")
    elif price_data:
        missing_coin_ids = [coin["id"] for coin in COINS if coin["id"] not in price_data]
        for coin_id in missing_coin_ids:
            print(f"Missing coin data: {coin_id}")

        if not dry_run:
            snapshots = [
                simple_price_to_snapshot(coin["id"], coin["symbol"], price_data[coin["id"]])
                for coin in COINS
                if coin["id"] in price_data
            ]
            record_price_snapshots(snapshots)
        plan_message(format_price_broadcast(COINS, price_data), "price_broadcast")
    else:
        print("No price data received")
        result["skipped"].append("price_broadcast: no_data")

    if should_send_daily_rankings(context["now"]):
        gainers = get_gainers(10)
        if gainers and is_rate_limited(gainers[0]):
            print("CoinGecko rate limited; daily gainers skipped")
            result["skipped"].append("daily_gainers: rate_limited")
        elif gainers and is_error(gainers[0]):
            print("CoinGecko unavailable; daily gainers skipped")
            result["skipped"].append("daily_gainers: unavailable")
        elif gainers:
            if not dry_run:
                record_price_snapshots(market_to_snapshot(market) for market in gainers)
            plan_message(format_movers(gainers, "📈 今日涨幅榜 TOP10"), "daily_gainers")
        else:
            print("No gainers data received")
            result["skipped"].append("daily_gainers: no_data")

        losers = get_losers(10)
        if losers and is_rate_limited(losers[0]):
            print("CoinGecko rate limited; daily losers skipped")
            result["skipped"].append("daily_losers: rate_limited")
        elif losers and is_error(losers[0]):
            print("CoinGecko unavailable; daily losers skipped")
            result["skipped"].append("daily_losers: unavailable")
        elif losers:
            if not dry_run:
                record_price_snapshots(market_to_snapshot(market) for market in losers)
            plan_message(format_movers(losers, "📉 今日跌幅榜 TOP10"), "daily_losers")
        else:
            print("No losers data received")
            result["skipped"].append("daily_losers: no_data")

        trending = get_trending(10)
        if trending and is_rate_limited(trending[0]):
            print("CoinGecko rate limited; daily trending skipped")
            result["skipped"].append("daily_trending: rate_limited")
        elif trending and is_error(trending[0]):
            print("CoinGecko unavailable; daily trending skipped")
            result["skipped"].append("daily_trending: unavailable")
        elif trending:
            plan_message(format_trending(trending), "daily_trending")
        else:
            print("No trending data received")
            result["skipped"].append("daily_trending: no_data")
    else:
        print("Daily rankings skipped; allowed window is Beijing 08:00-09:59")
        result["skipped"].append("daily_rankings: outside_schedule")

    if should_send:
        ping_assistant_bot()
    result["success"] = not result["errors"] and not result["uncertain"]
    print("Broadcaster finished")
    return result


def main() -> None:
    run_broadcast(send_messages=True, dry_run=False, trigger_source="script")


if __name__ == "__main__":
    main()
