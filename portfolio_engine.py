#!/usr/bin/env python3
"""
📊 组合策略引擎 — 对选股结果做整体仓位配置和风控
用法: python3 portfolio_engine.py [--file picks.json]
"""

import sys, os, json, textwrap, warnings
warnings.filterwarnings("ignore")

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")


def build_portfolio_strategy(picks):
    """根据选股组合，生成整体配置策略"""
    
    if not picks:
        print("❌ 没有选股结果，无法生成策略")
        return
    
    # 提取关键信息
    total = len(picks)
    
    # 统计行业分布
    industries = {}
    for s in picks:
        ind = s.get("industry", "其他")
        industries[ind] = industries.get(ind, 0) + 1
    
    # 计算组合平均指标
    avg_pe = sum(s.get("pe_ttm", 20) for s in picks) / total
    avg_pb = sum(s.get("pb", 2) for s in picks) / total
    avg_roe = sum(s.get("roe", 10) for s in picks) / total
    
    # 评估整体风格
    avg_momentum = sum(s.get("change_20d", 0) for s in picks) / total
    avg_volume = sum(s.get("volume_ratio", 1) for s in picks) / total
    
    print("\n" + "="*60)
    print("📊 组合策略分析")
    print("="*60)
    
    print(f"\n📋 组合概况")
    print(f"  股票数量: {total} 只")
    print(f"  平均 PE:  {avg_pe:.1f}")
    print(f"  平均 PB:  {avg_pb:.2f}")
    print(f"  平均 ROE: {avg_roe:.1f}%")
    print(f"  平均 20日涨幅: {avg_momentum:+.1f}%")
    print(f"  平均量比: {avg_volume:.2f}")
    
    print(f"\n🏭 行业分布:")
    for ind, cnt in sorted(industries.items(), key=lambda x: -x[1]):
        bar = "█" * cnt
        print(f"  {ind:<10} {bar} {cnt}只")
    
    # 判断组合风格
    style = ""
    if avg_pe < 15 and avg_roe > 12:
        style = "价值型"
    elif avg_momentum > 8 and avg_volume > 2:
        style = "动量型"
    elif avg_momentum < -5:
        style = "超跌反弹型"
    else:
        style = "均衡型"
    
    print(f"\n🎯 组合风格: {style}")
    
    # 用 LLM 生成策略
    if DEEPSEEK_API_KEY:
        strategy = llm_portfolio_strategy(picks, style)
    else:
        strategy = rule_based_strategy(picks, style)
    
    print(f"\n{strategy}")
    print("="*60)
    print()
    
    return strategy


def rule_based_strategy(picks, style):
    """基于规则的组合配置（不调 API 的兜底方案）"""
    total = len(picks)
    
    lines = []
    lines.append("📌 建议配置方案")
    lines.append("")
    
    # 仓位分配
    if style == "价值型":
        lines.append("  💰 仓位建议: 70%-80%（价值股波动小，可重仓）")
        lines.append("  📅 持有周期: 中长期（1-3个月）")
        lines.append("  🎯 止损线: -8%（基本面好，容忍度高）")
    elif style == "动量型":
        lines.append("  💰 仓位建议: 50%-65%（动量股追高需谨慎）")
        lines.append("  📅 持有周期: 中短线（1-4周）")
        lines.append("  🎯 止损线: -5%（趋势破位必须走）")
    elif style == "超跌反弹型":
        lines.append("  💰 仓位建议: 30%-50%（反弹不确定性强）")
        lines.append("  📅 持有周期: 短线（3-10天）")
        lines.append("  🎯 止损线: -3%（抄底必须严格止损）")
    else:
        lines.append("  💰 仓位建议: 50%-70%")
        lines.append("  📅 持有周期: 中短线（2-6周）")
        lines.append("  🎯 止损线: -5%")
    
    lines.append("")
    lines.append("  📊 仓位分配建议:")
    
    # 等权重
    base_pct = round(100 / total, 1)
    for i, s in enumerate(picks, 1):
        # 基本面好的稍微多配
        bonus = 0
        if s.get("pe_ttm", 20) > 0 and s.get("pe_ttm", 999) < 20:
            bonus += 2
        if s.get("roe", 0) > 15:
            bonus += 2
        if s.get("volume_ratio", 1) > 2:
            bonus += 1
        
        weight = round(base_pct + bonus, 1)
        lines.append(f"    {i}. {s['name']} ({s.get('code','')}) — {weight}%")
    
    lines.append("")
    lines.append("  ⚠️ 风控规则:")
    lines.append("    • 单只股票最大仓位不超过 25%")
    lines.append("    • 同一行业不超过 2 只（防行业风险集中）")
    lines.append("    • 总仓位+现金 = 100%")
    lines.append("    • 大盘暴跌（-3%+）时减半仓")
    
    return "\n".join(lines)


def llm_portfolio_strategy(picks, style):
    """用 DeepSeek 生成组合策略"""
    from openai import OpenAI
    
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    
    candidates = []
    for s in picks:
        candidates.append({
            "code": s.get("code", ""),
            "name": s.get("name", ""),
            "industry": s.get("industry", ""),
            "price": s.get("price", 0),
            "pe_ttm": s.get("pe_ttm", 0),
            "pb": s.get("pb", 0),
            "roe": s.get("roe", 0),
            "market_cap": s.get("market_cap", 0),
            "change_pct": s.get("change_pct", 0),
            "volume_ratio": s.get("volume_ratio", 0),
            "rsi": s.get("rsi", 50),
            "change_20d": s.get("change_20d", 0),
            "reason": s.get("_llm_reason", ""),
            "risk": s.get("_llm_risk", ""),
        })
    
    prompt = f"""你是一个专业的 A 股量化投资组合经理。请为以下选股结果制定一个完整的组合配置方案。

组合风格：{style}

候选股票：
{json.dumps(candidates, ensure_ascii=False, indent=2)}

请返回完整的策略方案，格式如下：

📌 组合配置方案

**总体仓位建议：**
- 建议总仓位: XX%-XX%
- 持有周期: 
- 风险等级:

**仓位分配（每只股票建议比例及原因）：**
1. 股票名 (代码) — XX% — 原因（一句话）
2. ...

**行业分散度检查：**
- 是否存在行业集中风险？
- 是否需要调整？

**风控规则：**
1. 止损线：
2. 止盈线：
3. 特殊情况处理（大盘暴跌、突发利空等）：

**操作建议：**
- 建仓节奏（一次性还是分批）：
- 加仓条件：
- 减仓条件：
"""
    
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=2000,
    )
    
    return "\n" + resp.choices[0].message.content


# ===== 命令行入口 =====
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="组合策略引擎")
    parser.add_argument("--file", "-f", help="从 JSON 文件读取选股结果")
    parser.add_argument("--picks", "-p", help="直接传 JSON 字符串")
    args = parser.parse_args()
    
    picks = []
    if args.file:
        with open(args.file) as f:
            picks = json.load(f)
    elif args.picks:
        picks = json.loads(args.picks)
    
    if not picks:
        # 测试数据
        print("⚠️ 没有传入选股结果，使用测试数据演示")
        picks = [
            {"name": "药明康德", "code": "603259", "industry": "医药生物", 
             "price": 191.82, "pe_ttm": 53.2, "pb": 2.48, "roe": 10.0, 
             "change_pct": 7.69, "volume_ratio": 3.96, "rsi": 37.9, 
             "change_20d": 6.4, "market_cap": 195,
             "_llm_reason": "放量突破，RSI低位", "_llm_risk": "PE偏高"},
            {"name": "金山办公", "code": "688111", "industry": "软件",
             "price": 199.86, "pe_ttm": 49.6, "pb": 2.50, "roe": 18.6,
             "change_pct": 7.08, "volume_ratio": 3.91, "rsi": 33.3,
             "change_20d": 0.4, "market_cap": 126,
             "_llm_reason": "软件龙头放量", "_llm_risk": "估值偏高"},
            {"name": "中信证券", "code": "600030", "industry": "券商",
             "price": 224.82, "pe_ttm": 41.7, "pb": 7.91, "roe": 12.9,
             "change_pct": 7.37, "volume_ratio": 2.87, "rsi": 63.2,
             "change_20d": 15.2, "market_cap": 951,
             "_llm_reason": "券商龙头放量突破", "_llm_risk": "短期涨幅较大"},
        ]
    
    build_portfolio_strategy(picks)
