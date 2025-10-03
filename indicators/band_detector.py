#!/usr/bin/env python3
"""
Band Cross Detector with State Tracking
Detects when candle body crosses Gaussian Channel bands
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

class BandCrossDetector:
    def __init__(self, state_file: str = 'cache/gc_alert_state.json'):
        """
        Initialize band cross detector
        
        Args:
            state_file: Path to state persistence file
        """
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
                'last_alert_time': None,
                'last_position': 'inside',  # inside, above_upper, below_lower
                'alert_count': 0
            }
        return self.state[symbol]
    
    def detect_30m_cross(self, symbol: str, open_price: float, close_price: float,
                         upper_band: float, lower_band: float, 
                         timestamp: int) -> Optional[Dict]:
        """
        Detect 30-minute band cross (only upper/lower bands)
        
        Args:
            symbol: Coin symbol
            open_price: Candle open price
            close_price: Candle close price
            upper_band: Upper band value
            lower_band: Lower band value
            timestamp: Candle timestamp
        
        Returns:
            Alert dict if cross detected, None otherwise
        """
        coin_state = self._get_coin_state(symbol)
        
        # Determine candle body position
        candle_high = max(open_price, close_price)
        candle_low = min(open_price, close_price)
        
        # Check current position
        crosses_upper = candle_high > upper_band
        crosses_lower = candle_low < lower_band
        
        # Determine new position
        if crosses_upper and crosses_lower:
            # Candle crosses both bands (rare, but possible with high volatility)
            new_position = 'both_bands'
        elif crosses_upper:
            new_position = 'above_upper'
        elif crosses_lower:
            new_position = 'below_lower'
        else:
            new_position = 'inside'
        
        # Check if we should alert
        last_position = coin_state['last_position']
        should_alert = False
        alert_type = None
        
        if new_position == 'both_bands' and last_position == 'inside':
            should_alert = True
            alert_type = 'BOTH_BANDS'
        elif new_position == 'above_upper' and last_position != 'above_upper':
            should_alert = True
            alert_type = 'UPPER_BAND'
        elif new_position == 'below_lower' and last_position != 'below_lower':
            should_alert = True
            alert_type = 'LOWER_BAND'
        
        # Update state
        coin_state['last_position'] = new_position
        
        if should_alert:
            coin_state['last_alert_time'] = datetime.fromtimestamp(timestamp / 1000).isoformat()
            coin_state['alert_count'] += 1
            self._save_state()
            
            return {
                'symbol': symbol,
                'type': alert_type,
                'timestamp': timestamp,
                'close': close_price,
                'upper_band': upper_band,
                'lower_band': lower_band,
                'direction': 'BULLISH' if alert_type in ['UPPER_BAND', 'BOTH_BANDS'] else 'BEARISH'
            }
        
        self._save_state()
        return None
    
    def detect_4h_cross(self, symbol: str, open_price: float, close_price: float,
                        filter_line: float, upper_band: float, lower_band: float,
                        timestamp: int) -> Optional[Dict]:
        """
        Detect 4-hour line cross (filter, upper band, OR lower band)
        
        Args:
            symbol: Coin symbol
            open_price: Candle open price
            close_price: Candle close price
            filter_line: Filter line value
            upper_band: Upper band value
            lower_band: Lower band value
            timestamp: Candle timestamp
        
        Returns:
            Alert dict if cross detected, None otherwise
        """
        coin_state = self._get_coin_state(symbol)
        
        # Determine candle body position
        candle_high = max(open_price, close_price)
        candle_low = min(open_price, close_price)
        
        # Check what lines are crossed
        crosses_upper = candle_high > upper_band
        crosses_filter = candle_low < filter_line < candle_high
        crosses_lower = candle_low < lower_band
        
        # Build list of crossed lines
        crossed_lines = []
        if crosses_upper:
            crossed_lines.append('UPPER_BAND')
        if crosses_filter:
            crossed_lines.append('FILTER')
        if crosses_lower:
            crossed_lines.append('LOWER_BAND')
        
        # Determine alert type
        if len(crossed_lines) == 0:
            new_position = 'inside'
        else:
            new_position = '_'.join(crossed_lines)
        
        # Check if we should alert (only if position changed)
        last_position = coin_state.get('last_position_4h', 'inside')
        should_alert = new_position != 'inside' and last_position != new_position
        
        # Update state
        coin_state['last_position_4h'] = new_position
        
        if should_alert and crossed_lines:
            coin_state['last_alert_time'] = datetime.fromtimestamp(timestamp / 1000).isoformat()
            coin_state['alert_count'] = coin_state.get('alert_count', 0) + 1
            self._save_state()
            
            return {
                'symbol': symbol,
                'type': '_'.join(crossed_lines),
                'crossed_lines': crossed_lines,
                'timestamp': timestamp,
                'close': close_price,
                'filter': filter_line,
                'upper_band': upper_band,
                'lower_band': lower_band
            }
        
        self._save_state()
        return None
    
    def reset_coin_state(self, symbol: str):
        """Reset state for a specific coin"""
        if symbol in self.state:
            del self.state[symbol]
            self._save_state()
