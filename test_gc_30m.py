#!/usr/bin/env python3
"""
Gaussian Channel 30-Minute Production System
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

class Gaussian30m:
    def __init__(self):
        self.exchange = SimpleExchangeManager()
        self.gaussian = GaussianChannel(
            poles=4,
            period=144,
            multiplier=1.414,
            reduced_lag=True,
            fast_response=False
        )
        self.detector = BandCrossDetector(state_file='cache/gc_30m_state.json')
        self.telegram = TelegramBot()
        self.batch_alerts = []
        
        print("Gaussian Channel 30m System Initialized")
    
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
        
        print(f"Loaded {len(coins)} coins")
        return coins
    
    def analyze_coin(self, symbol: str) -> bool:
        try:
            data, source = self.exchange.fetch_ohlcv_with_fallback(symbol, '30m', limit=200)
            
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
            alert = self.detector.detect_30m_cross(
                symbol=symbol,
                open_price=open_price[idx],
                close_price=close[idx],
                high_price=high[idx],
                low_price=low[idx],
                upper_band=upper_band[idx],
                lower_band=lower_band[idx],
                timestamp=timestamps[idx]
            )
            
            if alert:
                print(f"ALERT: {symbol}: {alert['type']} ({alert['cross_method']})")
                self.batch_alerts.append(alert)
                self._log_alert(alert)
            else:
                print(f"OK: {symbol}")
            
            return True
            
        except Exception as e:
            print(f"ERROR: {symbol}: {e}")
            return False
    
    def _log_alert(self, alert: dict):
        os.makedirs('logs', exist_ok=True)
        log_file = f"logs/gc_30m_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(log_file, 'a', encoding='utf-8') as f:
            json.dump(alert, f)
            f.write('\n')
    
    def send_batch_alerts(self):
        if not self.batch_alerts:
            print("\nNo alerts to send")
            return
        
        total_alerts = len(self.batch_alerts)
        batch_size = 40
        
        print(f"\nSending {total_alerts} alerts in batches of {batch_size}...")
        
        batches = [self.batch_alerts[i:i + batch_size] for i in range(0, total_alerts, batch_size)]
        
        for batch_num, batch in enumerate(batches, 1):
            print(f"Batch {batch_num}/{len(batches)}: {len(batch)} alerts")
            message = self.telegram.format_batch_alert(batch, timeframe_minutes=30)
            success = self.telegram.send_message(message)
            
            if success:
                print(f"SUCCESS: Batch {batch_num} sent")
            else:
                print(f"ERROR: Batch {batch_num} failed")
    
    def run(self):
        print("\n" + "="*60)
        print("Gaussian Channel 30m Analysis")
        print("="*60 + "\n")
        
        coins = self.load_coins()
        
        if not coins:
            return
        
        print(f"Analyzing {len(coins)} coins...\n")
        
        for i, symbol in enumerate(coins, 1):
            print(f"[{i}/{len(coins)}] {symbol}")
            self.analyze_coin(symbol)
        
        print("\n" + "="*60)
        self.send_batch_alerts()

def main():
    system = Gaussian30m()
    system.run()

if __name__ == "__main__":
    main()
