import pandas as pd
import numpy as np
from datetime import datetime

RNG = np.random.RandomState(42)

SYMBOL_INFO = {
    "AAPL": {"name": "Apple Inc.", "sector": "Technology", "price": 182.50, "pe": 28.5, "market_cap": 2800000000000, "beta": 1.2},
    "MSFT": {"name": "Microsoft Corporation", "sector": "Technology", "price": 425.00, "pe": 35.0, "market_cap": 3150000000000, "beta": 0.9},
    "GOOGL": {"name": "Alphabet Inc.", "sector": "Technology", "price": 175.00, "pe": 24.0, "market_cap": 2150000000000, "beta": 1.05},
    "NVDA": {"name": "NVIDIA Corporation", "sector": "Technology", "price": 890.00, "pe": 75.0, "market_cap": 2200000000000, "beta": 1.65},
    "TSLA": {"name": "Tesla, Inc.", "sector": "Automotive", "price": 240.00, "pe": 65.0, "market_cap": 765000000000, "beta": 2.0},
    "AMZN": {"name": "Amazon.com Inc.", "sector": "Technology", "price": 198.00, "pe": 42.0, "market_cap": 2050000000000, "beta": 1.15},
}

def generate_price_data(symbol, days=120, end_date=None):
    info = SYMBOL_INFO.get(symbol.upper(), {"name": symbol, "sector": "Unknown", "price": 100.0, "pe": 20.0, "market_cap": 1e11, "beta": 1.0})
    base_price = info["price"]
    if end_date is None:
        end_date = datetime.now()
    dates = pd.date_range(end=end_date, periods=days, freq='D')
    daily_vol = 0.015 * info["beta"]
    returns = RNG.randn(days) * daily_vol + 0.0005
    for i in range(1, days):
        returns[i] += 0.3 * returns[i-1]
    prices = base_price * np.exp(np.cumsum(returns))
    prices = np.maximum(prices, base_price * 0.7)
    volume_base = 50000000 * (base_price / 100)
    volumes = np.abs(RNG.randn(days) * volume_base * 0.3 + volume_base).astype(int)
    df = pd.DataFrame({
        'Open': prices * (1 + RNG.randn(days) * 0.003),
        'High': prices * (1 + abs(RNG.randn(days)) * 0.008),
        'Low': prices * (1 - abs(RNG.randn(days)) * 0.008),
        'Close': prices, 'Adj Close': prices, 'Volume': volumes,
    }, index=dates)
    return df, info

def generate_fundamentals(symbol):
    info = SYMBOL_INFO.get(symbol.upper(), {"name": symbol, "sector": "Other", "price": 100.0, "pe": 20.0, "market_cap": 1e11, "beta": 1.0})
    yf_info = {
        'symbol': symbol.upper(), 'longName': info["name"], 'currentPrice': info["price"],
        'previousClose': info["price"] * 0.995, 'marketCap': info["market_cap"],
        'sector': info["sector"], 'trailingPE': info["pe"], 'forwardPE': info["pe"] * 0.95,
        'fiftyTwoWeekHigh': info["price"] * 1.25, 'fiftyTwoWeekLow': info["price"] * 0.75,
        'dividendYield': 0.005, 'beta': info["beta"], 'returnOnEquity': 0.35,
        'profitMargins': 0.25, 'totalRevenue': info["market_cap"] * 0.15,
        'freeCashflow': info["market_cap"] * 0.05, 'volume': 45000000, 'averageVolume': 50000000,
        'shortRatio': 1.5, 'debtToEquity': 1.5, 'priceToBook': info["pe"] * 1.2,
        'earningsQuarterlyGrowth': 0.12, 'operatingMargins': 0.30,
        'grossProfits': info["market_cap"] * 0.08, 'ebitda': info["market_cap"] * 0.06,
        'revenuePerShare': info["price"] * 0.15, 'operatingCashflow': info["market_cap"] * 0.06,
        'recommendationKey': 'buy', 'targetMeanPrice': info["price"] * 1.15,
        'numberOfAnalystOpinions': 45, '52WeekChange': 0.25,
    }
    return {
        'info': yf_info,
        'balance_sheet': pd.DataFrame({'Total Assets': [info["market_cap"] * 1.5], 'Total Liabilities Net Minority Interest': [info["market_cap"] * 0.8], 'Stockholders Equity': [info["market_cap"] * 0.7], 'Total Debt': [info["market_cap"] * 0.3]}, index=['2026']),
        'financials': pd.DataFrame({'Total Revenue': [info["market_cap"] * 0.15], 'Net Income': [info["market_cap"] * 0.15 * (2 / info["pe"])]}, index=['2026']),
        'quarterly_financials': pd.DataFrame({'Total Revenue': [info["market_cap"] * 0.036]*4, 'Net Income': [info["market_cap"] * 0.036 * (2 / info["pe"])]*4}, index=pd.date_range(end='2026-03-31', periods=4, freq='QE')),
        'cashflow': pd.DataFrame({'Operating Cash Flow': [info["market_cap"] * 0.06], 'Free Cash Flow': [info["market_cap"] * 0.04]}, index=['2026']),
    }
