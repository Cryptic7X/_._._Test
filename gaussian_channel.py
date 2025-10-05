"""
Gaussian Channel Indicator - Exact DonovanWall Pine Script Implementation
100% accurate calculation matching TradingView's Gaussian Channel [DW]
"""

import numpy as np
import pandas as pd


class GaussianChannel:
    """
    Gaussian Channel Indicator using Ehlers Gaussian Filter technique
    
    Parameters:
    - poles: Number of filter poles (1-9), default 4
    - period: Sampling period, default 144
    - tr_multiplier: Filtered True Range multiplier for bands, default 1.414
    - reduced_lag: Enable reduced lag mode, default True
    - fast_response: Enable fast response mode, default False
    """
    
    def __init__(self, poles=4, period=144, tr_multiplier=1.414, reduced_lag=True, fast_response=False):
        self.poles = poles
        self.period = period
        self.tr_multiplier = tr_multiplier
        self.reduced_lag = reduced_lag
        self.fast_response = fast_response
        
    def calculate_alpha_beta(self):
        """Calculate Gaussian filter coefficients - exact Pine Script formula"""
        pi = 4 * np.arcsin(1)  # Pine Script: 4*asin(1)
        beta = (1 - np.cos(pi / self.period)) / (pow(1.414, 2/self.poles) - 1)
        alpha = -beta + np.sqrt(beta**2 + 2*beta)
        return alpha, beta
    
    def get_weights(self, poles):
        """Get exact weights from Pine Script conditional logic"""
        weights = {
            'm2': {9: 36, 8: 28, 7: 21, 6: 15, 5: 10, 4: 6, 3: 3, 2: 1}.get(poles, 0),
            'm3': {9: 84, 8: 56, 7: 35, 6: 20, 5: 10, 4: 4, 3: 1}.get(poles, 0),
            'm4': {9: 126, 8: 70, 7: 35, 6: 15, 5: 5, 4: 1}.get(poles, 0),
            'm5': {9: 126, 8: 56, 7: 21, 6: 6, 5: 1}.get(poles, 0),
            'm6': {9: 84, 8: 28, 7: 7, 6: 1}.get(poles, 0),
            'm7': {9: 36, 8: 8, 7: 1}.get(poles, 0),
            'm8': {9: 9, 8: 1}.get(poles, 0),
            'm9': {9: 1}.get(poles, 0)
        }
        return weights
    
    def apply_filter(self, source, alpha, poles):
        """
        Apply Gaussian filter - exact Pine Script f_filt9x function
        This is a recursive IIR filter with alternating signs
        """
        n = len(source)
        filtered = np.zeros(n)
        x = 1 - alpha
        weights = self.get_weights(poles)
        
        for i in range(n):
            # Base term: alpha^poles * source
            filt = pow(alpha, poles) * source[i]
            
            # Add pole terms using previous filter values
            if i >= 1:
                filt += poles * x * filtered[i-1]
            
            if poles >= 2 and i >= 2:
                filt -= weights['m2'] * pow(x, 2) * filtered[i-2]
            
            if poles >= 3 and i >= 3:
                filt += weights['m3'] * pow(x, 3) * filtered[i-3]
            
            if poles >= 4 and i >= 4:
                filt -= weights['m4'] * pow(x, 4) * filtered[i-4]
            
            if poles >= 5 and i >= 5:
                filt += weights['m5'] * pow(x, 5) * filtered[i-5]
            
            if poles >= 6 and i >= 6:
                filt -= weights['m6'] * pow(x, 6) * filtered[i-6]
            
            if poles >= 7 and i >= 7:
                filt += weights['m7'] * pow(x, 7) * filtered[i-7]
            
            if poles >= 8 and i >= 8:
                filt -= weights['m8'] * pow(x, 8) * filtered[i-8]
            
            if poles == 9 and i >= 9:
                filt += weights['m9'] * pow(x, 9) * filtered[i-9]
            
            filtered[i] = filt
        
        return filtered
    
    def calculate(self, df):
        """
        Calculate Gaussian Channel bands on OHLCV dataframe
        
        Args:
            df: DataFrame with columns ['open', 'high', 'low', 'close', 'volume']
            
        Returns:
            DataFrame with added columns: filter, upper_band, lower_band
        """
        df = df.copy()
        alpha, beta = self.calculate_alpha_beta()
        
        # Calculate HLC3 source
        df['hlc3'] = (df['high'] + df['low'] + df['close']) / 3
        
        # Calculate True Range - exact Pine Script tr(true) function
        prev_close = df['close'].shift(1)
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - prev_close),
                abs(df['low'] - prev_close)
            )
        )
        df['tr'] = df['tr'].fillna(df['high'] - df['low'])
        
        # Calculate lag for reduced lag mode
        lag = int((self.period - 1) / (2 * self.poles))
        
        # Prepare source data with lag reduction if enabled
        if self.reduced_lag:
            src_lag = df['hlc3'].shift(lag)
            tr_lag = df['tr'].shift(lag)
            df['srcdata'] = df['hlc3'] + (df['hlc3'] - src_lag)
            df['trdata'] = df['tr'] + (df['tr'] - tr_lag)
        else:
            df['srcdata'] = df['hlc3']
            df['trdata'] = df['tr']
        
        # Fill NaN values
        df['srcdata'] = df['srcdata'].fillna(df['hlc3'])
        df['trdata'] = df['trdata'].fillna(df['tr'])
        
        # Apply Gaussian filter to source (filtn)
        filtn = self.apply_filter(df['srcdata'].values, alpha, self.poles)
        
        # Apply Gaussian filter to true range (filtntr)
        filtntr = self.apply_filter(df['trdata'].values, alpha, self.poles)
        
        # Apply 1-pole filter for fast response mode
        if self.fast_response:
            filt1 = self.apply_filter(df['srcdata'].values, alpha, 1)
            filt1tr = self.apply_filter(df['trdata'].values, alpha, 1)
            df['filter'] = (filtn + filt1) / 2
            df['filter_tr'] = (filtntr + filt1tr) / 2
        else:
            df['filter'] = filtn
            df['filter_tr'] = filtntr
        
        # Calculate upper and lower bands
        df['upper_band'] = df['filter'] + df['filter_tr'] * self.tr_multiplier
        df['lower_band'] = df['filter'] - df['filter_tr'] * self.tr_multiplier
        
        return df
