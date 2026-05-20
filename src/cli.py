"""AI Investor — unified CLI entry point."""

import argparse
import json
import sys
from pathlib import Path

from src.config import (
    DEFAULT_SYMBOLS, INITIAL_CAPITAL, BACKTEST_PERIOD,
    MAX_POSITIONS,
    STRATEGY_PROFILES, load_strategy_profile, save_strategy_profile,
)
from src.data_fetcher import fetch_stock_data
from src.strategy import create_strategy
from src.backtest import run_backtest
from src.live import run_analysis as live_analysis, load_portfolio
from src.scheduler import (
    load_schedule, save_schedule,
    set_time, set_days, set_timezone, describe,
)


# ── helpers ──────────────────────────────────────────────────────────

def _print_header(title: str) -> None:
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


def _print_result(result) -> None:
    """Pretty-print a backtest result."""
    _print_header("📊 回测报告")
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

    if result.history is not None and not result.history.empty:
        days = len(result.history)
        if days > 1 and result.total_return_pct != 0:
            daily = result.total_return_pct / days
            print(f"  ── 按当前表现推算 ──")
            print(f"  日均: {daily:+.2f}%  |  周预估: {daily*5:+.2f}%  |  月预估: {daily*21:+.2f}%  |  年化: {daily*252:+.2f}%")
            print()

    if result.trades:
        print(f"  ── 最近 10 笔交易 ──")
        for t in result.trades[-10:]:
            print(f"  {'📈' if t.action == 'BUY' else '📉'} {t.date} | {t.action:4s} {t.symbol:8s} {t.shares:6.0f}股 @HK${t.price:.2f} | {t.reason}")
        print()


# ── subcommands ──────────────────────────────────────────────────────

def cmd_scan(args) -> None:
    """Run daily live scan."""
    _print_header("📡 AI Investor 每日扫描")
    profile = load_strategy_profile()
    print(f"  策略档案: {profile['name']} ({profile['key']})")

    portfolio = load_portfolio()
    live_analysis(portfolio, verbose=not args.quiet)


def cmd_backtest(args) -> None:
    """Run historical backtest."""
    symbols = args.symbols or DEFAULT_SYMBOLS
    strategy = args.strategy
    period = args.period
    capital = args.capital
    max_positions = args.max_positions

    _print_header("🤖 AI Investor 回测（港股）")
    print(f"  策略: {strategy} | 资金: HK${capital:,.0f} | 周期: {period}")
    print(f"  股票: {', '.join(symbols)}")

    print("\n📡 正在获取市场数据...")
    prices_df = fetch_stock_data(symbols, period=period)
    closes = prices_df.get("Close")
    if closes is None or closes.empty:
        print("❌ 无法获取数据，请检查股票代码或网络")
        sys.exit(1)

    valid = [c for c in closes.columns if closes[c].dropna().shape[0] > 5]
    valid_syms = [s for s in symbols if s in valid]
    if not valid_syms:
        print("❌ 所有股票数据不足")
        sys.exit(1)

    if len(valid_syms) < len(symbols):
        print(f"⚠️  跳过数据不足: {set(symbols) - set(valid_syms)}")

    latest = {s: float(closes[s].dropna().iloc[-1]) for s in valid_syms}
    print(f"  获取到 {len(closes)} 个交易日")
    print("  当前价格:")
    for sym, p in latest.items():
        chg = ((p - closes[sym].dropna().iloc[-2]) / closes[sym].dropna().iloc[-2] * 100) if len(closes[sym].dropna()) >= 2 else 0
        print(f"    {sym:8s}  HK${p:>10.2f}  ({chg:+.2f}%)")

    strat_obj = create_strategy(strategy, valid_syms)
    result = run_backtest(
        prices_df=prices_df,
        strategy=strat_obj,
        initial_capital=capital,
        max_positions=max_positions,
        verbose=not args.quiet,
    )
    _print_result(result)


def cmd_strategy(args) -> None:
    """View or switch strategy profile."""
    if args.set:
        save_strategy_profile(args.set)
        p = load_strategy_profile()
        print(f"✅ 已切换到: {p['name']} ({p['key']})")
        print(f"   {p['desc']}")
        print(f"   仓位: {p['position_size']*100:.0f}% | 止损: {p['stop_loss']*100:.0f}% | 止盈: +{p['take_profit']*100:.0f}%")
        w_desc = ", ".join(f"{k}×{v}" for k, v in p["weights"].items() if v != 0)
        print(f"   权重: {w_desc}")
    elif args.list:
        print(f"\n{'─' * 55}")
        print(f"  {'档案':<15} {'描述'}")
        print(f"  {'─' * 55}")
        for key, p in STRATEGY_PROFILES.items():
            marker = "⭐" if load_strategy_profile()["key"] == key else "  "
            print(f"  {marker} {key:<13s} {p['desc']}")
        print()
    else:
        p = load_strategy_profile()
        print(f"\n  当前策略: {p['name']} ({p['key']})")
        print(f"  描述: {p['desc']}")
        print(f"  仓位: {p['position_size']*100:.0f}% | 止损: {p['stop_loss']*100:.0f}% | 止盈: +{p['take_profit']*100:.0f}%")
        w_desc = ", ".join(f"{k}×{v}" for k, v in p["weights"].items() if v != 0)
        print(f"  权重: {w_desc}")
        print(f"  市场过滤: {'开启' if p['market_filter'] else '关闭'}")
        print(f"  买入阈值: 得分≥{p['min_score']}")
        print()


def cmd_schedule(args) -> None:
    """View or change daily scan schedule."""
    if args.show:
        s = load_schedule()
        print(f"\n  当前扫描时间: {describe(s)}")
        return

    changed = False
    s = load_schedule()

    if args.time:
        set_time(args.time)
        changed = True
    if args.days:
        set_days(args.days)
        changed = True
    if args.tz:
        set_timezone(args.tz)
        changed = True

    if changed:
        s = load_schedule()
        print(f"✅ 扫描时间已更新: {describe(s)}")
    else:
        print(f"  当前扫描时间: {describe(s)}")


# ── main ─────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="investment-bot",
        description="AI Investor — 港股波段交易助手",
    )
    sub = parser.add_subparsers(dest="command", title="命令")

    # scan
    p_scan = sub.add_parser("scan", help="每日技术扫描")
    p_scan.add_argument("--quiet", "-q", action="store_true", help="精简输出")
    p_scan.set_defaults(func=cmd_scan)

    # backtest
    p_bt = sub.add_parser("backtest", help="历史回测")
    p_bt.add_argument("--strategy", "-s", choices=["ma", "rsi", "momentum"], default="momentum")
    p_bt.add_argument("--symbols", nargs="+")
    p_bt.add_argument("--period", "-p", default="1mo")
    p_bt.add_argument("--capital", "-c", type=float, default=INITIAL_CAPITAL)
    p_bt.add_argument("--max-positions", type=int, default=MAX_POSITIONS)
    p_bt.add_argument("--quiet", "-q", action="store_true")
    p_bt.set_defaults(func=cmd_backtest)

    # strategy
    p_st = sub.add_parser("strategy", help="查看/切换策略档案")
    p_st.add_argument("--set", "-s", choices=list(STRATEGY_PROFILES.keys()), help="切换到此策略")
    p_st.add_argument("--list", "-l", action="store_true", help="列出所有策略")
    p_st.set_defaults(func=cmd_strategy)

    # schedule
    p_sc = sub.add_parser("schedule", help="查看/设置每日扫描时间")
    p_sc.add_argument("--show", action="store_true", help="显示当前扫描时间")
    p_sc.add_argument("--time", "-t", metavar="HH:MM", help="扫描时间，如 09:30")
    p_sc.add_argument("--days", "-d", metavar="DAYS", help="扫描日，0=日 1=一...6=六，如 1-5 或 1,3,5")
    p_sc.add_argument("--tz", metavar="TZ", help="时区，如 Asia/Hong_Kong")
    p_sc.set_defaults(func=cmd_schedule)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
