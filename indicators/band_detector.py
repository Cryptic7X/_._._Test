#!/usr/bin/env python3
"""
Band Cross Detector - TRUE CROSSOVER DETECTION (15m/30m)
Detects FIRST candle that crosses HBand or LBand
Alternating alerts: HBand → LBand → HBand
"""

import json
import os
from typing import Dict, Optional
from datetime import datetime

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
        dirname = os.path.dirname(self.state_file)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def _get_coin_state(self, symbol: str) -> Dict:
        if symbol not in self.state:
            self.state[symbol] = {
                'last_band_crossed': None,
                'prev_high': None,
                'prev_low': None,
                'prev_close': None,
                'prev_upper_band': None,
                'prev_lower_band': None,
                'alert_count': 0
            }
        return self.state[symbol]
    
    def detect_30m_cross(self, symbol: str, open_price: float, close_price: float, 
                         high_price: float, low_price: float,
                         upper_band: float, lower_band: float, 
                         timestamp: int) -> Optional[Dict]:
        """
        Detect TRUE crossover (first touch after not touching)
        Works for both 15m and 30m
        """
        coin_state = self._get_coin_state(symbol)
        
        prev_high = coin_state.get('prev_high')
        prev_low = coin_state.get('prev_low')
        prev_upper = coin_state.get('prev_upper_band')
        prev_lower = coin_state.get('prev_lower_band')
        last_band = coin_state.get('last_band_crossed')
        
        # Update state for next iteration
        coin_state['prev_high'] = high_price
        coin_state['prev_low'] = low_price
        coin_state['prev_close'] = close_price
        coin_state['prev_upper_band'] = upper_band
        coin_state['prev_lower_band'] = lower_band
        
        if prev_high is None or prev_upper is None:
            self._save_state()
            return None
        
        body_high = max(open_price, close_price)
        body_low = min(open_price, close_price)
        
        # Detect crossovers
        curr_touches_hband = (high_price > upper_band) or (body_high > upper_band)
        prev_touches_hband = (prev_high > prev_upper)
        hband_crossover = curr_touches_hband and not prev_touches_hband
        cross_method_h = 'BODY' if body_high > upper_band else 'WICK'
        
        curr_touches_lband = (low_price < lower_band) or (body_low < lower_band)
        prev_touches_lband = (prev_low < prev_lower)
        lband_crossover = curr_touches_lband and not prev_touches_lband
        cross_method_l = 'BODY' if body_low < lower_band else 'WICK'
        
        alert = None
        
        if last_band is None:
            if hband_crossover:
                alert = self._create_alert(symbol, 'HBAND', cross_method_h, 'BULLISH',
                                          open_price, high_price, low_price, close_price,
                                          upper_band, lower_band, timestamp)
                coin_state['last_band_crossed'] = 'HBAND'
                coin_state['alert_count'] += 1
            elif lband_crossover:
                alert = self._create_alert(symbol, 'LBAND', cross_method_l, 'BEARISH',
                                          open_price, high_price, low_price, close_price,
                                          upper_band, lower_band, timestamp)
                coin_state['last_band_crossed'] = 'LBAND'
                coin_state['alert_count'] += 1
        
        elif last_band == 'HBAND':
            if lband_crossover:
                alert = self._create_alert(symbol, 'LBAND', cross_method_l, 'BEARISH',
                                          open_price, high_price, low_price, close_price,
                                          upper_band, lower_band, timestamp)
                coin_state['last_band_crossed'] = 'LBAND'
                coin_state['alert_count'] += 1
        
        elif last_band == 'LBAND':
            if hband_crossover:
                alert = self._create_alert(symbol, 'HBAND', cross_method_h, 'BULLISH',
                                          open_price, high_price, low_price, close_price,
                                          upper_band, lower_band, timestamp)
                coin_state['last_band_crossed'] = 'HBAND'
                coin_state['alert_count'] += 1
        
        self._save_state()
        return alert
    
    def _create_alert(self, symbol, band, cross_method, direction,
                     open_price, high_price, low_price, close_price,
                     upper_band, lower_band, timestamp):
        dt = datetime.fromtimestamp(timestamp / 1000)
        time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
        
        band_name = 'HBand' if band == 'HBAND' else 'LBand'
        
        return {
            'symbol': symbol,
            'type': f'{band}_CROSS',
            'band': band,
            'cross_method': cross_method,
            'timestamp': timestamp,
            'time_str': time_str,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'upper_band': upper_band,
            'lower_band': lower_band,
            'direction': direction,
            'alert_message': f"{symbol} crossed {band_name} ({cross_method})"
        }
    
    def reset_coin_state(self, symbol: str):
        if symbol in self.state:
            del self.state[symbol]
            self._save_state()
