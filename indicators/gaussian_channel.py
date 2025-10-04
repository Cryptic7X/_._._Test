#!/usr/bin/env python3
"""
Gaussian Channel Calculator - Direct Port from Pine Script
Supports all 9 poles with exact Pine Script logic
"""

import numpy as np
import math
from typing import Tuple, List

class GaussianChannel:
    def __init__(self, poles: int = 4, period: int = 144, multiplier: float = 1.414, 
                 reduced_lag: bool = False, fast_response: bool = False):
        """
        Initialize Gaussian Channel with Pine Script parameters
        
        Args:
            poles: Number of poles (1-9)
            period: Sampling period
            multiplier: True range multiplier for bands
            reduced_lag: Reduced lag mode
            fast_response: Fast response mode
        """
        self.poles = max(1, min(9, poles))
        self.period = max(2, period)
        self.multiplier = multiplier
        self.reduced_lag = reduced_lag
        self.fast_response = fast_response
        
        # Calculate beta and alpha (Pine Script logic)
        self.beta = (1 - math.cos(4 * math.asin(1) / self.period)) / (pow(1.414, 2 / self.poles) - 1)
        self.alpha = -self.beta + math.sqrt(pow(self.beta, 2) + 2 * self.beta)
        
        # Lag calculation
        self.lag = int((self.period - 1) / (2 * self.poles))
    
    def _get_weights(self, poles: int) -> List[int]:
        """Get binomial coefficient weights for filter calculation"""
        weights = [poles]  # m1 = poles
        
        # m2
        if poles >= 2:
            m2_map = {9: 36, 8: 28, 7: 21, 6: 15, 5: 10, 4: 6, 3: 3, 2: 1}
            weights.append(m2_map.get(poles, 0))
        else:
            weights.append(0)
        
        # m3
        if poles >= 3:
            m3_map = {9: 84, 8: 56, 7: 35, 6: 20, 5: 10, 4: 4, 3: 1}
            weights.append(m3_map.get(poles, 0))
        else:
            weights.append(0)
        
        # m4
        if poles >= 4:
            m4_map = {9: 126, 8: 70, 7: 35, 6: 15, 5: 5, 4: 1}
            weights.append(m4_map.get(poles, 0))
        else:
            weights.append(0)
        
        # m5
        if poles >= 5:
            m5_map = {9: 126, 8: 56, 7: 21, 6: 6, 5: 1}
            weights.append(m5_map.get(poles, 0))
        else:
            weights.append(0)
        
        # m6
        if poles >= 6:
            m6_map = {9: 84, 8: 28, 7: 7, 6: 1}
            weights.append(m6_map.get(poles, 0))
        else:
            weights.append(0)
        
        # m7
        if poles >= 7:
            m7_map = {9: 36, 8: 8, 7: 1}
            weights.append(m7_map.get(poles, 0))
        else:
            weights.append(0)
        
        # m8
        if poles >= 8:
            m8_map = {9: 9, 8: 1}
            weights.append(m8_map.get(poles, 0))
        else:
            weights.append(0)
        
        # m9
        if poles >= 9:
            weights.append(1)
        else:
            weights.append(0)
        
        return weights
    
    def _calculate_filter(self, source: np.ndarray, poles: int) -> np.ndarray:
        """
        Calculate Gaussian filter for given poles
        Direct port of Pine Script f_filt9x function
        """
        n = len(source)
        filt = np.zeros(n)
        alpha = self.alpha
        x = 1 - alpha
        
        weights = self._get_weights(poles)
        
        for i in range(n):
            if i < 10:
                filt[i] = source[i]
            else:
                # Pine Script filter formula
                val = pow(alpha, poles) * source[i]
                val += weights[0] * x * filt[i-1]
                
                if poles >= 2:
                    val -= weights[1] * pow(x, 2) * filt[i-2]
                if poles >= 3:
                    val += weights[2] * pow(x, 3) * filt[i-3]
                if poles >= 4:
                    val -= weights[3] * pow(x, 4) * filt[i-4]
                if poles >= 5:
                    val += weights[4] * pow(x, 5) * filt[i-5]
                if poles >= 6:
                    val -= weights[5] * pow(x, 6) * filt[i-6]
                if poles >= 7:
                    val += weights[6] * pow(x, 7) * filt[i-7]
                if poles >= 8:
                    val -= weights[7] * pow(x, 8) * filt[i-8]
                if poles >= 9:
                    val += weights[8] * pow(x, 9) * filt[i-9]
                
                filt[i] = val
        
        return filt
    
    def calculate(self, high: np.ndarray, low: np.ndarray, close: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculate Gaussian Channel (filter line, upper band, lower band)
        
        Args:
            high: High prices
            low: Low prices
            close: Close prices
        
        Returns:
            Tuple of (filter, upper_band, lower_band)
        """
        # Calculate HLC3 source
        hlc3 = (high + low + close) / 3
        
        # Calculate true range
        n = len(close)
        tr = np.zeros(n)
        tr[0] = high[0] - low[0]
        for i in range(1, n):
            tr[i] = max(
                high[i] - low[i],
                abs(high[i] - close[i-1]),
                abs(low[i] - close[i-1])
            )
        
        # Apply lag reduction if enabled
        if self.reduced_lag and n > self.lag:
            srcdata = hlc3.copy()
            trdata = tr.copy()
            for i in range(self.lag, n):
                srcdata[i] = hlc3[i] + (hlc3[i] - hlc3[i - self.lag])
                trdata[i] = tr[i] + (tr[i] - tr[i - self.lag])
        else:
            srcdata = hlc3
            trdata = tr
        
        # Calculate N-pole filters
        filtn = self._calculate_filter(srcdata, self.poles)
        filtntr = self._calculate_filter(trdata, self.poles)
        
        # Calculate 1-pole filters for fast response mode
        if self.fast_response:
            filt1 = self._calculate_filter(srcdata, 1)
            filt1tr = self._calculate_filter(trdata, 1)
            
            # Average N-pole and 1-pole
            filt = (filtn + filt1) / 2
            filttr = (filtntr + filt1tr) / 2
        else:
            filt = filtn
            filttr = filtntr
        
        # Calculate bands
        upper_band = filt + filttr * self.multiplier
        lower_band = filt - filttr * self.multiplier
        
        return filt, upper_band, lower_band