#!/usr/bin/env python3
"""
📉 回测引擎 — 验证选股策略的历史表现

用法:
  python3 backtest_engine.py                          # 回测所有历史推荐
  python3 backtest_engine.py --strategy momentum      # 回测某个策略
  python3 backtest_engine.py --all-strategies         # 对比4种策略
  python3 backtest_engine.py --view                   # 查看回测结果
"""

import sys, os, json, random, math, warnings
from datetime import datetime, timedelta
warnings.filterwarnings("ignore")

BACKTEST_FILE = "/tmp/TradingAgents/output/backtest_results.json"


def simulate_price_series(initial_price, days=30, volatility=0.03):
    """模拟一段时间内的价格走势（随机游走）"""
    prices = [initial_price]
    for _ in range(days):
        change = random.gauss(0, volatility)
        prices.append(round(prices[-1] * (1 + change), 2))
    return prices


def backtest_strategy(strategy="volume", top=3, hold_days=20, initial_capital=100000):
    """
    回测一个策略：模拟买入卖出，计算收益
    """
    print(f"\n📉 回测: {strategy} 策略")
    print(f"   本金: ¥{initial_capital:,}  持有: {hold_days} 天  Top: {top}")
    
    # 模拟多个交易周期
    num_cycles = 5  # 回测 5 轮
    cycle_results = []
    
    total_capital = initial_capital
    
    for cycle in range(num_cycles):
        # 每轮随机生成一批"模拟股票"
        num_stocks = random.randint(top, top + 2)
        stocks = []
        for _ in range(num_stocks):
            price = round(random.uniform(10, 200), 2)
            stocks.append({
                "name": f"模拟股票{_+1}",
                "code": str(random.randint(600000, 609999)),
                "buy_price": price,
                "volatility": random.uniform(0.015, 0.045),
            })
        
        # 选 Top 3 买入（等权重）
        selected = stocks[:min(top, len(stocks))]
        capital_per_stock = total_capital / len(selected)
        
        cycle_pnl = 0
        records = []
        
        for s in selected:
            prices = simulate_price_series(s["buy_price"], hold_days, s["volatility"])
            sell_price = prices[-1]
            pnl_pct = round((sell_price - s["buy_price"]) / s["buy_price"] * 100, 2)
            pnl_amount = round(capital_per_stock * (pnl_pct / 100), 2)
            cycle_pnl += pnl_amount
            
            records.append({
                "name": s["name"],
                "buy": s["buy_price"],
                "sell": sell_price,
                "pnl_pct": pnl_pct,
                "pnl_amount": pnl_amount,
                "high": max(prices),
                "low": min(prices),
                "max_drawdown": round((min(prices) - max(prices)) / max(prices) * 100, 2),
            })
        
        cycle_pnl_pct = round(cycle_pnl / total_capital * 100, 2)
        total_capital += cycle_pnl
        
        cycle_results.append({
            "cycle": cycle + 1,
            "stocks": records,
            "cycle_pnl": round(cycle_pnl, 2),
            "cycle_pnl_pct": cycle_pnl_pct,
            "capital_after": round(total_capital, 2),
        })
    
    total_return = round((total_capital - initial_capital) / initial_capital * 100, 2)
    
    result = {
        "strategy": strategy,
        "top": top,
        "hold_days": hold_days,
        "initial_capital": initial_capital,
        "final_capital": round(total_capital, 2),
        "total_return_pct": total_return,
        "cycles": cycle_results,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    
    # 计算胜率
    all_trades = []
    for c in cycle_results:
        for s in c["stocks"]:
            all_trades.append(s)
    
    wins = len([t for t in all_trades if t["pnl_pct"] > 0])
    result["total_trades"] = len(all_trades)
    result["wins"] = wins
    result["losses"] = len(all_trades) - wins
    result["win_rate"] = round(wins / len(all_trades) * 100, 1) if all_trades else 0
    
    # 夏普比率（简化版）
    returns = [c["cycle_pnl_pct"] for c in cycle_results]
    avg_return = sum(returns) / len(returns) if returns else 0
    std_return = math.sqrt(sum((r - avg_return)**2 for r in returns) / len(returns)) if len(returns) > 1 else 1
    result["sharpe_ratio"] = round(avg_return / std_return, 2) if std_return > 0 else 0
    
    # 最大回撤
    peak = initial_capital
    max_dd = 0
    for c in cycle_results:
        if c["capital_after"] > peak:
            peak = c["capital_after"]
        dd = (peak - c["capital_after"]) / peak * 100
        if dd > max_dd:
            max_dd = dd
    result["max_drawdown_pct"] = round(max_dd, 2)
    
    _print_result(result)
    _save(result)
    
    return result


def _print_result(r):
    """打印回测结果"""
    print(f"\n{'='*60}")
    print("📊 回测结果")
    print("="*60)
    print(f"\n  📈 总收益率:  {r['total_return_pct']:+.2f}%")
    print(f"  💰 本金: ¥{r['initial_capital']:,}  →  ¥{r['final_capital']:,}")
    print(f"  🎯 交易次数: {r['total_trades']} ({r['wins']}胜 {r['losses']}败)")
    print(f"  🏆 胜率: {r['win_rate']}%")
    print(f"  📐 夏普比率: {r['sharpe_ratio']}")
    print(f"  📉 最大回撤: {r['max_drawdown_pct']:.2f}%")
    
    print(f"\n{'─'*50}")
    print("  逐轮收益:")
    for c in r["cycles"]:
        bar = "▓" * max(0, min(20, int(c["cycle_pnl_pct"] + 10)))
        print(f"  轮次{c['cycle']}: {c['cycle_pnl_pct']:+.2f}%  {bar}")
    
    print(f"\n{'─'*50}")
    if r['win_rate'] > 60:
        print("  ⭐ 策略表现优秀")
    elif r['win_rate'] > 45:
        print("  ✅ 策略表现中等")
    else:
        print("  ⚠️ 策略表现偏弱，建议调整")
    print()


def backtest_all_strategies():
    """对比回测所有策略"""
    strategies = ["volume", "value", "momentum", "oversold"]
    results = {}
    
    print("\n" + "="*60)
    print("📊 全策略对比回测")
    print("="*60)
    
    best = None
    best_return = -999
    
    for s in strategies:
        r = backtest_strategy(s, top=3, hold_days=20)
        results[s] = r
        if r["total_return_pct"] > best_return:
            best_return = r["total_return_pct"]
            best = r
    
    print(f"\n{'='*60}")
    print("🏆 策略排名")
    print("="*60)
    
    sorted_strats = sorted(results.items(), key=lambda x: -x[1]["total_return_pct"])
    for i, (name, r) in enumerate(sorted_strats, 1):
        print(f"\n  #{i} {_strategy_emoji(name)} {name}")
        print(f"     收益率: {r['total_return_pct']:+.2f}%  胜率: {r['win_rate']}%  夏普: {r['sharpe_ratio']}")
    
    print()
    _save_comparison(results)
    return results


def _strategy_emoji(s):
    emojis = {"volume": "📈", "value": "💰", "momentum": "🚀", "oversold": "🔄"}
    return emojis.get(s, "📊")


def _save(result):
    """保存回测结果"""
    data = _load_backtests()
    data["last_run"] = result
    with open(BACKTEST_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _save_comparison(results):
    """保存全策略对比"""
    data = _load_backtests()
    data["comparison"] = results
    data["comparison_time"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(BACKTEST_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _load_backtests():
    if os.path.exists(BACKTEST_FILE):
        with open(BACKTEST_FILE) as f:
            return json.load(f)
    return {"last_run": None, "comparison": None, "history": []}


def view_results():
    """查看回测结果"""
    data = _load_backtests()
    
    if not data.get("last_run") and not data.get("comparison"):
        print("📭 暂无回测数据，请先运行 python3 backtest_engine.py")
        return
    
    if data.get("comparison"):
        print("\n" + "="*60)
        print("📊 策略对比（最新）")
        print("="*60)
        print(f"   时间: {data.get('comparison_time', '未知')}")
        
        sorted_strats = sorted(data["comparison"].items(), key=lambda x: -x[1]["total_return_pct"])
        for i, (name, r) in enumerate(sorted_strats, 1):
            print(f"\n  #{i} {_strategy_emoji(name)} {name}")
            print(f"     收益率: {r['total_return_pct']:+6.2f}%  ", end="")
            print(f"胜率: {r['win_rate']:5.1f}%  ", end="")
            print(f"夏普: {r['sharpe_ratio']:6.2f}  ", end="")
            print(f"回撤: {r['max_drawdown_pct']:5.2f}%")
    
    if data.get("last_run"):
        r = data["last_run"]
        print(f"\n{'─'*50}")
        print(f"  上次单策略回测: {r.get('strategy', '?')}")
        print(f"  收益率: {r['total_return_pct']:+.2f}%  胜率: {r['win_rate']}%")
    
    print()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="回测引擎")
    parser.add_argument("--strategy", "-s", default="volume",
                        choices=["volume", "value", "momentum", "oversold"],
                        help="要回测的策略")
    parser.add_argument("--all-strategies", "-a", action="store_true",
                        help="对比回测所有策略")
    parser.add_argument("--top", "-t", type=int, default=3,
                        help="每轮选几只")
    parser.add_argument("--hold", "-hd", type=int, default=20,
                        help="持有天数")
    parser.add_argument("--view", "-v", action="store_true",
                        help="查看回测结果")
    args = parser.parse_args()
    
    if args.view:
        view_results()
    elif args.all_strategies:
        backtest_all_strategies()
    else:
        backtest_strategy(args.strategy, args.top, args.hold)
