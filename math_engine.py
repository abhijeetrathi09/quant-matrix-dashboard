# math_engine.py

import pandas as pd
import ta

def calculate_indicators(df):
    """Calculates all necessary indicators for the Market State Engine."""
    # 1. Structure
    df['EMA_20'] = ta.trend.EMAIndicator(close=df['close'], window=20).ema_indicator()
    df['VWAP'] = ta.volume.VolumeWeightedAveragePrice(
        high=df['high'], low=df['low'], close=df['close'], volume=df['volume']
    ).volume_weighted_average_price()
    
    # 2. Momentum
    macd = ta.trend.MACD(close=df['close'])
    df['MACD_Line'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()
    df['MACD_Hist'] = macd.macd_diff()
    df['RSI'] = ta.momentum.RSIIndicator(close=df['close'], window=14).rsi()
    
    # 3. Participation (Volume)
    df['Volume_Avg_20'] = df['volume'].rolling(window=20).mean()
    
    # 4. Volatility (ATR)
    df['ATR'] = ta.volatility.AverageTrueRange(
        high=df['high'], low=df['low'], close=df['close'], window=14
    ).average_true_range()
    
    # Calculate ATR expansion (is current ATR higher than 5 periods ago?)
    df['ATR_Expanding'] = df['ATR'] > df['ATR'].shift(5)

    return df.dropna()