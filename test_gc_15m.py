#!/usr/bin/env python3
"""
Gaussian Channel 15-Minute Test Runner
Tests 30m analysis logic on 15m timeframe with batched Telegram alerts
"""

import os
import sys
import json
import numpy as np
from datetime import datetime
from typing import List

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from indicators.gaussian_channel import GaussianChannel
from indicators.band_detector import BandCrossDetector
from utils.telegram_bot import TelegramBot
from simple_exchange import SimpleExchangeManager

class GaussianTest15m:
    def __init__(self):
        """Initialize 15m test system"""
        self.exchange = SimpleExchangeManager()
        self.gaussian = GaussianChannel(
            poles=4,
            period=144,
            multiplier=1.414,
            reduced_lag=False,
            fast_response=False
        )
        self.detector = BandCrossDetector(state_file='cache/gc_test_15m_state.json')
        self.telegram = TelegramBot()
        
        # Store all alerts for batching
        self.batch_alerts = []
        
        print("🚀 Gaussian Channel 15m Test System Initialized")
        print(f"📊 Parameters: Poles={self.gaussian.poles}, Period={self.gaussian.period}, Multiplier={self.gaussian.multiplier}")
    
    def load_coins(self) -> List[str]:
        """Load ALL coins from coins.txt"""
        coins_file = 'config/coins.txt'
        
        if not os.path.exists(coins_file):
            print(f"❌ {coins_file} not found!")
            print(f"📝 Please create config/coins.txt with your coin list")
            return []
        
        coins = []
        
        with open(coins_file, 'r', encoding='utf-8') as f:
            for line in f:
                coin = line.strip().upper()
                
                # Skip empty lines and comments
                if not coin or coin.startswith('#'):
                    continue
                
                coins.append(coin)
        
        print(f"📋 Loaded {len(coins)} coins from coins.txt")
        return coins
    
    def analyze_coin(self, symbol: str) -> bool:
        """
        Analyze single coin for band crosses
        
        Args:
            symbol: Coin symbol (e.g., BTCUSDT)
        
        Returns:
            True if analysis successful, False otherwise
        """
        try:
            # Fetch 15m OHLCV data
            data, source = self.exchange.fetch_ohlcv_with_fallback(symbol, '15m', limit=200)
            
            if not data or len(data['close']) < 150:
                print(f"⚠️ {symbol}: Insufficient data")
                return False
            
            # Convert to numpy arrays
            high = np.array(data['high'])
            low = np.array(data['low'])
            close = np.array(data['close'])
            open_price = np.array(data['open'])
            timestamps = data['timestamp']
            
            # Calculate Gaussian Channel
            filter_line, upper_band, lower_band = self.gaussian.calculate(high, low, close)
            
            # Get last closed candle (index -2, since -1 is current unclosed)
            idx = -2
            candle_open = open_price[idx]
            candle_high = high[idx]
            candle_low = low[idx]
            candle_close = close[idx]
            candle_upper = upper_band[idx]
            candle_lower = lower_band[idx]
            candle_time = timestamps[idx]
            
            # Detect band cross with ALL required parameters
            alert = self.detector.detect_30m_cross(
                symbol=symbol,
                open_price=candle_open,
                close_price=candle_close,
                high_price=candle_high,
                low_price=candle_low,
                upper_band=candle_upper,
                lower_band=candle_lower,
                timestamp=candle_time
            )
            
            if alert:
                cross_method = alert.get('cross_method', 'BODY')
                print(f"🔔 {symbol}: {alert['type']} ({cross_method}) - {alert['direction']}")
                
                # Add to batch instead of sending immediately
                self.batch_alerts.append(alert)
                
                # Log alert to file
                self._log_alert(alert)
                
                return True
            else:
                print(f"✓ {symbol}: No band cross detected")
            
            return True
            
        except Exception as e:
            print(f"❌ {symbol}: Error - {e}")
            return False
    
    def _log_alert(self, alert: dict):
        """Log alert to file"""
        os.makedirs('logs', exist_ok=True)
        log_file = f"logs/gc_alerts_15m_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        with open(log_file, 'a') as f:
            json.dump(alert, f)
            f.write('
')
    
    def send_batch_alerts(self):
        """Send all collected alerts as one message"""
        if not self.batch_alerts:
            print("
ℹ️ No alerts to send")
            return
        
        print(f"
📤 Sending {len(self.batch_alerts)} alert(s) in batch...")
        
        # Format and send batch message
        message = self.telegram.format_batch_alert(self.batch_alerts, timeframe_minutes=15)
        success = self.telegram.send_message(message)
        
        if success:
            print(f"✅ Batch alert sent to Telegram ({len(self.batch_alerts)} signals)")
        else:
            print(f"❌ Failed to send batch alert to Telegram")
    
    def run(self):
        """Run 15m test analysis"""
        print("
" + "="*60)
        print("🧪 Starting Gaussian Channel 15m Test")
        print("="*60 + "
")
        
        # Load ALL coins from coins.txt
        coins = self.load_coins()
        
        if not coins:
            print("❌ No coins to analyze")
            return
        
        print(f"📊 Analyzing {len(coins)} coins on 15-minute timeframe...")
        print(f"🔔 Alerts will be batched and sent to Telegram
")
        
        success_count = 0
        
        for i, symbol in enumerate(coins, 1):
            print(f"
[{i}/{len(coins)}] {symbol}")
            success = self.analyze_coin(symbol)
            if success:
                success_count += 1
        
        print("
" + "="*60)
        print(f"✅ Analysis complete: {success_count}/{len(coins)} coins processed")
        print("="*60 + "
")
        
        # Send batch alerts after all analysis is complete
        self.send_batch_alerts()

def main():
    """Main entry point"""
    tester = GaussianTest15m()
    tester.run()

if __name__ == "__main__":
    main()