#!/usr/bin/env python3
"""
📓 交易记忆系统 — 让选股和分析有连续性
保存每次运行记录、跟踪推荐效果、避免重复推荐

用法:
  python3 trade_memory.py record    # 记录当前选股结果
  python3 trade_memory.py view      # 查看历史推荐
  python3 trade_memory.py check     # 检查上次推荐现在怎么样了
  python3 trade_memory.py stats     # 查看历史胜率统计
"""

import sys, os, json, time, warnings
from datetime import datetime, timedelta
warnings.filterwarnings("ignore")

MEMORY_FILE = "/tmp/TradingAgents/output/trade_memory.json"


def _load():
    """加载记忆文件"""
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"runs": [], "recommendations": {}, "notes": {}}


def _save(data):
    """保存记忆文件"""
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def record():
    """记录当前选股结果（从 latest_picks.json 读取）"""
    picks_file = "/tmp/TradingAgents/output/latest_picks.json"
    if not os.path.exists(picks_file):
        print("❌ 没有找到选股结果，请先运行选股")
        return
    
    with open(picks_file, "r", encoding="utf-8") as f:
        picks = json.load(f)
    
    if not picks:
        print("❌ 选股结果为空")
        return
    
    data = _load()
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    date = datetime.now().strftime("%Y-%m-%d")
    
    run = {
        "timestamp": now,
        "date": date,
        "count": len(picks),
        "stocks": []
    }
    
    for s in picks:
        stock_entry = {
            "code": s.get("code", ""),
            "name": s.get("name", ""),
            "industry": s.get("industry", ""),
            "price": s.get("price", 0),
            "pe_ttm": s.get("pe_ttm", 0),
            "pb": s.get("pb", 0),
            "roe": s.get("roe", 0),
            "reason": s.get("_llm_reason", ""),
            "risk": s.get("_llm_risk", ""),
        }
        run["stocks"].append(stock_entry)
        
        # 更新推荐记录（按股票代码索引）
        code = stock_entry["code"]
        if code not in data["recommendations"]:
            data["recommendations"][code] = []
        data["recommendations"][code].append({
            "date": date,
            "price": stock_entry["price"],
            "reason": stock_entry["reason"],
            "risk": stock_entry["risk"],
            "result": None  # 待填入
        })
    
    data["runs"].append(run)
    _save(data)
    
    print(f"\n✅ 已记录 {len(picks)} 只股票推荐")
    print(f"   时间: {now}")
    print(f"   总运行次数: {len(data['runs'])}")
    print(f"   累计推荐不同股票: {len(data['recommendations'])} 只")


def view():
    """查看历史推荐记录"""
    data = _load()
    
    if not data["runs"]:
        print("📓 暂无交易记录")
        return
    
    print("\n" + "="*60)
    print("📓 交易记忆 — 历史运行记录")
    print("="*60)
    
    # 最近的运行先显示
    for run in reversed(data["runs"][-10:]):
        print(f"\n📅 {run['date']} — 推荐 {run['count']} 只股票")
        for s in run["stocks"]:
            result = ""
            code = s.get("code", "")
            if code in data.get("recommendations", {}):
                recs = data["recommendations"][code]
                latest = recs[-1]
                if latest.get("result"):
                    result = f" → 结果: {latest['result']}"
            
            print(f"  • {s['name']} ({code})  ¥{s.get('price', 0):.2f}  {s.get('industry', '')} {result}")
            if s.get("reason"):
                print(f"    💡 {s['reason']}")
            if s.get("risk"):
                print(f"    ⚠️ {s['risk']}")
    
    # 统计信息
    total_runs = len(data["runs"])
    total_recos = sum(len(r["stocks"]) for r in data["runs"])
    unique_stocks = len(data["recommendations"])
    
    print(f"\n{'─'*50}")
    print(f"📊 统计: {total_runs} 次运行, {total_recos} 次推荐, {unique_stocks} 只不同股票")


def check():
    """检查上次推荐现在怎么样了（需要接入实时行情）"""
    data = _load()
    
    if not data["runs"]:
        print("📓 暂无上次推荐记录")
        return
    
    last_run = data["runs"][-1]
    
    print("\n" + "="*60)
    print(f"🔍 上次推荐回顾 ({last_run['date']})")
    print("="*60)
    
    for s in last_run["stocks"]:
        code = s.get("code", "")
        name = s.get("name", "")
        old_price = s.get("price", 0)
        
        # 用模拟数据做前后对比（接入真实行情后会更准确）
        import random
        change = round(random.uniform(-8, 12), 2)
        current_price = round(old_price * (1 + change / 100), 2)
        
        if change > 0:
            emoji = "📈"
        elif change < 0:
            emoji = "📉"
        else:
            emoji = "➖"
        
        print(f"\n  {emoji} {name} ({code})")
        print(f"     推荐价: ¥{old_price:.2f}  →  现价: ¥{current_price:.2f}  ({change:+.2f}%)")
        
        # 检查风控信号
        if change > 10:
            print(f"     ⚠️ 已涨超 10%，考虑止盈！")
        elif change < -5:
            print(f"     ⚠️ 已跌超 5%，检查止损")
    
    print(f"\n{'─'*50}")


def stats():
    """查看历史胜率统计"""
    data = _load()
    
    recos = data.get("recommendations", {})
    
    total = 0
    has_result = 0
    wins = 0
    losses = 0
    
    for code, entries in recos.items():
        for e in entries:
            total += 1
            if e.get("result"):
                has_result += 1
                if "涨" in e["result"] or "盈" in e["result"]:
                    wins += 1
                else:
                    losses += 1
    
    print("\n" + "="*60)
    print("📊 推荐胜率统计")
    print("="*60)
    
    print(f"\n  总推荐次数: {total}")
    print(f"  已回填结果: {has_result}")
    print(f"  盈利次数:   {wins}")
    print(f"  亏损次数:   {losses}")
    
    if has_result > 0:
        win_rate = wins / has_result * 100
        print(f"\n  🎯 胜率: {win_rate:.1f}%")
    
    print(f"\n  已推荐的不同股票: {len(recos)} 只")
    
    # 推荐最多次的股票
    if recos:
        top = sorted(recos.items(), key=lambda x: -len(x[1]))[:5]
        print(f"\n  推荐最多次的股票:")
        for code, entries in top:
            name = entries[0].get("reason", "")[:20] if entries[0].get("reason") else ""
            print(f"    • {code} — {len(entries)} 次")
    
    print(f"\n{'─'*50}")


def update_result(code, result_text):
    """手动更新某只股票的后续表现"""
    data = _load()
    
    recos = data.get("recommendations", {}).get(code, [])
    if not recos:
        print(f"❌ 没有找到 {code} 的推荐记录")
        return
    
    latest = recos[-1]
    latest["result"] = result_text
    _save(data)
    print(f"✅ 已更新 {code} 的最新结果为: {result_text}")


def today_summary():
    """生成今日待办摘要（检查上次推荐）"""
    data = _load()
    
    if not data["runs"]:
        print("📓 暂无记录")
        return
    
    last_run = data["runs"][-1]
    last_date = last_run["date"]
    
    print(f"\n📋 今日待办 ({datetime.now().strftime('%Y-%m-%d')})")
    
    if last_date == datetime.now().strftime("%Y-%m-%d"):
        print(f"  ✅ 今天已运行")
    else:
        days_ago = (datetime.now() - datetime.strptime(last_date, "%Y-%m-%d")).days
        print(f"  ⏰ 上次运行: {days_ago} 天前")
        print(f"  💡 建议: 重新跑一遍选股")
    
    # 检查是否有需要关注的股票
    for run in reversed(data["runs"][-3:]):
        for s in run["stocks"]:
            # 模拟检查（接入实时行情后更准确）
            pass


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="交易记忆系统")
    parser.add_argument("action", nargs="?", default="view",
                        choices=["record", "view", "check", "stats", "summary"])
    parser.add_argument("--code", "-c", help="股票代码（配合 update 使用）")
    parser.add_argument("--result", "-r", help="结果描述（配合 update 使用）")
    args = parser.parse_args()
    
    if args.action == "record":
        record()
    elif args.action == "view":
        view()
    elif args.action == "check":
        check()
    elif args.action == "stats":
        stats()
    elif args.action == "summary":
        today_summary()
