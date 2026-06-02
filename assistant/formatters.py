from typing import Any, Dict, List


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


def format_price(symbol: str, data: Dict[str, Any]) -> str:
    change = data.get("price_change_percentage_24h", 0)
    trend = "📈" if change >= 0 else "📉"
    return (
        f"💰 **{symbol.upper()} 价格**\n\n"
        f"💵 {_fmt_usd(data.get('price_usd'))} USD\n"
        f"💴 {_fmt_cny(data.get('price_cny'))} CNY\n"
        f"{trend} 24h: {_fmt_percent(change)}\n\n"
        "数据源：CoinGecko\n"
        "仅供信息参考，非投资建议。"
    )


def format_compare(coin1: str, data1: Dict[str, Any], coin2: str, data2: Dict[str, Any]) -> str:
    price1 = data1.get("price_usd", 0) or 0
    price2 = data2.get("price_usd", 0) or 0
    ratio = price1 / price2 if price2 else 0
    return (
        f"📊 **币种对比: {coin1.upper()} vs {coin2.upper()}**\n\n"
        f"💰 **{coin1.upper()}**\n"
        f"价格: {_fmt_usd(price1)}\n"
        f"24h: {_fmt_percent(data1.get('price_change_percentage_24h'))}\n\n"
        f"💰 **{coin2.upper()}**\n"
        f"价格: {_fmt_usd(price2)}\n"
        f"24h: {_fmt_percent(data2.get('price_change_percentage_24h'))}\n\n"
        f"🔄 参考汇率: 1 {coin1.upper()} = {ratio:.4f} {coin2.upper()}\n\n"
        "数据源：CoinGecko\n"
        "仅供信息参考，非投资建议。"
    )


def format_market_cap(markets: List[Dict[str, Any]], title: str = "🏆 市值排行 TOP10") -> str:
    lines = [title, ""]
    for idx, coin in enumerate(markets, start=1):
        symbol = (coin.get("symbol") or "").upper()
        name = coin.get("name") or symbol
        price = _fmt_usd(coin.get("current_price"))
        market_cap = coin.get("market_cap")
        cap_text = f"${market_cap:,.0f}" if market_cap else "N/A"
        lines.append(f"{idx}. {name} ({symbol}) {price}")
        lines.append(f"   市值: {cap_text}")
    lines.extend(["", "数据源：CoinGecko", "仅供信息参考，非投资建议。"])
    return "\n".join(lines)


def format_movers(markets: List[Dict[str, Any]], title: str) -> str:
    lines = [title, ""]
    for idx, coin in enumerate(markets, start=1):
        symbol = (coin.get("symbol") or "").upper()
        name = coin.get("name") or symbol
        change = _fmt_percent(coin.get("price_change_percentage_24h"))
        lines.append(f"{idx}. {name} ({symbol}) {change}")
    lines.extend(["", "数据源：CoinGecko", "仅供信息参考，非投资建议。"])
    return "\n".join(lines)


def format_trending(coins: List[Dict[str, Any]]) -> str:
    lines = ["🔥 热门币榜 TOP10", ""]
    for idx, coin in enumerate(coins, start=1):
        symbol = (coin.get("symbol") or "").upper()
        name = coin.get("name") or symbol
        rank = coin.get("market_cap_rank") or "N/A"
        lines.append(f"{idx}. {name} ({symbol}) 市值排名: {rank}")
    lines.extend(["", "数据源：CoinGecko", "仅供信息参考，非投资建议。"])
    return "\n".join(lines)


def format_help() -> str:
    return (
        "🤖 **Crypto Pulse 行情助手**\n\n"
        "📋 **可用指令：**\n"
        "/price <币种> - 查询单个币种价格\n"
        "示例: /price btc\n\n"
        "/compare <币种1> <币种2> - 对比两个币种\n"
        "示例: /compare btc eth\n\n"
        "/top - 查看市值排行 TOP10\n"
        "/trending - 查看热门币榜\n"
        "/gainers - 查看 24h 涨幅榜\n"
        "/losers - 查看 24h 跌幅榜\n\n"
        "数据源：CoinGecko（带缓存）\n"
        "仅供信息参考，非投资建议。"
    )
