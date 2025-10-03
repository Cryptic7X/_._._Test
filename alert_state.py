#!/usr/bin/env python3
"""
Alert State Manager - Tracks alert history to prevent duplicates
"""

import json
import os
from typing import Dict, Optional
from datetime import datetime


class AlertStateManager:
    """
    Manages alert state to prevent duplicate alerts.
    Tracks last alert per coin per line.
    """
    
    def __init__(self, state_file: str = "alert_state.json"):
        """
        Args:
            state_file: Path to JSON file storing alert state
        """
        self.state_file = state_file
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        """Load alert state from JSON file."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ Error loading state file: {e}")
                return {}
        return {}
    
    def _save_state(self):
        """Save alert state to JSON file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            print(f"⚠️ Error saving state file: {e}")
    
    def should_send_alert(self, symbol: str, cross_type: str, 
                         current_price: float, band_value: float) -> bool:
        """
        Check if alert should be sent based on state history.
        
        Args:
            symbol: Trading pair symbol
            cross_type: Type of cross (upper_band, lower_band, filter_line)
            current_price: Current close price
            band_value: Value of the band/line being crossed
        
        Returns:
            True if alert should be sent, False if duplicate
        """
        key = f"{symbol}_{cross_type}"
        
        # If no previous alert for this symbol+cross_type, send alert
        if key not in self.state:
            return True
        
        last_alert = self.state[key]
        last_price = last_alert.get('price', 0)
        last_band = last_alert.get('band_value', 0)
        
        # Determine if price has "reset" (returned to other side)
        if cross_type == "upper_band":
            # For upper band, price must go below band to reset
            has_reset = current_price < band_value and last_price >= last_band
        elif cross_type == "lower_band":
            # For lower band, price must go above band to reset
            has_reset = current_price > band_value and last_price <= last_band
        elif cross_type == "filter_line":
            # For filter, price must cross to opposite side
            was_above = last_price > last_band
            now_above = current_price > band_value
            has_reset = was_above != now_above
        else:
            has_reset = False
        
        return has_reset
    
    def record_alert(self, symbol: str, cross_type: str, 
                    price: float, band_value: float):
        """
        Record an alert in the state.
        
        Args:
            symbol: Trading pair symbol
            cross_type: Type of cross
            price: Close price at alert
            band_value: Value of band/line at alert
        """
        key = f"{symbol}_{cross_type}"
        self.state[key] = {
            'timestamp': datetime.now().isoformat(),
            'price': price,
            'band_value': band_value,
            'cross_type': cross_type
        }
        self._save_state()
    
    def get_alert_history(self, symbol: str) -> Dict:
        """Get all alert history for a symbol."""
        return {k: v for k, v in self.state.items() if k.startswith(symbol)}
    
    def clear_symbol_state(self, symbol: str):
        """Clear all state for a specific symbol."""
        keys_to_remove = [k for k in self.state.keys() if k.startswith(symbol)]
        for key in keys_to_remove:
            del self.state[key]
        self._save_state()
    
    def clear_all_state(self):
        """Clear all alert state."""
        self.state = {}
        self._save_state()


# Test function
if __name__ == "__main__":
    print("\n✅ Alert State Manager Test")
    print("=" * 60)
    
    # Create test manager
    manager = AlertStateManager(state_file="test_alert_state.json")
    
    # Test 1: First alert should be sent
    should_send = manager.should_send_alert("BTC-USDT", "upper_band", 45000, 44000)
    print(f"Test 1 - First alert: {should_send} (expected: True)")
    
    # Record the alert
    manager.record_alert("BTC-USDT", "upper_band", 45000, 44000)
    
    # Test 2: Duplicate alert should not be sent
    should_send = manager.should_send_alert("BTC-USDT", "upper_band", 45500, 44000)
    print(f"Test 2 - Duplicate alert: {should_send} (expected: False)")
    
    # Test 3: After reset, alert should be sent
    should_send = manager.should_send_alert("BTC-USDT", "upper_band", 43000, 44000)
    print(f"Test 3 - After reset: {should_send} (expected: True)")
    
    # Get history
    history = manager.get_alert_history("BTC-USDT")
    print(f"\nAlert history for BTC-USDT: {len(history)} entries")
    
    # Cleanup
    os.remove("test_alert_state.json")
    print("\n✅ Test completed and cleaned up")
