#!/usr/bin/env python3
"""AI Investor — AI 驱动的虚拟投资回测系统

用法:
    python main.py                      # 默认: 动量策略, 1个月, 100万
    python main.py --strategy rsi       # RSI 策略
    python main.py --strategy ma        # 均线策略
    python main.py --period 3mo         # 3个月回测
    python main.py --capital 500000     # 50万资金
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from data_fetcher import fetch_stock_data
from strategy import create_strategy
from backtest import run_backtest
from portfolio import Portfolio
from config import (
    INITIAL_CAPITAL, DEFAULT_SYMBOLS, BACKTEST_PERIOD,
    MAX_POSITIONS, POSITION_SIZE, STOP_LOSS, TAKE_PROFIT, COMMISSION,
)


def print_header(title: str):
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(result):
    """打印漂亮的回测报告"""
    print_header("📊 回测报告")

    color = "🟢" if result.total_return >= 0 else "🔴"
    print(f"""
   初始资金:       HK${result.initial_capital:>11,.0f}
   最终资金:       HK${result.final_value:>11,.0f}
   {'─' * 35}
   总收益:         {color} HK${result.total_return:>10,.0f}  ({result.total_return_pct:+.2f}%)
   {'─' * 35}
   交易次数:       {result.num_trades:>12}
   胜率:           {result.win_rate:>11.0%}
   最大回撤:       {result.max_drawdown:>11.2%}
   夏普比率:       {result.sharpe_ratio:>11.2f}
""")

    # 如果盈利明显，按比例推算
    if result.history is not None and not result.history.empty:
        days = len(result.history)
        if days > 1 and result.total_return_pct != 0:
            daily_return = result.total_return_pct / days
            weekly_proj = daily_return * 5
            monthly_proj = daily_return * 21
            yearly_proj = daily_return * 252

            print(f"  ── 按当前表现推算 ──")
            print(f"  日均收益:       {daily_return:+.2f}%")
            print(f"  周预估:         {weekly_proj:+.2f}%  (HK${result.initial_capital * weekly_proj / 100:,.0f})")
            print(f"  月预估:         {monthly_proj:+.2f}%  (HK${result.initial_capital * monthly_proj / 100:,.0f})")
            print(f"  年化预估:       {yearly_proj:+.2f}%  (HK${result.initial_capital * yearly_proj / 100:,.0f})")
            print()

    # 最近交易
    if result.trades:
        print(f"  ── 最近 10 笔交易 ──")
        for t in result.trades[-10:]:
            emoji = "📈" if t.action == "BUY" else "📉"
            print(f"  {emoji} {t.date} | {t.action:4s} {t.symbol:8s} {t.shares:6.0f}股 @HK${t.price:.2f} | {t.reason}")
        print()


def main():
    parser = argparse.ArgumentParser(description="AI Investor 回测系统")
    parser.add_argument("--strategy", choices=["ma", "rsi", "momentum", "ai"],
                        default="momentum", help="交易策略 (默认: momentum)")
    parser.add_argument("--symbols", nargs="+", default=DEFAULT_SYMBOLS,
                        help="股票代码列表")
    parser.add_argument("--period", default="1mo",
                        help="回测周期: 1mo, 3mo, 6mo, 1y, 5d 等")
    parser.add_argument("--capital", type=float, default=INITIAL_CAPITAL,
                        help="初始资金 (默认: 100万)")
    parser.add_argument("--max-positions", type=int, default=MAX_POSITIONS,
                        help="最大持仓数")
    parser.add_argument("--quiet", action="store_true", help="静默模式")
    args = parser.parse_args()

    print_header(f"🤖 AI Investor 回测系统（港股）")
    print(f"  策略: {args.strategy} | 资金: HK${args.capital:,.0f} | 周期: {args.period}")
    print(f"  股票: {', '.join(args.symbols)}")
    print()

    # 1. 获取数据
    print("📡 正在获取市场数据...")
    prices_df = fetch_stock_data(args.symbols, period=args.period)

    closes = prices_df.get("Close", None)
    if closes is None or closes.empty:
        print("❌ 无法获取数据，请检查股票代码或网络")
        sys.exit(1)

    # 删除全是 NaN 的列
    valid_cols = [c for c in closes.columns if closes[c].dropna().shape[0] > 5]
    valid_symbols = [s for s in args.symbols if s in valid_cols]
    if not valid_symbols:
        print("❌ 所有股票数据不足")
        sys.exit(1)

    if len(valid_symbols) < len(args.symbols):
        skipped = set(args.symbols) - set(valid_symbols)
        print(f"⚠️  跳过数据不足的股票: {skipped}")

    # 显示最新价格
    latest_prices = {s: float(closes[s].dropna().iloc[-1]) for s in valid_symbols}
    print(f"  获取到 {len(closes)} 个交易日数据")
    print()
    print("  当前价格:")
    for sym, p in latest_prices.items():
        change = ((p - closes[sym].dropna().iloc[-2]) / closes[sym].dropna().iloc[-2] * 100) if len(closes[sym].dropna()) >= 2 else 0
        print(f"    {sym:8s}  HK${p:>10.2f}  ({change:+.2f}%)")

    # 2. 创建策略
    strategy = create_strategy(args.strategy, valid_symbols)

    # 3. 运行回测
    print()
    print("🔄 运行回测中...")
    print("─" * 60)

    result = run_backtest(
        prices_df=prices_df,
        strategy=strategy,
        initial_capital=args.capital,
        max_positions=args.max_positions,
        verbose=not args.quiet,
    )

    # 4. 打印报告
    print_result(result)

    # 5. 额外信息
    print_header("📌 持仓明细")
    closes_last = {s: float(closes[s].dropna().iloc[-1]) for s in valid_symbols}
    portfolio = Portfolio(args.capital, COMMISSION)
    # 重新模拟一遍得到最终持仓 (简单方法: 从 result 中提取)
    held = {}
    buy_qty = {}
    for t in result.trades:
        if t.action == "BUY":
            buy_qty[t.symbol] = buy_qty.get(t.symbol, 0) + t.shares
            # 重新计算成本
            if t.symbol not in held:
                held[t.symbol] = {"shares": 0, "cost": 0}
            total_cost = held[t.symbol]["cost"] + t.price * t.shares
            held[t.symbol]["shares"] += t.shares
            held[t.symbol]["cost"] = total_cost / held[t.symbol]["shares"] if held[t.symbol]["shares"] > 0 else 0
        elif t.action == "SELL":
            if t.symbol in held:
                held[t.symbol]["shares"] -= t.shares
                if held[t.symbol]["shares"] <= 0:
                    del held[t.symbol]

    if held:
        for sym, info in held.items():
            if info["shares"] > 0:
                price = latest_prices.get(sym, 0)
                value = info["shares"] * price
                pnl = (price - info["cost"]) * info["shares"]
                pnl_pct = (price - info["cost"]) / info["cost"] * 100 if info["cost"] > 0 else 0
                print(f"  {sym:8s}  {info['shares']:6.0f}股  @HK${info['cost']:.2f}  现价 HK${price:.2f}  "
                      f"市值 HK${value:,.0f}  {pnl_pct:+.1f}%")
    else:
        print("  (空仓)")

    print()
    print("=" * 60)
    print(f"  💡 试试: python main.py --strategy rsi --period 3mo")
    print(f"  💡 试试: python main.py --strategy ma --symbols 0700.HK 9988.HK 3690.HK")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
