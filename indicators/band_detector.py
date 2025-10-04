#!/usr/bin/env python3
"""
Band Cross Detector - SIMPLE LOGIC
Only alerts when candle body ACTUALLY crosses a band line
"""

import json
import os
from datetime import datetime
from typing import Dict, Optional

class BandCrossDetector:
    def __init__(self, state_file: str = 'cache/gc_alert_state.json'):
        """Initialize band cross detector"""
        self.state_file = state_file
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        """Load alert state from file"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _save_state(self):
        """Save alert state to file"""
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def _get_coin_state(self, symbol: str) -> Dict:
        """Get state for specific coin"""
        if symbol not in self.state:
            self.state[symbol] = {
                'last_upper_cross': None,
                'last_lower_cross': None,
                'last_filter_cross': None,
                'alert_count': 0
            }
        return self.state[symbol]
    
    def detect_30m_cross(self, symbol: str, open_price: float, close_price: float, 
                         high_price: float, low_price: float,
                         upper_band: float, lower_band: float, 
                         timestamp: int) -> Optional[Dict]:
        """
        Detect 30-minute band cross - SIMPLE LOGIC
        Alert when candle body crosses upper OR lower band
        
        Args:
            symbol: Coin symbol
            open_price: Candle open
            close_price: Candle close
            high_price: Candle high
            low_price: Candle low
            upper_band: Upper band value
            lower_band: Lower band value
            timestamp: Candle timestamp
        
        Returns:
            Alert dict if cross detected, None otherwise
        """
        coin_state = self._get_coin_state(symbol)
        
        # Define candle body (min/max of open/close)
        body_high = max(open_price, close_price)
        body_low = min(open_price, close_price)
        
        # Check if body crosses upper band
        body_crosses_upper = body_high > upper_band
        
        # Check if body crosses lower band
        body_crosses_lower = body_low < lower_band
        
        # Optional: Check wicks if body doesn't cross
        wick_touches_upper = high_price > upper_band and not body_crosses_upper
        wick_touches_lower = low_price < lower_band and not body_crosses_lower
        
        alert = None
        
        # UPPER BAND CROSS (Body)
        if body_crosses_upper:
            # Check if we already sent alert for this cross
            if coin_state['last_upper_cross'] != timestamp:
                coin_state['last_upper_cross'] = timestamp
                coin_state['alert_count'] += 1
                
                alert = {
                    'symbol': symbol,
                    'type': 'UPPER_BAND',
                    'cross_method': 'BODY',
                    'timestamp': timestamp,
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'upper_band': upper_band,
                    'lower_band': lower_band,
                    'direction': 'BULLISH'
                }
        
        # LOWER BAND CROSS (Body)
        elif body_crosses_lower:
            # Check if we already sent alert for this cross
            if coin_state['last_lower_cross'] != timestamp:
                coin_state['last_lower_cross'] = timestamp
                coin_state['alert_count'] += 1
                
                alert = {
                    'symbol': symbol,
                    'type': 'LOWER_BAND',
                    'cross_method': 'BODY',
                    'timestamp': timestamp,
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'upper_band': upper_band,
                    'lower_band': lower_band,
                    'direction': 'BEARISH'
                }
        
        # UPPER BAND TOUCH (Wick only) - Optional, less reliable
        elif wick_touches_upper:
            if coin_state['last_upper_cross'] != timestamp:
                coin_state['last_upper_cross'] = timestamp
                coin_state['alert_count'] += 1
                
                alert = {
                    'symbol': symbol,
                    'type': 'UPPER_BAND',
                    'cross_method': 'WICK',
                    'timestamp': timestamp,
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'upper_band': upper_band,
                    'lower_band': lower_band,
                    'direction': 'BULLISH'
                }
        
        # LOWER BAND TOUCH (Wick only) - Optional, less reliable
        elif wick_touches_lower:
            if coin_state['last_lower_cross'] != timestamp:
                coin_state['last_lower_cross'] = timestamp
                coin_state['alert_count'] += 1
                
                alert = {
                    'symbol': symbol,
                    'type': 'LOWER_BAND',
                    'cross_method': 'WICK',
                    'timestamp': timestamp,
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'upper_band': upper_band,
                    'lower_band': lower_band,
                    'direction': 'BEARISH'
                }
        
        if alert:
            self._save_state()
        
        return alert
    
    def detect_4h_cross(self, symbol: str, open_price: float, close_price: float,
                        high_price: float, low_price: float,
                        filter_line: float, upper_band: float, lower_band: float,
                        timestamp: int) -> Optional[Dict]:
        """
        Detect 4-hour line cross (filter, upper band, OR lower band)
        Simple logic: check if body crosses any line
        """
        coin_state = self._get_coin_state(symbol)
        
        # Define candle body
        body_high = max(open_price, close_price)
        body_low = min(open_price, close_price)
        
        # Check crosses
        crosses_upper = body_high > upper_band
        crosses_filter = body_low <= filter_line <= body_high
        crosses_lower = body_low < lower_band
        
        # Build alert
        crossed_lines = []
        if crosses_upper and coin_state.get('last_upper_cross') != timestamp:
            crossed_lines.append('UPPER_BAND')
            coin_state['last_upper_cross'] = timestamp
        
        if crosses_filter and coin_state.get('last_filter_cross') != timestamp:
            crossed_lines.append('FILTER')
            coin_state['last_filter_cross'] = timestamp
        
        if crosses_lower and coin_state.get('last_lower_cross') != timestamp:
            crossed_lines.append('LOWER_BAND')
            coin_state['last_lower_cross'] = timestamp
        
        if crossed_lines:
            coin_state['alert_count'] = coin_state.get('alert_count', 0) + 1
            self._save_state()
            
            return {
                'symbol': symbol,
                'type': '_'.join(crossed_lines),
                'cross_method': 'BODY',
                'crossed_lines': crossed_lines,
                'timestamp': timestamp,
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'filter': filter_line,
                'upper_band': upper_band,
                'lower_band': lower_band
            }
        
        return None
    
    def reset_coin_state(self, symbol: str):
        """Reset state for a specific coin"""
        if symbol in self.state:
            del self.state[symbol]
            self._save_state()