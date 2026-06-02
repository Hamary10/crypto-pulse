# API Reference - Crypto Pulse

## 用途

本文件记录 Crypto Pulse 使用的外部 API、请求限制和数据结构，避免 AI Agent 重复调研或引入不可用 API。

## 当前外部 API

### CoinGecko API

用途：

- 获取加密货币价格。
- 获取 USD、CNY 价格。
- 获取 24 小时涨跌幅。
- 后续可用于涨跌榜、热门币排行、异动提醒。

当前使用原则：

- 优先使用 CoinGecko API。
- 注意免费 API 请求限制。
- 需要缓存，避免频繁请求。
- 请求失败时必须有降级提示或错误处理。
- 支持可选 CoinGecko Demo API Key。
- 如果配置了 `CG_DEMO_API_KEY`，请求会加入 `x-cg-demo-api-key` 请求头。
- 如果未配置 `CG_DEMO_API_KEY`，继续使用无 key 模式。
- 不允许把 API Key 打印到日志。

当前使用接口：

```text
GET https://api.coingecko.com/api/v3/simple/price
```

当前参数：

| 参数 | 说明 |
|---|---|
| ids | CoinGecko 币种 ID，例如 `bitcoin` |
| vs_currencies | 计价货币，例如 `usd,cny,mmk` |
| include_24hr_change | 是否返回 24 小时涨跌幅 |

示例请求：

```text
https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd,cny&include_24hr_change=true
```

示例数据结构：

```json
{
  "bitcoin": {
    "usd": 68000,
    "cny": 492000,
    "usd_24h_change": 1.23
  }
}
```

新增 P0 榜单接口：

```text
GET https://api.coingecko.com/api/v3/coins/markets
```

用途：

- `/top` 市值排行。
- `/gainers` 24 小时涨幅榜。
- `/losers` 24 小时跌幅榜。
- 频道每日涨幅榜和跌幅榜。
- 价格快照记录。

当前参数：

| 参数 | 说明 |
|---|---|
| vs_currency | 当前使用 `usd` |
| order | 当前使用 `market_cap_desc` |
| per_page | 当前最多取 100 条后本地排序 |
| page | 当前使用第 1 页 |
| sparkline | 当前使用 `false` |
| price_change_percentage | 当前使用 `24h` |

新增热门币接口：

```text
GET https://api.coingecko.com/api/v3/search/trending
```

用途：

- `/trending` 热门币榜。
- 频道每日热门币榜。

当前常用 CoinGecko ID：

| 符号 | CoinGecko ID |
|---|---|
| BTC | bitcoin |
| ETH | ethereum |
| BNB | binancecoin |
| SOL | solana |
| ADA | cardano |
| XRP | ripple |
| DOGE | dogecoin |
| DOT | polkadot |
| POL | polygon-ecosystem-token |
| USDT | tether |

Bot1 USDT 汇率模块：

- 使用 `tether` 请求 `usd,cny,mmk`。
- `USDT/CNY`、`USDT/USD`、`USDT/MMK` 只显示 CoinGecko 实际返回的项目。
- 如果 `mmk` 或其他汇率缺失，不会导致整条频道播报失败。
- 缺失项会打印日志，例如 `Missing USDT rate: mmk`。

## 请求限制

CoinGecko 免费 API 有请求频率限制，实际限制可能随政策变化。

开发要求：

- 必须使用缓存。
- 批量请求优先于逐个请求。
- 定时任务应避免过高频率。
- API 失败不能导致 Bot 崩溃。
- 新增行情功能前必须评估请求量。
- P0 版本使用内存缓存，默认缓存时间为 10 分钟。

## P0 请求次数估算

Bot1 广播员：

- 每小时价格播报：1 次 `/simple/price` 批量请求。
- 北京时间 00:00 每日榜单额外请求：1 次 `/coins/markets`，1 次 `/search/trending`。
- 每日榜单中的涨幅榜和跌幅榜共享同一次 `/coins/markets` 缓存。
- 所以普通小时约 1 次 CoinGecko 请求，每日榜单小时约 3 次请求。

Bot2 客服 Bot 冷缓存请求量：

- `/price <coin>`：1 次 `/simple/price`。
- `/compare <coin1> <coin2>`：1 次批量 `/simple/price`。
- `/top`：1 次 `/coins/markets`。
- `/gainers`：1 次 `/coins/markets`。
- `/losers`：1 次 `/coins/markets`。
- `/trending`：1 次 `/search/trending`。

缓存说明：

- 10 分钟内存缓存对 Bot1 和 Bot2 的所有 CoinGecko 请求模块生效。
- Bot1 每次 GitHub Actions 运行都是新进程，缓存只在单次运行内有效。
- Bot2 在 Render 进程存活期间缓存有效，重启后缓存清空。
- `/top`、`/gainers`、`/losers` 在同一进程 10 分钟内共享 `/coins/markets` 缓存。
- `/compare` 批量请求成功后，会同时写入单币缓存，因此后续 `/price btc` 可复用缓存。

429 降级机制：

- 请求前先查有效缓存。
- 有效缓存存在时直接返回，不请求 CoinGecko。
- 缓存过期后才请求 CoinGecko。
- 请求成功后更新缓存。
- CoinGecko 返回 429 时，优先返回过期旧缓存。
- 429 且没有旧缓存时，返回可识别的 `rate_limited` 状态。
- 其他网络错误时，优先返回过期旧缓存。
- 其他网络错误且没有旧缓存时，返回可识别的 `error` 状态。
- 用户侧不会把 429 误提示为“币种符号错误”。

限流风险：

- 当前 P0 请求量较低，正常使用下触发 CoinGecko 免费 API 限流的风险较低。
- 如果群组公开后短时间大量用户频繁使用命令，仍可能触发限流。
- 后续如用户量增加，应考虑更长缓存、请求队列或共享缓存。

## 禁止或不推荐 API

### Binance API

状态：当前不可用。

原因：

- 存在地区限制。

规则：

- 不要新增依赖 Binance API 的功能。
- 不要把 Binance API 作为主要数据源。

## 未来可能新增 API

未来可评估：

- 新闻 API：用于新闻摘要。
- 社交热度 API：用于热门币或热门讨论。
- 其他无地区限制的行情 API：作为 CoinGecko 备用数据源。

新增 API 前必须记录：

- API 名称。
- 用途。
- 请求地址。
- 鉴权方式。
- 免费额度。
- 请求限制。
- 数据结构。
- 失败处理方式。

## API 更新规则

新增、替换或删除任何外部 API 后，必须同步更新：

- `API_REFERENCE.md`
- `PROJECT_STATUS.md`
- `ROADMAP.md`
- `CHANGELOG.md`
