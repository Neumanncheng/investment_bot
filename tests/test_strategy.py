"""Tests for strategy logic."""

import pandas as pd
import pytest

from src.strategy import (
    Signal,
    MomentumStrategy,
    RSIMeanReversion as RSIStrategy,
    MovingAverageCrossover as MAStrategy,
    create_strategy,
)


def _make_prices(series: pd.Series) -> dict:
    """Wrap a Series into the format strategies expect."""
    return {"Close": pd.DataFrame({series.name or "TEST": series})}


def _uptrend(n: int = 60) -> dict:
    s = pd.Series([100 + i * 0.5 for i in range(n)], name="TEST")
    idx = pd.date_range("2026-01-01", periods=n, freq="D")
    s.index = idx
    return _make_prices(s)


def _downtrend(n: int = 60) -> dict:
    s = pd.Series([100 - i * 0.5 for i in range(n)], name="TEST")
    idx = pd.date_range("2026-01-01", periods=n, freq="D")
    s.index = idx
    return _make_prices(s)


def _custom_series(values: list[float]) -> dict:
    s = pd.Series(values, name="TEST")
    idx = pd.date_range("2026-01-01", periods=len(values), freq="D")
    s.index = idx
    return _make_prices(s)


# ── MomentumStrategy ──────────────────────────────────────────────────

def test_momentum_buy_on_uptrend():
    """10日动量 > 3% 且最近日涨幅 > 0 → BUY"""
    strat = MomentumStrategy(["TEST"])
    sig, _ = strat.decide("2026-03-01", "TEST", _uptrend(60), {})
    assert sig == Signal.BUY


def test_momentum_sell_on_downtrend():
    """10日动量 < -3% → SELL"""
    strat = MomentumStrategy(["TEST"])
    sig, _ = strat.decide("2026-03-01", "TEST", _downtrend(60), {})
    assert sig == Signal.SELL


def test_momentum_hold_when_flat():
    """平盘 → HOLD"""
    flat = _custom_series([100] * 40)
    strat = MomentumStrategy(["TEST"])
    sig, _ = strat.decide("2026-02-10", "TEST", flat, {})
    assert sig == Signal.HOLD


# ── RSIStrategy ───────────────────────────────────────────────────────

def test_rsi_buy_when_oversold():
    """持续下跌产生低RSI → BUY"""
    strat = RSIStrategy(["TEST"])
    sig, _ = strat.decide("2026-03-01", "TEST", _downtrend(60), {})
    assert sig == Signal.BUY


def test_rsi_sell_when_overbought():
    """持续上涨产生高RSI → SELL"""
    strat = RSIStrategy(["TEST"])
    sig, _ = strat.decide("2026-03-01", "TEST", _uptrend(60), {})
    assert sig == Signal.SELL


# ── MAStrategy ────────────────────────────────────────────────────────

def test_ma_buy_on_golden_cross():
    """MA5从下方上穿MA20 → BUY"""
    prices = []
    prices.extend([100] * 25)       # flat
    prices.extend([95, 94, 93, 92, 91])  # dip below
    prices.extend([96, 100, 105, 108])    # recovery → cross at last point
    strat = MAStrategy(["TEST"])
    sig, _ = strat.decide("2026-02-09", "TEST", _custom_series(prices), {})
    assert sig == Signal.BUY, f"Expected BUY, got {sig}"


def test_ma_sell_on_death_cross():
    """MA5从上方下穿MA20 → SELL"""
    prices = []
    prices.extend([100] * 25)
    prices.extend([105, 108, 110, 112, 115])  # above
    prices.extend([108, 102, 98, 95, 92])  # drop below → cross at last point
    strat = MAStrategy(["TEST"])
    sig, _ = strat.decide("2026-02-10", "TEST", _custom_series(prices), {})
    assert sig == Signal.SELL, f"Expected SELL, got {sig}"


# ── create_strategy ───────────────────────────────────────────────────

def test_create_strategy_returns_correct_type():
    assert isinstance(create_strategy("momentum", []), MomentumStrategy)
    assert isinstance(create_strategy("rsi", []), RSIStrategy)
    assert isinstance(create_strategy("ma", []), MAStrategy)


def test_create_strategy_unknown_raises():
    with pytest.raises(ValueError):
        create_strategy("unknown", [])


# ── Signal enum ───────────────────────────────────────────────────────

def test_signal_repr():
    assert Signal.BUY.value == "BUY"
    assert Signal.SELL.value == "SELL"
    assert Signal.HOLD.value == "HOLD"
