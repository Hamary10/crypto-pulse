# Project Status - Crypto Pulse

## 最近更新时间

2026-06-02

## 当前阶段

项目处于 P0 精简版验收完成阶段：MVP 已可运行，已补齐用户行为记录、基础数据库、P0 行情榜单、频道自动化内容和最小本地测试。

## 已完成功能

### Bot1：广播员 Bot

- 已实现每小时自动播报加密货币价格。
- 已接入 CoinGecko API。
- 已支持 Telegram 频道推送。
- 已部署到 GitHub Actions。
- 已配置 GitHub Actions 定时运行。
- 已新增每日涨幅榜 TOP10 推送。
- 已新增每日跌幅榜 TOP10 推送。
- 已新增每日热门币榜 TOP10 推送。
- 每日榜单仅在北京时间 00:00 的定时任务中发送。
- 已记录价格快照到 SQLite。
- 已通过本地语法检查和最小测试。
- 当前状态：运行中。

### Bot2：客服 Bot

- 已实现 `/price` 命令。
- 已实现 `/compare` 命令。
- 已实现 `/help` 命令。
- 已新增 `/top` 命令：市值排行 TOP10。
- 已新增 `/trending` 命令：CoinGecko 热门币榜。
- 已新增 `/gainers` 命令：24 小时涨幅榜。
- 已新增 `/losers` 命令：24 小时跌幅榜。
- 已接入统一 CoinGecko API 模块。
- 已实现请求缓存，减少 CoinGecko 请求频率。
- 已支持 `CG_DEMO_API_KEY`，可通过 `x-cg-demo-api-key` 请求头访问 CoinGecko。
- 已增加 429 降级机制：优先返回旧缓存，无缓存时返回友好限流提示。
- 已优化 `/price` 和 `/compare` 的缓存复用。
- 已记录用户基础信息到 SQLite。
- 已记录命令使用日志到 SQLite。
- 已记录币种查询统计到 SQLite。
- 已记录价格快照到 SQLite。
- 已通过本地语法检查和最小测试。
- 已新增 CoinGecko 稳定性测试，覆盖 API Key、429 旧缓存、限流状态和缓存复用。
- 已部署到 Render。
- 已使用 FastAPI Webhook 模式。
- 当前状态：运行中。

### SQLite 数据库

- 已新增最小数据库基础。
- 默认数据库路径：`crypto_pulse.db`。
- 可通过 `DATABASE_PATH` 环境变量覆盖。
- 已支持 `users`、`command_logs`、`coin_query_stats`、`price_snapshots` 四张 P0 表。

### 频道

- Telegram 频道已创建。
- 当前未公开运营。
- 当前用于接收自动行情播报、每日涨跌榜和每日热门币榜。

### 群组

- Telegram 群组已创建。
- 当前未公开运营。
- 当前用于 Bot 命令查询和后续用户互动。

## 正在开发功能

当前 P0 精简版已完成验收与稳定性测试，暂无正在进行的新功能。

## 待开发功能

### P0 后续

- 异动提醒基础版本。
- 自动欢迎系统。
- 更完善的错误处理和结构化日志。

### P1 以后

- 用户活跃统计展示。
- 活跃用户排行榜。
- 群互动话题或每日投票。
- 基础运营数据统计。

## 线上部署情况

### GitHub Actions

- 用途：运行 Bot1 广播员 Bot。
- 触发方式：定时任务。
- 当前状态：运行中。
- 部署形态未改变。

### Render

- 用途：运行 Bot2 客服 Bot。
- 服务类型：Web Service。
- 运行方式：FastAPI + Webhook。
- 当前状态：运行中。
- 部署形态未改变。

### UptimeRobot

- 用途：防止 Render 免费服务休眠。
- 当前状态：已配置。

## 已知限制

- 默认 SQLite 文件在免费部署环境中可能不是长期持久化存储。
- GitHub Actions 中生成的 SQLite 文件是临时运行产物。
- Render 免费实例重启或重新部署时，本地 SQLite 文件可能丢失。
- Bot1 和 Bot2 当前部署在不同平台，默认不会共享 SQLite 数据库。
- P0 精简版先满足最小行为记录和功能验证，未来如需要持久化运营数据，再评估免费数据库或 PostgreSQL 迁移。

## 验收结果

- SQLite 初始化测试通过。
- 数据库写入测试通过。
- `/price` 命令逻辑测试通过。
- `/compare` 命令逻辑测试通过，并已合并为单次批量价格请求。
- `/top`、`/trending`、`/gainers`、`/losers` 格式化测试通过。
- CoinGecko Demo API Key header 测试通过。
- CoinGecko 429 降级测试通过。
- `/compare` 后 `/price` 缓存复用测试通过。
- 429 用户提示测试通过，不再误判为币种不存在。
- Python 语法检查通过。

## 每次开发完成后必须更新

- `docs/PROJECT_STATUS.md`
- `docs/ROADMAP.md`
- `docs/CHANGELOG.md`
