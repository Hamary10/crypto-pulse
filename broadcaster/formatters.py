from datetime import datetime
from typing import Any, Dict, List

import pytz


BEIJING_TZ = pytz.timezone("Asia/Shanghai")


def _fmt_usd(value: Any) -> str:
    if value is None:
        return "N/A"
    return f"${float(value):,.2f}"


def _fmt_cny(value: Any) -> str:
    if value is None:
        return "N/A"
    return f"¥{float(value):,.2f}"


def _fmt_mmk(value: Any) -> str:
    if value is None:
        return "N/A"
    return f"Ks {float(value):,.0f}"


def _fmt_percent(value: Any) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):+.2f}%"


def _format_usdt_rates(tether_data: Dict[str, Any]) -> List[str]:
    lines = ["💱 USDT 汇率参考"]
    if tether_data.get("cny") is not None:
        lines.append(f"USDT/CNY: {_fmt_cny(tether_data.get('cny'))}")
    else:
        print("Missing USDT rate: cny")

    if tether_data.get("usd") is not None:
        lines.append(f"USDT/USD: ${float(tether_data.get('usd')):,.4f}")
    else:
        print("Missing USDT rate: usd")

    if tether_data.get("mmk") is not None:
        lines.append(f"USDT/MMK: {_fmt_mmk(tether_data.get('mmk'))}")
    else:
        print("Missing USDT rate: mmk")

    return lines


def format_price_broadcast(coins: List[Dict[str, str]], price_data: Dict[str, Any]) -> str:
    current_time = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d %H:%M")
    lines = ["📊 加密货币行情更新", ""]

    tether_data = price_data.get("tether", {})
    if tether_data:
        lines.extend(_format_usdt_rates(tether_data))
        lines.append("")
    else:
        print("Missing coin data: tether")

    lines.append("💰 主流币价格")

    for coin in coins:
        coin_id = coin["id"]
        data = price_data.get(coin_id)
        if not data:
            print(f"Missing coin data: {coin_id}")
            continue

        lines.append(f"{coin['symbol']}: {_fmt_cny(data.get('cny'))}")

    lines.extend(["", f"⏰ 北京时间: {current_time}", "数据源：CoinGecko", "仅供信息参考，非投资建议。"])
    return "\n".join(lines)


def format_movers(markets: List[Dict[str, Any]], title: str) -> str:
    lines = [title, ""]
    for idx, coin in enumerate(markets, start=1):
        symbol = (coin.get("symbol") or "").upper()
        name = coin.get("name") or symbol
        lines.append(f"{idx}. {name} ({symbol}) {_fmt_percent(coin.get('price_change_percentage_24h'))}")
    lines.extend(["", "数据源：CoinGecko", "仅供信息参考，非投资建议。"])
    return "\n".join(lines)


def format_trending(coins: List[Dict[str, Any]]) -> str:
    lines = ["🔥 今日热门币榜 TOP10", ""]
    for idx, coin in enumerate(coins, start=1):
        symbol = (coin.get("symbol") or "").upper()
        name = coin.get("name") or symbol
        rank = coin.get("market_cap_rank") or "N/A"
        lines.append(f"{idx}. {name} ({symbol}) 市值排名: {rank}")
    lines.extend(["", "数据源：CoinGecko", "仅供信息参考，非投资建议。"])
    return "\n".join(lines)
