import pandas as pd
import numpy as np

def add_bollinger_bands(df, column='mid_price', window=20, num_std=2):
    """Adds Bollinger Bands."""
    df = df.copy()
    rolling_mean = df.groupby('day')[column].transform(lambda x: x.rolling(window, min_periods=1).mean())
    rolling_std = df.groupby('day')[column].transform(lambda x: x.rolling(window, min_periods=1).std())
    
    df['BB_upper'] = rolling_mean + (rolling_std * num_std)
    df['BB_lower'] = rolling_mean - (rolling_std * num_std)
    df['BB_mid'] = rolling_mean
    return df

def add_vwap(df):
    """Calculates trade-based or orderbook-based VWAP."""
    df = df.copy()
    # Micro-price (Orderbook imbalance weighted price)
    df['micro_price'] = (df['bid_price_1'] * df['ask_volume_1'] + df['ask_price_1'] * df['bid_volume_1']) / (df['bid_volume_1'] + df['ask_volume_1']).replace(0, 1)
    
    # Cumulative VWAP per day using proxy size
    df['total_volume'] = df['bid_volume_1'] + df['ask_volume_1']
    df['cum_vwap'] = (df['mid_price'] * df['total_volume']).groupby(df['day']).cumsum() / df['total_volume'].groupby(df['day']).cumsum().replace(0, 1)
    
    return df

def add_emas(df, column='mid_price', spans=[12, 26]):
    """Adds Exponential Moving Averages."""
    df = df.copy()
    for span in spans:
        df[f'EMA_{span}'] = df.groupby('day')[column].transform(lambda x: x.ewm(span=span, adjust=False).mean())
    return df
