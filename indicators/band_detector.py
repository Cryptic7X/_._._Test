#!/usr/bin/env python3
"""
Band Cross Detector - Accurate Wick-then-Body Cross Logic
Checks wicks first, if absent, checks body. Alerts only on true cross direction change.
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
                'last_cross_type': None,    # e.g., 'hwick_above', 'hwick_below', 'body_hband_above', etc.
                'alert_count': 0
            }
        return self.state[symbol]
    
    def detect_30m_cross(self, symbol: str, open_price: float, close_price: float, 
                         high_price: float, low_price: float,
                         upper_band: float, lower_band: float, 
                         timestamp: int) -> Optional[Dict]:
        """
        Detect band cross with priority: wicks first, then body
        """
        coin_state = self._get_coin_state(symbol)
        last_cross = coin_state.get('last_cross_type', None)
        
        body_high = max(open_price, close_price)
        body_low = min(open_price, close_price)
        
        alert = None

        # Wick crossing logic
        if high_price > upper_band and last_cross != 'hwick_above':
            coin_state['last_cross_type'] = 'hwick_above'
            coin_state['alert_count'] += 1
            self._save_state()
            alert = {
                'symbol': symbol,
                'type': 'UPPER_BAND',
                'alert_type': 'WICK_CROSS_ABOVE_HBAND',
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
        elif low_price < lower_band and last_cross != 'lwick_below':
            coin_state['last_cross_type'] = 'lwick_below'
            coin_state['alert_count'] += 1
            self._save_state()
            alert = {
                'symbol': symbol,
                'type': 'LOWER_BAND',
                'alert_type': 'WICK_CROSS_BELOW_LBAND',
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
        # Body crossing logic (only if no wick cross triggered above)
        elif body_high > upper_band and last_cross != 'body_hband_above':
            coin_state['last_cross_type'] = 'body_hband_above'
            coin_state['alert_count'] += 1
            self._save_state()
            alert = {
                'symbol': symbol,
                'type': 'UPPER_BAND',
                'alert_type': 'BODY_CROSS_ABOVE_HBAND',
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
        elif body_low < lower_band and last_cross != 'body_lband_below':
            coin_state['last_cross_type'] = 'body_lband_below'
            coin_state['alert_count'] += 1
            self._save_state()
            alert = {
                'symbol': symbol,
                'type': 'LOWER_BAND',
                'alert_type': 'BODY_CROSS_BELOW_LBAND',
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
        # Reset on inside channel (allows retrigger after recross)
        elif lower_band <= body_low and body_high <= upper_band and last_cross not in [None, 'inside']:
            coin_state['last_cross_type'] = 'inside'
            self._save_state()

        return alert
    
    def reset_coin_state(self, symbol: str):
        if symbol in self.state:
            del self.state[symbol]
            self._save_state()
