import pandas as pd
import numpy as np

def ema(series, length):
    return series.ewm(span=length, adjust=False).mean()

def sma(series, length):
    return series.rolling(window=length).mean()

def detect_exact_cipherb_signals(df, config=None):
    wtChannelLen = 9
    wtAverageLen = 12
    wtMALen = 3
    osLevel2 = -60
    obLevel2 = 60
    
    hlc3 = (df['high'] + df['low'] + df['close']) / 3
    
    esa = ema(hlc3, wtChannelLen)
    de = ema(abs(hlc3 - esa), wtChannelLen)
    ci = (hlc3 - esa) / (0.015 * de)
    wt1 = ema(ci, wtAverageLen)
    wt2 = sma(wt1, wtMALen)
    
    signals = pd.DataFrame(index=df.index)
    signals['wt1'] = wt1
    signals['wt2'] = wt2
    
    wt1_prev = wt1.shift(1)
    wt2_prev = wt2.shift(1)
    
    wtCross = ((wt1 > wt2) & (wt1_prev <= wt2_prev)) | ((wt1 < wt2) & (wt1_prev >= wt2_prev))
    wtCrossUp = (wt2 - wt1) <= 0
    wtCrossDown = (wt2 - wt1) >= 0
    
    wtOversold = (wt1 <= osLevel2) & (wt2 <= osLevel2)
    wtOverbought = (wt2 >= obLevel2) & (wt1 >= obLevel2)
    
    signals['buySignal'] = wtCross & wtCrossUp & wtOversold
    signals['sellSignal'] = wtCross & wtCrossDown & wtOverbought
    
    return signals
