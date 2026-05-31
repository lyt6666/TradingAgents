#!/bin/bash
# TradingAgents + DeepSeek + Mock 数据一键运行
# 用法: ./run_mock.sh [股票代码] [日期]
# 示例: ./run_mock.sh AAPL 2026-05-29

set -e

TICKER="${1:-AAPL}"
DATE="${2:-2026-05-29}"

cd /tmp/TradingAgents

# 设置环境变量
export PYTHONPATH="/tmp/TradingAgents:$PYTHONPATH"
export DEEPSEEK_API_KEY="sk-677696e8d5fb45b6b4a22ad23e773b41"

echo "===== TradingAgents + DeepSeek ====="
echo "标的: $TICKER"
echo "日期: $DATE"
echo "===================================="
echo ""

python3 -c "
import sys, os, ssl, certifi
ssl._create_default_https_context = ssl.create_default_context
sys.path.insert(0, '/tmp/TradingAgents')
import warnings; warnings.filterwarnings('ignore')

# Mock yfinance
import yfinance as yf
from mock_data import generate_fundamentals, generate_price_data
from unittest.mock import Mock
class MockTicker:
    def __init__(self, symbol):
        self.symbol = symbol.upper()
        funds = generate_fundamentals(symbol)
        self._info = funds['info']
        self._price_data, _ = generate_price_data(symbol, days=120)
    def history(self, period='1mo', interval='1d', **kw): return self._price_data.tail(21)
    @property
    def info(self): return self._info
yf.Ticker = MockTicker
import yfinance.exceptions
yfinance.exceptions.YFRateLimitError.__init__ = lambda self, *a, **kw: None
import yfinance.data
yfinance.data.YfData._make_request = lambda self, url, **kw: Mock(status_code=200, ok=True)

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph
import time

config = DEFAULT_CONFIG.copy()
config['llm_provider'] = 'deepseek'
config['deep_think_llm'] = 'deepseek-chat'
config['quick_think_llm'] = 'deepseek-chat'
config['output_language'] = 'Chinese'
config['max_debate_rounds'] = 1
config['max_risk_discuss_rounds'] = 1
config['news_article_limit'] = 3
config['global_news_article_limit'] = 3

print('初始化 TradingAgents...')
ta = TradingAgentsGraph(
    selected_analysts=['market'],
    debug=False,
    config=config,
)

print(f'分析 $TICKER...')
state = ta.propagator.create_initial_state(
    '$TICKER', '$DATE',
    past_context='',
    instrument_context=ta.resolve_instrument_context('$TICKER', 'stock'),
)

start = time.time()
print('运行中（约 2 分钟）...')
print('')
result = ta.graph.invoke(state, **ta.propagator.get_graph_args())
total = time.time() - start

print(f'\n✅ 完成! 耗时 {total:.0f} 秒')
print('')

if isinstance(result, dict):
    report = result.get('market_report', '')
    if report:
        print('='*50)
        print('📊 市场分析报告:')
        print('='*50)
        print(report[:1500])
        print('...')
    
    decision = result.get('final_trade_decision', '')
    if decision:
        print('\n' + '='*50)
        print('💰 最终交易决策:')
        print('='*50)
        print(decision[:1500])
"
