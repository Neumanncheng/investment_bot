"""数据获取模块 — 封装 yfinance"""

import yfinance as yf
import pandas as pd
from typing import List


def fetch_stock_data(symbols: List[str], period: str = "1mo", interval: str = "1d") -> pd.DataFrame:
    """下载股票历史数据，返回 MultiIndex DataFrame"""
    tickers = yf.Tickers(" ".join(symbols))
    df = tickers.history(period=period, interval=interval)
    return df


def fetch_info(symbols: List[str]) -> dict:
    """获取公司基本信息"""
    info = {}
    for sym in symbols:
        try:
            t = yf.Ticker(sym)
            info[sym] = t.info
        except Exception:
            info[sym] = {}
    return info


def get_current_prices(symbols: List[str]) -> dict:
    """获取当前价格"""
    prices = {}
    for sym in symbols:
        try:
            t = yf.Ticker(sym)
            prices[sym] = t.info.get("regularMarketPreviousClose") or t.info.get("previousClose") or 0
        except Exception:
            prices[sym] = 0
    return prices
