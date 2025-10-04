#!/usr/bin/env python3
"""
Band Cross Detector - Direction-Based Crossing Logic
Detects when candle body CROSSES bands (not just position)
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
                'last_position': 'unknown',  # inside, above_upper, below_lower
                'last_timestamp': None,
                'alert_count': 0
            }
        return self.state[symbol]
    
    def detect_30m_cross(self, symbol: str, open_price: float, close_price: float, 
                         high_price: float, low_price: float,
                         upper_band: float, lower_band: float, 
                         timestamp: int) -> Optional[Dict]:
        """
        Detect band CROSSING - only alerts when body crosses FROM one side TO another
        
        BODY ONLY (no wicks):
        - Body = range between open and close (min to max)
        
        Crossing logic:
        1. Upper band crossed from ABOVE → Body goes from above_upper to inside (ALERT)
        2. Upper band crossed from BELOW → Body goes from inside to above_upper (ALERT)
        3. Lower band crossed from ABOVE → Body goes from inside to below_lower (ALERT)
        4. Lower band crossed from BELOW → Body goes from below_lower to inside (ALERT)
        
        Args:
            symbol: Coin symbol
            open_price: Open
            close_price: Close
            high_price: High (not used for body detection)
            low_price: Low (not used for body detection)
            upper_band: Upper band
            lower_band: Lower band
            timestamp: Timestamp
        
        Returns:
            Alert dict if crossing detected, None otherwise
        """
        coin_state = self._get_coin_state(symbol)
        
        # Calculate body range (min/max of open/close)
        body_high = max(open_price, close_price)
        body_low = min(open_price, close_price)
        
        # Determine CURRENT body position relative to bands
        if body_low > upper_band:
            # Entire body is ABOVE upper band
            current_position = 'above_upper'
        elif body_high < lower_band:
            # Entire body is BELOW lower band
            current_position = 'below_lower'
        else:
            # Body is INSIDE the channel (between bands)
            current_position = 'inside'
        
        # Get last position
        last_position = coin_state['last_position']
        
        # Detect CROSSING (position changed)
        alert = None
        
        if last_position != current_position and last_position != 'unknown':
            # Position changed = band was crossed
            
            # UPPER BAND CROSSINGS
            if last_position == 'above_upper' and current_position == 'inside':
                # Crossed upper band from ABOVE (entering channel from top)
                alert = {
                    'symbol': symbol,
                    'type': 'UPPER_BAND',
                    'cross_direction': 'FROM_ABOVE',
                    'cross_method': 'BODY',
                    'timestamp': timestamp,
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'upper_band': upper_band,
                    'lower_band': lower_band,
                    'direction': 'BEARISH',
                    'description': 'Body crossed Upper Band from above (entering channel)'
                }
            
            elif last_position == 'inside' and current_position == 'above_upper':
                # Crossed upper band from BELOW (exiting channel upward)
                alert = {
                    'symbol': symbol,
                    'type': 'UPPER_BAND',
                    'cross_direction': 'FROM_BELOW',
                    'cross_method': 'BODY',
                    'timestamp': timestamp,
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'upper_band': upper_band,
                    'lower_band': lower_band,
                    'direction': 'BULLISH',
                    'description': 'Body crossed Upper Band from below (exiting channel upward)'
                }
            
            # LOWER BAND CROSSINGS
            elif last_position == 'inside' and current_position == 'below_lower':
                # Crossed lower band from ABOVE (exiting channel downward)
                alert = {
                    'symbol': symbol,
                    'type': 'LOWER_BAND',
                    'cross_direction': 'FROM_ABOVE',
                    'cross_method': 'BODY',
                    'timestamp': timestamp,
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'upper_band': upper_band,
                    'lower_band': lower_band,
                    'direction': 'BEARISH',
                    'description': 'Body crossed Lower Band from above (exiting channel downward)'
                }
            
            elif last_position == 'below_lower' and current_position == 'inside':
                # Crossed lower band from BELOW (entering channel from bottom)
                alert = {
                    'symbol': symbol,
                    'type': 'LOWER_BAND',
                    'cross_direction': 'FROM_BELOW',
                    'cross_method': 'BODY',
                    'timestamp': timestamp,
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'upper_band': upper_band,
                    'lower_band': lower_band,
                    'direction': 'BULLISH',
                    'description': 'Body crossed Lower Band from below (entering channel)'
                }
        
        # Update state with current position
        coin_state['last_position'] = current_position
        coin_state['last_timestamp'] = timestamp
        
        if alert:
            coin_state['alert_count'] += 1
            self._save_state()
            print(f"  CROSS DETECTED: {last_position} -> {current_position}")
        else:
            self._save_state()
            print(f"  Position: {current_position} (no change from {last_position})")
        
        return alert
    
    def detect_4h_cross(self, symbol: str, open_price: float, close_price: float,
                        high_price: float, low_price: float,
                        filter_line: float, upper_band: float, lower_band: float,
                        timestamp: int) -> Optional[Dict]:
        """
        Detect 4h cross - will use wick logic (implement later)
        For now, just body crossing logic
        """
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
        """Reset state for a specific coin"""
        if symbol in self.state:
            del self.state[symbol]
            self._save_state()
            print(f"Reset state for {symbol}")
