# Database - Crypto Pulse

## 用途

本文件记录 Crypto Pulse 的数据库结构设计、字段说明和索引说明。

当前 P0 精简版使用 SQLite。默认数据库路径为 `crypto_pulse.db`，可通过 `DATABASE_PATH` 环境变量覆盖。

## 当前状态

- 已接入 SQLite 最小数据库。
- Bot2 会记录用户基础信息、命令日志、币种查询统计和价格快照。
- Bot1 会记录价格快照。
- 暂不上 PostgreSQL。

## 部署限制

- Render 免费实例的本地 SQLite 文件可能在重启或重新部署后丢失。
- GitHub Actions 中的 SQLite 文件是单次运行产物，不作为长期存储。
- Bot2 运行在 Render，默认使用 Render 实例本地的 SQLite 文件。
- Bot1 运行在 GitHub Actions，默认使用每次 workflow 运行时生成的 SQLite 文件。
- 因为 Bot1 和 Bot2 部署在不同平台，默认数据库不共享。
- 当前数据库用于 P0 行为记录和功能验证，后续如需要长期数据留存，再评估迁移方案。

## 数据库共享影响

当前 P0 阶段可以接受数据库不共享，原因：

- Bot2 的用户记录、命令日志、币种查询统计只服务于客服 Bot 自身命令统计。
- Bot1 的价格快照只用于频道推送运行日志和未来异动提醒准备。
- 当前没有任何功能要求 Bot1 读取 Bot2 的用户行为数据。
- 当前没有任何功能要求 Bot2 读取 Bot1 的频道推送记录。

未来如果开发以下功能，数据库不共享会产生影响：

- 跨 Bot 的统一运营后台。
- 基于频道推送和群组命令的综合数据分析。
- 用户活跃统计与频道内容效果关联。
- 异动提醒需要长期历史价格快照。
- PostgreSQL 或其他共享数据库迁移。

## 表结构

### users

用途：记录 Telegram 用户基础信息。

| 字段 | 类型 | 说明 |
|---|---|---|
| telegram_id | INTEGER | Telegram 用户 ID，主键 |
| username | TEXT | Telegram 用户名 |
| first_name | TEXT | 名 |
| last_name | TEXT | 姓 |
| first_seen_at | TEXT | 首次出现时间 |
| last_seen_at | TEXT | 最近活跃时间 |

索引：

- `telegram_id` 主键索引。

### command_logs

用途：记录用户命令使用。

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER | 主键，自增 |
| telegram_id | INTEGER | Telegram 用户 ID |
| command | TEXT | 命令名称 |
| args | TEXT | 命令参数 |
| created_at | TEXT | 创建时间 |

索引：

- `idx_command_logs_telegram_id`：用于按用户查询命令记录。
- `idx_command_logs_command`：用于统计命令使用情况。
- `idx_command_logs_created_at`：用于按时间统计。

### coin_query_stats

用途：记录币种查询次数。

| 字段 | 类型 | 说明 |
|---|---|---|
| coin_id | TEXT | CoinGecko 币种 ID，主键 |
| symbol | TEXT | 币种符号 |
| query_count | INTEGER | 查询次数 |
| last_queried_at | TEXT | 最近查询时间 |

索引：

- `coin_id` 主键索引。

### price_snapshots

用途：记录价格快照，用于未来异动提醒。

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER | 主键，自增 |
| coin_id | TEXT | CoinGecko 币种 ID |
| symbol | TEXT | 币种符号 |
| price_cny | REAL | CNY 价格 |
| price_usd | REAL | USD 价格 |
| market_cap | REAL | 市值 |
| volume_24h | REAL | 24 小时成交量 |
| price_change_percentage_24h | REAL | 24 小时涨跌幅 |
| created_at | TEXT | 创建时间 |

索引：

- `idx_price_snapshots_coin_id`：用于按币种查询。
- `idx_price_snapshots_created_at`：用于按时间查询。

## 未来扩展表

当前不做以下表：

- 积分表。
- 等级表。
- 勋章表。
- 竞猜表。
- 邀请表。

未来可按 Roadmap 再评估：

- `alerts`：异动或价格提醒。
- `channel_posts`：频道内容发布记录。

## 数据库更新规则

每次新增或修改数据库结构后，必须同步更新：

- `docs/DATABASE.md`
- `docs/PROJECT_STATUS.md`
- `docs/ROADMAP.md`
- `docs/CHANGELOG.md`
