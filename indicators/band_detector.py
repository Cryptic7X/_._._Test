#!/usr/bin/env python3
"""
Band Cross Detector - ALTERNATING ALERTS
Logic: HBand → LBand → HBand → LBand (prevents spam)
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
                'alert_count': 0
            }
        return self.state[symbol]
    
    def detect_30m_cross(self, symbol: str, open_price: float, close_price: float, 
                         high_price: float, low_price: float,
                         upper_band: float, lower_band: float, 
                         timestamp: int) -> Optional[Dict]:
        """
        Detect alternating band crosses
        First HBand → Next must be LBand → Next must be HBand
        """
        coin_state = self._get_coin_state(symbol)
        last_band = coin_state.get('last_band_crossed')
        
        body_high = max(open_price, close_price)
        body_low = min(open_price, close_price)
        
        hband_crossed = (body_high > upper_band) or (high_price > upper_band)
        lband_crossed = (body_low < lower_band) or (low_price < lower_band)
        
        cross_method_h = 'BODY' if body_high > upper_band else 'WICK'
        cross_method_l = 'BODY' if body_low < lower_band else 'WICK'
        
        alert = None
        
        if last_band is None:
            if hband_crossed:
                alert = self._create_hband_alert(symbol, open_price, high_price, low_price, 
                                                 close_price, upper_band, lower_band, 
                                                 timestamp, cross_method_h)
                coin_state['last_band_crossed'] = 'HBAND'
                coin_state['alert_count'] += 1
            elif lband_crossed:
                alert = self._create_lband_alert(symbol, open_price, high_price, low_price, 
                                                 close_price, upper_band, lower_band, 
                                                 timestamp, cross_method_l)
                coin_state['last_band_crossed'] = 'LBAND'
                coin_state['alert_count'] += 1
        
        elif last_band == 'HBAND':
            if lband_crossed:
                alert = self._create_lband_alert(symbol, open_price, high_price, low_price, 
                                                 close_price, upper_band, lower_band, 
                                                 timestamp, cross_method_l)
                coin_state['last_band_crossed'] = 'LBAND'
                coin_state['alert_count'] += 1
        
        elif last_band == 'LBAND':
            if hband_crossed:
                alert = self._create_hband_alert(symbol, open_price, high_price, low_price, 
                                                 close_price, upper_band, lower_band, 
                                                 timestamp, cross_method_h)
                coin_state['last_band_crossed'] = 'HBAND'
                coin_state['alert_count'] += 1
        
        if alert:
            self._save_state()
        
        return alert
    
    def _create_hband_alert(self, symbol, open_price, high_price, low_price, close_price, 
                           upper_band, lower_band, timestamp, cross_method):
        return {
            'symbol': symbol,
            'type': 'HBAND_CROSS',
            'band': 'HBAND',
            'cross_method': cross_method,
            'timestamp': timestamp,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'upper_band': upper_band,
            'lower_band': lower_band,
            'direction': 'BULLISH',
            'alert_message': f"{symbol} crossed Filtered True Range High Band ({cross_method}) on 30m"
        }
    
    def _create_lband_alert(self, symbol, open_price, high_price, low_price, close_price, 
                           upper_band, lower_band, timestamp, cross_method):
        return {
            'symbol': symbol,
            'type': 'LBAND_CROSS',
            'band': 'LBAND',
            'cross_method': cross_method,
            'timestamp': timestamp,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'upper_band': upper_band,
            'lower_band': lower_band,
            'direction': 'BEARISH',
            'alert_message': f"{symbol} crossed Filtered True Range Low Band ({cross_method}) on 30m"
        }
    
    def reset_coin_state(self, symbol: str):
        if symbol in self.state:
            del self.state[symbol]
            self._save_state()
