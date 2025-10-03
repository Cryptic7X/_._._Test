#!/usr/bin/env python3
"""
Simple Exchange Layer - BingX + Public API Fallbacks
Supports: 15m, 30m, 1h, 2h, 4h, 8h
Standalone version - no config files required
"""

import os
import json
import time
import requests
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any

class SimpleExchangeManager:
    def __init__(self):
        """Initialize exchange manager without config files"""
        self.symbol_mapping = self.load_symbol_mapping()
        self.session = self.create_session()
    
    def load_symbol_mapping(self) -> Dict:
        """Load symbol mapping from config/symbol_mapping.json (optional)"""
        mapping_path = os.path.join(os.path.dirname(__file__), 'config', 'symbol_mapping.json')
        try:
            with open(mapping_path) as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def create_session(self):
        """Create HTTP session with headers"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Gaussian-Channel-Alert-System/1.0',
            'Accept': 'application/json'
        })
        return session
    
    def apply_symbol_mapping(self, symbol: str) -> Tuple[str, str]:
        """Apply custom symbol mappings"""
        api_symbol = self.symbol_mapping.get(symbol, symbol)
        return api_symbol, symbol
    
    def get_supported_timeframes(self) -> list:
        """Return supported timeframes"""
        return ['15m', '30m', '1h', '2h', '4h', '8h']
    
    def fetch_bingx_perpetuals_data(self, symbol: str, timeframe: str, limit: int = 200) -> Optional[Dict]:
        """Fetch BingX Perpetuals OHLCV data"""
        try:
            interval_map = {
                '15m': '15m',
                '30m': '30m',
                '1h': '1h',
                '2h': '2h',
                '4h': '4h',
                '8h': '8h'
            }
            
            if timeframe not in interval_map:
                return None
            
            url = "https://open-api.bingx.com/openApi/swap/v3/quote/klines"
            params = {
                'symbol': f"{symbol.replace('USDT', '')}-USDT",
                'interval': interval_map[timeframe],
                'limit': limit
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('code') == 0 and 'data' in data:
                candles = data['data']
                return {
                    'timestamp': [c['time'] for c in candles],
                    'open': [float(c['open']) for c in candles],
                    'high': [float(c['high']) for c in candles],
                    'low': [float(c['low']) for c in candles],
                    'close': [float(c['close']) for c in candles],
                    'volume': [float(c['volume']) for c in candles]
                }
        except:
            pass
        return None
    
    def fetch_bingx_spot_data(self, symbol: str, timeframe: str, limit: int = 200) -> Optional[Dict]:
        """Fetch BingX Spot OHLCV data"""
        try:
            interval_map = {
                '15m': '15m',
                '30m': '30m',
                '1h': '1h',
                '2h': '2h',
                '4h': '4h',
                '8h': '8h'
            }
            
            if timeframe not in interval_map:
                return None
            
            url = "https://open-api.bingx.com/openApi/spot/v1/market/kline"
            params = {
                'symbol': f"{symbol.replace('USDT', '')}-USDT",
                'interval': interval_map[timeframe],
                'limit': limit
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('code') == 0 and 'data' in data:
                candles = data['data']
                return {
                    'timestamp': [c[0] for c in candles],
                    'open': [float(c[1]) for c in candles],
                    'high': [float(c[2]) for c in candles],
                    'low': [float(c[3]) for c in candles],
                    'close': [float(c[4]) for c in candles],
                    'volume': [float(c[5]) for c in candles]
                }
        except:
            pass
        return None
    
    def fetch_kucoin_data(self, symbol: str, timeframe: str, limit: int = 200) -> Optional[Dict]:
        """Fetch KuCoin OHLCV data (Public API)"""
        try:
            interval_map = {
                '15m': '15min',
                '30m': '30min',
                '1h': '1hour',
                '2h': '2hour',
                '4h': '4hour',
                '8h': '8hour'
            }
            
            if timeframe not in interval_map:
                return None
            
            timeframe_minutes = {
                '15m': 15,
                '30m': 30,
                '1h': 60,
                '2h': 120,
                '4h': 240,
                '8h': 480
            }
            
            end_time = int(time.time())
            start_time = end_time - (limit * timeframe_minutes[timeframe] * 60)
            
            url = "https://api.kucoin.com/api/v1/market/candles"
            params = {
                'symbol': symbol,
                'type': interval_map[timeframe],
                'startAt': start_time,
                'endAt': end_time
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('code') == '200000' and 'data' in data:
                candles = sorted(data['data'], key=lambda x: int(x[0]))
                return {
                    'timestamp': [int(c[0]) * 1000 for c in candles],
                    'open': [float(c[1]) for c in candles],
                    'close': [float(c[2]) for c in candles],
                    'high': [float(c[3]) for c in candles],
                    'low': [float(c[4]) for c in candles],
                    'volume': [float(c[5]) for c in candles]
                }
        except:
            pass
        return None
    
    def fetch_okx_data(self, symbol: str, timeframe: str, limit: int = 200) -> Optional[Dict]:
        """Fetch OKX OHLCV data (Public API)"""
        try:
            interval_map = {
                '15m': '15m',
                '30m': '30m',
                '1h': '1H',
                '2h': '2H',
                '4h': '4H',
                '8h': '8H'
            }
            
            if timeframe not in interval_map:
                return None
            
            url = "https://www.okx.com/api/v5/market/candles"
            params = {
                'instId': symbol.replace('USDT', '-USDT'),
                'bar': interval_map[timeframe],
                'limit': limit
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('code') == '0' and 'data' in data:
                candles = sorted(data['data'], key=lambda x: int(x[0]))
                return {
                    'timestamp': [int(c[0]) for c in candles],
                    'open': [float(c[1]) for c in candles],
                    'high': [float(c[2]) for c in candles],
                    'low': [float(c[3]) for c in candles],
                    'close': [float(c[4]) for c in candles],
                    'volume': [float(c[5]) for c in candles]
                }
        except:
            pass
        return None
    
    def fetch_ohlcv_with_fallback(self, symbol: str, timeframe: str, limit: int = 200) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Fetch OHLCV data with multi-exchange fallback
        
        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            timeframe: Timeframe (15m, 30m, 1h, 2h, 4h, 8h)
            limit: Number of candles to fetch
        
        Returns:
            Tuple of (data_dict, source_name)
        """
        if timeframe not in self.get_supported_timeframes():
            return None, None
        
        api_symbol, display_symbol = self.apply_symbol_mapping(symbol)
        
        # Try BingX Perpetuals first
        data = self.fetch_bingx_perpetuals_data(api_symbol, timeframe, limit)
        if data and len(data.get('timestamp', [])) > 0:
            return data, 'BingX Perpetuals'
        
        # Try BingX Spot
        data = self.fetch_bingx_spot_data(api_symbol, timeframe, limit)
        if data and len(data.get('timestamp', [])) > 0:
            return data, 'BingX Spot'
        
        # Try KuCoin
        data = self.fetch_kucoin_data(api_symbol, timeframe, limit)
        if data and len(data.get('timestamp', [])) > 0:
            return data, 'KuCoin'
        
        # Try OKX
        data = self.fetch_okx_data(api_symbol, timeframe, limit)
        if data and len(data.get('timestamp', [])) > 0:
            return data, 'OKX'
        
        return None, None
