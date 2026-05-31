#!/usr/bin/env python3
"""
📡 A股选股 Agent — 从全市场扫描到精选股票
配合 TradingAgents 使用，先筛选，再深度分析

用法:
  python3 stock_picker.py                    # 默认策略扫描 A 股
  python3 stock_picker.py --strategy volume  # 放量突破策略
  python3 stock_picker.py --strategy value   # 价值低估策略  
  python3 stock_picker.py --strategy momentum# 动量策略
  python3 stock_picker.py --top 10           # 输出前 10 只
  python3 stock_picker.py --run-ta           # 筛选后自动跑 TradingAgents 分析
"""

import sys, os, json, time, argparse, warnings, datetime
warnings.filterwarnings("ignore")

# ========== 配置区 ==========
# 如果安装了 akshare 就用实时数据，否则用模拟数据
USE_AKSHARE = False  # 暂设为 False，因为需要安装 akshare
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

# ========== 策略定义 ==========
STRATEGIES = {
    "volume": {
        "name": "放量突破",
        "description": "成交量放大 + 价格突破均线，短线资金活跃",
        "filters": {
            "volume_ratio_gt": 1.5,      # 量比 > 1.5
            "close_above_ma20": True,    # 收盘价在 MA20 上方
            "change_pct_gt": 2.0,        # 涨幅 > 2%
            "change_pct_lt": 9.8,        # 涨幅 < 9.8%（排除涨停）
        },
        "score_weights": {
            "volume_ratio": 0.30,        # 放量程度
            "momentum": 0.25,            # 短期动量
            "relative_strength": 0.25,   # 相对强度
            "fundamental": 0.20,         # 基本面
        }
    },
    "value": {
        "name": "价值低估",
        "description": "低 PE + 低 PB + 高 ROE，基本面优秀的便宜货",
        "filters": {
            "pe_ttm_lt": 20,             # PE < 20
            "pe_ttm_gt": 0,              # PE > 0（盈利）
            "pb_lt": 2,                  # PB < 2
            "roe_gt": 8,                 # ROE > 8%
            "market_cap_gt": 50,         # 市值 > 50亿
        },
        "score_weights": {
            "value_score": 0.35,
            "quality_score": 0.30,
            "momentum": 0.15,
            "dividend": 0.10,
            "sentiment": 0.10,
        }
    },
    "momentum": {
        "name": "动量趋势",
        "description": "近期涨幅靠前 + 均线多头排列，趋势跟踪",
        "filters": {
            "close_above_ma20": True,
            "close_above_ma60": True,
            "ma20_above_ma60": True,     # 短均线在长均线上方
            "change_20d_gt": 5,          # 20日涨幅 > 5%
            "volume_ratio_gt": 0.8,      # 量比 > 0.8（不能太缩量）
        },
        "score_weights": {
            "momentum_20d": 0.30,
            "momentum_60d": 0.20,
            "volume_trend": 0.20,
            "relative_strength": 0.20,
            "fundamental": 0.10,
        }
    },
    "oversold": {
        "name": "超跌反弹",
        "description": "RSI 超卖 + 跌幅过大，可能的技术性反弹机会",
        "filters": {
            "rsi_lt": 35,                # RSI < 35（超卖）
            "change_20d_lt": -10,        # 20日跌幅 > 10%
            "volume_ratio_gt": 0.6,      # 不能完全缩量死寂
            "market_cap_gt": 30,         # 市值 > 30亿
        },
        "score_weights": {
            "oversold_severity": 0.30,
            "volume_pickup": 0.25,
            "fundamental": 0.25,
            "industry_strength": 0.20,
        }
    },
}


# ========== 模拟数据生成（演示用）==========
def get_mock_universe():
    """生成模拟的 A 股全市场股票池"""
    stocks = []
    names = [
        ("贵州茅台", 600519, "食品饮料"), ("宁德时代", 300750, "新能源"),
        ("招商银行", 600036, "金融"), ("中国平安", 601318, "金融"),
        ("美的集团", "000333", "家电"), ("比亚迪", "002594", "新能源"),
        ("迈瑞医疗", "300760", "医疗"), ("恒瑞医药", "600276", "医药"),
        ("海康威视", "002415", "科技"), ("中芯国际", "688981", "半导体"),
        ("药明康德", "603259", "医药生物"), ("长江电力", "600900", "公用事业"),
        ("万华化学", "600309", "化工"), ("三一重工", "600031", "机械"),
        ("立讯精密", "002475", "消费电子"), ("隆基绿能", "601012", "光伏"),
        ("紫金矿业", "601899", "有色"), ("海尔智家", "600690", "家电"),
        ("中国中免", "601888", "消费"), ("东方财富", "300059", "金融科技"),
        ("格力电器", "000651", "家电"), ("中兴通讯", "000063", "通信"),
        ("阳光电源", "300274", "光伏"), ("福耀玻璃", "600660", "汽车零部件"),
        ("片仔癀", "600436", "中药"), ("通威股份", "600438", "光伏"),
        ("国电南瑞", "600406", "电力设备"), ("中国神华", "601088", "煤炭"),
        ("华能国际", "600011", "电力"), ("科大讯飞", "002230", "AI"),
        ("金山办公", "688111", "软件"), ("韦尔股份", "603501", "半导体"),
        ("中国中车", "601766", "轨交"), ("宝钢股份", "600019", "钢铁"),
        ("牧原股份", "002714", "养殖"), ("温氏股份", "300498", "养殖"),
        ("青岛啤酒", "600600", "食品饮料"), ("伊利股份", "600887", "食品饮料"),
        ("保利发展", "600048", "房地产"), ("万科A", "000002", "房地产"),
        ("中信证券", "600030", "券商"), ("华泰证券", "601688", "券商"),
        ("中国石油", "601857", "能源"), ("中国石化", "600028", "能源"),
        ("中国移动", "600941", "通信"), ("中国电信", "601728", "通信"),
        ("京东方A", "000725", "面板"), ("TCL科技", "000100", "面板"),
        ("中微公司", "688012", "半导体设备"), ("北方华创", "002371", "半导体设备"),
    ]
    
    import random
    random.seed(42)
    
    for name, code, industry in names:
        pe = round(random.uniform(5, 60), 1)
        pb = round(random.uniform(0.5, 8), 2)
        roe = round(random.uniform(-5, 25), 1)
        market_cap = round(random.uniform(20, 1000), 1)
        change_pct = round(random.uniform(-6, 9), 2)
        volume_ratio = round(random.uniform(0.3, 4.5), 2)
        rsi = round(random.uniform(20, 80), 1)
        ma20_pct = round(random.uniform(-8, 12), 2)  # 收盘价偏离 MA20 的百分比
        change_20d = round(random.uniform(-18, 22), 1)
        change_60d = round(random.uniform(-25, 35), 1)
        
        stocks.append({
            "name": name,
            "code": str(code),
            "industry": industry,
            "price": round(random.uniform(5, 250), 2),
            "pe_ttm": pe,
            "pb": pb,
            "roe": roe,
            "market_cap": market_cap,
            "change_pct": change_pct,
            "volume_ratio": volume_ratio,
            "rsi": rsi,
            "ma20_deviation_pct": ma20_pct,
            "change_20d": change_20d,
            "change_60d": change_60d,
        })
    return stocks


def apply_filters(stocks, strategy):
    """根据策略筛选条件过滤股票"""
    filters = STRATEGIES[strategy]["filters"]
    passed = []
    
    for s in stocks:
        ok = True
        
        # 成交量
        if "volume_ratio_gt" in filters and s["volume_ratio"] < filters["volume_ratio_gt"]:
            ok = False
        if "volume_ratio_lt" in filters and s["volume_ratio"] > filters["volume_ratio_lt"]:
            ok = False
        
        # 涨跌幅
        if "change_pct_gt" in filters and s["change_pct"] < filters["change_pct_gt"]:
            ok = False
        if "change_pct_lt" in filters and s["change_pct"] > filters["change_pct_lt"]:
            ok = False
        
        # PE
        if "pe_ttm_gt" in filters and s["pe_ttm"] < filters["pe_ttm_gt"]:
            ok = False
        if "pe_ttm_lt" in filters and s["pe_ttm"] > filters["pe_ttm_lt"]:
            ok = False
        
        # PB
        if "pb_lt" in filters and s["pb"] > filters["pb_lt"]:
            ok = False
        
        # ROE
        if "roe_gt" in filters and s["roe"] < filters["roe_gt"]:
            ok = False
        
        # 市值
        if "market_cap_gt" in filters and s["market_cap"] < filters["market_cap_gt"]:
            ok = False
        
        # RSI
        if "rsi_lt" in filters and s["rsi"] > filters["rsi_lt"]:
            ok = False
        if "rsi_gt" in filters and s["rsi"] < filters["rsi_gt"]:
            ok = False
        
        # 均线
        if filters.get("close_above_ma20") and s["ma20_deviation_pct"] < 0:
            ok = False
        if filters.get("close_above_ma60") and s.get("ma60_deviation_pct", 1) < 0:
            ok = False
        
        # 短期涨幅
        if "change_20d_gt" in filters and s["change_20d"] < filters["change_20d_gt"]:
            ok = False
        if "change_20d_lt" in filters and s["change_20d"] > filters["change_20d_lt"]:
            ok = False
        
        if ok:
            passed.append(s)
    
    return passed


def score_with_llm(stocks, strategy_info, top_n=10):
    """用 DeepSeek 对候选股票进行智能评分和排序"""
    if not stocks:
        return []
    
    # 先做一次量化评分（保证基础排序）
    for s in stocks:
        s["_quant_score"] = quant_score(s, strategy_info["name"])
    stocks.sort(key=lambda x: x["_quant_score"], reverse=True)
    top_stocks = stocks[:min(30, len(stocks))]
    
    # 做 LLM 排序（只对 Top 30 做，省 token）
    if DEEPSEEK_API_KEY:
        try:
            sorted_stocks = llm_rank(top_stocks, strategy_info)
            return sorted_stocks[:top_n]
        except Exception as e:
            print(f"  ⚠️ LLM 排序失败 ({e})，使用量化评分结果")
            return top_stocks[:top_n]
    else:
        print("  ⚠️ 未设置 DEEPSEEK_API_KEY，使用量化评分（无 LLM 重排）")
        return top_stocks[:top_n]


def quant_score(stock, strategy_name):
    """量化评分（纯数学，不调 API）"""
    score = 50.0  # 基准分
    
    if strategy_name == "放量突破":
        score += min(stock["volume_ratio"] * 5, 15)  # 放量加分
        score += min(max(stock["change_pct"], 0) * 2, 10)  # 涨幅加分
        if stock["market_cap"] > 100:  # 大市值安全加分
            score += 5
    elif strategy_name == "价值低估":
        pe_score = max(0, 15 - stock["pe_ttm"]) * 1.5  # PE 越低越好
        score += min(pe_score, 20)
        score += min(stock["roe"], 20)  # ROE 越高越好
    elif strategy_name == "动量趋势":
        score += min(max(stock["change_60d"], 0) * 0.8, 15)
        score += min(stock["change_20d"], 10)
    elif strategy_name == "超跌反弹":
        score += min(abs(stock.get("change_20d", 0)), 15)  # 跌得越深反弹空间越大
        score += min(stock["volume_ratio"] * 3, 10)  # 放量加分
    
    return score


def llm_rank(stocks, strategy_info):
    """用 DeepSeek 对候选股票做智能重排"""
    from openai import OpenAI
    
    client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com"
    )
    
    # 构造候选列表（返回简洁信息就够）
    candidates = []
    for s in stocks:
        candidates.append({
            "code": s["code"],
            "name": s["name"],
            "industry": s["industry"],
            "price": s["price"],
            "pe_ttm": s["pe_ttm"],
            "pb": s["pb"],
            "roe": s["roe"],
            "market_cap": s["market_cap"],
            "change_pct": s["change_pct"],
            "volume_ratio": s["volume_ratio"],
            "rsi": s["rsi"],
            "change_20d": s["change_20d"],
            "change_60d": s["change_60d"],
        })
    
    prompt = f"""你是一个专业的 A 股量化选股助理，请从以下候选股票中，选出最适合「{strategy_info['name']}」策略的 TOP 10 股票。

策略说明：{strategy_info['description']}

筛选逻辑：
1. 首先严格审查每只股票是否真正符合策略的核心逻辑
2. 对符合逻辑的股票，从技术面、基本面、资金面综合评分
3. 考虑行业分散度（避免同一行业太多选入）
4. 按推荐优先级排序

候选股票（共 {len(candidates)} 只）：
{json.dumps(candidates, ensure_ascii=False, indent=2)}

请返回格式要求（仅返回 JSON 数组，不要有其他文字）：
[
  {{
    "code": "股票代码",
    "reason": "入选理由（一句话，说核心逻辑）",
    "risk": "主要风险（一句话）"
  }},
  ...
]
"""
    
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    
    content = resp.choices[0].message.content
    # 提取 JSON
    try:
        # 找第一个 [ 和最后一个 ]
        start = content.find("[")
        end = content.rfind("]")
        if start >= 0 and end > start:
            result = json.loads(content[start:end+1])
        else:
            result = json.loads(content)
    except:
        print("  ⚠️ LLM 返回格式异常，用原始排序")
        return stocks
    
    # 把 LLM 排序结果映射回原始 stock 对象
    ranked = []
    for item in result:
        code = str(item["code"])
        for s in stocks:
            if s["code"] == code:
                s["_llm_reason"] = item.get("reason", "")
                s["_llm_risk"] = item.get("risk", "")
                ranked.append(s)
                break
    
    # 如果 LLM 返回的太少，补充一些
    for s in stocks:
        if s not in ranked and len(ranked) < 10:
            ranked.append(s)
    
    return ranked


def pick_stocks(strategy="volume", top_n=10):
    """主函数：从选股到输出推荐"""
    print(f"\n📡 选股策略: {STRATEGIES[strategy]['name']}")
    print(f"   {STRATEGIES[strategy]['description']}")
    print(f"   目标输出: Top {top_n}")
    print()
    
    # Step 1: 获取全市场股票数据
    print("📦 获取全市场股票数据...")
    if USE_AKSHARE:
        print("   (使用 akshare 实时数据)")
        # TODO: 接入 akshare
        universe = get_mock_universe()
    else:
        print("   (使用模拟数据，安装 akshare 后可获取实时数据)")
        universe = get_mock_universe()
    
    print(f"   全市场: {len(universe)} 只候选")
    
    # Step 2: 策略筛选
    print(f"\n🔍 策略筛选 ({STRATEGIES[strategy]['name']})...")
    passed = apply_filters(universe, strategy)
    print(f"   通过筛选: {len(passed)} 只")
    
    if not passed:
        print("   ❌ 没有符合条件的股票，请放宽筛选条件")
        return []
    
    # Step 3: AI 排序
    print(f"\n🤖 AI 排序中 ({'DeepSeek' if DEEPSEEK_API_KEY else '量化评分'})...")
    picks = score_with_llm(passed, STRATEGIES[strategy], top_n)
    
    # Step 4: 输出结果
    print(f"\n{'='*60}")
    print(f"📊 推荐股票 TOP {len(picks)}")
    print(f"{'='*60}")
    
    for i, s in enumerate(picks, 1):
        reason = s.get("_llm_reason", "")
        risk = s.get("_llm_risk", "")
        
        print(f"\n{'─'*50}")
        print(f"  #{i}  {s['name']} ({s['code']})  {s['industry']}")
        print(f"     价格: ¥{s['price']:<8.2f}  PE: {s['pe_ttm']:<5.1f}  PB: {s['pb']:<5.2f}  ROE: {s['roe']:.1f}%")
        print(f"     涨幅: {s['change_pct']:+.2f}%  量比: {s['volume_ratio']:.2f}  RSI: {s['rsi']:.1f}")
        print(f"     20日: {s['change_20d']:+.1f}%  60日: {s['change_60d']:+.1f}%  市值: {s['market_cap']:.0f}亿")
        if reason:
            print(f"     💡 理由: {reason}")
        if risk:
            print(f"     ⚠️ 风险: {risk}")
    
    print(f"\n{'='*60}")
    print(f"✅ 选股完成！")
    
    # 保存到 JSON 文件，供 portfolio_engine 使用
    os.makedirs("/tmp/TradingAgents/output", exist_ok=True)
    json_path = "/tmp/TradingAgents/output/latest_picks.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(picks, f, ensure_ascii=False, indent=2, default=str)
    print(f"   结果已保存: {json_path}")
    
    # 返回 picks 供外部使用
    return picks


def run_tradingagents(picks):
    """对选中的股票跑 TradingAgents 深度分析"""
    sys.path.insert(0, "/tmp/TradingAgents")
    
    from tradingagents.default_config import DEFAULT_CONFIG
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    
    os.environ["DEEPSEEK_API_KEY"] = DEEPSEEK_API_KEY
    
    config = DEFAULT_CONFIG.copy()
    config['llm_provider'] = 'deepseek'
    config['deep_think_llm'] = 'deepseek-chat'
    config['quick_think_llm'] = 'deepseek-chat'
    config['output_language'] = 'Chinese'
    config['max_debate_rounds'] = 1
    config['max_risk_discuss_rounds'] = 1
    config['news_article_limit'] = 3
    config['global_news_article_limit'] = 3
    
    print("\n🔬 TradingAgents 深度分析...")
    
    try:
        ta = TradingAgentsGraph(selected_analysts=['market'], debug=False, config=config)
    except Exception as e:
        print(f"  ❌ 初始化失败: {e}")
        print("  💡 确保在 /tmp/TradingAgents 目录下运行")
        return
    
    for i, s in enumerate(picks):
        ticker = s['code']
        if len(ticker) == 6:
            if ticker.startswith('6'):
                ticker += '.SS'
            else:
                ticker += '.SZ'
        
        print(f"\n📈 分析 {s['name']} ({ticker})... (第{i+1}/{len(picks)}只)")
        
        if i > 0:
            wait = 45
            print(f"   ⏳ 等待 {wait} 秒避免 API 限流...")
            time.sleep(wait)
        
        try:
            state = ta.propagator.create_initial_state(
                ticker, datetime.date.today().strftime("%Y-%m-%d"),
                past_context='',
                instrument_context=ta.resolve_instrument_context(ticker, 'stock'),
            )
            result = ta.graph.invoke(state, **ta.propagator.get_graph_args())
            
            decision = result.get('final_trade_decision', '')
            if decision:
                print(f"   ✅ 决策输出 ({len(decision)} 字)")
                # 提取摘要
                lines = decision.strip().split('\n')
                summary = [l for l in lines if 'Rating' in l or '评级' in l or '建议' in l or '减持' in l or '增持' in l or '买入' in l or '卖出' in l]
                if summary:
                    for l in summary[:3]:
                        print(f"   📌 {l}")
        except Exception as e:
            print(f"   ❌ 分析失败: {e}")
    
    print("\n✅ 所有股票分析完成！")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A股选股 Agent")
    parser.add_argument("--strategy", "-s", default="volume",
                        choices=list(STRATEGIES.keys()),
                        help="选股策略")
    parser.add_argument("--top", "-t", type=int, default=10,
                        help="输出前几只")
    parser.add_argument("--run-ta", action="store_true",
                        help="选股后自动跑 TradingAgents 深度分析")
    args = parser.parse_args()
    
    picks = pick_stocks(args.strategy, args.top)
    
    if args.run_ta and picks:
        run_tradingagents(picks)
