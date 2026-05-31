#!/bin/bash
# ════════════════════════════════════════════════════════════
# 📡  A股量化 Pipeline
#     选股 → 情报搜集 → TradingAgents深度分析 → 组合策略
# ════════════════════════════════════════════════════════════
# 用法:
#   ./run_pipeline.sh                    # 完全体：所有步骤
#   ./run_pipeline.sh volume 3           # 只选股
#   ./run_pipeline.sh value 3 --quick    # 快跑（选股+情报+策略）
#   ./run_pipeline.sh momentum 5 --ta    # 全流程（包含TradingAgents分析）
# ════════════════════════════════════════════════════════════

cd /tmp/TradingAgents
export PYTHONPATH="/tmp/TradingAgents:$PYTHONPATH"
export DEEPSEEK_API_KEY="sk-677696e8d5fb45b6b4a22ad23e773b41"

STRATEGY="${1:-volume}"
TOP="${2:-3}"
MODE="${3:---quick}"   # --quick 快跑(选股+情报+策略) | --ta 全流程 | --pick-only 只选股

case $STRATEGY in
    volume) SNAME="放量突破 📈" ;;
    value) SNAME="价值低估 💰" ;;
    momentum) SNAME="动量趋势 🚀" ;;
    oversold) SNAME="超跌反弹 🔄" ;;
    *) SNAME=$STRATEGY ;;
esac

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║     📡  A股量化 Pipeline                            ║"
echo "║     选股 → 情报 → 分析 → 策略                      ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "  策略: $SNAME"
echo "  输出: Top $TOP"
echo "  模式: $([ "$MODE" = "--ta" ] && echo '全流程（含TA深度分析）' || echo '快跑（选股+情报+策略）')"
echo ""

# ============================================================
# 第一步：选股
# ============================================================
echo "╔══════════════════════════════════════════════════════╗"
echo "║  ① 选股                                             ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

python3 stock_picker.py --strategy $STRATEGY --top $TOP

# 检查选股结果
if [ ! -f "/tmp/TradingAgents/output/latest_picks.json" ]; then
    echo "❌ 选股失败，没有输出结果"
    exit 1
fi

PICK_COUNT=$(python3 -c "import json; d=json.load(open('/tmp/TradingAgents/output/latest_picks.json')); print(len(d))")
echo ""
echo "✅ 选股完成，选中 $PICK_COUNT 只"

# 如果只选股，结束
[ "$MODE" = "--pick-only" ] && exit 0

# ============================================================
# 第二步：情报搜集
# ============================================================
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  ② 情报搜集                                         ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

python3 intel_agent.py

# ============================================================
# 第三步：TradingAgents 深度分析（仅 --ta 模式）
# ============================================================
if [ "$MODE" = "--ta" ]; then
    echo ""
    echo "╔══════════════════════════════════════════════════════╗"
    echo "║  ③ TradingAgents 深度分析                          ║"
    echo "║     每只股票约 2 分钟（含 45 秒间隔防限流）         ║"
    echo "╚══════════════════════════════════════════════════════╝"
    echo ""
    python3 stock_picker.py --strategy $STRATEGY --top $TOP --run-ta
fi

# ============================================================
# 第四步：组合策略 + 记忆记录
# ============================================================
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  ④ 组合策略分析 + 记忆存储                          ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

python3 portfolio_engine.py --file /tmp/TradingAgents/output/latest_picks.json

# 记录到记忆系统
python3 trade_memory.py record

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  ⑤ 持仓监控预警                                    ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

python3 watchman.py
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║     ✅ Pipeline 全部完成！                           ║"
echo "║                                                     ║"
echo "║     查看历史:  python3 trade_memory.py view         ║"
echo "║     跟踪表现:  python3 trade_memory.py check        ║"
echo "║     胜率统计:  python3 trade_memory.py stats        ║"
echo "║     查看预警:  python3 watchman.py --history        ║"
echo "║     每日监控:  python3 watchman.py --daemon         ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
