"""
Crypto Pulse - 1号Bot（广播员）
部署入口：Render 内部广播接口；GitHub Actions 仅保留手动备用
功能：按四小时栏目排期获取行情并推送 Telegram 频道
"""

import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pytz
import requests

try:
    from .coingecko_client import (
        get_gainers,
        get_global_market_data,
        get_hourly_markets,
        get_losers,
        get_markets,
        get_prices,
        get_trending,
        get_weekly_movers,
        is_error,
        is_rate_limited,
        market_to_snapshot,
        simple_price_to_snapshot,
    )
    from .database import init_database, record_price_snapshots
    from .formatters import (
        format_evening_watch,
        format_anomaly_alert,
        format_morning_brief,
        format_movers,
        format_price_broadcast,
        format_trending,
        format_weekly_review,
    )
except ImportError:
    from coingecko_client import (
        get_gainers,
        get_global_market_data,
        get_hourly_markets,
        get_losers,
        get_markets,
        get_prices,
        get_trending,
        get_weekly_movers,
        is_error,
        is_rate_limited,
        market_to_snapshot,
        simple_price_to_snapshot,
    )
    from database import init_database, record_price_snapshots
    from formatters import (
        format_evening_watch,
        format_anomaly_alert,
        format_morning_brief,
        format_movers,
        format_price_broadcast,
        format_trending,
        format_weekly_review,
    )


CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN_1")
ASSISTANT_WEBHOOK_URL = os.getenv("ASSISTANT_WEBHOOK_URL")
FORCE_DAILY_RANKINGS = os.getenv("FORCE_DAILY_RANKINGS", "0") == "1"
BEIJING_TZ = pytz.timezone("Asia/Shanghai")
ALLOWED_WINDOW = "scheduled hours 00/04/08/12/16/20, minute 10-45 Asia/Shanghai"

CONTENT_PRICE = "price_broadcast"
CONTENT_MORNING = "morning_market_brief"
CONTENT_EVENING = "evening_market_watch"
CONTENT_WEEKLY = "weekly_market_review"
SCHEDULED_CONTENT = {
    0: CONTENT_PRICE,
    4: CONTENT_PRICE,
    8: CONTENT_MORNING,
    12: CONTENT_PRICE,
    16: CONTENT_PRICE,
    20: CONTENT_EVENING,
}
SILENT_HOURS = {0, 4}

RADAR_CORE_THRESHOLDS = {"bitcoin": 2.5, "ethereum": 2.5}
RADAR_DEFAULT_THRESHOLD = 4.0
RADAR_COOLDOWN = timedelta(hours=2)
RADAR_HOURLY_LIMIT = 3
# Local-only safety lock. No endpoint or scheduler invokes the radar.
RADAR_PRODUCTION_ENABLED = False

EXCLUDED_WEEKLY_ASSET_IDS = {
    "tether",
    "usd-coin",
    "dai",
    "first-digital-usd",
    "ethena-usde",
    "paypal-usd",
    "usds",
    "true-usd",
    "usdd",
    "frax",
    "wrapped-bitcoin",
    "weth",
    "staked-ether",
    "wrapped-steth",
    "coinbase-wrapped-staked-eth",
    "rocket-pool-eth",
    "wrapped-eeth",
    "ether-fi-staked-eth",
    "marinade-staked-sol",
    "jito-staked-sol",
    "binance-staked-sol",
}
EXCLUDED_WEEKLY_SYMBOLS = {
    "USDT", "USDC", "DAI", "FDUSD", "USDE", "PYUSD", "USDS", "TUSD",
    "USDD", "FRAX", "WBTC", "WETH", "STETH", "WSTETH", "CBETH", "RETH",
    "WEETH", "EETH", "MSOL", "JITOSOL", "BNSOL",
}

# P0 protection only: this state is lost whenever the Render process restarts.
_delivery_states: Dict[str, str] = {}
_radar_cooldowns: Dict[str, datetime] = {}
_radar_hour_counts: Dict[str, int] = {}

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

RADAR_WHITELIST = {
    coin["id"]: coin["symbol"] for coin in COINS if coin["id"] != "tether"
}


def send_to_telegram(message: str, label: str, silent: bool = False):
    if not BOT_TOKEN or not CHANNEL_ID:
        print("Telegram channel id or bot token is not configured")
        return False

    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHANNEL_ID,
            "text": message,
            "disable_web_page_preview": True,
            "disable_notification": silent,
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
    """Legacy manual-ranking predicate retained for compatibility and history."""
    now = now or datetime.now(BEIJING_TZ)
    return FORCE_DAILY_RANKINGS or now.hour in (8, 9)


def generate_legacy_daily_ranking_messages() -> List[Dict[str, str]]:
    """Keep the former three-message ranking logic available, but off the new schedule."""
    messages: List[Dict[str, str]] = []
    gainers = get_gainers(10)
    if gainers and not is_rate_limited(gainers[0]) and not is_error(gainers[0]):
        messages.append({
            "label": "daily_gainers",
            "text": format_movers(gainers, "📈 今日涨幅榜 TOP10"),
        })

    losers = get_losers(10)
    if losers and not is_rate_limited(losers[0]) and not is_error(losers[0]):
        messages.append({
            "label": "daily_losers",
            "text": format_movers(losers, "📉 今日跌幅榜 TOP10"),
        })

    trending = get_trending(10)
    if trending and not is_rate_limited(trending[0]) and not is_error(trending[0]):
        messages.append({"label": "daily_trending", "text": format_trending(trending)})
    return messages


def scheduled_content_for(now) -> Optional[str]:
    content_type = SCHEDULED_CONTENT.get(now.hour)
    if content_type == CONTENT_EVENING and now.weekday() == 6:
        return CONTENT_WEEKLY
    return content_type


def get_broadcast_context(now=None) -> dict:
    now = now or datetime.now(BEIJING_TZ)
    date = now.strftime("%Y-%m-%d")
    content_type = scheduled_content_for(now)
    slot = f"{content_type}:{date}:{now.hour:02d}" if content_type else None
    return {
        "now": now,
        "current_time_local": now.isoformat(),
        "allowed_window": ALLOWED_WINDOW,
        "content_type": content_type,
        "silent": content_type == CONTENT_PRICE and now.hour in SILENT_HOURS,
        "within_allowed_window": content_type is not None and 10 <= now.minute <= 45,
        "slot": slot,
        "slots": {content_type: slot} if content_type else {},
    }


def _delivery_key(slot: str, label: str) -> str:
    return f"{slot}|{label}"


def _send_status(message: str, label: str, silent: bool) -> str:
    status = send_to_telegram(message, label, silent=silent)
    if status == "uncertain":
        return "uncertain"
    return "sent" if status else "failed"


def _safe_market_list(
    items: List[Dict[str, Any]],
    description: str,
    result: Dict[str, Any],
) -> List[Dict[str, Any]]:
    if items and is_rate_limited(items[0]):
        print(f"CoinGecko rate limited; {description} unavailable")
        result["skipped"].append(f"{description}: rate_limited")
        return []
    if items and is_error(items[0]):
        print(f"CoinGecko unavailable; {description} unavailable")
        result["skipped"].append(f"{description}: unavailable")
        return []
    return items or []


def _safe_global_data(data: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    if is_rate_limited(data):
        result["skipped"].append("global_market: rate_limited")
        return {}
    if is_error(data):
        result["skipped"].append("global_market: unavailable")
        return {}
    return data or {}


def _market_movers(
    markets: List[Dict[str, Any]],
    field: str,
    limit: int = 3,
) -> List[Dict[str, Any]]:
    valid = [market for market in markets if market.get(field) is not None]
    gainers = sorted(valid, key=lambda market: float(market[field]), reverse=True)[:limit]
    losers = sorted(valid, key=lambda market: float(market[field]))[:limit]
    return gainers + losers


def _filter_weekly_reference_markets(
    markets: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    filtered = []
    for market in markets:
        coin_id = (market.get("id") or "").lower()
        symbol = (market.get("symbol") or "").upper()
        if coin_id in EXCLUDED_WEEKLY_ASSET_IDS or symbol in EXCLUDED_WEEKLY_SYMBOLS:
            continue
        if market.get("price_change_percentage_7d_in_currency") is None:
            continue
        filtered.append(market)
    return filtered


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
        "content_type": context["content_type"],
        "silent": context["silent"],
        "slot": context["slot"],
        "slots": context["slots"],
        "message_labels": [],
        "messages": [],
        "planned_count": 0,
        "sent_count": 0,
        "duplicate_skipped": [],
        "skipped": [],
        "uncertain": [],
        "errors": [],
    }

    if context["content_type"] is None:
        result["skipped"].append("no_scheduled_content")
        print("Broadcast skipped; no content is scheduled for this hour")
        return result

    if should_send and not context["within_allowed_window"]:
        result["skipped"].append("outside_allowed_window")
        print("Real broadcast skipped; outside allowed window")
        return result

    if not dry_run:
        init_database()

    def plan_message(message: str, label: str, silent: bool = False) -> None:
        result["message_labels"].append(label)
        result["messages"].append({"label": label, "text": message, "silent": silent})
        result["planned_count"] += 1
        if should_send:
            slot = context["slot"]
            key = _delivery_key(slot, label)
            state = _delivery_states.get(key)
            if state == "sent":
                result["duplicate_skipped"].append({"slot": slot, "message_label": label})
                return
            if state == "uncertain":
                result["uncertain"].append({"slot": slot, "message_label": label})
                return

            status = _send_status(message, label, silent)
            if status == "sent":
                _delivery_states[key] = "sent"
                result["sent_count"] += 1
            elif status == "uncertain":
                _delivery_states[key] = "uncertain"
                result["uncertain"].append({"slot": slot, "message_label": label})
            else:
                result["errors"].append(f"Failed to send {label}")

    content_type = context["content_type"]
    coin_ids = [coin["id"] for coin in COINS]
    price_data = get_prices(coin_ids)
    if is_rate_limited(price_data):
        print("CoinGecko rate limited; price broadcast skipped")
        result["skipped"].append(f"{content_type}: rate_limited")
    elif is_error(price_data):
        print("CoinGecko unavailable; price broadcast skipped")
        result["skipped"].append(f"{content_type}: unavailable")
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
        if content_type == CONTENT_PRICE:
            plan_message(
                format_price_broadcast(COINS, price_data, current_time=context["now"]),
                CONTENT_PRICE,
                silent=context["silent"],
            )
        elif content_type == CONTENT_MORNING:
            markets = _safe_market_list(get_markets(100), "morning markets", result)
            trending = _safe_market_list(get_trending(3), "morning trending", result)
            global_data = _safe_global_data(get_global_market_data(), result)
            plan_message(
                format_morning_brief(
                    price_data,
                    markets,
                    trending,
                    global_data,
                    current_time=context["now"],
                ),
                CONTENT_MORNING,
            )
            if not dry_run:
                record_price_snapshots(
                    market_to_snapshot(market)
                    for market in _market_movers(markets, "price_change_percentage_24h")
                )
        elif content_type == CONTENT_EVENING:
            markets = _safe_market_list(get_markets(100), "evening markets", result)
            global_data = _safe_global_data(get_global_market_data(), result)
            plan_message(
                format_evening_watch(
                    price_data,
                    markets,
                    global_data,
                    current_time=context["now"],
                ),
                CONTENT_EVENING,
            )
            if not dry_run:
                record_price_snapshots(
                    market_to_snapshot(market)
                    for market in _market_movers(markets, "price_change_percentage_24h")
                )
        elif content_type == CONTENT_WEEKLY:
            weekly_markets = _safe_market_list(
                get_markets(100, "7d"),
                "weekly markets",
                result,
            )
            weekly_markets = _filter_weekly_reference_markets(weekly_markets)
            if weekly_markets:
                plan_message(
                    format_weekly_review(
                        price_data,
                        weekly_markets,
                        current_time=context["now"],
                    ),
                    CONTENT_WEEKLY,
                )
            else:
                result["skipped"].append(f"{CONTENT_WEEKLY}: no_weekly_data")
    else:
        print("No price data received")
        result["skipped"].append(f"{content_type}: no_data")

    if should_send:
        ping_assistant_bot()
    result["success"] = not result["errors"] and not result["uncertain"]
    print("Broadcaster finished")
    return result


def _radar_direction(change: float) -> str:
    return "up" if change > 0 else "down"


def _radar_cooldown_key(coin_id: str, direction: str) -> str:
    return f"{coin_id}:{direction}"


def run_anomaly_radar(
    send_messages: bool = False,
    dry_run: bool = True,
    trigger_source: str = "local",
    current_time=None,
) -> Dict[str, Any]:
    now = current_time or datetime.now(BEIJING_TZ)
    should_send = send_messages and not dry_run
    hour_slot = now.strftime("%Y-%m-%d:%H")
    result: Dict[str, Any] = {
        "success": True,
        "dry_run": dry_run,
        "trigger_source": trigger_source,
        "production_enabled": RADAR_PRODUCTION_ENABLED,
        "production_blocked": False,
        "current_time_local": now.isoformat(),
        "hour_slot": hour_slot,
        "messages": [],
        "candidate_count": 0,
        "planned_count": 0,
        "sent_count": 0,
        "cooldown_skipped": [],
        "hourly_limit_skipped": [],
        "data_skipped": [],
        "uncertain": [],
        "errors": [],
        "skipped": [],
    }

    if should_send and not RADAR_PRODUCTION_ENABLED:
        result["production_blocked"] = True
        result["skipped"].append("radar_real_send_disabled")
        return result

    markets = get_hourly_markets(list(RADAR_WHITELIST))
    if markets and is_rate_limited(markets[0]):
        result["skipped"].append("hourly_markets: rate_limited")
        return result
    if markets and is_error(markets[0]):
        result["skipped"].append("hourly_markets: unavailable")
        return result

    seen_coin_ids = set()
    candidates: List[Dict[str, Any]] = []
    for market in markets:
        coin_id = market.get("id")
        if coin_id not in RADAR_WHITELIST or coin_id in seen_coin_ids:
            continue
        seen_coin_ids.add(coin_id)

        change = market.get("price_change_percentage_1h_in_currency")
        current_price = market.get("current_price")
        data_time = market.get("last_updated")
        if change is None or current_price is None or not data_time:
            result["data_skipped"].append({"coin_id": coin_id, "reason": "missing_data"})
            continue

        change = float(change)
        threshold = RADAR_CORE_THRESHOLDS.get(coin_id, RADAR_DEFAULT_THRESHOLD)
        if abs(change) < threshold:
            continue

        direction = _radar_direction(change)
        cooldown_key = _radar_cooldown_key(coin_id, direction)
        last_delivery = _radar_cooldowns.get(cooldown_key)
        if last_delivery is not None and now - last_delivery < RADAR_COOLDOWN:
            result["cooldown_skipped"].append({
                "coin_id": coin_id,
                "direction": direction,
                "last_delivery": last_delivery.isoformat(),
            })
            continue

        item = dict(market)
        item["symbol"] = RADAR_WHITELIST[coin_id]
        item["threshold"] = threshold
        item["direction"] = direction
        item["cooldown_key"] = cooldown_key
        candidates.append(item)

    candidates.sort(
        key=lambda market: abs(float(market["price_change_percentage_1h_in_currency"])),
        reverse=True,
    )
    result["candidate_count"] = len(candidates)
    remaining = max(0, RADAR_HOURLY_LIMIT - _radar_hour_counts.get(hour_slot, 0))
    selected = candidates[:remaining]
    for market in candidates[remaining:]:
        result["hourly_limit_skipped"].append({
            "coin_id": market["id"],
            "direction": market["direction"],
        })

    for market in selected:
        message = format_anomaly_alert(market)
        label = f"anomaly_radar_{market['symbol'].lower()}_{market['direction']}"
        result["messages"].append({
            "label": label,
            "text": message,
            "coin_id": market["id"],
            "direction": market["direction"],
            "threshold": market["threshold"],
        })
        result["planned_count"] += 1

        if should_send:
            status = _send_status(message, label, silent=False)
            if status == "sent":
                result["sent_count"] += 1
            elif status == "uncertain":
                result["uncertain"].append({
                    "coin_id": market["id"],
                    "direction": market["direction"],
                })
            else:
                result["errors"].append(f"Failed to send {label}")
                continue

            _radar_cooldowns[market["cooldown_key"]] = now
            _radar_hour_counts[hour_slot] = _radar_hour_counts.get(hour_slot, 0) + 1

    result["success"] = not result["errors"] and not result["uncertain"]
    return result


def main() -> None:
    run_broadcast(send_messages=True, dry_run=False, trigger_source="script")


if __name__ == "__main__":
    main()
