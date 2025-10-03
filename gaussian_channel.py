#!/usr/bin/env python3
"""
Gaussian Channel Calculator - Python Port from Pine Script
Based on DonovanWall's Gaussian Channel [DW]
https://www.tradingview.com/script/WpVY7GKW-Gaussian-Channel-DW/
"""

import numpy as np
import pandas as pd
from typing import Tuple, List
import math


class GaussianChannel:
    """
    Gaussian Channel implementation using Ehlers Gaussian Filter technique.
    
    Parameters:
    - poles: Number of poles (1-9), default=4
    - period: Sampling period, default=144
    - multiplier: True range multiplier, default=1.414
    - mode_lag: Reduced lag mode, default=False
    - mode_fast: Fast response mode, default=False
    """
    
    def __init__(self, poles: int = 4, period: int = 144, 
                 multiplier: float = 1.414, mode_lag: bool = False, 
                 mode_fast: bool = False):
        self.poles = poles
        self.period = period
        self.multiplier = multiplier
        self.mode_lag = mode_lag
        self.mode_fast = mode_fast
        
        # Calculate beta and alpha
        self.beta = (1 - math.cos(4 * math.asin(1) / period)) / (math.pow(1.414, 2/poles) - 1)
        self.alpha = -self.beta + math.sqrt(math.pow(self.beta, 2) + 2 * self.beta)
        
        # Calculate lag
        self.lag = int((period - 1) / (2 * poles))
    
    def _get_weights(self, poles: int) -> List[int]:
        """Get weights for filter calculation based on number of poles."""
        weights = {
            1: [0, 0, 0, 0, 0, 0, 0, 0, 0],
            2: [1, 0, 0, 0, 0, 0, 0, 0, 0],
            3: [3, 1, 0, 0, 0, 0, 0, 0, 0],
            4: [6, 4, 1, 0, 0, 0, 0, 0, 0],
            5: [10, 10, 5, 1, 0, 0, 0, 0, 0],
            6: [15, 20, 15, 6, 1, 0, 0, 0, 0],
            7: [21, 35, 35, 21, 7, 1, 0, 0, 0],
            8: [28, 56, 70, 56, 28, 8, 1, 0, 0],
            9: [36, 84, 126, 126, 84, 36, 9, 1, 0]
        }
        return weights.get(poles, [0] * 9)
    
    def _filter_function(self, alpha: float, source: pd.Series, poles: int) -> pd.Series:
        """Calculate Gaussian filter for given source data."""
        result = pd.Series(index=source.index, dtype=float)
        result.iloc[:] = 0.0
        
        x = 1 - alpha
        weights = self._get_weights(poles)
        
        for i in range(len(source)):
            if i == 0:
                result.iloc[i] = math.pow(alpha, poles) * source.iloc[i]
            else:
                val = math.pow(alpha, poles) * source.iloc[i]
                
                # Add weighted previous values
                val += poles * x * result.iloc[i-1]
                
                if poles >= 2 and i >= 2:
                    val -= weights[0] * math.pow(x, 2) * result.iloc[i-2]
                if poles >= 3 and i >= 3:
                    val += weights[1] * math.pow(x, 3) * result.iloc[i-3]
                if poles >= 4 and i >= 4:
                    val -= weights[2] * math.pow(x, 4) * result.iloc[i-4]
                if poles >= 5 and i >= 5:
                    val += weights[3] * math.pow(x, 5) * result.iloc[i-5]
                if poles >= 6 and i >= 6:
                    val -= weights[4] * math.pow(x, 6) * result.iloc[i-6]
                if poles >= 7 and i >= 7:
                    val += weights[5] * math.pow(x, 7) * result.iloc[i-7]
                if poles >= 8 and i >= 8:
                    val -= weights[6] * math.pow(x, 8) * result.iloc[i-8]
                if poles == 9 and i >= 9:
                    val += weights[7] * math.pow(x, 9) * result.iloc[i-9]
                
                result.iloc[i] = val
        
        return result
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Gaussian Channel for given OHLCV dataframe.
        
        Args:
            df: DataFrame with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        
        Returns:
            DataFrame with additional columns: 'filter', 'upper_band', 'lower_band'
        """
        df = df.copy()
        
        # Calculate HLC3 source
        df['hlc3'] = (df['high'] + df['low'] + df['close']) / 3
        
        # Calculate True Range
        df['prev_close'] = df['close'].shift(1)
        df['tr'] = df.apply(lambda row: max(
            row['high'] - row['low'],
            abs(row['high'] - row['prev_close']) if pd.notna(row['prev_close']) else 0,
            abs(row['low'] - row['prev_close']) if pd.notna(row['prev_close']) else 0
        ), axis=1)
        
        # Apply lag reduction if enabled
        if self.mode_lag and self.lag > 0:
            df['src_data'] = df['hlc3'] + (df['hlc3'] - df['hlc3'].shift(self.lag))
            df['tr_data'] = df['tr'] + (df['tr'] - df['tr'].shift(self.lag))
        else:
            df['src_data'] = df['hlc3']
            df['tr_data'] = df['tr']
        
        # Fill NaN values
        df['src_data'] = df['src_data'].fillna(df['hlc3'])
        df['tr_data'] = df['tr_data'].fillna(df['tr'])
        
        # Calculate N-pole filter
        filt_n = self._filter_function(self.alpha, df['src_data'], self.poles)
        filt_n_tr = self._filter_function(self.alpha, df['tr_data'], self.poles)
        
        # Calculate 1-pole filter for fast response mode
        if self.mode_fast:
            filt_1 = self._filter_function(self.alpha, df['src_data'], 1)
            filt_1_tr = self._filter_function(self.alpha, df['tr_data'], 1)
            
            df['filter'] = (filt_n + filt_1) / 2
            df['filt_tr'] = (filt_n_tr + filt_1_tr) / 2
        else:
            df['filter'] = filt_n
            df['filt_tr'] = filt_n_tr
        
        # Calculate bands
        df['upper_band'] = df['filter'] + df['filt_tr'] * self.multiplier
        df['lower_band'] = df['filter'] - df['filt_tr'] * self.multiplier
        
        # Clean up intermediate columns
        df = df.drop(columns=['hlc3', 'prev_close', 'tr', 'src_data', 'tr_data', 'filt_tr'])
        
        return df
    
    def get_latest_values(self, df: pd.DataFrame) -> dict:
        """Get the latest Gaussian Channel values."""
        if len(df) == 0:
            return None
        
        latest = df.iloc[-1]
        return {
            'timestamp': latest['timestamp'],
            'close': latest['close'],
            'filter': latest['filter'],
            'upper_band': latest['upper_band'],
            'lower_band': latest['lower_band']
        }


# Test function
if __name__ == "__main__":
    # Example usage
    data = {
        'timestamp': pd.date_range('2024-01-01', periods=200, freq='15min'),
        'open': np.random.randn(200).cumsum() + 100,
        'high': np.random.randn(200).cumsum() + 102,
        'low': np.random.randn(200).cumsum() + 98,
        'close': np.random.randn(200).cumsum() + 100,
        'volume': np.random.randint(1000, 10000, 200)
    }
    df = pd.DataFrame(data)
    
    gc = GaussianChannel(poles=4, period=144, multiplier=1.414)
    result = gc.calculate(df)
    
    print("\n✅ Gaussian Channel Calculation Test")
    print("=" * 60)
    print(result[['timestamp', 'close', 'filter', 'upper_band', 'lower_band']].tail())
    print("\n✅ Latest values:")
    print(gc.get_latest_values(result))
