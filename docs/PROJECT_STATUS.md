# Project Status - Crypto Pulse

## 最近更新时间

2026-06-22

## 当前阶段

项目处于 P0 稳定试运营后的本地升级验收阶段。Bot1 四小时内容排期、三类差异化栏目和异动雷达 dry-run 已在本地完成，尚未提交、推送或部署，生产仍使用原排期。

## Bot1 四小时内容系统（本地待部署）

- 排期：`00:17`、`04:17` 普通行情静默；`08:17` 早间市场简报；`12:17`、`16:17` 普通行情；`20:17` 晚间重点观察；周日 `20:17` 每周市场复盘。
- 08:17、20:17 均使用替代关系，每个时段只生成一个栏目，不重复生成普通行情。
- 早间简报展示全球总市值、24 小时变化、BTC 占有率、市场宽度、主流币、领涨、回撤和热门关注。
- 晚间观察以当前市场强弱、涨跌分布、BTC 占有率、BTC/ETH/SOL 和领涨回撤为主，不复制早报结构。
- 周报展示 BTC/ETH/SOL 当前价格和 7 日涨跌，过滤稳定币、包装币和重复锚定资产，不添加无可靠来源的新闻或事件。
- 三类总结均由固定数据规则生成，不推测行情原因。
- dry-run 返回完整正文和静默标记，覆盖全部栏目、周日替换、允许窗口边界和非排期小时。
- 保留内部密钥 + `ALLOW_REAL_BROADCAST` 双门控、`:10-:45` 代码时间窗、进程内时段去重、Telegram 超时 uncertain 保护和 CoinGecko 失败保护。
- 周报使用 CoinGecko `/coins/markets` 的免费 `7d` 涨跌幅参数；未新增付费数据源。
- GitHub Actions 自动 schedule 仍停用；本次未修改 Render、cron-job.org、`.env`、密钥、Bot2 或 GroupGuard。
- 当前状态：本地测试通过，待人工审查后部署。

## Bot1 异动雷达（本地待部署、禁止生产启用）

- BTC、ETH 在 1 小时涨跌达到 ±2.5% 时进入候选；其他白名单主流币阈值为 ±4%。阈值边界包含等于值。
- 同币种同方向冷却 2 小时；上涨和下跌方向分别计时。
- 全频道每个自然小时最多规划 3 条，按绝对涨跌幅从强到弱选择；重复币种行只处理一次。
- 消息只显示币种、当前 CNY 价格、1 小时涨跌和已转换的北京时间数据时间，不解释原因，不使用投资引导词。
- dry-run 默认开启，不发送且不占用冷却或小时配额。
- `RADAR_PRODUCTION_ENABLED=false` 会在数据请求前阻断真实发送；雷达未接入排期、内部接口或线上任务。
- 冷却和限流当前仅保存于进程内。现有 SQLite 表不能安全复用为发送幂等状态，因此禁止生产启用，详见 `docs/RADAR_PERSISTENCE_EVALUATION.md`。

本地验收结果：

- 全量测试：72 项通过，其中异动雷达及时间格式测试覆盖阈值、冷却、限流、重复触发、缺失数据、发送状态和 UTC/偏移时间转换。
- `python -m py_compile`：通过。
- `git diff --check`：通过。
- 固定模拟数据 dry-run：早报、晚报、周报和异动雷达均只规划 1 条对应栏目消息，未触发真实发送。

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
- 已修复同群多 Bot 场景下误回复其他 Bot 命令的问题。
- `/command@其他Bot` 会在写入用户/命令日志和执行查询之前静默忽略。
- `/command` 与 `/command@Bot2Username` 继续由 Bot2 正常处理；未知命令仍返回原有提示。
- Bot2 username 可通过 `TELEGRAM_BOT_USERNAME_2` 配置，默认值为当前生产用户名 `CryptoService2_bot`。
- 已为 GroupGuard 专属短命令增加静默忽略列表：`/gid`、`/gst`、`/grules`、`/gabout`、`/gdisc`、`/ghelp`、`/grep`。

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

Bot1 四小时内容系统已完成本地实现与测试，等待人工审查、cron 调整和部署验证。

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
