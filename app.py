import streamlit as st
import ccxt
import pandas as pd
import numpy as np

st.set_page_config(page_title="Crypto Multi-TF Confluence Scanner", layout="wide")

# ─────────────────────────────────────────────
# 1. EXCHANGE DATA FETCHER (BINANCE -> OKX -> KUCOIN)
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchanges():
    return {
        'binance': ccxt.binance({'enableRateLimit': True}),
        'okx': ccxt.okx({'enableRateLimit': True}),
        'kucoin': ccxt.kucoin({'enableRateLimit': True}),
    }

exchanges = get_exchanges()


def fetch_ohlcv(symbol, timeframe, limit=300):
    """Returns (df, exchange_name, error_text). df is None if every exchange failed."""
    errors = []
    for ex_name, ex in exchanges.items():
        try:
            ohlcv = ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            if ohlcv and len(ohlcv) >= 60:
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                return df, ex_name, None
            errors.append(f"{ex_name}: not enough candles")
        except Exception as e:
            errors.append(f"{ex_name}: {type(e).__name__}")
    return None, None, " | ".join(errors)


# ─────────────────────────────────────────────
# 2. INDICATORS (ATR, SUPERTREND, PIVOTS, TRENDLINE)
# ─────────────────────────────────────────────
def calculate_atr(df, period=14):
    high, low, close = df['high'], df['low'], df['close']
    tr = pd.concat(
        [high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


def calculate_supertrend(df, period=10, multiplier=3.0):
    df = df.copy()
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    hl2 = (high + low) / 2.0
    atr = calculate_atr(df, period).values

    basic_upper = hl2 + multiplier * atr
    basic_lower = hl2 - multiplier * atr
    final_upper = basic_upper.copy()
    final_lower = basic_lower.copy()

    n = len(df)
    trend = np.ones(n, dtype=int)
    st_line = np.full(n, np.nan
