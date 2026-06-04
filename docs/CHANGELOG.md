# Changelog - Crypto Pulse

## 格式规范

每次开发完成后，必须按照以下格式追加记录：

```markdown
## YYYY-MM-DD

### 新增

- ...

### 修复

- ...

### 优化

- ...
```

没有内容的分类可以写“无”。

## 2026-06-04

### 新增

- 新增 Bot1 定时策略测试，覆盖 GitHub Actions cron 和每日榜单发送窗口。

### 修复

- 无

### 优化

- Bot1 GitHub Actions cron 从每小时整点改为 `17 */2 * * *`，每 2 小时第 17 分运行，避开整点高负载。
- 每日涨幅榜、跌幅榜、热门榜从北京时间 00:00 调整为北京时间 08:17 左右发送。
- 保留 `FORCE_DAILY_RANKINGS=1` 手动测试逻辑。
- 明确本次不开发异动提醒、不新增数据库去重逻辑。

## 2026-06-03

### 新增

- README 和项目状态文档新增“仓库状态”说明。
- 明确 `crypto-pulse` 是当前唯一生产仓库。
- 记录历史仓库 `crypto-notification-channel` 属于早期版本，存在旧版 Bot1 “加密货币行情更新 (1/2)” 分批播报逻辑。

### 修复

- 无

### 优化

- 明确 2026-06-03 已手动禁用 `crypto-notification-channel` 的 GitHub Actions Workflow。
- 增加 AI Agent 接手规则：每次开始工作前必须确认当前仓库是否为 `crypto-pulse`，发现旧仓库或旧版 `(1/2)` 播报逻辑时不得直接修改或部署。

## 2026-06-02

### 新增

- 文档补充运营报告数据库位置说明，明确本地报告为空不是 bug。
- 文档说明真实 Bot2 数据当前在 Render，Bot1 数据在 GitHub Actions 临时环境。

### 修复

- 无

### 优化

- 明确 P0 开放测试阶段暂不开发数据库导出功能，先通过 Render Logs 和 Telegram 群实际使用情况观察。
- 补充后续可选升级方向：管理员专用 `/report`、数据库导出、免费云数据库迁移。

## 2026-06-02

### 新增

- 新增轻量运营观察报告脚本 `generate_report.py`。
- 新增运营报告测试，覆盖数据库不存在、表不存在、统计正常和隐私字段不输出。
- README 和部署文档新增每日运营观察报告的小白友好操作说明。

### 修复

- 无

### 优化

- `.gitignore` 新增忽略 `*.db`、`*.sqlite`、`*.sqlite3`、`reports/`、`backups/`，避免真实用户数据和报告误提交到 GitHub。

## 2026-06-02

### 新增

- 开放前检查清单，覆盖 Bot1、Bot2、日志、Actions、测试数据和 stable/tag。
- 开放前测试数据清理方案，要求先备份 SQLite，再清空测试数据。

### 修复

- 无

### 优化

- Bot1 USDT 汇率模块收窄为只显示 `USDT/CNY`，不再显示 `USDT/USD` 和 `USDT/MMK`。
- Bot1 频道中的 POL 显示优化为 `POL（原 MATIC）`。

## 2026-06-02

### 新增

- 新增“代码修改后的部署提醒规范”，要求每次代码修改完成报告必须附带小白部署步骤。
- README 新增每次代码修改后的 git 提交、push、Render 部署和 Telegram 复测流程。

### 修复

- 更新 README 本地测试成功判断，避免继续写旧的 `Ran 5 tests`。

### 优化

- 强化开发完成后的部署闭环：本地测试、Git 提交、GitHub 确认、Render 部署、Telegram 复测。

## 2026-06-02

### 新增

- Bot1 主流币价格播报新增 USDT。
- Bot1 每小时价格播报新增 USDT 汇率参考模块，支持 CNY、USD、MMK。
- Bot1 对缺失币种数据增加日志：`Missing coin data: <coin_id>`。
- 新增 Bot1 格式化测试，覆盖 USDT、POL、汇率缺失和缺失币种日志。

### 修复

- 将 Bot1 主流币播报中的 MATIC 替换为 POL，CoinGecko ID 使用 `polygon-ecosystem-token`。

### 优化

- Bot1 价格播报格式改为更紧凑的频道阅读格式。
- 如果 USDT 某个汇率缺失，只跳过该项，不影响整条播报。

## 2026-06-02

### 新增

- Bot1 频道消息发送失败时，日志会打印 Telegram API 返回的错误内容，便于排查频道 ID、Bot 权限或消息格式问题。

### 修复

- 无

### 优化

- 优化 Bot1 验收阶段的故障排查信息，避免只看到 `400 Bad Request` 而不知道具体原因。

## 2026-06-02

### 新增

- 无

### 修复

- 修复 `/top` 等榜单消息因 CoinGecko 币名包含特殊字符导致 Telegram Markdown 解析失败、消息发送失败的问题。

### 优化

- Bot1 和 Bot2 发送 Telegram 消息时不再强制使用 Markdown 解析，提升行情榜单发送稳定性。

## 2026-06-02

### 新增

- CoinGecko 请求支持可选 `CG_DEMO_API_KEY` 环境变量。
- CoinGecko 请求会在配置 key 后使用 `x-cg-demo-api-key` 请求头。
- 新增 429 降级机制：优先返回过期旧缓存，无缓存时返回可识别限流状态。
- 新增网络错误降级机制：优先返回过期旧缓存，无缓存时返回可识别错误状态。
- 新增 CoinGecko 稳定性测试，覆盖 API Key header、无 key 模式、429 降级和缓存复用。

### 修复

- 修复 `/price` 遇到 429 时误提示“检查币种符号”的问题。
- 修复 `get_price()` 丢失 `rate_limited` 状态的问题。
- 修复广播端遇到 CoinGecko 限流时可能生成空榜单的问题。

### 优化

- `/compare` 批量请求成功后同步写入单币缓存，后续 `/price` 可复用。
- `/price`、`/compare`、`/top`、`/trending`、`/gainers`、`/losers` 的错误提示区分限流、币种不存在和网络错误。
- 部署文档按小白友好操作规范补充 Render 配置 `CG_DEMO_API_KEY` 的步骤。

## 2026-06-02

### 新增

- 新增小白友好操作规范，要求所有人工操作必须提供目的、操作位置、分步步骤、成功判断和失败处理。
- 在部署文档中补充 GitHub Actions、Render、查看日志和回滚操作的逐步说明。
- 在 README 中补充当前 P0 功能的手动测试步骤。

### 修复

- 修正 README 中关于 Binance API 的旧维护建议，继续遵守“不使用 Binance API”的项目限制。

### 优化

- 强化面向非专业开发者的操作说明格式，避免只给一句概括性指令。

## 2026-06-02

### 新增

- 新增本地最小测试：SQLite 初始化与写入测试、格式化测试、`/price` 与 `/compare` 命令逻辑测试。
- GitHub Actions 手动触发新增 `force_daily_rankings` 输入，用于测试每日榜单推送。
- 文档补充 Render 与 GitHub Actions 的 SQLite 持久化差异和数据库不共享影响。
- 文档补充 GitHub Actions cron 使用 UTC、每日榜单北京时间触发逻辑。
- 文档补充 P0 阶段 CoinGecko API 请求次数估算。

### 修复

- `/compare` 改为单次批量价格请求，降低 CoinGecko 请求次数。
- 修复 SQLite 连接未显式关闭的问题，避免长期运行连接泄漏。
- 修正 GitHub Actions workflow 中关于 UTC 与北京时间的说明。

### 优化

- 增加 Bot 启动、用户命令、CoinGecko 请求、SQLite 写入、频道推送和每日榜单触发日志。
- 测试不依赖真实网络请求或 Telegram API。

## 2026-06-02

### 新增

- 新增 SQLite 最小数据库基础，支持 `users`、`command_logs`、`coin_query_stats`、`price_snapshots`。
- 新增 `DATABASE_PATH` 可选环境变量，默认使用 `crypto_pulse.db`。
- Bot2 新增 `/top`、`/trending`、`/gainers`、`/losers` P0 命令。
- Bot2 新增用户记录、命令日志、币种查询统计和价格快照记录。
- Bot1 新增每日涨幅榜、每日跌幅榜、每日热门币榜频道推送。
- 新增轻量模块：`database.py`、`coingecko_client.py`、`formatters.py`。

### 修复

- 统一 CoinGecko 请求入口，减少重复请求逻辑。
- 用户可见错误信息改为友好提示，避免直接暴露 Python 报错。

### 优化

- CoinGecko 请求增加统一缓存，降低免费 API 压力。
- 每日频道榜单限制为北京时间 00:00 发送，避免每小时重复推送。
- 同步更新数据库、部署和 API 文档。

## 2026-06-02

### 新增

- 建立 AI Agent 长期协作记忆系统文档规范。
- 新增 `ROADMAP.md`，用于记录 P0-P3 未来规划。
- 新增 `DATABASE.md`，用于记录数据库结构和后续迁移设计。
- 新增 `DEPLOYMENT.md`，用于记录 GitHub Actions、Render、环境变量和 Webhook 部署流程。
- 新增 `API_REFERENCE.md`，用于记录 CoinGecko 等外部 API 使用规范。
- 新增 `DEVELOPMENT_RULES.md`，用于约束所有 AI Agent 的开发方向。

### 修复

- 补齐 `AI_CONTEXT.md` 中提到但此前缺失的 Roadmap 和 Changelog 文档。

### 优化

- 统一 `docs/` 目录作为 AI Agent 接手项目的唯一长期记忆入口。
- 明确每次开发完成后必须更新 `PROJECT_STATUS.md`、`ROADMAP.md`、`CHANGELOG.md`。
