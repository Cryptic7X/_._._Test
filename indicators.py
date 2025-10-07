import pandas as pd
import numpy as np
from datetime import datetime, timedelta

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

def is_bar_confirmed(timestamp, timeframe='30m'):
    """
    Check if a bar is confirmed (closed) based on timestamp
    For 30m timeframe, bar is confirmed if timestamp is more than 30 minutes old
    """
    timeframe_minutes = {
        '1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30,
        '1h': 60, '2h': 120, '4h': 240, '6h': 360, '8h': 480, '12h': 720,
        '1d': 1440
    }
    
    minutes = timeframe_minutes.get(timeframe, 30)
    now = datetime.utcnow()
    
    # Convert timestamp to datetime if it's not already
    if isinstance(timestamp, pd.Timestamp):
        bar_time = timestamp.to_pydatetime()
    else:
        bar_time = timestamp
    
    # Bar is confirmed if it's older than the timeframe duration
    time_diff = (now - bar_time.replace(tzinfo=None)).total_seconds() / 60
    
    return time_diff >= minutes

def is_signal_fresh(timestamp, freshness_minutes=60):
    """
    Check if signal is fresh (within freshness window)
    Default: 60 minutes (1 hour)
    """
    now = datetime.utcnow()
    
    # Convert timestamp to datetime if it's not already
    if isinstance(timestamp, pd.Timestamp):
        signal_time = timestamp.to_pydatetime()
    else:
        signal_time = timestamp
    
    # Calculate age in minutes
    age_minutes = (now - signal_time.replace(tzinfo=None)).total_seconds() / 60
    
    return age_minutes <= freshness_minutes

def detect_strong_signals(df, upper_threshold=70, lower_threshold=30, timeframe='30m', freshness_minutes=60):
    """
    Detect ONLY Strong Signals (BIG Diamonds) on confirmed and fresh bars.
    
    Pine Script conditions (EXACT MATCH):
    s_sig_up = isBelow != isBelow[1] and isBelow and barstate.isconfirmed and sar_rsi <= lower_
    s_sig_dn = isBelow != isBelow[1] and not isBelow and barstate.isconfirmed and sar_rsi >= upper_
    
    Regular signals (small diamonds) are:
    sig_up = isBelow != isBelow[1] and isBelow and barstate.isconfirmed
    sig_dn = isBelow != isBelow[1] and not isBelow and barstate.isconfirmed
    
    The ONLY difference is the threshold check: sar_rsi <= 30 or sar_rsi >= 70
    """
    if len(df) < 3:
        return []
    
    # Check if last bar is confirmed
    last_bar_confirmed = is_bar_confirmed(df.iloc[-1]['timestamp'], timeframe)
    
    # If last bar is not confirmed, check the second-to-last bar (which is definitely confirmed)
    if last_bar_confirmed:
        # Last bar is confirmed, use it
        latest = df.iloc[-1]
        previous = df.iloc[-2]
    else:
        # Last bar is still forming, use second-to-last bar (confirmed)
        latest = df.iloc[-2]
        previous = df.iloc[-3]
    
    # Check if signal is fresh (within freshness window)
    if not is_signal_fresh(latest['timestamp'], freshness_minutes):
        return []  # Signal is too old, ignore it
    
    signals = []
    
    # Check if we have valid data
    if pd.isna(latest['sar']) or pd.isna(previous['sar']) or pd.isna(latest['rsi']):
        return signals
    
    # Check if there was a SAR direction flip on this confirmed bar
    sar_flipped = latest['is_below'] != previous['is_below']
    
    if not sar_flipped:
        return signals  # No flip, no signal at all
    
    # CRITICAL: Check threshold conditions for STRONG signals only
    # Strong Bullish Signal: SAR flipped to bullish (is_below=True) AND SAR value is <= 30
    # Pine Script: s_sig_up = isBelow != isBelow[1] and isBelow and barstate.isconfirmed and sar_rsi <= lower_
    if latest['is_below'] and latest['sar'] <= lower_threshold:
        print(f"    DEBUG: STRONG BUY - SAR flipped to bullish, SAR={latest['sar']:.2f} <= {lower_threshold}")
        signals.append('STRONG_BUY')
    
    # Strong Bearish Signal: SAR flipped to bearish (is_below=False) AND SAR value is >= 70
    # Pine Script: s_sig_dn = isBelow != isBelow[1] and not isBelow and barstate.isconfirmed and sar_rsi >= upper_
    if not latest['is_below'] and latest['sar'] >= upper_threshold:
        print(f"    DEBUG: STRONG SELL - SAR flipped to bearish, SAR={latest['sar']:.2f} >= {upper_threshold}")
        signals.append('STRONG_SELL')
    
    # If SAR flipped but threshold not met, this is a SMALL diamond (which we ignore)
    if sar_flipped and not signals:
        if latest['is_below']:
            print(f"    DEBUG: Small diamond (bullish flip) - SAR={latest['sar']:.2f} > {lower_threshold} (not strong)")
        else:
            print(f"    DEBUG: Small diamond (bearish flip) - SAR={latest['sar']:.2f} < {upper_threshold} (not strong)")
    
    return signals