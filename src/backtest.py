"""回测引擎 — 模拟历史交易"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from src.portfolio import Portfolio
from src.strategy import BaseStrategy, Signal
from src.config import (
    INITIAL_CAPITAL, MAX_POSITIONS, POSITION_SIZE,
    STOP_LOSS, TAKE_PROFIT, COMMISSION,
)


@dataclass
class BacktestResult:
    initial_capital: float
    final_value: float
    total_return: float
    total_return_pct: float
    num_trades: int
    win_rate: float
    max_drawdown: float
    sharpe_ratio: float
    history: pd.DataFrame
    trades: List


def run_backtest(
    prices_df: pd.DataFrame,
    strategy: BaseStrategy,
    initial_capital: float = INITIAL_CAPITAL,
    max_positions: int = MAX_POSITIONS,
    position_size: float = POSITION_SIZE,
    stop_loss: float = STOP_LOSS,
    take_profit: float = TAKE_PROFIT,
    commission: float = COMMISSION,
    verbose: bool = True,
) -> BacktestResult:
    """运行回测"""

    portfolio = Portfolio(initial_capital, commission)
    symbols = strategy.symbols

    # 获取价格数据
    closes = prices_df.get("Close", pd.DataFrame())
    if closes.empty:
        raise ValueError("无收盘价数据")

    # 只保留有数据的股票
    valid_symbols = [s for s in symbols if s in closes.columns and closes[s].dropna().shape[0] >= 20]
    if verbose:
        print(f"回测股票: {valid_symbols}")
        print(f"初始资金: HK${initial_capital:,.0f}")
        print(f"时间范围: {closes.index[0].date()} → {closes.index[-1].date()}")
        print(f"交易日数: {len(closes)}")
        print()

    dates = closes.index
    prev_prices = {}

    for i, date in enumerate(dates):
        date_str = str(date.date())

        # 当前价格
        current_prices = {}
        for sym in valid_symbols:
            val = closes[sym].iloc[i]
            if pd.notna(val):
                current_prices[sym] = float(val)

        # === 检查止盈止损 ===
        for sym, pos in list(portfolio.positions.items()):
            if sym not in current_prices or pos.shares <= 0:
                continue
            price = current_prices[sym]
            pnl_pct = (price - pos.avg_cost) / pos.avg_cost

            if pnl_pct <= stop_loss:
                shares_to_sell = pos.shares
                portfolio.sell(date_str, sym, price, shares_to_sell, f"止损 ({pnl_pct*100:.1f}%)")
                if verbose:
                    print(f"  [{date_str}] 🔴 止损 {sym}: {shares_to_sell:.0f}股 @HK${price:.2f} ({pnl_pct*100:.1f}%)")

            elif pnl_pct >= take_profit:
                shares_to_sell = pos.shares
                portfolio.sell(date_str, sym, price, shares_to_sell, f"止盈 ({pnl_pct*100:.1f}%)")
                if verbose:
                    print(f"  [{date_str}] 🟢 止盈 {sym}: {shares_to_sell:.0f}股 @HK${price:.2f} (+{pnl_pct*100:.1f}%)")

        # === 策略决策 ===
        for sym in valid_symbols:
            if sym not in current_prices:
                continue

            price = current_prices[sym]
            pos = portfolio.positions.get(sym)

            # 只用到当前日期为止的数据（避免未来数据泄露）
            signal, reason = strategy.decide(
                date_str, sym,
                {"Close": closes.loc[:date]},
                {"positions": {s: p.shares for s, p in portfolio.positions.items()},
                 "cash": portfolio.cash}
            )

            if signal == Signal.BUY and (pos is None or pos.shares == 0):
                if len(portfolio.positions) >= max_positions:
                    continue

                max_value = portfolio.cash * position_size
                shares = int(max_value / price)
                if shares > 0 and portfolio.can_buy(price, shares):
                    portfolio.buy(date_str, sym, price, shares, reason)
                    if verbose:
                        print(f"  [{date_str}] 📈 买入 {sym}: {shares}股 @HK${price:.2f} | {reason}")

            elif signal == Signal.SELL and pos is not None and pos.shares > 0:
                sold_shares = pos.shares
                portfolio.sell(date_str, sym, price, sold_shares, reason)
                if verbose:
                    print(f"  [{date_str}] 📉 卖出 {sym}: {sold_shares:.0f}股 @HK${price:.2f} | {reason}")

        # 记录当日快照
        portfolio.record_snapshot(date_str, current_prices)
        prev_prices = current_prices

    # === 计算指标 ===
    final_prices = {s: float(closes[s].dropna().iloc[-1]) for s in valid_symbols if not closes[s].dropna().empty}
    summary = portfolio.summary(final_prices)

    # 计算最大回撤
    history_df = pd.DataFrame(portfolio.history)
    if not history_df.empty:
        peak = history_df["total"].cummax()
        drawdown = (history_df["total"] - peak) / peak
        max_dd = float(drawdown.min())
    else:
        max_dd = 0.0

    # 日收益率
    if not history_df.empty and len(history_df) > 1:
        daily_returns = history_df["total"].pct_change().dropna()
        sharpe = float(daily_returns.mean() / daily_returns.std() * np.sqrt(252)) if daily_returns.std() > 0 else 0
    else:
        sharpe = 0.0

    # 胜率
    winning_trades = 0
    buy_prices = {}
    for t in portfolio.trades:
        if t.action == "BUY":
            buy_prices.setdefault(t.symbol, []).append((t.shares, t.price))
        elif t.action == "SELL" and t.symbol in buy_prices and buy_prices[t.symbol]:
            # 简化：用平均买入价判断
            bought = buy_prices[t.symbol]
            avg_buy = sum(p * s for s, p in bought) / max(sum(s for s, _ in bought), 1)
            if t.price > avg_buy:
                winning_trades += 1
            buy_prices[t.symbol] = []

    win_rate = winning_trades / len([t for t in portfolio.trades if t.action == "SELL"]) if portfolio.trades else 0

    return BacktestResult(
        initial_capital=summary["initial_capital"],
        final_value=summary["total_value"],
        total_return=summary["pnl"],
        total_return_pct=summary["pnl_pct"],
        num_trades=len(portfolio.trades),
        win_rate=win_rate,
        max_drawdown=max_dd,
        sharpe_ratio=sharpe,
        history=history_df,
        trades=portfolio.trades,
    )
