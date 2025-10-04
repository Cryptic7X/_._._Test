#!/usr/bin/env python3
"""
Gaussian Channel Calculator - Matches Pine Script exactly
Based on Donovan Wall's TradingView indicator
"""

import numpy as np

class GaussianChannel:
    def __init__(self, poles=4, period=144, multiplier=1.414, reduced_lag=False, fast_response=False):
        """
        Initialize Gaussian Channel
        
        Args:
            poles: Number of poles (1-9)
            period: Sampling period
            multiplier: True range multiplier
            reduced_lag: Enable lag reduction
            fast_response: Enable fast response mode
        """
        self.poles = poles
        self.period = period
        self.multiplier = multiplier
        self.reduced_lag = reduced_lag
        self.fast_response = fast_response
        
        # Calculate beta and alpha (from Pine Script)
        beta = (1 - np.cos(4 * np.arcsin(1) / period)) / (np.power(1.414, 2/poles) - 1)
        self.alpha = -beta + np.sqrt(beta**2 + 2*beta)
        
        # Calculate lag
        self.lag = int((period - 1) / (2 * poles))
    
    def _true_range(self, high, low, close):
        """Calculate True Range"""
        tr = np.zeros(len(high))
        tr[0] = high[0] - low[0]
        
        for i in range(1, len(high)):
            tr[i] = max(
                high[i] - low[i],
                abs(high[i] - close[i-1]),
                abs(low[i] - close[i-1])
            )
        
        return tr
    
    def _apply_pole_filter(self, data, poles):
        """
        Apply N-pole Gaussian filter
        This is the core recursive filter from Pine Script
        """
        n = len(data)
        result = np.zeros(n)
        alpha = self.alpha
        x = 1 - alpha
        
        # Get binomial coefficients for this pole count
        coeffs = self._get_coefficients(poles)
        
        for i in range(n):
            # Start with alpha^poles * current_data
            val = (alpha ** poles) * data[i]
            
            # Add contributions from previous filtered values
            for p in range(1, min(i + 1, 10)):
                if p == 1 and poles >= 1:
                    val += poles * x * result[i-1]
                elif p == 2 and poles >= 2:
                    val -= coeffs[0] * (x**2) * result[i-2]
                elif p == 3 and poles >= 3:
                    val += coeffs[1] * (x**3) * result[i-3]
                elif p == 4 and poles >= 4:
                    val -= coeffs[2] * (x**4) * result[i-4]
                elif p == 5 and poles >= 5:
                    val += coeffs[3] * (x**5) * result[i-5]
                elif p == 6 and poles >= 6:
                    val -= coeffs[4] * (x**6) * result[i-6]
                elif p == 7 and poles >= 7:
                    val += coeffs[5] * (x**7) * result[i-7]
                elif p == 8 and poles >= 8:
                    val -= coeffs[6] * (x**8) * result[i-8]
                elif p == 9 and poles >= 9:
                    val += coeffs[7] * (x**9) * result[i-9]
            
            result[i] = val
        
        return result
    
    def _get_coefficients(self, poles):
        """Get binomial coefficients for N poles (from Pine Script)"""
        if poles == 1:
            return [0, 0, 0, 0, 0, 0, 0, 0]
        elif poles == 2:
            return [1, 0, 0, 0, 0, 0, 0, 0]
        elif poles == 3:
            return [3, 1, 0, 0, 0, 0, 0, 0]
        elif poles == 4:
            return [6, 4, 1, 0, 0, 0, 0, 0]
        elif poles == 5:
            return [10, 10, 5, 1, 0, 0, 0, 0]
        elif poles == 6:
            return [15, 20, 15, 6, 1, 0, 0, 0]
        elif poles == 7:
            return [21, 35, 35, 21, 7, 1, 0, 0]
        elif poles == 8:
            return [28, 56, 70, 56, 28, 8, 1, 0]
        elif poles == 9:
            return [36, 84, 126, 126, 84, 36, 9, 1]
        else:
            return [0, 0, 0, 0, 0, 0, 0, 0]
    
    def calculate(self, high, low, close):
        """
        Calculate Gaussian Channel
        
        Args:
            high: High prices array
            low: Low prices array
            close: Close prices array
        
        Returns:
            Tuple of (filter_line, upper_band, lower_band)
        """
        # Calculate source (HLC3)
        src = (high + low + close) / 3.0
        
        # Calculate True Range
        tr = self._true_range(high, low, close)
        
        # Apply lag reduction if enabled
        if self.reduced_lag and self.lag > 0:
            srcdata = np.copy(src)
            trdata = np.copy(tr)
            
            for i in range(self.lag, len(src)):
                srcdata[i] = src[i] + (src[i] - src[i - self.lag])
                trdata[i] = tr[i] + (tr[i] - tr[i - self.lag])
        else:
            srcdata = src
            trdata = tr
        
        # Apply Gaussian filter with N poles
        filtn = self._apply_pole_filter(srcdata, self.poles)
        filtntr = self._apply_pole_filter(trdata, self.poles)
        
        # Apply 1-pole filter (for fast response mode)
        if self.fast_response:
            filt1 = self._apply_pole_filter(srcdata, 1)
            filt1tr = self._apply_pole_filter(trdata, 1)
            
            filt = (filtn + filt1) / 2
            filttr = (filtntr + filt1tr) / 2
        else:
            filt = filtn
            filttr = filtntr
        
        # Calculate bands
        upper_band = filt + filttr * self.multiplier
        lower_band = filt - filttr * self.multiplier
        
        return filt, upper_band, lower_band
