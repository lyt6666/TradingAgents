#!/bin/bash
# TradingAgents + DeepSeek + Mock 数据 + 回测验证
# 用法: ./run_backtest.sh [股票代码] [日期]

set -e

TICKER="${1:-AAPL}"
DATE="${2:-2026-05-29}"

cd /tmp/TradingAgents
export PYTHONPATH="/tmp/TradingAgents:$PYTHONPATH"
export DEEPSEEK_API_KEY="sk-677696e8d5fb45b6b4a22ad23e773b41"

echo "===== TradingAgents + 回测验证 ====="
echo "标的: $TICKER"
echo "分析日期: $DATE"
echo "==================================="
echo ""

TICKER="$TICKER"
DATE="$DATE"

python3 << PYEOF
import sys, os, ssl, certifi, json, re, time
ssl._create_default_https_context = ssl.create_default_context
sys.path.insert(0, '/tmp/TradingAgents')
import warnings; warnings.filterwarnings('ignore')

# ---- Mock data layer ----
import yfinance as yf
from mock_data import generate_fundamentals, generate_price_data
from unittest.mock import Mock
class MockTicker:
    def __init__(self, symbol):
        self.symbol = symbol.upper()
        funds = generate_fundamentals(symbol)
        self._info = funds['info']
        self._price_data, _ = generate_price_data(symbol, days=200)
    def history(self, period='1mo', interval='1d', **kw): 
        ret = self._price_data.tail(22)
        return ret
    @property
    def info(self): return self._info
yf.Ticker = MockTicker
import yfinance.exceptions; yfinance.exceptions.YFRateLimitError.__init__ = lambda self, *a, **kw: None
import yfinance.data; yfinance.data.YfData._make_request = lambda self, url, **kw: Mock(status_code=200, ok=True)

# ---- Run TradingAgents ----
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph

TICKER = "$TICKER"
DATE = "$DATE"

config = DEFAULT_CONFIG.copy()
config['llm_provider'] = 'deepseek'
config['deep_think_llm'] = 'deepseek-chat'
config['quick_think_llm'] = 'deepseek-chat'
config['output_language'] = 'Chinese'
config['max_debate_rounds'] = 1
config['max_risk_discuss_rounds'] = 1
config['news_article_limit'] = 3
config['global_news_article_limit'] = 3

print('🏗️ 初始化 TradingAgents...')
ta = TradingAgentsGraph(selected_analysts=['market'], debug=False, config=config)
state = ta.propagator.create_initial_state(
    TICKER, DATE,
    past_context='',
    instrument_context=ta.resolve_instrument_context(TICKER, 'stock'),
)

print(f'🔍 分析 {TICKER}...')
start = time.time()
result = ta.graph.invoke(state, **ta.propagator.get_graph_args())
analysis_time = time.time() - start
print(f'✅ 分析完成 ({analysis_time:.0f}s)')

market_report = result.get('market_report', '')
decision = result.get('final_trade_decision', '')

print('\n' + '='*60)
print('📊 分析报告摘要')
print('='*60)
if market_report:
    # Extract first few paragraphs
    lines = market_report.strip().split('\n')
    for line in lines[:15]:
        print(line)
    if len(lines) > 15:
        print('  ...')

print('\n' + '='*60)
print('💰 交易决策')
print('='*60)
print(decision[:800] if decision else '（无决策输出）')

# ---- Parse the decision to extract direction ----
def parse_signal(text):
    """从 TradingAgents 的输出中提取交易信号"""
    if not text:
        return 'NEUTRAL', 0
    
    text_lower = text.lower()
    
    # 关键词评分
    signals = {
        'BUY': 0,
        'SELL': 0,
        'HOLD': 0,
    }
    
    # 买入信号
    buy_words = ['买入', '加仓', '增持', 'overweight', '超配', '做多', 'long']
    sell_words = ['卖出', '减仓', '减持', 'underweight', '低配', '做空', 'short', '止损']
    
    for w in buy_words:
        if w in text_lower:
            signals['BUY'] += text_lower.count(w)
    for w in sell_words:
        if w in text_lower:
            signals['SELL'] += text_lower.count(w)
    
    # Check rating
    rating_match = re.search(r'(评级|rating|信号)[：:]\s*(\S+)', text)
    if rating_match:
        rating = rating_match.group(2).lower()
        if any(w in rating for w in ['买入', '买', 'overweight', 'bull']):
            signals['BUY'] += 3
        elif any(w in rating for w in ['卖出', '卖', 'underweight', 'bear']):
            signals['SELL'] += 3
    
    if signals['BUY'] > signals['SELL']:
        return 'BUY', signals['BUY'] - signals['SELL']
    elif signals['SELL'] > signals['BUY']:
        return 'SELL', signals['SELL'] - signals['BUY']
    else:
        return 'HOLD', 0

direction, confidence = parse_signal(decision)
print(f'\n📈 解析信号: {direction} (置信度: {confidence})')

# ---- Backtest ----
print('\n' + '='*60)
print('📉 回测验证 (模拟分析日之后 20 个交易日)')
print('='*60)

# Generate price data for backtest period (after the analysis date)
mock_price_data, _ = generate_price_data(TICKER, days=60)
# Trim to just 20 days after analysis date
bt_data = mock_price_data.tail(25).iloc[:21].copy()
bt_data['Date'] = bt_data.index

if len(bt_data) < 2:
    print('⚠️ 数据不足，无法回测')
else:
    entry_price = bt_data['Close'].iloc[0]
    exit_price = bt_data['Close'].iloc[-1]
    high_price = bt_data['High'].max()
    low_price = bt_data['Low'].min()
    
    raw_return = (exit_price - entry_price) / entry_price * 100
    
    if direction == 'BUY':
        strategy_return = raw_return  # 买入持有
        strategy_label = '做多'
    elif direction == 'SELL':
        strategy_return = -raw_return  # 做空/卖出
        strategy_label = '做空/卖出'
    else:
        strategy_return = 0  # 空仓
        strategy_label = '空仓'
    
    max_drawdown = (bt_data['Low'].min() - bt_data['Close'].iloc[0]) / bt_data['Close'].iloc[0] * 100
    
    print(f'\n入场价格: ${entry_price:.2f}  ')
    print(f'出场价格: ${exit_price:.2f}  ')
    print(f'区间最高: ${high_price:.2f}  ')
    print(f'区间最低: ${low_price:.2f}  ')
    print(f'\n📌 交易信号: {strategy_label}')
    print(f'  策略收益: {strategy_return:+.2f}%')
    print(f'  买入持有收益: {raw_return:+.2f}%')
    print(f'  最大回撤: {max_drawdown:.1f}%')
    
    if strategy_return > raw_return:
        print(f'\n✅ 策略跑赢买入持有 {(strategy_return - raw_return):+.2f}%')
    elif strategy_return < raw_return and direction != 'HOLD':
        print(f'\n⚠️ 策略跑输买入持有 {(raw_return - strategy_return):+.2f}%')
    
    # 每日明细
    print(f'\n📋 每日明细:')
    print(f'{"日期":<14} {"收盘价":<10} {"日收益":<10}')
    print('-'*34)
    for i, (idx, row) in enumerate(bt_data.iterrows()):
        if i == 0:
            daily_ret = 0
        else:
            daily_ret = (row['Close'] - bt_data['Close'].iloc[i-1]) / bt_data['Close'].iloc[i-1] * 100
        if direction == 'SELL':
            # Short: profit when price goes down
            if i == 0:
                daily_ret = 0
            else:
                daily_ret = -(row['Close'] - bt_data['Close'].iloc[i-1]) / bt_data['Close'].iloc[i-1] * 100
        date_str = str(idx.date()) if hasattr(idx, 'date') else str(idx)[:10]
        print(f'{date_str:<14} ${row["Close"]:<8.2f} {daily_ret:+.2f}%')

print(f'\n⏱ 总耗时: {time.time()-start:.0f}s')
PYEOF