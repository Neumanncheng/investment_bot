#!/usr/bin/env python3
"""AI Investor — 港股每日实盘分析

用法:
    python3 -m src.live              # 扫描所有默认股票
    python3 -m src.live --buy 0700.HK --shares 200  # 手动买入
    python3 -m src.live --sell 0700.HK              # 手动清仓
    python3 -m src.live --reset                     # 重置账户
"""

import json
import sys
from datetime import datetime
from pathlib import Path

from src.config import DEFAULT_SYMBOLS, INITIAL_CAPITAL, COMMISSION
from src.config import MAX_POSITIONS, POSITION_SIZE, STOP_LOSS, TAKE_PROFIT
from src.config import load_strategy_profile
from src.data_fetcher import fetch_stock_data
from src.portfolio import Portfolio, Position, Trade
from src.strategy import create_strategy, Signal

PORTFOLIO_FILE = Path(__file__).parent / "portfolio_state.json"
SIGNALS_FILE = Path(__file__).parent / "latest_signals.json"


# ═══════════════════════════════════════════════════
# Portfolio 持久化
# ═══════════════════════════════════════════════════

def load_portfolio() -> Portfolio:
    if PORTFOLIO_FILE.exists():
        with open(PORTFOLIO_FILE, encoding="utf-8-sig") as f:
            data = json.load(f)
        p = Portfolio(data["initial_capital"], data.get("commission", COMMISSION))
        p.cash = data["cash"]
        for sym, pos_data in data.get("positions", {}).items():
            p.positions[sym] = Position(sym, pos_data["shares"], pos_data["avg_cost"])
        for t in data.get("trades", []):
            p.trades.append(Trade(**t))
        return p
    return Portfolio(INITIAL_CAPITAL, COMMISSION)


def save_portfolio(p: Portfolio):
    data = {
        "initial_capital": p.initial_capital,
        "commission": p.commission,
        "cash": p.cash,
        "positions": {
            sym: {"shares": pos.shares, "avg_cost": pos.avg_cost}
            for sym, pos in p.positions.items()
        },
        "trades": [
            {"date": t.date, "symbol": t.symbol, "action": t.action,
             "shares": t.shares, "price": t.price, "value": t.value,
             "reason": t.reason}
            for t in p.trades[-100:]
        ],
        "last_updated": datetime.now().isoformat(),
    }
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ═══════════════════════════════════════════════════
# 分析引擎
# ═══════════════════════════════════════════════════

def run_analysis(portfolio: Portfolio, verbose: bool = True):
    """Run full daily analysis and return signals + report."""

    # 加载策略档案
    profile = load_strategy_profile()
    weights = profile["weights"]
    market_filter = profile["market_filter"]
    min_score = profile["min_score"]

    # 确定要追踪的股票
    symbols = set(DEFAULT_SYMBOLS)
    for sym in portfolio.positions:
        symbols.add(sym)
    symbols = sorted(symbols)

    # 获取行情
    if verbose:
        print(f"📡 获取行情... ({len(symbols)} 只)")
    prices = fetch_stock_data(symbols, period="3mo")
    closes = prices.get("Close")

    # 最新价
    latest_prices = {}
    for sym in symbols:
        if sym in closes.columns:
            s = closes[sym].dropna()
            if not s.empty:
                latest_prices[sym] = float(s.iloc[-1])

    # ── 当前持仓 ──
    total_value = portfolio.cash
    if verbose:
        print()
        print("═" * 60)
        print(f"💰 账户总览  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("═" * 60)
        print(f"  初始资金:  HK${portfolio.initial_capital:,.0f}")
        print(f"  可用现金:  HK${portfolio.cash:,.0f}")

    if portfolio.positions:
        stock_val = 0
        if verbose:
            print(f"\n  📊 当前持仓:")
        for sym, pos in list(portfolio.positions.items()):
            price = latest_prices.get(sym)
            if price:
                value = pos.shares * price
                pnl_pct = (price - pos.avg_cost) / pos.avg_cost * 100
                stock_val += value
                emoji = "🟢" if pnl_pct >= 0 else "🔴"
                if verbose:
                    print(f"  {emoji} {sym:10s} {pos.shares:6.0f}股  "
                          f"成本 HK${pos.avg_cost:.2f}  现价 HK${price:.2f}  "
                          f"盈亏 {pnl_pct:+.1f}%  (HK${value - pos.shares*pos.avg_cost:+,.0f})")
            elif verbose:
                print(f"  ❓ {sym:10s} {pos.shares:6.0f}股  成本 HK${pos.avg_cost:.2f}  (无行情)")

        total_value += stock_val
    else:
        stock_val = 0
        if verbose:
            print(f"\n  (空仓)")

    pnl = total_value - portfolio.initial_capital
    pnl_pct = pnl / portfolio.initial_capital * 100
    if verbose:
        print(f"  {'─' * 55}")
        print(f"  总资产: HK${total_value:,.0f}  |  累计: {pnl:+,.0f} ({pnl_pct:+.2f}%)")

    # ── 策略档案 ──
    if verbose:
        w_desc = ", ".join(
            f"{k}×{v}" for k, v in weights.items() if v != 0
        ) or "无权重"
        print(f"\n  📋 策略档案: {profile['name']} ({profile['key']})")
        print(f"     权重: {w_desc}  |  仓位: {profile['position_size']*100:.0f}%  |  "
              f"止损: {profile['stop_loss']*100:.0f}%  |  止盈: +{profile['take_profit']*100:.0f}%")

    # ── 市场环境过滤 ──
    hsi_bearish = False
    if market_filter:
        try:
            hsi = fetch_stock_data(["^HSI"], period="3mo")
            hsi_close = hsi.get("Close")
            if hsi_close is not None and not hsi_close.empty:
                hsi_series = hsi_close["^HSI"].dropna()
                if len(hsi_series) >= 20:
                    hsi_ma20 = float(hsi_series.rolling(20).mean().iloc[-1])
                    hsi_now = float(hsi_series.iloc[-1])
                    hsi_bearish = hsi_now < hsi_ma20
                    if verbose:
                        tag = "🔴 恒指弱于MA20 — 买入信号将降级" if hsi_bearish else "🟢 恒指强于MA20"
                        print(f"  🏛️ 市场环境: 恒指 HK${hsi_now:,.0f} (MA20: {hsi_ma20:,.0f})  {tag}")
        except Exception as e:
            if verbose:
                print(f"  ⚠️ 获取恒指数据失败: {e}")

    # ── 多策略打分 ──
    strategies = {
        "动量": create_strategy("momentum", symbols),
        "RSI": create_strategy("rsi", symbols),
        "MA": create_strategy("ma", symbols),
    }
    last_date = str(closes.index[-1].date())

    # 计算最大可得分（用于比例判断）
    max_buy = sum(max(w, 0) for w in weights.values())
    max_sell = sum(max(-w, 0) for w in weights.values())

    if verbose:
        print(f"\n🎯 多策略信号扫描  |  日期: {last_date}")
        print(f"  {'代码':<10} {'价格':>8}  动量  RSI   MA   共识   判断")
        print(f"  {'─' * 58}")

    all_signals = []

    for sym in symbols:
        if sym not in closes.columns:
            continue
        s = closes[sym].dropna()
        if len(s) < 30:
            continue

        price = float(s.iloc[-1])
        weighted_buy = weighted_sell = 0
        display = {"BUY": 0, "SELL": 0, "HOLD": 0}
        reasons = []

        portfolio_snapshot = {
            "positions": {s: p.shares for s, p in portfolio.positions.items()},
            "cash": portfolio.cash}
        for name, strat in strategies.items():
            sig, reason = strat.decide(last_date, sym, prices, portfolio_snapshot)
            display[sig.name] += 1
            w = weights.get(name, 0)
            if w > 0:
                if sig == Signal.BUY:
                    weighted_buy += w
                elif sig == Signal.SELL:
                    weighted_sell += w
            elif w < 0:
                # 负权重：反转信号
                if sig == Signal.BUY:
                    weighted_sell += abs(w)
                elif sig == Signal.SELL:
                    weighted_buy += abs(w)
            # w == 0: 跳过该策略

            if sig != Signal.HOLD and reason:
                reasons.append(f"[{name}] {reason}")

        score = weighted_buy - weighted_sell
        max_abs = max(max_buy, max_sell, 1)

        # 市场环境降级
        if hsi_bearish and score > 0:
            score = max(0, score - max_abs * 0.5)
            reasons.append("[市场] 恒指弱势，信号降级")

        # 共识判断
        if max_abs > 0:
            ratio = score / max_abs
            if ratio >= 0.5:
                verdict = "🟢 看多"
            elif ratio >= 0.25:
                verdict = "🟡 偏多"
            elif ratio > -0.25:
                verdict = "⚖️ 观望"
            elif ratio > -0.5:
                verdict = "🟠 偏空"
            else:
                verdict = "🔴 看空"
        else:
            verdict = "⚖️ 无效"

        m = "📈" if score > 0 else ("📉" if score < 0 else "⏸️")
        b, s_c, h = display["BUY"], display["SELL"], display["HOLD"]

        if verbose:
            print(f"  {m} {sym:<8s} HK${price:>7.2f}  {b}/{s_c}/{h}  [{score:+d}]  {verdict}")

        all_signals.append({
            "symbol": sym,
            "price": price,
            "score": score,
            "buy": b, "sell": s_c, "hold": h,
            "verdict": verdict,
            "reasons": reasons,
            "in_portfolio": sym in portfolio.positions,
        })

    # ── 风控检查 ──
    alerts = []
    if portfolio.positions and verbose:
        stop_loss_line = profile["stop_loss"]
        take_profit_line = profile["take_profit"]
        print(f"\n⚠️ 持仓风控 (策略: {profile['name']}):")
        has_alert = False
        for sym, pos in list(portfolio.positions.items()):
            price = latest_prices.get(sym)
            if price:
                pnl_pct = (price - pos.avg_cost) / pos.avg_cost
                if pnl_pct <= stop_loss_line:
                    print(f"   🔴 {sym}: 触发止损线! 浮亏 {pnl_pct*100:.1f}% (止损: {stop_loss_line*100:.0f}%)")
                    alerts.append({"type": "stop_loss", "symbol": sym, "pnl_pct": pnl_pct*100})
                    has_alert = True
                elif pnl_pct >= take_profit_line:
                    print(f"   🟢 {sym}: 触发止盈线! 浮盈 +{pnl_pct*100:.1f}% (止盈: +{take_profit_line*100:.0f}%)")
                    alerts.append({"type": "take_profit", "symbol": sym, "pnl_pct": pnl_pct*100})
                    has_alert = True
                elif pnl_pct <= stop_loss_line * 0.7:
                    print(f"   🟠 {sym}: 接近止损 浮亏 {pnl_pct*100:.1f}%")
                    alerts.append({"type": "near_stop", "symbol": sym, "pnl_pct": pnl_pct*100})
                    has_alert = True
        if not has_alert:
            print(f"   ✅ 无预警")

    # ── 操作建议 ──
    if verbose:
        ranked = sorted(all_signals, key=lambda x: x["score"], reverse=True)
        # 计算加权后的有效阈值
        effective_max = max(max_buy, max_sell, 1)
        buy_threshold = effective_max * 0.5    # 得分 ≥ 最大分的50%
        sell_threshold = -effective_max * 0.5  # 得分 ≤ 最大分的-50%

        print(f"\n📋 操作建议 (买入阈值: 得分≥{buy_threshold:.0f}):")

        buys = [s for s in ranked if s["score"] >= buy_threshold]
        sells = [s for s in ranked if s["score"] <= sell_threshold]

        if buys:
            print(f"   🟢 看多信号:")
            for s in buys:
                tag = " (已持有)" if s["in_portfolio"] else ""
                reasons_str = ', '.join(s['reasons'][:2]) if s['reasons'] else "—"
                print(f"      {s['symbol']:10s} HK${s['price']:.2f}{tag}  |  {reasons_str}")
        else:
            print(f"   (无买入信号)")

        if sells:
            print(f"   🔴 看空信号:")
            for s in sells:
                tag = " ⚡持有!" if s["in_portfolio"] else " (未持有)"
                reasons_str = ', '.join(s['reasons'][:2]) if s['reasons'] else "—"
                print(f"      {s['symbol']:10s} HK${s['price']:.2f}{tag}  |  {reasons_str}")
        else:
            print(f"   (无卖出信号)")

        print()
        print("  💡 以上为技术信号，最终决策需结合新闻+基本面。")
        print("  💡 执行交易: python3 -m src.live --buy/sell <代码>")

    # 保存信号供 agent 读取
    with open(SIGNALS_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "date": last_date,
            "total_value": round(total_value, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "alerts": alerts,
            "signals": all_signals,
        }, f, indent=2, ensure_ascii=False)

    return all_signals, alerts


# ═══════════════════════════════════════════════════
# 交易执行
# ═══════════════════════════════════════════════════

def execute_trade(action: str, symbol: str, shares: float = None):
    """执行单笔交易并保存"""
    portfolio = load_portfolio()

    # 获取当前价
    prices = fetch_stock_data([symbol], period="5d")
    closes = prices.get("Close")
    if symbol not in closes.columns or closes[symbol].dropna().empty:
        print(f"❌ 无法获取 {symbol} 行情")
        return

    price = float(closes[symbol].dropna().iloc[-1])
    today = datetime.now().strftime("%Y-%m-%d")

    if action == "buy":
        if shares is None:
            # 默认用 POSITION_SIZE 算股数
            max_cost = portfolio.cash * POSITION_SIZE
            shares = max_cost / (price * (1 + COMMISSION))

        # 港股一手规则提示（不强制执行）
        board_lot_hint = get_board_lot(symbol)
        if board_lot_hint and shares < board_lot_hint:
            print(f"⚠️ 港股 {symbol} 每手 {board_lot_hint} 股，当前 {shares:.0f} 股可能无法成交")

        success = portfolio.buy(today, symbol, price, shares, "手动买入")
        if success:
            print(f"✅ 买入 {symbol}: {shares:.0f}股 @HK${price:.2f}")
            print(f"   金额: HK${shares * price:,.0f} | 手续费: HK${shares * price * COMMISSION:,.0f}")
            print(f"   剩余现金: HK${portfolio.cash:,.0f}")
        else:
            print(f"❌ 买入失败: 资金不足 (需要 HK${shares * price * (1+COMMISSION):,.0f})")

    elif action == "sell":
        if symbol not in portfolio.positions:
            print(f"❌ 未持有 {symbol}")
            return

        pos = portfolio.positions[symbol]
        if shares is None:
            shares = pos.shares

        success = portfolio.sell(today, symbol, price, shares, "手动卖出")
        if success:
            pnl = (price - pos.avg_cost) * shares
            print(f"✅ 卖出 {symbol}: {shares:.0f}股 @HK${price:.2f}")
            print(f"   盈亏: HK${pnl:+,.0f} ({(price/pos.avg_cost-1)*100:+.1f}%)")
            print(f"   现金余额: HK${portfolio.cash:,.0f}")
        else:
            print(f"❌ 卖出失败")

    save_portfolio(portfolio)


def get_board_lot(symbol: str) -> int:
    """港股每手股数（常见股票）"""
    lot_map = {
        "0700.HK": 100, "9988.HK": 100, "3690.HK": 100, "9618.HK": 50,
        "9999.HK": 100, "1810.HK": 200, "9888.HK": 50, "1024.HK": 100,
        "2015.HK": 100, "9868.HK": 100, "1211.HK": 500, "0175.HK": 1000,
        "2333.HK": 500, "0388.HK": 100, "1299.HK": 200, "0005.HK": 400,
        "2269.HK": 500, "2020.HK": 200, "6862.HK": 1000, "2800.HK": 500,
    }
    return lot_map.get(symbol, 100)


# ═══════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════

def parse_args():
    """简易参数解析"""
    args = {"action": "scan", "symbol": None, "shares": None}
    i = 1
    while i < len(sys.argv):
        a = sys.argv[i]
        if a == "--reset":
            args["action"] = "reset"
        elif a == "--buy":
            args["action"] = "buy"
            if i + 1 < len(sys.argv) and not sys.argv[i+1].startswith("--"):
                args["symbol"] = sys.argv[i+1]
                i += 1
        elif a == "--sell":
            args["action"] = "sell"
            if i + 1 < len(sys.argv) and not sys.argv[i+1].startswith("--"):
                args["symbol"] = sys.argv[i+1]
                i += 1
        elif a == "--shares":
            if i + 1 < len(sys.argv):
                args["shares"] = float(sys.argv[i+1])
                i += 1
        i += 1
    return args


if __name__ == "__main__":
    args = parse_args()

    if args["action"] == "reset":
        PORTFOLIO_FILE.unlink(missing_ok=True)
        SIGNALS_FILE.unlink(missing_ok=True)
        print("✅ 账户已重置 — 回到 HK$1,000,000")
    elif args["action"] == "buy":
        if not args["symbol"]:
            print("❌ 用法: python3 -m src.live --buy <代码> [--shares <股数>]")
        else:
            execute_trade("buy", args["symbol"], args["shares"])
    elif args["action"] == "sell":
        if not args["symbol"]:
            print("❌ 用法: python3 -m src.live --sell <代码> [--shares <股数>]")
        else:
            execute_trade("sell", args["symbol"], args["shares"])
    else:
        portfolio = load_portfolio()
        run_analysis(portfolio)
