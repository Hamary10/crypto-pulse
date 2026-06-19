"""
Crypto Pulse - 2号Bot（互动客服）
部署平台：Render (Webhook模式)
功能：处理群组指令、记录用户行为、提供 P0 行情榜单
"""

import asyncio
import hmac
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException, Request

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from broadcaster.broadcaster_bot import run_broadcast

from coingecko_client import (
    get_gainers,
    get_losers,
    get_price,
    get_prices,
    get_top_markets,
    get_trending,
    market_to_snapshot,
    is_error,
    is_rate_limited,
    symbol_to_coingecko,
)
from database import (
    increment_coin_query,
    init_database,
    log_command,
    record_price_snapshot,
    record_price_snapshots,
    upsert_user,
)
from formatters import (
    format_compare,
    format_help,
    format_market_cap,
    format_movers,
    format_price,
    format_trending,
)


BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN_2")
INTERNAL_BROADCAST_SECRET = os.getenv("INTERNAL_BROADCAST_SECRET")
PORT = int(os.getenv("PORT", 10000))
ALLOWED_GROUP_IDS_ENV = "ALLOWED_TELEGRAM_GROUP_IDS"
BOT_USERNAME_ENV = "TELEGRAM_BOT_USERNAME_2"
DEFAULT_BOT_USERNAME = "CryptoService2_bot"
GROUP_CHAT_TYPES = {"group", "supergroup"}
GROUPGUARD_SHORT_COMMANDS = {
    "/gid",
    "/gst",
    "/grules",
    "/gabout",
    "/gdisc",
    "/ghelp",
    "/grep",
}

app = FastAPI()
_broadcast_lock = asyncio.Lock()
init_database()
print("Assistant bot started; database initialized")

RATE_LIMIT_MESSAGE = "❌ CoinGecko 当前请求过于频繁，请稍后重试。"
SERVICE_ERROR_MESSAGE = "❌ 行情服务暂时不可用，请稍后重试。"
POL_COIN_ID = "polygon-ecosystem-token"
POL_DISPLAY_NAME = "POL（原 MATIC）"


def _real_broadcast_enabled() -> bool:
    return os.getenv("ALLOW_REAL_BROADCAST", "").strip().lower() == "true"


def _list_status(items: List[Dict[str, Any]]) -> Optional[str]:
    if not items:
        return None
    first = items[0]
    if is_rate_limited(first):
        return "rate_limited"
    if is_error(first):
        return "error"
    return None


def _market_error_message(items: List[Dict[str, Any]], empty_message: str) -> Optional[str]:
    status = _list_status(items)
    if status == "rate_limited":
        return RATE_LIMIT_MESSAGE
    if status == "error":
        return SERVICE_ERROR_MESSAGE
    if not items:
        return empty_message
    return None


def _user_id(user: Optional[Dict[str, Any]]) -> Optional[int]:
    return user.get("id") if user else None


def _allowed_group_ids() -> set[int]:
    raw_ids = os.getenv(ALLOWED_GROUP_IDS_ENV, "")
    allowed_ids = set()
    for raw_id in raw_ids.split(","):
        raw_id = raw_id.strip()
        if not raw_id:
            continue
        try:
            allowed_ids.add(int(raw_id))
        except ValueError:
            print(f"Ignoring invalid {ALLOWED_GROUP_IDS_ENV} entry")
    return allowed_ids


def _is_chat_allowed(chat: Dict[str, Any]) -> bool:
    if chat.get("type") not in GROUP_CHAT_TYPES:
        return True
    return chat.get("id") in _allowed_group_ids()


def _command_targets_this_bot(command_token: str) -> bool:
    _, separator, target = command_token.partition("@")
    if not separator or not target:
        return True

    bot_username = os.getenv(BOT_USERNAME_ENV, DEFAULT_BOT_USERNAME).strip().lstrip("@")
    return bool(bot_username) and target.casefold() == bot_username.casefold()


def _record_coin_query(coin_id: str, symbol: str, data: Optional[Dict[str, Any]]) -> None:
    increment_coin_query(coin_id, symbol)
    if data:
        record_price_snapshot(data)


def _display_symbol(symbol: str, coin_id: str) -> str:
    if coin_id == POL_COIN_ID:
        return POL_DISPLAY_NAME
    return symbol


async def handle_command(command: str, args: List[str], chat_id: int, user: Dict[str, Any]) -> str:
    command = command.lower()
    print(f"Handling command={command}, args={args}, chat_id={chat_id}")

    try:
        if command == "/price" and args:
            symbol = args[0]
            coin_id = symbol_to_coingecko(symbol)
            data = get_price(coin_id)
            if is_rate_limited(data):
                return RATE_LIMIT_MESSAGE
            if is_error(data):
                return SERVICE_ERROR_MESSAGE
            if not data:
                return "❌ 未找到该币种，请检查币种符号。"

            _record_coin_query(coin_id, symbol, data)
            return format_price(_display_symbol(symbol, coin_id), data)

        if command == "/compare" and len(args) >= 2:
            coin1, coin2 = args[0], args[1]
            id1 = symbol_to_coingecko(coin1)
            id2 = symbol_to_coingecko(coin2)
            prices = get_prices([id1, id2])
            if is_rate_limited(prices):
                return RATE_LIMIT_MESSAGE
            if is_error(prices):
                return SERVICE_ERROR_MESSAGE
            data1 = prices.get(id1)
            data2 = prices.get(id2)
            if not data1 or not data2:
                return "❌ 未找到其中一个币种，请检查币种符号。"

            _record_coin_query(id1, coin1, data1)
            _record_coin_query(id2, coin2, data2)
            return format_compare(coin1, data1, coin2, data2)

        if command == "/top":
            markets = get_top_markets(10)
            error_message = _market_error_message(markets, "❌ 暂时无法获取市值排行，请稍后再试。")
            if error_message:
                return error_message
            record_price_snapshots(market_to_snapshot(market) for market in markets)
            return format_market_cap(markets)

        if command == "/trending":
            coins = get_trending(10)
            error_message = _market_error_message(coins, "❌ 暂时无法获取热门币榜，请稍后再试。")
            if error_message:
                return error_message
            return format_trending(coins)

        if command == "/gainers":
            markets = get_gainers(10)
            error_message = _market_error_message(markets, "❌ 暂时无法获取涨幅榜，请稍后再试。")
            if error_message:
                return error_message
            record_price_snapshots(market_to_snapshot(market) for market in markets)
            return format_movers(markets, "📈 24小时涨幅榜 TOP10")

        if command == "/losers":
            markets = get_losers(10)
            error_message = _market_error_message(markets, "❌ 暂时无法获取跌幅榜，请稍后再试。")
            if error_message:
                return error_message
            record_price_snapshots(market_to_snapshot(market) for market in markets)
            return format_movers(markets, "📉 24小时跌幅榜 TOP10")

        if command == "/help":
            return format_help()

        return "❌ 未知命令，使用 /help 查看可用指令。"
    except Exception as exc:
        print(f"Command handling failed: {command} {exc}")
        return "❌ 当前服务繁忙，请稍后再试。"


async def send_telegram_message(chat_id: int, text: str) -> Dict[str, Any]:
    if not BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN_2 is not configured")
        return {"ok": False, "error": "missing bot token"}

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10)
            result = response.json()
            if not result.get("ok"):
                print(f"Telegram API error: {result}")
            return result
    except Exception as exc:
        print(f"Telegram send failed: {exc}")
        return {"ok": False, "error": str(exc)}


@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        message = data.get("message", {})
        chat = message.get("chat", {})
        chat_id = chat.get("id")
        text = message.get("text", "")
        user = message.get("from", {})

        if not text or not chat_id:
            return {"status": "ok"}

        if not text.startswith("/"):
            return {"status": "ok"}

        if not _is_chat_allowed(chat):
            print("Ignored command from unauthorized Telegram group")
            return {"status": "ok"}

        parts = text.split()
        command_token = parts[0]
        if not _command_targets_this_bot(command_token):
            print("Ignored command addressed to another Telegram bot")
            return {"status": "ok"}

        command = command_token.partition("@")[0]
        if "@" not in command_token and command.lower() in GROUPGUARD_SHORT_COMMANDS:
            print("Ignored GroupGuard short command")
            return {"status": "ok"}

        args = parts[1:] if len(parts) > 1 else []

        print(f"Received command={command.lower()} chat_id={chat_id}")
        upsert_user(user)
        log_command(_user_id(user), command.lower(), args)

        response_text = await handle_command(command, args, chat_id, user)
        send_result = await send_telegram_message(chat_id, response_text)
        if not send_result.get("ok"):
            print(f"Message send failed: {send_result}")

        return {"status": "ok"}
    except Exception as exc:
        print(f"Webhook failed: {exc}")
        return {"status": "error"}


@app.post("/internal/broadcast/run")
async def internal_broadcast_run(request: Request, dry_run: bool = True):
    provided_secret = request.headers.get("X-Internal-Broadcast-Secret", "")
    if not INTERNAL_BROADCAST_SECRET or not hmac.compare_digest(
        provided_secret,
        INTERNAL_BROADCAST_SECRET,
    ):
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not dry_run and not _real_broadcast_enabled():
        raise HTTPException(status_code=403, detail="Real broadcast is disabled")

    if _broadcast_lock.locked():
        raise HTTPException(status_code=409, detail="Broadcast is already running")

    async with _broadcast_lock:
        return await asyncio.to_thread(
            run_broadcast,
            send_messages=not dry_run,
            dry_run=dry_run,
            trigger_source="render_http",
        )


@app.get("/")
async def root():
    return {"status": "running", "service": "crypto-assistant-bot"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)
