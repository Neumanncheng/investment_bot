"""多策略信号扫描"""
from data_fetcher import fetch_stock_data
from strategy import create_strategy, Signal
from config import DEFAULT_SYMBOLS


def run_scan(symbols=None):
    """运行多策略扫描并打印结果。"""
    if symbols is None:
        symbols = DEFAULT_SYMBOLS
    print("📡 获取数据...")
    prices = fetch_stock_data(symbols, period="3mo")
    closes = prices.get("Close")

    strategies = {
        "动量": create_strategy("momentum", symbols),
        "RSI": create_strategy("rsi", symbols),
        "MA": create_strategy("ma", symbols),
    }

    header = f"{'代码':<10} {'价格':>8} {'动量':>6} {'RSI':>6} {'MA':>6}  {'建议':<24}"
    print()
    print(header)
    print("─" * 75)

    for sym in symbols:
        if sym not in closes.columns:
            continue
        series = closes[sym].dropna()
        if len(series) < 30:
            continue

        price = float(series.iloc[-1])
        last_date = str(series.index[-1].date())
        results = {}
        sig_list = []

        for name, strat in strategies.items():
            sig, reason = strat.decide(last_date, sym, prices, {})
            results[name] = sig
            if sig == Signal.BUY:
                sig_list.append("BUY")
            elif sig == Signal.SELL:
                sig_list.append("SELL")
            else:
                sig_list.append("HOLD")

        buy_n = sig_list.count("BUY")
        sell_n = sig_list.count("SELL")

        if buy_n >= 2:
            advice = "🟢 多策略看多"
        elif sell_n >= 2:
            advice = "🔴 多策略看空"
        elif buy_n == sell_n:
            advice = "⚖️ 多空分歧"
        else:
            advice = "⏸️ 观望为主"

        m_icon = "📈" if results["动量"] == Signal.BUY else ("📉" if results["动量"] == Signal.SELL else "⏸️")
        r_icon = "📈" if results["RSI"] == Signal.BUY else ("📉" if results["RSI"] == Signal.SELL else "⏸️")
        a_icon = "📈" if results["MA"] == Signal.BUY else ("📉" if results["MA"] == Signal.SELL else "⏸️")

        line = f"{sym:<10} HK${price:>7.2f} {m_icon:>5} {r_icon:>5} {a_icon:>5}  {advice:<24}"
        print(line)

    print()
    print("动量=过去N日涨幅排名 | RSI=超买超卖 | MA=均线金叉死叉")


if __name__ == "__main__":
    run_scan()
