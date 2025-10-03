#!/usr/bin/env python3
"""
Band Cross Detector - Detects when candle bodies cross Gaussian Channel bands
"""

import pandas as pd
from typing import Dict, List, Optional
from enum import Enum


class CrossType(Enum):
    """Types of band crosses."""
    UPPER_BAND = "upper_band"
    LOWER_BAND = "lower_band"
    FILTER_LINE = "filter_line"
    NONE = "none"


class BandDetector:
    """
    Detects band crosses for Gaussian Channel alerts.
    
    For 30-minute analysis: Detects upper_band and lower_band crosses only
    For 4-hour analysis: Detects filter, upper_band, and lower_band crosses
    """
    
    def __init__(self, analysis_type: str = "30m"):
        """
        Args:
            analysis_type: Either "30m" or "4h"
        """
        self.analysis_type = analysis_type
    
    def detect_cross(self, df: pd.DataFrame, check_filter: bool = False) -> List[Dict]:
        """
        Detect band crosses in the most recent closed candle.
        
        Args:
            df: DataFrame with Gaussian Channel data
            check_filter: If True, also check filter line crosses (for 4h analysis)
        
        Returns:
            List of cross events with details
        """
        if len(df) < 2:
            return []
        
        # Get the last closed candle (previous to current)
        current = df.iloc[-1]
        previous = df.iloc[-2]
        
        crosses = []
        
        # Check candle body (open and close)
        candle_high = max(current['open'], current['close'])
        candle_low = min(current['open'], current['close'])
        
        prev_candle_high = max(previous['open'], previous['close'])
        prev_candle_low = min(previous['open'], previous['close'])
        
        # Check Upper Band Cross
        if self._is_crossing_upper(candle_high, candle_low, 
                                   current['upper_band'],
                                   prev_candle_high, prev_candle_low,
                                   previous['upper_band']):
            crosses.append({
                'type': CrossType.UPPER_BAND.value,
                'timestamp': current['timestamp'],
                'close': current['close'],
                'upper_band': current['upper_band'],
                'direction': 'above' if current['close'] > current['upper_band'] else 'touch'
            })
        
        # Check Lower Band Cross
        if self._is_crossing_lower(candle_high, candle_low,
                                   current['lower_band'],
                                   prev_candle_high, prev_candle_low,
                                   previous['lower_band']):
            crosses.append({
                'type': CrossType.LOWER_BAND.value,
                'timestamp': current['timestamp'],
                'close': current['close'],
                'lower_band': current['lower_band'],
                'direction': 'below' if current['close'] < current['lower_band'] else 'touch'
            })
        
        # Check Filter Line Cross (only for 4h analysis)
        if check_filter and self.analysis_type == "4h":
            if self._is_crossing_filter(candle_high, candle_low,
                                        current['filter'],
                                        prev_candle_high, prev_candle_low,
                                        previous['filter']):
                crosses.append({
                    'type': CrossType.FILTER_LINE.value,
                    'timestamp': current['timestamp'],
                    'close': current['close'],
                    'filter': current['filter'],
                    'direction': 'above' if current['close'] > current['filter'] else 'below'
                })
        
        return crosses
    
    def _is_crossing_upper(self, candle_high: float, candle_low: float,
                          upper_band: float,
                          prev_high: float, prev_low: float,
                          prev_upper: float) -> bool:
        """Check if candle body is crossing upper band."""
        # Current candle body touches or crosses upper band
        current_crosses = candle_high >= upper_band
        
        # Previous candle was below upper band
        previous_below = prev_high < prev_upper
        
        return current_crosses and previous_below
    
    def _is_crossing_lower(self, candle_high: float, candle_low: float,
                          lower_band: float,
                          prev_high: float, prev_low: float,
                          prev_lower: float) -> bool:
        """Check if candle body is crossing lower band."""
        # Current candle body touches or crosses lower band
        current_crosses = candle_low <= lower_band
        
        # Previous candle was above lower band
        previous_above = prev_low > prev_lower
        
        return current_crosses and previous_above
    
    def _is_crossing_filter(self, candle_high: float, candle_low: float,
                           filter_line: float,
                           prev_high: float, prev_low: float,
                           prev_filter: float) -> bool:
        """Check if candle body is crossing filter line."""
        # Check if candle body crosses from one side to another
        current_above = candle_low > filter_line
        current_below = candle_high < filter_line
        
        prev_above = prev_low > prev_filter
        prev_below = prev_high < prev_filter
        
        # Cross from below to above or above to below
        return (current_above and prev_below) or (current_below and prev_above)
    
    def format_alert_message(self, symbol: str, crosses: List[Dict]) -> str:
        """
        Format consolidated alert message for multiple crosses.
        
        Args:
            symbol: Trading pair symbol
            crosses: List of cross events
        
        Returns:
            Formatted alert message
        """
        if not crosses:
            return ""
        
        # Consolidate multiple crosses into single message
        cross_types = [c['type'] for c in crosses]
        timestamp = crosses[0]['timestamp']
        close_price = crosses[0]['close']
        
        if len(crosses) == 1:
            cross = crosses[0]
            if cross['type'] == CrossType.UPPER_BAND.value:
                band_value = cross['upper_band']
                return (f"🔴 {symbol} | Upper Band Cross\n"
                       f"Time: {timestamp}\n"
                       f"Close: {close_price:.8f}\n"
                       f"Upper Band: {band_value:.8f}\n"
                       f"Direction: {cross['direction']}")
            elif cross['type'] == CrossType.LOWER_BAND.value:
                band_value = cross['lower_band']
                return (f"🟢 {symbol} | Lower Band Cross\n"
                       f"Time: {timestamp}\n"
                       f"Close: {close_price:.8f}\n"
                       f"Lower Band: {band_value:.8f}\n"
                       f"Direction: {cross['direction']}")
            elif cross['type'] == CrossType.FILTER_LINE.value:
                filter_value = cross['filter']
                return (f"🟡 {symbol} | Filter Line Cross\n"
                       f"Time: {timestamp}\n"
                       f"Close: {close_price:.8f}\n"
                       f"Filter: {filter_value:.8f}\n"
                       f"Direction: {cross['direction']}")
        else:
            # Multiple crosses in same candle
            cross_names = ", ".join([c.replace('_', ' ').title() for c in cross_types])
            return (f"⚠️ {symbol} | Multiple Band Cross\n"
                   f"Time: {timestamp}\n"
                   f"Close: {close_price:.8f}\n"
                   f"Crosses: {cross_names}")
        
        return ""


# Test function
if __name__ == "__main__":
    import numpy as np
    
    # Create test data
    data = {
        'timestamp': pd.date_range('2024-01-01', periods=50, freq='15min'),
        'open': np.linspace(100, 105, 50),
        'close': np.linspace(100, 105, 50),
        'high': np.linspace(101, 106, 50),
        'low': np.linspace(99, 104, 50),
        'filter': np.linspace(100, 104, 50),
        'upper_band': np.linspace(102, 106, 50),
        'lower_band': np.linspace(98, 102, 50)
    }
    df = pd.DataFrame(data)
    
    # Simulate a cross
    df.loc[df.index[-1], 'close'] = 107  # Above upper band
    
    detector = BandDetector(analysis_type="30m")
    crosses = detector.detect_cross(df)
    
    print("\n✅ Band Cross Detection Test")
    print("=" * 60)
    print(f"Detected crosses: {len(crosses)}")
    for cross in crosses:
        print(f"  - {cross}")
        message = detector.format_alert_message("BTC-USDT", [cross])
        print(f"\nAlert Message:\n{message}")
