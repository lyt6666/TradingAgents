"""
Full yfinance monkey-patch for TradingAgents.
Cover ALL import paths to prevent rate limit errors.
"""
import os, sys, ssl, certifi
ssl._create_default_https_context = ssl.create_default_context
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd, numpy as np
from datetime import datetime
from mock_data import generate_price_data, generate_fundamentals

class MockTicker:
    def __init__(self, symbol):
        self.symbol = symbol.upper()
        funds = generate_fundamentals(symbol)
        self._info = funds['info']
        self._price_data, _ = generate_price_data(symbol, days=120)
        self._balance_sheet = funds.get('balance_sheet', pd.DataFrame())
        self._financials = funds.get('financials', pd.DataFrame())
        self._quarterly = funds.get('quarterly_financials', pd.DataFrame())
        self._cashflow = funds.get('cashflow', pd.DataFrame())
    def history(self, period="1mo", interval="1d", **kw):
        pmap = {"1d": 1, "5d": 5, "1mo": 21, "3mo": 63, "6mo": 126, "1y": 252}
        n = pmap.get(period, 60)
        return self._price_data.tail(min(n, len(self._price_data)))
    @property
    def info(self): return self._info
    def financials(self): return self._financials
    def quarterly_financials(self): return self._quarterly
    def balance_sheet(self): return self._balance_sheet
    def cashflow(self): return self._cashflow
    def get_insider_transactions(self): return pd.DataFrame()
    def get_shares_full(self): return pd.DataFrame()

# Patch yfinance at every single import path
import yfinance as _yf_main
_yf_main.Ticker = MockTicker

# Create a FakeTickerStory for any lazy-loaded modules
# Also patch yfinance.data 
import yfinance.exceptions as _yf_exc

# The key: prevent ANY yfinance internal YFRateLimitError
original_yf_exc_init = _yf_exc.YFRateLimitError.__init__
def no_rate_limit_init(self, *args, **kwargs):
    # Don't call original - never create rate limit errors
    self.args = ()
    self.msg = "MOCKED - no rate limits"
_yf_exc.YFRateLimitError.__init__ = no_rate_limit_init
# Also patch the exception class itself to never be raised

# Most importantly, patch _make_request in YfData to never hit the network
import yfinance.data as _yf_data
original_make_request = _yf_data.YfData._make_request
def mocked_make_request(self, url, **kwargs):
    print(f"  [BLOCKED yfinance request] {url[:60]}...")
    from unittest.mock import Mock
    resp = Mock()
    resp.status_code = 200
    resp.ok = True
    resp.json = lambda: {}
    resp.text = ""
    return resp
_yf_data.YfData._make_request = mocked_make_request

# Patch scrapers
import yfinance.scrapers.quote as _yf_quote
_yf_quote.Quote._fetch_info = lambda self: setattr(self, '_info', MockTicker(self._symbol).info)

import yfinance.scrapers.history as _yf_history
_yf_history.PriceHistory.history = lambda self, *a, **kw: MockTicker(getattr(self, 'ticker', 'AAPL')).history()

# Patch the yf.download function
_yf_main.download = lambda tickers=None, *a, **kw: MockTicker(
    tickers if isinstance(tickers, str) else (list(tickers)[0] if tickers else 'AAPL')
).history()

# Patch every known yfinance internal reference
for mod_name in list(sys.modules.keys()):
    if 'yfinance' in mod_name and mod_name != 'yfinance':
        mod = sys.modules[mod_name]
        if hasattr(mod, 'Ticker'):
            mod.Ticker = MockTicker

print(f"✅ yfinance fully patched ({datetime.now().strftime('%H:%M:%S')})")
