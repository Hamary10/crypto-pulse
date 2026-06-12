# Project Status - Crypto Pulse

## 最近更新时间

2026-06-12

## 当前阶段

项目处于 P0 稳定试运营阶段。Bot1 已完成连续稳定运行验证，当前结论为：P0 稳定试运营第一阶段通过。

## P0 稳定试运营第一阶段

- 稳定观察时间段：2026-06-10 18:17 至 2026-06-12 20:17。
- Bot1 连续稳定运行。
- 每 2 小时价格播报正常。
- 北京时间 08:17 的早间通知和榜单通知正常。
- 当前结论：P0 稳定试运营第一阶段通过。

下一步建议：

- 继续观察满 7 天。
- 小范围测试 Bot2 命令。
- 暂不扩展新功能。

Rejected direction：

- 当前不要大改播报逻辑。
- 当前不要新增大量功能。
- 当前不要更换 CoinGecko 数据源。

项目边界：

- Crypto Pulse 与 YouTube LoFi 完全分开。
- 不混用路径、素材、逻辑或提示词。

## 仓库状态

### 当前唯一生产仓库

`crypto-pulse`

说明：

- 当前 Bot1 和 Bot2 的正式开发、部署、维护全部在 `crypto-pulse`。
- GitHub Actions、Render、文档、数据库规划均以 `crypto-pulse` 为准。

### 历史仓库

`crypto-notification-channel`

说明：

- 属于早期版本项目。
- 已确认存在旧版 Bot1 分批播报逻辑，频道消息会显示“加密货币行情更新 (1/2)”。
- 2026-06-03 已手动禁用 GitHub Actions Workflow。
- 不再作为生产环境使用。
- 不允许在该仓库继续开发新功能。
- 保留作为历史备份参考。

### AI Agent 接手规则

每次开始工作前，必须优先确认当前仓库是否为 `crypto-pulse`。

如果发现以下内容，应先确认是否属于历史代码，不得直接修改或部署：

- `crypto-notification-channel`
- 旧版 broadcaster
- 旧版 `(1/2)` 播报逻辑

## 已完成功能

### Bot1：广播员 Bot

- 已实现每 2 小时自动播报加密货币价格，运行分钟为第 17 分，避开 GitHub Actions 整点高负载。
- 已接入 CoinGecko API。
- 已支持 Telegram 频道推送。
- 当前由 Render 内部广播接口作为主触发来源。
- GitHub Actions 自动 schedule 已停用，仅保留手动测试备用。
- 已新增每日涨幅榜 TOP10 推送。
- 已新增每日跌幅榜 TOP10 推送。
- 已新增每日热门币榜 TOP10 推送。
- 每日榜单仅在北京时间 08:17 左右的定时任务中发送。
- 已将 USDT 加入主流币价格播报。
- 已将 MATIC 替换为 POL，CoinGecko ID 使用 `polygon-ecosystem-token`。
- 已新增 USDT/CNY 参考价模块，仅显示 CNY，避免展示争议较大的 USD/MMK 汇率。
- 已新增缺失币种日志：`Missing coin data: <coin_id>`。
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
- 已修复 CoinGecko 币名包含特殊字符时 Telegram Markdown 解析失败的问题。
- 已增强 Bot1 Telegram 发送失败日志，便于定位频道 ID 或 Bot 权限问题。
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

### 运营观察报告

- 已新增本地轻量运营观察报告脚本：`generate_report.py`。
- 默认读取 `crypto_pulse.db`，也支持通过 `DATABASE_PATH` 指定数据库路径。
- 默认输出到 `reports/daily_report_YYYYMMDD.md`。
- 报告只显示统计数据，不显示 Telegram 用户 ID、用户名、first_name 或 last_name。
- `reports/`、`backups/` 和 SQLite 数据库文件已加入 `.gitignore`，默认不提交 GitHub。
- 如果本地没有 `crypto_pulse.db`，脚本会生成“未找到数据库文件”的友好报告，这不是 bug。
- 当前真实 Bot2 运营数据在 Render 运行环境里的 SQLite 数据库中，不在本地。
- Bot1 的 SQLite 数据在 GitHub Actions 临时环境中，不适合作长期运营统计。
- P0 开放测试阶段暂时不开发数据库导出功能，先通过 Render Logs 和 Telegram 群实际使用情况观察。

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
- 等出现真实用户后，再评估管理员专用 `/report`、数据库导出或免费云数据库迁移。

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

## 开放前检查清单

公开频道和群组前，开发者必须逐项确认：

1. Bot1 频道价格播报正常。
2. Bot1 涨幅榜正常。
3. Bot1 跌幅榜正常。
4. Bot1 热门榜正常。
5. Bot2 `/help` 正常。
6. Bot2 `/price` 正常。
7. Bot2 `/compare` 正常。
8. Bot2 `/top` 正常。
9. Bot2 `/trending` 正常。
10. Bot2 `/gainers` 正常。
11. Bot2 `/losers` 正常。
12. Render 日志无严重错误。
13. GitHub Actions 最近一次运行成功。
14. 测试数据已清理。
15. `stable` 分支和稳定版本 tag 已更新到最新稳定版本。
