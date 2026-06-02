# Development Rules - Crypto Pulse

## 用途

本文件是所有 AI Agent 和开发者必须遵守的开发规则。

目标是避免：

- AI 上下文丢失。
- 重复解释项目。
- 重复设计功能。
- 开发方向偏移。
- 忽略文档更新。

## 接手项目必读顺序

任何 AI Agent 接手项目时，必须先阅读：

1. `docs/AI_CONTEXT.md`
2. `docs/PROJECT_STATUS.md`
3. `docs/ROADMAP.md`
4. `docs/DEVELOPMENT_RULES.md`
5. 根据任务需要阅读其他 docs 文件。

## 核心开发规则

### 1. 优先用户增长，不是优先开发复杂功能

开发应服务于真实用户增长。

优先考虑：

- 公开运营前必要功能。
- 用户能理解和愿意使用的功能。
- 能提升留存和转发的功能。

避免：

- 技术复杂但用户价值不清晰的功能。
- 长期无人使用的内部系统。

### 2. 优先社区活跃，不是优先增加查询命令

项目目标是社区生态，不是命令大全。

优先考虑：

- 群互动。
- 用户活跃统计。
- 排行榜。
- 每日话题或投票。
- 自动欢迎和引导。

避免：

- 大量类似 `/price` 的重复查询命令。
- 只增加工具功能，不提升社区互动。

### 3. 优先自动化内容，不是人工维护

频道和群组运营应尽量自动化。

优先考虑：

- 异动提醒。
- 涨跌榜。
- 热门币排行。
- AI 市场摘要。
- 新闻摘要。

避免：

- 需要长期人工复制粘贴的流程。
- 依赖人工每天维护的内容。

### 4. 优先免费方案，不是增加服务器成本

项目当前必须保持低成本或零成本运营。

优先使用：

- GitHub Actions。
- Render 免费方案。
- SQLite。
- 免费或低频 API。

避免：

- 未经确认引入付费服务器。
- 未经确认引入付费数据库。
- 未经确认引入高成本 API。

### 5. 代码必须模块化

随着功能增加，代码必须逐步模块化。

建议方向：

- 配置独立。
- API 客户端独立。
- 命令处理独立。
- Telegram 发送逻辑独立。
- 数据库访问独立。
- 文案格式化独立。

避免：

- 所有功能继续堆在一个大文件。
- 复制粘贴相似逻辑。
- 将密钥写入代码。

### 6. 所有重大改动必须同步更新文档

重大改动包括：

- 新增功能。
- 修改部署方式。
- 新增数据库结构。
- 新增或替换外部 API。
- 修改产品方向。
- 修改 Roadmap 优先级。

必须同步更新：

- `docs/PROJECT_STATUS.md`
- `docs/ROADMAP.md`
- `docs/CHANGELOG.md`

根据改动类型，可能还需要更新：

- `docs/DATABASE.md`
- `docs/DEPLOYMENT.md`
- `docs/API_REFERENCE.md`
- `docs/AI_CONTEXT.md`

## 每次开发完成后的固定检查

开发完成后必须检查：

- 功能是否符合 Crypto Pulse 项目目标。
- 是否避免投资建议、喊单、信号群、付费会员方向。
- 是否继续保持免费或低成本部署。
- 是否影响 Bot1 或 Bot2 在线运行。
- 是否需要新增环境变量。
- 是否需要更新数据库文档。
- 是否需要更新部署文档。
- 是否已经更新 `PROJECT_STATUS.md`、`ROADMAP.md`、`CHANGELOG.md`。

## 统一提醒规范

每次开发完成后，AI Agent 必须提醒开发者：

```text
本次开发完成后，请确认以下文档已同步更新：
- docs/PROJECT_STATUS.md
- docs/ROADMAP.md
- docs/CHANGELOG.md
```

如果涉及数据库、部署或外部 API，还必须提醒：

```text
本次改动涉及数据库、部署或外部 API，请同时确认：
- docs/DATABASE.md
- docs/DEPLOYMENT.md
- docs/API_REFERENCE.md
```

## 代码修改后的部署提醒规范

以后每次 AI Agent 完成任何代码修改后，最终开发完成报告必须附带“小白部署步骤”。不能只说“请部署”或“请 git push”。

开发者必须手动完成以下流程：

1. 在本地确认文件已修改。
2. 运行测试。
3. 执行 `git add .`。
4. 执行 `git commit -m "本次修改说明"`。
5. 执行 `git push`。
6. 打开 GitHub 确认代码已更新。
7. 打开 Render 确认服务是否自动部署。
8. 如果 Render 没有自动部署，点击 Manual Deploy，再点击 Deploy Latest Commit。
9. 部署完成后重新测试 Telegram Bot。

AI Agent 输出开发完成报告时，必须按小白友好格式附带：

```text
一、我要做什么
把本次代码修改提交到 GitHub，并让 Render 部署最新版本。

二、在哪里操作
Windows 终端、GitHub、Render、Telegram。

三、具体步骤
1. 打开 Windows 终端。
2. 进入项目目录。
3. 运行测试命令。
4. 执行 git add .
5. 执行 git commit -m "本次修改说明"
6. 执行 git push
7. 打开 GitHub 仓库确认文件已更新。
8. 打开 Render，进入 crypto-assistant-bot 服务。
9. 查看是否自动部署最新提交。
10. 如果没有自动部署，点击 Manual Deploy。
11. 点击 Deploy Latest Commit。
12. 部署完成后，在 Telegram 群组重新测试 Bot。

四、怎么判断成功
- GitHub 能看到最新提交。
- Render 显示部署成功并处于 Live。
- Telegram Bot 能正常回复命令。

五、如果失败怎么办
- 如果测试失败，先不要提交，把错误发给 AI Agent。
- 如果 git push 失败，检查网络和 GitHub 权限。
- 如果 Render 没有自动部署，手动点击 Deploy Latest Commit。
- 如果 Telegram Bot 没回复，查看 Render Logs。
```

## 小白友好操作规范

项目开发者不是专业程序员。以后任何需要开发者手动操作的任务，AI Agent 都必须提供一步一步说明，不能只写一句概括性指令。

适用范围包括但不限于：

- GitHub Actions 操作。
- Render 操作。
- Telegram BotFather 操作。
- Telegram 群和频道设置。
- 环境变量配置。
- 本地命令行操作。
- 测试命令。
- 查看日志。
- 回滚操作。
- 故障排查。

所有人工操作说明必须包含以下 5 个部分：

### 一、我要做什么

用一句话说明这次操作的目的。

### 二、在哪里操作

说明具体平台或工具，例如 GitHub、Render、Telegram、BotFather、Windows 终端。

### 三、具体步骤

必须按 1、2、3、4 分步写清楚。每一步都要能直接照做。

### 四、怎么判断成功

说明成功后开发者会看到什么结果，例如页面提示、日志内容、Telegram 消息、命令输出。

### 五、如果失败怎么办

列出常见错误和处理办法。

错误示例，禁止只写：

```text
设置环境变量 DATABASE_PATH。
```

正确示例，必须写成：

```text
一、我要做什么
给 Render 服务配置 SQLite 数据库路径。

二、在哪里操作
Render 控制台。

三、具体步骤
1. 打开 Render。
2. 进入 crypto-assistant-bot 服务。
3. 点击 Environment。
4. 点击 Add Environment Variable。
5. Key 填 DATABASE_PATH。
6. Value 填 crypto_pulse.db。
7. 点击 Save。
8. 点击 Manual Deploy，重新部署服务。

四、怎么判断成功
部署完成后，Render 日志中能看到 SQLite initialized。

五、如果失败怎么办
- 如果找不到 Environment，确认你进入的是 Web Service 页面。
- 如果部署失败，打开 Logs 查看错误内容。
- 如果 Bot 无响应，确认 TELEGRAM_BOT_TOKEN_2 仍然存在。
```

另一个正确示例：

```text
一、我要做什么
手动运行 GitHub Actions，测试频道是否能收到广播消息。

二、在哪里操作
GitHub 仓库的 Actions 页面。

三、具体步骤
1. 打开 GitHub 仓库。
2. 点击 Actions。
3. 点击 Crypto Broadcaster Bot workflow。
4. 点击 Run workflow。
5. 如果要测试每日榜单，force_daily_rankings 填 1。
6. 点击绿色 Run workflow。
7. 等待运行完成。
8. 打开 Telegram 频道检查是否收到消息。

四、怎么判断成功
GitHub Actions 显示绿色成功，Telegram 频道收到行情播报或榜单消息。

五、如果失败怎么办
- 如果 Actions 失败，点开失败步骤查看日志。
- 如果提示缺少 secret，检查 TELEGRAM_CHANNEL_ID 和 TELEGRAM_BOT_TOKEN_1。
- 如果频道没收到消息，确认 Bot1 是频道管理员。
```

## 禁止事项

- 不要使用 Binance API 作为主要数据源。
- 不要提供投资建议。
- 不要开发喊单功能。
- 不要开发信号群功能。
- 不要开发付费会员功能。
- 不要引入未确认的付费服务。
- 不要忽略文档更新。
