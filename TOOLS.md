# Tool Usage Notes

## exec — 运行 Python 脚本

- `timeout: 120` — yfinance 取数据可能较慢，给充足时间
- `denyPatterns: ["/home/neumann/nanobot/*"]` — 禁止修改 nanobot 源码
- 主要脚本：
  - `src/live.py` — 每日技术扫描 + 多策略打分
  - `src/scan.py` — 单一策略信号扫描
  - `src/backtest.py` — 历史回测
  - `src/data_fetcher.py` — yfinance 数据获取
  - `src/strategy.py` — 策略逻辑（动量/RSI/MA）
  - `src/portfolio.py` — 组合管理
  - `src/config.py` — 配置参数

## web_search / web_fetch — 新闻搜索

- 搜索港股相关新闻（公司公告、行业动态、宏观政策）
- 对技术评分 top 5 的股票逐只搜索
- 交叉验证：技术信号 + 新闻共振才操作

## write_file / edit_file — 记录

- 维护 `trades.jsonl` 交易日志（JSONL 格式，每行一条交易记录）
- 维护 `portfolio_state.json` 当前持仓状态
