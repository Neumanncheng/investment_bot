# Heartbeat Tasks

This file is checked every 30 minutes by your AI investor agent.
Add tasks below that you want the agent to work on periodically.

If this file has no tasks (only headers and comments), the agent will skip the heartbeat.

## Active Tasks

<!-- Add your periodic tasks below this line -->

- **每日港股扫描（心跳版）** — 每个交易日 HKT 16:30-20:00 期间：先检查 `latest_signals.json` 的 `date` 字段，若已是今天则跳过；若不是今天则运行 `python3 -m src.live` → 搜索新闻 → 交叉验证 → 发报告到 Discord。这样即使 cron 错过、gateway 刚启动，心跳也能在 30 分钟内补扫。

## Completed

<!-- Move completed tasks here or delete them -->
