#!/usr/bin/env python3
"""
📡 A股情报搜集 Agent — 整合各类信息源，提供多维度市场快照
用于 Pipeline 第二段：选股后搜集相关情报
"""

import sys, os, json, warnings, random, textwrap
from datetime import datetime
warnings.filterwarnings("ignore")

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")


def research_stocks(picks):
    """对选中的股票搜集情报"""
    if not picks:
        return []
    
    results = []
    
    for s in picks:
        name = s.get("name", "")
        code = s.get("code", "")
        industry = s.get("industry", "")
        
        print(f"\n📡 搜集 {name} ({code}) 情报...")
        
        info = {
            "code": code,
            "name": name,
            "industry": industry,
            "policy_signals": _mock_policy(industry),
            "market_signals": _mock_market(code),
            "sentiment": _mock_sentiment(name),
            "news_headlines": _mock_news(name),
            "key_events": _mock_events(name),
        }
        
        results.append(info)
        _print_info(info)
    
    return results


def _mock_policy(industry):
    """模拟政策信号"""
    signals = {
        "新能源": ["新能源补贴政策延续", "充电桩建设加速"],
        "光伏": ["光伏出口退税调整", "分布式光伏装机目标上调"],
        "半导体": ["大基金三期投资进展", "芯片国产化替代加速"],
        "医药": ["医保谈判结果公布", "创新药审批提速"],
        "医药生物": ["集采政策影响逐步减弱", "创新药出海加速"],
        "金融": ["降准预期升温", "金融监管政策优化"],
        "券商": ["活跃资本市场政策持续", "IPO节奏恢复"],
        "科技": ["数字经济政策密集出台", "AI监管框架落地"],
        "家电": ["以旧换新补贴政策", "出口退税调整"],
        "消费": ["消费刺激政策加码", "节假日消费数据向好"],
        "食品饮料": ["消费升级趋势延续", "原材料成本下降"],
        "汽车零部件": ["智能驾驶政策支持", "出口增长强劲"],
        "养殖": ["猪肉收储政策支撑", "非洲猪瘟防控加强"],
        "煤炭": ["能源保供政策持续", "碳交易市场扩容"],
        "房地产": ["楼市松绑政策继续", "保交楼进展顺利"],
        "AI": ["AI大模型备案加快", "算力基建投资增加"],
        "软件": ["信创国产化加速", "工业软件支持政策"],
        "通信": ["5G-A商用推进", "卫星互联网建设提速"],
        "化工": ["环保限产政策", "出口退税调整"],
        "有色": ["全球资源安全政策", "新能源金属需求增长"],
    }
    return signals.get(industry, [f"{industry}行业政策平稳"])


def _mock_market(code):
    """模拟市场信号"""
    money_flow = random.choice(["主力净流入", "主力净流出", "资金博弈"])
    amount = round(random.uniform(0.5, 5.0), 1)
    return {
        "money_flow": money_flow,
        "amount": f"{amount}亿",
        "volume_abnormal": "是" if random.random() > 0.7 else "否",
        "institutional_activity": random.choice(["北向资金增持", "基金加仓", "游资活跃", "无明显异动"]),
    }


def _mock_sentiment(name):
    """模拟情绪"""
    sentiments = ["偏乐观", "中性", "偏谨慎", "乐观", "悲观"]
    weights = [0.3, 0.3, 0.2, 0.1, 0.1]
    sentiment = random.choices(sentiments, weights=weights, k=1)[0]
    return {
        "level": sentiment,
        "hot_topics": [f"{name}最新动态", f"行业景气度讨论"],
        "retail_sentiment": sentiment,
    }


def _mock_news(name):
    """模拟新闻"""
    headlines_pool = [
        f"{name}发布最新财报",
        f"机构上调{name}评级",
        f"{name}新业务进展顺利",
        f"行业龙头{name}获政策利好",
        f"{name}技术研发取得突破",
        f"市场看好{name}发展前景",
        f"{name}宣布回购计划",
        f"{name}高管增持",
        f"行业景气度提升，{name}受益",
        f"{name}中标重大项目",
    ]
    return random.sample(headlines_pool, min(3, len(headlines_pool)))


def _mock_events(name):
    """模拟关键事件"""
    return [
        {"date": "近期", "event": f"{name}股价波动加大", "impact": "关注"},
        {"date": "下月", "event": "行业数据发布", "impact": "中等"},
    ]


def _print_info(info):
    """打印情报摘要"""
    print(f"  🔍 政策信号: {'; '.join(info['policy_signals'][:2])}")
    print(f"  💰 资金动向: {info['market_signals']['money_flow']} {info['market_signals']['amount']}")
    print(f"  🧠 市场情绪: {info['sentiment']['level']}")
    if info["news_headlines"]:
        headline = info["news_headlines"][0][:40]
        print(f"  📰 头条新闻: {headline}...")


# ===== 带 DeepSeek 的深度情报分析 =====
def deep_research(picks, strategy_name):
    """用 DeepSeek 做深度情报分析"""
    if not DEEPSEEK_API_KEY:
        return research_stocks(picks)
    
    from openai import OpenAI
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    
    stocks_info = []
    for s in picks:
        stocks_info.append({
            "name": s.get("name", ""),
            "code": s.get("code", ""),
            "industry": s.get("industry", ""),
            "price": s.get("price", 0),
            "change_pct": s.get("change_pct", 0),
            "reason": s.get("_llm_reason", ""),
            "risk": s.get("_llm_risk", ""),
        })
    
    prompt = f"""你是一个 A 股情报分析师。请为以下候选股票搜集关键情报，辅助投资决策。

当前选股策略：{strategy_name}

股票列表：
{json.dumps(stocks_info, ensure_ascii=False, indent=2)}

请分析每只股票的以下维度，返回 JSON 格式：

[
  {{
    "code": "股票代码",
    "policy_impact": "政策面影响（一句话）",
    "market_momentum": "资金面和技术面判断（一句话）",
    "key_catalysts": "近期催化剂（最多2个）",
    "risk_factors": "近期风险（最多2个）",
    "overall_assessment": "综合评估（一句话）"
  }}
]

只返回 JSON 数组，不要其他文字。
"""
    
    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1500,
        )
        
        content = resp.choices[0].message.content
        start = content.find("[")
        end = content.rfind("]")
        if start >= 0 and end > start:
            analysis = json.loads(content[start:end+1])
        else:
            analysis = json.loads(content)
        
        # 打印结果
        print(f"\n{'='*60}")
        print("🔬 DeepSeek 深度情报分析")
        print("="*60)
        
        for a in analysis:
            print(f"\n  📌 {a.get('name', a['code'])} ({a['code']})")
            print(f"     📋 {a.get('overall_assessment', '')}")
            print(f"     🏛️  政策: {a.get('policy_impact', '')}")
            print(f"     📈 资金: {a.get('market_momentum', '')}")
            catalysts = a.get('key_catalysts', [])
            if catalysts:
                for c in catalysts if isinstance(catalysts, list) else [catalysts]:
                    print(f"     🚀 催化: {c}"[:80])
            risks = a.get('risk_factors', [])
            if risks:
                for r in risks if isinstance(risks, list) else [risks]:
                    print(f"     ⚠️  风险: {r}"[:80])
        
        return analysis
        
    except Exception as e:
        print(f"  ⚠️ DeepSeek 情报分析失败: {e}")
        print("  使用模拟情报...")
        return research_stocks(picks)


if __name__ == "__main__":
    # 从 latest_picks.json 读取
    picks_file = "/tmp/TradingAgents/output/latest_picks.json"
    if os.path.exists(picks_file):
        with open(picks_file) as f:
            picks = json.load(f)
    else:
        # 演示数据
        picks = [
            {"name": "海尔智家", "code": "600690", "industry": "家电", "price": 17.39, "change_pct": 3.56, "_llm_reason": "动量趋势强劲", "_llm_risk": "RSI超买"},
            {"name": "福耀玻璃", "code": "600660", "industry": "汽车零部件", "price": 43.65, "change_pct": 5.12, "_llm_reason": "放量突破", "_llm_risk": "估值偏高"},
            {"name": "中信证券", "code": "600030", "industry": "券商", "price": 224.82, "change_pct": 7.37, "_llm_reason": "券商龙头放量", "_llm_risk": "短期涨幅较大"},
        ]
    
    deep_research(picks, "动量趋势")
