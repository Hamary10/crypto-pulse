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


def _fmt_percent(value: Any) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):+.2f}%"


def format_price_broadcast(coins: List[Dict[str, str]], price_data: Dict[str, Any]) -> str:
    current_time = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S")
    lines = ["📊 **加密货币行情更新**", f"⏰ 时间: {current_time}", ""]

    for coin in coins:
        coin_id = coin["id"]
        data = price_data.get(coin_id)
        if not data:
            continue

        change = data.get("usd_24h_change", 0)
        trend = "📈" if change >= 0 else "📉"
        lines.extend(
            [
                f"{coin['emoji']} **{coin['symbol']}**",
                f"价格: {_fmt_usd(data.get('usd'))} USD",
                f"价格: {_fmt_cny(data.get('cny'))} CNY",
                f"{trend} 24h涨跌: {_fmt_percent(change)}",
                "",
            ]
        )

    lines.extend(["数据源：CoinGecko", "仅供信息参考，非投资建议。"])
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
