# 🤖 AI Investor Agent

基于 [nanobot](https://github.com/neumanncheng/nanobot) 框架的港股中期波段交易分析机器人。

**策略**：多策略技术扫描（动量/RSI/MA）+ 新闻交叉验证 → 信号共振才交易

---

## 功能

- 📊 **每日自动扫描** — HKT 16:30 后自动执行多策略技术打分
- 📰 **新闻交叉验证** — 对评分前 5 股票自动搜索相关新闻
- 💰 **模拟交易** — 100 万港币虚拟资金，仓位/止损/止盈全自动管理
- 📈 **回测引擎** — 历史数据回测验证策略表现
- 🐳 **Docker 一键部署** — 支持任意 Linux 环境

## 策略

| 策略 | 信号逻辑 |
|------|---------|
| 动量 | N 日价格变化率，突破阈值触发 |
| RSI | 超买(>70)/超卖(<30)，带背离检测 |
| MA 交叉 | 短/长期均线金叉死叉 |

信号强度：+2/+1（偏多）· 0（观望）· -1/-2（偏空）

## 快速开始

### Docker（推荐）

```bash
git clone https://github.com/Neumanncheng/investment_bot.git
cd investment_bot
cp .env.example .env
# 编辑 .env 填入 DEEPSEEK_API_KEY 和 AI_INVESTOR_DISCORD_TOKEN
docker compose up -d
```

### 手动部署

```bash
pip install nanobot-ai
git clone https://github.com/Neumanncheng/investment_bot.git
cp -r investment_bot/* ~/.nanobot/workspace/
cd ~/.nanobot/workspace
pip install -r requirements.txt
export DEEPSEEK_API_KEY="sk-xxx"
export AI_INVESTOR_DISCORD_TOKEN="MTE-xxx"
nanobot gateway
```

## 配置

### 环境变量

| 变量 | 说明 |
|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 |
| `AI_INVESTOR_DISCORD_TOKEN` | Discord Bot Token |

### 策略参数

编辑 `config.py`：

- `INITIAL_CAPITAL` — 初始资金（默认 100万）
- `POSITION_SIZE` — 单只仓位上限（默认 20%）
- `STOP_LOSS` — 止损比例（默认 8%）
- `TAKE_PROFIT` — 止盈比例（默认 20%）
- `DEFAULT_SYMBOLS` — 监控的港股列表（70+ 只）

### 扫描频率

默认 HKT 每个交易日 16:30 自动扫描。通过 `HEARTBEAT.md` 或 `cron/jobs.json` 调整。

## 文件结构

```
investment_bot/
├── src/live.py         # 每日扫描入口
├── src/scan.py         # 单策略信号扫描
├── src/backtest.py     # 历史回测引擎
├── src/strategy.py     # 策略逻辑（动量/RSI/MA）
├── src/portfolio.py    # 组合与仓位管理
├── src/data_fetcher.py # yfinance 数据获取
├── src/config.py       # 策略参数配置
├── config.json          # nanobot 全局配置
├── AGENTS.md            # Agent 行为指令
├── SOUL.md              # 交易理念
├── HEARTBEAT.md         # 定期任务
├── cron/jobs.json       # 定时任务定义
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 风险声明

⚠️ 本系统为**模拟交易**，所有信号仅供参考学习，不构成投资建议。真实市场有滑点、流动性等额外风险。
