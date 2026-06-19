# Deployment - Crypto Pulse

## 用途

本文件记录 Crypto Pulse 的部署方式、环境变量、Webhook 配置和部署流程。

## 部署架构

当前采用双 Bot 架构：

- Bot1 广播员 Bot：由 Render 内部接口触发；GitHub Actions 仅保留手动备用。
- Bot2 客服 Bot：Render Web Service 常驻运行，使用 FastAPI Webhook。

## GitHub Actions

用途：

- 仅通过 `workflow_dispatch` 手动运行 Bot1 作为备用。
- 自动 `schedule` 已停用。

时间说明：

- GitHub Actions cron 使用 UTC 时间，不使用北京时间。
- 原 `cron: '17 */2 * * *'` 已停用，仅保留注释参考。
- 北京时间为 UTC+8，因此北京时间 08:17 对应 UTC 00:17。
- 当前代码使用 `Asia/Shanghai` 判断本地时间，每日榜单在北京时间 08:00-08:29 的运行窗口发送，正常约为 08:17。
- `FORCE_DAILY_RANKINGS=1` 可用于手动测试每日榜单。

配置文件：

- `.github/workflows/broadcaster.yml`

运行目录：

- `broadcaster/`

主要命令：

```bash
pip install -r requirements.txt
python broadcaster_bot.py
```

需要的 GitHub Secrets：

| 变量 | 说明 |
|---|---|
| TELEGRAM_CHANNEL_ID | Telegram 频道 ID |
| TELEGRAM_BOT_TOKEN_1 | Bot1 广播员 Token |
| ASSISTANT_WEBHOOK_URL | Bot2 Render 服务地址 |
| CG_DEMO_API_KEY | 可选，CoinGecko Demo API Key |

可选环境变量：

| 变量 | 说明 |
|---|---|
| DATABASE_PATH | SQLite 数据库路径，默认 `crypto_pulse.db` |
| FORCE_DAILY_RANKINGS | 设置为 `1` 时强制发送每日榜单，主要用于手动测试 |

说明：

- GitHub Actions 默认每 2 小时运行一次价格播报。
- 每日涨幅榜、跌幅榜、热门币榜只在北京时间 08:17 左右发送一次。
- GitHub Actions 中生成的 SQLite 文件是临时运行产物，不作为长期持久化数据。
- Bot1 默认数据库不与 Render 上的 Bot2 共享。

## Render

用途：

- 运行 Bot2 客服 Bot。
- 接收 Telegram Webhook 请求。
- 响应群组命令。
- 通过受保护的内部接口触发 Bot1 广播。

### Render 内部广播 P0 防重复

- 内部接口由服务端按 `Asia/Shanghai` 自行计算 time slot，不信任外部调用方传入的 slot。
- 价格播报每两个小时一个 slot，例如 `price:2026-06-10:14`。
- 每日榜单每个标签每天一个 slot，例如 `daily_gainers:2026-06-10`。
- 真实发送仅允许在偶数小时的 `:10-:45`；dry-run 不受此窗口限制。
- dry-run 不发送、不占用 slot。只有 Telegram 明确成功后才标记 `sent`。
- Telegram 超时会标记为 `uncertain`，同一进程内不会自动重试该标签。
- P0 状态只保存在单个 Render 进程内存中。Render 休眠、重启或重新部署后状态会丢失，不能替代持久化幂等存储。

运行目录：

- `assistant/`

服务类型：

- Web Service

主要命令：

```bash
pip install -r requirements.txt
python assistant_bot.py
```

需要的环境变量：

| 变量 | 说明 |
|---|---|
| TELEGRAM_BOT_TOKEN_2 | Bot2 客服 Bot Token |
| PORT | Render 自动分配端口，代码默认 10000 |
| DATABASE_PATH | 可选，SQLite 数据库路径，默认 `crypto_pulse.db` |
| CG_DEMO_API_KEY | 可选，CoinGecko Demo API Key，用于降低 429 限流风险 |
| ALLOWED_TELEGRAM_GROUP_IDS | Bot2 允许响应的 Telegram 群 Chat ID；多个群使用英文逗号分隔 |

说明：

- `ALLOWED_TELEGRAM_GROUP_IDS` 未配置时，Bot2 会静默忽略所有群组和超级群组命令，私聊维持原有行为。
- 不要把真实群 Chat ID 写入代码、GitHub 文档或测试；真实值只保存在 Render Environment。
- Bot2 command target 判断使用 username `CryptoService2_bot`，不使用群内显示名 `Crypto Service`。
- `TELEGRAM_BOT_USERNAME_2` 是可选覆盖项；当前 username 未变时不需要新增。

持久化说明：

- Render 免费实例上的本地 SQLite 文件不应视为稳定长期存储。
- 服务重启、重新部署或实例迁移时，本地 SQLite 文件可能丢失。
- Bot2 默认数据库不与 GitHub Actions 上的 Bot1 共享。

### 配置 Bot2 允许群列表

一、我要做什么

只允许指定的 Crypto Pulse Telegram 群使用 Bot2 命令。

二、在哪里操作

Render 控制台。

三、具体步骤

1. 打开 Render。
2. 进入 `crypto-assistant-bot` 服务。
3. 点击 Environment。
4. 点击 Add Environment Variable。
5. Key 填 `ALLOWED_TELEGRAM_GROUP_IDS`。
6. Value 填真实 Crypto Pulse 群 Chat ID，例如 `<真实 Crypto Pulse 群 Chat ID>`。
7. 如果以后允许多个群，使用英文逗号分隔多个 Chat ID。
8. 点击 Save。
9. 等待 Render 自动重新部署，或在代码 push 后等待最新 commit 自动部署。
10. 部署完成后，在允许群测试 `/help` 和 `/price BTC`。

四、怎么判断成功

- 允许群中的 Bot2 命令正常回复。
- 其他群中的 Bot2 命令被静默忽略。
- Render Logs 不会显示未允许群的正常命令处理和查询日志。

五、如果失败怎么办

- 如果允许群没有回复，检查 Chat ID 是否包含负号，以及超级群 ID 是否以 `-100` 开头。
- 如果配置多个群，确认使用英文逗号，且没有输入中文逗号。
- 如果 Render 尚未使用最新代码，打开 Deploys 确认最新 commit 已部署成功。
- 不要把真实群 ID 提交到 GitHub；需要排查时只提供脱敏值。

### 配置 CoinGecko Demo API Key

一、我要做什么

给 Render 上的 Bot2 配置 CoinGecko Demo API Key，降低 `/price btc` 等命令遇到 429 限流的概率。

二、在哪里操作

Render 控制台。

三、具体步骤

1. 打开 Render。
2. 进入 `crypto-assistant-bot` 服务。
3. 点击 Environment。
4. 点击 Add Environment Variable。
5. Key 填 `CG_DEMO_API_KEY`。
6. Value 填你的 CoinGecko Demo API Key。
7. 点击 Save。
8. 点击 Manual Deploy。
9. 重新部署服务。
10. 部署完成后，回到 Telegram 群组。
11. 重新测试 `/price btc`。

四、怎么判断成功

- Render 服务重新部署成功并显示 Live。
- Telegram 群组发送 `/price btc` 后能收到价格回复。
- Render Logs 中不会打印 API Key。
- 如果 CoinGecko 短时限流，有缓存时会优先返回旧缓存；没有缓存时会提示请求过于频繁。

五、如果失败怎么办

- 如果找不到 Environment，确认你进入的是 `crypto-assistant-bot` Web Service。
- 如果部署失败，打开 Logs 查看错误。
- 如果 `/price btc` 仍提示请求过于频繁，等待几分钟后再试。
- 如果仍然失败，确认 `CG_DEMO_API_KEY` 是否填写正确，且没有多余空格。

## Webhook

Bot2 使用 Telegram Webhook 模式。

Webhook 地址格式：

```text
https://<render-service-url>/webhook
```

Telegram 设置 Webhook 的请求格式：

```text
https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN_2>/setWebhook?url=https://<render-service-url>/webhook
```

成功返回应包含：

```json
{
  "ok": true,
  "result": true
}
```

## 健康检查

Bot2 根路径用于健康检查：

```text
GET /
```

预期返回：

```json
{
  "status": "running",
  "service": "crypto-assistant-bot"
}
```

## UptimeRobot

用途：

- 定期访问 Render 服务，减少免费服务休眠影响。

建议配置：

- 类型：HTTP(s)。
- URL：Render 服务根地址。
- 间隔：5 分钟。

## 部署流程

## 小白友好操作规范

以后所有需要开发者手动执行的部署、测试、配置、查看日志、回滚和故障排查操作，都必须按以下格式说明：

1. 一、我要做什么：一句话说明目的。
2. 二、在哪里操作：说明平台，例如 GitHub、Render、Telegram、Windows 终端。
3. 三、具体步骤：按 1、2、3、4 写清楚。
4. 四、怎么判断成功：说明成功后会看到什么。
5. 五、如果失败怎么办：列出常见错误和处理办法。

### Bot1 部署流程

一、我要做什么

部署并验证 Bot1 广播员，确认 Telegram 频道能收到自动行情消息。

二、在哪里操作

GitHub 仓库和 Telegram 频道。

三、具体步骤

1. 打开 GitHub 仓库。
2. 点击 Settings。
3. 点击 Secrets and variables。
4. 点击 Actions。
5. 确认已经配置 `TELEGRAM_CHANNEL_ID`、`TELEGRAM_BOT_TOKEN_1`、`ASSISTANT_WEBHOOK_URL`。
6. 点击仓库顶部的 Actions。
7. 点击 Crypto Broadcaster Bot workflow。
8. 点击 Run workflow。
9. 如果只是测试普通价格播报，`force_daily_rankings` 保持 `0`。
10. 如果要测试每日涨跌榜和热门榜，`force_daily_rankings` 填 `1`。
11. 点击绿色 Run workflow。
12. 等待 workflow 运行完成。
13. 打开 Telegram 频道查看是否收到消息。

四、怎么判断成功

- GitHub Actions 显示绿色成功。
- Telegram 频道收到行情播报。
- 如果 `force_daily_rankings` 填了 `1`，频道还会收到涨幅榜、跌幅榜和热门币榜。

五、如果失败怎么办

- 如果 Actions 显示红色失败，点击失败的运行记录，再点击失败步骤查看日志。
- 如果日志提示缺少 `TELEGRAM_CHANNEL_ID`，回到 GitHub Secrets 检查频道 ID。
- 如果日志提示 Telegram 发送失败，检查 Bot1 是否是频道管理员。
- 如果没有榜单消息，确认手动运行时 `force_daily_rankings` 填的是 `1`。

### Bot2 部署流程

一、我要做什么

部署并验证 Bot2 客服 Bot，确认 Telegram 群组命令可以正常回复。

二、在哪里操作

Render、Telegram、浏览器。

三、具体步骤

1. 打开 Render。
2. 进入 `crypto-assistant-bot` 服务。
3. 点击 Environment。
4. 确认已经配置 `TELEGRAM_BOT_TOKEN_2`。
5. 如需配置数据库路径，点击 Add Environment Variable。
6. Key 填 `DATABASE_PATH`。
7. Value 填 `crypto_pulse.db`，或填写你想使用的 SQLite 路径。
8. 点击 Save。
9. 点击 Manual Deploy。
10. 点击 Clear build cache & deploy。
11. 等待部署完成。
12. 复制 Render 服务网址，例如 `https://crypto-assistant-bot.onrender.com`。
13. 在浏览器打开 Telegram setWebhook 地址：`https://api.telegram.org/bot<2号BotToken>/setWebhook?url=https://<Render网址>/webhook`。
14. 打开 Telegram 群组。
15. 发送 `/help`。
16. 发送 `/price btc`。

四、怎么判断成功

- Render 部署状态显示 Live。
- setWebhook 页面返回 `ok: true`。
- Telegram 群组收到 `/help` 和 `/price btc` 的回复。
- Render Logs 中能看到 `Assistant bot started`、`Received command`、`SQLite command logged`。

五、如果失败怎么办

- 如果 Render 部署失败，打开 Logs 查看错误。
- 如果 setWebhook 返回失败，检查 Bot Token 和 Render 网址是否正确。
- 如果群里没有回复，确认 Bot2 已加入群组。
- 如果日志提示缺少 `TELEGRAM_BOT_TOKEN_2`，回到 Environment 重新添加环境变量。
- 如果数据库日志异常，先删除自定义 `DATABASE_PATH`，使用默认 `crypto_pulse.db` 再试。

### 查看 GitHub Actions 日志

一、我要做什么

查看 Bot1 广播员为什么成功或失败。

二、在哪里操作

GitHub 仓库的 Actions 页面。

三、具体步骤

1. 打开 GitHub 仓库。
2. 点击 Actions。
3. 点击 Crypto Broadcaster Bot workflow。
4. 点击最近一次运行记录。
5. 点击 broadcast 任务。
6. 展开失败或需要查看的步骤。
7. 阅读日志内容。

四、怎么判断成功

- 看到 `Broadcaster started` 表示 Bot1 已启动。
- 看到 `Sent channel message` 表示频道消息发送成功。
- 看到绿色对勾表示 workflow 成功完成。

五、如果失败怎么办

- 如果看见 Telegram 发送失败，检查 Bot Token、频道 ID、Bot 管理员权限。
- 如果看见 CoinGecko 请求失败，稍后重试，可能是 API 临时不可用或限流。
- 如果看见缺少 secret，回到 Settings 配置 GitHub Secrets。

### 查看 Render 日志

一、我要做什么

查看 Bot2 客服 Bot 是否正常运行和响应命令。

二、在哪里操作

Render 控制台。

三、具体步骤

1. 打开 Render。
2. 点击 `crypto-assistant-bot` 服务。
3. 点击 Logs。
4. 在 Telegram 群组发送 `/help`。
5. 回到 Logs 页面查看新日志。

四、怎么判断成功

- 看到 `Assistant bot started` 表示服务已启动。
- 看到 `Received command` 表示收到了 Telegram 命令。
- 看到 `SQLite command logged` 表示命令已写入数据库。

五、如果失败怎么办

- 如果没有新日志，检查 Webhook 是否设置正确。
- 如果日志中有 Token 相关错误，检查 `TELEGRAM_BOT_TOKEN_2`。
- 如果 Telegram 无回复，确认 Bot 在群组里，并且 Render 服务是 Live。

### 回滚操作

一、我要做什么

如果新版本出现问题，临时回到上一个可用版本。

二、在哪里操作

GitHub 和 Render。

三、具体步骤

1. 打开 GitHub 仓库。
2. 找到上一个确认可用的提交或备份版本。
3. 恢复对应文件，或让 AI Agent 根据该版本生成回滚补丁。
4. 提交并推送到 GitHub。
5. 打开 Render。
6. 进入 `crypto-assistant-bot` 服务。
7. 点击 Manual Deploy。
8. 选择最新提交重新部署。
9. 打开 GitHub Actions 手动运行 Bot1 验证。

四、怎么判断成功

- Render 重新部署成功。
- Telegram 群组命令恢复回复。
- GitHub Actions 运行成功。
- Telegram 频道恢复收到消息。

五、如果失败怎么办

- 如果不确定回滚哪个文件，先停止继续修改，并把 Render/GitHub Actions 错误日志发给 AI Agent。
- 如果 Render 无法部署，先检查最近一次改动是否涉及依赖或环境变量。
- 如果频道仍不发消息，检查 GitHub Secrets 和频道管理员权限。

## 开放前清理测试数据

### 当前数据库文件判断

当前本地仓库没有发现 SQLite `.db` 文件。线上环境按部署平台分别判断：

- Bot2 在 Render 运行，默认数据库文件为 `assistant/crypto_pulse.db` 或环境变量 `DATABASE_PATH` 指向的路径。
- Bot1 在 GitHub Actions 运行，默认数据库文件为 `broadcaster/crypto_pulse.db`，每次 workflow 结束后通常不会长期保留。
- Bot1 和 Bot2 当前默认不共享数据库。

当前实际创建的 SQLite 表：

- `users`
- `command_logs`
- `coin_query_stats`
- `price_snapshots`

说明：`channel_posts` 目前没有在代码中创建。如果未来新增该表，开放前清理时再加入清理列表。

### 清理方案

一、我要做什么

开放前清除测试期间产生的用户、命令、币种查询和价格快照数据，但保留代码、文档、环境变量和数据库表结构。

二、在哪里操作

Render Shell、Windows 终端或能访问 SQLite 数据库文件的服务器终端。

三、具体步骤

1. 先确认数据库文件路径。默认是 `crypto_pulse.db`，如果配置了 `DATABASE_PATH`，以 `DATABASE_PATH` 为准。
2. 先备份数据库文件，不要直接删除原文件。
3. 执行清理命令，只清空表数据，不删除表结构。
4. 清理后检查表是否还存在。
5. 清理后检查每张表的数据量是否为 0。

本地 Windows PowerShell 示例：

```powershell
Copy-Item crypto_pulse.db crypto_pulse.backup-before-open.db
python -c "import sqlite3; db='crypto_pulse.db'; conn=sqlite3.connect(db); cur=conn.cursor(); [cur.execute(f'DELETE FROM {table}') for table in ['users','command_logs','coin_query_stats','price_snapshots']]; conn.commit(); conn.close()"
python -c "import sqlite3; db='crypto_pulse.db'; conn=sqlite3.connect(db); cur=conn.cursor(); print(cur.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()); print({t: cur.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in ['users','command_logs','coin_query_stats','price_snapshots']}); conn.close()"
```

如果未来新增 `channel_posts` 表，清理命令中的表名列表增加 `channel_posts`。

四、怎么判断成功

- 备份文件存在，例如 `crypto_pulse.backup-before-open.db`。
- `users`、`command_logs`、`coin_query_stats`、`price_snapshots` 表仍然存在。
- 每张表的数量都是 0。
- Bot 启动后不会报数据库表不存在。

五、如果失败怎么办

- 如果提示找不到 `crypto_pulse.db`，先检查 `DATABASE_PATH` 是否配置了其他路径。
- 如果提示某张表不存在，说明当前数据库不是最新结构，先启动 Bot 让它自动初始化数据库。
- 如果清理后 Bot 报错，先停止继续操作，用备份文件恢复原数据库。
- 如果不确定线上 Render 是否能直接操作数据库，不要强行清理，把 Render 日志和 `DATABASE_PATH` 配置发给 AI Agent 判断。

## 生成每日运营观察报告

一、我要做什么

生成每日运营观察报告，用来查看总用户数、今日新增用户、今日活跃用户、命令使用和币种关注情况。

二、在哪里操作

Windows 终端，本地项目目录。

三、具体步骤

1. 打开 Windows 终端。
2. 进入项目目录：

```powershell
cd D:\TelegramBot\货币通知频道计划
```

3. 确认数据库文件在本地。默认文件名是 `crypto_pulse.db`。
4. 如果数据库文件就在项目根目录，运行：

```powershell
python generate_report.py
```

5. 如果数据库文件不在项目根目录，先设置数据库路径：

```powershell
$env:DATABASE_PATH="你的数据库文件完整路径"
python generate_report.py
```

6. 打开项目里的 `reports` 文件夹。
7. 打开当天报告，例如 `daily_report_20260602.md`。

四、怎么判断成功

- 终端显示 `运营观察报告已生成`。
- 看到 `reports/daily_report_日期.md` 文件。
- 报告能看到总用户数、今日新增用户数、今日活跃用户数、今日命令调用总数、最常用命令 TOP10、最常查询币种 TOP10。
- 报告不会显示 Telegram 用户 ID、用户名、first_name 或 last_name。

五、如果失败怎么办

- 如果提示未找到数据库文件，检查 `DATABASE_PATH` 或 `crypto_pulse.db` 是否存在。
- 如果提示某张表不存在，说明当前数据库没有初始化或还没有对应功能数据。
- 如果报告里某个指标显示暂无法统计，先确认对应表是否已经存在。
- 如果生成了报告，不要把 `reports` 文件夹上传到 GitHub。
- 如果需要分析线上 Render 数据，先确认如何安全取得数据库备份，不要把真实用户数据库提交到 GitHub。

### 运营报告数据库位置说明

一、为什么报告为空

`generate_report.py` 默认读取运行命令所在目录的本地 `crypto_pulse.db`。如果本地没有数据库文件，报告会显示“未找到数据库文件”。这是正常保护逻辑，不是程序错误。

二、数据现在在哪里

- Bot2 的真实用户、命令和币种查询数据目前在 Render 运行环境里的 SQLite 数据库中。
- Bot1 在 GitHub Actions 中生成的 SQLite 数据属于临时运行产物，不适合作长期统计。
- 本地电脑只有在手动取得数据库备份后，才会有可供 `generate_report.py` 统计的数据。
- Render 免费环境的本地 SQLite 不适合长期稳定保存，服务重启、重新部署或实例迁移时可能丢失。

三、我现在应该怎么看运营情况

P0 开放测试阶段先不开发数据库导出功能，先按下面方式观察：

1. 打开 Render。
2. 进入 `crypto-assistant-bot` 服务。
3. 点击 Logs。
4. 观察是否有 `Received command`。
5. 观察是否有 `SQLite command logged`。
6. 观察是否有 `SQLite coin query updated`。
7. 打开 Telegram 群，查看是否有真实用户使用命令。

四、以后什么时候需要升级数据库方案

当出现真实用户并且需要每日稳定统计时，再考虑：

- 管理员专用 `/report`
- 数据库导出功能
- 迁移到免费云数据库

五、如果失败怎么办

- 如果本地报告为空，先确认本地是否真的有 `crypto_pulse.db`。
- 如果 Render Logs 有命令记录但本地报告为空，说明数据在 Render，不在本地。
- 如果需要正式统计，不要把 Render 数据库提交到 GitHub，先设计安全导出或迁移方案。

## 部署注意事项

- 不要提交 Telegram Bot Token。
- 不要把密钥写入代码。
- 不要增加非必要付费服务。
- 不要依赖 Binance API。
- SQLite 默认用于 P0 最小行为记录，Render 免费实例重启或重新部署后可能丢失本地数据库文件。
- 修改部署方式后必须同步更新本文件。
