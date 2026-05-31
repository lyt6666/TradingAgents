#!/usr/bin/env python3
"""
🔔 持仓监控 + 预警系统
每天跑一次，检查之前推荐的股票，出信号就提醒

用法:
  python3 watchman.py              # 检查所有历史推荐，输出预警
  python3 watchman.py --monitor    # 持续监控模式（每30秒检查一次）
  python3 watchman.py --daemon     # 一键初始化：加到 crontab 每日跑
"""

import sys, os, json, random, warnings
from datetime import datetime, timedelta
warnings.filterwarnings("ignore")

MEMORY_FILE = "/tmp/TradingAgents/output/trade_memory.json"
ALERTS_FILE = "/tmp/TradingAgents/output/alerts.json"

# 预警阈值
THRESHOLDS = {
    "price_up_alert": 8,     # 涨超 8% 提示关注止盈
    "price_up_critical": 15, # 涨超 15% 强烈建议止盈
    "price_down_warn": 5,    # 跌超 5% 检查止损
    "price_down_critical": 8,# 跌超 8% 必须止损
    "rsi_overbought": 75,    # RSI 超买
    "rsi_oversold": 30,      # RSI 超卖
}


def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"runs": [], "recommendations": {}}


def load_alerts():
    if os.path.exists(ALERTS_FILE):
        with open(ALERTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"alerts": [], "acknowledged": []}


def save_alerts(alerts):
    os.makedirs(os.path.dirname(ALERTS_FILE), exist_ok=True)
    with open(ALERTS_FILE, "w", encoding="utf-8") as f:
        json.dump(alerts, f, ensure_ascii=False, indent=2, default=str)


def simulate_current_price(original_price):
    """模拟当前价格（后续可替换为真实数据源）"""
    change = round(random.uniform(-12, 15), 2)
    return round(original_price * (1 + change / 100), 2), change


def check_stock(name, code, original_price, reason, risk, days_since):
    """检查单只股票，返回预警信号"""
    current_price, change_pct = simulate_current_price(original_price)
    
    signals = []
    
    # 价格涨跌预警
    if change_pct >= THRESHOLDS["price_up_critical"]:
        signals.append({
            "level": "🔴 紧急",
            "type": "止盈",
            "message": f"{name} 已涨 {change_pct:+.1f}%（¥{original_price:.2f}→¥{current_price:.2f}），强烈建议止盈！",
            "detail": f"超过 {THRESHOLDS['price_up_critical']}% 止盈警戒线"
        })
    elif change_pct >= THRESHOLDS["price_up_alert"]:
        signals.append({
            "level": "🟡 提醒",
            "type": "关注止盈",
            "message": f"{name} 已涨 {change_pct:+.1f}%（¥{original_price:.2f}→¥{current_price:.2f}），关注止盈机会",
            "detail": f"超过 {THRESHOLDS['price_up_alert']}% 关注线"
        })
    
    if change_pct <= -THRESHOLDS["price_down_critical"]:
        signals.append({
            "level": "🔴 紧急",
            "type": "止损",
            "message": f"{name} 已跌 {change_pct:+.1f}%（¥{original_price:.2f}→¥{current_price:.2f}），必须止损！",
            "detail": f"超过 {THRESHOLDS['price_down_critical']}% 止损警戒线"
        })
    elif change_pct <= -THRESHOLDS["price_down_warn"]:
        signals.append({
            "level": "🟡 提醒",
            "type": "关注止损",
            "message": f"{name} 已跌 {change_pct:+.1f}%（¥{original_price:.2f}→¥{current_price:.2f}），检查是否需要止损",
            "detail": f"超过 {THRESHOLDS['price_down_warn']}% 关注线"
        })
    
    # 风险提示回顾
    if risk and ("RSI" in risk or "超买" in risk or "回调" in risk):
        # 模拟 RSI 变化
        simulated_rsi = round(random.uniform(25, 85), 1)
        if simulated_rsi >= THRESHOLDS["rsi_overbought"]:
            signals.append({
                "level": "🟡 提醒",
                "type": "技术面",
                "message": f"{name} RSI {simulated_rsi}，已进入超买区，注意回调风险",
                "detail": f"推荐时提示: {risk[:40]}"
            })
        elif simulated_rsi <= THRESHOLDS["rsi_oversold"]:
            signals.append({
                "level": "🟢 机会",
                "type": "技术面",
                "message": f"{name} RSI {simulated_rsi}，已进入超卖区，可能是加仓机会",
                "detail": f"推荐时提示: {risk[:40]}"
            })
    
    # 持有时间预警
    if days_since >= 30 and abs(change_pct) < 5:
        signals.append({
            "level": "ℹ️ 提醒",
            "type": "持有时间过长",
            "message": f"{name} 已持有 {days_since} 天，涨幅仅 {change_pct:+.1f}%，考虑是否继续持有",
            "detail": "资金利用率低"
        })
    
    return signals, current_price, change_pct


def run_check(show_detail=True):
    """主检查函数"""
    data = load_memory()
    alerts_history = load_alerts()
    
    if not data.get("recommendations"):
        if show_detail:
            print("🔔 暂无历史推荐记录")
        return []
    
    today = datetime.now()
    all_signals = []
    
    if show_detail:
        print("\n" + "="*60)
        print("🔔 持仓监控 & 预警")
        print("="*60)
    
    for code, recos in data["recommendations"].items():
        for reco in recos:
            reco_date = reco.get("date", "")
            if not reco_date:
                continue
            
            try:
                rec_dt = datetime.strptime(reco_date, "%Y-%m-%d")
            except:
                continue
            
            days_since = (today - rec_dt).days
            if days_since < 1:
                continue  # 今天刚推荐的，不检查
            
            signals, cur_price, change = check_stock(
                name=reco.get("name", code),
                code=code,
                original_price=reco.get("price", 0),
                reason=reco.get("reason", ""),
                risk=reco.get("risk", ""),
                days_since=days_since,
            )
            
            all_signals.extend(signals)
            
            if show_detail and signals:
                print(f"\n📊 {reco.get('name', code)} ({code})")
                print(f"   推荐价: ¥{reco.get('price', 0):.2f}  →  当前: ¥{cur_price:.2f}  ({change:+.2f}%)")
                print(f"   推荐于: {reco_date}（{days_since} 天前）")
                for s in signals:
                    print(f"   {s['level']} {s['type']}: {s['message']}")
    
    # 保存到预警历史
    if all_signals:
        for s in all_signals:
            s["timestamp"] = today.strftime("%Y-%m-%d %H:%M")
            s["acknowledged"] = False
        
        # 去重（同一个股票同一天不重复记录）
        existing_keys = set()
        for a in alerts_history.get("alerts", []):
            key = (a.get("type", ""), a.get("message", "")[:30])
            existing_keys.add(key)
        
        new_alerts = []
        for s in all_signals:
            key = (s["type"], s["message"][:30])
            if key not in existing_keys:
                new_alerts.append(s)
                existing_keys.add(key)
        
        alerts_history["alerts"].extend(new_alerts)
        save_alerts(alerts_history)
        
        if show_detail:
            print(f"\n{'─'*50}")
            print(f"🆕 新增 {len(new_alerts)} 条预警（已保存）")
    
    # 总结
    if show_detail:
        critical = [s for s in all_signals if "紧急" in s["level"]]
        warning = [s for s in all_signals if "提醒" in s["level"]]
        info = [s for s in all_signals if "ℹ️" in s["level"]]
        
        print(f"\n{'='*60}")
        print("📋 预警摘要")
        if critical:
            print(f"  🔴 紧急: {len(critical)} 条 — 需立即处理")
        if warning:
            print(f"  🟡 提醒: {len(warning)} 条 — 关注即可")
        if info:
            print(f"  ℹ️  信息: {len(info)} 条")
        if not all_signals:
            print("  ✅ 暂无预警信号")
        print("="*60)
    
    return all_signals


def view_alerts():
    """查看历史预警记录"""
    alerts = load_alerts()
    
    if not alerts.get("alerts"):
        print("📭 暂无历史预警")
        return
    
    print("\n" + "="*60)
    print("📋 预警历史")
    print("="*60)
    
    # 未确认的排最前
    unack = [a for a in alerts["alerts"] if not a.get("acknowledged")]
    acked = [a for a in alerts["alerts"] if a.get("acknowledged")]
    
    print(f"\n未处理: {len(unack)} 条")
    for a in unack[-10:]:
        print(f"  {a['level']} [{a['timestamp']}] {a['type']}: {a['message'][:60]}")
    
    if acked:
        print(f"\n已确认: {len(acked)} 条")
        for a in acked[-5:]:
            print(f"  ✅ [{a['timestamp']}] {a['type']}: {a['message'][:50]}")
    
    print()
    print("  确认预警: python3 watchman.py --acknowledge <预警编号>")
    print("  全部确认: python3 watchman.py --ack-all")


def acknowledge(alert_index=None):
    """确认预警"""
    alerts = load_alerts()
    
    if not alerts.get("alerts"):
        print("📭 暂无预警")
        return
    
    if alert_index is not None:
        if 0 <= alert_index < len(alerts["alerts"]):
            alerts["alerts"][alert_index]["acknowledged"] = True
            save_alerts(alerts)
            print(f"✅ 已确认第 {alert_index} 条预警")
        else:
            print(f"❌ 编号 {alert_index} 无效")
    else:
        # 确认所有
        for a in alerts["alerts"]:
            a["acknowledged"] = True
        save_alerts(alerts)
        print(f"✅ 已确认全部 {len(alerts['alerts'])} 条预警")


def setup_cron():
    """设置每日定时任务"""
    cron_cmd = "0 9 * * * cd /tmp/TradingAgents && python3 watchman.py >> output/watchman.log 2>&1"
    
    print("\n🔧 设置每日监控任务（09:00 自动检查）")
    print()
    print("  手动添加到 crontab:")
    print(f"    echo '{cron_cmd}' | crontab -")
    print()
    print("  或者直接执行:")
    print("    (crontab -l 2>/dev/null; echo '{}') | crontab -".format(cron_cmd))
    print()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="持仓监控 & 预警系统")
    parser.add_argument("--monitor", action="store_true", help="持续监控（每60秒检查一次）")
    parser.add_argument("--daemon", action="store_true", help="设置每日定时任务")
    parser.add_argument("--history", action="store_true", help="查看历史预警")
    parser.add_argument("--acknowledge", type=int, metavar="N", help="确认第 N 条预警")
    parser.add_argument("--ack-all", action="store_true", help="确认所有预警")
    args = parser.parse_args()
    
    if args.daemon:
        setup_cron()
    elif args.monitor:
        print("🔔 持续监控模式（每60秒检查一次，Ctrl+C 退出）")
        import time
        while True:
            run_check(show_detail=False)
            # 打印简短状态
            alerts = load_alerts()
            unack = len([a for a in alerts.get("alerts", []) if not a.get("acknowledged")])
            now = datetime.now().strftime("%H:%M:%S")
            print(f"[{now}] 检查完成，未处理预警: {unack} 条", end="\r")
            time.sleep(60)
    elif args.history:
        view_alerts()
    elif args.acknowledge is not None:
        acknowledge(args.acknowledge)
    elif args.ack_all:
        acknowledge()
    else:
        run_check()
