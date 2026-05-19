# 🤖 AI Investor Agent

基于 [nanobot](https://github.com/neumanncheng/nanobot) 框架的港股中期波段交易分析机器人。

**策略**：多策略技术扫描（动量/RSI/MA）+ 新闻交叉验证 → 信号共振才交易

---

## 功能

- 📊 **每日自动扫描** — HKT 16:30 后自动执行多策略技术打分
- 📰 **新闻交叉验证** — 对评分前 5 股票自动搜索相关新闻
- 💰 **模拟交易** — 100 万港币虚拟资金，仓位/止损/止盈全自动管理
- 📈 **回测引擎** — 历史数据回测验证策略表现
- 🎛️ **策略档案** — 5 种预设模式一键切换（激进/均衡/保守/纯趋势/逆向）
- 🐳 **Docker 一键部署** — 支持任意 Linux 环境

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
pip install -e .      # 安装项目 + 依赖
export DEEPSEEK_API_KEY="sk-xxx"
export AI_INVESTOR_DISCORD_TOKEN="MTE-xxx"
nanobot gateway
```

## CLI 命令

安装后可使用 `investment-bot` 命令：

```bash
investment-bot scan                  # 每日技术扫描
investment-bot backtest -s ma        # 历史回测（-s 可选 ma/rsi/momentum）
investment-bot strategy              # 查看当前策略
investment-bot strategy --list       # 列出所有策略档案
investment-bot strategy --set aggressive  # 切换到激进策略
```

## 策略档案

5 种预设模式，适合不同市况：

| 档案 | 描述 | 仓位 | 止损 | 动量 | RSI | MA |
|------|------|------|------|------|-----|----|
| **balanced** ⭐ | 三策略等权，适合大多数市况 | 20% | -8% | ×1 | ×1 | ×1 |
| **aggressive** 🔥 | 动量主导，牛市利器 | 25% | -10% | ×3 | ×1 | ×1 |
| **conservative** 🛡️ | RSI主导，熊市防守，恒指过滤 | 15% | -5% | ×0 | ×2 | ×1 |
| **trend_only** 📏 | 仅看均线金叉死叉 | 20% | -8% | ×0 | ×0 | ×3 |
| **contrarian** 🔄 | 反向动量+超卖抄底 | 15% | -6% | ×-1 | ×2 | ×1 |

**切换方式：** Discord 发送 `@AI Investor 切换到 aggressive`，或 CLI `investment-bot strategy --set aggressive`。

## 配置

### 环境变量

| 变量 | 说明 |
|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 |
| `AI_INVESTOR_DISCORD_TOKEN` | Discord Bot Token |

### 策略参数

编辑 `src/config.py`：

- `INITIAL_CAPITAL` — 初始资金（默认 100万）
- `MAX_POSITIONS` — 最大持仓数（默认 5）
- `DEFAULT_SYMBOLS` — 监控的港股列表（70+ 只）
- `STRATEGY_PROFILES` — 5 种策略档案的参数定义
- `strategy_profile.json` — 当前选中的档案（运行时自动生成）

### 扫描频率

默认 HKT 每个交易日 16:30 自动扫描。通过 `HEARTBEAT.md` 或 `cron/jobs.json` 调整。

## 文件结构

```
investment_bot/
├── src/
│   ├── cli.py           # CLI 统一入口（scan/backtest/strategy）
│   ├── live.py          # 每日扫描 + 多策略打分
│   ├── scan.py          # 单策略信号扫描
│   ├── backtest.py      # 历史回测引擎
│   ├── strategy.py      # 策略逻辑（动量/RSI/MA）
│   ├── portfolio.py     # 组合与仓位管理
│   ├── data_fetcher.py  # yfinance 数据获取
│   └── config.py        # 全局参数 + 策略档案
├── tests/
│   └── test_strategy.py # 策略逻辑单元测试
├── pyproject.toml        # 项目元数据 + CLI 入口定义
├── config.json           # nanobot 全局配置
├── AGENTS.md             # Agent 行为指令
├── SOUL.md               # 交易理念
├── HEARTBEAT.md          # 定期任务
├── cron/jobs.json        # 定时任务定义
├── Dockerfile
├── docker-compose.yml
└── strategy_profile.json # 当前策略档案选择
```

## 风险声明

⚠️ 本系统为**模拟交易**，所有信号仅供参考学习，不构成投资建议。真实市场有滑点、流动性等额外风险。
