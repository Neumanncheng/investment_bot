# Agent Instructions

## Daily Workflow

每个交易日（周一至周五，排除香港公众假期）HKT 16:30 后执行每日扫描：

1. **技术扫描** — 运行 `python live.py`，获取动量/RSI/MA 多策略打分
2. **新闻搜索** — 对评分前 5 的股票，用 `web_search` 搜索相关新闻
3. **交叉验证** — 技术信号 + 新闻共振才考虑交易
4. **决策执行** — 输出买卖决策和仓位调整

## Heartbeat Tasks

用 `HEARTBEAT.md` 管理定期任务。不要只写到 MEMORY.md。

## Nanobot Code Protection

⚠️ **禁止修改** `/home/neumann/nanobot/` 下的任何文件（bridge、webui 等 nanobot 核心代码）。
你只能**读取**这些文件，不能使用 `write_file`、`edit_file` 或任何 `exec` 命令去修改它们。
如需改动 nanobot 代码，请明确告知用户，由用户手动操作。

## Tools

- `exec` — 运行 Python 脚本（live.py, backtest.py 等）
- `web_search` / `web_fetch` — 搜索港股新闻
- `write_file` / `edit_file` — 维护交易日志和组合状态
- `cron` — 设置定时任务（如有需要）
