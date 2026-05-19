"""虚拟投资组合管理"""

from dataclasses import dataclass, field
from typing import Dict, List
import pandas as pd


@dataclass
class Position:
    symbol: str
    shares: float = 0
    avg_cost: float = 0


@dataclass
class Trade:
    date: str
    symbol: str
    action: str         # BUY / SELL
    shares: float
    price: float
    value: float
    reason: str = ""


class Portfolio:
    """虚拟投资组合"""

    def __init__(self, initial_capital: float, commission: float = 0.001):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.commission = commission
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.history: List[dict] = []

    @property
    def total_value(self) -> float:
        """当前总市值（估值需要外部注入）"""
        return self.cash  # 纯现金部分

    def can_buy(self, price: float, shares: float) -> bool:
        cost = price * shares * (1 + self.commission)
        return self.cash >= cost

    def buy(self, date: str, symbol: str, price: float, shares: float, reason: str = ""):
        cost = price * shares
        fee = cost * self.commission
        if self.cash < cost + fee:
            return False

        self.cash -= cost + fee

        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol=symbol)

        pos = self.positions[symbol]
        total_cost = pos.avg_cost * pos.shares + cost
        pos.shares += shares
        pos.avg_cost = total_cost / pos.shares if pos.shares > 0 else 0

        self.trades.append(Trade(date, symbol, "BUY", shares, price, cost, reason))
        return True

    def sell(self, date: str, symbol: str, price: float, shares: float, reason: str = ""):
        if symbol not in self.positions or self.positions[symbol].shares < shares:
            return False

        pos = self.positions[symbol]
        proceeds = price * shares
        fee = proceeds * self.commission
        self.cash += proceeds - fee
        pos.shares -= shares

        if pos.shares == 0:
            del self.positions[symbol]

        self.trades.append(Trade(date, symbol, "SELL", shares, price, proceeds, reason))
        return True

    def record_snapshot(self, date: str, prices: Dict[str, float]):
        """记录当日快照（用于画曲线）"""
        stock_value = sum(
            pos.shares * prices.get(sym, 0)
            for sym, pos in self.positions.items()
        )
        total = self.cash + stock_value
        pnl = total - self.initial_capital
        pnl_pct = pnl / self.initial_capital * 100

        self.history.append({
            "date": date,
            "cash": round(self.cash, 2),
            "stock_value": round(stock_value, 2),
            "total": round(total, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
        })

    def current_positions_value(self, prices: Dict[str, float]) -> float:
        return sum(
            pos.shares * prices.get(sym, 0)
            for sym, pos in self.positions.items()
        )

    def summary(self, prices: Dict[str, float]) -> dict:
        stock_val = self.current_positions_value(prices)
        total = self.cash + stock_val
        pnl = total - self.initial_capital
        return {
            "initial_capital": self.initial_capital,
            "cash": round(self.cash, 2),
            "stock_value": round(stock_val, 2),
            "total_value": round(total, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl / self.initial_capital * 100, 2),
            "num_positions": len(self.positions),
            "num_trades": len(self.trades),
        }
