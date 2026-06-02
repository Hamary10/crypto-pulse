# 货币通知频道计划 - 部署指南

## 项目概述

这是一个零成本的加密货币行情Telegram机器人系统，采用双Bot架构：
- **1号Bot（广播员）**：定时推送行情到频道（GitHub Actions）
- **2号Bot（互动客服）**：处理群组指令查询（Render免费版）

## 小白友好操作规范

项目开发者不是专业程序员。以后任何需要你手动操作的内容，都必须写成一步一步能照做的说明。

每个操作说明都必须包含：

一、我要做什么

用一句话说明目的。

二、在哪里操作

说明是在 GitHub、Render、Telegram、BotFather、Windows 终端还是浏览器里操作。

三、具体步骤

必须按 1、2、3、4 分步写清楚。

四、怎么判断成功

说明成功后会看到什么结果。

五、如果失败怎么办

列出常见错误和处理办法。

例如以后不要只说“设置环境变量 DATABASE_PATH”，而要写成：

1. 打开 Render。
2. 进入对应服务。
3. 点击 Environment。
4. 点击 Add Environment Variable。
5. Key 填 `DATABASE_PATH`。
6. Value 填 `crypto_pulse.db`。
7. 点击 Save。
8. 重新部署服务。

例如以后不要只说“手动运行 GitHub Actions”，而要写成：

1. 打开 GitHub 仓库。
2. 点击 Actions。
3. 点击 broadcaster workflow。
4. 点击 Run workflow。
5. 如果要测试每日榜单，`force_daily_rankings` 填 `1`。
6. 点击绿色 Run workflow。
7. 等待运行完成。
8. 打开 Telegram 频道检查是否收到消息。

## 每次代码修改后的部署步骤

以后每次 AI Agent 修改代码后，都必须提醒你完成下面的部署流程。

一、我要做什么

把本次代码修改提交到 GitHub，并让 Render 部署最新版本。

二、在哪里操作

Windows 终端、GitHub、Render、Telegram。

三、具体步骤

1. 打开 Windows 终端。
2. 进入项目目录：`D:\TelegramBot\货币通知频道计划`。
3. 运行测试：`python -m unittest discover -s tests`。
4. 确认测试通过。
5. 执行：`git add .`。
6. 执行：`git commit -m "本次修改说明"`。
7. 执行：`git push`。
8. 打开 GitHub 仓库。
9. 确认能看到刚刚 push 的最新提交。
10. 打开 Render。
11. 进入 `crypto-assistant-bot` 服务。
12. 查看是否自动开始部署最新提交。
13. 如果没有自动部署，点击 Manual Deploy。
14. 点击 Deploy Latest Commit。
15. 等待 Render 部署完成。
16. 打开 Telegram 群组。
17. 发送 `/help`。
18. 发送 `/price btc`。
19. 打开 Telegram 频道。
20. 如需测试频道广播，打开 GitHub Actions 手动运行 broadcaster workflow。

四、怎么判断成功

- 本地测试显示 `OK`。
- GitHub 仓库能看到最新提交。
- Render 显示部署成功，服务状态为 Live。
- Telegram 群组中 Bot 能回复 `/help` 和 `/price btc`。
- Telegram 频道能收到广播消息。

五、如果失败怎么办

- 如果测试失败，先不要 `git add`、`git commit`、`git push`，把错误内容发给 AI Agent。
- 如果 `git push` 失败，检查网络、GitHub 登录状态和仓库权限。
- 如果 GitHub 看不到最新提交，确认是否 push 到正确仓库和分支。
- 如果 Render 没有自动部署，点击 Manual Deploy，再点击 Deploy Latest Commit。
- 如果 Render 部署失败，打开 Logs，把错误内容发给 AI Agent。
- 如果 Telegram Bot 没回复，先查看 Render Logs，再检查 Webhook 和环境变量。

## 生成每日运营观察报告

一、我要做什么

生成一份本地运营观察报告，用来查看开放测试后有没有真实用户、哪些命令常用、哪些币种更受关注。

二、在哪里操作

Windows 终端，本地项目目录。

三、具体步骤

1. 打开 Windows 终端。
2. 进入项目目录：

```powershell
cd D:\TelegramBot\货币通知频道计划
```

3. 如果数据库就在项目根目录，文件名是 `crypto_pulse.db`，直接运行：

```powershell
python generate_report.py
```

4. 如果数据库在其他位置，先设置数据库路径，例如：

```powershell
$env:DATABASE_PATH="D:\TelegramBot\货币通知频道计划\crypto_pulse.db"
python generate_report.py
```

5. 打开生成的 `reports` 文件夹。
6. 打开当天报告文件，例如 `daily_report_20260602.md`。

四、怎么判断成功

- 终端显示 `运营观察报告已生成`。
- 项目目录里出现 `reports` 文件夹。
- `reports` 文件夹里出现 `daily_report_日期.md`。
- 报告里只显示统计数据，不显示 Telegram 用户 ID、用户名、first_name 或 last_name。

五、如果失败怎么办

- 如果报告提示未找到数据库文件，检查 `DATABASE_PATH` 是否正确，或者确认 `crypto_pulse.db` 是否存在。
- 如果报告提示某张表不存在，说明当前数据库还没有对应数据，先让 Bot 正常运行并产生记录。
- 如果运行命令提示找不到 Python，先确认本机是否安装 Python，并重新打开 Windows 终端。
- 如果不确定数据库在哪里，不要上传数据库到 GitHub，把当前操作截图或终端提示发给 AI Agent 判断。

### 为什么运营报告为空

一、为什么报告为空

`generate_report.py` 默认读取本地项目目录里的 `crypto_pulse.db`。如果你的电脑本地没有这个数据库文件，脚本会正常生成一份“未找到数据库文件”的友好报告。这不是 bug，说明本地没有可读取的真实运营数据。

二、数据现在在哪里

当前真实 Bot2 数据在 Render 运行环境里的 SQLite 数据库中，不在本地电脑。Bot1 数据在 GitHub Actions 临时运行环境中，每次 workflow 结束后通常不会长期保留，因此不适合作为长期运营统计来源。

三、我现在应该怎么看运营情况

P0 开放测试阶段，先通过 Render Logs 和 Telegram 群实际使用情况观察：

1. 打开 Render。
2. 进入 `crypto-assistant-bot` 服务。
3. 点击 Logs。
4. 查看是否出现 `Received command`、`SQLite command logged`、`SQLite coin query updated`。
5. 打开 Telegram 群，观察是否有真实用户使用 `/help`、`/price`、`/compare`、`/top` 等命令。

四、以后什么时候需要升级数据库方案

等小范围开放测试出现真实用户后，再考虑升级：

- 管理员专用 `/report`
- 数据库导出功能
- 迁移到免费云数据库

当前暂时不开发数据库导出功能，也不要把真实数据库或报告上传到 GitHub。

## 前置准备

### 第一步：创建两个Telegram Bot

1. 在Telegram中搜索 @BotFather
2. 发送 `/newbot` 创建第一个bot（广播员）
3. 记录Bot Token（格式：123456789:ABCdefGHIjklMNOpqrsTUVwxyz）
4. 重复步骤创建第二个bot（互动客服）
5. 记录第二个Bot Token

### 第二步：创建Telegram频道和群组

1. 在Telegram中创建一个频道（用于接收行情推送）
2. 创建一个讨论群组（用于互动查询）
3. 将频道和群组关联
4. 将两个bot都加入群组
5. 将1号Bot设为频道管理员

### 第三步：获取频道ID

1. 在Telegram中搜索 @userinfobot
2. 发送任意消息获取你的ID
3. 转发频道的任意消息到 @userinfobot
4. 记录频道ID（格式：-1001234567890 或 @channelname）

## 部署步骤

### 步骤1：创建GitHub仓库

**你需要操作：**
1. 访问 https://github.com/new
2. 创建新仓库，命名为 `crypto-notification-channel`
3. 选择Private（私有）
4. 点击创建仓库
5. 将本地上传的代码推送到GitHub

**本地操作（我帮你）：**
```bash
cd D:\TelegramBot\货币通知频道计划
git init
git add .
git commit -m "Initial commit"
git branch -M main
```

**你需要操作：**
在GitHub仓库页面点击"Upload files"，将整个文件夹上传，或者按照GitHub的指示推送本地仓库。

### 步骤2：配置GitHub Secrets

**你需要操作：**
1. 在GitHub仓库页面，点击 Settings → Secrets and variables → Actions
2. 点击 "New repository secret"
3. 添加以下Secrets：

| Secret Name | Value | 说明 |
|-------------|-------|------|
| TELEGRAM_CHANNEL_ID | 你的频道ID | 如：-1001234567890 |
| TELEGRAM_BOT_TOKEN_1 | 1号Bot Token | 广播员Token |
| ASSISTANT_WEBHOOK_URL | 2号Bot的Render网址 | 部署后填写 |

### 步骤3：启用GitHub Actions

**你需要操作：**
1. 在GitHub仓库页面，点击 Actions 标签
2. 点击 "I understand my workflows, go ahead and enable them"
3. 确认workflow已启用

### 步骤4：部署2号Bot到Render

**你需要操作：**
1. 访问 https://render.com 注册账号
2. 点击 "New +" → "Web Service"
3. 连接GitHub仓库（选择 `crypto-notification-channel`）
4. 配置：
   - Name: `crypto-assistant-bot`
   - Branch: `main`
   - Root Directory: `assistant`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python assistant_bot.py`
5. 点击 "Create Web Service"
6. 等待部署完成（约2-3分钟）
7. 记录Render分配的网址（如：https://crypto-assistant-bot.onrender.com）

### 步骤5：配置2号Bot环境变量

**你需要操作：**
1. 在Render服务页面，点击 "Environment"
2. 添加环境变量：
   - Key: `TELEGRAM_BOT_TOKEN_2`
   - Value: 2号Bot Token
3. 点击 "Save Changes"
4. 点击 "Manual Deploy" → "Clear build cache & deploy"

### 步骤6：设置Webhook

**你需要操作：**
1. 在浏览器中访问：
   ```
   https://api.telegram.org/bot<2号BotToken>/setWebhook?url=https://<你的Render网址>/webhook
   ```
2. 确认返回 `{"ok":true,"result":true,"description":"Webhook was set"}`

### 步骤7：更新GitHub Secrets

**你需要操作：**
1. 回到GitHub仓库 → Settings → Secrets
2. 更新 `ASSISTANT_WEBHOOK_URL` 为你的Render网址
3. 保存

### 步骤8：配置UptimeRobot防休眠

**你需要操作：**
1. 访问 https://uptimerobot.com 注册账号
2. 点击 "Add New Monitor"
3. 选择 "HTTP(s)"
4. 配置：
   - Monitor Type: HTTP(s)
   - URL: 你的Render网址
   - Monitoring Interval: 5 minutes
5. 点击 "Create Monitor"

## 测试验证

### 测试1号Bot（广播员）

一、我要做什么

确认 1 号 Bot 可以给 Telegram 频道发送行情播报和 P0 榜单。

二、在哪里操作

GitHub 和 Telegram。

三、具体步骤

1. 打开 GitHub 仓库。
2. 点击 Actions。
3. 点击 Crypto Broadcaster Bot workflow。
4. 点击 Run workflow。
5. 如果只测试普通价格播报，`force_daily_rankings` 保持 `0`。
6. 如果要测试每日涨幅榜、跌幅榜、热门币榜，`force_daily_rankings` 填 `1`。
7. 点击绿色 Run workflow。
8. 等待运行完成。
9. 打开 Telegram 频道查看是否收到消息。

四、怎么判断成功

- GitHub Actions 显示绿色成功。
- Telegram 频道收到行情播报。
- 如果 `force_daily_rankings` 填了 `1`，频道还会收到涨幅榜、跌幅榜、热门币榜。

五、如果失败怎么办

- 如果 GitHub Actions 失败，点开失败步骤查看日志。
- 如果提示缺少 secret，检查 GitHub Secrets。
- 如果频道没收到消息，确认 1 号 Bot 是频道管理员。

### 测试2号Bot（互动客服）

一、我要做什么

确认 2 号 Bot 可以在 Telegram 群组回复 P0 命令。

二、在哪里操作

Telegram 群组和 Render。

三、具体步骤

1. 打开 Telegram 群组。
2. 发送 `/help`。
3. 确认 Bot 回复帮助信息。
4. 发送 `/price btc`。
5. 确认 Bot 回复 BTC 价格。
6. 发送 `/compare btc eth`。
7. 确认 Bot 回复 BTC 和 ETH 对比。
8. 发送 `/top`。
9. 确认 Bot 回复市值排行。
10. 发送 `/trending`。
11. 确认 Bot 回复热门币榜。
12. 发送 `/gainers`。
13. 确认 Bot 回复涨幅榜。
14. 发送 `/losers`。
15. 确认 Bot 回复跌幅榜。
16. 打开 Render。
17. 进入 `crypto-assistant-bot` 服务。
18. 点击 Logs。
19. 查看是否出现 `Received command` 和 `SQLite command logged`。

四、怎么判断成功

- Telegram 群组每条命令都有回复。
- Render Logs 中能看到命令日志和数据库写入日志。
- 回复中包含“数据源：CoinGecko”和“非投资建议”。

五、如果失败怎么办

- 如果群组没有回复，检查 Bot2 是否在群里。
- 如果 Render 没有日志，检查 Telegram Webhook 是否设置成功。
- 如果日志提示缺少 Token，检查 Render 环境变量 `TELEGRAM_BOT_TOKEN_2`。
- 如果 CoinGecko 请求失败，稍后重试，可能是免费 API 临时限流。

### 本地最小测试

一、我要做什么

在 Windows 本地检查数据库和格式化逻辑是否正常。

二、在哪里操作

Windows 终端。

三、具体步骤

1. 打开 Windows 终端。
2. 进入项目目录：`D:\TelegramBot\货币通知频道计划`。
3. 输入 `python -m unittest discover -s tests`。
4. 等待测试运行完成。

四、怎么判断成功

终端显示测试数量和 `OK`，例如 `Ran 11 tests` 和 `OK`。

五、如果失败怎么办

- 如果提示找不到 Python，先安装 Python 或检查 Python 是否加入 PATH。
- 如果提示找不到 tests，确认当前目录是 `D:\TelegramBot\货币通知频道计划`。
- 如果测试失败，把完整错误内容发给 AI Agent。

## 常见问题

### Q: GitHub Actions没有自动运行？
A: 检查workflow是否启用，检查cron表达式是否正确，检查Secrets是否配置正确。

### Q: Render部署失败？
A: 检查requirements.txt是否正确，检查Python版本兼容性，查看Render日志。

### Q: Bot没有回复消息？
A: 检查Webhook是否设置成功，检查Bot Token是否正确，检查Bot是否在群组中。

### Q: Render服务休眠？
A: 确认UptimeRobot已配置并正常运行，确认1号Bot正在定时唤醒。

## 维护建议

1. **定期检查**：每周检查一次GitHub Actions和Render服务状态
2. **监控API限制**：CoinGecko API有速率限制，如遇问题优先降低请求频率或评估其他无地区限制的数据源，不要使用Binance API
3. **备份数据**：定期备份GitHub仓库
4. **更新依赖**：定期更新Python依赖包

## 成本总结

| 项目 | 平台 | 费用 |
|------|------|------|
| 1号Bot | GitHub Actions | $0 |
| 2号Bot | Render Free | $0 |
| 数据存储 | 无需存储 | $0 |
| 防休眠 | UptimeRobot | $0 |
| **总计** | - | **$0** |

## 联系支持

如遇问题，请检查：
1. GitHub Actions日志
2. Render服务日志
3. Telegram Bot API响应
