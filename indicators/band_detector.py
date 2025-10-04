#!/usr/bin/env python3
"""
Band Cross Detector - FRESH SIGNALS ONLY
Only alerts on NEW crosses within last 30 minutes
"""

import json
import os
from typing import Dict, Optional
from datetime import datetime

class BandCrossDetector:
    def __init__(self, state_file: str = 'cache/gc_alert_state.json'):
        self.state_file = state_file
        self.state = self._load_state()
        self.current_run_time = int(datetime.now().timestamp() * 1000)
    
    def _load_state(self) -> Dict:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _save_state(self):
        dirname = os.path.dirname(self.state_file)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def _get_coin_state(self, symbol: str) -> Dict:
        if symbol not in self.state:
            self.state[symbol] = {
                'last_hband_cross_time': 0,
                'last_lband_cross_time': 0,
                'last_band_crossed': None,
                'alert_count': 0
            }
        return self.state[symbol]
    
    def detect_30m_cross(self, symbol: str, open_price: float, close_price: float, 
                         high_price: float, low_price: float,
                         upper_band: float, lower_band: float, 
                         timestamp: int) -> Optional[Dict]:
        """
        Detect fresh band crosses only
        
        Rules:
        1. Only alert if candle timestamp is within last 30 min
        2. Alternating bands (HBand → LBand → HBand)
        3. No duplicate alerts for same timestamp
        """
        coin_state = self._get_coin_state(symbol)
        
        # Check if this candle is fresh (within last 30 minutes)
        time_diff_minutes = (self.current_run_time - timestamp) / 1000 / 60
        
        if time_diff_minutes > 35:  # Allow 5 min buffer
            # Skip old candles
            return None
        
        last_band = coin_state.get('last_band_crossed')
        
        body_high = max(open_price, close_price)
        body_low = min(open_price, close_price)
        
        hband_crossed = (body_high > upper_band) or (high_price > upper_band)
        lband_crossed = (body_low < lower_band) or (low_price < lower_band)
        
        cross_method_h = 'BODY' if body_high > upper_band else 'WICK'
        cross_method_l = 'BODY' if body_low < lower_band else 'WICK'
        
        alert = None
        
        # Alternating logic with timestamp check
        if last_band is None or last_band == '':
            # First alert - accept any
            if hband_crossed:
                last_hband_time = coin_state.get('last_hband_cross_time', 0)
                if timestamp > last_hband_time:
                    alert = self._create_hband_alert(symbol, open_price, high_price, low_price, 
                                                     close_price, upper_band, lower_band, 
                                                     timestamp, cross_method_h)
                    coin_state['last_band_crossed'] = 'HBAND'
                    coin_state['last_hband_cross_time'] = timestamp
                    coin_state['alert_count'] += 1
            
            elif lband_crossed:
                last_lband_time = coin_state.get('last_lband_cross_time', 0)
                if timestamp > last_lband_time:
                    alert = self._create_lband_alert(symbol, open_price, high_price, low_price, 
                                                     close_price, upper_band, lower_band, 
                                                     timestamp, cross_method_l)
                    coin_state['last_band_crossed'] = 'LBAND'
                    coin_state['last_lband_cross_time'] = timestamp
                    coin_state['alert_count'] += 1
        
        elif last_band == 'HBAND':
            # Last was HBand - only accept LBand now
            if lband_crossed:
                last_lband_time = coin_state.get('last_lband_cross_time', 0)
                if timestamp > last_lband_time:
                    alert = self._create_lband_alert(symbol, open_price, high_price, low_price, 
                                                     close_price, upper_band, lower_band, 
                                                     timestamp, cross_method_l)
                    coin_state['last_band_crossed'] = 'LBAND'
                    coin_state['last_lband_cross_time'] = timestamp
                    coin_state['alert_count'] += 1
        
        elif last_band == 'LBAND':
            # Last was LBand - only accept HBand now
            if hband_crossed:
                last_hband_time = coin_state.get('last_hband_cross_time', 0)
                if timestamp > last_hband_time:
                    alert = self._create_hband_alert(symbol, open_price, high_price, low_price, 
                                                     close_price, upper_band, lower_band, 
                                                     timestamp, cross_method_h)
                    coin_state['last_band_crossed'] = 'HBAND'
                    coin_state['last_hband_cross_time'] = timestamp
                    coin_state['alert_count'] += 1
        
        if alert:
            self._save_state()
        
        return alert
    
    def _create_hband_alert(self, symbol, open_price, high_price, low_price, close_price, 
                           upper_band, lower_band, timestamp, cross_method):
        # Get human readable time
        dt = datetime.fromtimestamp(timestamp / 1000)
        time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
        
        return {
            'symbol': symbol,
            'type': 'HBAND_CROSS',
            'band': 'HBAND',
            'cross_method': cross_method,
            'timestamp': timestamp,
            'time_str': time_str,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'upper_band': upper_band,
            'lower_band': lower_band,
            'direction': 'BULLISH',
            'alert_message': f"{symbol} crossed HBand ({cross_method}) at {time_str}"
        }
    
    def _create_lband_alert(self, symbol, open_price, high_price, low_price, close_price, 
                           upper_band, lower_band, timestamp, cross_method):
        # Get human readable time
        dt = datetime.fromtimestamp(timestamp / 1000)
        time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
        
        return {
            'symbol': symbol,
            'type': 'LBAND_CROSS',
            'band': 'LBAND',
            'cross_method': cross_method,
            'timestamp': timestamp,
            'time_str': time_str,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'upper_band': upper_band,
            'lower_band': lower_band,
            'direction': 'BEARISH',
            'alert_message': f"{symbol} crossed LBand ({cross_method}) at {time_str}"
        }
    
    def reset_coin_state(self, symbol: str):
        if symbol in self.state:
            del self.state[symbol]
            self._save_state()
