import pandas as pd
import numpy as np

def calculate_rsi(close, length=14):
    """Calculate RSI indicator"""
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=length).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=length).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi

def calculate_parabolic_sar_on_rsi(rsi, start=0.02, increment=0.02, maximum=0.2):
    """
    Calculate Parabolic SAR on RSI values (not price)
    This is the key difference - SAR is applied to RSI line itself
    
    Based on ChartPrime's Pine Script implementation
    """
    rsi_high = rsi + 1
    rsi_low = rsi - 1
    
    result = np.full(len(rsi), np.nan)
    max_min = np.full(len(rsi), np.nan)
    acceleration = np.full(len(rsi), np.nan)
    is_below = np.full(len(rsi), False, dtype=bool)
    
    # Initialize first valid values
    for i in range(1, len(rsi)):
        if pd.notna(rsi.iloc[i]) and pd.notna(rsi.iloc[i-1]):
            if rsi.iloc[i] > rsi.iloc[i-1]:
                is_below[i] = True
                max_min[i] = rsi_high.iloc[i]
                result[i] = rsi_low.iloc[i-1]
            else:
                is_below[i] = False
                max_min[i] = rsi_low.iloc[i]
                result[i] = rsi_high.iloc[i-1]
            
            acceleration[i] = start
            break
    
    # Calculate SAR for remaining bars
    for i in range(2, len(rsi)):
        if pd.isna(result[i-1]):
            continue
        
        is_first_trend_bar = False
        
        # Calculate new SAR value
        result[i] = result[i-1] + acceleration[i-1] * (max_min[i-1] - result[i-1])
        
        # Copy previous values
        is_below[i] = is_below[i-1]
        max_min[i] = max_min[i-1]
        acceleration[i] = acceleration[i-1]
        
        # Check for trend reversal
        if is_below[i]:
            if result[i] > rsi_low.iloc[i]:
                is_first_trend_bar = True
                is_below[i] = False
                result[i] = max(rsi_high.iloc[i], max_min[i])
                max_min[i] = rsi_low.iloc[i]
                acceleration[i] = start
        else:
            if result[i] < rsi_high.iloc[i]:
                is_first_trend_bar = True
                is_below[i] = True
                result[i] = min(rsi_low.iloc[i], max_min[i])
                max_min[i] = rsi_high.iloc[i]
                acceleration[i] = start
        
        # Update acceleration and extreme point
        if not is_first_trend_bar:
            if is_below[i]:
                if rsi_high.iloc[i] > max_min[i]:
                    max_min[i] = rsi_high.iloc[i]
                    acceleration[i] = min(acceleration[i] + increment, maximum)
            else:
                if rsi_low.iloc[i] < max_min[i]:
                    max_min[i] = rsi_low.iloc[i]
                    acceleration[i] = min(acceleration[i] + increment, maximum)
        
        # Ensure SAR doesn't penetrate last two lows/highs
        if is_below[i]:
            result[i] = min(result[i], rsi_low.iloc[i-1])
            if i >= 2:
                result[i] = min(result[i], rsi_low.iloc[i-2])
        else:
            result[i] = max(result[i], rsi_high.iloc[i-1])
            if i >= 2:
                result[i] = max(result[i], rsi_high.iloc[i-2])
    
    return pd.Series(result, index=rsi.index), pd.Series(is_below, index=rsi.index)

def calculate_parabolic_rsi(df, rsi_length=14, sar_start=0.02, sar_increment=0.02, sar_max=0.2):
    """
    Calculate complete Parabolic RSI indicator
    
    Returns dataframe with columns: rsi, sar, is_below
    """
    # Calculate RSI
    df['rsi'] = calculate_rsi(df['close'], length=rsi_length)
    
    # Apply Parabolic SAR to RSI values
    df['sar'], df['is_below'] = calculate_parabolic_sar_on_rsi(
        df['rsi'],
        start=sar_start,
        increment=sar_increment,
        maximum=sar_max
    )
    
    return df

def detect_strong_signals(df, upper_threshold=70, lower_threshold=30):
    """
    Detect Strong Signals (Big Diamonds) only:
    - Strong Buy: SAR flips to bullish (is_below=True) AND SAR <= lower_threshold (30)
    - Strong Sell: SAR flips to bearish (is_below=False) AND SAR >= upper_threshold (70)
    
    This matches the Pine Script conditions:
    s_sig_up = isBelow != isBelow[1] and isBelow and barstate.isconfirmed and sar_rsi <= lower_
    s_sig_dn = isBelow != isBelow[1] and not isBelow and barstate.isconfirmed and sar_rsi >= upper_
    """
    if len(df) < 2:
        return []
    
    latest = df.iloc[-1]
    previous = df.iloc[-2]
    
    signals = []
    
    # Check if we have valid data
    if pd.isna(latest['sar']) or pd.isna(previous['sar']):
        return signals
    
    # Strong Bullish Signal: SAR flips to bullish AND SAR <= 30
    if latest['is_below'] != previous['is_below'] and latest['is_below'] and latest['sar'] <= lower_threshold:
        signals.append('STRONG_BUY')
    
    # Strong Bearish Signal: SAR flips to bearish AND SAR >= 70
    if latest['is_below'] != previous['is_below'] and not latest['is_below'] and latest['sar'] >= upper_threshold:
        signals.append('STRONG_SELL')
    
    return signals
