#!/usr/bin/env python3
"""
Band Cross Detector - Simple Body Cross Detection
"""

import json
import os
from datetime import datetime
from typing import Dict, Optional

class BandCrossDetector:
    def __init__(self, state_file: str = 'cache/gc_alert_state.json'):
        self.state_file = state_file
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _save_state(self):
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def _get_coin_state(self, symbol: str) -> Dict:
        if symbol not in self.state:
            self.state[symbol] = {
                'last_upper_timestamp': None,
                'last_lower_timestamp': None,
                'alert_count': 0
            }
        return self.state[symbol]
    
    def detect_30m_cross(self, symbol: str, open_price: float, close_price: float, 
                         high_price: float, low_price: float,
                         upper_band: float, lower_band: float, 
                         timestamp: int) -> Optional[Dict]:
        """
        Detect band cross - BODY ONLY
        
        Args:
            symbol: Coin symbol
            open_price: Open
            close_price: Close
            high_price: High (with wicks)
            low_price: Low (with wicks)
            upper_band: Upper band
            lower_band: Lower band
            timestamp: Timestamp
        """
        coin_state = self._get_coin_state(symbol)
        
        # Body range (min/max of open/close)
        body_high = max(open_price, close_price)
        body_low = min(open_price, close_price)
        
        # UPPER BAND CROSS: Body goes ABOVE upper band
        if body_high > upper_band:
            if coin_state['last_upper_timestamp'] == timestamp:
                return None  # Already alerted
            
            coin_state['last_upper_timestamp'] = timestamp
            coin_state['alert_count'] += 1
            self._save_state()
            
            return {
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
        
        # LOWER BAND CROSS: Body goes BELOW lower band
        elif body_low < lower_band:
            if coin_state['last_lower_timestamp'] == timestamp:
                return None  # Already alerted
            
            coin_state['last_lower_timestamp'] = timestamp
            coin_state['alert_count'] += 1
            self._save_state()
            
            return {
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
        
        return None
    
    def detect_4h_cross(self, symbol: str, open_price: float, close_price: float,
                        high_price: float, low_price: float,
                        filter_line: float, upper_band: float, lower_band: float,
                        timestamp: int) -> Optional[Dict]:
        """Detect 4h cross (filter + bands)"""
        coin_state = self._get_coin_state(symbol)
        
        body_high = max(open_price, close_price)
        body_low = min(open_price, close_price)
        
        crossed_lines = []
        
        if body_high > upper_band:
            crossed_lines.append('UPPER_BAND')
        if body_low <= filter_line <= body_high:
            crossed_lines.append('FILTER')
        if body_low < lower_band:
            crossed_lines.append('LOWER_BAND')
        
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
        if symbol in self.state:
            del self.state[symbol]
            self._save_state()