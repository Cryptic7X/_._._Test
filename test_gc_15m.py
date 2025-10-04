#!/usr/bin/env python3
"""
Gaussian Channel 15-Minute Test Runner
"""

import os
import sys
import json
import numpy as np
from datetime import datetime
from typing import List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from indicators.gaussian_channel import GaussianChannel
from indicators.band_detector import BandCrossDetector
from utils.telegram_bot import TelegramBot
from simple_exchange import SimpleExchangeManager

class GaussianTest15m:
    def __init__(self):
        self.exchange = SimpleExchangeManager()
        self.gaussian = GaussianChannel(poles=4, period=144, multiplier=1.414, reduced_lag=False, fast_response=False)
        self.detector = BandCrossDetector(state_file='cache/gc_test_15m_state.json')
        self.telegram = TelegramBot()
        self.batch_alerts = []
        
        print("Gaussian Channel 15m Test System Initialized")
        print(f"Parameters: Poles={self.gaussian.poles}, Period={self.gaussian.period}, Multiplier={self.gaussian.multiplier}")
    
    def load_coins(self) -> List[str]:
        coins_file = 'config/coins.txt'
        
        if not os.path.exists(coins_file):
            print(f"ERROR: {coins_file} not found!")
            return []
        
        coins = []
        with open(coins_file, 'r', encoding='utf-8') as f:
            for line in f:
                coin = line.strip().upper()
                if coin and not coin.startswith('#'):
                    coins.append(coin)
        
        print(f"Loaded {len(coins)} coins from coins.txt")
        return coins
    
    def analyze_coin(self, symbol: str) -> bool:
        try:
            data, source = self.exchange.fetch_ohlcv_with_fallback(symbol, '15m', limit=200)
            
            if not data or len(data['close']) < 150:
                print(f"WARNING: {symbol}: Insufficient data")
                return False
            
            high = np.array(data['high'])
            low = np.array(data['low'])
            close = np.array(data['close'])
            open_price = np.array(data['open'])
            timestamps = data['timestamp']
            
            filter_line, upper_band, lower_band = self.gaussian.calculate(high, low, close)
            
            idx = -2
            candle_open = open_price[idx]
            candle_high = high[idx]
            candle_low = low[idx]
            candle_close = close[idx]
            candle_upper = upper_band[idx]
            candle_lower = lower_band[idx]
            candle_time = timestamps[idx]
            
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
                print(f"ALERT: {symbol}: {alert['type']} ({cross_method}) - {alert['direction']}")
                self.batch_alerts.append(alert)
                self._log_alert(alert)
                return True
            else:
                print(f"OK: {symbol}: No band cross detected")
            
            return True
            
        except Exception as e:
            print(f"ERROR: {symbol}: {e}")
            return False
    
    def _log_alert(self, alert: dict):
        os.makedirs('logs', exist_ok=True)
        log_file = f"logs/gc_alerts_15m_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(log_file, 'a', encoding='utf-8') as f:
            json.dump(alert, f)
            f.write('\n')
    
    def send_batch_alerts(self):
        if not self.batch_alerts:
            print("\nINFO: No alerts to send")
            return
        
        print(f"\nSending {len(self.batch_alerts)} alerts in batch...")
        message = self.telegram.format_batch_alert(self.batch_alerts, timeframe_minutes=15)
        success = self.telegram.send_message(message)
        
        if success:
            print(f"SUCCESS: Batch alert sent to Telegram ({len(self.batch_alerts)} signals)")
        else:
            print(f"ERROR: Failed to send batch alert to Telegram")
    
    def run(self):
        print("\n" + "="*60)
        print("Starting Gaussian Channel 15m Test")
        print("="*60 + "\n")
        
        coins = self.load_coins()
        
        if not coins:
            print("ERROR: No coins to analyze")
            return
        
        print(f"Analyzing {len(coins)} coins on 15-minute timeframe...")
        print(f"Alerts will be batched and sent to Telegram\n")
        
        success_count = 0
        
        for i, symbol in enumerate(coins, 1):
            print(f"\n[{i}/{len(coins)}] {symbol}")
            success = self.analyze_coin(symbol)
            if success:
                success_count += 1
        
        print("\n" + "="*60)
        print(f"Analysis complete: {success_count}/{len(coins)} coins processed")
        print("="*60 + "\n")
        
        self.send_batch_alerts()

def main():
    tester = GaussianTest15m()
    tester.run()

if __name__ == "__main__":
    main()
