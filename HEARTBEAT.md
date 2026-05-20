# Heartbeat Tasks

This file is checked every 30 minutes by your AI investor agent.
Add tasks below that you want the agent to work on periodically.

If this file has no tasks (only headers and comments), the agent will skip the heartbeat.

## Active Tasks

<!-- Add your periodic tasks below this line -->

- **每日港股扫描（心跳版）** — 每个交易日：先检查 `latest_signals.json` 的 `date` 字段，若已是今天则跳过；若不是今天则运行 `python3 -m src.live` → 搜索新闻 → 交叉验证 → 发报告到 Discord。扫描时间由 `scan_schedule.json` 控制（通过 `investment-bot schedule` 命令或 Discord 的 `@AI Investor 设置扫描时间` 设定），默认 HKT 16:30。心跳在设定的扫描窗口前 30 分钟到后 2 小时内生效，即使 cron 错过也能补扫。

## Completed

<!-- Move completed tasks here or delete them -->
