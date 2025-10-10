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

def detect_all_signals(df, upper_threshold=70, lower_threshold=30):
    """
    Detect ALL Parabolic RSI signals (both regular and strong) exactly as in Pine Script:
    
    Regular Signals (Small Diamonds):
    - sig_up = isBelow != isBelow[1] and isBelow and barstate.isconfirmed  
    - sig_dn = isBelow != isBelow[1] and not isBelow and barstate.isconfirmed
    
    Strong Signals (Big Diamonds):
    - s_sig_up = isBelow != isBelow[1] and isBelow and barstate.isconfirmed and sar_rsi <= lower_
    - s_sig_dn = isBelow != isBelow[1] and not isBelow and barstate.isconfirmed and sar_rsi >= upper_
    
    Chart Signals (what appears on price chart):
    - Chart Strong Rsi Up = s_sig_up
    - Chart Strong Rsi Dn = s_sig_dn  
    - Chart Rsi Up = sig_up and sar_rsi >= lower_
    - Chart Rsi Dn = sig_dn and sar_rsi <= upper_
    """
    if len(df) < 2:
        return []
    
    latest = df.iloc[-1]
    previous = df.iloc[-2]
    
    signals = []
    
    # Check if we have valid data
    if pd.isna(latest['sar']) or pd.isna(previous['sar']):
        return signals
    
    # Check for SAR direction flip (equivalent to barstate.isconfirmed)
    sar_flipped = latest['is_below'] != previous['is_below']
    
    if not sar_flipped:
        return signals
    
    # Regular Signals (Small Diamonds) - SAR direction flip only
    if latest['is_below']:  # SAR flipped to bullish
        # sig_up = isBelow != isBelow[1] and isBelow and barstate.isconfirmed
        signals.append('REGULAR_BUY')
        
        # Strong signal condition: also check if SAR <= 30
        if latest['sar'] <= lower_threshold:
            # s_sig_up = isBelow != isBelow[1] and isBelow and barstate.isconfirmed and sar_rsi <= lower_
            signals.append('STRONG_BUY')
    
    else:  # SAR flipped to bearish  
        # sig_dn = isBelow != isBelow[1] and not isBelow and barstate.isconfirmed
        signals.append('REGULAR_SELL')
        
        # Strong signal condition: also check if SAR >= 70
        if latest['sar'] >= upper_threshold:
            # s_sig_dn = isBelow != isBelow[1] and not isBelow and barstate.isconfirmed and sar_rsi >= upper_
            signals.append('STRONG_SELL')
    
    # Chart signals (what shows on price chart)
    chart_signals = []
    
    if 'STRONG_BUY' in signals:
        chart_signals.append('CHART_STRONG_BUY')  # Big diamond below bar
    elif 'REGULAR_BUY' in signals and latest['sar'] >= lower_threshold:
        chart_signals.append('CHART_REGULAR_BUY')  # Small diamond below bar
        
    if 'STRONG_SELL' in signals:
        chart_signals.append('CHART_STRONG_SELL')  # Big diamond above bar  
    elif 'REGULAR_SELL' in signals and latest['sar'] <= upper_threshold:
        chart_signals.append('CHART_REGULAR_SELL')  # Small diamond above bar
    
    # Combine all signals
    all_signals = signals + chart_signals
    
    return all_signals

def is_signal_fresh(candle_timestamp, current_time, freshness_window_hours=1):
    """
    Check if signal is fresh (within freshness window)
    Equivalent to barstate.isconfirmed - only alert on completed candles that are recent
    """
    if isinstance(candle_timestamp, str):
        candle_time = datetime.fromisoformat(candle_timestamp.replace('Z', '+00:00'))
    else:
        candle_time = pd.to_datetime(candle_timestamp)
    
    if isinstance(current_time, str):
        current_time = datetime.fromisoformat(current_time.replace('Z', '+00:00'))
    elif not isinstance(current_time, datetime):
        current_time = pd.to_datetime(current_time)
    
    # Make timezone-aware if needed
    if candle_time.tzinfo is None:
        candle_time = candle_time.replace(tzinfo=None)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=None)
    
    time_diff = current_time - candle_time
    freshness_window = timedelta(hours=freshness_window_hours)
    
    return time_diff <= freshness_window

def should_alert(symbol, signals, candle_timestamp, last_alerts_db, current_time):
    """
    Determine if we should send alert based on:
    1. Signal freshness (within 1 hour)
    2. No duplicate alerts for same symbol+signal combination
    """
    if not signals:
        return False, []
    
    # Check freshness
    if not is_signal_fresh(candle_timestamp, current_time):
        return False, []
    
    # Check for duplicates
    fresh_signals = []
    current_time_dt = pd.to_datetime(current_time)
    
    for signal in signals:
        signal_key = f"{symbol}_{signal}"
        
        # Check if we've alerted this signal recently (within 2 hours to prevent spam)
        if signal_key in last_alerts_db:
            last_alert_time = pd.to_datetime(last_alerts_db[signal_key])
            time_since_last = current_time_dt - last_alert_time
            
            # Don't alert same signal within 2 hours
            if time_since_last < timedelta(hours=2):
                continue
        
        fresh_signals.append(signal)
        # Update last alert time
        last_alerts_db[signal_key] = current_time_dt.isoformat()
    
    return len(fresh_signals) > 0, fresh_signals
