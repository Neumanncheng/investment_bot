"""交易策略模块

策略基类 + 多种内置策略。AI 策略预留接口供 nanobot 调用。
"""

from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from enum import Enum


class Signal(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class BaseStrategy(ABC):
    """策略基类"""

    def __init__(self, symbols: List[str]):
        self.symbols = symbols

    @abstractmethod
    def decide(self, date: str, symbol: str, prices: pd.DataFrame, portfolio: dict) -> Tuple[Signal, str]:
        """返回 (买入/卖出/持有, 理由)"""
        ...


class MovingAverageCrossover(BaseStrategy):
    """双均线交叉策略：金叉买入，死叉卖出"""

    def __init__(self, symbols: List[str], short: int = 5, long: int = 20):
        super().__init__(symbols)
        self.short = short
        self.long = long

    def decide(self, date, symbol, prices, portfolio) -> Tuple[Signal, str]:
        closes = prices.get("Close", pd.DataFrame())
        if symbol not in closes.columns or closes[symbol].dropna().empty:
            return Signal.HOLD, "数据不足"

        series = closes[symbol].dropna()
        if len(series) < self.long:
            return Signal.HOLD, f"需要至少 {self.long} 天数据"

        ma_short = series.rolling(self.short).mean().iloc[-1]
        ma_long = series.rolling(self.long).mean().iloc[-1]
        prev_short = series.rolling(self.short).mean().iloc[-2]
        prev_long = series.rolling(self.long).mean().iloc[-2]

        if pd.isna(ma_short) or pd.isna(ma_long) or pd.isna(prev_short) or pd.isna(prev_long):
            return Signal.HOLD, "均线数据不足"

        if prev_short <= prev_long and ma_short > ma_long:
            return Signal.BUY, f"金叉信号 MA{self.short}({ma_short:.2f}) > MA{self.long}({ma_long:.2f})"
        elif prev_short >= prev_long and ma_short < ma_long:
            return Signal.SELL, f"死叉信号 MA{self.short}({ma_short:.2f}) < MA{self.long}({ma_long:.2f})"

        return Signal.HOLD, ""


class RSIMeanReversion(BaseStrategy):
    """RSI 均值回归：超卖买入，超买卖出"""

    def __init__(self, symbols: List[str], period: int = 14, oversold: int = 30, overbought: int = 70):
        super().__init__(symbols)
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    @staticmethod
    def calc_rsi(series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def decide(self, date, symbol, prices, portfolio) -> Tuple[Signal, str]:
        closes = prices.get("Close", pd.DataFrame())
        if symbol not in closes.columns or closes[symbol].dropna().empty:
            return Signal.HOLD, "数据不足"

        series = closes[symbol].dropna()
        if len(series) < self.period + 1:
            return Signal.HOLD, f"需要至少 {self.period + 1} 天数据"

        rsi = self.calc_rsi(series, self.period)
        current_rsi = rsi.iloc[-1]

        if pd.isna(current_rsi):
            return Signal.HOLD, "RSI 数据不足"

        if current_rsi < self.oversold:
            return Signal.BUY, f"RSI 超卖 ({current_rsi:.1f} < {self.oversold})"
        elif current_rsi > self.overbought:
            return Signal.SELL, f"RSI 超买 ({current_rsi:.1f} > {self.overbought})"

        return Signal.HOLD, ""


class MomentumStrategy(BaseStrategy):
    """动量策略：涨势买入，跌势卖出"""

    def __init__(self, symbols: List[str], lookback: int = 10, threshold: float = 0.03):
        super().__init__(symbols)
        self.lookback = lookback
        self.threshold = threshold

    def decide(self, date, symbol, prices, portfolio) -> Tuple[Signal, str]:
        closes = prices.get("Close", pd.DataFrame())
        if symbol not in closes.columns or closes[symbol].dropna().empty:
            return Signal.HOLD, "数据不足"

        series = closes[symbol].dropna()
        if len(series) < self.lookback:
            return Signal.HOLD, f"需要至少 {self.lookback} 天数据"

        momentum = (series.iloc[-1] - series.iloc[-self.lookback]) / series.iloc[-self.lookback]
        recent_change = (series.iloc[-1] - series.iloc[-2]) / series.iloc[-2]

        if momentum > self.threshold and recent_change > 0:
            return Signal.BUY, f"正动量 {momentum*100:.1f}% (近{self.lookback}日)"
        elif momentum < -self.threshold:
            return Signal.SELL, f"负动量 {momentum*100:.1f}% (近{self.lookback}日)"

        return Signal.HOLD, ""


class AIStrategy(BaseStrategy):
    """AI 决策策略 — 预留给 nanobot agent 调用

    工作流程：
    1. 每交易日收集 stock 的技术指标 + 基本面 + 新闻
    2. 调用 LLM 分析并做出 BUY/SELL/HOLD 决策
    3. 执行交易

    Usage:
        strategy = AIStrategy(symbols)
        # 每个交易日:
        analysis = strategy.prepare_analysis_prompt(symbol, market_data, portfolio)
        # 发送给 LLM → 解析回复 → 得到 Signal
    """

    def __init__(self, symbols: List[str]):
        super().__init__(symbols)

    def prepare_analysis_prompt(
        self,
        symbol: str,
        closes: pd.Series,
        volumes: pd.Series,
        portfolio_positions: dict,
        cash: float,
    ) -> str:
        """生成发给 LLM 的分析 prompt"""
        latest_price = closes.iloc[-1]
        change_1d = (closes.iloc[-1] - closes.iloc[-2]) / closes.iloc[-2] * 100 if len(closes) >= 2 else 0
        change_5d = (closes.iloc[-1] - closes.iloc[-5]) / closes.iloc[-5] * 100 if len(closes) >= 5 else 0
        avg_vol = volumes.iloc[-5:].mean() if len(volumes) >= 5 else volumes.iloc[-1]
        vol_ratio = volumes.iloc[-1] / avg_vol if avg_vol > 0 else 1

        return f"""分析股票: {symbol}
当前价格: HK${latest_price:.2f}
1日涨跌: {change_1d:+.2f}%
5日涨跌: {change_5d:+.2f}%
成交量比: {vol_ratio:.2f}x 日均
当前持仓: {portfolio_positions}
可用现金: HK${cash:,.2f}

请做出交易决策: BUY / SELL / HOLD
并说明理由（一句话）。"""

    def decide(self, date, symbol, prices, portfolio) -> Tuple[Signal, str]:
        # AI 策略需要外部 LLM 调用，这里返回 HOLD 作为 fallback
        # 实际使用时，在 backtest 循环中调用 prepare_analysis_prompt 然后传给 LLM
        return Signal.HOLD, "AI 策略需外部 LLM 调用"


# ========== 策略工厂 ==========

def create_strategy(name: str, symbols: List[str], **kwargs) -> BaseStrategy:
    strategies = {
        "ma": MovingAverageCrossover,
        "rsi": RSIMeanReversion,
        "momentum": MomentumStrategy,
        "ai": AIStrategy,
    }
    cls = strategies.get(name)
    if cls is None:
        raise ValueError(f"未知策略: {name}，可选: {list(strategies.keys())}")
    return cls(symbols, **kwargs)
