from datetime import datetime, timezone
from typing import Any, Dict, List

import pytz


BEIJING_TZ = pytz.timezone("Asia/Shanghai")


def _fmt_cny(value: Any) -> str:
    if value is None:
        return "N/A"
    return f"¥{float(value):,.2f}"


def _fmt_percent(value: Any) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):+.2f}%"


def _fmt_ratio_percent(value: Any) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):.2f}%"


def _fmt_usd_compact(value: Any) -> str:
    if value is None:
        return "N/A"
    value = float(value)
    if abs(value) >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:.2f}T"
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    return f"${value:,.2f}"


def _format_usdt_rates(tether_data: Dict[str, Any]) -> List[str]:
    if tether_data.get("cny") is not None:
        return [f"💱 USDT/CNY 参考价：{_fmt_cny(tether_data.get('cny'))}"]
    print("Missing USDT rate: cny")
    return []


def _current_time_text(current_time=None) -> str:
    return (current_time or datetime.now(BEIJING_TZ)).strftime("%Y-%m-%d %H:%M")


def _beijing_data_time_text(value: Any) -> str:
    if not value:
        return "N/A"
    try:
        normalized = str(value).strip()
        if normalized.endswith("Z"):
            normalized = f"{normalized[:-1]}+00:00"
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return "N/A"


def _price_change_line(symbol: str, data: Dict[str, Any]) -> str:
    return f"{symbol}: {_fmt_cny(data.get('cny'))}（24h {_fmt_percent(data.get('usd_24h_change'))}）"


def _market_lines(markets: List[Dict[str, Any]], field: str, empty_text: str) -> List[str]:
    if not markets:
        return [empty_text]
    lines = []
    for idx, market in enumerate(markets, start=1):
        symbol = (market.get("symbol") or "").upper()
        name = market.get("name") or symbol
        lines.append(f"{idx}. {name} ({symbol}) {_fmt_percent(market.get(field))}")
    return lines


def _market_breadth(markets: List[Dict[str, Any]], field: str) -> Dict[str, int]:
    values = [market.get(field) for market in markets if market.get(field) is not None]
    return {
        "up": sum(1 for value in values if float(value) > 0),
        "down": sum(1 for value in values if float(value) < 0),
        "flat": sum(1 for value in values if float(value) == 0),
        "total": len(values),
    }


def _select_movers(
    markets: List[Dict[str, Any]],
    field: str,
    limit: int = 3,
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    valid = [market for market in markets if market.get(field) is not None]
    gainers = sorted(valid, key=lambda market: float(market[field]), reverse=True)[:limit]
    losers = sorted(valid, key=lambda market: float(market[field]))[:limit]
    return gainers, losers


def _global_metrics(global_data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "total_market_cap_usd": (global_data.get("total_market_cap") or {}).get("usd"),
        "market_cap_change_24h": global_data.get("market_cap_change_percentage_24h_usd"),
        "btc_dominance": (global_data.get("market_cap_percentage") or {}).get("btc"),
    }


def _market_strength(global_change: Any, breadth: Dict[str, int]) -> str:
    if global_change is None or breadth["total"] == 0:
        return "数据不足"
    global_change = float(global_change)
    up_ratio = breadth["up"] / breadth["total"]
    down_ratio = breadth["down"] / breadth["total"]
    if global_change >= 1.5 and up_ratio >= 0.55:
        return "偏强"
    if global_change <= -1.5 and down_ratio >= 0.55:
        return "偏弱"
    return "震荡分化"


def _morning_state_sentence(global_change: Any, breadth: Dict[str, int]) -> str:
    strength = _market_strength(global_change, breadth)
    if strength == "偏强":
        return "市场状态：总市值上升且上涨币种占多数，整体数据表现偏强。"
    if strength == "偏弱":
        return "市场状态：总市值下降且下跌币种占多数，整体数据表现偏弱。"
    if strength == "震荡分化":
        return "市场状态：总市值变化与涨跌分布未形成一致方向，市场呈震荡分化。"
    return "市场状态：关键数据不足，暂不判断整体强弱。"


def _evening_summary_sentence(global_change: Any, breadth: Dict[str, int]) -> str:
    strength = _market_strength(global_change, breadth)
    if strength == "偏强":
        return "晚间总结：截至当前，上涨覆盖面较广，市场整体强度偏强。"
    if strength == "偏弱":
        return "晚间总结：截至当前，下跌覆盖面较广，市场整体强度偏弱。"
    if strength == "震荡分化":
        return "晚间总结：截至当前，币种涨跌分布分化，市场整体方向不集中。"
    return "晚间总结：关键数据不足，暂不判断整体强弱。"


def _weekly_summary_sentence(markets: List[Dict[str, Any]]) -> str:
    breadth = _market_breadth(markets, "price_change_percentage_7d_in_currency")
    if breadth["total"] == 0:
        return "周度总结：关键数据不足，暂不判断本周整体强弱。"
    if breadth["up"] / breadth["total"] >= 0.6:
        return "周度总结：近7日上涨币种占明显多数，周度市场表现偏强。"
    if breadth["down"] / breadth["total"] >= 0.6:
        return "周度总结：近7日下跌币种占明显多数，周度市场表现偏弱。"
    return "周度总结：近7日涨跌分布较为分化，未形成一致方向。"


def format_price_broadcast(
    coins: List[Dict[str, str]],
    price_data: Dict[str, Any],
    current_time=None,
) -> str:
    current_time_text = _current_time_text(current_time)
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

        display_symbol = coin.get("display_symbol") or coin["symbol"]
        lines.append(f"{display_symbol}: {_fmt_cny(data.get('cny'))}")

    lines.extend(["", f"⏰ 北京时间: {current_time_text}", "数据源：CoinGecko", "仅供信息参考，非投资建议。"])
    return "\n".join(lines)


def format_morning_brief(
    price_data: Dict[str, Any],
    markets: List[Dict[str, Any]],
    trending: List[Dict[str, Any]],
    global_data: Dict[str, Any],
    current_time=None,
) -> str:
    metrics = _global_metrics(global_data)
    breadth = _market_breadth(markets, "price_change_percentage_24h")
    gainers, losers = _select_movers(markets, "price_change_percentage_24h")
    lines = [
        "🌅 早间市场简报",
        "",
        "🌍 全球市场",
        f"总市值：{_fmt_usd_compact(metrics['total_market_cap_usd'])}",
        f"24h变化：{_fmt_percent(metrics['market_cap_change_24h'])}",
        f"BTC市场占有率：{_fmt_ratio_percent(metrics['btc_dominance'])}",
        "",
        "📊 市值前100涨跌分布",
        f"上涨 {breadth['up']}｜下跌 {breadth['down']}｜持平 {breadth['flat']}｜有效样本 {breadth['total']}",
        _morning_state_sentence(metrics["market_cap_change_24h"], breadth),
        "",
        "📍 主流币表现",
    ]
    for coin_id, symbol in (("bitcoin", "BTC"), ("ethereum", "ETH"), ("solana", "SOL")):
        if price_data.get(coin_id):
            lines.append(_price_change_line(symbol, price_data[coin_id]))

    tether = price_data.get("tether", {})
    if tether.get("cny") is not None:
        lines.append(f"USDT/CNY: {_fmt_cny(tether.get('cny'))}")

    lines.extend(["", "📈 24小时领涨"])
    lines.extend(_market_lines(gainers, "price_change_percentage_24h", "暂无可用数据"))
    lines.extend(["", "📉 24小时回撤"])
    lines.extend(_market_lines(losers, "price_change_percentage_24h", "暂无可用数据"))
    lines.extend(["", "🔥 热门关注"])
    if trending:
        for idx, coin in enumerate(trending, start=1):
            symbol = (coin.get("symbol") or "").upper()
            name = coin.get("name") or symbol
            rank = coin.get("market_cap_rank") or "N/A"
            lines.append(f"{idx}. {name} ({symbol}) 市值排名: {rank}")
    else:
        lines.append("暂无可用数据")

    lines.extend([
        "",
        f"⏰ 北京时间: {_current_time_text(current_time)}",
        "数据源：CoinGecko",
        "仅供信息参考，非投资建议。",
    ])
    return "\n".join(lines)


def format_evening_watch(
    price_data: Dict[str, Any],
    markets: List[Dict[str, Any]],
    global_data: Dict[str, Any],
    current_time=None,
) -> str:
    metrics = _global_metrics(global_data)
    breadth = _market_breadth(markets, "price_change_percentage_24h")
    gainers, losers = _select_movers(markets, "price_change_percentage_24h")
    strength = _market_strength(metrics["market_cap_change_24h"], breadth)
    lines = [
        "🌙 晚间重点观察",
        "",
        f"🧭 当前市场整体强弱：{strength}",
        f"市值前100：上涨 {breadth['up']}｜下跌 {breadth['down']}｜持平 {breadth['flat']}",
        f"BTC市场占有率：{_fmt_ratio_percent(metrics['btc_dominance'])}",
        "",
        "📍 BTC / ETH / SOL 24小时表现",
    ]
    for coin_id, symbol in (("bitcoin", "BTC"), ("ethereum", "ETH"), ("solana", "SOL")):
        if price_data.get(coin_id):
            lines.append(_price_change_line(symbol, price_data[coin_id]))

    lines.extend(["", "📈 领涨观察"])
    lines.extend(_market_lines(gainers, "price_change_percentage_24h", "暂无可用数据"))
    lines.extend(["", "📉 回撤观察"])
    lines.extend(_market_lines(losers, "price_change_percentage_24h", "暂无可用数据"))
    lines.extend([
        "",
        _evening_summary_sentence(metrics["market_cap_change_24h"], breadth),
        "观察口径：按 CoinGecko 市值前100币种的24小时涨跌幅整理。",
        f"⏰ 北京时间: {_current_time_text(current_time)}",
        "数据源：CoinGecko",
        "仅供信息参考，非投资建议。",
    ])
    return "\n".join(lines)


def format_weekly_review(
    price_data: Dict[str, Any],
    weekly_markets: List[Dict[str, Any]],
    current_time=None,
) -> str:
    weekly_by_id = {market.get("id"): market for market in weekly_markets}
    gainers, losers = _select_movers(
        weekly_markets,
        "price_change_percentage_7d_in_currency",
    )
    lines = ["🗓 每周市场复盘", "", "📍 BTC / ETH / SOL 当前价格与7日表现"]
    for coin_id, symbol in (("bitcoin", "BTC"), ("ethereum", "ETH"), ("solana", "SOL")):
        data = price_data.get(coin_id)
        if data:
            weekly_change = (weekly_by_id.get(coin_id) or {}).get(
                "price_change_percentage_7d_in_currency"
            )
            lines.append(
                f"{symbol}: {_fmt_cny(data.get('cny'))}（7d {_fmt_percent(weekly_change)}）"
            )

    field = "price_change_percentage_7d_in_currency"
    lines.extend(["", "📈 近7日领涨"])
    lines.extend(_market_lines(gainers, field, "暂无可用数据"))
    lines.extend(["", "📉 近7日回撤"])
    lines.extend(_market_lines(losers, field, "暂无可用数据"))
    lines.extend([
        "",
        _weekly_summary_sentence(weekly_markets),
        "复盘口径：按过滤稳定币及重复锚定资产后的市值前100币种近7日涨跌幅整理。",
        f"⏰ 北京时间: {_current_time_text(current_time)}",
        "数据源：CoinGecko",
        "仅供信息参考，非投资建议。",
    ])
    return "\n".join(lines)


def format_anomaly_alert(market: Dict[str, Any]) -> str:
    symbol = (market.get("symbol") or "").upper()
    change = market.get("price_change_percentage_1h_in_currency")
    data_time = _beijing_data_time_text(market.get("last_updated"))
    direction = "上涨" if float(change) > 0 else "下跌"
    lines = [
        "⚡ 市场异动雷达",
        "",
        f"币种：{symbol}",
        f"当前价格：{_fmt_cny(market.get('current_price'))}",
        f"1小时涨跌：{_fmt_percent(change)}（{direction}）",
        f"数据时间（北京时间）：{data_time}",
        "",
        "数据源：CoinGecko",
        "仅供信息参考，非投资建议。",
    ]
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
